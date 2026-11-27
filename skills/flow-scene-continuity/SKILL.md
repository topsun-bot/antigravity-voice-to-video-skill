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

### 技法 B：`Save frame` 尾帧接续（适合切换景别/运镜但保持时空连贯）
- 对上一镜末尾满意的画面点击 **`Save frame`** 存进项目素材库；
- 下一镜切至 **`视频 → 帧 (Frames)`** 模式，把刚存下的尾帧设为新镜头的 **`开始`（Start Frame）**，再输入新的动作与运镜提示词（如切特写、环绕拉远），实现零跳切丝滑转场。

---

## 3. 在线局部修改（Inline Video Edit）

若某一镜整体动作很好，只有局部细节不满意（如衣服颜色、灯光氛围、背景杂物）：
- 在 Flow Clip Editor 中使用 **Inline Edit**，用简短明确的自然语言指令修改单一要素，并明确追加 `"Keep everything else the same."`，无需推倒重拍整镜。

---

## 4. 下载与交付规范

- **读取实时积分**：执行 `Extend`、Inline Edit 或 `4K` 超分前，先核对页面显示的 `Generating will use <N> credits`（Checkpoint 模式下先向用户确认）。
- **默认画质**：下载 **`1080p` 超分版（Ultra 1～10 秒免费，+0 积分）**；仅在用户明确选择 `4k` 时点击 **`4K` 超分（+50 积分/镜）**。
- 下载完成后，既可直接用 Flow 的 `Scenes` 导出完整视频，也可交回 `voice-to-video` 的 `build_video.py` 做本地 1080p/4K 精剪（按需加 BGM、可选字幕或 Contact Sheet 质检）。
