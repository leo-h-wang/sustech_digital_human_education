"""阿里云通义千问 LLM 适配器"""
import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from app.llm_providers.base import LLMClient

# 配置日志
logger = logging.getLogger(__name__)
from app.models.schemas import SolutionStep, NarrationStep
from app.prompts.solver_prompt import get_solver_prompt
from app.prompts.narration_prompt import get_narration_prompt
from app.utils.validation import (
    validate_solution_steps,
    validate_narration_steps,
    try_fix_json_response,
    sanitize_solution_step,
    sanitize_narration_step
)


class TongyiClient(LLMClient):
    """通义千问客户端"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        初始化通义千问客户端
        
        Args:
            api_key: API密钥，如果为None则从环境变量获取
            model: 模型名称，如果为None则从环境变量获取，默认为 qwen-turbo
                  可选值: qwen-turbo, qwen-plus, qwen-max, qwen-max-longcontext
        """
        self.api_key = api_key or os.getenv("TONGYI_API_KEY", "")
        if not self.api_key:
            raise ValueError("TONGYI_API_KEY 未设置，请在环境变量或初始化参数中提供")
        
        # 支持通过环境变量配置地域（默认北京，可选新加坡）
        # 北京: https://dashscope.aliyuncs.com
        # 新加坡: https://dashscope-intl.aliyuncs.com
        region = os.getenv("TONGYI_REGION", "beijing").lower()
        if region in ["singapore", "sg", "intl"]:
            base_domain = "https://dashscope-intl.aliyuncs.com"
        else:
            base_domain = "https://dashscope.aliyuncs.com"
        
        self.base_url = f"{base_domain}/api/v1/services/aigc/text-generation/generation"
        # 支持通过环境变量或参数配置模型，默认使用 qwen-turbo
        self.model = model or os.getenv("TONGYI_MODEL", "qwen-turbo")
        
        # 记录使用的模型信息
        logger.info(f"🤖 通义千问客户端已初始化")
        logger.info(f"   模型: {self.model}")
        logger.info(f"   地域: {region}")
        logger.info(f"   API端点: {self.base_url}")
        
        # 如果使用较弱的模型，给出警告
        if self.model == "qwen-turbo":
            logger.warning(
                f"⚠️  当前使用 {self.model} 模型，该模型在复杂数学问题上可能准确率较低。"
                f"建议在 .env 文件中设置 TONGYI_MODEL=qwen-max 以获得更好的答案质量。"
            )
        else:
            logger.info(f"✅ 使用 {self.model} 模型，适合处理复杂数学问题")
    
    def _get_timeout(self, default_timeout: Optional[float] = None) -> float:
        """
        根据模型类型获取合适的超时时间
        
        Args:
            default_timeout: 如果提供，则优先使用此值
            
        Returns:
            超时时间（秒）
        """
        if default_timeout is not None:
            return default_timeout
        
        # 从环境变量读取超时配置
        env_timeout = os.getenv("TONGYI_TIMEOUT")
        if env_timeout:
            try:
                return float(env_timeout)
            except ValueError:
                pass
        
        # 根据模型类型设置默认超时
        # 更强的模型需要更长的处理时间
        if "max" in self.model.lower():
            return 180.0  # qwen-max 等强模型使用 180 秒
        elif "plus" in self.model.lower():
            return 120.0  # qwen-plus 使用 120 秒
        else:
            return 60.0   # qwen-turbo 等快速模型使用 60 秒
    
    def _call_api(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, timeout: Optional[float] = None) -> str:
        """调用通义千问 API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "result_format": "message"  # 指定返回格式为 message，便于解析
            }
        }
        
        # 获取合适的超时时间
        actual_timeout = self._get_timeout(timeout)
        
        # 记录 API 调用信息
        call_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        logger.info(f"📤 [调用 {call_id}] 开始调用通义千问 API")
        logger.info(f"   模型: {self.model}")
        logger.info(f"   参数: temperature={temperature}, max_tokens={max_tokens}")
        logger.debug(f"   Prompt 长度: {len(prompt)} 字符")
        logger.debug(f"   Prompt 预览: {prompt[:200]}...")
        logger.debug(f"   超时设置: {actual_timeout} 秒")
        
        start_time = datetime.now()
        try:
            with httpx.Client(timeout=actual_timeout) as client:
                response = client.post(self.base_url, json=payload, headers=headers)
                
                # 检查 HTTP 状态码
                if response.status_code != 200:
                    error_detail = f"HTTP {response.status_code}"
                    try:
                        error_json = response.json()
                        if "message" in error_json:
                            error_detail += f": {error_json['message']}"
                        elif "error" in error_json:
                            error_detail += f": {error_json['error']}"
                        else:
                            error_detail += f": {response.text[:200]}"
                    except:
                        error_detail += f": {response.text[:200]}"
                    raise ValueError(f"API 请求失败: {error_detail}")
                
                result = response.json()

                # 检查是否有错误信息
                if "code" in result and result.get("code") != "Success":
                    error_msg = result.get("message", "未知错误")
                    raise ValueError(f"API 返回错误: {error_msg}")

                # 通义千问目前有两种常见返回格式：
                # 1) output.text: 纯文本格式（result_format='text'）
                # 2) output.choices[0].message.content: Chat 格式（result_format='message'）
                if "output" in result:
                    output = result["output"]

                    # 新版/简洁文本格式
                    if isinstance(output, dict) and "text" in output:
                        content = output.get("text", "")
                    # Chat 风格格式
                    elif "choices" in output:
                        choices = output.get("choices") or []
                        if not choices:
                            raise ValueError("API 返回的 choices 为空")
                        message = choices[0].get("message") or {}
                        content = message.get("content", "")
                    else:
                        raise ValueError(f"API 返回格式异常（缺少 text 或 choices 字段）: {result}")

                    if not content or not isinstance(content, str) or not content.strip():
                        raise ValueError("API 返回内容为空")
                    
                    # 记录成功响应
                    elapsed = (datetime.now() - start_time).total_seconds()
                    logger.info(f"✅ [调用 {call_id}] API 调用成功")
                    logger.info(f"   响应时间: {elapsed:.2f} 秒")
                    logger.info(f"   响应长度: {len(content)} 字符")
                    logger.debug(f"   响应预览: {content[:300]}...")
                    return content

                raise ValueError(f"API 返回格式异常（缺少 output 字段）: {result}")
        except httpx.TimeoutException:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ [调用 {call_id}] API 请求超时（{actual_timeout}秒，已用时 {elapsed:.2f}秒）")
            raise TimeoutError(f"API 请求超时（{actual_timeout}秒）")
        except httpx.HTTPStatusError as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ [调用 {call_id}] API 请求失败: HTTP {e.response.status_code}")
            logger.error(f"   错误详情: {e.response.text[:500]}")
            raise ValueError(f"API 请求失败: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ [调用 {call_id}] API 调用异常: {str(e)}")
            raise ValueError(f"API 调用异常: {str(e)}")
    
    def _parse_solution_steps(self, response_text: str) -> List[SolutionStep]:
        """解析解题步骤"""
        # 尝试解析 JSON
        try:
            # 先尝试使用验证工具修复
            fixed_data = try_fix_json_response(response_text)
            if fixed_data:
                # 验证格式
                is_valid, error_msg = validate_solution_steps(fixed_data)
                if is_valid:
                    steps = []
                    for item in fixed_data:
                        sanitized = sanitize_solution_step(item)
                        steps.append(SolutionStep(**sanitized))
                    return steps
            
            # 如果修复失败，尝试直接解析
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
                
                # 验证并清理
                is_valid, error_msg = validate_solution_steps(data)
                if not is_valid:
                    # 尝试清理后重试
                    data = [sanitize_solution_step(item) for item in data]
                
                steps = []
                for item in data:
                    sanitized = sanitize_solution_step(item)
                    steps.append(SolutionStep(**sanitized))
                return steps
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            pass
        
        # 如果 JSON 解析失败，尝试按行解析
        lines = response_text.split('\n')
        steps = []
        current_step = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测步骤开始（如 "步骤1:", "Step 1:", "1." 等）
            if any(marker in line.lower() for marker in ['步骤', 'step', '第']) and any(c.isdigit() for c in line):
                if current_step:
                    steps.append(current_step)
                
                # 提取步骤号
                step_num = 1
                for char in line:
                    if char.isdigit():
                        step_num = int(char)
                        break
                
                current_step = SolutionStep(
                    step_index=step_num,
                    title=line,
                    description="",
                    formula_latex=None
                )
            elif current_step:
                if current_step.description:
                    current_step.description += "\n" + line
                else:
                    current_step.description = line
        
        if current_step:
            steps.append(current_step)
        
        # 如果仍然没有步骤，创建一个默认步骤
        if not steps:
            steps.append(SolutionStep(
                step_index=1,
                title="解题过程",
                description=response_text,
                formula_latex=None
            ))
        
        return steps
    
    def solve(self, problem_text: str, meta: Optional[Dict[str, Any]] = None) -> List[SolutionStep]:
        """调用 LLM 解题"""
        logger.info("=" * 60)
        logger.info("📝 开始解题流程")
        logger.info(f"   题目: {problem_text[:100]}..." if len(problem_text) > 100 else f"   题目: {problem_text}")
        if meta:
            logger.info(f"   元数据: {meta}")
        
        prompt = get_solver_prompt(problem_text, meta or {})
        # 使用更低的 temperature (0.1) 以提高答案准确性和一致性
        response = self._call_api(prompt, temperature=0.1, max_tokens=4000)
        
        logger.info("📊 开始解析解题步骤...")
        steps = self._parse_solution_steps(response)
        logger.info(f"✅ 解析完成，共生成 {len(steps)} 个步骤")
        logger.info("=" * 60)
        
        return steps
    
    def narrate(
        self,
        problem_text: str,
        solution_steps: List[SolutionStep],
        meta: Optional[Dict[str, Any]] = None
    ) -> List[NarrationStep]:
        """调用 LLM 生成讲解脚本"""
        logger.info("=" * 60)
        logger.info("🎙️  开始生成讲解脚本")
        logger.info(f"   解题步骤数: {len(solution_steps)}")
        
        prompt = get_narration_prompt(problem_text, solution_steps, meta or {})
        response = self._call_api(prompt, temperature=0.7, max_tokens=3000)
        
        logger.info("📊 开始解析讲解步骤...")
        narration_steps = self._parse_narration_steps(response, len(solution_steps))
        logger.info(f"✅ 解析完成，共生成 {len(narration_steps)} 个讲解步骤")
        logger.info("=" * 60)
        
        return narration_steps
    
    def _parse_narration_steps(self, response_text: str, expected_steps: int) -> List[NarrationStep]:
        """解析讲解步骤"""
        steps = []
        lines = response_text.split('\n')
        current_step = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测步骤开始
            if any(marker in line.lower() for marker in ['步骤', 'step', '第']):
                if current_step:
                    steps.append(current_step)
                
                step_num = 1
                for char in line:
                    if char.isdigit():
                        step_num = int(char)
                        break
                
                # 提取步骤文本（去掉标记）
                narration_text = line
                for marker in ['步骤', 'Step', '第', ':']:
                    narration_text = narration_text.replace(marker, '').strip()
                
                sanitized = sanitize_narration_step({
                    "step_index": step_num,
                    "narration_text": narration_text
                })
                current_step = NarrationStep(**sanitized)
            elif current_step:
                if current_step.narration_text and not current_step.narration_text.startswith('步骤'):
                    current_step.narration_text += " " + line
                else:
                    current_step.narration_text = line
        
        if current_step:
            steps.append(current_step)
        
        # 如果解析失败，按段落分割
        if not steps:
            paragraphs = [p.strip() for p in response_text.split('\n\n') if p.strip()]
            for i, para in enumerate(paragraphs[:expected_steps], 1):
                sanitized = sanitize_narration_step({
                    "step_index": i,
                    "narration_text": para
                })
                steps.append(NarrationStep(**sanitized))
        
        # 验证结果
        steps_dict = [s.dict() for s in steps]
        is_valid, error_msg = validate_narration_steps(steps_dict)
        if not is_valid:
            # 如果验证失败，至少返回清理后的步骤
            steps = [NarrationStep(**sanitize_narration_step(s.dict())) for s in steps]
        
        return steps
    
    def get_provider_name(self) -> str:
        return "tongyi"

