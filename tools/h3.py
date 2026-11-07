#!/usr/bin/env python3
"""Submit and track renders for tools/h3_server.py (standard library only, Python >= 3.10).

  h3.py submit --kind i2v --image first.png --prompt-file shot.txt --secs 10 --out shots/s01.mp4 [--wait]
  h3.py submit --kind r2v --image first.png --refs cast_a.png,cast_b.png --auds a.wav,b.wav \\
               --prompt-file seg.txt --secs 10 --out seg01.mp4
  h3.py wait ID [ID ...]     block until the jobs finish and copy each mp4 to its --out
  h3.py status               server heartbeat, queued count, the running job
  h3.py list                 every job in the queue folder
  h3.py cancel ID            drop a queued job (a running job always finishes)

From Python (e.g. a batch script):
  import h3
  ids = [h3.submit("queue", "i2v", img, open(p).read(), 10, out=o) for img, p, o in shots]
  h3.wait("queue", ids)
"""
import argparse
import json
import os
import random
import shutil
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prompt_lint  # noqa: E402

SIZES = {"i2v": (1344, 768), "r2v": (768, 1344)}
ALIVE_SECS = 30


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_result(queue, res):
    (queue / "results").mkdir(parents=True, exist_ok=True)
    tmp = queue / "results" / f".{res['id']}.tmp"
    tmp.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, queue / "results" / f"{res['id']}.json")


def server_pid(queue):
    """pid of a live server process for this queue folder, else None."""
    try:
        pid = int((queue / "pid").read_text())
    except (OSError, ValueError):
        return None
    try:
        os.kill(pid, 0)
    except PermissionError:   # alive, but run by another user
        return pid
    except OSError:
        return None
    return pid


def heartbeat_age(queue):
    try:
        return time.time() - (queue / "heartbeat").stat().st_mtime
    except OSError:
        return None


def server_alive(queue):
    queue = Path(queue)
    age = heartbeat_age(queue)
    return server_pid(queue) is not None and age is not None and age < ALIVE_SECS


def submit(queue, kind, image, prompt, secs, out=None, last=None, refs=(), auds=(), w=None, h=None,
           seed=None, extra=None, lint=True):
    """Queue one job and return its id. Raises ValueError for a job that would fail or render badly."""
    queue = Path(queue)
    refs, auds = list(refs), list(auds)
    if kind not in SIZES:
        raise ValueError(f"kind must be i2v or r2v, not {kind!r}")
    if secs < prompt_lint.MIN_SECS:
        raise ValueError(f"{secs} s is too short: FastH3 renders at least {prompt_lint.MIN_SECS} s and fills shorter "
                         "requests with improvised speech. Render 4.5 s or more and cut it shorter in the edit")
    if kind == "i2v" and (refs or auds):
        raise ValueError("reference images and voices (--refs/--auds) need --kind r2v")
    if kind == "r2v" and last:
        raise ValueError("a last frame (--last) works only with --kind i2v")
    if len(auds) > 3:
        raise ValueError("at most 3 voice references")
    if extra is not None and not isinstance(extra, dict):
        raise ValueError("extra must be a JSON object")
    files = [("image", image)] + ([("last", last)] if last else [])
    files += [(f"ref{i + 1}", f) for i, f in enumerate(refs)] + [(f"aud{i + 1}", f) for i, f in enumerate(auds)]
    missing = [str(f) for _, f in files if not Path(f).is_file()]
    if missing:
        raise ValueError("file(s) not found: " + ", ".join(missing))
    errors, warns = prompt_lint.lint(prompt, secs)
    for m in warns:
        print("lint WARN ", m, file=sys.stderr)
    for m in errors:
        print("lint ERROR", m, file=sys.stderr)
    if errors and lint:
        raise ValueError("the prompt has lint errors (above); fix them or pass --no-lint")

    jid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    inp = queue / "input" / jid
    inp.mkdir(parents=True)
    rel = {}
    for role, f in files:
        dst = inp / f"{role}_{Path(f).name}"
        shutil.copy2(f, dst)
        rel[role] = dst.relative_to(queue).as_posix()
    dw, dh = SIZES[kind]
    job = {"id": jid, "kind": kind, "image": rel["image"], "last": rel.get("last"),
           "refs": [rel[f"ref{i + 1}"] for i in range(len(refs))],
           "auds": [rel[f"aud{i + 1}"] for i in range(len(auds))],
           "prompt": prompt, "secs": secs, "w": w or dw, "h": h or dh,
           "seed": seed if seed is not None else random.randint(1, 2**31 - 1), "extra": extra or {},
           "out": str(Path(out).resolve()) if out else None, "submitted": time.time()}
    (queue / "jobs").mkdir(parents=True, exist_ok=True)
    tmp = queue / "jobs" / f".{jid}.tmp"
    tmp.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, queue / "jobs" / f"{jid}.json")
    if not server_alive(queue):
        print(f"note: no server heartbeat in {queue}; the job waits until tools/h3_server.py runs", file=sys.stderr)
    return jid


def collect(queue, res):
    """Report one finished job; copy its mp4 to the job's out. Returns done / failed / cancelled."""
    jid, job = res["id"], res.get("job") or {}
    if res.get("ok"):
        src, out = queue / res["mp4"], job.get("out")
        if out:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out)
        print(f"{jid} done: {res.get('render_secs')} s render, seed {job.get('seed')} -> {out or src}", flush=True)
        return "done"
    state = "cancelled" if res.get("cancelled") else "failed"
    print(f"{jid} {state}: {res.get('error', '')}", flush=True)
    return state


def wait(queue, ids, timeout=None, poll=2.0):
    """Block until every job has finished. Returns {id: done|failed|cancelled|lost|unknown|timeout}."""
    queue = Path(queue)
    left, state, t0, hinted = list(dict.fromkeys(ids)), {}, time.time(), False
    while left:
        for jid in list(left):
            res_file = queue / "results" / f"{jid}.json"
            if (queue / "jobs" / f"{jid}.json").exists():
                continue
            if (queue / "running" / f"{jid}.json").exists():
                if server_pid(queue) is not None or res_file.exists():
                    continue
                state[jid] = "lost"
                print(f"{jid} lost: the server stopped during the job; resubmit it", flush=True)
            elif res_file.exists():
                state[jid] = collect(queue, read_json(res_file))
            else:
                state[jid] = "unknown"
                print(f"{jid}: no such job in {queue}", flush=True)
            left.remove(jid)
        if left and not hinted and not server_alive(queue):
            print(f"waiting: no server heartbeat in {queue}; start tools/h3_server.py", file=sys.stderr, flush=True)
            hinted = True
        if left and timeout and time.time() - t0 > timeout:
            state.update({jid: "timeout" for jid in left})
            break
        if left:
            time.sleep(poll)
    return state


def jobs_in(queue, folder):
    """[(mtime, data)] of the job/result files in one folder; files that vanish meanwhile are skipped."""
    out = []
    for p in sorted((queue / folder).glob("*.json")):
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        data = read_json(p)
        if data:
            out.append((mtime, data))
    return out


def status(queue):
    queue = Path(queue)
    age, pid = heartbeat_age(queue), server_pid(queue)
    if server_alive(queue):
        print(f"server  : running (pid {pid}, heartbeat {age:.0f} s ago)")
    else:
        print("server  : not running" + (f" (last heartbeat {age:.0f} s ago)" if age is not None else ""))
    print(f"queued  : {len(jobs_in(queue, 'jobs'))}")
    for mtime, job in jobs_in(queue, "running"):
        print(f"running : {job['id']}  {job['kind']} {job['secs']} s {job['w']}x{job['h']} seed {job['seed']}"
              f"  ({time.time() - mtime:.0f} s so far)")
    counts = {"done": 0, "failed": 0, "cancelled": 0}
    for _, res in jobs_in(queue, "results"):
        counts["done" if res.get("ok") else "cancelled" if res.get("cancelled") else "failed"] += 1
    print("results : " + ", ".join(f"{n} {k}" for k, n in counts.items()))


def list_jobs(queue):
    queue = Path(queue)
    rows = [(job["id"], "queued", job) for _, job in jobs_in(queue, "jobs")]
    rows += [(job["id"], "running", job) for _, job in jobs_in(queue, "running")]
    for _, res in jobs_in(queue, "results"):
        st = "done" if res.get("ok") else "cancelled" if res.get("cancelled") else "failed"
        rows.append((res["id"], st, res.get("job") or {}))
    for jid, st, job in sorted(rows, key=lambda r: r[0]):
        size = f"{job.get('w')}x{job.get('h')}" if job else "?"
        print(f"{jid}  {st:9}  {job.get('kind', '?'):3}  {job.get('secs', '?'):>5} s  {size:9}  "
              f"seed {job.get('seed', '?'):<10}  {job.get('out') or ''}")


def cancel(queue, jid):
    queue = Path(queue)
    held = queue / "jobs" / f".{jid}.cancel"
    try:
        os.rename(queue / "jobs" / f"{jid}.json", held)   # the server claims jobs with the same rename
    except FileNotFoundError:
        raise ValueError(f"{jid} is not queued (a running job always finishes; see `h3.py list`)") from None
    write_result(queue, {"id": jid, "ok": False, "cancelled": True, "error": "cancelled", "job": read_json(held) or {}})
    held.unlink()
    print(f"{jid} cancelled")


def split_list(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--queue", default="queue", help="queue folder of the server (default: ./queue)")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit", parents=[common], help="queue one shot")
    s.add_argument("--kind", choices=SIZES, required=True,
                   help="i2v: first frame (+ last frame) + prompt; r2v: first frame + reference images + voices")
    s.add_argument("--image", required=True, help="first frame (<Picture 1>)")
    s.add_argument("--last", help="i2v only: last frame to land on")
    s.add_argument("--refs", help="r2v only: comma-separated reference images (<Picture 2>, <Picture 3>, ...)")
    s.add_argument("--auds", help="r2v only: up to 3 comma-separated voice references (<Audio 1..3>), ~5 s each")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--prompt", help="prompt text (structured English form)")
    g.add_argument("--prompt-file", help="file with the prompt")
    s.add_argument("--secs", type=float, required=True, help="clip length in seconds (4.5-12 recommended)")
    s.add_argument("--w", type=int, help="width (default: 1344 for i2v, 768 for r2v)")
    s.add_argument("--h", type=int, help="height (default: 768 for i2v, 1344 for r2v)")
    s.add_argument("--seed", type=int, help="seed (default: random, recorded in the job)")
    s.add_argument("--extra", help="JSON object of extra WanGP settings, merged last")
    s.add_argument("--out", required=True, help="where --wait / wait copies the finished mp4")
    s.add_argument("--wait", action="store_true", help="block until the take is rendered")
    s.add_argument("--no-lint", action="store_true", help="submit even when prompt_lint reports errors")
    w = sub.add_parser("wait", parents=[common], help="wait for jobs and collect their mp4s")
    w.add_argument("ids", nargs="+")
    w.add_argument("--timeout", type=float, help="give up after this many seconds")
    sub.add_parser("status", parents=[common], help="server and queue state")
    sub.add_parser("list", parents=[common], help="every job with its state")
    c = sub.add_parser("cancel", parents=[common], help="drop queued jobs")
    c.add_argument("ids", nargs="+")
    a = ap.parse_args(argv)
    queue = Path(a.queue)
    try:
        if a.cmd == "submit":
            prompt = a.prompt if a.prompt is not None else Path(a.prompt_file).read_text(encoding="utf-8")
            extra = json.loads(a.extra) if a.extra else None
            jid = submit(queue, a.kind, a.image, prompt, a.secs, out=a.out, last=a.last, refs=split_list(a.refs),
                         auds=split_list(a.auds), w=a.w, h=a.h, seed=a.seed, extra=extra, lint=not a.no_lint)
            print(jid, flush=True)
            return 0 if not a.wait or wait(queue, [jid])[jid] == "done" else 1
        if a.cmd == "wait":
            return 0 if all(v == "done" for v in wait(queue, a.ids, a.timeout).values()) else 1
        if a.cmd == "status":
            status(queue)
        elif a.cmd == "list":
            list_jobs(queue)
        elif a.cmd == "cancel":
            for jid in a.ids:
                cancel(queue, jid)
        return 0
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
