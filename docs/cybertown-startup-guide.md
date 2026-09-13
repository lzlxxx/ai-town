# CyberTown 赛博小镇启动与使用指南

本文档是当前本机环境的最终启动说明，适用于项目：

```bash
/Users/brianye/PycharmProjects/AI-town
```

## 1. 已确认的环境

当前已经配置并验证通过：

- Python 虚拟环境：`.venv311`
- Python 版本：`3.11.15`
- 后端依赖：已安装
- 向量数据库：Qdrant Docker 容器 `ai-town-qdrant`
- Qdrant 地址：`http://127.0.0.1:6333`
- Qdrant 集合：`ai_town_local`
- 本地 embedding 模型：`sentence-transformers/all-MiniLM-L6-v2`
- Godot：`/Applications/Godot.app`

当前不需要额外配置：

- MySQL
- Redis
- RabbitMQ
- Elasticsearch
- Neo4j

项目的记忆存储方式：

- SQLite：保存记忆原文，路径为 `Helloagents-AI-Town/backend/memory_data/<NPC>/memory.db`
- Qdrant：保存长期记忆向量索引，用于语义检索
- 本地 embedding 模型：把文本转成向量

## 2. 首次配置 LLM 中转站

进入后端目录：

```bash
cd /Users/brianye/PycharmProjects/AI-town/Helloagents-AI-Town/backend
```

复制配置模板：

```bash
cp .env.example .env
```

编辑 `.env`，填写你的第三方中转站配置：

```env
LLM_API_KEY=你的中转站key
LLM_BASE_URL=https://你的中转站地址/v1
LLM_MODEL_ID=你的模型名
LLM_TIMEOUT=60
LLM_MAX_RETRIES=0
LLM_AFFINITY_ENABLED=true
LLM_AFFINITY_API_KEY=
LLM_AFFINITY_BASE_URL=
LLM_AFFINITY_MODEL_ID=
LLM_AFFINITY_TIMEOUT=8
LLM_AFFINITY_MAX_RETRIES=0
LLM_AFFINITY_FALLBACK_TO_MAIN=true

EMBED_MODEL_TYPE=local
QDRANT_URL=http://127.0.0.1:6333
QDRANT_COLLECTION=ai_town_local
```

也支持 OpenAI 兼容变量名：

```env
OPENAI_API_KEY=你的中转站key
OPENAI_BASE_URL=https://你的中转站地址/v1
OPENAI_MODEL=你的模型名

EMBED_MODEL_TYPE=local
QDRANT_URL=http://127.0.0.1:6333
QDRANT_COLLECTION=ai_town_local
```

注意：

- `LLM_BASE_URL` / `OPENAI_BASE_URL` 一般填写到 `/v1`
- 不要填写完整的 `/chat/completions`
- 当前代码会自动读取 `backend/.env`
- 当前代码也会自动把误填的 `/chat/completions` 后缀截成 `/v1`
- `LLM_AFFINITY_TIMEOUT` 只控制好感度分析的等待时间，超时会降级为好感度不变化
- `LLM_AFFINITY_API_KEY` / `LLM_AFFINITY_BASE_URL` / `LLM_AFFINITY_MODEL_ID` 可单独配置好感度分析模型；留空时复用主 `LLM_*`
- `LLM_AFFINITY_FALLBACK_TO_MAIN=true` 表示独立好感度模型失败时，会用主对话模型按同样超时时间兜底一次
- 如果只是本地测试对话，可以设置 `LLM_AFFINITY_ENABLED=false` 关闭好感度分析的额外 LLM 调用
- 不要把真实 Key 提交到仓库、截图或发给别人

## 3. 日常启动后端

进入项目根目录：

```bash
cd /Users/brianye/PycharmProjects/AI-town
```

启动 Qdrant：

```bash
docker start ai-town-qdrant
```

激活 Python 环境：

```bash
source .venv311/bin/activate
```

进入后端目录：

```bash
cd Helloagents-AI-Town/backend
```

启动后端：

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

启动成功后，浏览器打开：

```text
http://localhost:8000/docs
```

## 4. 验证后端

新开一个终端执行：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/npcs
curl http://127.0.0.1:8000/npcs/status
```

期望结果：

- `/health` 返回 `healthy`
- `/npcs` 返回张三、李四、王五，并且 `available` 为 `true`
- `/npcs/status` 返回三个 NPC 的背景状态文本

测试对话：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"npc_name":"张三","message":"你好，你在做什么？"}'
```

如果中转站配置正确，应返回 NPC 正常回复。

任务系统接口验证：

```bash
curl http://127.0.0.1:8000/tasks
curl -X PUT "http://127.0.0.1:8000/npcs/张三/affinity?affinity=60"
curl -X POST http://127.0.0.1:8000/tasks/zhang_debug_code/accept
```

任务状态说明：

- `locked`：对应 NPC 好感度未达到 60
- `available`：已解锁，可以接受
- `active`：已接受，需要通过 NPC 对话完成
- `completed`：已完成，后端已发放好感度奖励并写入 NPC 长期记忆

当前第一版任务系统是后端内存态，重启后端后任务接受/完成状态会重置；NPC 对话记忆仍会写入 SQLite/Qdrant。

如果返回类似：

```text
LLM调用失败
```

说明后端、记忆和接口链路已经跑通，但 LLM 中转站的 Key、Base URL、模型名或额度存在问题。

## 5. 启动 Godot 客户端

打开 Godot：

```bash
open /Applications/Godot.app
```

导入项目文件：

```text
/Users/brianye/PycharmProjects/AI-town/Helloagents-AI-Town/helloagents-ai-town/project.godot
```

运行游戏：

- 点击 Godot 右上角运行按钮
- 或按 `F5`

游戏操作：

- `WASD`：移动
- `E`：与 NPC 交互
- `Enter`：发送消息
- `T`：打开或关闭任务面板
- `ESC`：关闭对话框

任务面板：

- 第一次打开会请求 `/tasks`，后续会优先显示缓存并刷新
- 可接受任务会显示 `接受` 和 `暂不接受`
- 任务完成需要继续和对应 NPC 对话，不在任务面板里提交文本
- 每次 NPC 对话成功后，客户端会刷新任务缓存

Godot 默认连接后端：

```text
http://localhost:8000
```

对应配置文件：

```text
Helloagents-AI-Town/helloagents-ai-town/scripts/config.gd
```

如果后端端口不是 `8000`，需要同步修改 `config.gd` 中的 `API_BASE_URL`。

## 6. 停止服务

停止后端：

```text
在后端终端按 Ctrl+C
```

停止 Qdrant：

```bash
docker stop ai-town-qdrant
```

如果只是临时关闭游戏，不一定要停止 Qdrant。

## 7. 常见问题

### 7.1 后端提示未设置 `LLM_API_KEY`

检查 `.env` 是否存在：

```bash
cd /Users/brianye/PycharmProjects/AI-town/Helloagents-AI-Town/backend
ls -la .env
```

如果不存在：

```bash
cp .env.example .env
```

然后填写：

```env
LLM_API_KEY=你的中转站key
LLM_BASE_URL=https://你的中转站地址/v1
LLM_MODEL_ID=你的模型名
```

### 7.2 返回 `401`

通常原因：

- API Key 错误
- 中转站账号无额度
- 中转站鉴权格式不兼容

### 7.3 返回 `404` 或 `model not found`

通常原因：

- `LLM_MODEL_ID` / `OPENAI_MODEL` 填错
- 中转站不支持该模型
- `LLM_BASE_URL` / `OPENAI_BASE_URL` 填错

建议确认中转站文档中的模型名，比如：

```text
deepseek-chat
gpt-4o-mini
qwen-plus
```

具体以你的中转站支持列表为准。

### 7.4 后端出现 `'str' object has no attribute 'choices'`

这说明请求已经打到 LLM 相关链路，但中转站返回值不是 OpenAI SDK 默认期望的 `choices` 对象格式。优先检查 `.env`：

```env
LLM_BASE_URL=https://你的中转站地址/v1
LLM_MODEL_ID=你的模型名
```

不要填成完整接口：

```env
LLM_BASE_URL=https://你的中转站地址/v1/chat/completions
```

也不要优先使用没有 `/v1` 的根地址，除非你的中转站文档明确要求根地址。修改后需要停止后端并重新启动：

```text
在后端终端按 Ctrl+C
```

然后重新执行：

```bash
cd /Users/brianye/PycharmProjects/AI-town
source .venv311/bin/activate
cd Helloagents-AI-Town/backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 7.5 Qdrant 连接失败

检查 Qdrant：

```bash
docker ps --filter name=ai-town-qdrant
curl http://127.0.0.1:6333/
```

如果没有运行：

```bash
docker start ai-town-qdrant
```

### 7.6 端口 `8000` 被占用

检查占用：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

如果是旧的后端进程，回到对应终端按 `Ctrl+C`。

也可以换端口启动：

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

同时修改 Godot：

```text
Helloagents-AI-Town/helloagents-ai-town/scripts/config.gd
```

把 `API_BASE_URL` 改成：

```gdscript
const API_BASE_URL = "http://localhost:8001"
```

### 7.7 Godot 中无法对话

按顺序检查：

1. 后端是否正在运行
2. `http://localhost:8000/docs` 是否能打开
3. Godot 的 `API_BASE_URL` 是否仍指向正确后端地址
4. 后端终端是否有 LLM 报错
5. Qdrant 是否正在运行

### 7.8 对话后出现好感度分析超时

如果 NPC 已经正常回复，但后端显示：

```text
好感度分析跳过: 分析超时
```

这不是主对话失败，只是回复之后的好感度分析调用中转站超时，本次好感度不会变化。可以继续测试游戏。

如果本地测试时不想额外调用一次 LLM 分析好感度，在 `backend/.env` 中改成：

```env
LLM_AFFINITY_ENABLED=false
```

修改后重启后端生效。

## 8. 当前最终验证结果

已在当前机器上验证：

```bash
.venv311/bin/python -m compileall -q Helloagents-AI-Town/backend
curl http://127.0.0.1:6333/
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/npcs
curl http://127.0.0.1:8000/npcs/status
```

验证结论：

- 后端代码可编译
- Python 依赖完整
- Qdrant 可访问
- 后端可启动
- 三个 NPC 可用
- 状态刷新接口可用
- `/chat` 在 dummy LLM 下会返回受控错误，不会导致服务崩溃

未验证项：

- 真实 LLM 对话质量
- 真实中转站 Key、Base URL、模型名是否可用

这两项需要你填入真实 `.env` 后再验证。
