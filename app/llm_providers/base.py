"""LLM 客户端基类接口"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.models.schemas import SolutionStep, NarrationStep, VerificationResult


class LLMClient(ABC):
    """LLM 客户端抽象基类"""
    
    @abstractmethod
    def solve(
        self, 
        problem_text: str, 
        meta: Optional[Dict[str, Any]] = None
    ) -> List[SolutionStep]:
        """
        调用 LLM 解题
        
        Args:
            problem_text: 题目文本
            meta: 元数据（题型、难度等）
            
        Returns:
            结构化的解题步骤列表
        """
        pass
    
    @abstractmethod
    def narrate(
        self,
        problem_text: str,
        solution_steps: List[SolutionStep],
        meta: Optional[Dict[str, Any]] = None
    ) -> List[NarrationStep]:
        """
        调用 LLM 生成讲解脚本
        
        Args:
            problem_text: 题目文本
            solution_steps: 解题步骤
            meta: 元数据
            
        Returns:
            TTS友好的讲解步骤列表
        """
        pass
    
    @abstractmethod
    def verify(
        self,
        problem_text: str,
        solution_steps: List[SolutionStep],
        meta: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """
        交叉验证解题步骤是否正确

        Args:
            problem_text: 题目文本
            solution_steps: 待验证的解题步骤
            meta: 元数据

        Returns:
            VerificationResult
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """返回提供商名称"""
        pass

