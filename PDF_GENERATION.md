# PDF 生成方案说明

## 技术栈

本项目使用 **Playwright + Chromium** 进行PDF生成，数学公式通过 **MathML** 渲染。

### 核心依赖

- `playwright>=1.40.0` - 浏览器自动化
- `latex2mathml>=3.75.0` - LaTeX转MathML

## 安装步骤

### 1. 安装Python依赖

```bash
uv pip install playwright latex2mathml
```

### 2. 安装Chromium浏览器

```bash
uv run playwright install chromium
```

这会下载约300MB的Chromium浏览器到用户目录（`~/.cache/ms-playwright/`）。

## 工作原理

```
LaTeX公式 → MathML → HTML → Chromium渲染 → PDF
```

1. **LaTeX转换**：`app/utils/latex_converter.py` 将LaTeX公式转换为MathML
2. **HTML生成**：`app/slides/generator.py` 生成包含MathML的HTML
3. **PDF渲染**：`app/slides/pdf_export_playwright.py` 使用Chromium渲染并导出PDF

## 使用示例

### 测试PDF生成

```bash
uv run python test_pdf_playwright.py
```

### 在代码中使用

```python
from app.slides.pdf_export_playwright import generate_pdf, generate_pdf_async
from app.models.schemas import SolutionStep

# 同步版本（用于脚本）
pdf_bytes = generate_pdf(
    problem_text="solve: $$\\int x^2 dx$$",
    solution_steps=[...],
    narration_steps=[...]
)

# 异步版本（用于FastAPI）
pdf_bytes = await generate_pdf_async(
    problem_text="solve: $$\\int x^2 dx$$",
    solution_steps=[...],
    narration_steps=[...]
)
```

## 生成的PDF特点

- ✅ **数学公式完美渲染** - 使用浏览器原生MathML支持
- ✅ **独立文档** - 不依赖外部资源
- ✅ **跨平台兼容** - 任何PDF阅读器都能打开
- ✅ **矢量图形** - 公式是矢量渲染，可无限缩放
- ✅ **打印友好** - 直接打印即可

## 性能考虑

- **首次生成**：~2-3秒（启动浏览器）
- **后续生成**：~1-2秒
- **并发处理**：通过线程池支持3个并发任务

## 故障排除

### Chromium未安装

```
Error: Executable doesn't exist at ...
```

**解决方案**：运行 `uv run playwright install chromium`

### 权限问题

如果遇到权限错误，确保：
- 有写入临时目录的权限
- 有执行Chromium的权限

### 内存不足

如果处理大量PDF时内存不足，可以调整线程池大小：

```python
# 在 app/slides/pdf_export_playwright.py 中修改
_thread_pool = ThreadPoolExecutor(max_workers=2)  # 减少并发数
```

## 相关文件

- `app/slides/pdf_export_playwright.py` - PDF生成主模块
- `app/utils/latex_converter.py` - LaTeX到MathML转换
- `app/slides/generator.py` - HTML模板生成
- `test_pdf_playwright.py` - 测试脚本

## 技术优势

相比其他方案（ReportLab、WeasyPrint等）：

| 特性 | Playwright | 其他方案 |
|------|-----------|---------|
| MathML支持 | ✅ 原生 | ⚠️ 有限/需要额外库 |
| Windows兼容 | ✅ 完美 | ❌ 常需GTK等依赖 |
| 安装复杂度 | ✅ 简单（2条命令） | ⚠️ 复杂 |
| 渲染质量 | ✅ 浏览器级别 | ⚠️ 取决于实现 |
| 维护成本 | ✅ 低（跟随Chromium更新） | ⚠️ 高 |

