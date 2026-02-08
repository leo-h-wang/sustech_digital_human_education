import os
import asyncio
from typing import List, Dict

import aiohttp


class GammaGenerator:
    # Gamma API 基础 URL
    BASE_URL = "https://public-api.gamma.app/v1.0"

    def __init__(self) -> None:
        # 从环境变量获取 API Key
        self.api_key = os.getenv("GAMMA_API_KEY")
        if not self.api_key:
            print("Warning: GAMMA_API_KEY not found in environment variables")

        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    async def generate_slides_from_steps(
        self,
        problem_text: str,
        steps: List[Dict],
        export_as: str = "pptx",
    ) -> str:
        """
        核心方法：接收题目和步骤，返回生成的 PPT/PDF 下载链接
        """
        if not self.api_key:
            raise ValueError("GAMMA_API_KEY is not set. Please check your .env file.")

        # 1. 转换 Prompt
        formatted_prompt = self._convert_json_to_prompt(problem_text, steps)

        async with aiohttp.ClientSession(headers=self.headers) as session:
            # 2. 提交任务
            generation_id = await self._start_generation(
                session,
                formatted_prompt,
                steps,
                export_as=export_as,
            )
            print(f"[Gamma] Task started, ID: {generation_id}")

            # 3. 轮询结果
            result = await self._poll_for_completion(session, generation_id)
            file_url = (
                result.get("fileUrl")
                or result.get("output", {}).get("pptxUrl")
                or result.get("output", {}).get("pdfUrl")
                or result.get("gammaUrl")
            )
            print(f"[Gamma] Generation complete: {file_url}")
            return file_url

    async def generate_slides_assets(self, problem_text: str, steps: List[Dict]) -> Dict[str, str]:
        """
        生成 PPTX 和 PDF 下载链接（分别生成），返回 Gamma 页面链接
        """
        if not self.api_key:
            raise ValueError("GAMMA_API_KEY is not set. Please check your .env file.")

        formatted_prompt = self._convert_json_to_prompt(problem_text, steps)

        async with aiohttp.ClientSession(headers=self.headers) as session:
            pptx_id, pdf_id = await asyncio.gather(
                self._start_generation(session, formatted_prompt, steps, export_as="pptx"),
                self._start_generation(session, formatted_prompt, steps, export_as="pdf"),
            )
            print(f"[Gamma] PPTX task started, ID: {pptx_id}")
            print(f"[Gamma] PDF task started, ID: {pdf_id}")

            pptx_result, pdf_result = await asyncio.gather(
                self._poll_for_completion(session, pptx_id),
                self._poll_for_completion(session, pdf_id),
            )

            gamma_url = pptx_result.get("gammaUrl") or pdf_result.get("gammaUrl")
            pptx_url = (
                pptx_result.get("fileUrl")
                or pptx_result.get("output", {}).get("pptxUrl")
                or pptx_result.get("output", {}).get("pdfUrl")
            )
            pdf_url = (
                pdf_result.get("fileUrl")
                or pdf_result.get("output", {}).get("pdfUrl")
                or pdf_result.get("output", {}).get("pptxUrl")
            )

            return {
                "gammaUrl": gamma_url,
                "pptxUrl": pptx_url,
                "pdfUrl": pdf_url,
            }

    def _convert_json_to_prompt(self, problem_text: str, steps: List[Dict]) -> str:
        """
        将 JSON 数据转换为 Gamma 易于理解的结构化 Markdown
        """
        prompt = (
            "Create a step-by-step math solution presentation.\n\n"
            f"# Problem\n{problem_text}\n\n"
            "# Solution Steps\n"
        )

        for idx, step in enumerate(steps, 1):
            # 兼容不同的字段名，根据实际 JSON 调整
            title = step.get("title", f"Step {idx}")
            # 提取内容，优先使用 content 字段
            content = step.get("content") or step.get("text") or step.get("description") or ""

            # 确保 LaTeX 公式格式正确（Gamma 通常识别 $$ 或 $）
            prompt += f"## {title}\n{content}\n\n"

        prompt += (
            "\nRequirements:\n"
            "- Use a clean, educational visual style.\n"
            "- Render LaTeX equations clearly using $$ for block math.\n"
            "- One step per slide."
        )
        return prompt

    async def _start_generation(
        self,
        session: aiohttp.ClientSession,
        prompt: str,
        steps: List[Dict],
        export_as: str | None = None,
    ) -> str:
        url = f"{self.BASE_URL}/generations"
        payload = {
            "inputText": prompt,
            "textMode": "preserve",
            "format": "presentation",
            "numCards": max(len(steps), 1),
            "themeId": "opgltylm2d2fdfs",
            "textOptions": {
                "language": "zh-cn"
            },
        }
        if export_as:
            payload["exportAs"] = export_as
        # 未提供图片时，禁止 Gamma 自动生成图片
        if "http://" not in prompt and "https://" not in prompt:
            payload["imageOptions"] = {"source": "noImages"}

        async with session.post(url, json=payload) as resp:
            if resp.status not in (200, 201):
                error_text = await resp.text()
                raise Exception(f"Gamma API Error {resp.status}: {error_text}")

            data = await resp.json()
            return data["generationId"]

    async def _poll_for_completion(self, session: aiohttp.ClientSession, generation_id: str) -> Dict:
        url = f"{self.BASE_URL}/generations/{generation_id}"

        # 设置超时时间，例如 3 分钟 (60 * 3s)
        for _ in range(60):
            await asyncio.sleep(3)
            async with session.get(url) as resp:
                if resp.status != 200:
                    continue

                data = await resp.json()
                status = data.get("status")

                if status == "completed":
                    return data

                if status == "error":
                    raise Exception("Gamma generation failed with status error.")

        raise Exception("Gamma generation timed out.")

