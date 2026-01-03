"""PDF 导出模块 - 使用 Playwright（浏览器渲染）"""
from io import BytesIO
from typing import Optional, List
import logging
import tempfile
import os
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.models.schemas import SolutionStep, NarrationStep
from app.slides.generator import generate_slides_html_with_formulas

logger = logging.getLogger(__name__)

# 全局线程池，用于在异步环境中运行同步Playwright代码
_thread_pool = ThreadPoolExecutor(max_workers=3)


def _generate_pdf_sync(
    problem_text: str,
    solution_steps: list[SolutionStep],
    narration_steps: Optional[list[NarrationStep]] = None,
    output_path: Optional[str] = None
) -> BytesIO:
    """
    使用 Playwright 生成 PDF（通过浏览器渲染）
    
    Args:
        problem_text: 题目文本
        solution_steps: 解题步骤列表
        narration_steps: 讲解步骤列表（可选）
        output_path: 输出文件路径（可选）
        
    Returns:
        PDF 文件的字节流
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        logger.error(f"Playwright 未安装: {e}")
        raise ImportError(
            "Playwright 库未安装。请运行:\n"
            "  uv pip install playwright\n"
            "  uv run playwright install chromium\n"
        ) from e
    
    logger.info(f"开始生成PDF（Playwright方案）- 题目: {problem_text[:30]}...")
    logger.info(f"解题步骤数: {len(solution_steps)}")
    
    # 生成带有 MathML 公式的 HTML
    try:
        html_content = generate_slides_html_with_formulas(
            problem_text=problem_text,
            solution_steps=solution_steps,
            narration_steps=narration_steps
        )
        logger.info("HTML 内容生成成功")
    except Exception as e:
        logger.error(f"生成 HTML 内容失败: {e}")
        raise
    
    # 使用 Playwright 渲染 PDF
    try:
        with sync_playwright() as p:
            # 启动浏览器（无头模式）
            logger.info("启动 Chromium 浏览器...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 创建临时HTML文件
            with tempfile.NamedTemporaryFile(
                mode='w', 
                encoding='utf-8', 
                suffix='.html', 
                delete=False
            ) as f:
                f.write(html_content)
                temp_html_path = f.name
            
            try:
                # 加载HTML
                logger.info(f"加载 HTML 文件: {temp_html_path}")
                page.goto(f'file:///{temp_html_path}')
                
                # 等待页面加载完成
                page.wait_for_load_state('networkidle')
                logger.info("页面加载完成")
                
                # 生成PDF
                logger.info("开始渲染 PDF...")
                pdf_bytes_data = page.pdf(
                    format='A4',
                    landscape=True,
                    margin={
                        'top': '2cm',
                        'right': '2cm',
                        'bottom': '2cm',
                        'left': '2cm'
                    },
                    print_background=True
                )
                
                logger.info(f"PDF 渲染成功，大小: {len(pdf_bytes_data) / 1024:.2f} KB")
                
            finally:
                # 清理临时文件
                browser.close()
                try:
                    os.unlink(temp_html_path)
                except:
                    pass
        
        # 转换为 BytesIO
        pdf_bytes = BytesIO(pdf_bytes_data)
        
        # 如果指定了输出路径，保存到文件
        if output_path:
            try:
                with open(output_path, 'wb') as f:
                    f.write(pdf_bytes_data)
                logger.info(f"PDF 已保存到: {output_path}")
            except Exception as e:
                logger.error(f"保存 PDF 文件失败: {e}")
                raise
        
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Playwright 渲染失败: {e}")
        raise


async def generate_pdf_with_playwright_async(
    problem_text: str,
    solution_steps: list[SolutionStep],
    narration_steps: Optional[list[NarrationStep]] = None,
    output_path: Optional[str] = None
) -> BytesIO:
    """
    异步版本：使用 Playwright 生成 PDF（在线程池中运行同步代码）
    
    Args:
        problem_text: 题目文本
        solution_steps: 解题步骤列表
        narration_steps: 讲解步骤列表（可选）
        output_path: 输出文件路径（可选）
        
    Returns:
        PDF 文件的字节流
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _thread_pool,
        _generate_pdf_sync,
        problem_text,
        solution_steps,
        narration_steps,
        output_path
    )


def generate_pdf_with_playwright(
    problem_text: str,
    solution_steps: list[SolutionStep],
    narration_steps: Optional[list[NarrationStep]] = None,
    output_path: Optional[str] = None
) -> BytesIO:
    """
    同步版本：使用 Playwright 生成 PDF
    """
    return _generate_pdf_sync(problem_text, solution_steps, narration_steps, output_path)


# 为了保持兼容性，创建一个wrapper
def generate_pdf(
    problem_text: str,
    solution_steps: list[SolutionStep],
    narration_steps: Optional[list[NarrationStep]] = None,
    output_path: Optional[str] = None
) -> BytesIO:
    """
    生成 PDF - 自动选择可用的方法（同步版本）
    """
    # 首先尝试 Playwright（推荐）
    try:
        return generate_pdf_with_playwright(
            problem_text, solution_steps, narration_steps, output_path
        )
    except ImportError as e:
        logger.warning(f"Playwright 不可用，尝试 WeasyPrint: {e}")
        
        # 降级到 WeasyPrint
        try:
            from app.slides.pdf_export import generate_pdf as weasyprint_generate
            return weasyprint_generate(
                problem_text, solution_steps, narration_steps, output_path
            )
        except Exception as we:
            logger.error(f"WeasyPrint 也失败: {we}")
            raise RuntimeError(
                "无法生成PDF。请安装 Playwright:\n"
                "  uv pip install playwright\n"
                "  uv run playwright install chromium\n"
            ) from e


async def generate_pdf_async(
    problem_text: str,
    solution_steps: list[SolutionStep],
    narration_steps: Optional[list[NarrationStep]] = None,
    output_path: Optional[str] = None
) -> BytesIO:
    """
    生成 PDF - 自动选择可用的方法（异步版本，用于FastAPI）
    """
    # 首先尝试 Playwright（推荐）
    try:
        return await generate_pdf_with_playwright_async(
            problem_text, solution_steps, narration_steps, output_path
        )
    except ImportError as e:
        logger.warning(f"Playwright 不可用，尝试 WeasyPrint: {e}")
        
        # 降级到 WeasyPrint（在线程池中运行）
        try:
            from app.slides.pdf_export import generate_pdf as weasyprint_generate
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                _thread_pool,
                weasyprint_generate,
                problem_text,
                solution_steps,
                narration_steps,
                output_path
            )
        except Exception as we:
            logger.error(f"WeasyPrint 也失败: {we}")
            raise RuntimeError(
                "无法生成PDF。请安装 Playwright:\n"
                "  uv pip install playwright\n"
                "  uv run playwright install chromium\n"
            ) from e

