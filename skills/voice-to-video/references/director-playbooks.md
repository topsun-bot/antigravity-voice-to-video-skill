# 反模板化导演手册（全题材通用 · Anti-Template Director Playbooks）

本手册用于根治 AI 视频常见的“千片一面、幻灯片硬拼、廉价赛博塑料味”问题。每次开拍前先定题材与方向，再选对应的拍摄与剪辑语法。

---

## 一、开拍前「10 秒导演定调卡」（宽泛需求必做）

当用户只给了一句宽泛主题（如“帮我做个机器人跳舞的 1 分钟视频”“做一个公司未来愿景片”），且**没有提供明确脚本、分镜或 PPT** 时：
- **严禁** Agent 自己拍脑袋套用“暗舞台 + 霓虹雾 + 播音旁白”的旧模板。
- 在开始生成任何画面前，用一次 `ask_question` 把 **「视觉方向 3 选 1（风格反差极大）」** 与 **「导出清晰度 1080p / 4K」** 合并问清：
  - 示例（以“机器人跳舞”为例）：
    1. **写实街头/实景纪录风**：傍晚城市广场/水泥篮球场，工业感人形机器人和真人舞者即兴斗舞，手持跟拍 + 路人围观喝彩；
    2. **木地板排练室一镜到底风**：阳光透进来的镜面舞蹈室，用 Flow `Extend` 延长出 16–24 秒连贯编舞长镜头 + 真实鞋底摩擦与音箱鼓点；
    3. **高燃多机位广告快剪风**：多机位拍摄（低仰拍、脚部步伐特写、手部细节）+ 非线性 1.5s–3.5s 交叉剪辑与统一连贯 BGM。
- *跳过条件*：若用户已提供完整脚本、PPT/PDF 或已明确指定了拍摄风格，则跳过方向题，仅在未提画质时确认 `1080p` / `4k`。

---

## 二、4 大通用题材拍摄与剪辑语法（Genre Playbooks）

不同题材必须使用完全不同的叙事、声景与剪辑节奏，严禁混套：

### 1. 剧情 / 生活微电影（Narrative / Slice-of-Life）
- **声画策略**：默认 **无 AI 旁白、无字幕、无章节角标**；靠环境原声、自然动作和情绪反应讲故事（`keep_audio: true`）。
- **连续性技法**：优先用 Flow 专用 **Characters** + **`Save frame` 尾帧接续** + 经典电影正反打（全景定场 → 中景互动 → 表情特写）。
- **剪辑节奏**：3.5s–7s 舒缓电影节奏，关键情绪转场可用 `transition: "dissolve"`（0.4s 叠化）与 `acrossfade` 消除切镜声音断层。

### 2. 写实真机 / 工业产品纪录（Realistic Product / Hardware Demo）
- **声画策略**：真实自然光实景（车间、办公室、客厅、户外街道），保留真实机械运转声与环境底噪；不加花哨文字包装。
- **镜头语言**：交替使用 **固定纪录片机位（locked-off tripod）**、**手持呼吸感跟拍（handheld 28mm）** 与 **85mm 局部细节微距**（关节、抓握、纹理微瑕疵）。
- **剪辑节奏**：用 `build_video.py` 的**多片段素材复用**做 A/B-roll 交切（同一段 8s 演示素材拆成 `2.5s 全景 → 1.8s 手部特写 → 3.0s 切回全景`）。

### 3. 节奏表演 / 动作 / 创意短片 / MV（Performance / Action / Montage）
- **声画策略**：**绝对不加播音腔解说、不加章节角标、不强塞黑底文字片尾**；优先用一段完整连续的 BGM 或 Flow 连续延长镜头，避免每 8 秒音乐断层。
- **镜头语言**：结合 **Flow `Extend`（15–24s 连续完整动作）** 与 **多机位短切（1.5s–3.5s）**，大景别、低仰拍、细节特写高频交替。

### 4. PPT 汇报 / 商业演讲 / 知识科普（Deck / Explainer / Keynote）
- **声画策略**：**只有这一类题材**才按需建议开启免费中文 AI 配音（`tts.enabled: true`）、底部圆角字幕条（`subtitles.enabled: true`）以及可选的左上角章节角标与片尾总结卡。
- **镜头语言**：数据/架构页可直接展示高清 PPT 原页（轻推镜头），概念/愿景页穿插 Google Flow 真·动态视频。

---

## 三、反 AI 塑料味黑名单（Anti-Cliché Guard）

除非用户明确要求赛博朋克/科幻虚空概念风，否则编写 Prompt 时**严格遵守以下禁令与多样性规则**：

1. **禁止高频 AI 廉价套路词**：
   - 禁用：`neon cyan and magenta lighting`、`glowing cyan chest ring`、`volumetric neon fog`、`dark glossy void stage`、`floating holographic HUD circles`（除非剧本明确写到全息界面）。
   - 改用真实世界光源与材质：`overcast afternoon daylight`、`warm tungsten practical lamps`、`scuffed hardwood floor`、`brushed anodized aluminum with slight wear`、`dusty concrete plaza`。
2. **禁止运镜单调重复**：
   - **严禁连续 3 个镜头都使用 `slow dolly-in` / `smooth push-in`**！
   - 相邻镜头必须在以下 3 项中至少变换 2 项：
     - **景别**：大远景（Extreme Wide） / 中景（Medium） / 特写（Close-Up） / 局部细节（Insert Detail）
     - **机位高度**：低仰拍（Low-angle） / 平视（Eye-level） / 俯拍（High-angle / Overhead）
     - **运动方式**：固定机位（Locked-off tripod） / 手持跟拍（Handheld tracking） / 横移（Lateral glide） / 环绕（Orbit） / 甩镜（Whip-pan）
3. **打破固定 8 秒一镜**：
   - 善用 `build_video.py` 的 `visual.start` + `duration`（或 `visual.end`）对同一段 8 秒/16 秒素材截取不同时间片交叉剪辑，让全片有快有慢、张弛有度。
