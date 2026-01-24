"""API 请求和响应的数据模型"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ProblemInput(BaseModel):
    """题目输入模型"""
    text: str = Field(..., description="题目文本（支持 Markdown/LaTeX）")
    topic: Optional[str] = Field(None, description="题型：如 极限、微分、积分、级数等")
    difficulty: Optional[str] = Field(None, description="难度：如 简单、中等、困难")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")


class SolutionStep(BaseModel):
    """解题步骤模型"""
    step_index: int = Field(..., description="步骤序号")
    title: str = Field(..., description="步骤标题")
    description: str = Field(..., description="步骤描述")
    formula_latex: Optional[str] = Field(None, description="LaTeX 公式")


class SolutionResponse(BaseModel):
    """解题响应模型"""
    problem_text: str = Field(..., description="原始题目文本")
    steps: List[SolutionStep] = Field(..., description="解题步骤列表")
    method: Optional[str] = Field(None, description="解题方法说明")


class NarrationStep(BaseModel):
    """讲解步骤模型"""
    step_index: int = Field(..., description="步骤序号")
    narration_text: str = Field(..., description="TTS友好的讲解文本")


class NarrationResponse(BaseModel):
    """讲解响应模型"""
    problem_text: str = Field(..., description="原始题目文本")
    steps: List[NarrationStep] = Field(..., description="讲解步骤列表")


class ProblemMetadata(BaseModel):
    """题目元数据"""
    id: str = Field(..., description="题目ID")
    created_at: datetime = Field(default_factory=datetime.now)
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

