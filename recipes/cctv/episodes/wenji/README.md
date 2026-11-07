# 闻鸡起舞

《古代监控实录》第 08 集。半夜，红外夜视。两条 10 s 的 i2v 镜头，同一个机位，第二条用第一条的末帧接力，拼成 20 s 的成片。

| 文件 | 内容 |
|---|---|
| `first_frame.png` | 第一镜的首帧（红外黑白，两人同盖一床被睡着，右边篱笆上站着鸡，墙边兵器架上有两把剑） |
| `plate_prompt.txt` | 首帧的出图提示词（红外版底句，写法见 [`../../plate.md`](../../plate.md)） |
| `prompts/wj_c1.txt`、`wj_c2.txt` | 两条镜头的视频提示词 |
| `episode.json` | 后期参数（`"ir": true` 红外夜视） |

## 原文和动作链

《晋书·祖逖传》：

> （祖逖）与司空刘琨俱为司州主簿，情好绸缪，共被同寝。中夜闻荒鸡鸣，蹴琨觉曰：「此非恶声也。」因起舞。

- **中夜**：半夜，取子时。
- **蹴**：用脚踢。祖逖是一脚把刘琨踢醒的，不是推醒、叫醒。
- 动作链：鸡叫 → 祖逖坐起 → **用脚跟踢**被子里的刘琨 → 刘琨蒙头 → 祖逖掀被，把他拉起来 → 取剑、抛给刘琨 → 两人在院里练剑，刘琨先是迷迷糊糊，然后认真跟上。

## 两条镜头

| 镜头 | 动作 | 看片时核对 |
|---|---|---|
| `wj_c1`（首帧 `first_frame.png`） | 两人同被而睡，鸡扑翅打鸣 → 祖逖猛地坐起，听了听，用脚跟狠踢被里的刘琨 → 刘琨惊醒，拉被子蒙头，祖逖一把掀开 → 祖逖跳下床把他拉起来，刘琨坐在床沿揉眼 | 是用脚踢醒；一床被子；只有两个人 |
| `wj_c2`（首帧是 c1 的末帧） | 祖逖到兵器架取下两把剑，抛一把给刘琨，刘琨手忙脚乱接住 → 走到院里，祖逖练剑 → 刘琨半睡半醒地跟着比划、打哈欠 → 刘琨摇摇头站直，认真和他并排练 | 剑是从架上取的（两把）；鸡一直在篱笆上 |

## 那句台词为什么没让人说出来

原文里祖逖说了一句「此非恶声也」。这一集刻意做成**全静默**：只演踢醒、掀被、抛剑，提示词里写 `No music, no clear speech`，台词放在出处注释里。

另一种做法是把台词用引号写进 `wj_c1` 的节拍里，让祖逖说出来，出片后用 `take_gate.py --profile dialogue --lines "此非恶声也"` 核对，再在 `episode.json` 里给这条镜头加 `keep_audio`、`subs` 和 `gate`（见 [`../../README.md`](../../README.md)「台词：要么给原句，要么全静默」）。不要做的是让他「说话」却不给词，那样出来的是听不懂的伪中文。

## 屏显时间

| 镜头 | 日期 | 年号月 | s0 | 时钟 |
|---|---|---|---|---|
| wj_c1 | 0296-11-21 | 元康六年十月 | 2410 | 00:40:10 子时 |
| wj_c2 | 0296-11-21 | 元康六年十月 | 2420 | 00:40:20（接力） |

- 年份取晋惠帝元康六年（296 年）：《晋书·刘琨传》说刘琨「年二十六，为司隶从事」，两人同为司州属吏应在这前后。
- 日子没有记载，取十月中气小雪，296 年小雪按儒略历约在 11 月 21–22 日。日期为演绎，`note` 里写明了。
- 中夜取子时，00:40。

## 曾经的错误

- 年份最初写成元康元年（291 年），那时刘琨才二十一岁，对不上「年二十六，为司隶从事」。

## 复现

在仓库根目录，服务已经启动：

```bash
E=recipes/cctv/episodes/wenji
S=outputs/wenji/shots
python3 tools/h3.py submit --kind i2v --image $E/first_frame.png --prompt-file $E/prompts/wj_c1.txt \
    --secs 10 --seed 31 --out $S/wj_c1_s31.mp4 --wait
ffmpeg -sseof -0.15 -i $S/wj_c1_s31.mp4 -frames:v 1 -update 1 $S/wj_c1_last.png
python3 tools/h3.py submit --kind i2v --image $S/wj_c1_last.png --prompt-file $E/prompts/wj_c2.txt \
    --secs 10 --seed 7 --out $S/wj_c2_s7.mp4 --wait

for f in $S/wj_c1_s31.mp4 $S/wj_c2_s7.mp4; do python3 tools/take_gate.py $f; bash tools/contact_sheet.sh $f; done

python3 recipes/cctv/cctv_post.py $E/episode.json        # -> outputs/wenji/master.mp4, outputs/wenji/vertical.mp4
```

- 成片用的 seed：第一镜 31，第二镜 7。同一个 seed 在不同的显卡、驱动或 WanGP 版本上不一定出同一条，把它当起点，不满意就换 seed 再渲。
- 文件名要和 `episode.json` 里的镜头名一致（`wj_c1_s31`、`wj_c2_s7`）。
