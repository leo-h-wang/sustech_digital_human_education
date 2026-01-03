"""测试脚本：验证 PDF 生成和 MathML 公式渲染"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.models.schemas import SolutionStep, NarrationStep
from app.slides.pdf_export import generate_pdf
from app.utils.latex_converter import latex_to_mathml


def test_latex_to_mathml():
    """测试 LaTeX 到 MathML 的转换"""
    print("\n" + "="*60)
    print("测试 1: LaTeX 到 MathML 转换")
    print("="*60)
    
    test_cases = [
        r"$\int_{2}^{\infty} \frac{1}{(x-1)(x-2)^2} dx$",
        r"$\frac{1}{(x-1)(x-2)^2}$",
        r"$x^2 + y^2 = r^2$",
        r"$\sum_{i=1}^{n} i = \frac{n(n+1)}{2}$",
    ]
    
    for i, latex in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"输入 LaTeX: {latex}")
        try:
            mathml = latex_to_mathml(latex)
            print(f"输出 MathML: {mathml[:100]}..." if len(mathml) > 100 else f"输出 MathML: {mathml}")
            print("✓ 转换成功")
        except Exception as e:
            print(f"✗ 转换失败: {e}")


def test_pdf_generation():
    """测试 PDF 生成"""
    print("\n" + "="*60)
    print("测试 2: PDF 生成（含 MathML 公式）")
    print("="*60)
    
    # 准备测试数据
    problem_text = r"solve: $$\int_{2}^{\infty} \frac{1}{(x-1)(x-2)^2} dx$$"
    
    solution_steps = [
        SolutionStep(
            step_index=1,
            title="识别题目类型与处理策略",
            description="该定积分是一个广义积分，因为它具有无限的上限。为了解决这种类型的积分，我们通常会使用适当的变量替换来简化被积函数。",
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
            title="计算定积分",
            description="使用分解后的形式进行积分。",
            formula_latex=r"$$I = \lim_{t \to \infty} \left[ \ln|x-1| - \ln|x-2| - \frac{1}{x-2} \right]_{2}^{t}$$"
        ),
    ]
    
    narration_steps = [
        NarrationStep(
            step_index=1,
            narration_text="同学们，我们先来看这道题目。这是一个从二到无穷大的定积分，被积函数是分式。"
        ),
        NarrationStep(
            step_index=2,
            narration_text="对于这类分式，我们通常使用部分分式分解的方法。"
        ),
    ]
    
    # 生成 PDF
    output_path = "test_output_mathml.pdf"
    
    try:
        print(f"\n正在生成 PDF 文件: {output_path}")
        print("（这将测试 LaTeX 公式是否正确转换为 MathML 并渲染）")
        
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
        print(f"\n请打开 {output_path} 检查数学公式是否正确渲染。")
        
    except ImportError as e:
        print(f"\n✗ 依赖库未安装:")
        print(f"  {e}")
        print(f"\n请先安装依赖:")
        print(f"  uv pip install weasyprint latex2mathml")
        print(f"\n注意: Windows 用户可能还需要安装 GTK3 运行时:")
        print(f"  https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
        
    except Exception as e:
        print(f"\n✗ PDF 生成失败:")
        print(f"  错误信息: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("PDF MathML 渲染测试套件")
    print("="*60)
    
    # 测试 1: LaTeX 转换
    test_latex_to_mathml()
    
    # 测试 2: PDF 生成
    test_pdf_generation()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

