"""
核心数据模型 —— 贯穿全系统的数据结构定义
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ==================== 用户相关 ====================

class RiskLevel(str, Enum):
    """投资者风险等级"""
    CONSERVATIVE = "保守型"      # C1
    STEADY = "稳健型"             # C2
    BALANCED = "平衡型"           # C3
    GROWTH = "成长型"             # C4
    AGGRESSIVE = "进取型"         # C5

    @property
    def level_num(self) -> int:
        return {"保守型": 1, "稳健型": 2, "平衡型": 3, "成长型": 4, "进取型": 5}[self.value]


class UserProfile(BaseModel):
    """用户画像（脱敏后）"""
    user_id: str = "anonymous"
    nickname: str = "用户***"
    risk_level: RiskLevel = RiskLevel.CONSERVATIVE
    age_range: str = "**-**"           # 年龄段（脱敏）
    income_range: str = "****"        # 收入区间（脱敏）
    holding_products: list[str] = Field(default_factory=list)
    investment_preference: list[str] = Field(default_factory=list)
    knowledge_level: str = "入门"      # 认知水平：入门/进阶/专业
    conversation_history_count: int = 0


class ChatMessage(BaseModel):
    """对话消息"""
    role: str  # user / assistant / system / tool
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ==================== RAG检索 ====================

class RetrievedChunk(BaseModel):
    """RAG检索到的知识片段"""
    content: str
    source: str               # 来源文件/文档名
    page: Optional[int] = None
    score: float = 0.0        # 相似度得分
    chunk_id: str = ""


class RAGRetrievalResult(BaseModel):
    """RAG检索结果（附带来源标注，亮点二）"""
    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    retrieval_strategy: str = ""   # 检索策略说明（Agentic RAG）
    sources: list[str] = Field(default_factory=list)  # 来源汇总


# ==================== Agent推理 ====================

class AgentThought(BaseModel):
    """Agent推理步骤（XAI可解释，亮点四）"""
    agent_name: str
    thought: str              # 思考内容
    action: str = ""          # 执行动作
    action_input: str = ""    # 动作输入
    observation: str = ""     # 观察结果
    timestamp: datetime = Field(default_factory=datetime.now)


class RecommendationItem(BaseModel):
    """单条理财推荐"""
    product_name: str
    product_type: str            # 存款/理财/基金/保险等
    risk_level: str              # 产品风险等级
    expected_return_range: str   # 预期收益区间
    recommended_reason: str      # 推荐理由（XAI）
    allocation_ratio: float = 0.0  # 配置比例
    data_source: str = ""        # 数据来源（RAG来源标注）
    compliance_passed: bool = True


class WealthPlan(BaseModel):
    """理财配置方案"""
    plan_id: str = ""
    user_id: str = "anonymous"
    created_at: datetime = Field(default_factory=datetime.now)
    total_assets: str = "****"   # 脱敏
    risk_level: RiskLevel = RiskLevel.CONSERVATIVE
    market_analysis: str = ""
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    risk_disclosure: str = ""
    reasoning_chain: list[AgentThought] = Field(default_factory=list)  # 推理链


# ==================== 合规审查 ====================

class ComplianceCheckResult(BaseModel):
    """合规审查结果（亮点七、八）"""
    passed: bool = True
    violated_rules: list[str] = Field(default_factory=list)
    intercepted_content: str = ""    # 被拦截内容
    sanitized_content: str = ""      # 处理后内容
    risk_warnings: list[str] = Field(default_factory=list)
    audit_id: str = ""


class AuditRecord(BaseModel):
    """审计记录（全链路留痕）"""
    audit_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: str = ""
    agent_name: str = ""
    input_content: str = ""
    output_content: str = ""
    compliance_result: Optional[ComplianceCheckResult] = None
    reasoning_chain: list[AgentThought] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
