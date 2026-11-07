# 03 提示词指南（FastH3）

## 先记住三条

1. **描述用英文，按六段写；中文只能出现在引号台词 “…” 里。** 描述里出现中文，FastH3 会把它当字幕烧进画面，套在六段格式里也一样。
2. **按秒写动作节拍，同时写运镜和表情变化。** 只写表情或情绪，出来的是一张会动的照片。
3. **`subject_definitions` 只写第一帧里已经在画面中的人和物。** 写进去的人，模型会让他从第一帧就出现。

`tools/prompt_lint.py` 会检查第 1 条，以及缺段、片长、节拍密度；`h3.py submit` 提交前会自动跑它，有 ERROR 就拒绝提交。

## 格式说明

六段的段名固定，每段以 `段名:` 开头，顺序如下：

```
subject_definitions: ...
summary: ...
retention_analysis: ...
detailed_description: ...
overall_soundscape: ...
non_diegetic_music: ...
```

- 中文只放在台词引号里：`“…”`（推荐），`prompt_lint` 也接受 `「…」` 和 `<d>…</d>`。引号里的中文会被说出来，所以引号里只放台词本身。
- 空行随便用：服务提交时带 `multi_prompts_gen_type: "FG"`，不带的话 WanGP 会把空行当成分隔，拆成好几条任务。
- FastH3 至少要一张参考图。i2v 时服务会自动把首帧同时作为参考图，不用操心。

## 六段逐段讲

### 1. subject_definitions：开场就在画面里的人和物

- 每个人写年龄、身份、服装、发型、在画面里的位置；关键道具写清在谁手里、放在哪。
- **人数写死**，最后加一句 “Nobody else is in the courtyard.” 这类话。
- **不写后来才进场的人或物。** 模型会把这里定义的每个主体都放进开头几帧：守株待兔第二镜因为和第一镜共用了定义块，树桩边凭空多出一只兔子，笑点全没了。后进场的人只在他的节拍里写（“at 8 s a servant boy opens the cottage door”）。
- 每个镜头单独写一份，不要整集共用。
- r2v 时在这里说明每张参考图和每段声音是谁（见下文「r2v 格式」）。

### 2. summary：一两句话的动作梗概

- 只写动作和结果：谁做了什么，导致什么。
- **不要写间接引语。** “mutters that the cock has crowed”“asks whether it is a deer” 都等于让人物说一句没给词的话，模型会编出听不懂的「伪中文」。台词只写一次，加引号，放在它所在的节拍里。

### 3. retention_analysis：哪些保持不变，镜头怎么拍

- 写清哪些和首帧保持一致：场景、道具、服装、画面风格。
- 镜头行为：固定机位就把它写满（见下面的 CCTV 例子）；要运镜就别在这里锁死构图。
- 两种保持方式：
  - `fully_preserved`，或者「和首帧完全一致」一类的写法：姿态、构图、机位一起被锁住。适合固定机位的监控画面，拿去拍人物 MV 就成了会动的照片。
  - `identity_preserved - keep faces/hairstyles/costumes/makeup; pose, expression, camera angle and framing may change`：只锁身份，允许动作和运镜。人物 MV、短剧用这个。
- 常用条款：`No people other than those described appear.`、`Real-time speed, no slow motion.`、`Bodies and objects have real weight: every force has a believable reaction and every action has a visible consequence.`
- 画面文字：CCTV 样例用的是 `No writing or text appears anywhere in the picture.`；对白短剧的测试里改用正向写法 `clean live-action footage from edge to edge` 效果更好。不管哪种写法，对白镜头都可能烧字幕，每条都要看画面下三分之一。

### 4. detailed_description：按秒的动作节拍

- 格式 `0-2 s: ...`、`2-3 s: ...`，每拍写谁、做什么、用多大力、结果是什么。
- **10 s 最多 4–5 拍。** 写多了模型会合并或跳过；动作链长就拆成 2–3 个镜头。
- 每拍写到力度（见下文「动作写到力度」）。
- 运镜：一个镜头只用一个主要运镜，写清起点、速度和终点（推到哪停）。不要「推 + 环绕」「推 + 摇」同时用，也不要朝一个正在移动的人推。没写终点，模型会停在随机的位置；没写速度，它推得很快。
- 表情：一个情绪词 + 2–3 个身体细节（咬紧下颌、眼神不动、呼吸变浅），用正向写法。表情写得太极端，脸会走样，把强烈情绪放到身体、头发和环境上（风、雨、手）。
- 多镜头（r2v 一场戏）：用 `[Shot 1] (0–4 s)`、`[Shot 2] (4–7 s)` 分镜，每个镜头写景别、按秒动作和机位，**每个镜头都重写一遍人物服装和位置**（否则跨镜头会换衣服）。10–12 s 放 2–4 个镜头，每个 ≥ 2.5 s。

### 5. overall_soundscape：声音

- 写具体的声源：环境底噪、脚步、碰撞、水声、喘气。
- 没人说话的镜头写 `No clear speech`，不然模型可能自己配一段听不懂的人声。
- 引号里的台词会被说出来，这一段不要再写中文。

### 6. non_diegetic_music：配乐

写 `none.`。配乐在剪辑时加，生成时带音乐，剪辑就没法改了。

## 完整示例：《司马光砸瓮》第二镜

这是成片实际用的提示词（[`smg_c2.txt`](../recipes/cctv/episodes/smg/prompts/smg_c2.txt)，i2v，10 s，seed 31，首帧是上一镜的末帧）：

```
subject_definitions: Sima Guang, a small seven-year-old boy in a grey Song dynasty tunic with a hair bun, standing
in front of the huge big-bellied glazed ceramic water jar in the stone-paved courtyard, clutching a heavy rough rock
the size of his head. A child is trapped under the water inside the jar (not visible, only bubbles rising). Nobody
else is in the courtyard.
summary: The little boy uses all his strength to smash the heavy rock into the lower side wall of the jar. The first
blow is so hard the rock bounces out of his hands and knocks him onto his bottom, leaving a crack; he scrambles up and
strikes the same spot again, glaze chips fly, the crack spreads and thin jets of water spray out.
retention_analysis: Keep the courtyard, the jar and the boy; the jar stays standing in place exactly as in the first
frame. Fixed wall-mounted security camera, high angle, wide lens, locked off, no camera movement, nobody looks at the
camera. The camera stays completely static for the whole clip: no pan, no tilt, no zoom, no push-in, no shake, no
cuts, no change of angle; the framing, the lens distortion and the size of everything in the frame stay exactly as in
the first frame, and the people stay small in the frame. Real CCTV surveillance footage: flat dull ambient light, no
cinematic lighting, no dramatic composition. The people do not know the camera is there: they never look up at it,
never pose and never turn to face it. Real-time speed, no slow motion. Bodies and objects have real weight: every
force has a believable reaction and every action has a visible consequence. No people other than those described
appear. No writing or text appears anywhere in the picture.
detailed_description: 0-2 s: gritting his teeth, the boy steps up to the side of the jar and heaves the rock up above
his head with both arms trembling. 2-3 s: he swings it down with his whole body weight like chopping wood and slams it
into the lower side wall of the jar near its base: a loud crack, his arms jolt, the whole jar shudders and water slops
over the rim. 3-4 s: the rock rebounds out of his hands and thuds onto the stone floor; he stumbles back and falls on
his bottom. 4-5 s: a pale crack line now runs across the glaze where he hit. 5-7 s: he scrambles up, grabs the rock
again with both hands and lifts it above his head, panting. 7-8 s: he lunges forward and smashes it into the same
cracked spot with all his strength: chips of glaze and ceramic fly off. 8-10 s: the crack spreads into a web and
several thin jets of water spray out of the cracks onto the ground; he staggers and raises the rock again.
overall_soundscape: thin tinny surveillance microphone ambience, faint background hiss, a heavy dull thud and a loud
crack of ceramic, water slopping, the boy panting. No music, no clear speech, no subtitles, no on-screen text.
non_diegetic_music: none.
```

逐段看它做了什么：

- **subject_definitions**：只有司马光一个人在画面里，手里已经抱着石头（接上一镜的结尾）。瓮里的孩子写成「看不见，只有气泡」，最后一句 `Nobody else is in the courtyard.` 把人数写死。
- **summary**：动词落到具体部位：砸的是「瓮侧壁下部」（lower side wall），不是笼统的 smash the vat。第一版写得含糊，模型把石头扔进了瓮里，整只瓮炸开，和《宋史》「持石击瓮破之」不符。
- **retention_analysis**：先说「瓮一直立着」，堵住「整只炸开」的默认物理；再把固定机位写满（不摇、不推、不切、构图和人物大小不变）；最后是监控质感、人不看镜头、真实速度和重量、不加人、无文字。
- **detailed_description**：一次撞击拆成蓄力（举过头顶、手臂发抖）→ 接触（全身重量砸下、一声脆响）→ 反作用（石头弹出、人摔坐在地）→ 可见后果（釉面出现裂纹）→ 再来一次。这一镜有 7 拍，超过「10 s 最多 4–5 拍」的建议，`prompt_lint` 会报 WARN。成片用的就是这一版，留着当对照：动作链一长就容易贴着上限，看片时要逐帧核对每一环。
- **overall_soundscape**：只写声音，并明确 `no clear speech`。
- **non_diegetic_music**：none。

## 动作写到力度

H3 默认把所有接触都演得很轻，像「轻轻磕碰」。每个关键动作按这个顺序写：

**蓄力 → 接触 → 反作用 → 可见后果 → 身体反应**

- 司马光：双手把石头举过头顶、手臂发抖 → 像劈柴一样用全身重量砸下 → 一声脆响、瓮一震、水泼出来 → 石头弹飞、人摔坐在地 → 出现裂纹 → 爬起来再砸。
- 小孩抱头那么大的石头要显得吃力：膝盖发软、踉跄、要砸好几下，前几下砸不开。
- 旁观者的反应要给一拍：先愣住约 2 s，再跑。
- 动词要具体到「打在哪、什么保持完好、结果在哪里出现」。破坏类动词默认会演成爆炸：写明什么不坏、破口在哪。
- 两个人之间的接触按轻重分：从对方手里拿走东西、抓住手腕这类轻、中度接触能演出来；推搡、扇耳光、打斗这类重接触演不出力道，改成「意图 → 切 → 结果」，力度交给音效。

## 人数和道具归属

- 人数写死，并加 `No people other than those described appear.`。模型会多加人：三顾茅庐里冒出过第四个跟着走的孩子。
- 每件道具写明属于谁，其他人写 `hands empty`。羽扇跑到过关羽手里。
- 空镜（只拍物件、空景、碑文）最容易凭空走进人来：写正向的 `the scene stays empty of people: only X, Y, Z`，一次出两个 seed，挑干净的那条。

## 以正向描述为主

- **写「不在画面里的某人」反而会把他招来。** 「X is NOT in this frame」在 5 张图里画出了 5 次 X。只写画面里有什么（空地板、那扇门）。
- 「does NOT smile」单独写，人物照样笑。先写正向状态（冷笑、咬牙、眼神冰冷、下颌绷紧），需要时再在后面补一句短禁令。
- 例外：模型的默认行为就是错的时候，在正向描述后面加一句短禁令。比如武侠里掌风会长出光球，要明确写 no glow, no energy orbs；不能笑的反应镜头，写完微表情之后加 no smile, no grin。

## 对白怎么写

- 台词原文用引号写在它所在的节拍里，并写明谁说、用哪个声音、什么情绪：`he says in Mandarin Chinese, with the voice of <Audio 1>, cold and controlled: “……”`。
- **导演表演，不要掐秒表。** 给每句台词标时间点（“At about 0.3 s … finishes by 5.3 s”）、写语速、写「慢一点、每个字都清楚」，人物会变成念稿。写人物想要什么、身体在做什么、在哪里换气；台词按口语写，停顿用标点表示。只有分镜边界带时间。
- 长度：普通话约每秒 4 个字。10 s 的镜头放 2–3 句。按内容定长度，不超过 12 s。
- **不要写中文括号注释**（比如「（冷笑）」），模型会把它念出来。引号里只放台词。
- 要强调的关键词也不能用中文写在引号外，用英文描述，比如 “the word for fourteen”。容易被听错的词，在台词里给它加一点铺垫，再用英文写一句 “the key word clear and a little drawn out”。
- 停顿用逗号或「……」。「——」在《古代监控实录》里和烧字幕一起出现过，能不用就不用。
- 镜头里没人说话，就只写手势（指、摇头、挥手），加 `everyone stays silent, nobody talks`。让人「说话」却不给台词，出来的是听不懂的伪中文。
- 说话的人不要直视镜头：`three-quarter profile, eyes looking off-screen left at <partner>, never looks into the camera lens`。不想让模型在台词中途切到正面反打，再加一句 `one continuous shot, no cut`。
- 提前堵住常见的嘴部问题：`closed or tight lips between words, no teeth bared, no puckered lips`。
- 另外两个常见偏差也要写明：干涸的血会被演成鲜血，写 `dried dark blood stays dried`；只要一次的动作会被重复，写 `the gesture happens exactly once`。

## r2v 格式（参考图 + 声音）

r2v 用于对白和一整场戏：首帧 + 人物参考图 + 每个说话角色的声音参考。和 `h3.py` 参数的对应关系：

| 提示词里 | `h3.py submit` 参数 |
|---|---|
| `<Picture 1>`：首帧，也是构图锚点，镜头从它开始 | `--image first.png` |
| `<Picture 2>`、`<Picture 3>` …：定妆参考图，按顺序 | `--refs cast_a.png,cast_b.png` |
| `<Audio 1>` … `<Audio 3>`：声音参考，最多 3 段，每段约 5 s | `--auds a.wav,b.wav` |

- 定妆参考图要在这场戏的房间和光线里拍，服装和首帧一致。用摄影棚背景的定妆照，人物单独出镜时会把棚拍背景带进画面。
- 声音参考用这个角色自己「试镜」出来的台词：先不给声音参考，按角色写一场戏，出两个 seed，挑一条，把那句台词剪成 5 s 左右当他整季的声音参考。朗读语料或 TTS 做的参考会把「念稿腔」一起带进每条镜头。
- 一段里最多两个说话人，主要说话人放 `<Audio 1>`。说话人数不等于画面人数：听的人可以留在画面里（背影、侧脸、闭着嘴）。

下面是按作者的对白短剧写法整理的模板，人物是为本文新写的，**没有在本仓库里原样渲染验证过**：

```
subject_definitions: <Picture 1> is the first frame: a small office at night, a desk lamp on the left, cold blue
window light on the right. <Picture 2> is Lin, a woman in her thirties, dark grey blazer, hair in a low bun, a small
mole under her left eye. <Picture 3> is Zhou, a man in his forties, white shirt with a loosened tie, short greying
hair. <Audio 1> is the voice timbre anchor for Lin: every word Lin speaks uses exactly this voice. <Audio 2> is the
voice timbre anchor for Zhou: every word Zhou speaks uses exactly this voice. Lin stands at the desk, Zhou sits
behind it. Nobody else is in the room.
summary: Lin confronts Zhou about the missing contract; he deflects; she slides a photo across the desk and he goes
quiet.
retention_analysis: identity_preserved - keep faces/hairstyles/costumes/makeup of <Picture 2> and <Picture 3>; pose,
expression, camera angle and framing may change. The room and its light stay as in <Picture 1>: the desk lamp and the
cold window light, no other source. Natural real-time speed, no slow motion. Clean live-action footage from edge to
edge.
detailed_description: Brisk editing: each shot lasts only as long as its action. [Shot 1] (0–4 s) over-the-shoulder
from behind Zhou onto Lin in her dark grey blazer, hair in a low bun: she leans forward, palms flat on the desk, eyes
fixed on him, jaw set, and says in Mandarin Chinese with the voice of <Audio 1>, cold and controlled:
“合同昨天还在你桌上。” [Shot 2] (4–7 s) medium close-up of Zhou in his white shirt and loosened tie, three-quarter
profile, eyes looking off-screen left at Lin, never looks into the camera lens: he swallows, glances down and says
with the voice of <Audio 2>, evasive: “我不知道你在说什么。” [Shot 3] (7–10 s) side two-shot, Lin still in her dark
grey blazer standing, Zhou seated: she slides a photo across the desk; he looks down at it, his hand stops halfway to
his cup, lips pressed tight.
overall_soundscape: quiet office room tone, distant traffic, the photo sliding on wood.
non_diegetic_music: none.
```

提交：

```bash
python3 tools/h3.py submit --kind r2v --image office_first.png --refs lin_cast.png,zhou_cast.png \
    --auds lin_5s.wav,zhou_5s.wav --prompt-file seg01.txt --secs 10 --out outputs/ep01/seg01_a.mp4
```

## 常见翻车和对应写法

| 现象 | 写法 |
|---|---|
| 画面里烧出中文字幕 | 描述全英文，中文只在引号里；对白镜头逐条看画面下三分之一 |
| 会动的照片、人几乎不动 | 按秒写动作 + 一个运镜 + 一次表情变化；MV 不要用 fully_preserved |
| 机位自己推近 | 把固定机位写满；关键动作放在画面中部、中景距离 |
| 多出一个人 | 人数写死 + `No people other than those described appear.` |
| 后来才该出现的人一开场就在 | 只在他的节拍里写，不进 subject_definitions |
| 道具换手 | 写明每件道具属于谁，其他人 `hands empty` |
| 冒出听不懂的伪中文 | 给出带引号的原句，或只写手势 + `everyone stays silent` |
| 碰撞轻飘飘 | 蓄力 → 接触 → 反作用 → 可见后果 → 身体反应 |
| 台词念得像读稿 | 不标时间点和语速，写情绪、意图、身体和呼吸 |

更多案例见 [08-lessons.md](08-lessons.md)。
