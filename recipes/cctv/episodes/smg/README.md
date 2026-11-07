# 司马光砸瓮

《古代监控实录》第 01 集。三条 10 s 的 i2v 镜头，同一个机位，后两条用上一条的末帧接力，拼成 30 s 的成片。

| 文件 | 内容 |
|---|---|
| `first_frame.png` | 第一镜的首帧（1672×941，用图像模型出的监控空镜，人物已在画面中） |
| `plate_prompt.txt` | 首帧的出图提示词（写法见 [`../../plate.md`](../../plate.md)） |
| `prompts/smg_c1.txt` … `smg_c3.txt` | 三条镜头的视频提示词 |
| `episode.json` | 后期参数：片名、文案、出处注释、每条镜头的屏显日期和时钟 |

## 原文和动作链

《宋史·司马光传》：

> 群儿戏于庭，一儿登瓮，足跌没水中，众皆弃去，光持石击瓮破之，水迸，儿得活。

动作链（动词 → 对象 → 打在哪 → 结果）：

> 一儿登瓮，**足跌**没水 → 众儿先**愣住**，再「皆弃去」→ 光**持**石（双手抱起）→ **击**瓮**侧壁下部**，前几下不破 → 瓮**破**出一个大口（一大块瓮壁脱落，瓮仍立着）→ 水**迸**，儿**随水从破口冲出** → 儿得活

原文是「瓮」（大腹小口），不是「缸」。片名沿用了大家熟悉的「砸缸」，出处注释里写明了原文是「瓮」。

## 三条镜头

| 镜头 | 动作 | 看片时核对 |
|---|---|---|
| `smg_c1`（首帧 `first_frame.png`） | 蹲在瓮沿的孩子脚下一滑，掉进瓮里没顶 → 所有孩子愣住 2 s → 三个孩子尖叫着跑出画面 → 司马光左右张望，没人 → 跑到石头边 → 双手抱起一块和他头一样大的石头，膝盖发软 | 是脚先滑落没顶，不是跳进去；先愣住再跑；跑掉三个，留下司马光 |
| `smg_c2`（首帧是 c1 的末帧） | 举过头顶 → 像劈柴一样砸在瓮侧壁下部，一声脆响，瓮一震 → 石头弹飞、人摔坐在地 → 出现裂纹 → 爬起来再砸，釉片飞溅 → 裂纹扩成网，几道细水柱喷出 | 第一下不破；砸的是侧壁下部；瓮一直立着 |
| `smg_c3`（首帧是 c2 的末帧） | 最后一次举起 → 全力砸在裂处 → 一大块下部瓮壁向外崩开，水冲出来，孩子随水从破口冲到地上 → 司马光丢下石头，跪下拍他的背 → 孩子坐起来咳水大哭，司马光累得坐倒 | 一大块瓮壁脱落而不是整只炸开；孩子是被水冲出来的 |

`smg_c2` 有 7 拍，超过「10 s 最多 4–5 拍」的建议，`prompt_lint` 会报 WARN。成片用的就是这一版，原样保留：节拍贴着上限时，看片要逐帧核对每一环。

## 屏显时间

| 镜头 | 日期 | 年号月 | s0 | 时钟 |
|---|---|---|---|---|
| smg_c1 | 1025-04-15 | 天圣三年三月 | 51785 | 14:23:05 未时 |
| smg_c2 | 1025-04-15 | 天圣三年三月 | 51795 | 14:23:15（接力） |
| smg_c3 | 1025-04-15 | 天圣三年三月 | 51805 | 14:23:25（接力） |

- 司马光生于 1019 年，七岁（虚岁）是 1025 年，即宋仁宗天圣三年。
- 首帧是春景（花开着），月份就写三月。日子取三月中气谷雨，1025 年谷雨按儒略历约在 4 月 15 日。月份和日期都是演绎，`note` 里写明了。
- 原文没写时辰，取午后的未时（孩子们在院里玩）。

## 曾经的错误

- 第一版提示词写「smash the vat」：孩子把石头抛进瓮里，整只瓮炸开。和「持石击瓮破之」不符。
- 只砸出一道细水柱，孩子自己从瓮口爬出来：「破之」是砸开一个大口，孩子要随水冲出。
- 一下就砸破：七岁孩子抱头那么大的石头，要连砸几下，前几下不破。
- 首帧是春景，屏显却写了五月。
- 有一个 seed 动作完全对，但镜头推近了：固定机位的格式里不用这条。另一个 seed 在 2.83 s 自己切了一刀，也不用。

## 复现

在仓库根目录，服务已经启动（见 [docs/01-install.md](../../../../docs/01-install.md)）：

```bash
E=recipes/cctv/episodes/smg
S=outputs/smg/shots
python3 tools/h3.py submit --kind i2v --image $E/first_frame.png --prompt-file $E/prompts/smg_c1.txt \
    --secs 10 --seed 31 --out $S/smg_c1_s31.mp4 --wait
ffmpeg -sseof -0.15 -i $S/smg_c1_s31.mp4 -frames:v 1 -update 1 $S/smg_c1_last.png
python3 tools/h3.py submit --kind i2v --image $S/smg_c1_last.png --prompt-file $E/prompts/smg_c2.txt \
    --secs 10 --seed 31 --out $S/smg_c2_s31.mp4 --wait
ffmpeg -sseof -0.15 -i $S/smg_c2_s31.mp4 -frames:v 1 -update 1 $S/smg_c2_last.png
python3 tools/h3.py submit --kind i2v --image $S/smg_c2_last.png --prompt-file $E/prompts/smg_c3.txt \
    --secs 10 --seed 31 --out $S/smg_c3_s31.mp4 --wait

for f in $S/smg_c?_s31.mp4; do python3 tools/take_gate.py $f; bash tools/contact_sheet.sh $f; done

python3 recipes/cctv/cctv_post.py $E/episode.json        # -> outputs/smg/master.mp4, outputs/smg/vertical.mp4
```

- 三条用的 seed 都是 31。同一个 seed 在不同的显卡、驱动或 WanGP 版本上不一定出同一条，把它当起点，不要当保证；不满意就换 seed 再渲。
- 每一条都要在联系表上对照上面的「看片时核对」，任何一环断了就重渲。接力的下一条要用你实际选中的那一条的末帧。
- 文件名要和 `episode.json` 里的镜头名一致（`smg_c1_s31` …）。换了 seed 的话，改文件名或改 `episode.json` 里的名字。
