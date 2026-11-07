# h3-local-studio

Make AI video with MiniMax H3 (FastH3 Omni, 8 steps) on one NVIDIA card at home: how to install it, how to write
prompts that work, the production process, automatic checks for every take, and two formats that were actually
finished with it. The docs are in Simplified Chinese; the code and its comments are in English.

There is no new model here and no one-click film. The value is the record of what fails, why, and what to write
instead, plus a few small tools: a resident render server (the model loads once), a submit client, a prompt linter,
a per-take quality gate and the post-processing script for the CCTV format.

## Samples

Two episodes of 《古代监控实录》 ("ancient CCTV": Chinese history scenes re-staged as fixed-camera surveillance
footage), 司马光砸瓮 and 闻鸡起舞, were made with this workflow and published on the author's WeChat Channels account.
Their first frames, all prompts, seeds and post settings are in [`recipes/cctv/episodes/`](recipes/cctv/episodes/).

## Hardware

All numbers were measured on an **RTX 5080 (16 GB)**; anything about other cards is arithmetic from them.

| | measured / arithmetic | advice |
|---|---|---|
| GPU | RTX 50: NVFP4 model (default). RTX 30/40: the INT8 file of the same model (~20 GB weights; NVFP4 is slower without FP4 tensor cores) | RTX 50 fits best; RTX 30/40 speed and memory were not measured |
| VRAM | H3 process peak 6.0–6.2 GB (12 s 1344×768 i2v, sampled every 2 s for 5 min) | 16 GB is plenty. A 12 GB card has ~2× headroom at 768p by arithmetic; **the author has not run a 12 GB card** |
| RAM | the render process holds 22–28 GB; the author's box has 30 GB RAM + 15 GB swap, swap fills up, it still renders | 32 GB minimum with ≥ 16 GB swap; 64 GB is comfortable |
| Disk | model files ≈ 35 GB | keep ~50 GB free |
| Resolution | 1080×1920: 7 s rendered in 317 s; 12 s stalled with only ~4.7 GB free (another program held the card), not tested with the full card free | use 768p (1344×768 / 768×1344) on 12–16 GB cards |

Speed on the RTX 5080 (median of 506 real jobs, 8 steps, model kept loaded):

| job | clip | median |
|---|---|---|
| i2v (first frame + prompt) 1344×768 | 5 / 10 / 12 s | 88 / 175 / 220 s |
| r2v (first frame + reference images + voice) 768×1344 | 5 / 6 / 8 / 10 s | 90 / 111 / 144–153 / 190 s |

Rule of thumb: ~18 s of render time per second of 768p video.

## Quick start

1. Install WanGP and the model ([docs/01-install.md](docs/01-install.md)).
2. From the repo root, start the server with WanGP's own Python:
   `~/WanGP/.venv/bin/python tools/h3_server.py --wangp-dir ~/WanGP`
3. From the repo root, in another terminal:

   ```bash
   python3 tools/h3.py submit --kind i2v --image recipes/cctv/episodes/smg/first_frame.png \
       --prompt-file recipes/cctv/episodes/smg/prompts/smg_c1.txt --secs 10 --seed 31 \
       --out outputs/smg/shots/smg_c1_s31.mp4 --wait
   python3 tools/take_gate.py outputs/smg/shots/smg_c1_s31.mp4
   bash tools/contact_sheet.sh outputs/smg/shots/smg_c1_s31.mp4
   ```

Prompts must be the structured English form (`subject_definitions / summary / retention_analysis /
detailed_description / overall_soundscape / non_diegetic_music`): FastH3 burns Chinese description text into the
picture as subtitles, so Chinese goes only inside quoted spoken lines “…”. `tools/prompt_lint.py` enforces this.

## Layout

- `tools/` — `h3_server.py` (resident server), `h3.py` (client: submit / wait / status / list / cancel, standard
  library only), `prompt_lint.py`, `take_gate.py` + `qa/` (cuts, freezes, push/pull drift, frontal head while
  speaking, spoken-line check), `contact_sheet.sh`.
- `docs/` — install, hardware and speed, prompt guide, workflow, recipes (CCTV, wuxia MV, dialogue drama), lessons.
- `recipes/cctv/` — the CCTV recipe, review prompt, first-frame recipe, `cctv_post.py` and two complete episodes.

## Licence and credits

MIT for this repository's code and documents (see [LICENSE](LICENSE)); third-party notices in [NOTICE](NOTICE).
Nothing third-party is bundled.

- WanGP ([deepbeepmeep/WanGP](https://github.com/deepbeepmeep/WanGP), WanGP Community License 2.0): only its public
  Python API is called; not bundled or modified.
- MiniMax H3 is licensed under the MiniMax H3 Community License Agreement, Copyright © 2026 MiniMax. All Rights
  Reserved. Excluded territories: EU, UK, South Korea, US. Follow its Acceptable Use Policy: label AI-generated
  content (Exhibit A §12), no IP infringement, no impersonation.
- FastH3 Omni 8-step: FastVideo's step distillation, packaged for WanGP by DeepBeepMeep on Hugging Face.
- The character face-library method comes from the public WeChat article "GPT Image 2.5 做 Seedance 2.5 角色脸型库"
  by 远见明察 (2026-11).
- Every public AI video needs an AI-generated label; the CCTV vertical cut burns in "内容由AI生成 · 纯属虚构演绎".
