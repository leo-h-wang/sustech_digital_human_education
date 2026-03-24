"""API 路由"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from typing import List, Dict
import os
from datetime import datetime
import json
from pathlib import Path

from app.models.schemas import (
    ProblemInput,
    SolutionResponse,
    NarrationResponse,
    ManimPipelineRequest,
    ManimPipelineResponse,
)
from app.llm_providers.factory import create_llm_client
from app.llm_providers.base import LLMClient
from app.slides.gamma_export import GammaGenerator
from app.text.tts_friendly import convert_to_tts_friendly
from app.utils.text_utils import clean_problem_text

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
        if not problem.text or not problem.text.strip():
            raise HTTPException(status_code=400, detail="题目文本不能为空")
        
        if len(problem.text) > 5000:
            raise HTTPException(status_code=400, detail="题目文本过长（超过5000字符）")
        
        cleaned_text = clean_problem_text(problem.text)
        
        meta = {
            "topic": problem.topic,
            "difficulty": problem.difficulty,
            "tags": problem.tags
        }
        
        steps = llm_client.solve(cleaned_text, meta)
        
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
        
        for step in narration_steps:
            step.narration_text = convert_to_tts_friendly(step.narration_text)
        
        return NarrationResponse(
            problem_text=problem_text,
            steps=narration_steps
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成讲解失败: {str(e)}")


def align_narration_to_solution(
    solution_steps: List,
    narration_steps: List,
) -> Dict[int, str]:
    """
    将讲解步骤对齐到解题步骤的 step_index

    Returns:
        字典 {step_index: aligned_narration_text}
    """
    narration_dict = {}
    for narr in narration_steps:
        step_idx = narr.step_index
        if step_idx not in narration_dict:
            narration_dict[step_idx] = []
        narration_dict[step_idx].append(narr.narration_text)
    
    aligned = {}
    for step in solution_steps:
        step_idx = step.step_index
        if step_idx in narration_dict:
            aligned[step_idx] = '\n\n'.join(narration_dict[step_idx])
        else:
            aligned[step_idx] = convert_to_tts_friendly(step.description or step.title)

    for step_idx, texts in narration_dict.items():
        if step_idx not in aligned:
            aligned[step_idx] = '\n\n'.join(texts)
    
    return aligned


def _clean_narration_text(text: str) -> str:
    """
    Sanitize narration text: if the text looks like a JSON array/object leaked from
    the LLM, try to extract narration_text values from it.
    """
    stripped = text.strip()
    if not (stripped.startswith('[') or stripped.startswith('{')):
        return text
    try:
        import json as _json
        data = _json.loads(stripped)
        if isinstance(data, list):
            parts = []
            for item in data:
                if isinstance(item, dict) and 'narration_text' in item:
                    parts.append(item['narration_text'])
            if parts:
                return '\n\n'.join(parts)
        if isinstance(data, dict) and 'narration_text' in data:
            return data['narration_text']
    except Exception:
        pass
    return text


def save_narration_txt(
    timestamp: str,
    solution_steps: List,
    narration_steps: List,
) -> str:
    """
    将对齐后的讲解保存为 txt 文件

    Returns:
        保存的文件路径
    """
    os.makedirs("problems", exist_ok=True)
    
    filename = f"problems/problem_{timestamp}_narration.txt"
    
    aligned_narration = align_narration_to_solution(solution_steps, narration_steps)
    
    lines = []
    lines.append("=" * 80)
    lines.append("高等数学题目讲解脚本")
    lines.append(f"生成时间: {timestamp}")
    lines.append("=" * 80)
    lines.append("")
    
    solution_indices = [step.step_index for step in solution_steps]
    extra_indices = sorted([idx for idx in aligned_narration.keys() if idx not in solution_indices])
    ordered_indices = solution_indices + extra_indices

    step_title_map = {step.step_index: step.title for step in solution_steps}
    for step_idx in ordered_indices:
        title = step_title_map.get(step_idx, "补充讲解")
        lines.append(f"【步骤 {step_idx}】{title}")
        lines.append("")
        if step_idx in aligned_narration:
            lines.append(_clean_narration_text(aligned_narration[step_idx]))
        lines.append("")
        lines.append("-" * 80)
        lines.append("")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return filename


@router.post("/full_pipeline")
async def full_pipeline(
    problem: ProblemInput,
    format: str = "pptx",
    llm_client: LLMClient = Depends(get_llm_client)
):
    """
    完整流水线接口：一键完成解题、生成讲解、生成 Gamma PPT/PDF 链接、导出讲解txt
    """
    try:
        if not problem.text or not problem.text.strip():
            raise HTTPException(status_code=400, detail="题目文本不能为空")
        
        cleaned_text = clean_problem_text(problem.text)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
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
        
        try:
            narration_steps = llm_client.narrate(cleaned_text, solution_steps, meta)
            if not narration_steps:
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
        
        for step in narration_steps:
            step.narration_text = convert_to_tts_friendly(step.narration_text)
            if not step.narration_text.strip():
                matching = next((s for s in solution_steps if s.step_index == step.step_index), None)
                step.narration_text = convert_to_tts_friendly(
                    (matching.description if matching else "") or (matching.title if matching else "") or "（讲解缺失）"
                )
        
        try:
            save_narration_txt(timestamp, solution_steps, narration_steps)
        except Exception as e:
            import logging
            logging.warning(f"保存讲解 txt 失败: {e}")
        
        format_lower = format.strip().lower()
        if format_lower not in {"pdf", "pptx"}:
            raise HTTPException(status_code=400, detail="format 只支持 pdf 或 pptx")

        try:
            gamma_generator = GammaGenerator()
            steps_payload = []
            for step in solution_steps:
                content_parts = []
                if step.description:
                    content_parts.append(step.description)
                if step.formula_latex:
                    content_parts.append(step.formula_latex)
                content = "\n\n".join(content_parts)
                steps_payload.append({
                    "title": step.title or f"Step {step.step_index}",
                    "content": content
                })

            file_url = await gamma_generator.generate_slides_from_steps(
                problem_text=cleaned_text,
                steps=steps_payload,
                export_as=format_lower,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gamma 生成失败: {str(e)}")
        
        try:
            save_problem_record_with_timestamp(
                timestamp, cleaned_text, solution_steps, narration_steps, meta
            )
        except Exception:
            pass
        
        return {
            "gamma_url": None,
            "pptx_url": file_url if format_lower == "pptx" else None,
            "pdf_url": file_url if format_lower == "pdf" else None,
            "narration_timestamp": timestamp
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流水线处理失败: {str(e)}")


@router.post("/retry_narration")
async def retry_narration(
    file: UploadFile = File(...),
    llm_client: LLMClient = Depends(get_llm_client)
):
    """
    重新生成讲解脚本：上传之前的 problem JSON 文件，重新生成讲解 txt
    """
    try:
        content = await file.read()
        record = json.loads(content.decode('utf-8'))
        
        problem_text = record.get("problem_text", "")
        if not problem_text:
            raise HTTPException(status_code=400, detail="JSON 文件中缺少 problem_text")
        
        from app.models.schemas import SolutionStep, NarrationStep
        raw_steps = record.get("solution_steps", [])
        solution_steps = [SolutionStep(**s) for s in raw_steps]
        
        if not solution_steps:
            raise HTTPException(status_code=400, detail="JSON 文件中缺少 solution_steps")
        
        meta = record.get("meta", {})
        
        try:
            narration_steps = llm_client.narrate(problem_text, solution_steps, meta)
            if not narration_steps:
                narration_steps = [
                    NarrationStep(
                        step_index=s.step_index,
                        narration_text=s.description
                    )
                    for s in solution_steps
                ]
        except TimeoutError as e:
            raise HTTPException(status_code=504, detail=f"讲解生成超时: {str(e)}")
        
        for step in narration_steps:
            step.narration_text = convert_to_tts_friendly(step.narration_text)
            if not step.narration_text.strip():
                matching = next((s for s in solution_steps if s.step_index == step.step_index), None)
                step.narration_text = convert_to_tts_friendly(
                    (matching.description if matching else "") or (matching.title if matching else "") or "（讲解缺失）"
                )
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            save_narration_txt(timestamp, solution_steps, narration_steps)
        except Exception as e:
            import logging
            logging.warning(f"保存讲解 txt 失败: {e}")
        
        try:
            save_problem_record_with_timestamp(
                timestamp, problem_text, solution_steps, narration_steps, meta
            )
        except Exception:
            pass
        
        return {
            "narration_timestamp": timestamp,
            "message": "讲解脚本重新生成成功"
        }
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 文件")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新生成讲解失败: {str(e)}")


@router.get("/download_narration/{timestamp}")
async def download_narration(timestamp: str):
    """
    下载讲解脚本 txt 文件
    """
    try:
        import re
        if not re.match(r'^\d{8}_\d{6}$', timestamp):
            raise HTTPException(status_code=400, detail="无效的时间戳格式")

        filename = f"problems/problem_{timestamp}_narration.txt"
        filepath = Path(filename)

        if not filepath.exists():
            raise HTTPException(status_code=404, detail="讲解脚本文件不存在")

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


@router.get("/download_video/{timestamp}")
async def download_video(timestamp: str):
    """下载 Manim 渲染视频"""
    import re
    if not re.match(r'^\d{8}_\d{6}$', timestamp):
        raise HTTPException(status_code=400, detail="无效的时间戳格式")
    filepath = Path(f"problems/problem_{timestamp}_solution.mp4")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")
    return FileResponse(
        path=str(filepath),
        media_type="video/mp4",
        filename=f"solution_{timestamp}.mp4",
        headers={"Content-Disposition": f"attachment; filename=solution_{timestamp}.mp4"}
    )


@router.get("/download_timing/{timestamp}")
async def download_timing(timestamp: str):
    """下载时序 JSON 文件"""
    import re
    if not re.match(r'^\d{8}_\d{6}$', timestamp):
        raise HTTPException(status_code=400, detail="无效的时间戳格式")
    filepath = Path(f"problems/problem_{timestamp}_timing.json")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="时序文件不存在")
    return FileResponse(
        path=str(filepath),
        media_type="application/json",
        filename=f"timing_{timestamp}.json",
        headers={"Content-Disposition": f"attachment; filename=timing_{timestamp}.json"}
    )


@router.post("/manim_pipeline", response_model=ManimPipelineResponse)
async def manim_pipeline(
    problem: ManimPipelineRequest,
    llm_client: LLMClient = Depends(get_llm_client)
):
    """
    完整 Manim 视频流水线：
    1. LLM 解题
    2. 交叉验证（最多重试 2 次）
    3. 生成讲解脚本
    4. 渲染 Manim 视频（每步时长由讲解词数决定）
    5. 返回视频路径、讲解脚本路径、时序 JSON 路径及时序数据
    """
    from app.manim_scenes.renderer import compute_timings, render_solution_video

    if not problem.text or not problem.text.strip():
        raise HTTPException(status_code=400, detail="题目文本不能为空")
    if len(problem.text) > 5000:
        raise HTTPException(status_code=400, detail="题目文本过长（超过5000字符）")

    cleaned_text = clean_problem_text(problem.text)
    meta = {
        "topic": problem.topic,
        "difficulty": problem.difficulty,
        "tags": problem.tags,
    }

    # ── 1. Solve ──────────────────────────────────────────────────────────────
    try:
        steps = llm_client.solve(cleaned_text, meta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解题失败: {e}")

    if not steps:
        raise HTTPException(status_code=500, detail="LLM 返回的解题步骤为空")

    # ── 2. Verify (max 2 retries) ─────────────────────────────────────────────
    MAX_RETRIES = 2
    validation_attempts = 1
    for attempt in range(MAX_RETRIES + 1):
        try:
            verification = llm_client.verify(cleaned_text, steps, meta)
        except Exception:
            # If verification itself fails, proceed with current solution
            break
        if verification.is_correct:
            break
        if attempt < MAX_RETRIES:
            # Re-solve
            validation_attempts += 1
            try:
                steps = llm_client.solve(cleaned_text, meta)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"重新解题失败: {e}")
            if not steps:
                raise HTTPException(status_code=500, detail="重新解题结果为空")

    # ── 3. Narrate ────────────────────────────────────────────────────────────
    try:
        narration_steps = llm_client.narrate(cleaned_text, steps, meta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成讲解失败: {e}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    narration_txt_path = save_narration_txt(timestamp, steps, narration_steps)
    aligned = align_narration_to_solution(steps, narration_steps)

    # Save solution JSON for inspection
    os.makedirs("problems", exist_ok=True)
    solution_json_path = f"problems/problem_{timestamp}_solution.json"
    with open(solution_json_path, "w", encoding="utf-8") as _f:
        json.dump({
            "timestamp": timestamp,
            "problem_text": cleaned_text,
            "meta": meta,
            "validation_attempts": validation_attempts,
            "solution_steps": [s.dict() for s in steps],
            "narration_steps": [s.dict() for s in narration_steps],
        }, _f, ensure_ascii=False, indent=2)

    # ── 4. Compute timings ────────────────────────────────────────────────────
    timings = compute_timings(
        solution_steps=steps,
        aligned_narration=aligned,
        words_per_second=problem.words_per_second,
    )

    # ── 5. Render video ───────────────────────────────────────────────────────
    try:
        video_path, timing_json_path = render_solution_video(
            timestamp=timestamp,
            solution_steps=steps,
            timings=timings,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manim 渲染失败: {e}")

    return ManimPipelineResponse(
        problem_text=cleaned_text,
        steps=steps,
        narration_txt_path=narration_txt_path,
        video_path=video_path,
        timing_json_path=timing_json_path,
        timing=timings,
        validation_attempts=validation_attempts,
    )


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
