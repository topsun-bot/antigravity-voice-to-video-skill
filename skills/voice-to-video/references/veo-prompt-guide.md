# Veo 3.1 & Gemini Omni 1.2 Flash 导演提示词指南

写好动态视频提示词的核心是**让画面自己讲故事、让声音与动作同步发生**，而不是套用千篇一律的“科幻蓝光 + 旁白解说”。

## 1. 选对模型档位
- **`Veo 3.1 - Fast`**（Ultra 10 积分/8s 镜）：日常主力，动态自然、物理运动稳、原生声景好。
- **`Veo 3.1 - Quality`**（100 积分/8s 镜）：仅用于全片最关键的 1～2 个封面级开场或大特写。
- **`Omni 1.2 Flash`**（按秒计，3s–15s）：适合需要更长单镜（10–15s）、精准时间轴卡点（`[0-5s] ... [5-10s] ...`）或多图/视频参考编辑。

## 2. 电影级提示词 5 要素公式
```text
[景别与机位运动] + [主体精确动作与微表情] + [真实物理环境与材质光影] + [原生声音设计] + [镜头约束]
```
- **景别与机位**：明确写实机位语言（如 `handheld 28mm street tracking shot`、`low-angle Steadicam orbit`、`locked-off documentary tripod`、`whip-pan transition`），避免所有镜头全是“slow dolly-in”。
- **具体物理动作**：用可观察的连续动作动词（如 `plants left heel, pivots 180 degrees, drops into a sharp floor freeze, dust lifting off concrete`），少用空泛形容词（`amazing`, `epic`, `cool`）。
- **真实光线与质感**：按题材选风格——写实纪录片用自然窗光/阴天漫射/街头钠灯；商业片用柔和柔光箱；实景舞蹈用木地板排练厅镜面/街头夕阳/地下停车场自然光，**不要所有题材都加霓虹赛博雾**。
- **原生声景（纯净成片极关键）**：明确写出想要的原生声音，例如：
  - 舞蹈：`Sound design: punchy live hip-hop drum break, sneakers squeaking sharply on hardwood floor, crisp mechanical servo whirs on beat drops. No voiceover.`
  - 生活故事：`Sound design: gentle morning birdsong outside the window, soft water pouring into ceramic soil, quiet natural room tone. No dialogue.`
- **镜头约束**：单镜头保持连贯时写 `Single continuous unbroken shot, no scene cuts, no text, no watermarks.`

## 3. 多镜头连续性铁律
- 不要写 7 个互不相干的镜头！优先规划：
  - **2～3 组长连续动作**（用 Flow `Extend` 延长，或 `Save frame` 尾帧接下一镜起始帧）；
  - 同一场景内通过**切换景别与机位角度**（全景定场 → 侧跟中景 → 脚部/手部动作特写 → 反打反应镜头）营造真正的剪辑节奏感。
