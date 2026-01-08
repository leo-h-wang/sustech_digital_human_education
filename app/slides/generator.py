"""幻灯片 HTML 生成器"""
from typing import List, Optional
from jinja2 import Template
from app.models.schemas import SolutionStep, NarrationStep
from app.utils.latex_converter import latex_to_mathml, process_text_with_latex
import logging

logger = logging.getLogger(__name__)


SLIDE_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>高等数学题目讲解</title>
    <style>
        @page {
            size: A4 landscape;
            margin: 2cm;
        }
        body {
            font-family: "Microsoft YaHei", "SimHei", "STHeiti", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            box-sizing: border-box;
        }
        .slide {
            width: 100%;
            min-height: 100vh;
            background: white;
            margin-bottom: 20px;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            page-break-after: always;
            box-sizing: border-box;
        }
        .slide:last-child {
            page-break-after: auto;
        }
        .problem-header {
            background: #4a90e2;
            color: white;
            padding: 20px;
            margin: -40px -40px 30px -40px;
            font-size: 20px;
            font-weight: bold;
            border-radius: 0;
            max-width: 100%;
            box-sizing: border-box;
            overflow-x: auto;
            word-break: normal;
            overflow-wrap: normal;
            white-space: nowrap; /* 题目中的长公式不折行，超宽时横向滚动 */
        }
        .problem-header math {
            display: inline-block;
            max-width: 100%;
            overflow-x: auto;
            white-space: nowrap;
            word-break: normal;
            overflow-wrap: normal;
        }
        .step-title {
            font-size: 28px;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #4a90e2;
            max-width: 100%;
            box-sizing: border-box;
        }
        .step-content {
            font-size: 22px;
            line-height: 1.8;
            color: #34495e;
            margin-bottom: 20px;
            word-break: break-word;
            overflow-wrap: anywhere;
            hyphens: auto;
            max-width: 100%;
            box-sizing: border-box;
        }
        .formula {
            background: #f8f9fa;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #4a90e2;
            font-family: "Times New Roman", serif;
            font-size: 20px;
            overflow-x: auto;
            word-break: normal;
            overflow-wrap: normal;
            white-space: nowrap; /* 避免公式被强制断行，超宽时横向滚动 */
            max-width: 100%;
            box-sizing: border-box;
        }
        /* MathML 样式支持 */
        .formula math {
            display: block;
            margin: 10px auto;
            font-size: 16px;
            max-width: 100%;
            overflow-x: auto;
            white-space: nowrap;
            word-break: normal;
            overflow-wrap: normal;
        }
        math {
            font-family: "Latin Modern Math", "STIX Two Math", "Cambria Math", serif;
            max-width: 100%;
            display: inline-block;
            overflow-x: auto;
            white-space: nowrap;
            word-break: normal;
            overflow-wrap: normal;
        }
        .narration-text {
            font-size: 24px;
            line-height: 2;
            color: #2c3e50;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            word-break: break-word;
            overflow-wrap: anywhere;
            max-width: 100%;
            box-sizing: border-box;
        }
        .step-number {
            display: inline-block;
            width: 40px;
            height: 40px;
            background: #4a90e2;
            color: white;
            border-radius: 50%;
            text-align: center;
            line-height: 40px;
            font-size: 20px;
            font-weight: bold;
            margin-right: 15px;
        }
    </style>
</head>
<body>
    {% for slide in slides %}
    <div class="slide">
        <div class="problem-header">
            {{ problem_text | safe }}
        </div>
        
        <div class="step-title">
            <span class="step-number">{{ slide.step_index }}</span>
            {{ slide.title | safe }}
        </div>
        
        {% if slide.description %}
        <div class="step-content">
            {{ slide.description | safe }}
        </div>
        {% endif %}
        
        {% if slide.formula_mathml %}
        <div class="formula">
            {{ slide.formula_mathml | safe }}
        </div>
        {% endif %}
        
        {% if slide.narration_text %}
        <div class="narration-text">
            {{ slide.narration_text }}
        </div>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>
"""


def generate_slides_html(
    problem_text: str,
    solution_steps: List[SolutionStep],
    narration_steps: Optional[List[NarrationStep]] = None
) -> str:
    """
    生成幻灯片 HTML（LaTeX 公式以纯文本显示，用于网页浏览）
    
    Args:
        problem_text: 题目文本
        solution_steps: 解题步骤列表
        narration_steps: 讲解步骤列表（可选）
        
    Returns:
        HTML 字符串
    """
    # 合并步骤信息
    slides = []
    for i, step in enumerate(solution_steps):
        slide_data = {
            "step_index": step.step_index,
            "title": step.title,
            "description": step.description,
            "formula_mathml": step.formula_latex,  # 保持原LaTeX用于显示
            "narration_text": None
        }
        
        # 如果有对应的讲解步骤，合并所有匹配的 narration_text
        if narration_steps:
            narration_texts = []
            for narration in narration_steps:
                if narration.step_index == step.step_index:
                    narration_texts.append(narration.narration_text)
            if narration_texts:
                slide_data["narration_text"] = ' '.join(narration_texts)
        
        slides.append(slide_data)
    
    # 如果没有讲解步骤，至少生成解题步骤的幻灯片
    if not slides:
        slides.append({
            "step_index": 1,
            "title": "题目解析",
            "description": "暂无详细步骤",
            "formula_mathml": None,
            "narration_text": None
        })
    
    template = Template(SLIDE_TEMPLATE)
    html = template.render(
        problem_text=problem_text,
        slides=slides
    )
    
    return html


def generate_slides_html_with_formulas(
    problem_text: str,
    solution_steps: List[SolutionStep],
    narration_steps: Optional[List[NarrationStep]] = None
) -> str:
    """
    生成带有MathML渲染公式的幻灯片 HTML（用于PDF导出）
    
    Args:
        problem_text: 题目文本
        solution_steps: 解题步骤列表
        narration_steps: 讲解步骤列表（可选）
        
    Returns:
        HTML 字符串，其中LaTeX公式已转换为MathML
    """
    # 处理题目文本中的 LaTeX 公式
    processed_problem_text = process_text_with_latex(problem_text)
    # #region agent log
    try:
        import json, time
        with open(r"e:\sustech_digital_human_education\.cursor\debug.log", "a", encoding="utf-8") as _f:
            _f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "formula-debug",
                "hypothesisId": "H1",
                "location": "generator.generate_slides_html_with_formulas:problem_text",
                "message": "problem_text processed",
                "data": {"raw": (problem_text or "")[:180], "processed": (processed_problem_text or "")[:180]},
                "timestamp": int(time.time()*1000)
            }) + "\n")
    except Exception:
        pass
    # #endregion
    
    # 合并步骤信息并转换公式
    slides = []
    for i, step in enumerate(solution_steps):
        # 处理标题中的 LaTeX 公式（行内显示）
        processed_title = process_text_with_latex(step.title) if step.title else ""
        # #region agent log
        try:
            import json, time
            with open(r"e:\sustech_digital_human_education\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "formula-debug",
                    "hypothesisId": "TTitle1",
                    "location": "generator.generate_slides_html_with_formulas:before_title",
                    "message": "raw title",
                    "data": {"step": step.step_index, "raw": step.title[:180] if step.title else ""},
                    "timestamp": int(time.time()*1000)
                }) + "\n")
                _f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "formula-debug",
                    "hypothesisId": "TTitle2",
                    "location": "generator.generate_slides_html_with_formulas:after_title",
                    "message": "processed title",
                    "data": {"step": step.step_index, "processed": processed_title[:180]},
                    "timestamp": int(time.time()*1000)
                }) + "\n")
        except Exception:
            pass
        # #endregion

        # 处理 description 中的 LaTeX 公式
        processed_description = None
        if step.description:
            processed_description = process_text_with_latex(step.description)
        
        # 处理 formula_latex（可能包含换行和混合内容）
        formula_mathml = None
        if step.formula_latex:
            logger.info(f"转换步骤 {step.step_index} 的公式: {step.formula_latex[:50]}...")
            # #region agent log
            try:
                import json, time
                with open(r"e:\sustech_digital_human_education\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "formula-debug",
                        "hypothesisId": "F1",
                        "location": "generator.generate_slides_html_with_formulas:before_formula",
                        "message": "raw formula_latex",
                        "data": {"step": step.step_index, "title": step.title, "raw": step.formula_latex[:180]},
                        "timestamp": int(time.time()*1000)
                    }) + "\n")
            except Exception:
                pass
            # #endregion
            formula_mathml = process_text_with_latex(step.formula_latex)
            # #region agent log
            try:
                import json, time
                with open(r"e:\sustech_digital_human_education\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "formula-debug",
                        "hypothesisId": "F2",
                        "location": "generator.generate_slides_html_with_formulas:after_formula",
                        "message": "processed formula_mathml snippet",
                        "data": {"step": step.step_index, "processed": (formula_mathml or "")[:180]},
                        "timestamp": int(time.time()*1000)
                    }) + "\n")
            except Exception:
                pass
            # #endregion
        
        slide_data = {
            "step_index": step.step_index,
            "title": processed_title,
            "description": processed_description,
            "formula_mathml": formula_mathml,
            "narration_text": None
        }
        
        # 如果有对应的讲解步骤，合并所有匹配的 narration_text
        if narration_steps:
            narration_texts = []
            for narration in narration_steps:
                if narration.step_index == step.step_index:
                    narration_texts.append(narration.narration_text)
            if narration_texts:
                slide_data["narration_text"] = ' '.join(narration_texts)
        
        slides.append(slide_data)
    
    # 如果没有讲解步骤，至少生成解题步骤的幻灯片
    if not slides:
        slides.append({
            "step_index": 1,
            "title": "题目解析",
            "description": "暂无详细步骤",
            "formula_mathml": None,
            "narration_text": None
        })
    
    template = Template(SLIDE_TEMPLATE)
    html = template.render(
        problem_text=processed_problem_text,
        slides=slides
    )
    
    return html

