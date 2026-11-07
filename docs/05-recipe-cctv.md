# 05 配方：《古代监控实录》

把历史名场面、寓言和传说（司马光砸瓮、闻鸡起舞……）重新演成一段固定机位的监控录像：高位俯拍、广角畸变、黑白或红外、屏幕上走着「公历日期 + 年号农历月 + 时辰」的时间码。笑点在「现代监控拍到了古人」，所以时间码的年代信息必须对，动作必须和原文一致。

这个格式很适合本地 H3：一集只有一个固定机位，镜头不动、人物很小，正好避开了运镜、脸部特写和多人对白这些难点；一集 2–3 个 10 s 镜头，用上一镜的末帧接下一镜。

完整配方在 [`recipes/cctv/README.md`](../recipes/cctv/README.md)：

- 三道关：原文锁定（动作链）、表演力度、一集一个固定机位、`subject_definitions` 只写开场就在的人；文字审校；看片验收；
- 时间戳规则（公历、年号、农历月、时辰，没有星期，太初改历以前的月份怎么定）；
- 已知翻车和对应写法；
- 首帧（监控空镜）怎么做：[`recipes/cctv/plate.md`](../recipes/cctv/plate.md)；
- 给另一个大模型用的审校提示词：[`recipes/cctv/review_prompt.md`](../recipes/cctv/review_prompt.md)；
- 后期脚本 `cctv_post.py`：监控质感、屏显时间码、闪烁 REC、竖屏版排版和 AI 标识；
- 两集完整样例（首帧、提示词、seed、后期参数）：[司马光砸瓮](../recipes/cctv/episodes/smg/README.md)、[闻鸡起舞](../recipes/cctv/episodes/wenji/README.md)。
