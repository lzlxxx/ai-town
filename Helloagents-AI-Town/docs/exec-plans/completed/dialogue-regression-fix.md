# 对话显示与好感度回归修复

## 目标
恢复对话文本、输入框和好感度显示，并修复独立好感度分析配置。

## 验收
- 对话文本区域有正高度并随窗口伸缩。
- 输入框占据剩余宽度，发送/关闭按钮可见。
- `/chat` 返回当前好感度，客户端显示在摘要中。
- 独立分析使用可用模型，Markdown JSON 可解析。

## 验证
- `python3 -m py_compile backend/agents.py backend/relationship_manager.py backend/main.py backend/models.py`
- `godot --headless --path helloagents-ai-town --editor --quit`
