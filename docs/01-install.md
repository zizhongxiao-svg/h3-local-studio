# 01 安装

要装的东西：WanGP（渲染引擎）、FastH3 模型、ffmpeg ≥ 5。质检想做全的话，再加 OpenCV、faster-whisper 和 pypinyin。本仓库的脚本本身不用装：`h3.py` 只用 Python 标准库，`h3_server.py` 用 WanGP 自己的 Python 跑。

作者在 Linux 上用。其他系统请以 WanGP 官方文档为准。

## 1. WanGP

WanGP（[deepbeepmeep/WanGP](https://github.com/deepbeepmeep/WanGP)）是把各种开源视频模型做成低显存可用的一套程序，自带界面，也有 Python API。本仓库只调用它的 API（`from shared.api import init` → `session.submit_task(settings).result()`），不打包也不改它。

1. 从官方仓库克隆，按仓库里的 INSTALLATION.md 装，包括它要求的 PyTorch / CUDA 版本和独立 Python 环境。
2. 作者验证过的版本是 commit `bd1ff59`（2026-11-04）。WanGP 更新很快，新版本的 API 或模型名如果变了，先回到这个版本对照。
3. 装完先用 WanGP 自己的界面或命令行确认能正常启动，再接本仓库的服务。

`tools/h3_server.py` 必须用 **WanGP 的那个 Python** 启动（比如 `~/WanGP/.venv/bin/python`，或你的 conda 环境），因为它要 `import` WanGP 的模块。服务启动后会把工作目录切到 WanGP 目录，和正常启动 WanGP 一致。

## 2. FastH3 模型

FastH3 Omni 8 步是 FastVideo 对 MiniMax H3 做的步数蒸馏版本（裁剪到 20B，8 步出片），DeepBeepMeep 把它打包成 WanGP 能直接用的权重，放在 Hugging Face 上。

| 显卡 | WanGP 模型名（`--model`） | 说明 |
|---|---|---|
| RTX 50 系 | `minimax_h3_fasth3_omni_nvfp4`（默认） | NVFP4 权重，用上 50 系的 FP4 张量核 |
| RTX 30/40 系 | `minimax_h3_fasth3_omni` | 同一个模型的 INT8 权重（约 20 GB）。按 WanGP 的模型说明，NVFP4 在 30/40 系上更慢，所以换 INT8 |

RTX 50 系（NVFP4）要下载的文件，以作者机器上的实际文件为准：

| 文件 | 大小 |
|---|---|
| FastH3-Omni-NVFP4-QAD-pruned_rank8_nvfp4.safetensors（视频模型） | 13.8 GB |
| qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors（文本编码器 Qwen3-VL-32B，NVFP4-AWQ） | 15.7 GB |
| MiniMax-H3-video_vae_fp16.safetensors | 5.2 GB |
| MiniMax-H3-audio_vae_fp32.safetensors | 0.6 GB |
| 合计 | 约 35 GB（磁盘留约 50 GB，放模型和成片） |

- 权重放在 WanGP 的 `ckpts/` 目录。第一次用到某个模型时 WanGP 会自己下载，具体以 WanGP 文档为准。
- 下载慢的话：WanGP 走 Hugging Face 下载，可以试试设置 `HF_ENDPOINT` 环境变量指向你能访问的镜像，再启动 WanGP 或本仓库的服务。
- 文本编码器用的是 `nvfp4_awq` 这一版，服务提交任务时会自动带上（`config: "nvfp4_awq"`），不用手动选。RTX 30/40 系换成 INT8 模型时，服务仍然带这个设置；作者没在 30/40 系上验证过。如果 WanGP 给你的卡提供了别的文本编码器版本，可以在提交时用 `--extra '{"config": "..."}'` 覆盖。
- 使用前请读 MiniMax H3 社区许可：许可排除欧盟、英国、韩国、美国；公开发布要加 AI 生成标识。详见 [NOTICE](../NOTICE)。

## 3. ffmpeg ≥ 5

WanGP 的后处理要用 `PATH` 里的 ffmpeg，而且版本要 ≥ 5（它用到 `fps_mode` 参数，旧版没有）。`h3_server.py` 启动时会检查，找不到或版本太旧会打印警告。

```bash
ffmpeg -version | head -1
```

`recipes/cctv/cctv_post.py` 对 ffmpeg 还有两个要求：带 `drawtext` 滤镜（编译时要有 libfreetype）和 `libx264` 编码器。不是每个静态编译版都有 drawtext，作者就碰到过没有的。先查一下：

```bash
ffmpeg -hide_banner -filters | grep drawtext
ffmpeg -hide_banner -encoders | grep libx264
```

不满足的话，换一个带 drawtext 的 ffmpeg，用 `--ffmpeg /path/to/ffmpeg` 传给脚本即可，不必替换系统里的那个。

## 4. 质检的可选依赖

`tools/take_gate.py` 只靠 ffmpeg 就能查模型自切和画面冻结。下面几样装了才有对应检查，没装会在结论里写明跳过了哪项：

| 依赖 | 打开的检查 |
|---|---|
| `opencv-python-headless` | ZOOM：画面持续推拉（ORB 特征点算缩放） |
| OpenCV ≥ 4.5.4 + YuNet 模型文件 | LENS：说台词时接近正脸（可能在直视镜头） |
| `faster-whisper` | 台词核对：每句有没有说出来、说没说全、有没有多出来的人声 |
| `pypinyin` | 台词核对时按拼音比对，同音字不算错 |

建议单独建一个环境，不要往 WanGP 的环境里装东西：

```bash
python3 -m venv ~/.venvs/take-gate
~/.venvs/take-gate/bin/pip install opencv-python-headless faster-whisper pypinyin
~/.venvs/take-gate/bin/python tools/take_gate.py take.mp4 --profile dialogue --lines "台词一" "台词二"
```

- YuNet 模型文件 `face_detection_yunet_2023mar.onnx` 在 OpenCV 官方的 opencv_zoo 仓库（`models/face_detection_yunet/`），下载后用 `--yunet` 传路径。
- faster-whisper 第一次运行会下载识别模型（默认 `large-v3-turbo`），在 CPU 上用 int8 跑，不占显卡，渲染可以同时进行。

## 5. 字体（只有 CCTV 后期要）

`cctv_post.py` 的屏显和竖屏文字要一个简体中文字体文件，时间码最好再有一个等宽字体。不传参数时它用 `fc-list` 自动找。

注意 `.ttc` 字体集：drawtext 只读集合里的第 0 个字体。常见的 Noto Sans CJK `.ttc` 第 0 个是日文字形（JP），部分汉字会显示成日文写法。最好用单独的简体字体文件（比如 Noto Sans CJK SC / Source Han Sans SC 的 `.otf`），用 `--font` 指定。脚本自动找字体时，如果找到的第 0 个字体不是简体，会打印警告。

## 6. 第一次加载为什么慢

开机后第一次加载模型很慢：约 35 GB 权重要先经过内存，内存不够时还要走 swap。所以本仓库用常驻服务：`h3_server.py` 在第一条任务到来时加载一次，之后每条任务都直接渲染，不再重载。README 里的速度都是模型常驻时测的。

服务空闲 15 分钟（`--idle 900`）后会自己退出，把显存和内存还给系统；`--idle 0` 表示不退出。

## 7. 自检

```bash
python3 tools/prompt_lint.py recipes/cctv/episodes/*/prompts/*.txt --secs 10    # 应当只有 smg_c2 一条 WARN
~/WanGP/.venv/bin/python tools/h3_server.py --wangp-dir ~/WanGP               # 终端 1：起服务
python3 tools/h3.py submit --kind i2v --image recipes/cctv/episodes/wenji/first_frame.png \
    --prompt-file recipes/cctv/episodes/wenji/prompts/wj_c1.txt --secs 10 --out outputs/test.mp4 --wait  # 终端 2
python3 tools/h3.py status
```

第一条任务包含模型加载，会比 README 速度表里的数慢很多。从第二条开始才是常驻速度（5080 上 10 s 的 i2v 中位 175 s）。
