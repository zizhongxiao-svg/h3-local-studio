# 首帧配方（监控画面静帧）

i2v 镜头从首帧精确开始：机位、构图、人数、道具位置全由这张图决定，首帧错了，两个 seed 都会带着同一个错。所以先把首帧做对、看过，再渲视频。

## 提示词

每张首帧都以同一句「监控底句」开头，后面接 `Scene:` 写这一集的场景和人物。底句：

```text
Real security CCTV camera footage still frame, fixed camera mounted high in a corner looking down at about 40 degrees, wide-angle lens with slight barrel distortion, slightly washed-out low-contrast colors, mild digital noise, realistic photographic live-action, ancient China setting with people in authentic historical hanfu costume. No text, no timestamp, no watermark, no logo, no UI overlay.
```

夜景用红外版底句：

```text
Real security CCTV camera footage still frame in infrared night vision mode, black and white monochrome image with slight green-grey tint, fixed camera mounted high in a corner looking down at about 40 degrees, wide-angle lens with slight barrel distortion, mild digital noise, realistic photographic live-action, ancient China. No text, no timestamp, no watermark, no logo, no UI overlay.
```

完整例子见 [`episodes/smg/plate_prompt.txt`](episodes/smg/plate_prompt.txt)（白天、彩色）和 [`episodes/wenji/plate_prompt.txt`](episodes/wenji/plate_prompt.txt)（夜里、红外）。`Scene:` 部分要写清：

- **朝代和场景**：Song dynasty courtyard garden、Western Jin dynasty official residence，地面、建筑、季节、昼夜。
- **人数写死**，每个人写年龄、服装、发型、在做什么、在画面哪一侧。
- **关键道具**写明是什么（瓮不是缸、耒不是锄）、多大、在哪、归谁。
- 最后一句 `Whole scene visible, people small in frame.`：人在画面里要小，这才像监控。

## 构图规则

- 高位墙角，俯拍约 40°，广角，人物小。不要电影构图和电影光。
- **关键动作放在画面中部、中景距离。** 离镜头太远，H3 会自己推过去；离镜头太近，人只剩背影。
- **季节和屏显月份一致**：春景首帧不能配五月的时间码。
- **多次拜访型的集**（三顾茅庐这类）：做一张人物已经站在中景位置的关键帧，每一次拜访都用它当首帧（同一机位、同一批人，靠时间码跳跃出笑点）。只有人物是从画外走进来的时候，才用空场景当首帧。
- 画面里不能有任何文字、时间码和水印：时间码由 `cctv_post.py` 加。

## 用什么出图

任何能出写实照片的图像模型都可以（比如 GPT Image、即梦，或本地的 Qwen-Image）。出 16:9 横图。

- **同一机位的后续状态**（下雪了、船装满了、田荒了）不要重新出图，用图像编辑：把上一张首帧作为参考图，写「EDIT the attached image, keep the camera and the people, change only …」。这样人物的脸、服装和位置都能保住。命令行工具的参考图参数如果能接多个文件（比如 `-i a.png b.png`），提示词要写在它前面，否则会被当成文件名吞掉。
- **并行出图**时，几个会话可能共用同一个输出目录。让每个任务复制它自己生成的那个文件，而不是「最新的文件」，否则一集的首帧会变成另一集的图。每批跑完查一遍重复：

  ```bash
  md5sum frames/*.png | sort | uniq -w32 -d
  ```

- **尺寸**：样例里的首帧是图像模型出的 1672×941 原图，直接提交即可。要自己先转成 1344×768 的话，按比例缩放后裁掉左右两边（1.777 比 1.75 宽），不要裁上下，否则会补黑边：

  ```bash
  ffmpeg -i plate.png -vf "scale=-2:768,crop=1344:768" first_frame.png
  ```

## 用之前检查

把这一集的首帧排在一起看，逐张核对：

- [ ] 人数对，没有多出来的人和动物（包括后来才该出现的那只兔子）；
- [ ] 关键道具对：名称、大小、位置、在谁手里；
- [ ] 左右对：看实际的图，不要信提示词。作者遇到过一张图里人物的左右和提示词写的正好相反；
- [ ] 昼夜、季节、天气和原文、屏显月份一致；
- [ ] 关键动作的位置在画面中部、中景距离；
- [ ] 画面里没有文字、时间码、水印；
- [ ] 并行出图后跑过 md5 去重。
