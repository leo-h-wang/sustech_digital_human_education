"""PDF 导出模块 - 使用 ReportLab"""
from io import BytesIO
from typing import Optional, List
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from app.models.schemas import SolutionStep, NarrationStep
import os


# 尝试注册中文字体
def _register_chinese_fonts():
    """注册中文字体"""
    try:
        # Windows 常见中文字体路径（优先使用TTF格式）
        font_paths = [
            (r"C:\Windows\Fonts\simhei.ttf", "SimHei"),  # 黑体
            (r"C:\Windows\Fonts\msyh.ttf", "MicrosoftYaHei"),  # 微软雅黑（TTF版本）
            (r"C:\Windows\Fonts\simsun.ttf", "SimSun"),  # 宋体（TTF版本）
        ]
        
        for font_path, font_name in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    return font_name
                except Exception as e:
                    # 如果注册失败，尝试下一个字体
                    continue
        
        # 如果都失败，使用默认字体（可能不支持中文，但至少不会报错）
        return 'Helvetica'
    except Exception:
        return 'Helvetica'


# 注册字体
CHINESE_FONT = _register_chinese_fonts()


def _create_styles():
    """创建样式"""
    styles = getSampleStyleSheet()
    
    # 题目标题样式
    problem_style = ParagraphStyle(
        'ProblemStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=HexColor('#FFFFFF'),
        backColor=HexColor('#4a90e2'),
        spaceAfter=20,
        spaceBefore=0,
        leftIndent=0,
        rightIndent=0,
        alignment=TA_LEFT,
        fontName=CHINESE_FONT,
    )
    
    # 步骤标题样式
    step_title_style = ParagraphStyle(
        'StepTitleStyle',
        parent=styles['Heading2'],
        fontSize=24,
        textColor=HexColor('#2c3e50'),
        spaceAfter=15,
        spaceBefore=20,
        fontName=CHINESE_FONT,
        borderWidth=0,
        borderPadding=0,
    )
    
    # 步骤内容样式
    step_content_style = ParagraphStyle(
        'StepContentStyle',
        parent=styles['Normal'],
        fontSize=16,
        textColor=HexColor('#34495e'),
        spaceAfter=12,
        leading=28,
        fontName=CHINESE_FONT,
    )
    
    # 公式样式
    formula_style = ParagraphStyle(
        'FormulaStyle',
        parent=styles['Normal'],
        fontSize=16,
        textColor=HexColor('#2c3e50'),
        backColor=HexColor('#f8f9fa'),
        leftIndent=15,
        rightIndent=15,
        spaceBefore=10,
        spaceAfter=10,
        leading=24,
        fontName='Courier',  # 公式用等宽字体
    )
    
    # 讲解文本样式
    narration_style = ParagraphStyle(
        'NarrationStyle',
        parent=styles['Normal'],
        fontSize=18,
        textColor=HexColor('#2c3e50'),
        backColor=HexColor('#f8f9fa'),
        leftIndent=20,
        rightIndent=20,
        spaceBefore=15,
        spaceAfter=15,
        leading=32,
        fontName=CHINESE_FONT,
    )
    
    return {
        'problem': problem_style,
        'step_title': step_title_style,
        'step_content': step_content_style,
        'formula': formula_style,
        'narration': narration_style,
    }


def _prepare_slide_data(
    problem_text: str,
    solution_steps: List[SolutionStep],
    narration_steps: Optional[List[NarrationStep]] = None
) -> List[dict]:
    """准备幻灯片数据"""
    slides = []
    for step in solution_steps:
        slide_data = {
            "step_index": step.step_index,
            "title": step.title,
            "description": step.description,
            "formula_latex": step.formula_latex,
            "narration_text": None
        }
        
        # 如果有对应的讲解步骤，添加进去
        if narration_steps:
            for narration in narration_steps:
                if narration.step_index == step.step_index:
                    slide_data["narration_text"] = narration.narration_text
                    break
        
        slides.append(slide_data)
    
    # 如果没有步骤，创建一个默认步骤
    if not slides:
        slides.append({
            "step_index": 1,
            "title": "题目解析",
            "description": "暂无详细步骤",
            "formula_latex": None,
            "narration_text": None
        })
    
    return slides


def _escape_text(text: str) -> str:
    """转义文本中的特殊字符（ReportLab需要）"""
    if not text:
        return ""
    # ReportLab 的 Paragraph 需要转义 < > & 等字符
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def generate_pdf(
    problem_text: str,
    solution_steps: list[SolutionStep],
    narration_steps: Optional[list[NarrationStep]] = None,
    output_path: Optional[str] = None
) -> BytesIO:
    """
    生成 PDF 文件
    
    Args:
        problem_text: 题目文本
        solution_steps: 解题步骤列表
        narration_steps: 讲解步骤列表（可选）
        output_path: 输出文件路径（可选，如果提供则保存到文件）
        
    Returns:
        PDF 文件的字节流
    """
    # 准备数据
    slides = _prepare_slide_data(problem_text, solution_steps, narration_steps)
    
    # 创建PDF字节流
    pdf_bytes = BytesIO()
    
    # 创建文档（A4横向）
    doc = SimpleDocTemplate(
        pdf_bytes,
        pagesize=landscape(A4),
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )
    
    # 创建样式
    styles = _create_styles()
    
    # 构建内容
    story = []
    
    # 为每个步骤创建一页
    for slide in slides:
        # 题目标题（每页顶部）
        problem_para = Paragraph(
            _escape_text(problem_text),
            styles['problem']
        )
        story.append(problem_para)
        story.append(Spacer(1, 0.5*cm))
        
        # 步骤标题（带步骤号）
        step_title_text = f"<b>步骤 {slide['step_index']}：{_escape_text(slide['title'])}</b>"
        step_title_para = Paragraph(step_title_text, styles['step_title'])
        story.append(step_title_para)
        story.append(Spacer(1, 0.3*cm))
        
        # 步骤描述
        if slide['description']:
            # 将描述按行分割，每行一个段落
            description_lines = slide['description'].split('\n')
            for line in description_lines:
                if line.strip():
                    desc_para = Paragraph(_escape_text(line.strip()), styles['step_content'])
                    story.append(desc_para)
            story.append(Spacer(1, 0.2*cm))
        
        # 公式（如果有）
        if slide['formula_latex']:
            formula_text = f"<i>{_escape_text(slide['formula_latex'])}</i>"
            formula_para = Paragraph(formula_text, styles['formula'])
            story.append(formula_para)
            story.append(Spacer(1, 0.3*cm))
        
        # 讲解文本（如果有）
        if slide['narration_text']:
            narration_para = Paragraph(_escape_text(slide['narration_text']), styles['narration'])
            story.append(narration_para)
        
        # 如果不是最后一页，添加分页
        if slide != slides[-1]:
            story.append(PageBreak())
    
    # 构建PDF
    doc.build(story)
    
    # 重置字节流位置
    pdf_bytes.seek(0)
    
    # 如果指定了输出路径，保存到文件
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes.getvalue())
        pdf_bytes.seek(0)
    
    return pdf_bytes
