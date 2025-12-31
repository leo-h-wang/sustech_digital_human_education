"""幻灯片 HTML 生成器"""
from typing import List, Optional
from jinja2 import Template
from app.models.schemas import SolutionStep, NarrationStep


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
        }
        .slide {
            width: 100%;
            min-height: 100vh;
            background: white;
            margin-bottom: 20px;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            page-break-after: always;
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
        }
        .step-title {
            font-size: 28px;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #4a90e2;
        }
        .step-content {
            font-size: 22px;
            line-height: 1.8;
            color: #34495e;
            margin-bottom: 20px;
        }
        .formula {
            background: #f8f9fa;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #4a90e2;
            font-family: "Times New Roman", serif;
            font-size: 20px;
        }
        .narration-text {
            font-size: 24px;
            line-height: 2;
            color: #2c3e50;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
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
            {{ problem_text }}
        </div>
        
        <div class="step-title">
            <span class="step-number">{{ slide.step_index }}</span>
            {{ slide.title }}
        </div>
        
        {% if slide.description %}
        <div class="step-content">
            {{ slide.description | safe }}
        </div>
        {% endif %}
        
        {% if slide.formula_latex %}
        <div class="formula">
            {{ slide.formula_latex }}
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
    生成幻灯片 HTML
    
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
    
    # 如果没有讲解步骤，至少生成解题步骤的幻灯片
    if not slides:
        slides.append({
            "step_index": 1,
            "title": "题目解析",
            "description": "暂无详细步骤",
            "formula_latex": None,
            "narration_text": None
        })
    
    template = Template(SLIDE_TEMPLATE)
    html = template.render(
        problem_text=problem_text,
        slides=slides
    )
    
    return html

