"""TTS 友好文本转换工具"""
import re
from typing import List


def strip_markdown_for_tts(text: str) -> str:
    """
    去除 Markdown 格式符号，使文本更适合 TTS 朗读
    
    保守策略：只处理明确的 Markdown 结构，避免误伤数学符号
    
    Args:
        text: 原始文本（可能包含 Markdown 符号）
        
    Returns:
        清理后的纯文本
    """
    if not text:
        return text
    
    result = text
    
    # 1. 去除代码块围栏（三反引号）
    result = re.sub(r'```[\s\S]*?```', '', result)  # 多行代码块
    result = re.sub(r'```[^\n]*', '', result)  # 未闭合的代码块开始
    
    # 2. 去除行内代码（单反引号）
    result = re.sub(r'`([^`]+)`', r'\1', result)  # 提取代码内容，去除反引号
    result = re.sub(r'`', '', result)  # 清理残留的单个反引号
    
    # 3. 去除粗体/斜体（保守：仅处理成对的且不在数学公式中的）
    # **bold** 或 __bold__
    result = re.sub(r'\*\*([^\*]+)\*\*', r'\1', result)
    result = re.sub(r'__([^_]+)__', r'\1', result)
    # *italic* 或 _italic_（只处理明确的单星号/下划线包围）
    result = re.sub(r'(?<!\*)\*([^\*\n]+)\*(?!\*)', r'\1', result)
    result = re.sub(r'(?<!_)_([^_\n]+)_(?!_)', r'\1', result)
    
    # 4. 去除行首的 Markdown 结构标记
    lines = result.split('\n')
    cleaned_lines = []
    for line in lines:
        # 去除标题符号（行首的 # ）
        line = re.sub(r'^#+\s+', '', line)
        # 去除列表符号（行首的 -、*、+ 加空格）
        line = re.sub(r'^[\-\*\+]\s+', '', line)
        # 去除引用符号（行首的 > ）
        line = re.sub(r'^>\s+', '', line)
        cleaned_lines.append(line)
    result = '\n'.join(cleaned_lines)
    
    # 5. 去除链接语法 [text](url)，保留 text
    result = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', result)
    
    # 6. 去除水平分隔线
    result = re.sub(r'^[\-\*_]{3,}\s*$', '', result, flags=re.MULTILINE)
    
    return result


# 数学符号到口语的映射规则
SYMBOL_REPLACEMENTS = [
    # 幂次
    (r'\^(\d+)', r'的\1次方'),
    (r'\^\{([^}]+)\}', r'的\1次方'),
    # 分数
    (r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1除以\2'),
    # 根号
    (r'\\sqrt\{([^}]+)\}', r'根号\1'),
    (r'\\sqrt\[(\d+)\]\{([^}]+)\}', r'\1次根号\2'),
    # 积分
    (r'\\int_\{([^}]+)\}\^\{([^}]+)\}', r'从\1到\2的定积分'),
    (r'\\int', r'积分'),
    # 求和
    (r'\\sum_\{([^}]+)\}\^\{([^}]+)\}', r'从\1到\2的求和'),
    (r'\\sum', r'求和'),
    # 极限
    (r'\\lim_\{([^}]+)\}', r'当\1时的极限'),
    # 导数
    (r'\\frac\{d\}\{d([^}]+)\}', r'对\1求导'),
    (r"\\frac\{d\^(\d+)\}\{d([^}]+)\^\1\}", r'对\2求\1阶导数'),
    # 三角函数
    (r'\\sin', 'sin'),
    (r'\\cos', 'cos'),
    (r'\\tan', 'tan'),
    (r'\\cot', 'cot'),
    (r'\\sec', 'sec'),
    (r'\\csc', 'csc'),
    # 对数
    (r'\\ln', 'ln'),
    (r'\\log', 'log'),
    # 希腊字母
    (r'\\alpha', '阿尔法'),
    (r'\\beta', '贝塔'),
    (r'\\gamma', '伽马'),
    (r'\\delta', '德尔塔'),
    (r'\\epsilon', '艾普西龙'),
    (r'\\theta', '西塔'),
    (r'\\lambda', '拉姆达'),
    (r'\\mu', '缪'),
    (r'\\pi', '派'),
    (r'\\sigma', '西格玛'),
    (r'\\phi', '斐'),
    (r'\\omega', '欧米伽'),
    # 关系符号
    (r'\\neq', '不等于'),
    (r'\\geq', '大于等于'),
    (r'\\leq', '小于等于'),
    (r'\\approx', '约等于'),
    (r'\\equiv', '恒等于'),
    # 其他符号
    (r'\\pm', '正负'),
    (r'\\mp', '负正'),
    (r'\\infty', '无穷大'),
    (r'\\cdot', '乘'),
    (r'\\times', '乘'),
    (r'\\div', '除以'),
    # 括号处理（简化）
    (r'\{', ''),
    (r'\}', ''),
    (r'\(', '（'),
    (r'\)', '）'),
    # 美元符号（LaTeX标记）
    (r'\$', ''),
]


def convert_to_tts_friendly(text: str) -> str:
    """
    将包含数学公式的文本转换为 TTS 友好的文本
    
    处理流程：
    1. 先去除 Markdown 格式符号
    2. 再将 LaTeX 数学符号转换为口语表达
    3. 最后清理空白
    
    Args:
        text: 原始文本（可能包含 Markdown 和 LaTeX 公式）
        
    Returns:
        TTS 友好的文本
    """
    # 第一步：去除 Markdown 符号
    result = strip_markdown_for_tts(text)
    
    # 第二步：应用数学符号到口语的转换规则
    for pattern, replacement in SYMBOL_REPLACEMENTS:
        result = re.sub(pattern, replacement, result)
    
    # 第三步：清理多余的空格
    result = re.sub(r'\s+', ' ', result)
    result = result.strip()
    
    return result


def process_narration_steps(narration_steps: List[str]) -> List[str]:
    """
    批量处理讲解步骤，转换为 TTS 友好格式
    
    Args:
        narration_steps: 原始讲解步骤列表
        
    Returns:
        处理后的讲解步骤列表
    """
    return [convert_to_tts_friendly(step) for step in narration_steps]

