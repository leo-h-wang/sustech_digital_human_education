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
    # 格式化解题步骤
    steps_text = ""
    for step in solution_steps:
        steps_text += f"\n**步骤 {step.step_index}：{step.title}**\n"
        steps_text += f"{step.description}\n"
        if step.formula_latex:
            steps_text += f"公式：{step.formula_latex}\n"
    
    prompt = f"""你是一位大学高等数学老师，正在课堂上对学生讲解这道题。请根据解题步骤，生成一份适合口头讲解的脚本。

**题目：**
{problem_text}

**解题步骤：**
{steps_text}

**要求：**
1. 讲解风格要亲切、耐心，适合大学生理解水平
2. 语言要口语化，自然流畅，就像在课堂上面对面讲解一样
3. **重要：所有数学公式和符号必须转换为适合文本转语音（TTS）的口语表达**
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

4. 每步讲解要循序渐进，可以适当使用类比、小结等方式帮助学生理解
5. 每步讲解长度控制在3-8句话，不要太长
6. 输出格式：每步以 "步骤N：" 开头，然后跟讲解内容

**输出格式示例：**
步骤1：同学们，我们先来看这道题。这是一道关于[题型]的题目，我们需要[整体思路]...

步骤2：首先，我们注意到[观察点]。根据[知识点]，我们可以[方法]...

步骤3：接下来，我们计算[具体计算]。这里要注意[注意点]...

**请开始生成讲解脚本：**
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

