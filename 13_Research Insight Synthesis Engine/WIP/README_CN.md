# WIP

| 文件夹 | 说明 |
|--------|------|
| **AI-UX-Research-/** | 当前 PoC 基线（`AI_Research_Copilot_v0`：Interview Intelligence + 高保真 Demo） |
| **Archive/ux-research-studio/** | 旧版九模块研究规划工作台；依赖已迁移的 `.cursor/skills`，当前不作为 Research Agent 入口 |
| **Data Resource/** | PoC 阶段的数据与参考素材；仅允许存放已脱敏内容 |

定稿文档在 `../00_Project_Docs/`。

## 怎么跑

macOS 推荐直接双击：

`启动 Research Agent.command`

该入口会启动 `AI-UX-Research-/AI_Research_Copilot_v0` 并打开多访谈 Agent 页面。

也可以使用终端：

```bash
cd WIP/AI-UX-Research-/AI_Research_Copilot_v0
PYTHONPATH=src python3 -m ai_ux_core.web
```

浏览器打开：http://127.0.0.1:8000/agent.html

详情见 `AI-UX-Research-/AI_Research_Copilot_v0/README.md`。

## 当前目录规则

- 尚未验证的产品代码、实验、数据和启动入口放在 `WIP/`。
- 产品战略、PRD、决策和周计划保留在 `00_Project_Docs/`，不作为 PoC 代码归入 WIP。
- 已确认的正式交付进入 `Final Delivery/`。
- `Archive/` 内容只用于追溯，不代表当前可用能力。
