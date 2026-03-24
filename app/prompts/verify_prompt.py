"""解题验证 Prompt 模板"""
from typing import List
from app.models.schemas import SolutionStep


def get_verify_prompt(problem_text: str, solution_steps: List[SolutionStep], meta: dict = None) -> str:
    """
    生成解题验证 Prompt

    Returns:
        完整的 Prompt 字符串
    """
    steps_text = ""
    for step in solution_steps:
        steps_text += f"\n步骤 {step.step_index}：{step.title}\n"
        steps_text += f"{step.description}\n"
        if step.formula_latex:
            steps_text += f"公式：{step.formula_latex}\n"

    return f"""你是一位严格的大学高等数学老师，负责审核学生提交的解题过程。

请仔细检查以下解题过程是否正确：

题目：
{problem_text}

解题步骤：
{steps_text}

审核要求：
1. 检查每个步骤的数学逻辑是否正确
2. 检查公式推导和计算是否无误
3. 检查步骤之间的逻辑连贯性
4. 检查最终结果是否正确

请以如下 JSON 格式回复（不要输出其他内容）：
{{
  "is_correct": true 或 false,
  "feedback": "如果有错误，请详细说明错在哪里、应该如何修正；如果正确，请写'解题过程正确'"
}}"""
