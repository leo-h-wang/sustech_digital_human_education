"""文本处理工具函数"""
import re


def normalize_latex_escapes(text: str) -> str:
    """
    规范化LaTeX转义符号
    
    将过度转义的反斜杠（如 \\\\ 变成 \\）标准化。
    主要处理用户输入时多次转义的情况。
    
    Args:
        text: 原始文本
        
    Returns:
        规范化后的文本
    """
    if not text:
        return text
    
    # 检查是否有过度转义（连续4个或更多反斜杠）
    if '\\\\\\\\' in text:
        # 将4个反斜杠替换为2个（JSON中2个反斜杠代表1个实际反斜杠）
        # 这样在LaTeX中就是正常的反斜杠
        text = re.sub(r'\\\\\\\\+', r'\\\\', text)
        
    return text


def clean_problem_text(text: str) -> str:
    """
    清理题目文本
    
    Args:
        text: 原始题目文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return text
    
    # 去除首尾空白
    text = text.strip()
    
    # 规范化LaTeX转义
    text = normalize_latex_escapes(text)
    
    # 去除多余的空行（保留单个换行）
    text = re.sub(r'\n\n+', '\n\n', text)
    
    return text

