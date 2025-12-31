# 南科大高等数学数字人教学项目

AI 驱动的高等数学题目解答与课件生成工具，支持自动解题、生成讲解脚本和 PDF 幻灯片。

## 功能特性

- 🤖 **AI 解题**：调用大语言模型（优先支持国内模型）自动解答高等数学题目
- 📝 **讲解生成**：将解题过程转换为适合 TTS 的口语化讲解脚本
- 📄 **PDF 课件**：自动生成分步骤的 PDF 幻灯片，每步一页
- 🔄 **批量处理**：支持批量输入题目并生成多个 PDF
- 🎨 **Web 界面**：简洁易用的本地 Web 界面

## 技术栈

- **后端框架**：FastAPI
- **LLM 支持**：通义千问（可扩展其他模型）
- **PDF 生成**：ReportLab（纯Python，无需系统依赖）
- **模板引擎**：Jinja2

## 快速开始

### 1. 安装依赖

**使用 uv（推荐）：**
```bash
uv sync
```

**使用 pip：**
```bash
pip install -e .
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

**Windows PowerShell:**
```powershell
New-Item -Path .env -ItemType File
```

**Linux/Mac:**
```bash
touch .env
```

编辑 `.env` 文件，添加以下内容：

```env
LLM_PROVIDER=tongyi
TONGYI_API_KEY=你的API密钥
TONGYI_MODEL=qwen-max  # 可选: qwen-turbo, qwen-plus, qwen-max, qwen-max-longcontext
TONGYI_TIMEOUT=180     # 可选: 超时时间（秒），会根据模型自动调整
PORT=8000
```

**获取通义千问 API Key：**
1. 访问 https://dashscope.aliyun.com/
2. 注册/登录后进入"API-KEY管理"
3. 创建新的 API Key 并复制到 `.env` 文件

### 3. 运行服务

**使用 uv：**
```bash
uv run python main.py
```

**使用 pip：**
```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

**详细说明请参考：**
- [UV_SETUP.md](UV_SETUP.md) - uv 使用指南
- [INSTALL.md](INSTALL.md) - 详细安装说明

### 4. 使用 Web 界面

打开浏览器访问 `http://localhost:8000`，输入题目即可一键生成课件。

## API 接口

### 解题接口

```bash
POST /api/solve
Content-Type: application/json

{
  "text": "求极限：$\\lim_{x \\to 0} \\frac{\\sin x}{x}$",
  "topic": "极限",
  "difficulty": "中等"
}
```

### 生成讲解接口

```bash
POST /api/narrate
Content-Type: application/json

{
  "problem_text": "题目文本",
  "solution_steps": [...]
}
```

### 生成 PDF 接口

```bash
POST /api/generate_pdf
Content-Type: application/json

{
  "problem_text": "题目文本",
  "solution_steps": [...],
  "narration_steps": [...]
}
```

### 完整流水线接口

```bash
POST /api/full_pipeline
Content-Type: application/json

{
  "text": "题目文本",
  "topic": "极限",
  "difficulty": "中等"
}
```

## 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── models/          # 数据模型
│   │   └── schemas.py
│   ├── llm_providers/   # LLM 适配器
│   │   ├── base.py
│   │   ├── tongyi.py
│   │   └── factory.py
│   ├── prompts/         # Prompt 模板
│   │   ├── solver_prompt.py
│   │   └── narration_prompt.py
│   ├── text/            # 文本处理
│   │   └── tts_friendly.py
│   ├── slides/          # 幻灯片生成
│   │   ├── generator.py
│   │   └── pdf_export.py
│   ├── routers/         # API 路由
│   │   ├── api.py
│   │   └── web.py
│   └── templates/       # HTML 模板
│       └── index.html
├── problems/            # 题目记录（自动生成）
├── main.py              # 主入口
├── config.yaml.example  # 配置示例
├── .env.example         # 环境变量示例
└── README.md
```

## 开发计划

- [x] 基础项目结构
- [x] LLM 客户端接口与通义千问适配器
- [x] 解题与讲解 Prompt 模块
- [x] PDF 幻灯片生成
- [x] API 路由与 Web 界面
- [x] 批量处理与 PDF 合并功能
- [x] 输出校验与错误处理
- [x] 并发控制与超时处理
- [ ] 更多 LLM 提供商支持（星火、Kimi）
- [ ] 结果缓存功能（已实现基础框架）

## 许可证

MIT License

