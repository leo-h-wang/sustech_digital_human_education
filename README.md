**Language / 语言:** [English](#english) | [中文](#中文)

<a id="english"></a>

# SUSTech Digital Human Teaching Project for Advanced Mathematics

An AI-powered tool for solving advanced mathematics (calculus) problems and generating courseware. It automatically solves problems, generates narration scripts, and produces high-quality PPTX/PDF slides via the Gamma API.

## Features

- 🤖 **AI Problem Solving**: Calls large language models to automatically solve advanced mathematics problems
- 📝 **Narration Generation**: Converts the solution process into a conversational, TTS-friendly narration script (TXT)
- 🎯 **Gamma Slides**: Calls the Gamma Generate API to produce PPTX or PDF files
- 🎨 **Web Interface**: A clean, easy-to-use local Web UI

## Tech Stack

- **Backend Framework**: FastAPI
- **LLM Support**: Tongyi Qianwen (Qwen) / Gemini (extensible)
- **Slide Generation**: Gamma Generate API (async requests via `aiohttp`)
- **Template Engine**: Jinja2

## Quick Start

### 1. Install Dependencies

**Using uv (recommended):**
```bash
uv sync
```

**Using pip:**
```bash
pip install -e .
```

### 2. Configure Environment Variables

Create a `.env` file in the project root and add:

```env
# LLM provider selection (tongyi or gemini)
LLM_PROVIDER=gemini

# ========== Tongyi Qianwen Configuration ==========
TONGYI_API_KEY=your_api_key
TONGYI_MODEL=qwen-max
TONGYI_TIMEOUT=180

# ========== Gemini Configuration ==========
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT=120

# ========== Gamma Configuration ==========
GAMMA_API_KEY=your_gamma_api_key

PORT=8000
```
### Configure the gamma_export theme
```
"themeId: "YOUR_THEME_ID"
```
You can choose different templates here to adjust the font size and style of the generated slides.

### 3. Run the Server

```bash
uv run python main.py
```

The server will start at `http://localhost:8000`.

### 4. Use the Web Interface

Open `http://localhost:8000` in your browser, enter a problem and choose an export format (PPTX or PDF). Once generation finishes, you can directly download the Gamma-generated slides and the narration script TXT.

## API Endpoints

### Solve Endpoint

```bash
POST /api/solve
Content-Type: application/json

{
  "text": "Find the limit: $\\lim_{x \\to 0} \\frac{\\sin x}{x}$",
  "topic": "Limits",
  "difficulty": "Medium"
}
```

### Narration Endpoint

```bash
POST /api/narrate
Content-Type: application/json

{
  "problem_text": "Problem text",
  "solution_steps": [...]
}
```

### Full Pipeline Endpoint

```bash
POST /api/full_pipeline?format=pptx
Content-Type: application/json

{
  "text": "Problem text",
  "topic": "Limits",
  "difficulty": "Medium"
}
```

Example response:
```json
{
  "gamma_url": null,
  "pptx_url": "https://...",
  "pdf_url": null,
  "narration_timestamp": "20260124_230426"
}
```

### Download Narration Script

```bash
GET /api/download_narration/{timestamp}
```

## Pipeline Architecture (main.py → LLM → Gamma)

```mermaid
sequenceDiagram
    participant User
    participant WebUI
    participant API
    participant LLM
    participant GammaAPI
    participant Storage

    User->>WebUI: Enter problem and format
    WebUI->>API: POST /api/full_pipeline
    API->>LLM: solve(problem_text)
    LLM-->>API: solution_steps
    API->>LLM: narrate(problem_text, steps)
    LLM-->>API: narration_steps
    API->>API: TTS-friendly processing
    API->>Storage: Save narration TXT and problem JSON
    API->>GammaAPI: POST /generations
    GammaAPI-->>API: generationId
    API->>GammaAPI: GET /generations/{id}
    GammaAPI-->>API: fileUrl
    API-->>WebUI: pptx_url / pdf_url + narration_timestamp
    WebUI-->>User: Download Gamma slides + narration script
```

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── models/          # Data models
│   │   └── schemas.py
│   ├── llm_providers/   # LLM adapters
│   │   ├── base.py
│   │   ├── tongyi.py
│   │   ├── gemini.py
│   │   └── factory.py
│   ├── prompts/         # Prompt templates
│   │   ├── solver_prompt.py
│   │   └── narration_prompt.py
│   ├── text/            # Text processing
│   │   └── tts_friendly.py
│   ├── slides/          # Gamma slide generation
│   │   └── gamma_export.py
│   ├── routers/         # API routes
│   │   ├── api.py
│   │   └── web.py
│   └── templates/       # HTML templates
│       └── index.html
├── problems/            # Problem records and narration scripts
├── main.py              # Main entry point
└── README.md
```

## License

MIT License

---

<a id="中文"></a>

# 南科大高等数学数字人教学项目

AI 驱动的高等数学题目解答与课件生成工具，支持自动解题、生成讲解脚本，并通过 Gamma API 生成高质量 PPTX/PDF 课件。

## 功能特性

- 🤖 **AI 解题**：调用大语言模型自动解答高等数学题目
- 📝 **讲解生成**：将解题过程转换为适合 TTS 的口语化讲解脚本（TXT）
- 🎯 **Gamma 课件**：调用 Gamma Generate API 生成 PPTX 或 PDF
- 🎨 **Web 界面**：简洁易用的本地 Web UI

## 技术栈

- **后端框架**：FastAPI
- **LLM 支持**：通义千问 / Gemini（可扩展）
- **课件生成**：Gamma Generate API（`aiohttp` 异步请求）
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

在项目根目录创建 `.env` 文件并添加：

```env
# LLM 提供商选择（tongyi 或 gemini）
LLM_PROVIDER=gemini

# ========== 通义千问配置 ==========
TONGYI_API_KEY=你的API密钥
TONGYI_MODEL=qwen-max
TONGYI_TIMEOUT=180

# ========== Gemini 配置 ==========
GEMINI_API_KEY=你的Gemini API密钥
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT=120

# ========== Gamma 配置 ==========
GAMMA_API_KEY=你的Gamma API密钥

PORT=8000
```
### 配置gamma_export theme
```
"themeId: "YOUR_THEME_ID"
```
此处可以通过选用不同的模板来调整生成的字体大小以及样式

### 3. 运行服务

```bash
uv run python main.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 使用 Web 界面

打开浏览器访问 `http://localhost:8000`，输入题目并选择导出格式（PPTX 或 PDF），生成后直接下载 Gamma 生成的课件和讲解稿 TXT。

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

### 完整流水线接口

```bash
POST /api/full_pipeline?format=pptx
Content-Type: application/json

{
  "text": "题目文本",
  "topic": "极限",
  "difficulty": "中等"
}
```

响应示例：
```json
{
  "gamma_url": null,
  "pptx_url": "https://...",
  "pdf_url": null,
  "narration_timestamp": "20260124_230426"
}
```

### 下载讲解稿

```bash
GET /api/download_narration/{timestamp}
```

## 流程架构（main.py → LLM → Gamma）

```mermaid
sequenceDiagram
    participant User
    participant WebUI
    participant API
    participant LLM
    participant GammaAPI
    participant Storage

    User->>WebUI: 输入题目与格式
    WebUI->>API: POST /api/full_pipeline
    API->>LLM: solve(problem_text)
    LLM-->>API: solution_steps
    API->>LLM: narrate(problem_text, steps)
    LLM-->>API: narration_steps
    API->>API: TTS 友好处理
    API->>Storage: 保存 narration TXT 与问题 JSON
    API->>GammaAPI: POST /generations
    GammaAPI-->>API: generationId
    API->>GammaAPI: GET /generations/{id}
    GammaAPI-->>API: fileUrl
    API-->>WebUI: pptx_url / pdf_url + narration_timestamp
    WebUI-->>User: 下载 Gamma 课件 + 讲解稿
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
│   │   ├── gemini.py
│   │   └── factory.py
│   ├── prompts/         # Prompt 模板
│   │   ├── solver_prompt.py
│   │   └── narration_prompt.py
│   ├── text/            # 文本处理
│   │   └── tts_friendly.py
│   ├── slides/          # Gamma 课件生成
│   │   └── gamma_export.py
│   ├── routers/         # API 路由
│   │   ├── api.py
│   │   └── web.py
│   └── templates/       # HTML 模板
│       └── index.html
├── problems/            # 题目记录与讲解稿
├── main.py              # 主入口
└── README.md
```

## 许可证

MIT License

