# Antigravity Voice-to-Video & Google Flow Operating Rules (v3.3)

本规则在启用 `antigravity-voice-to-video-skill` 插件（或进入工作区）时始终生效。

## 1. 纯净成片默认原则与反模板化铁律（极重要）

- **默认输出纯净动态电影画面，绝不强行套模板包装**：
  - **AI 中文配音（`tts.enabled`）**：默认 **关闭 (`false`)**；默认保留 **Omni 1.2 Flash** / Veo 原生生成的现场音效、音乐或对白（`keep_audio: true`），或在复刻参考视频/MV 时使用 `bgm.replace_audio: true` 直贴完整原音轨。仅在用户明确需要解说旁白（如 PPT 演讲汇报、知识科普、旁白故事）时才启用 `edge-tts` 或原声克隆。
  - **中文字幕条（`subtitles.enabled`）**：默认 **关闭 (`false`)**；仅在用户明确需要字幕或开启解说旁白时启用。
  - **左上角磨砂章节角标（`chapter`）**：默认 **关闭 (`""`)**；仅在多章节汇报/PPT 解说且用户希望分段提示时启用。
  - **深色文字片尾卡（`outro_card`）**：默认 **按需可选**，不要给纯创意片、舞蹈片强行拼接黑底大字片尾。
- **开拍前「10 秒导演定调卡」+ 清晰度二选一（已取消 2K 导出）**：
  - 若用户只给了宽泛主题（无明确脚本、参考视频或 PPT），开始生成前必须用一次 `ask_question` 同时确认：
    1. **视觉方向 3 选 1**（给出 3 个反差极大的真实导演方向，杜绝 Agent 盲猜套用旧模板）；
    2. **导出清晰度二选一**：**`1080p`（推荐，默认，1–10s 免费超分 / 11–15s 仅 +5 积分）** / **`4k`（3840×2160，Flow Ultra 专属 4K 超分 +50 积分/镜）**。
  - 若用户已提供明确脚本、本地参考视频或 PPT，则跳过方向题，仅在未指定画质时确认 `1080p` / `4k`。
- **反 AI 塑料味与参考图背景覆盖约束**：
  - 未要求赛博风时禁用青紫霓虹雾、虚空黑地板、发光胸环；严禁连续 3 镜使用相同景别或相同运镜（如全是 `slow dolly-in`）；人物构图优先黄金分割 `38% / 62%` 线，剧情群演必须写“错峰先后反应”（齐舞 MV 除外）。
  - 跨多场景复用同一张锁定角色参考图时，必须在提示词中显式声明 **主体锁定 + 背景/光影覆盖**（如 `"matching ONLY the character design from the reference image; completely ignore the reference image's grey background and flood the scene with [target color/location/camera]"`），防止每镜克隆同一灰底背景。
  - **提交前独立只读审核 + 切点 `±3 帧` 质检 + 能剪不重抽**：多镜头项目（`>=4` 镜）提交生视频前优先拉起独立只读 `research` 子智能体审核 `script.json`（防确认偏差与版权/穿帮词）；合片后必查 `contact_sheet.jpg` 与 `cuts_qc.jpg`（切点 `±3 帧`）；单镜首尾瑕疵先用 `start`/`duration` 裁剪修复，最后才重抽并保留旧版。
  - 善用非线性短片段复用、**Omni 1.2 Flash 15 秒长镜头**、Flow `Extend` 与平滑转场（`dissolve` / `acrossfade`）打破“每 8 秒硬切一页”的幻灯片感。

## 2. Google Flow 浏览器操控、模型生命周期与实测避坑红线

- **首选模型（已适配 2026-12-05 旧模型下线）**：
  - Google Flow 上的 `Veo 3.1 - Fast`、`Veo 3.1 - Quality`、`Omni 1.1 Flash` 将于 **2026 年 12 月 5 日停用**。
  - 新项目默认优先选用 **`Omni 1.2 Flash`**（支持 `3–15 秒` 单次长镜头，`720p` 15 秒 60 点数，1080p 重塑仅 +5 点数；`<=10 秒` 1080p 重塑免费）或低成本备选 **`Veo 3.1 - Lite`**。
- **时长自动重置防呆（必查）**：Flow 网页端每次提交生成后，**时长滑块会自动重置回 `8 秒`**。浏览器子智能体每次提交 `15 秒`（或 `9 秒` 等非 8 秒片段）前，**必须逐镜核对并重设目标时长**，严禁漏设！
- **禁止上传真人视频走 Flow 网页端 V2V 换人（实测硬边界）**：
  - Google Flow 网页端对上传的真人视频强执行 **`p=speech_edit`** 政策拦截（即便提前用 `ffmpeg -an` 剥离音轨，网页端也会因缺乏“生成无声视频”开关而报 `音频生成失败` 或 `p=speech_edit`）。
  - 遇到参考视频/舞蹈 MV 改编需求时，**不要浪费时间上传真人 `.mp4` 进 Flow**：直接本地运行 `prep_v2v_segments.py` 拆解全片分镜接触表 + 提取 `master_audio.m4a` 原音轨 → 在 Flow 内**仅挂载角色参考图**用 `Omni 1.2 Flash` 生成 15 秒高动态分镜长镜头 → `build_video.py` 用 `bgm.replace_audio: true` 直贴完整原音轨！
- **入口 URL 与会话复用**：始终直接打开 **`https://flow.google.com/`**（避免走旧跳转链导致多余 SSO 登录拦截），通过 Antigravity 内置 `browser` 子智能体（`Model: "flash"`）操作，并用 `send_message` 复用同一已登录标签页，不要在步骤之间销毁空闲子智能体。
- **语义化定位**：向浏览器子智能体下达语义目标（可见按钮文字、视觉状态），避免硬编码脆弱 CSS 选择器。
- **登录态快检（Fast-Path Auth Check）**：
  - 结合首屏 DOM（右上角 `Account details` 头像、`ULTRA`/`PRO` 徽章、`+ New project` / `新建项目` 按钮、无 `Sign in` 按钮）+ URL 停留在 `https://flow.google.com/` + 前端接口 `batchexecute` 返回 HTTP `200` 三重信号秒判已登录，直接跳过登录提示。
  - **沙箱禁令**：严禁通过 `page.evaluate` 读取 `document.cookie`、`localStorage` 或 `sessionStorage`。
- **关闭 Flow Agent 进入手动模式**：在 Flow 创作面板关闭自动改词的 `Flow Agent` 开关（切至 Manual Mode），确保我们的精准导演提示词不被篡改。

## 3. 实时积分读取与双自治模式（Checkpoint vs. Full-Auto）

- **读取页面实时积分**：在 Flow 中配好参数后，优先直接读取页面实时显示的 **`Generating will use <N> credits`**（或中文扣分提示），而不是仅靠静态估算。
- **`checkpoint` 模式（默认）**：自动完成分镜策划、项目建档、参数配置与实时积分读取后，暂停向用户汇报真实扣分并等待确认再点击生成或 `4K` 超分。
- **`auto` 模式（全自动）**：当用户指令中出现“全自动 / auto mode / full-auto / 不用问直接做 / 一气呵成”等表达时自动开启，一气呵成跑完角色建档、批量生视频、下载与合片（中途也可随时切换）。

## 4. 不可逾越的安全边界（两种模式均生效）

遇到以下场景必须立即暂停并交由用户在浏览器面板亲自完成，**严禁绕过**：
- **Google 账号登录 / 认证页**（`accounts.google.com`）
- **人机验证码（CAPTCHA）**
- **积分耗尽或付费结算页（`PAYMENT_REQUIRED`）**
