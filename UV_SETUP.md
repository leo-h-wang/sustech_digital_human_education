# 使用 uv 管理项目指南

## 1. 安装依赖

### 方式一：使用 uv sync（推荐）

```bash
# 同步所有依赖（会根据 uv.lock 安装精确版本）
uv sync

# 如果需要安装开发依赖
uv sync --dev
```

### 方式二：使用 uv pip install

```bash
# 安装项目及其依赖
uv pip install -e .

# 或者直接安装依赖
uv pip install -r pyproject.toml
```

### 方式三：添加新依赖

```bash
# 添加新包（会自动更新 pyproject.toml 和 uv.lock）
uv add package-name

# 例如：如果需要添加新包
uv add some-package
```

## 2. 配置 API Key

### 步骤 1：创建 .env 文件

在项目根目录创建 `.env` 文件：

**Windows PowerShell:**
```powershell
New-Item -Path .env -ItemType File
```

**Windows CMD:**
```cmd
type nul > .env
```

**Linux/Mac:**
```bash
touch .env
```

### 步骤 2：编辑 .env 文件

在 `.env` 文件中添加以下内容：

```env
# LLM 提供商（tongyi, gemini, spark, kimi）
LLM_PROVIDER=gemini

# ========== 通义千问配置 ==========
# 通义千问 API Key
# 获取方式：访问 https://dashscope.aliyun.com/ 注册并创建 API Key
TONGYI_API_KEY=你的API密钥

# 通义千问模型配置（可选，默认 qwen-turbo）
# 可选值: qwen-turbo（快速但能力较弱）, qwen-plus（平衡）, qwen-max（最强，推荐用于复杂数学问题）
# qwen-max-longcontext（支持更长上下文）
TONGYI_MODEL=qwen-max

# 通义千问超时配置（可选，会根据模型自动调整）
# qwen-max 等强模型默认 180 秒，qwen-plus 默认 120 秒，qwen-turbo 默认 60 秒
# TONGYI_TIMEOUT=180

# ========== Gemini 配置 ==========
# Gemini API Key
# 获取方式：访问 https://aistudio.google.com/app/apikey 创建 API Key
GEMINI_API_KEY=你的Gemini API密钥

# Gemini 模型配置（可选，默认 gemini-2.5-pro）
# 可选值: gemini-2.5-pro（推荐，推理最强，免费层级 5 RPM / 100 RPD）
#         gemini-2.5-flash（速度快，免费层级 10 RPM / 500 RPD）
#         gemini-2.5-flash-lite（最快，免费层级 15 RPM / 1000 RPD）
GEMINI_MODEL=gemini-2.5-pro

# 备用模型：主模型触发速率限制（429）时自动降级（设为空可禁用）
GEMINI_FALLBACK_MODEL=gemini-2.5-flash

# Gemini 超时配置（可选，会根据模型自动调整）
# Pro 模型默认 180 秒，Flash 模型默认 120 秒
# GEMINI_TIMEOUT=180

# Gemini 速率限制配置（可选，针对免费层级优化）
# GEMINI_MAX_RETRIES=3      # 最大重试次数（默认 3）
# GEMINI_RETRY_DELAY=1.0    # 初始重试延迟（秒，默认 1.0）
# GEMINI_MIN_INTERVAL=       # 请求最小间隔（秒）—— 留空则按模型自动设置
#                             # gemini-2.5-pro=12s, gemini-2.5-flash=6s, flash-lite=4s

# 服务端口（可选，默认8000）
PORT=8000
```

### 步骤 3：获取通义千问 API Key

1. 访问 [阿里云 DashScope 控制台](https://dashscope.aliyun.com/)
2. 注册/登录账号
3. 进入"API-KEY管理"页面
4. 创建新的 API Key
5. 将 API Key 复制到 `.env` 文件中的 `TONGYI_API_KEY` 字段

**重要提示：**
- `.env` 文件已配置在 `.gitignore` 中，不会被提交到 Git
- 不要将 API Key 提交到版本控制系统

## 3. 运行项目

### 使用 uv 运行

```bash
# 方式一：使用 uv run（推荐）
uv run python main.py

# 方式二：激活虚拟环境后运行
uv sync  # 确保依赖已安装
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
python main.py
```

### 使用 uv 运行 uvicorn

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 4. 验证安装

运行以下命令检查依赖是否安装成功：

```bash
uv run python -c "import fastapi; import uvicorn; import weasyprint; print('所有依赖安装成功！')"
```

## 5. uv 常用命令

```bash
# 同步依赖
uv sync

# 添加新依赖
uv add package-name

# 移除依赖
uv remove package-name

# 更新依赖
uv sync --upgrade

# 查看已安装的包
uv pip list

# 运行 Python 脚本
uv run python script.py

# 运行命令（会自动使用项目虚拟环境）
uv run command
```

## 6. 项目结构说明

使用 uv 管理项目时：
- `pyproject.toml` - 项目配置和依赖声明
- `uv.lock` - 锁定的依赖版本（确保一致性）
- `.venv/` - 虚拟环境目录（uv 自动创建）
- `.env` - 环境变量配置（需要手动创建）

## 7. 常见问题

### 问题 1：uv sync 失败

**解决方案：**
```bash
# 清理并重新同步
rm -rf .venv uv.lock  # Linux/Mac
# 或
rmdir /s .venv & del uv.lock  # Windows

uv sync
```

### 问题 2：PDF 生成相关问题

**解决方案：**
- 项目已使用 ReportLab（纯Python库），无需系统依赖
- 如果遇到中文字体问题，确保 Windows 系统字体目录存在中文字体文件
- ReportLab 会自动检测并使用系统中的中文字体

### 问题 3：API Key 未生效

**解决方案：**
- 确保 `.env` 文件在项目根目录
- 确保 `.env` 文件格式正确（没有多余空格）
- 重启服务以重新加载环境变量

### 问题 4：端口被占用

**解决方案：**
- 修改 `.env` 文件中的 `PORT` 为其他端口（如 8001）
- 或在运行命令中指定端口：`uv run uvicorn main:app --port 8001`

## 8. 下一步

配置完成后：
1. 运行 `uv sync` 安装依赖
2. 创建 `.env` 文件并配置 API Key
3. 运行 `uv run python main.py` 启动服务
4. 访问 http://localhost:8000 使用 Web 界面

