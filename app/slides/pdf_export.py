"""PDF 导出模块 - 使用 WeasyPrint 和 MathML"""
from io import BytesIO
from typing import Optional, List
import logging
from app.models.schemas import SolutionStep, NarrationStep
from app.slides.generator import generate_slides_html_with_formulas

logger = logging.getLogger(__name__)


def generate_pdf(
    problem_text: str,
    solution_steps: list[SolutionStep],
    narration_steps: Optional[list[NarrationStep]] = None,
    output_path: Optional[str] = None
) -> BytesIO:
    """
    生成 PDF 文件（使用 WeasyPrint 和 MathML 渲染数学公式）
    
    Args:
        problem_text: 题目文本
        solution_steps: 解题步骤列表
        narration_steps: 讲解步骤列表（可选）
        output_path: 输出文件路径（可选，如果提供则保存到文件）
        
    Returns:
        PDF 文件的字节流
    """
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
    except ImportError as e:
        logger.error(f"WeasyPrint 未安装或导入失败: {e}")
        logger.error("请运行: uv pip install weasyprint")
        raise ImportError(
            "WeasyPrint 库未安装。请运行: uv pip install weasyprint\n"
            "注意：Windows 用户可能需要安装 GTK3 运行时。"
        ) from e
    
    logger.info(f"开始生成PDF - 题目: {problem_text[:30]}...")
    logger.info(f"解题步骤数: {len(solution_steps)}")
    
    # 生成带有 MathML 公式的 HTML
    try:
        html_content = generate_slides_html_with_formulas(
            problem_text=problem_text,
            solution_steps=solution_steps,
            narration_steps=narration_steps
        )
        logger.info("HTML 内容生成成功")
    except Exception as e:
        logger.error(f"生成 HTML 内容失败: {e}")
        raise
    
    # 创建 PDF 字节流
    pdf_bytes = BytesIO()
    
    try:
        # 配置字体
        font_config = FontConfiguration()
        
        # 创建 HTML 对象
        html = HTML(string=html_content)
        
        # 生成 PDF
        logger.info("开始使用 WeasyPrint 渲染 PDF...")
        html.write_pdf(
            pdf_bytes,
            font_config=font_config
        )
        logger.info("PDF 渲染成功")
        
    except Exception as e:
        logger.error(f"WeasyPrint 渲染失败: {e}")
        # 尝试降级处理
        logger.warning("尝试不使用字体配置重新渲染...")
        try:
            pdf_bytes = BytesIO()
            html = HTML(string=html_content)
            html.write_pdf(pdf_bytes)
            logger.info("PDF 渲染成功（无字体配置）")
        except Exception as e2:
            logger.error(f"降级渲染也失败: {e2}")
            raise
    
    # 重置字节流位置
    pdf_bytes.seek(0)
    
    # 如果指定了输出路径，保存到文件
    if output_path:
        try:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes.getvalue())
            logger.info(f"PDF 已保存到: {output_path}")
            pdf_bytes.seek(0)
        except Exception as e:
            logger.error(f"保存 PDF 文件失败: {e}")
            raise
    
    pdf_size = len(pdf_bytes.getvalue())
    logger.info(f"PDF 生成完成，大小: {pdf_size / 1024:.2f} KB")
    
    return pdf_bytes
