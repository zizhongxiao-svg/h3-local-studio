# 06 配方：唯美武侠 MV

目标是两件事：**美**（人好看、光好看）和**动**（镜头里有运动，不呆）。这两件事在 H3 上互相拉扯：动作一快脸就糊，动作一少就成了会动的照片。下面是怎么同时做到。

## 美

- **景别**：以半身中景和带环境的远景为主，人物放在三分线上，留出大景。不要塞满画面的大脸特写，脸上的任何瑕疵都会被放大。
- **光**：逆光的金色轮廓光、发丝透光、丁达尔光，脸上加柔和补光保持白皙。不要套「低饱和 + 暗部偏青」的胶片调色，它会把肤色压灰。
- **柔光只上高光**：全画面加柔光会让整片发糊。只取高光部分做柔光，叠回去后再轻微锐化。这个滤镜必须在 RGB 里做；在 YUV 里做 screen 叠加会把色度通道也叠上去，整片偏紫：

  ```bash
  ffmpeg -i in.mp4 -vf "format=gbrp,split[a][b];[b]curves=all='0/0 0.62/0 1/1',gblur=sigma=18[g];[a][g]blend=all_mode=screen:all_opacity=0.5,format=yuv420p,unsharp=5:5:0.8" -c:a copy out.mp4
  ```

- **选脸**：先出 3–5 张定妆照挑脸，再用这张定妆照做参考图出每个镜头的首帧（方法见 [04-workflow.md](04-workflow.md) ②）。女主要柔美：「眼神冷、下颌分明」这类词会把她画成男相。
- **真实比例**：巨大的花瓣、雪花这类「巨物美学」看着廉价、AI 味重。尺度、材质和物理都保持真实。

## 动

- **每个镜头三件事**：一个明确的动作（甩纱、抛葫芦、旋剑、纵马）+ 一个运镜（环绕 arc、跟拍 track、升降 crane）+ 一次表情变化（低头 → 抬眼 → 笑开）。只写「微笑加深、轻飘、慢推」，出来一定是呆的。
- **两人镜头写一来一往**：他抛过去，她不看就接住，然后回眸。
- **保持条款别锁构图**：用 `identity_preserved - keep faces/hairstyles/costumes/makeup; pose, expression, camera angle and framing may change`。写 `fully_preserved ... composition` 会把姿态和运镜一起锁死，又成了会动的照片。
- **镜头动，人柔动**：露脸时身体不要做快动作（原地快转、甩袖），脸会「化」掉、五官变形，停下来才恢复。镜头推近或环绕，加上纱和头发飘动，不伤脸。最清楚的是人定住、只推镜头。
- **露脸镜头的脸要够大**：脸高至少约画高的 1/4（七分身或更近）才清楚。全身远景里的小脸会糊，几秒后五官就散了，所以远景只拍背影或剪影。
- **轻功**：不要写贴着水面滑翔（看着像神仙片），改成立定，或者点水后落地。
- **掌风、剑气**：H3 很容易让掌风长出发光的光球、护盾，要在正向描述之后明确写 no glow, no energy orbs, no magic，并检查这些帧。
- **兵器**：图像模型画剑横在脸前，常常画成玻璃；两把剑交叉会多长出刀刃。改成单人动作、手按剑柄这类细节。
- **背景被重画**：H3 有时会把首帧的背景重画（雾蓝的远山变成鲜绿的松林），这一镜在整片低饱和的色调里就跳出来了。把背景写进动作提示词（「背景始终是云海薄雾远山，低饱和」的英文版）重渲，不要靠整片调色去压，调色会把肤色一起压成死灰。
- **独臂这类残缺特征**：动作一大，大约 2 s 后模型会把缺的手长回来，写明了空袖也没用。只用前面干净的那一段。

## 剪

- **取运动最强的那一段**，不要从片头取：i2v 的第一秒是从静帧起步，最慢。
- **剪在动作上**：在动作进行中切到下一个镜头。
- **正反打和视线**：两个人的戏要有对视和反应。先定好谁在画左、谁在画右，视线方向前后一致。
- **按乐句剪**：剪辑点落在乐句上，情绪最高点对准副歌的重拍。
- **讲故事的片子不要一镜一段拼**：二十几条各自独立的 5 s i2v 拼起来，人物各自对着镜头摆姿势，没有对视、反应和台词，节奏机械。有情节的场面改用 r2v 整场生成：一场戏一次 12 s，场景图 + 定妆照做参考，`[Shot N]` 分镜，引号里的台词由角色自己说出来（见 [07-recipe-drama.md](07-recipe-drama.md)）。

## 音乐

- **有版权的歌只做内部预览。** 公开发布时用平台曲库里的音乐，在发布时加。
- 情绪片默认用一首连续的器乐曲，不要两首硬接；对白段把音乐压低，不要整段撤掉。
- 节拍过于规整的电子伴奏（标着「纯音乐」的 DJ 版）放在深情的片子里会显得滑稽，优先真人演奏的原声。
- 音乐要用耳朵挑：出几个版本，让人听了再定。

## 示例提示词（原创角色）

下面是为本文新写的 i2v 提示词，角色是原创的，**没有渲染验证过**，作为写法示例：

```
subject_definitions: A young swordswoman in a pale blue layered hanfu with a white gauze outer robe, long black hair
half tied up with a jade pin, a straight sword in a dark scabbard at her left hip, standing alone on a mossy stone
ledge in a bamboo forest at dawn; mist fills the valley behind her. She is the only person in the scene.
summary: She draws her sword halfway as a gust lifts her gauze sleeves, looks up toward the far ridge and softly
smiles, while the camera arcs around her from her side to the front.
retention_analysis: identity_preserved - keep her face, hairstyle, costume and makeup; pose, expression, camera angle
and framing may change. The bamboo forest, the mist and the dawn light stay as in the first frame: a low warm sun
behind her from the upper left, a golden rim on her hair and shoulders, soft fill light on her face, no other light
source. Real live-action footage, natural real-time speed, no slow motion. The scene stays empty of other people.
detailed_description: 0-2 s: waist-up medium shot from her left side; eyes lowered, she rests her right hand on the
sword hilt while a gust of wind lifts her gauze sleeves and loose strands of hair. 2-5 s: she draws the blade halfway
out of the scabbard in one smooth, controlled motion; the polished steel catches the low sun; the camera begins a slow
arc toward her front. 5-8 s: she lifts her eyes to the far ridge and her expression softens into a faint smile; the
arc ends on a frontal waist-up framing with her face in the upper third of the frame, the mist glowing behind her.
overall_soundscape: wind through bamboo leaves, gauze fluttering, the soft ring of the blade leaving the scabbard,
distant birds. No clear speech.
non_diegetic_music: none.
```

它对应上面的规则：半身中景、逆光金边 + 脸部柔光、封闭光源；一个动作（拔剑出鞘一半）、一个运镜（从侧面环绕到正面，写了终点）、一次表情变化（垂眼 → 抬眼 → 浅笑）；露脸时只做慢而稳的动作；`identity_preserved` 允许运镜；场景里不加人；不带配乐。
