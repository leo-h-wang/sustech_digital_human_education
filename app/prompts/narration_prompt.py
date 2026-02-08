"""讲解 Prompt 模板"""
from typing import List, Dict, Any
from app.models.schemas import SolutionStep


def get_narration_prompt(
    problem_text: str,
    solution_steps: List[SolutionStep],
    meta: Dict[str, Any]
) -> str:
    """
    生成讲解 Prompt
    
    Args:
        problem_text: 题目文本
        solution_steps: 解题步骤列表
        meta: 元数据
        
    Returns:
        完整的 Prompt 字符串
    """
    # 格式化解题步骤（纯文本，不使用 Markdown）
    steps_text = ""
    for step in solution_steps:
        steps_text += f"\n步骤 {step.step_index}：{step.title}\n"
        steps_text += f"{step.description}\n"
        if step.formula_latex:
            steps_text += f"公式：{step.formula_latex}\n"
    
    prompt = f"""你是一位大学高等数学老师，正在课堂上对学生讲解这道题。请根据解题步骤，生成一份适合口头讲解的脚本。

题目：
{problem_text}

解题步骤：
{steps_text}

核心要求（非常重要）：
1. 讲解风格要亲切、耐心，适合大学生理解水平
2. 语言要口语化，自然流畅，就像在课堂上面对面讲解一样
3. 重要：所有数学公式和符号必须转换为适合文本转语音（TTS）的口语表达
   - 例如：$x^3$ → "x的三次方"
   - 例如：$\\int_{{0}}^{{1}} x^2 dx$ → "从0到1的定积分，被积函数是x的二次方，对x积分"
   - 例如：$\\frac{{d}}{{dx}}$ → "对x求导" 或 "d比dx"
   - 例如：$\\lim_{{x \\to 0}}$ → "当x趋近于0时的极限"
   - 例如：$\\sum_{{i=1}}^n$ → "从i等于1到n的求和"
   - 例如：$\\sqrt{{x}}$ → "根号x" 或 "x的平方根"
   - 例如：$e^x$ → "e的x次方"
   - 例如：$\\sin(x)$ → "sin x" 或 "x的正弦值"
   - 例如：$\\ln(x)$ → "ln x" 或 "x的自然对数"
   - 例如：$\\pi$ → "派" 或 "圆周率"
   - 例如：$\\infty$ → "无穷大"
   - 例如：$\\neq$ → "不等于"
   - 例如：$\\geq$ → "大于等于"
   - 例如：$\\leq$ → "小于等于"
   - 例如：$\\pm$ → "正负"
   - 例如：$\\alpha, \\beta, \\gamma$ → "阿尔法"、"贝塔"、"伽马"

4. 绝对禁止使用任何 Markdown 格式符号：
   - 不要使用 ** 或 __ 加粗
   - 不要使用 ` 或 ``` 代码标记
   - 不要使用 # 标题符号
   - 不要在行首使用 - * + 作为列表符号
   - 不要使用 > 引用符号
   输出必须是纯文本，便于 TTS 系统直接朗读

5. 每步讲解要循序渐进，可以适当使用类比、小结等方式帮助学生理解
6. 每步讲解长度控制在3-8句话，不要太长

输出格式（必须严格遵守）：
必须输出标准 JSON 数组格式，每个元素对应一个解题步骤的讲解：
[
  {{
    "step_index": 1,
    "narration_text": "同学们，我们先来看这道题。这是一道关于某某的题目..."
  }},
  {{
    "step_index": 2,
    "narration_text": "首先，我们注意到某某。根据某某知识点，我们可以..."
  }},
  {{
    "step_index": 3,
    "narration_text": "接下来，我们计算某某。这里要注意某某..."
  }}
]

重要提示：
- 只返回 JSON 数组，不要添加任何其他文字说明、解释或 markdown 代码块标记
- 不要使用 ```json 或 ``` 等 markdown 标记，直接输出纯 JSON 数组
- 确保 JSON 格式正确，可以被直接解析
- step_index 必须与解题步骤的 step_index 一一对应
- narration_text 必须是纯文本，不含任何 Markdown 符号

请开始生成讲解脚本：
"""
    
    return prompt


# 调试模式：打印 Prompt
def debug_print_narration_prompt(
    problem_text: str,
    solution_steps: List[SolutionStep],
    meta: Dict[str, Any]
):
    """调试用：打印生成的 Prompt"""
    prompt = get_narration_prompt(problem_text, solution_steps, meta)
    print("=" * 80)
    print("讲解 Prompt:")
    print("=" * 80)
    print(prompt)
    print("=" * 80)