# Google Flow Live UI Audit Checklist (Read-Only · 0 Credits)

运行 `/flow-sync` 时按以下 7 项逐一核对（全程只浏览/展开菜单，严禁触发任何生图、生视频或 4K 超分扣费）：

1. **Canonical Entry & Auth Signals**
   - URL: `https://flow.google.com/`
   - Check: Top-right profile avatar, `ULTRA`/`PRO` badge, `+ New project` / `新建项目` button, no unexpected redirect loop.
2. **Changelogs & Model Lineup**
   - Check: Recent model additions or retirements (e.g. `Veo 3.1 Fast/Lite/Quality`, `Omni 1.2 Flash`, `Nano Banana 2.1`).
3. **Composer Modes & Manual Toggle**
   - Check: Exact labels for Image mode, Video -> Frames, Video -> Ingredients, and `Flow Agent` ON/OFF toggle.
4. **Live Credit Indicator**
   - Check: Exact text pattern for pre-flight credit notice (e.g. `Generating will use <N> credits`), output multiplier (`x1`/`x2`/`x4`), duration & aspect options.
5. **Characters & Ingredients Surface**
   - Check: `/project/<id>/character` route availability, archetype options, Collections creation, and asset library tabs (`图片` / `上传的内容`).
6. **Scenes & Clip Editor Surface**
   - Check: `Scenes` tab, `/project/<id>/edit/<clipId>`, `Extend`, `Save frame`, inline edit controls, and project download button.
7. **Download & Upscale Tiers**
   - Check: Download submenu labels and credit fees (`720p`, `1080p Upscaled` free vs paid threshold, `4K Upscaled · 50 credits`).
