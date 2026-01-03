"""LaTeX 到 MathML 转换工具"""
import logging
from typing import Optional
from html import escape

logger = logging.getLogger(__name__)


def latex_to_mathml(latex_str: str) -> str:
    """
    将 LaTeX 数学公式转换为 MathML 格式
    
    Args:
        latex_str: LaTeX 格式的数学公式字符串
        
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
        
        # 转换为 MathML（不需要添加美元符号，直接传递纯LaTeX）
        mathml = convert(latex_clean)
        
        # 添加样式属性使其居中显示
        if mathml.startswith('<math'):
            mathml = mathml.replace('<math', '<math display="block" style="margin: 15px auto; font-size: 18px;"', 1)
        
        return mathml
        
    except ImportError as e:
        logger.error(f"latex2mathml 库未安装: {e}")
        return _fallback_latex_display(latex_str)
    except Exception as e:
        logger.warning(f"LaTeX 转换为 MathML 失败: {latex_str[:50]}... 错误: {e}")
        return _fallback_latex_display(latex_str)


def _fallback_latex_display(latex_str: str) -> str:
    """
    降级处理：当转换失败时，使用格式化的纯文本显示
    
    Args:
        latex_str: 原始 LaTeX 字符串
        
    Returns:
        HTML 格式的字符串
    """
    escaped = escape(latex_str)
    return f'''
    <div style="background: #fff3cd; padding: 15px; margin: 15px 0; 
                border-left: 4px solid #ffc107; font-family: 'Courier New', monospace; 
                font-size: 16px; color: #856404; border-radius: 4px;">
        <strong>⚠ 公式渲染失败，显示原始LaTeX：</strong><br>
        <code style="display: block; margin-top: 8px; white-space: pre-wrap; word-wrap: break-word;">
        {escaped}
        </code>
    </div>
    '''


def batch_convert_latex(formulas: list[str]) -> list[str]:
    """
    批量转换 LaTeX 公式到 MathML
    
    Args:
        formulas: LaTeX 公式列表
        
    Returns:
        MathML 字符串列表
    """
    return [latex_to_mathml(formula) for formula in formulas]

