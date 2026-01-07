"""API 路由"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, HTMLResponse
from typing import List
import os
from datetime import datetime
import json

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


@router.post("/full_pipeline")
async def full_pipeline(
    problem: ProblemInput,
    llm_client: LLMClient = Depends(get_llm_client)
):
    """
    完整流水线接口：一键完成解题、生成讲解、生成PDF
    """
    try:
        # 基本输入验证
        if not problem.text or not problem.text.strip():
            raise HTTPException(status_code=400, detail="题目文本不能为空")
        
        # 清理题目文本
        cleaned_text = clean_problem_text(problem.text)
        
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
        
        # 应用 TTS 友好转换
        for step in narration_steps:
            step.narration_text = convert_to_tts_friendly(step.narration_text)
        
        # 步骤3：生成 PDF
        try:
            pdf_bytes = await generate_pdf_async(
                problem_text=cleaned_text,
                solution_steps=solution_steps,
                narration_steps=narration_steps
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")
        
        # 保存题目记录（可选）
        try:
            save_problem_record(cleaned_text, solution_steps, narration_steps, meta)
        except Exception:
            # 记录保存失败不影响主流程
            pass
        
        return StreamingResponse(
            pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=problem_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
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
        
        # 保存记录
        save_problem_record(problem.text, solution_steps, narration_steps, meta)
        
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
    """保存题目记录到本地文件"""
    os.makedirs("problems", exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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

