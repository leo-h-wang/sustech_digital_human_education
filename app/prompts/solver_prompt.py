"""解题 Prompt 模板"""
from typing import Dict, Any


def get_solver_prompt(problem_text: str, meta: Dict[str, Any]) -> str:
    """
    生成解题 Prompt
    
    Args:
        problem_text: 题目文本
        meta: 元数据（题型、难度等）
        
    Returns:
        完整的 Prompt 字符串
    """
    topic = meta.get("topic", "未知")
    difficulty = meta.get("difficulty", "")
    
    prompt = f"""你是一位经验丰富的高等数学教师，擅长解答微积分题目。请仔细分析以下题目，并给出详细、准确的解题过程。

**题目：**
{problem_text}

**要求：**
1. 请将解题过程分解为多个清晰的步骤，每一步都要有明确的说明
2. 不要省略中间步骤，不要跳步，确保每一步都易于理解
3. 如有多种解题方法，请选择最适合教学、最易于学生理解的方法
4. 对于涉及公式的地方，请使用 LaTeX 格式表示（例如：$\\int_0^1 x^2 dx$）
5. 输出格式必须为严格的 JSON 数组，每个元素代表一个步骤

**输出格式（JSON）：**
[
  {{
    "step_index": 1,
    "title": "步骤标题（如：识别题目类型）",
    "description": "步骤的详细说明和推理过程",
    "formula_latex": "如果有公式，用LaTeX格式表示，否则为null"
  }},
  {{
    "step_index": 2,
    "title": "下一步骤标题",
    "description": "下一步骤的详细说明",
    "formula_latex": "公式或null"
  }}
]

**注意：**
- 只返回 JSON 数组，不要添加任何其他文字说明
- 确保 JSON 格式正确，可以被直接解析
- 步骤数量根据题目复杂度决定，一般3-8步为宜
"""
    
    if topic and topic != "未知":
        prompt += f"\n**题型提示：**这是一道关于{topic}的题目。\n"
    
    if difficulty:
        prompt += f"\n**难度提示：**题目难度为{difficulty}。\n"
    
    prompt += "\n请开始解题：\n"
    
    return prompt


# 调试模式：打印 Prompt
def debug_print_prompt(problem_text: str, meta: Dict[str, Any]):
    """调试用：打印生成的 Prompt"""
    prompt = get_solver_prompt(problem_text, meta)
    print("=" * 80)
    print("解题 Prompt:")
    print("=" * 80)
    print(prompt)
    print("=" * 80)

