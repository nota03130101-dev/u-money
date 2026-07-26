# U Money AI Service

## 安全启动

服务默认不启用 Mock 模式。仅在本机学习和测试时，在启动前设置：

```powershell
$env:APP_ENV = "development"
$env:MOCK_MODE = "true"
```

正式部署必须设置 `APP_ENV=production` 与 `MOCK_MODE=false`。如果缺少模型、Supabase、日志哈希或明确 HTTPS CORS 配置，服务会拒绝启动。

这是 U Money 的最小 Python FastAPI 服务。目前实现自然语言智能记账接口，默认使用 mock 模式，不调用真实模型，也不需要模型密钥。

## 创建虚拟环境

虚拟环境是这个项目专用的 Python 工具箱，不会污染电脑中的其他 Python 项目。

在 `ai-service` 文件夹中执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Mock 模式

保持 `MOCK_MODE=true`。它不会调用模型，固定示例为：

```text
昨天午饭 32 元，坐地铁 4 元
```

mock 模式只接受非空 Bearer token，用于让本地前端流程与正式登录流程一致。它只能用于本地开发，不能部署给真实用户。

## 启动与测试

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

健康检查地址：<http://127.0.0.1:8000/health>

## 前端本地连接

使用本地静态服务器打开 U Money 页面时，页面默认请求 `http://127.0.0.1:8000`。正式 GitHub Pages 页面不会自动指向本地 AI 服务。

智能记账要求先登录。用户确认候选记录后，前端仍使用当前 Supabase 会话保存；AI 服务不写数据库。

## 真实模型模式

只有准备好模型服务和 Supabase Auth 验证后，才可以把 `MOCK_MODE` 改为 `false`。真实模式需要：

```text
# Alibaba Cloud Model Studio / Qwen. Copy MODEL_API_BASE_URL from the API Host
# shown for your Beijing-region key, and keep MODEL_API_KEY only in the server.
MODEL_API_BASE_URL=
MODEL_API_KEY=
MODEL_NAME=qwen-flash
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
```

Qwen uses JSON-object output in its OpenAI-compatible API. U Money validates the
returned JSON with Pydantic before returning any candidate transaction to the page.

不要把真实值写进前端、GitHub 或聊天消息。
