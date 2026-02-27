"""Google Gemini LLM 适配器"""
import json
import os
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from app.llm_providers.base import LLMClient
from app.models.schemas import SolutionStep, NarrationStep
from app.prompts.solver_prompt import get_solver_prompt
from app.prompts.narration_prompt import get_narration_prompt
from app.utils.validation import (
    validate_solution_steps,
    validate_narration_steps,
    try_fix_json_response,
    sanitize_solution_step,
    sanitize_narration_step,
    _fix_json_escape_sequences
)

# 配置日志
logger = logging.getLogger(__name__)


class GeminiClient(LLMClient):
    """Gemini 客户端（支持主模型 + 自动降级到备用模型）"""

    # 免费层级各模型的速率限制（2026-02 更新）
    FREE_TIER_LIMITS: Dict[str, Dict[str, Any]] = {
        "gemini-2.5-pro": {"rpm": 5, "rpd": 100, "tpm": 250_000, "min_interval": 12.0},
        "gemini-2.5-flash": {"rpm": 10, "rpd": 500, "tpm": 250_000, "min_interval": 6.0},
        "gemini-2.5-flash-lite": {"rpm": 15, "rpd": 1000, "tpm": 250_000, "min_interval": 4.0},
        "gemini-1.5-pro": {"rpm": 2, "rpd": 50, "tpm": 32_000, "min_interval": 30.0},
        "gemini-1.5-flash": {"rpm": 15, "rpd": 1500, "tpm": 1_000_000, "min_interval": 4.0},
    }

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        初始化 Gemini 客户端

        Args:
            api_key: API密钥，如果为None则从环境变量获取
            model: 主模型名称，默认 gemini-2.5-flash（免费层级通用可用）
                  可选值: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite,
                          gemini-1.5-pro, gemini-1.5-flash
                  注意: gemini-2.5-pro 在部分免费层级账户中 quota 可能为 0，
                        此时会自动降级到备用模型。
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY 未设置，请在环境变量或初始化参数中提供")

        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

        # 主模型：默认 gemini-2.5-flash（免费层级通用可用）
        # 如需使用 pro 模型，设置 GEMINI_MODEL=gemini-2.5-pro（需要账户有 pro 配额）
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        # 备用模型：主模型遇到速率限制/配额不足时自动降级
        # 设为空字符串可禁用降级
        self.fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "")
        if self.fallback_model == self.model:
            self.fallback_model = ""

        # 会话级别的已屏蔽模型集合：quota=0 的模型会被记住，后续请求直接跳过
        self._blocked_models: set = set()

        logger.info(f"🤖 Gemini 客户端已初始化")
        logger.info(f"   主模型: {self.model}")
        if self.fallback_model:
            logger.info(f"   备用模型: {self.fallback_model}（主模型触发速率限制时自动降级）")
        logger.info(f"   API端点: {self.base_url}")

        # 重试配置
        self.max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("GEMINI_RETRY_DELAY", "1.0"))

        # 每个模型独立的请求时间戳（用于节流）
        self._last_request_time: Dict[str, float] = {}

        # 根据模型查找最小请求间隔，支持环境变量覆盖
        env_interval = os.getenv("GEMINI_MIN_INTERVAL")
        if env_interval:
            self._default_min_interval = float(env_interval)
        else:
            self._default_min_interval = None

        limits = self.FREE_TIER_LIMITS.get(self.model, {})
        effective_interval = self._get_min_interval(self.model)
        logger.info(f"   免费层级限制 ({self.model}): RPM={limits.get('rpm','?')}, "
                     f"RPD={limits.get('rpd','?')}, 最小间隔={effective_interval}s")
    
    def _get_min_interval(self, model: str) -> float:
        """返回指定模型的最小请求间隔（秒）"""
        if self._default_min_interval is not None:
            return self._default_min_interval
        limits = self.FREE_TIER_LIMITS.get(model)
        if limits:
            return limits["min_interval"]
        return 6.0

    def _get_timeout(self, default_timeout: Optional[float] = None, model: Optional[str] = None) -> float:
        """根据模型类型获取合适的超时时间"""
        if default_timeout is not None:
            return default_timeout

        env_timeout = os.getenv("GEMINI_TIMEOUT")
        if env_timeout:
            try:
                return float(env_timeout)
            except ValueError:
                pass

        target = model or self.model
        if "pro" in target.lower() and "flash" not in target.lower():
            return 180.0
        return 120.0
    
    def _try_fallback(self, active_model: str, prompt: str, temperature: float,
                      max_tokens: int, timeout: Optional[float],
                      _model_override: Optional[str]) -> Optional[str]:
        """如果有可用的备用模型，尝试降级。返回结果字符串或 None。"""
        fallback = self.fallback_model
        if _model_override or not fallback or active_model == fallback:
            return None
        if fallback in self._blocked_models:
            logger.warning(f"   备用模型 {fallback} 也已被屏蔽（quota=0），无法降级")
            return None

        logger.warning(
            f"🔄 主模型 {active_model} 不可用，自动降级到备用模型 {fallback}"
        )
        return self._call_api(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            _model_override=fallback,
        )

    @staticmethod
    def _is_zero_quota(error_message: str) -> bool:
        """检测 429 错误是否因为 quota limit: 0（模型在该免费层级完全不可用）"""
        return "limit: 0" in error_message

    def _call_api(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000,
                  timeout: Optional[float] = None, *, _model_override: Optional[str] = None) -> str:
        """调用 Gemini API，支持自动降级到备用模型"""
        import re as _re

        active_model = _model_override or self.model

        # 如果该模型已被标记为 quota=0，直接跳到备用模型
        if active_model in self._blocked_models:
            logger.info(f"⏭️  跳过已屏蔽模型 {active_model}（quota=0）")
            result = self._try_fallback(
                active_model, prompt, temperature, max_tokens, timeout, _model_override
            )
            if result is not None:
                return result
            raise ValueError(
                f"模型 {active_model} 配额为 0 且无可用备用模型。"
                f"请检查 API key 的免费层级权限或更换 GEMINI_MODEL。"
            )

        call_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        logger.info(f"📤 [调用 {call_id}] 开始调用 Gemini API")
        logger.info(f"   模型: {active_model}")
        logger.info(f"   参数: temperature={temperature}, max_tokens={max_tokens}")
        logger.debug(f"   Prompt 长度: {len(prompt)} 字符")
        logger.debug(f"   Prompt 预览: {prompt[:200]}...")

        url = f"{self.base_url}/{active_model}:generateContent"
        params = {"key": self.api_key}

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
                "topK": 40,
            },
        }

        actual_timeout = self._get_timeout(timeout, model=active_model)
        logger.debug(f"   超时设置: {actual_timeout} 秒")

        # 模型级请求节流
        min_interval = self._get_min_interval(active_model)
        last_ts = self._last_request_time.get(active_model, 0)
        elapsed_since_last = time.time() - last_ts
        if elapsed_since_last < min_interval:
            wait_time = min_interval - elapsed_since_last
            logger.debug(f"   请求节流（{active_model}）：等待 {wait_time:.2f}s")
            time.sleep(wait_time)

        start_time = datetime.now()
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=actual_timeout) as client:
                    response = client.post(url, params=params, json=payload)
                    self._last_request_time[active_model] = time.time()

                if response.status_code != 200:
                    error_detail = f"HTTP {response.status_code}"
                    try:
                        error_json = response.json()
                        if "error" in error_json:
                            error_info = error_json["error"]
                            error_message = error_info.get("message", "未知错误")
                            error_detail += f": {error_message}"

                            if response.status_code == 429:
                                # 检测 quota=0：模型在该免费层级完全不可用
                                if self._is_zero_quota(error_message):
                                    self._blocked_models.add(active_model)
                                    logger.error(
                                        f"🚫 模型 {active_model} 免费层级配额为 0 "
                                        f"（已屏蔽，本次会话内不再尝试）"
                                    )
                                    result = self._try_fallback(
                                        active_model, prompt, temperature,
                                        max_tokens, timeout, _model_override,
                                    )
                                    if result is not None:
                                        return result
                                    raise ValueError(
                                        f"模型 {active_model} 配额为 0 且无可用备用模型。"
                                        f"请检查 API key 的免费层级权限或更换 GEMINI_MODEL。"
                                    )

                                logger.warning(
                                    f"⚠️  [尝试 {attempt + 1}/{self.max_retries + 1}] "
                                    f"{active_model} 速率限制（429）"
                                )
                                retry_seconds = self.retry_delay * (2 ** attempt)
                                if "retry" in error_message.lower():
                                    m = _re.search(r"(\d+\.?\d*)\s*seconds?", error_message, _re.IGNORECASE)
                                    if m:
                                        retry_seconds = max(float(m.group(1)), retry_seconds)

                                if attempt >= self.max_retries:
                                    result = self._try_fallback(
                                        active_model, prompt, temperature,
                                        max_tokens, timeout, _model_override,
                                    )
                                    if result is not None:
                                        return result
                                    logger.error(f"❌ 达到最大重试次数，放弃重试")
                                    raise ValueError(f"API 请求失败: {error_detail}")

                                logger.info(f"   等待 {retry_seconds:.2f}s 后重试...")
                                time.sleep(retry_seconds)
                                continue

                            if 500 <= response.status_code < 600:
                                retry_seconds = self.retry_delay * (2 ** attempt)
                                logger.warning(
                                    f"⚠️  [尝试 {attempt + 1}/{self.max_retries + 1}] "
                                    f"上游服务不可用 {response.status_code}，等待 {retry_seconds:.2f}s 后重试..."
                                )
                                if attempt >= self.max_retries:
                                    raise ValueError(f"API 请求失败: {error_detail}")
                                time.sleep(retry_seconds)
                                continue
                        else:
                            error_detail += f": {response.text[:200]}"
                    except (ValueError, KeyError):
                        error_detail += f": {response.text[:200]}"

                    raise ValueError(f"API 请求失败: {error_detail}")

                result = response.json()

                if "candidates" not in result or not result["candidates"]:
                    raise ValueError("API 返回的 candidates 为空")

                candidate = result["candidates"][0]
                if "content" not in candidate:
                    raise ValueError("API 返回的 content 为空")

                parts = candidate.get("content", {}).get("parts", [])
                if not parts:
                    raise ValueError("API 返回的 parts 为空")

                content = parts[0].get("text", "")
                if not content or not isinstance(content, str) or not content.strip():
                    raise ValueError("API 返回内容为空")

                finish_reason = candidate.get("finishReason", "")
                if finish_reason == "MAX_TOKENS":
                    logger.warning(f"   ⚠️  响应可能被截断（finishReason: {finish_reason}）")
                elif finish_reason:
                    logger.debug(f"   完成原因: {finish_reason}")

                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ [调用 {call_id}] API 调用成功（模型: {active_model}）")
                logger.info(f"   响应时间: {elapsed:.2f} 秒")
                logger.info(f"   响应长度: {len(content)} 字符")
                logger.info(f"   响应预览: {content[:500]}...")
                if len(content) < 1000:
                    logger.info(f"   完整响应: {content}")
                if len(content) < 200:
                    logger.warning(f"   ⚠️  响应非常短（{len(content)}字符），可能被截断")
                if content.strip().startswith("[") and not content.strip().endswith("]"):
                    logger.warning(f"   ⚠️  JSON数组可能不完整（以[开始但未以]结束）")
                return content

            except httpx.TimeoutException:
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.error(f"❌ [调用 {call_id}] 请求超时（{actual_timeout}s，已用时 {elapsed:.2f}s）")
                if attempt >= self.max_retries:
                    raise TimeoutError(f"API 请求超时（{actual_timeout}秒）")
                retry_seconds = self.retry_delay * (2 ** attempt)
                logger.info(f"   等待 {retry_seconds:.2f}s 后重试...")
                time.sleep(retry_seconds)
                continue
            except httpx.HTTPStatusError as e:
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.error(f"❌ [调用 {call_id}] 请求失败: HTTP {e.response.status_code}")
                logger.error(f"   错误详情: {e.response.text[:500]}")
                if attempt >= self.max_retries:
                    raise ValueError(f"API 请求失败: HTTP {e.response.status_code} - {e.response.text}")
                retry_seconds = self.retry_delay * (2 ** attempt)
                logger.info(f"   等待 {retry_seconds:.2f}s 后重试...")
                time.sleep(retry_seconds)
                continue
            except ValueError as e:
                error_str = str(e)
                if "429" in error_str and attempt < self.max_retries:
                    last_exception = e
                    continue
                raise
            except Exception as e:
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.error(f"❌ [调用 {call_id}] API 调用异常: {str(e)}")
                if attempt >= self.max_retries:
                    raise ValueError(f"API 调用异常: {str(e)}")
                retry_seconds = self.retry_delay * (2 ** attempt)
                logger.info(f"   等待 {retry_seconds:.2f}s 后重试...")
                time.sleep(retry_seconds)
                continue

        if last_exception:
            raise last_exception
        raise ValueError("API 调用失败：未知错误")
    
    def _parse_solution_steps(self, response_text: str) -> List[SolutionStep]:
        """解析解题步骤"""
        logger.info(f"   📊 开始解析解题步骤...")
        logger.info(f"   原始响应长度: {len(response_text)} 字符")
        logger.info(f"   原始响应预览: {response_text[:500]}...")
        # #region agent log
        import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"sessionId": "debug-session", "runId": "pre-fix", "hypothesisId": "H1", "location": "gemini.py:_parse_solution_steps:entry", "message": "parse_solution_steps entry", "data": {"response_len": len(response_text), "response_preview": response_text[:300]}, "timestamp": __import__('time').time()*1000}) + '\n')
        # #endregion
        
        # 如果响应太短，记录完整内容
        if len(response_text) < 500:
            logger.warning(f"   ⚠️  响应很短，完整内容: {response_text}")
        
        # 清理响应：移除可能的markdown代码块标记
        cleaned_response = response_text.strip()
        if cleaned_response.startswith('```'):
            # 移除 ```json 或 ``` 标记
            lines = cleaned_response.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            cleaned_response = '\n'.join(lines)
            logger.debug(f"   清理markdown标记后的响应: {cleaned_response[:500]}...")
        
        # 检查JSON是否可能被截断（以[开始但没有以]结束）
        if cleaned_response.startswith('[') and not cleaned_response.rstrip().endswith(']'):
            logger.warning(f"   ⚠️  JSON数组可能不完整（以[开始但未以]结束）")
            logger.warning(f"   尝试修复截断的JSON...")
            # 尝试修复：找到最后一个完整的JSON对象
            # 查找最后一个完整的 } 或 }, 后跟 ]
            last_brace = cleaned_response.rfind('}')
            if last_brace > 0:
                # 尝试补全JSON
                potential_json = cleaned_response[:last_brace+1] + ']'
                try:
                    # 验证是否可以解析
                    test_data = json.loads(potential_json)
                    if isinstance(test_data, list) and len(test_data) > 0:
                        logger.info(f"   ✅ 成功修复截断的JSON，提取到 {len(test_data)} 个步骤")
                        cleaned_response = potential_json
                except:
                    pass
        
        # 尝试解析 JSON
        try:
            # 先尝试使用验证工具修复
            fixed_data = try_fix_json_response(cleaned_response)
            if fixed_data:
                logger.info(f"   ✅ 成功提取JSON数组，包含 {len(fixed_data)} 个步骤")
                # 验证格式
                is_valid, error_msg = validate_solution_steps(fixed_data)
                # #region agent log
                import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"sessionId": "debug-session", "runId": "pre-fix", "hypothesisId": "H1", "location": "gemini.py:_parse_solution_steps:try_fix", "message": "try_fix_json_response result", "data": {"fixed_len": len(fixed_data), "is_valid": is_valid, "error_msg": error_msg}, "timestamp": __import__('time').time()*1000}) + '\n')
                # #endregion
                if is_valid:
                    steps = []
                    for item in fixed_data:
                        sanitized = sanitize_solution_step(item)
                        steps.append(SolutionStep(**sanitized))
                    logger.info(f"   ✅ 验证通过，返回 {len(steps)} 个步骤")
                    return steps
                else:
                    logger.warning(f"   ⚠️  JSON格式验证失败: {error_msg}，尝试清理后重试")
                    # 即使验证失败，也尝试清理后使用
                    steps = []
                    for item in fixed_data:
                        sanitized = sanitize_solution_step(item)
                        steps.append(SolutionStep(**sanitized))
                    if steps:
                        logger.info(f"   ✅ 清理后返回 {len(steps)} 个步骤")
                        return steps
            else:
                logger.warning(f"   ⚠️  try_fix_json_response 返回 None，尝试其他方法")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"   JSON解析异常: {e}")
            # #region agent log
            import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"sessionId": "debug-session", "runId": "pre-fix", "hypothesisId": "H1", "location": "gemini.py:_parse_solution_steps:json_exception", "message": "JSON parse exception", "data": {"error": str(e)}, "timestamp": __import__('time').time()*1000}) + '\n')
            # #endregion
            pass
        
        # 如果 JSON 解析失败，尝试按行解析
        import re
        lines = response_text.split('\n')
        steps = []
        current_step = None
        
        # 更精确的步骤检测模式，避免匹配 JSON 字段名如 "step_index"
        step_patterns = [
            r'^[\*\s]*步骤\s*(\d+)',          # 步骤1, **步骤 1
            r'^[\*\s]*[Ss]tep\s+(\d+)',        # Step 1, step 1（后面必须有空格）
            r'^[\*\s]*第\s*(\d+)\s*步',        # 第1步, 第 1 步
            r'^[\*\s]*(\d+)\s*[\.、：:]\s*\S',  # 1. xxx, 1、xxx, 1：xxx
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 跳过 JSON 结构行
            if line.startswith('"') or line.startswith('{') or line.startswith('[') or line.startswith('}') or line.startswith(']'):
                continue
            
            # 检测步骤开始
            step_num = None
            for pattern in step_patterns:
                match = re.match(pattern, line)
                if match:
                    step_num = int(match.group(1))
                    break
            
            if step_num:
                if current_step:
                    steps.append(current_step)
                
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
        
        # 如果仍然没有步骤
        if not steps:
            # 检查响应是否看起来像 JSON（但解析失败了）
            stripped_response = response_text.strip()
            if stripped_response.startswith('[') and stripped_response.endswith(']'):
                # 响应看起来像 JSON 数组，尝试最后的手段：逐个提取 JSON 对象
                logger.warning(f"   ⚠️  JSON 解析失败，尝试逐个提取对象...")
                try:
                    # 使用更宽松的方法：按 },{ 分割
                    import re
                    # 匹配每个完整的 JSON 对象
                    object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                    objects = re.findall(object_pattern, stripped_response)
                    for i, obj_str in enumerate(objects):
                        try:
                            # 尝试修复并解析单个对象
                            fixed_obj = _fix_json_escape_sequences(obj_str)
                            obj = json.loads(fixed_obj)
                            if isinstance(obj, dict) and 'step_index' in obj:
                                sanitized = sanitize_solution_step(obj)
                                steps.append(SolutionStep(**sanitized))
                        except:
                            continue
                    if steps:
                        logger.info(f"   ✅ 通过逐个提取，成功获取 {len(steps)} 个步骤")
                except Exception as e:
                    logger.warning(f"   ⚠️  逐个提取也失败: {e}")
            
            # 如果还是没有步骤，创建默认步骤
            if not steps:
                logger.warning(f"   ⚠️  所有解析方法都失败，创建默认步骤")
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
        # temperature=0.1 提高答案准确性；16000 tokens 支持复杂题目（10+ 步骤）
        response = self._call_api(prompt, temperature=0.1, max_tokens=16000)
        
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
        
        # 根据步骤数量动态调整token数：每个步骤预留~800 tokens，最少6000
        num_steps = len(solution_steps)
        estimated_tokens = max(6000, num_steps * 800 + 2000)
        max_tokens = min(estimated_tokens, 16000)  # 不超过16000
        logger.info(f"   预计需要 ~{estimated_tokens} tokens，设置 max_tokens={max_tokens}")
        
        prompt = get_narration_prompt(problem_text, solution_steps, meta or {})
        response = self._call_api(prompt, temperature=0.7, max_tokens=max_tokens)
        
        logger.info("📊 开始解析讲解步骤...")
        narration_steps = self._parse_narration_steps(response, len(solution_steps))
        logger.info(f"✅ 解析完成，共生成 {len(narration_steps)} 个讲解步骤")
        logger.info("=" * 60)
        
        return narration_steps
    
    def _parse_narration_steps(self, response_text: str, expected_steps: int) -> List[NarrationStep]:
        """解析讲解步骤（优先 JSON，失败回退文本解析）"""
        import re
        
        logger.info(f"   📊 开始解析讲解步骤...")
        logger.info(f"   原始响应长度: {len(response_text)} 字符")
        logger.debug(f"   原始响应预览: {response_text[:500]}...")
        
        # #region agent log
        import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"location": "gemini.py:_parse_narration_steps:entry", "message": "parse_narration called", "data": {"response_len": len(response_text), "response_preview": response_text[:500], "expected_steps": expected_steps}, "timestamp": __import__('time').time()*1000, "sessionId": "debug-session", "hypothesisId": "A,B,C,D"}) + '\n')
        # #endregion
        
        # 优先尝试 JSON 解析
        try:
            # 清理响应：移除可能的 markdown 代码块标记
            cleaned_response = response_text.strip()
            if cleaned_response.startswith('```'):
                lines = cleaned_response.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned_response = '\n'.join(lines)
                logger.debug(f"   清理 markdown 标记后的响应: {cleaned_response[:500]}...")
            
            # #region agent log
            import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"location": "gemini.py:_parse_narration_steps:before_json_parse", "message": "cleaned response before JSON parse", "data": {"cleaned_len": len(cleaned_response), "cleaned_preview": cleaned_response[:300], "starts_with_bracket": cleaned_response.startswith('[')}, "timestamp": __import__('time').time()*1000, "sessionId": "debug-session", "hypothesisId": "A,B"}) + '\n')
            # #endregion
            
            # 尝试使用验证工具修复并解析
            fixed_data = try_fix_json_response(cleaned_response)
            
            # #region agent log
            import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"location": "gemini.py:_parse_narration_steps:after_json_parse", "message": "try_fix_json_response result", "data": {"fixed_data_is_none": fixed_data is None, "fixed_data_len": len(fixed_data) if fixed_data else 0, "fixed_data_preview": str(fixed_data)[:500] if fixed_data else "None"}, "timestamp": __import__('time').time()*1000, "sessionId": "debug-session", "hypothesisId": "A,B"}) + '\n')
            # #endregion
            
            if fixed_data:
                logger.info(f"   ✅ 成功提取 JSON 数组，包含 {len(fixed_data)} 个讲解步骤")
                # 验证格式
                is_valid, error_msg = validate_narration_steps(fixed_data)
                
                # #region agent log
                import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"location": "gemini.py:_parse_narration_steps:validation", "message": "validation result", "data": {"is_valid": is_valid, "error_msg": error_msg}, "timestamp": __import__('time').time()*1000, "sessionId": "debug-session", "hypothesisId": "A,B"}) + '\n')
                # #endregion
                
                if is_valid:
                    steps = []
                    for item in fixed_data:
                        sanitized = sanitize_narration_step(item)
                        steps.append(NarrationStep(**sanitized))
                    logger.info(f"   ✅ JSON 验证通过，返回 {len(steps)} 个步骤")
                    return steps
                else:
                    logger.warning(f"   ⚠️  JSON 格式验证失败: {error_msg}，尝试清理后重试")
                    # 即使验证失败，也尝试清理后使用
                    steps = []
                    for item in fixed_data:
                        sanitized = sanitize_narration_step(item)
                        steps.append(NarrationStep(**sanitized))
                    if steps:
                        logger.info(f"   ✅ 清理后返回 {len(steps)} 个步骤")
                        return steps
            else:
                logger.warning(f"   ⚠️  try_fix_json_response 返回 None，尝试文本解析")
        except Exception as e:
            logger.warning(f"   JSON 解析异常: {e}，回退到文本解析")
            # #region agent log
            import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"location": "gemini.py:_parse_narration_steps:json_exception", "message": "JSON parsing exception", "data": {"error": str(e)}, "timestamp": __import__('time').time()*1000, "sessionId": "debug-session", "hypothesisId": "A,B"}) + '\n')
            # #endregion
        
        # 回退到文本解析模式
        logger.info(f"   📝 使用文本模式解析讲解步骤...")
        # #region agent log
        import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"location": "gemini.py:_parse_narration_steps:text_fallback", "message": "Falling back to text parsing mode", "data": {"response_preview": response_text[:300]}, "timestamp": __import__('time').time()*1000, "sessionId": "debug-session", "hypothesisId": "C,D"}) + '\n')
        # #endregion
        
        # 使用更精确的正则表达式模式来匹配步骤开始
        # 匹配: "步骤1", "步骤 1", "Step 1", "step1", "第1步", "**1：", "**1:", "1：", "1:"（行首）
        step_pattern = re.compile(
            r'^(?:'
            r'\*{0,2}\s*步骤\s*(\d+)'  # 步骤1, **步骤 1
            r'|'
            r'\*{0,2}\s*[Ss]tep\s*(\d+)'  # Step 1, **step1
            r'|'
            r'\*{0,2}\s*第\s*(\d+)\s*步'  # 第1步, **第 1 步
            r'|'
            r'\*{2,}\s*(\d+)\s*[：:]'  # **1：, **1:
            r'|'
            r'^(\d+)\s*[：:]\s*\S'  # 1：标题, 1: title（行首，后面必须有内容）
            r')'
        )
        
        steps_dict = {}  # 用字典按 step_index 合并内容
        lines = response_text.split('\n')
        current_step_index = None
        
        for line in lines:
            line = line.strip()
            if not line or line == '---':  # 跳过空行和分隔符
                continue
            
            # 尝试匹配步骤开始
            match = step_pattern.match(line)
            if match:
                # 提取步骤号（从多个捕获组中获取非空的那个）
                step_num = None
                for group in match.groups():
                    if group:
                        step_num = int(group)
                        break
                
                if step_num:
                    current_step_index = step_num
                    
                    # 提取标记后的文本作为讲解内容的开始
                    remaining_text = line[match.end():].strip()
                    # 清理开头的标点符号
                    remaining_text = re.sub(r'^[：:：\s]+', '', remaining_text).strip()
                    
                    if current_step_index not in steps_dict:
                        steps_dict[current_step_index] = []
                    
                    if remaining_text:
                        steps_dict[current_step_index].append(remaining_text)
                    continue
            
            # 非步骤标记行，追加到当前步骤
            if current_step_index is not None:
                if current_step_index not in steps_dict:
                    steps_dict[current_step_index] = []
                steps_dict[current_step_index].append(line)
        
        # 将字典转换为列表，并合并每个步骤的所有文本
        steps = []
        for step_index in sorted(steps_dict.keys()):
            narration_text = ' '.join(steps_dict[step_index])
            # 清理多余的空格和分隔符
            narration_text = re.sub(r'\s*---\s*', ' ', narration_text)
            narration_text = re.sub(r'\s+', ' ', narration_text).strip()
                
            if narration_text:
                sanitized = sanitize_narration_step({
                    "step_index": step_index,
                    "narration_text": narration_text
                })
                steps.append(NarrationStep(**sanitized))
        
        # 如果解析失败，按段落分割
        if not steps:
            # #region agent log
            import json as _json; open(r'e:\sustech_digital_human_education\.cursor\debug.log', 'a', encoding='utf-8').write(_json.dumps({"location": "gemini.py:_parse_narration_steps:paragraph_fallback", "message": "Text parsing failed, falling back to paragraph split", "data": {"response_preview": response_text[:300]}, "timestamp": __import__('time').time()*1000, "sessionId": "debug-session", "hypothesisId": "C,D"}) + '\n')
            # #endregion
            paragraphs = [p.strip() for p in response_text.split('\n\n') if p.strip()]
            for i, para in enumerate(paragraphs[:expected_steps], 1):
                sanitized = sanitize_narration_step({
                    "step_index": i,
                    "narration_text": para
                })
                steps.append(NarrationStep(**sanitized))
        
        # 验证结果
        steps_dict_list = [s.dict() for s in steps]
        is_valid, error_msg = validate_narration_steps(steps_dict_list)
        if not is_valid:
            # 如果验证失败，至少返回清理后的步骤
            steps = [NarrationStep(**sanitize_narration_step(s.dict())) for s in steps]
        
        return steps
    
    def get_provider_name(self) -> str:
        return "gemini"

