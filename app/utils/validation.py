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


def _fix_json_escape_sequences(json_str: str) -> str:
    """
    修复 JSON 中的无效转义序列
    
    LaTeX 公式中的反斜杠（如 \int, \frac）在 JSON 中是无效的转义序列，
    需要将单个 \ 转换为 \\
    """
    # 有效的 JSON 转义序列
    valid_escapes = {'"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'}
    
    result = []
    i = 0
    while i < len(json_str):
        char = json_str[i]
        if char == '\\' and i + 1 < len(json_str):
            next_char = json_str[i + 1]
            if next_char in valid_escapes:
                # 有效的转义序列，保持原样
                result.append(char)
                result.append(next_char)
                i += 2
            elif next_char == '\\':
                # 已经是双反斜杠
                result.append(char)
                result.append(next_char)
                i += 2
            else:
                # 无效的转义序列（如 \i, \f 在 LaTeX 中），添加额外的反斜杠
                result.append('\\')
                result.append('\\')
                result.append(next_char)
                i += 2
        else:
            result.append(char)
            i += 1
    
    return ''.join(result)


def try_fix_json_response(response_text: str) -> Optional[List[Dict]]:
    """
    尝试修复和提取 JSON 响应
    
    Returns:
        解析后的数据，如果失败返回 None
    """
    # #region agent log
    import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"location": "validation.py:try_fix_json_response:entry", "message": "try_fix_json_response called", "data": {"response_len": len(response_text) if response_text else 0, "response_preview": (response_text[:300] if response_text else "")}, "timestamp": __import__('time').time()*1000, "sessionId": "debug-session", "hypothesisId": "A,B"}) + '\n')
    # #endregion
    # 首先尝试直接解析整个响应
    try:
        data = json.loads(response_text.strip())
        if isinstance(data, list) and len(data) > 0:
            # #region agent log
            import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"location": "validation.py:try_fix_json_response:direct_parse_success", "message": "Direct JSON parse succeeded", "data": {"data_len": len(data), "first_item_keys": list(data[0].keys()) if data and isinstance(data[0], dict) else "not_dict"}, "timestamp": __import__('time').time()*1000, "sessionId": "debug-session", "hypothesisId": "A,B"}) + '\n')
            # #endregion
            return data
    except json.JSONDecodeError as e:
        # #region agent log
        import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"location": "validation.py:try_fix_json_response:direct_parse_failed", "message": "Direct JSON parse failed", "data": {"error": str(e), "error_pos": e.pos if hasattr(e, 'pos') else -1}, "timestamp": __import__('time').time()*1000, "sessionId": "debug-session", "hypothesisId": "A,B"}) + '\n')
        # #endregion
        pass
    
    # 尝试修复无效的转义序列后再解析
    try:
        fixed_response = _fix_json_escape_sequences(response_text.strip())
        data = json.loads(fixed_response)
        if isinstance(data, list) and len(data) > 0:
            return data
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 JSON 数组（使用非贪婪匹配，但需要匹配完整的JSON结构）
    # 先找最外层的数组
    json_start = response_text.find('[')
    if json_start >= 0:
        # 从第一个 [ 开始，找到匹配的 ]
        bracket_count = 0
        json_end = json_start
        for i in range(json_start, len(response_text)):
            if response_text[i] == '[':
                bracket_count += 1
            elif response_text[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    json_end = i + 1
                    break
        
        if json_end > json_start:
            json_str = response_text[json_start:json_end]
            # 先尝试直接解析
            try:
                data = json.loads(json_str)
                if isinstance(data, list) and len(data) > 0:
                    return data
            except json.JSONDecodeError:
                pass
            
            # 尝试修复后解析
            try:
                fixed_json = _fix_json_escape_sequences(json_str)
                data = json.loads(fixed_json)
                if isinstance(data, list) and len(data) > 0:
                    return data
            except json.JSONDecodeError:
                pass
    
    # 尝试使用正则表达式匹配（作为备选）
    json_patterns = [
        r'\[[\s\S]*?\]',  # 匹配数组（非贪婪）
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, response_text, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, list) and len(data) > 0:
                    return data
            except json.JSONDecodeError:
                # 尝试修复后解析
                try:
                    fixed_match = _fix_json_escape_sequences(match)
                    data = json.loads(fixed_match)
                    if isinstance(data, list) and len(data) > 0:
                        return data
                except json.JSONDecodeError:
                    continue
    
    return None


def sanitize_solution_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """清理和规范化解题步骤"""
    # 处理 title 字段：如果包含 JSON 字符串，尝试提取
    title = str(step.get("title", "")).strip()
    if title and ('"step_index"' in title or title.startswith('"')):
        # 可能是JSON字符串被错误解析，尝试提取真正的title
        try:
            import re
            # 尝试匹配 "title": "实际标题"
            title_match = re.search(r'"title":\s*"([^"]+)"', title)
            if title_match:
                title = title_match.group(1)
            # 如果还是包含JSON结构，尝试其他方式
            elif title.startswith('"') and title.endswith(','):
                # 可能是 "step_index": 1, 这种格式
                title = "解题步骤"
        except:
            pass
    
    # 处理 description 字段：如果包含 JSON 字符串，尝试提取
    description = str(step.get("description", "")).strip()
    if description and ('"title"' in description or '"description"' in description):
        # 可能是JSON字符串，尝试解析
        try:
            import re
            # 尝试提取真正的description
            desc_match = re.search(r'"description":\s*"([^"]+(?:\\.[^"]*)*)"', description)
            if desc_match:
                # 处理转义字符
                desc_text = desc_match.group(1).replace('\\n', '\n').replace('\\"', '"')
                description = desc_text
            # 或者尝试解析整个JSON对象
            elif description.startswith('"') or description.startswith('{'):
                # 尝试提取多行description（处理 \n 转义）
                desc_lines = []
                for line in description.split('\\n'):
                    line = line.strip().strip('"').strip(',')
                    # 跳过JSON结构标记
                    if line and not line.startswith('"') and not line.startswith('{') and '":' not in line:
                        desc_lines.append(line)
                if desc_lines:
                    description = '\n'.join(desc_lines)
        except:
            pass
    
    return {
        "step_index": int(step.get("step_index", 0)) or 1,
        "title": title or "解题步骤",
        "description": description or "",
        "formula_latex": str(step.get("formula_latex", "")).strip() if step.get("formula_latex") else None
    }


def sanitize_narration_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """清理和规范化讲解步骤"""
    return {
        "step_index": int(step.get("step_index", 0)) or 1,
        "narration_text": str(step.get("narration_text", "")).strip() or ""
    }

