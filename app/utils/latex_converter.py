"""LaTeX 到 MathML 转换工具"""
import logging
import re
from typing import Optional
from html import escape

logger = logging.getLogger(__name__)


def process_text_with_latex(text: str) -> str:
    """
    处理包含 LaTeX 公式的混合文本，将所有 LaTeX 公式转换为 MathML
    
    支持:
    - 行内公式: $...$
    - 块级公式: $$...$$
    - \[...\] 和 \(...\) 形式
    - 无分隔符的裸 LaTeX 命令 (如 \int, \frac 等)
    - 换行符: \n 转换为 <br>
    
    Args:
        text: 包含 LaTeX 公式的文本
        
    Returns:
        HTML 字符串，其中 LaTeX 已转换为 MathML
    """
    if not text or not text.strip():
        return ""
    
    # 首先处理换行符
    text = text.replace('\\n', '\n')
    
    # 使用正则表达式找到所有 LaTeX 公式
    # 先处理块级公式 $$...$$（避免被行内公式匹配）
    def replace_block_latex(match):
        latex = match.group(1)
        mathml = latex_to_mathml(latex, display_block=True)
        return mathml
    
    def replace_inline_latex(match):
        latex = match.group(1)
        mathml = latex_to_mathml(latex, display_block=False)
        return mathml
    
    # 处理块级公式 $$...$$
    text = re.sub(r'\$\$([^$]+?)\$\$', replace_block_latex, text, flags=re.DOTALL)
    
    # 处理行内公式 $...$（避免匹配已处理的块级公式）
    text = re.sub(r'(?<!\$)\$([^$]+?)\$(?!\$)', replace_inline_latex, text)
    
    # 处理 \[...\] 块级公式
    text = re.sub(r'\\\[(.+?)\\\]', replace_block_latex, text, flags=re.DOTALL)
    
    # 处理 \(...\) 行内公式
    text = re.sub(r'\\\((.+?)\\\)', replace_inline_latex, text, flags=re.DOTALL)
    
    # 处理无分隔符的裸 LaTeX 公式（检测常见的 LaTeX 命令）
    text = _process_bare_latex(text)
    
    # 处理 Markdown 粗体 **text** -> 保留文本内容（避免残留符号）
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)

    # 将剩余的换行符转换为 <br>
    text = text.replace('\n', '<br>\n')
    
    return text


def _process_bare_latex(text: str) -> str:
    """
    处理无分隔符的裸 LaTeX 公式
    
    对两种情况做处理：
    1) 文本完全是 LaTeX 公式 -> 整体转为 MathML（块级）
    2) 文本包含普通文字 + 裸 LaTeX 公式 -> 仅替换第一次出现的 LaTeX 子串为行内 MathML，保留前后文字与空格
    """
    latex_commands = [
        r'\\int', r'\\frac', r'\\sum', r'\\prod', r'\\lim', r'\\infty',
        r'\\sqrt', r'\\partial', r'\\nabla', r'\\alpha', r'\\beta', r'\\gamma',
        r'\\theta', r'\\pi', r'\\omega', r'\\sin', r'\\cos', r'\\tan',
        r'\\log', r'\\ln', r'\\exp', r'\\mathrm', r'\\mathbf', r'\\mathcal',
        r'\\cdot', r'\\times', r'\\div', r'\\pm', r'\\mp', r'\\leq', r'\\geq',
        r'\\neq', r'\\approx', r'\\equiv', r'\\subset', r'\\supset',
        r'\\in', r'\\notin', r'\\cup', r'\\cap', r'\\forall', r'\\exists',
        r'\\rightarrow', r'\\leftarrow', r'\\Rightarrow', r'\\Leftarrow',
        r'\\begin\{', r'\\end\{',
    ]
    latex_pattern = '|'.join(latex_commands)

    if not re.search(latex_pattern, text):
        return text

    stripped = text.strip()

    # 情况1：整体是 LaTeX
    if re.match(r'^\\[a-zA-Z]+', stripped) and not re.search(r'[A-Za-z]{2,}\s+[A-Za-z]{2,}', stripped):
        try:
            mathml = latex_to_mathml(stripped, display_block=True)
            if mathml and '<math' in mathml:
                return mathml
        except Exception as e:
            logger.warning(f"裸 LaTeX 转换失败: {e}")
        return text

    # 情况2：混合文本，仅替换第一个裸 LaTeX 片段为行内 MathML
    first_cmd = re.search(latex_pattern, text)
    if not first_cmd:
        return text
    start = first_cmd.start()

    # 如果裸命令前紧跟的是一个数字系数（如 "2\\sqrt{3}"），把系数一起纳入 MathML，
    # 否则浏览器可能在 "2" 和 <math> 之间断行。
    prefix = text[:start]
    coeff_match = re.search(r'([+\-]?\s*\d+(?:\.\d+)?)\s*$', prefix)
    if coeff_match:
        # #region agent log
        try:
            import json, time as _t
            with open(r"e:\sustech_digital_human_education\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "formula-debug",
                    "hypothesisId": "F4",
                    "location": "latex_converter._process_bare_latex:merge_coeff",
                    "message": "merged numeric coeff into latex_part",
                    "data": {"prefix_tail": prefix[max(0, len(prefix)-30):], "coeff": coeff_match.group(1)},
                    "timestamp": int(_t.time()*1000)
                }) + "\n")
        except Exception:
            pass
        # #endregion
        start = coeff_match.start()
        prefix = text[:start]
    latex_part = text[start:]

    try:
        mathml = latex_to_mathml(latex_part, display_block=False)
        if mathml and '<math' in mathml:
            return prefix + mathml
    except Exception as e:
        logger.warning(f"裸 LaTeX 片段转换失败: {e}")

    return text


def _is_primarily_latex(text: str) -> bool:
    """
    判断文本是否主要由 LaTeX 数学表达式组成
    """
    # 计算 LaTeX 相关字符的比例
    latex_chars = 0
    total_chars = len(text)
    
    if total_chars == 0:
        return False
    
    # 统计常见的 LaTeX 字符
    for char in text:
        if char in '\\{}^_':
            latex_chars += 1
    
    # 统计 LaTeX 命令
    commands = re.findall(r'\\[a-zA-Z]+', text)
    latex_chars += sum(len(cmd) for cmd in commands)
    
    # 如果 LaTeX 字符占比超过 15%，认为主要是 LaTeX
    return latex_chars / total_chars > 0.15


def _preprocess_latex(latex_str: str) -> str:
    """
    预处理 LaTeX 字符串，将一些 latex2mathml 不支持的命令转换为支持的格式
    """
    # 将 LaTeX 的换行命令 \\ 转为空格，避免在 MathML 中被强制换行
    latex_str = re.sub(r'\\\\(?![a-zA-Z])', ' ', latex_str)

    # \mathrm{d} -> {\rm d} 或直接用 d（积分微分符号）
    latex_str = re.sub(r'\\mathrm\{([^}]+)\}', r'{\rm \1}', latex_str)
    
    # \text{...} -> \textrm{...} 或直接处理
    latex_str = re.sub(r'\\text\{([^}]+)\}', r'{\rm \1}', latex_str)
    
    # \operatorname{...} -> 直接使用文本
    latex_str = re.sub(r'\\operatorname\{([^}]+)\}', r'{\rm \1}', latex_str)
    
    # \,（小空格）-> 普通空格
    latex_str = latex_str.replace('\\,', ' ')
    
    # \; \: \!（各种空格）-> 空格或空
    latex_str = latex_str.replace('\\;', ' ')
    latex_str = latex_str.replace('\\:', ' ')
    latex_str = latex_str.replace('\\!', '')
    
    return latex_str


def latex_to_mathml(latex_str: str, display_block: bool = True) -> str:
    """
    将 LaTeX 数学公式转换为 MathML 格式
    
    Args:
        latex_str: LaTeX 格式的数学公式字符串
        display_block: 是否为块级显示（居中），False 则为行内显示
        
    Returns:
        MathML 格式的字符串，如果转换失败则返回带样式的纯文本
    """
    if not latex_str or not latex_str.strip():
        return ""
    
    try:
        from latex2mathml.converter import convert
        
        # 清理 LaTeX 字符串 - 去除美元符号
        latex_clean = latex_str.strip()
        
        # 去除 $$ 或 $ 符号（但保留LaTeX命令中的\$）
        # 处理 $$...$$
        if latex_clean.startswith('$$') and latex_clean.endswith('$$'):
            latex_clean = latex_clean[2:-2].strip()
        # 处理 $...$
        elif latex_clean.startswith('$') and latex_clean.endswith('$'):
            latex_clean = latex_clean[1:-1].strip()
        # 处理 \[...\]
        elif latex_clean.startswith('\\[') and latex_clean.endswith('\\]'):
            latex_clean = latex_clean[2:-2].strip()
        # 处理 \(...\)
        elif latex_clean.startswith('\\(') and latex_clean.endswith('\\)'):
            latex_clean = latex_clean[2:-2].strip()
        
        # 如果清理后是空的，返回空
        if not latex_clean:
            return ""
        
        # 预处理 LaTeX 命令
        latex_clean = _preprocess_latex(latex_clean)
#region agent log
        try:
            import json, time as _t
            with open(r"e:\sustech_digital_human_education\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "formula-debug",
                    "hypothesisId": "F3",
                    "location": "latex_converter.latex_to_mathml:pre_convert",
                    "message": "cleaned latex",
                    "data": {"src": latex_clean[:200], "display_block": display_block},
                    "timestamp": int(_t.time()*1000)
                }) + "\n")
        except Exception:
            pass
#endregion
        
        # 转换为 MathML（不需要添加美元符号，直接传递纯LaTeX）
        mathml = convert(latex_clean)
        
        # 规范 display 属性：避免出现重复 display="..."（无效/不确定行为）
        mathml = re.sub(r'\sdisplay="(?:inline|block)"', '', mathml, count=1)

        # 添加样式属性
        if mathml.startswith('<math'):
            if display_block:
                # 块级显示：居中
                mathml = mathml.replace('<math', '<math display="block" style="margin: 15px auto; font-size: 18px;"', 1)
            else:
                # 行内显示
                mathml = mathml.replace('<math', '<math display="inline" style="font-size: 16px; vertical-align: middle;"', 1)

        # #region agent log
        try:
            import json, time as _t
            with open(r"e:\sustech_digital_human_education\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "formula-debug",
                    "hypothesisId": "F5",
                    "location": "latex_converter.latex_to_mathml:post_convert",
                    "message": "mathml head",
                    "data": {"head": mathml[:160], "display_block": display_block},
                    "timestamp": int(_t.time()*1000)
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        return mathml
        
    except ImportError as e:
        logger.error(f"latex2mathml 库未安装: {e}")
        return _fallback_latex_display(latex_str, display_block)
    except Exception as e:
        logger.warning(f"LaTeX 转换为 MathML 失败: {latex_str[:50]}... 错误: {e}")
        return _fallback_latex_display(latex_str, display_block)


def _fallback_latex_display(latex_str: str, display_block: bool = True) -> str:
    """
    降级处理：当转换失败时，使用格式化的纯文本显示
    
    Args:
        latex_str: 原始 LaTeX 字符串
        display_block: 是否为块级显示
        
    Returns:
        HTML 格式的字符串
    """
    escaped = escape(latex_str)
    style_block = "background: #f5f5f5; padding: 12px; margin: 10px 0; border-left: 4px solid #ccc; font-family: 'Courier New', monospace; font-size: 15px; color: #333; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word;"
    style_inline = "background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: monospace;"
    if display_block:
        return f'<div style="{style_block}">{escaped}</div>'
    else:
        return f'<code style="{style_inline}">{escaped}</code>'


def batch_convert_latex(formulas: list[str]) -> list[str]:
    """
    批量转换 LaTeX 公式到 MathML
    
    Args:
        formulas: LaTeX 公式列表
        
    Returns:
        MathML 字符串列表
    """
    return [latex_to_mathml(formula) for formula in formulas]

