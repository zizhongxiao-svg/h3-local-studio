#!/usr/bin/env python3
"""CCTV post for 《古代监控实录》: surveillance look, OSD clock and the vertical 9:16 cut.

  cctv_post.py recipes/cctv/episodes/smg/episode.json --shots outputs/smg/shots --font NotoSansCJKsc-Bold.otf

Takes <shots>/<name>.mp4 for every shot of the episode (schema in recipes/cctv/README.md) and writes
<out>/master.mp4 (1920x1080) and <out>/vertical.mp4 (1080x1920). Needs an ffmpeg with the drawtext filter and
libx264. Intermediate files and the exact commands (run.sh) stay in <out>/_work/.
"""
import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ZH = "子丑寅卯辰巳午未申酉戌亥"
MASTER_W = 1920
OX = MASTER_W * 9 // 80      # OSD inset (~11 %): stays visible when tall phones crop the sides of the vertical cut
SAFE_X, SAFE_W = 110, 860    # vertical cut: every text line stays inside x = 110..970
AI_LABEL = "内容由AI生成 · 纯属虚构演绎"
SERIES = "古代监控实录"


def dt(**k):
    return "drawtext=" + ":".join(f"{a}={v}" for a, v in k.items())


def clock(s0):
    """drawtext text of a hh:mm:ss clock that starts s0 seconds after midnight."""
    return (f"%{{eif:floor(({s0}+t)/3600):d:2}}:%{{eif:mod(floor(({s0}+t)/60),60):d:2}}"
            f":%{{eif:mod(floor({s0}+t),60):d:2}}")


def shichen(s0):
    """时辰 of the hour: 子 23-1, 丑 1-3, ..."""
    return ZH[((s0 // 3600 + 1) // 2) % 12] + "时"


def wrap(text, width):
    """Lines of at most `width` full-width characters (a run of Latin letters/digits counts 0.55 each)."""
    lines, cur, n = [], "", 0
    for tok in re.findall(r"[0-9A-Za-z.\-]+|.", text):
        k = len(tok) * 0.55 if tok[0].isascii() and tok[0].isalnum() else 1
        if cur and n + k > width:
            lines.append(cur)
            cur, n = "", 0
        cur += tok
        n += k
    return lines + ([cur] if cur else [])


def find_font(pattern, prefer=""):
    """(file, family) of a font fontconfig lists for `pattern`, preferring `prefer` in the family name, bold and
    upright. drawtext reads only face 0 of a .ttc collection, so only face 0 of each file counts."""
    try:
        out = subprocess.run(["fc-list", pattern, "--format", "%{file}\t%{index}\t%{family}\t%{style}\n"],
                             capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None, None
    faces = [x.split("\t") for x in out.splitlines() if x.count("\t") == 3]
    faces = [(f, fam, st.lower()) for f, idx, fam, st in faces if idx == "0"]
    best = min(faces, default=None, key=lambda x: (prefer not in x[1], "bold" not in x[2],
                                                   "italic" in x[2] or "oblique" in x[2], x[0]))
    return (best[0], best[1]) if best else (None, None)


def check_ffmpeg(ff):
    try:
        filters = subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=60).stdout
        encoders = subprocess.run([ff, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        sys.exit(f"cannot run {ff}; pass --ffmpeg PATH")
    missing = [n for n, txt in (("drawtext", filters), ("libx264", encoders)) if not re.search(rf"\s{n}\s", txt)]
    if missing:
        sys.exit(f"{ff} has no {' / '.join(missing)}: use an ffmpeg built with libfreetype (drawtext) and libx264")


def build(E, shots, work, out, ff):
    """ffmpeg argv lists, run inside `work`, that write out/master.mp4 and out/vertical.mp4."""
    ir, bw = E.get("ir", False), E.get("bw", True)
    txt = lambda name, s: (work / name).write_text(s, encoding="utf-8")  # noqa: E731
    osd = dict(fontcolor="white@0.92", borderw=2, bordercolor="black@0.6")
    cmds, parts, joins = [], [], []
    for i, shot in enumerate(E["shots"]):
        name, date, reign, s0 = shot[:4]
        o = shot[4] if len(shot) > 4 else {}
        cam = o.get("cam", E["cam"])
        joins.append(o.get("join", "static"))
        trim = o.get("trim")                       # [start, end] seconds of the take
        t_off = trim[0] if trim else 0
        dialogue = bool(o.get("keep_audio"))       # a take with a real quoted line keeps a wider voice band
        keep = o.get("keep_audio", not E.get("mute_src", False))
        txt(f"d{i}.txt", f"{date}  {reign}")
        txt(f"z{i}.txt", shichen(s0))
        txt(f"ts{i}.txt", clock(s0))
        txt(f"cam{i}.txt", cam)
        ch = (re.findall(r"\d+", cam.split()[0]) or ["01"])[0]
        subs = ""
        for j, (a, b, line) in enumerate(o.get("subs", [])):   # [t0, t1, "说话人：台词"] in the take's seconds
            txt(f"sub{i}_{j}.txt", line)
            subs += "," + dt(fontfile="cjk", textfile=f"sub{i}_{j}.txt", x="(w-tw)/2", y="h-236",
                             fontsize=min(76, (MASTER_W - 2 * OX) // max(1, len(line))), fontcolor="white",
                             borderw=4, bordercolor="black@0.85", box=1, boxcolor="black@0.35", boxborderw=12,
                             enable=f"'between(t,{max(0, a - t_off):.2f},{b - t_off:.2f})'")

        # cheap DVR first: 12 fps, 704x400, starved bitrate (macroblocks, smear), ~3 % of frames dropped (held);
        # an episode "crop" (source px "w:h:x:y") cuts the same window from every take, e.g. to hide burned-in text
        crop = f"crop={E['crop']}," if E.get("crop") else ""
        cut = ["-ss", f"{trim[0]}", "-t", f"{trim[1] - trim[0]}"] if trim else []
        cmds.append([ff, "-y", "-v", "error", "-i", str(shots / f"{name}.mp4"), *cut,
                     "-vf", f"{crop}fps=12,select='gt(random(0),0.03)',fps=12,scale=704:400",
                     "-c:v", "libx264", "-preset", "veryfast", "-b:v", "380k", "-maxrate", "380k", "-bufsize", "150k",
                     "-g", "24", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", f"lq{i}.mp4"])

        if ir:      # night: infrared black and white with a soft bloom
            look = ("hue=s=0,eq=contrast=1.28:gamma=1.32:brightness=0.03,split[ir0][ir1];[ir1]gblur=sigma=7[ir2];"
                    "[ir0][ir2]blend=all_mode=screen:all_opacity=0.3,hue=s=0,")
        elif bw:    # default: black and white with a slow exposure breathing
            look = "hue=s=0,eq=contrast=1.14:gamma=1.05:eval=frame:brightness='-0.02+0.012*sin(2*PI*t*0.37)',"
        else:       # washed-out colour
            look = "eq=saturation=0.62:contrast=1.06:brightness=-0.015,colorbalance=gs=0.03:bs=0.025:rh=-0.02,"
        vf = ("[0:v]fps=25,scale=1920:1080:flags=bilinear,setsar=1,lenscorrection=k1=0.045:k2=0.015," + look
              + "unsharp=7:7:1.1:7:7:0,noise=alls=12:allf=t," + ("vignette=PI/3.6," if ir else "vignette=PI/4.5,")
              + dt(fontfile="cjk", textfile=f"d{i}.txt", x=OX, y=30, fontsize=40, **osd) + ","
              + dt(fontfile="cjk", textfile=f"z{i}.txt", x=OX + 252, y=88, fontsize=40, **osd) + ","
              + dt(fontfile="mono", textfile=f"ts{i}.txt", x=OX, y=92, fontsize=46, **osd) + ","
              + dt(fontfile="cjk", text="'●'", x=f"w-{OX + 182}", y=34, fontsize=50, fontcolor="red",
                   enable="'lt(mod(t,1),0.6)'") + ","
              + dt(fontfile="mono", text="REC", x=f"w-{OX + 122}", y=40, fontsize=46, **osd) + ","
              + dt(fontfile="mono", text="CH" + ch, x=f"w-{OX + 102}", y="h-88", fontsize=42,
                   fontcolor="white@0.9", borderw=2, bordercolor="black@0.6") + ","
              + (dt(fontfile="mono", text="IR", x=f"w-{OX + 102}", y=100, fontsize=42, fontcolor="white@0.9",
                    borderw=2, bordercolor="black@0.6") + "," if ir else "")
              + dt(fontfile="cjk", textfile=f"cam{i}.txt", x=OX, y="h-90", fontsize=42, fontcolor="white@0.9",
                   borderw=2, bordercolor="black@0.6")
              + subs + "[v]")
        # mute_src drops the take's own sound (H3 improvises pseudo-speech when people talk without a quoted line)
        # and keeps only the room tone; "gate": [[t0, t1], ...] keeps a dialogue take's voice only inside those
        # windows, which removes the repeats and filler the model adds around a quoted line
        gate = ("volume='if(" + "+".join(f"between(t,{max(0, g0 - t_off):.2f},{g1 - t_off:.2f})"
                                         for g0, g1 in o["gate"]) + ",1,0)':eval=frame," if o.get("gate") else "")
        if not keep:
            af = "[0:a]aresample=48000,volume=0[a0];"
        elif dialogue:
            af = f"[0:a]aresample=48000,{gate}highpass=f=200,lowpass=f=5200,acompressor=threshold=-20dB:ratio=3,volume=1.4[a0];"
        else:
            af = "[0:a]aresample=48000,highpass=f=280,lowpass=f=3600,acompressor=threshold=-20dB:ratio=3,volume=1.1[a0];"
        af += "anoisesrc=color=pink:amplitude=0.018:r=48000[n];[a0][n]amix=inputs=2:duration=first,volume=2[a]"
        cmds.append([ff, "-y", "-v", "error", "-i", f"lq{i}.mp4", "-filter_complex", f"{vf};{af}",
                     "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", f"p{i}.mp4"])
        parts.append(f"p{i}.mp4")

    seq = [parts[0]]
    for k in range(1, len(parts)):
        seq += ["static.mp4", parts[k]] if joins[k] == "static" else [parts[k]]
    if "static.mp4" in seq:   # time jump on the same camera: 0.3 s of snow, then 0.5 s NO SIGNAL
        cmds.append([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=1920x1080:r=25:d=0.8",
                     "-f", "lavfi", "-i", "anoisesrc=color=white:amplitude=0.12:r=48000:d=0.8",
                     "-vf", "setsar=1,noise=alls=100:allf=t+u,drawbox=c=black:t=fill:enable='gte(t,0.3)',"
                     + dt(fontfile="mono", text="'NO SIGNAL'", x="(w-tw)/2", y="(h-th)/2", fontsize=90,
                          fontcolor="white", enable="'gte(t,0.3)'") + ","
                     + dt(fontfile="cjk", textfile="cam0.txt", x=OX, y="h-90", fontsize=42, fontcolor="white@0.9",
                          enable="'gte(t,0.3)'"),
                     "-af", "volume='if(lt(t,0.3),1,0)':eval=frame", "-c:v", "libx264", "-preset", "medium",
                     "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-shortest",
                     "static.mp4"])
    inputs = [x for p in seq for x in ("-i", p)]
    # temporal noise makes x264 explode in size (a 28 s master reached 282 MB at crf 19): cap the bitrate
    cmds.append([ff, "-y", "-v", "error", *inputs, "-filter_complex",
                 "".join(f"[{k}:v][{k}:a]" for k in range(len(seq))) + f"concat=n={len(seq)}:v=1:a=1[v][a]",
                 "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                 "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                 str(out / "master.mp4")])

    # vertical 1080x1920: series title + episode title, the footage band at full width, a 2-line hook caption,
    # 【tag】 + source note and the AI label. Tall phones (19.5:9, 20:9) fill the height and crop ~9-10 % off each
    # side, so the OSD sits inset (OX) and every text line stays inside x = 110..970.
    txt("t1.txt", SERIES)
    txt("t2.txt", E["title"])
    for j, c in enumerate(E["caption"]):
        txt(f"c{j}.txt", c)
    note = wrap(E["note"], 25)
    if len(note) > 7:
        print(f"warning: the note wraps to {len(note)} lines; more than 7 run into the AI label", file=sys.stderr)
    for j, line in enumerate(note):
        txt(f"n{j}.txt", line)
    txt("tag.txt", "【" + E["tag"] + "】")
    txt("ai.txt", AI_LABEL)
    cap_fs = min(54, SAFE_W // max(len(c) for c in E["caption"]))
    title_fs = min(64, SAFE_W // max(1, len(E["title"])))
    vv = ("color=c=0x101214:s=1080x1920:r=25[bg];[0:v]scale=1080:608,setsar=1[m];[bg][m]overlay=0:656:shortest=1,"
          + dt(fontfile="cjk", textfile="t1.txt", x="(w-tw)/2", y=330, fontsize=96, fontcolor="white") + ","
          + dt(fontfile="cjk", textfile="t2.txt", x="(w-tw)/2", y=470, fontsize=title_fs, fontcolor="0xFFC83D") + ","
          + dt(fontfile="cjk", text="'▼ 原始监控画面'", x=SAFE_X, y=600, fontsize=34, fontcolor="0x9aa3ad") + ","
          + ",".join(dt(fontfile="cjk", textfile=f"c{j}.txt", x="(w-tw)/2", y=1300 + j * (cap_fs + 22),
                        fontsize=cap_fs, fontcolor="white") for j in range(len(E["caption"]))) + ","
          + dt(fontfile="cjk", textfile="tag.txt", x=SAFE_X, y=1470, fontsize=34, fontcolor="0xFFC83D") + ","
          + ",".join(dt(fontfile="cjk", textfile=f"n{j}.txt", x=SAFE_X, y=1520 + j * 44, fontsize=32,
                        fontcolor="0xaab2bb") for j in range(len(note))) + ","
          + dt(fontfile="cjk", textfile="ai.txt", x="(w-tw)/2", y=1858, fontsize=32, fontcolor="0x7d848c") + "[v]")
    cmds.append([ff, "-y", "-v", "error", "-i", str(out / "master.mp4"), "-filter_complex", vv,
                 "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                 "-maxrate", "5M", "-bufsize", "10M", "-pix_fmt", "yuv420p", "-c:a", "copy", str(out / "vertical.mp4")])
    return cmds


def link(src, dst):
    dst.unlink(missing_ok=True)
    try:
        dst.symlink_to(Path(src).resolve())
    except OSError:
        shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", help="episode.json")
    ap.add_argument("--ep", help="episode key, when the file holds several episodes")
    ap.add_argument("--shots", help="folder with <shot name>.mp4 (default: <out>/shots)")
    ap.add_argument("--out", help="output folder (default: outputs/<episode key>)")
    ap.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg with drawtext (libfreetype) and libx264")
    ap.add_argument("--font", help="Simplified Chinese font file (default: fc-list's Chinese font, preferring a bold "
                                   "SC face; drawtext reads only face 0 of a .ttc)")
    ap.add_argument("--mono-font", help="monospace font for the clock, REC, CH and NO SIGNAL "
                                        "(default: fc-list's monospace font, else --font)")
    ap.add_argument("--dry-run", action="store_true", help="only write <out>/_work/run.sh")
    a = ap.parse_args()

    data = json.loads(Path(a.episode).read_text(encoding="utf-8"))
    key = a.ep or (next(iter(data)) if len(data) == 1 else None)
    if key not in data:
        sys.exit(f"pick an episode with --ep: {', '.join(data)}")
    E = data[key]
    out = Path(a.out or f"outputs/{key}").resolve()
    shots = Path(a.shots).resolve() if a.shots else out / "shots"
    missing = [s[0] for s in E["shots"] if not (shots / f"{s[0]}.mp4").is_file()]
    if missing and not a.dry_run:
        sys.exit(f"missing takes in {shots}: " + ", ".join(f"{m}.mp4" for m in missing))
    font = a.font
    if not font:
        font, family = find_font(":lang=zh-cn", prefer=" SC")
        if not font:
            sys.exit("no Chinese font found; pass --font PATH")
        if re.search(r"\b(JP|KR|TC|HK)\b", family):
            print(f"warning: {font} starts with {family}; some characters get non-Simplified shapes. "
                  "Pass --font with a Simplified Chinese (SC) font file", file=sys.stderr)
    mono = a.mono_font or find_font(":spacing=mono")[0] or font
    work = out / "_work"
    work.mkdir(parents=True, exist_ok=True)
    link(font, work / "cjk")
    link(mono, work / "mono")
    cmds = build(E, shots, work, out, a.ffmpeg)
    (work / "run.sh").write_text("set -e\ncd " + shlex.quote(str(work)) + "\n"
                                 + "\n".join(shlex.join(c) for c in cmds) + "\n", encoding="utf-8")
    if a.dry_run:
        print(work / "run.sh")
        return
    check_ffmpeg(a.ffmpeg)
    for k, c in enumerate(cmds, 1):
        print(f"[{k}/{len(cmds)}] {Path(c[-1]).name}", flush=True)
        subprocess.run(c, cwd=work, check=True)
    print("OK", out / "master.mp4", out / "vertical.mp4")


if __name__ == "__main__":
    main()
