"""LLM 输出校验工具"""
import json
import re
from typing import List, Dict, Any, Optional
from app.models.schemas import SolutionStep, NarrationStep


def validate_solution_steps(steps: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
    """
    校验解题步骤格式
    
    Returns:
        (is_valid, error_message)
    """
    if not steps:
        return False, "解题步骤为空"
    
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            return False, f"步骤 {i+1} 不是字典格式"
        
        if "step_index" not in step:
            return False, f"步骤 {i+1} 缺少 step_index 字段"
        
        if "title" not in step or not step["title"]:
            return False, f"步骤 {i+1} 缺少或为空 title 字段"
        
        if "description" not in step or not step["description"]:
            return False, f"步骤 {i+1} 缺少或为空 description 字段"
    
    return True, None


def validate_narration_steps(steps: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
    """
    校验讲解步骤格式
    
    Returns:
        (is_valid, error_message)
    """
    if not steps:
        return False, "讲解步骤为空"
    
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            return False, f"讲解步骤 {i+1} 不是字典格式"
        
        if "step_index" not in step:
            return False, f"讲解步骤 {i+1} 缺少 step_index 字段"
        
        if "narration_text" not in step or not step["narration_text"]:
            return False, f"讲解步骤 {i+1} 缺少或为空 narration_text 字段"
    
    return True, None


def try_fix_json_response(response_text: str) -> Optional[List[Dict]]:
    """
    尝试修复和提取 JSON 响应
    
    Returns:
        解析后的数据，如果失败返回 None
    """
    # 尝试提取 JSON 部分
    json_patterns = [
        r'\[[\s\S]*?\]',  # 匹配数组
        r'\{[\s\S]*?\}',  # 匹配对象
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, response_text)
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, list) and len(data) > 0:
                    return data
            except json.JSONDecodeError:
                continue
    
    return None


def sanitize_solution_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """清理和规范化解题步骤"""
    return {
        "step_index": int(step.get("step_index", 0)) or 1,
        "title": str(step.get("title", "")).strip() or "解题步骤",
        "description": str(step.get("description", "")).strip() or "",
        "formula_latex": str(step.get("formula_latex", "")).strip() if step.get("formula_latex") else None
    }


def sanitize_narration_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """清理和规范化讲解步骤"""
    return {
        "step_index": int(step.get("step_index", 0)) or 1,
        "narration_text": str(step.get("narration_text", "")).strip() or ""
    }

