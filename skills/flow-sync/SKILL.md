---
name: flow-sync
disable-model-invocation: true
description: >-
  Manual-only, strictly read-only, zero-credit live UI audit of Google Flow
  (https://flow.google.com). Explicitly run by the user (/flow-sync) whenever
  Google Flow updates its interface, models, or download tiers, to detect UI
  drift and update this plugin's skill instructions accurately.
---

# `/flow-sync` — Google Flow 界面零积分只读巡检

> **安全铁律**：本 Skill 为 **严格只读、0 积分消耗** 巡检工具。**严禁**点击任何会消耗积分的“开始生成 / Start generation / 4K 超分”按钮。

## 执行步骤

1. 读取本技能目录下的巡检清单：[references/audit-checklist.md](./references/audit-checklist.md)。
2. 通过 Antigravity 内置 `browser` 子智能体（`Model: "flash"`）打开 `https://flow.google.com/`（如未登录则暂停请用户登录，绝不绕过）。
3. 依次以只读方式巡检清单中的 7 个核心界面：
   - 首页与登录态信号（`Account details`、`ULTRA`/`PRO`、项目列表）
   - `/changelogs` 或顶部“新功能”公告（识别新模型或下线模型）
   - 项目内创作面板的模式切换（`图片` / `视频 → 帧` / `视频 → 素材`、`Flow Agent` 开关）
   - 模型选择器与时长/数量控件（确认当前可用 Veo / Omni 模型名与默认积分提示）
   - 专用 **Characters**（`/character`）与 Collections 入口
   - **Scenes / Clip Editor**（`Extend`、`Save frame`、Inline Edit 按钮文案）
   - 已有成片的下载子菜单（确认 `720p` / `1080p` / `4K` 名称与免费/付费积分标注）
4. 将实测结果与当前插件中的 `rules/AGENTS.md`、`skills/voice-to-video/SKILL.md` 和 `skills/flow-scene-continuity/SKILL.md` 对比，列出差异清单（新增功能、文案变更、下线选项），经用户确认后自动修补插件文档。
