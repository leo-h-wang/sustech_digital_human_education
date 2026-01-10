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

**核心要求（非常重要）：**
1. **准确性第一**：必须确保每一步计算都是正确的，最终答案必须准确无误
2. **严谨性**：使用正确的数学定理和方法，不要使用错误的方法或公式
3. **验证答案**：在最后一步，请验证答案的正确性（如代入原式检验、检查定义域等）
4. **完整步骤**：请将解题过程分解为多个清晰的步骤，每一步都要有明确的说明和推理
5. **不要跳步**：不要省略中间步骤，确保每一步都易于理解，特别是关键的计算过程
6. **方法选择**：如有多种解题方法，请选择最严谨、最准确的方法，而不是最容易理解的方法
7. **公式规范**：对于涉及公式的地方，请使用 LaTeX 格式表示（例如：$\int_0^1 x^2 dx$）
8. **输出格式**：输出格式必须为严格的 JSON 数组，每个元素代表一个步骤

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

**解题原则：**
- 如果题目是计算题，必须给出准确的数值结果
- 如果题目是证明题，必须给出严格的逻辑推理
- 如果题目是判断收敛性，必须给出明确的结论和理由
- 每一步都要检查是否有计算错误或逻辑错误
- 在最后一步，明确给出最终答案，并简要说明答案的正确性

**输出要求：**
- **只返回 JSON 数组，不要添加任何其他文字说明、解释或markdown代码块标记**
- **不要使用 ```json 或 ``` 等markdown标记，直接输出纯JSON数组**
- 确保 JSON 格式正确，可以被直接解析
- 步骤数量根据题目复杂度决定，一般4-10步为宜
- 最后一步应该包含最终答案和验证说明
- **重要：必须返回完整的JSON数组，不要截断**
- **每个步骤的 description 字段要详细但简洁，避免过长导致响应被截断**
- **如果JSON数组很长，确保最后一个步骤的 description 完整，并以 ] 正确结束数组**
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

