"""API 路由"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse, Response
from typing import List, Dict
import os
from datetime import datetime
import json
from pathlib import Path

from app.models.schemas import (
    ProblemInput,
    SolutionResponse,
    NarrationResponse,
    PDFGenerationRequest,
    BatchProblemInput
)
from app.llm_providers.factory import create_llm_client
from app.llm_providers.base import LLMClient
from app.slides.pdf_export_playwright import generate_pdf_async, generate_pdf
from app.text.tts_friendly import convert_to_tts_friendly
from app.utils.text_utils import clean_problem_text
from app.utils.pdf_merge import merge_pdfs
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

router = APIRouter(prefix="/api", tags=["api"])


def get_llm_client() -> LLMClient:
    """依赖注入：获取 LLM 客户端"""
    return create_llm_client()


@router.post("/solve", response_model=SolutionResponse)
async def solve_problem(
    problem: ProblemInput,
    llm_client: LLMClient = Depends(get_llm_client)
):
    """
    解题接口：输入题目，返回结构化的解题步骤
    """
    try:
        # 基本输入验证
        if not problem.text or not problem.text.strip():
            raise HTTPException(status_code=400, detail="题目文本不能为空")
        
        if len(problem.text) > 5000:
            raise HTTPException(status_code=400, detail="题目文本过长（超过5000字符）")
        
        # 清理题目文本（规范化LaTeX转义等）
        cleaned_text = clean_problem_text(problem.text)
        
        meta = {
            "topic": problem.topic,
            "difficulty": problem.difficulty,
            "tags": problem.tags
        }
        
        steps = llm_client.solve(cleaned_text, meta)
        
        # 验证返回结果
        if not steps:
            raise HTTPException(status_code=500, detail="LLM 返回的解题步骤为空")
        
        return SolutionResponse(
            problem_text=cleaned_text,
            steps=steps,
            method=None
        )
    except HTTPException:
        raise
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=f"请求超时: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解题失败: {str(e)}")


@router.post("/narrate", response_model=NarrationResponse)
async def generate_narration(
    problem_text: str,
    solution_steps: List[dict],
    llm_client: LLMClient = Depends(get_llm_client)
):
    """
    生成讲解脚本接口：输入题目和解题步骤，返回 TTS 友好的讲解文本
    """
    try:
        from app.models.schemas import SolutionStep
        steps = [SolutionStep(**step) for step in solution_steps]
        
        meta = {}
        narration_steps = llm_client.narrate(problem_text, steps, meta)
        
        # 应用 TTS 友好转换
        for step in narration_steps:
            step.narration_text = convert_to_tts_friendly(step.narration_text)
        
        return NarrationResponse(
            problem_text=problem_text,
            steps=narration_steps
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成讲解失败: {str(e)}")


@router.post("/generate_pdf")
async def generate_pdf_endpoint(request: PDFGenerationRequest):
    """
    生成 PDF 接口：输入题目、解题步骤和讲解步骤，返回 PDF 文件
    """
    try:
        pdf_bytes = await generate_pdf_async(
            problem_text=request.problem_text,
            solution_steps=request.solution_steps,
            narration_steps=request.narration_steps
        )
        
        return StreamingResponse(
            pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=problem_solution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成PDF失败: {str(e)}")


def align_narration_to_solution(
    solution_steps: List,
    narration_steps: List,
) -> Dict[int, str]:
    """
    将讲解步骤对齐到解题步骤的 step_index
    
    Args:
        solution_steps: 解题步骤列表
        narration_steps: 讲解步骤列表（可能缺失、重复或乱序）
        
    Returns:
        字典 {step_index: aligned_narration_text}
    """
    from app.models.schemas import SolutionStep, NarrationStep
    
    # 构建 narration 的索引字典
    narration_dict = {}
    for narr in narration_steps:
        step_idx = narr.step_index
        if step_idx not in narration_dict:
            narration_dict[step_idx] = []
        narration_dict[step_idx].append(narr.narration_text)
    
    # 按 solution_steps 顺序对齐
    aligned = {}
    for step in solution_steps:
        step_idx = step.step_index
        if step_idx in narration_dict:
            # 合并同一 step_index 的多条讲解（用双换行分隔）
            aligned[step_idx] = '\n\n'.join(narration_dict[step_idx])
        else:
            # 缺失时用解题描述兜底（已经过 TTS 处理）
            aligned[step_idx] = convert_to_tts_friendly(step.description or step.title)
    
    return aligned


def save_narration_txt(
    timestamp: str,
    solution_steps: List,
    narration_steps: List,
) -> str:
    """
    将对齐后的讲解保存为 txt 文件
    
    Args:
        timestamp: 时间戳（用于文件命名）
        solution_steps: 解题步骤列表
        narration_steps: 讲解步骤列表
        
    Returns:
        保存的文件路径
    """
    os.makedirs("problems", exist_ok=True)
    
    filename = f"problems/problem_{timestamp}_narration.txt"
    
    # 对齐讲解到解题步骤
    aligned_narration = align_narration_to_solution(solution_steps, narration_steps)
    
    # 构建 txt 内容
    lines = []
    lines.append("=" * 80)
    lines.append("高等数学题目讲解脚本")
    lines.append(f"生成时间: {timestamp}")
    lines.append("=" * 80)
    lines.append("")
    
    for step in solution_steps:
        step_idx = step.step_index
        lines.append(f"【步骤 {step_idx}】{step.title}")
        lines.append("")
        if step_idx in aligned_narration:
            lines.append(aligned_narration[step_idx])
        lines.append("")
        lines.append("-" * 80)
        lines.append("")
    
    # 写入文件（UTF-8 编码）
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return filename


@router.post("/full_pipeline")
async def full_pipeline(
    problem: ProblemInput,
    llm_client: LLMClient = Depends(get_llm_client)
):
    """
    完整流水线接口：一键完成解题、生成讲解、生成PDF、导出讲解txt
    """
    try:
        # 基本输入验证
        if not problem.text or not problem.text.strip():
            raise HTTPException(status_code=400, detail="题目文本不能为空")
        
        # 清理题目文本
        cleaned_text = clean_problem_text(problem.text)
        
        # 生成统一的时间戳（用于文件命名）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 步骤1：解题
        meta = {
            "topic": problem.topic,
            "difficulty": problem.difficulty,
            "tags": problem.tags
        }
        
        try:
            solution_steps = llm_client.solve(cleaned_text, meta)
            if not solution_steps:
                raise HTTPException(status_code=500, detail="解题步骤生成失败")
        except TimeoutError as e:
            raise HTTPException(status_code=504, detail=f"解题步骤生成超时: {str(e)}")
        
        # 步骤2：生成讲解
        try:
            narration_steps = llm_client.narrate(cleaned_text, solution_steps, meta)
            if not narration_steps:
                # 如果没有生成讲解，使用解题步骤作为备选
                from app.models.schemas import NarrationStep
                narration_steps = [
                    NarrationStep(
                        step_index=s.step_index,
                        narration_text=s.description
                    )
                    for s in solution_steps
                ]
        except TimeoutError as e:
            raise HTTPException(status_code=504, detail=f"讲解生成超时: {str(e)}")
        
        # 应用 TTS 友好转换（去除 Markdown + 数学符号口语化）
        for step in narration_steps:
            step.narration_text = convert_to_tts_friendly(step.narration_text)
        
        # 步骤3：保存讲解 txt（按 step_index 对齐）
        try:
            save_narration_txt(timestamp, solution_steps, narration_steps)
        except Exception as e:
            # 记录保存失败不影响主流程，但记录警告
            import logging
            logging.warning(f"保存讲解 txt 失败: {e}")
        
        # 步骤4：生成 PDF（不包含 narration）
        try:
            pdf_bytes = await generate_pdf_async(
                problem_text=cleaned_text,
                solution_steps=solution_steps,
                narration_steps=None  # 明确传 None，不渲染 narration
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")
        
        # 步骤5：保存题目记录（JSON）
        try:
            save_problem_record_with_timestamp(
                timestamp, cleaned_text, solution_steps, narration_steps, meta
            )
        except Exception:
            # 记录保存失败不影响主流程
            pass
        
        # 返回 PDF，并在响应头中携带 timestamp
        return StreamingResponse(
            pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=problem_{timestamp}.pdf",
                "X-Narration-Timestamp": timestamp  # 前端用此 timestamp 下载 txt
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流水线处理失败: {str(e)}")


def _process_single_problem(
    problem: ProblemInput,
    llm_client: LLMClient
) -> dict:
    """处理单个题目（用于并发执行）"""
    try:
        meta = {
            "topic": problem.topic,
            "difficulty": problem.difficulty,
            "tags": problem.tags
        }
        
        # 解题
        solution_steps = llm_client.solve(problem.text, meta)
        
        # 生成讲解
        narration_steps = llm_client.narrate(problem.text, solution_steps, meta)
        
        # TTS 友好转换
        for step in narration_steps:
            step.narration_text = convert_to_tts_friendly(step.narration_text)
        
        # 生成 PDF（批处理中使用同步版本）
        pdf_bytes = generate_pdf(
            problem_text=problem.text,
            solution_steps=solution_steps,
            narration_steps=narration_steps
        )
        
        # 保存记录（生成新的 timestamp）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_problem_record_with_timestamp(timestamp, problem.text, solution_steps, narration_steps, meta)
        
        return {
            "problem_text": problem.text,
            "solution_steps": [s.dict() if hasattr(s, 'dict') else s for s in solution_steps],
            "narration_steps": [s.dict() if hasattr(s, 'dict') else s for s in narration_steps],
            "pdf_bytes": pdf_bytes,
            "success": True
        }
    except Exception as e:
        return {
            "problem_text": problem.text,
            "error": str(e),
            "success": False
        }


@router.get("/download_narration/{timestamp}")
async def download_narration(timestamp: str):
    """
    下载讲解脚本 txt 文件
    
    Args:
        timestamp: 题目生成时的时间戳（格式：YYYYMMDD_HHMMSS）
        
    Returns:
        讲解脚本 txt 文件
    """
    try:
        # 验证 timestamp 格式（防止路径遍历攻击）
        import re
        if not re.match(r'^\d{8}_\d{6}$', timestamp):
            raise HTTPException(status_code=400, detail="无效的时间戳格式")
        
        # 构建文件路径
        filename = f"problems/problem_{timestamp}_narration.txt"
        filepath = Path(filename)
        
        # 检查文件是否存在
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="讲解脚本文件不存在")
        
        # 返回文件下载
        return FileResponse(
            path=str(filepath),
            media_type="text/plain; charset=utf-8",
            filename=f"narration_{timestamp}.txt",
            headers={
                "Content-Disposition": f"attachment; filename=narration_{timestamp}.txt"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载讲解脚本失败: {str(e)}")


@router.post("/batch_full_pipeline")
async def batch_full_pipeline(
    batch_input: BatchProblemInput,
    llm_client: LLMClient = Depends(get_llm_client),
    max_workers: int = 3
):
    """
    批量处理接口：处理多道题目，生成多个PDF或合并PDF
    
    Args:
        batch_input: 批量题目输入
        llm_client: LLM 客户端
        max_workers: 最大并发数（默认3，避免触发API限流）
    """
    try:
        # 限制批量大小
        if len(batch_input.problems) > 50:
            raise HTTPException(
                status_code=400,
                detail="批量处理题目数量不能超过50道"
            )
        
        results = []
        pdf_bytes_list = []
        
        # 使用线程池并发处理（注意：LLM API调用是IO密集型）
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                loop.run_in_executor(
                    executor,
                    _process_single_problem,
                    problem,
                    llm_client
                )
                for problem in batch_input.problems
            ]
            
            for future in as_completed(futures):
                result = await future
                results.append(result)
                if result.get("success") and "pdf_bytes" in result:
                    pdf_bytes_list.append(result["pdf_bytes"])
        
        # 如果要求合并PDF
        if batch_input.merge_pdf:
            if not pdf_bytes_list:
                raise HTTPException(
                    status_code=400,
                    detail="没有成功生成的PDF可以合并"
                )
            
            merged_pdf = merge_pdfs(pdf_bytes_list)
            
            return StreamingResponse(
                merged_pdf,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=batch_problems_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                }
            )
        else:
            # 返回处理结果摘要
            return {
                "total": len(batch_input.problems),
                "success": len([r for r in results if r.get("success")]),
                "failed": len([r for r in results if not r.get("success")]),
                "results": [
                    {k: v for k, v in r.items() if k != "pdf_bytes"}  # 移除PDF字节流，只返回元数据
                    for r in results
                ]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量处理失败: {str(e)}")


def save_problem_record(
    problem_text: str,
    solution_steps: List,
    narration_steps: List,
    meta: dict
):
    """保存题目记录到本地文件（自动生成 timestamp）"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_problem_record_with_timestamp(timestamp, problem_text, solution_steps, narration_steps, meta)


def save_problem_record_with_timestamp(
    timestamp: str,
    problem_text: str,
    solution_steps: List,
    narration_steps: List,
    meta: dict
):
    """保存题目记录到本地文件（使用指定的 timestamp）"""
    os.makedirs("problems", exist_ok=True)
    
    filename = f"problems/problem_{timestamp}.json"
    
    record = {
        "timestamp": timestamp,
        "problem_text": problem_text,
        "meta": meta,
        "solution_steps": [step.dict() if hasattr(step, 'dict') else step for step in solution_steps],
        "narration_steps": [step.dict() if hasattr(step, 'dict') else step for step in narration_steps]
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

