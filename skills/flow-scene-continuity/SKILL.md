---
name: flow-scene-continuity
description: >-
  Advanced Google Flow filmmaking workflow for character locking, seamless
  shot-to-shot continuity, clip extension, and inline video editing inside
  https://flow.google.com/. Activate whenever a multi-shot video needs
  dedicated Flow Characters (/character), continuous action via Extend or
  Save-frame start-frame chaining, or targeted inline video edits without
  regenerating from scratch.
---

# Google Flow 高级制片与镜头连续性指南

当多镜头视频需要**更强的角色一致性、长镜头无缝延续、镜头间动作衔接（而非生硬 8 秒硬切）**，或对已生成镜头做局部修改时，优先使用 Google Flow 站内以下高级能力（全部通过 Antigravity `browser` 子智能体操作，零额外 API 费）。

---

## 1. 专用角色建档（Characters）与素材分组（Collections）

相比单张图片参考，Flow 专用的 **Characters** 系统在多视角、大动作下角色一致性更稳：
1. 在已打开的 Flow 项目（`https://flow.google.com/project/<id>`）中，先关闭 `Flow Agent` 进入 **Manual Mode**。
2. 进入左侧或顶部 **Characters**（`/project/<id>/character`），为核心主角创建专用角色档案（支持角色原型与多角度外观锁定），或创建 **Collection** 整理场景/道具图片素材（`Nano Banana 2.1`，`x1`）。
3. 在视频创作面板选择 **`视频 → 素材 (Ingredients)`**，直接挂载已建档的 Character 与关键道具素材。

---

## 2. 镜头无缝衔接：抽尾帧（`Save frame`）与镜头延长（`Extend`）

**避免把 1 分钟视频切成 7 个彼此孤立的 8 秒碎片**，按场景需要组合使用两种连续技法：

### 技法 A：`Extend` 无缝延长（适合连续动作 / 舞蹈 / 一镜到底）
- 在 Flow 的 **Scenes** 视图或 Clip Editor（`/project/<id>/edit/<clipId>`）中选中一段效果出色的 8 秒镜头；
- 点击 **`Extend`（延长）**，输入下一段动作演变提示词（保持同一光影、舞步或运镜方向），将单镜头无缝延长至 15～24 秒，大幅提升画面连贯度与真实感。

### 技法 B：`Save frame` 尾帧接续与「先尾后首」关键帧法（适合切换景别/精准首尾帧过渡）
- **连续切镜**：对上一镜末尾满意的画面点击 **`Save frame`** 存进项目素材库；下一镜切至 **`视频 → 帧 (Frames)`** 模式，把刚存下的尾帧设为新镜头的 **`开始`（Start Frame）**，实现零跳切丝滑转场。
- **精准首尾帧（先尾后首）**：需要同时锁定首帧与尾帧时，优先**先生成信息量最满的尾帧**，再在尾帧上做局部修改退回首帧（纯推进镜头直接将首帧裁剪放大作为尾帧），可 100% 锁死机位与构图不漂移。
- **剧情长片资产三件套**：多场剧情戏优先生成 `16:9` 白底角色身份板（多视角 + 3 表情 + 鞋子比例）、场景正打/反打/全景三图，以及标明真实物理尺寸的白底道具图。

---

## 3. 在线局部修改（Inline Video Edit）

若某一镜整体动作很好，只有局部细节不满意（如衣服颜色、灯光氛围、背景杂物）：
- 在 Flow Clip Editor 中使用 **Inline Edit**，用简短明确的自然语言指令修改单一要素，并明确追加 `"Keep everything else the same."`，无需推倒重拍整镜。

---

## 4. 实测避坑规范（2026-11 实时验证，务必遵守）

### 4.1 模型生命周期与首选配置
- **首选 `Omni 1.2 Flash`**：单次直出最长 **`15 秒`**（`3–15s` 可选），`720p` 15 秒消耗约 `60 点数`，支持挂载角色参考图（`视频 → 素材`）。
- **旧模型停用提醒**：Flow 后台已标注 `Veo 3.1 - Fast`、`Veo 3.1 - Quality`、`Omni 1.1 Flash` **将于 2026 年 12 月 5 日停用**；低成本备选请改用 **`Veo 3.1 - Lite`**。
- **时长自动重置防呆**：Flow 每次提交生成后，**时长滑块会自动跳回 `8 秒`**！批量提交 `15 秒`（或 `9 秒` 收尾镜）时，必须在每次提交前显式检查并重新选中目标时长。

### 4.2 背景与光影强制覆盖法（防“每镜背景雷同”）
- 当整片只挂载 1 张锁定角色参考图（如在灰水泥舞室生成的机器人参考图）但需要跨多场景切换灯光与机位时，直接在提示词开头写死覆盖指令：
  > `matching ONLY the character design from the reference image; completely ignore the reference image's grey background and flood the scene with [目标光影/场景/特殊机位，如 blazing warm golden spotlights / straight-down God's-eye overhead circular white spotlight / neon-violet locker corridor]...`
- 实测可同时实现 **100% 角色外观锁定 + 多场景高反差电影感切换**。

### 4.3 上传真人视频 V2V 策略红线（`p=speech_edit`）
- **不要把真人舞蹈/MV `.mp4` 上传进 Flow 网页端做 V2V 换人**：Flow 网页端会对上传真人视频触发 **`p=speech_edit`（禁止编辑或生成已上传视频中人物的语音）**；即使提前用 `ffmpeg -an` 剥离全部音轨，也会因网页端缺少 `Omni 1.2 Flash` 无声开关而报 `音频生成失败`。
- **正确解法**：在本地用 `prep_v2v_segments.py` 自动抽出完整原音轨（`master_audio.m4a`）和全片分镜接触表（`work/storyboard_ref/sheet_*.jpg`），逐段视觉拆解灯光/人数/队形/机位，然后在 Flow 中**仅挂角色参考图**生成 15 秒高动态分镜，最后在 `build_video.py` 中用 `bgm.replace_audio: true` 直贴完整原音轨！

---

## 5. 下载与交付规范

- **读取实时积分**：执行生成、`Extend`、Inline Edit 或 `4K` 超分前，先核对页面显示的 `生成将消耗 <N> 个点数`（Checkpoint 模式下先向用户确认）。
- **默认画质**：下载 **`1080p 已高清重塑`**（1–10 秒免费 +0 积分，11–15 秒仅 +5 积分/镜）；仅在用户明确选择 `4k` 时点击 **`4K` 超分（+50 积分/镜）**。
- **批量防错位**：连续下载多段时必须逐个下载并记录每个 UUID 文件名对应的分镜号（如 `seg_01` → `xxx_1080p.mp4`），严禁混序。
- 下载完成后，既可直接用 Flow 的 `Scenes` 导出完整视频，也可交回 `voice-to-video` 的 `build_video.py` 做本地 1080p/4K 精剪（支持 `replace_audio: true` 直贴原音轨、可选字幕与 Contact Sheet 质检）。
