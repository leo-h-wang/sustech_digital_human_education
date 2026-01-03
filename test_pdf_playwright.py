"""测试 Playwright PDF 生成"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.models.schemas import SolutionStep, NarrationStep
from app.slides.pdf_export_playwright import generate_pdf


def main():
    print("="*60)
    print("Playwright PDF 生成测试")
    print("="*60)
    
    # 准备测试数据
    problem_text = r"solve: $$\int_{2}^{\infty} \frac{1}{(x-1)(x-2)^2} dx$$"
    
    solution_steps = [
        SolutionStep(
            step_index=1,
            title="识别题目类型与处理策略",
            description="该定积分是一个广义积分，因为它具有无限的上限。",
            formula_latex=r"$$I = \int_{2}^{\infty} \frac{1}{(x-1)(x-2)^2} dx$$"
        ),
        SolutionStep(
            step_index=2,
            title="部分分式分解",
            description="将分式分解为更简单的形式。",
            formula_latex=r"$$\frac{1}{(x-1)(x-2)^2} = \frac{A}{x-1} + \frac{B}{x-2} + \frac{C}{(x-2)^2}$$"
        ),
        SolutionStep(
            step_index=3,
            title="计算系数",
            description="通过乘以分母并比较系数来求解A、B、C。",
            formula_latex=r"$$1 = A(x-2)^2 + B(x-1)(x-2) + C(x-1)$$"
        ),
    ]
    
    narration_steps = [
        NarrationStep(
            step_index=1,
            narration_text="同学们，我们先来看这道题目。这是一个从二到无穷大的定积分。"
        ),
        NarrationStep(
            step_index=2,
            narration_text="对于这类分式，我们通常使用部分分式分解的方法。"
        ),
    ]
    
    output_path = "test_output_playwright.pdf"
    
    print(f"\n正在生成 PDF: {output_path}")
    print("（使用 Playwright + Chromium 渲染）")
    
    try:
        pdf_bytes = generate_pdf(
            problem_text=problem_text,
            solution_steps=solution_steps,
            narration_steps=narration_steps,
            output_path=output_path
        )
        
        file_size = len(pdf_bytes.getvalue())
        print(f"\n✓ PDF 生成成功！")
        print(f"  文件路径: {output_path}")
        print(f"  文件大小: {file_size / 1024:.2f} KB")
        print(f"\n请打开 {output_path} 检查：")
        print("  ✓ 数学公式是否正确渲染为符号")
        print("  ✓ 中文是否显示正常")
        print("  ✓ 布局是否美观")
        
    except ImportError as e:
        print(f"\n✗ 依赖库未安装:")
        print(f"  {e}")
        print(f"\n请按顺序运行以下命令:")
        print(f"  1. uv pip install playwright")
        print(f"  2. uv run playwright install chromium")
        print(f"\n这会下载 Chromium 浏览器（约 300MB）")
        
    except Exception as e:
        print(f"\n✗ PDF 生成失败:")
        print(f"  {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()

