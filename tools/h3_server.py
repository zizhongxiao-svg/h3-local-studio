#!/usr/bin/env python3
"""Resident MiniMax H3 render server: loads WanGP once and renders every job put into the queue folder,
so the model stays loaded between shots. Run it with WanGP's own Python:

    ~/WanGP/.venv/bin/python tools/h3_server.py --wangp-dir ~/WanGP

Submit jobs with tools/h3.py. Queue folder (default ./queue), shared with h3.py:
    jobs/<id>.json       queued jobs, oldest first (written as .tmp + rename)
    running/<id>.json    the job being rendered
    results/<id>.json    {"ok": true, "mp4": "output/<id>.mp4", ...} or {"ok": false, "error": "..."}
    input/<id>/          the job's images and voice references
    output/<id>.mp4      rendered takes
    heartbeat, pid, server.lock, STOP
"""
import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

MODEL = "minimax_h3_fasth3_omni_nvfp4"
STEPS = 8
FPS = 24


def log(*msg):
    print(time.strftime("%H:%M:%S"), *msg, flush=True)


def video_length(secs):
    """Frames for a clip of `secs` seconds: 24 fps, rounded up to the 17n+5 counts the model takes."""
    n = max(5, round(secs * FPS))
    return n + (5 - n % 17) % 17


def settings(job, queue, model):
    """WanGP task settings for one job."""
    path = lambda rel: str(queue / rel)  # noqa: E731
    st = {"model_type": model, "config": "nvfp4_awq",  # text-encoder variant (Qwen3-VL-32B NVFP4-AWQ)
          "prompt": job["prompt"], "image_prompt_type": "S",
          "image_start": path(job["image"]), "image_refs": [path(job["image"])],  # FastH3 needs >= 1 reference image
          "resolution": f"{job['w']}x{job['h']}", "video_length": video_length(job["secs"]),
          "num_inference_steps": STEPS, "seed": job["seed"],
          "multi_prompts_gen_type": "FG"}  # otherwise blank lines split the prompt into several jobs
    if job["kind"] == "i2v" and job.get("last"):
        st["image_prompt_type"] = "SE"
        st["image_end"] = path(job["last"])
    if job["kind"] == "r2v":
        st["image_refs"] = [path(r) for r in job.get("refs") or [job["image"]]]
        auds = (job.get("auds") or [])[:3]
        if auds:
            st["audio_prompt_type"] = ["A", "AB", "ABD"][len(auds) - 1]
            for i, a in enumerate(auds):
                st["audio_guide" + (str(i + 1) if i else "")] = path(a)
    st.update(job.get("extra") or {})
    return st


def render(session, job, queue, model):
    st = settings(job, queue, model)
    log(f"{job['id']}: {job['kind']} {st['resolution']}, {st['video_length']} frames, seed {job['seed']}")
    t0 = time.time()
    r = session.submit_task(st).result()
    if not r.success:
        raise RuntimeError("; ".join(str(getattr(e, "message", e)) for e in (r.errors or [])) or "WanGP failed")
    mp4 = [f for f in r.generated_files if str(f).endswith(".mp4")]
    if not mp4:
        raise RuntimeError("WanGP finished without writing an mp4")
    shutil.move(str(mp4[-1]), queue / "output" / f"{job['id']}.mp4")
    return {"mp4": f"output/{job['id']}.mp4", "render_secs": round(time.time() - t0, 1), "frames": st["video_length"]}


def write_result(queue, res):
    tmp = queue / "results" / f".{res['id']}.tmp"
    tmp.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, queue / "results" / f"{res['id']}.json")


def fail_leftovers(queue):
    """Jobs still in running/ belong to a server that stopped mid-job: report them as failed."""
    for run in (queue / "running").glob("*.json"):
        try:
            job = json.loads(run.read_text(encoding="utf-8"))
        except ValueError:
            job = {}
        write_result(queue, {"id": run.stem, "ok": False, "job": job,
                             "error": "interrupted: the server stopped during this job; resubmit it"})
        run.unlink(missing_ok=True)


def oldest_job(queue):
    found = []
    for p in (queue / "jobs").glob("*.json"):
        try:
            found.append((p.stat().st_mtime, p.name, p))
        except FileNotFoundError:   # cancelled meanwhile
            pass
    return min(found)[2] if found else None


def heartbeat(path):
    while True:   # a thread, because loading and rendering block the main loop for minutes
        try:
            path.touch()
        except OSError:
            pass
        time.sleep(5)


def gpu_temp():
    cmd = ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"]
    card = os.environ.get("CUDA_VISIBLE_DEVICES", "").split(",")[0].strip()
    if card:
        cmd += ["-i", card]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True).stdout
        return max(int(t) for t in out.split())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def wait_cool(pause, resume, stop):
    t = gpu_temp()
    if t is None or t < pause:
        return
    log(f"GPU at {t} °C (>= {pause} °C): pausing until it is at or below {resume} °C")
    while not stop.exists():
        time.sleep(15)
        t = gpu_temp()
        if t is None or t <= resume:
            log(f"GPU at {t} °C: resuming")
            return


def check_ffmpeg():
    try:
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        log("warning: no ffmpeg on PATH; WanGP's post-processing needs ffmpeg >= 5")
        return
    m = re.match(r"ffmpeg version n?(\d+)\.", out)
    if m and int(m.group(1)) < 5:
        log(f"warning: ffmpeg {m.group(1)}.x on PATH; WanGP's post-processing needs ffmpeg >= 5")


def serve(a):
    queue = Path(a.queue).resolve()
    for d in ("jobs", "running", "results", "input", "output"):
        (queue / d).mkdir(parents=True, exist_ok=True)
    lock = os.open(queue / "server.lock", os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log(f"another server already serves {queue}; exiting")
        return 1
    stop = queue / "STOP"
    stop.unlink(missing_ok=True)
    (queue / "pid").write_text(str(os.getpid()))
    threading.Thread(target=heartbeat, args=(queue / "heartbeat",), daemon=True).start()
    fail_leftovers(queue)

    wangp = Path(a.wangp_dir).expanduser().resolve()
    sys.path.insert(0, str(wangp))
    os.chdir(wangp)   # same working directory as a normal WanGP start
    try:
        from shared.api import init
    except ImportError as e:
        log(f"cannot import shared.api from {wangp} ({e}); start this script with WanGP's own python")
        (queue / "pid").unlink(missing_ok=True)
        return 1
    check_ffmpeg()
    if a.pause_temp and gpu_temp() is None:
        log("warning: nvidia-smi gives no temperature; the thermal pause is off")

    session, last_work = None, time.time()
    log(f"serving {queue}: {a.model}, profile {a.profile}, idle exit {f'{a.idle:.0f} s' if a.idle > 0 else 'off'}")
    try:
        while not stop.exists() and (a.idle <= 0 or time.time() - last_work < a.idle):
            jf = oldest_job(queue)
            if jf is None:
                time.sleep(1)
                continue
            if a.pause_temp:
                wait_cool(a.pause_temp, a.resume_temp, stop)
                if stop.exists():
                    break
            run = queue / "running" / jf.name
            try:
                os.rename(jf, run)   # claim it; `h3.py cancel` races for the same file with its own rename
            except FileNotFoundError:
                continue
            run.touch()
            res = {"id": jf.stem}
            try:
                job = res["job"] = json.loads(run.read_text(encoding="utf-8"))
                if session is None:
                    log(f"loading WanGP ({a.model}); the first load after a reboot is slow")
                    session = init(root=wangp, output_dir=queue / "wangp_out",
                                   cli_args=["--profile", str(a.profile)], console_output=True)
                res.update(ok=True, **render(session, job, queue, a.model))
                log(f"{jf.stem}: done in {res['render_secs']} s")
            except Exception as e:   # one bad job must not take the server down
                res.update(ok=False, error=str(e)[-2000:])
                log(f"{jf.stem}: failed: {res['error']}")
            write_result(queue, res)
            run.unlink(missing_ok=True)
            last_work = time.time()
        log("exit:", "STOP requested" if stop.exists() else f"idle for {a.idle:.0f} s")
    except KeyboardInterrupt:
        log("exit: interrupted")
    finally:
        fail_leftovers(queue)
        (queue / "pid").unlink(missing_ok=True)
        stop.unlink(missing_ok=True)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wangp-dir", default=os.environ.get("WANGP_DIR"), help="WanGP checkout (default: $WANGP_DIR)")
    ap.add_argument("--queue", default="queue", help="queue folder shared with h3.py (default: ./queue)")
    ap.add_argument("--model", default=MODEL,
                    help="WanGP model_type (default: %(default)s for RTX 50; RTX 30/40: minimax_h3_fasth3_omni)")
    ap.add_argument("--profile", default="5", help="WanGP memory profile (default: 5, the most RAM-frugal)")
    ap.add_argument("--idle", type=float, default=900,
                    help="exit after this many seconds without a job, 0 = never (default: 900)")
    ap.add_argument("--pause-temp", type=int, help="before each job, wait while the GPU is at or above this °C")
    ap.add_argument("--resume-temp", type=int, default=70, help="resume at or below this °C (default: 70)")
    ap.add_argument("--stop", action="store_true", help="ask the running server to exit after its current job")
    a = ap.parse_args()
    if a.stop:
        queue = Path(a.queue)
        queue.mkdir(parents=True, exist_ok=True)
        (queue / "STOP").touch()
        print(f"{queue / 'STOP'} written; the server exits after its current job")
        return 0
    if not a.wangp_dir:
        ap.error("pass --wangp-dir or set WANGP_DIR")
    if not Path(a.wangp_dir).expanduser().is_dir():
        ap.error(f"WanGP folder not found: {a.wangp_dir}")
    missing = [t for t in ("ffmpeg", "ffprobe") if not shutil.which(t)]
    if missing:   # WanGP muxes the video and audio with them; without them every job fails after rendering
        ap.error(f"{' and '.join(missing)} not on PATH; install ffmpeg >= 5 (see docs/01-install.md)")
    return serve(a)


if __name__ == "__main__":
    sys.exit(main())
