"""
多智能体协同架构（亮点一核心）

采用多智能体（Multi-Agent）协同架构作为核心设计范式，
而非单一对话机器人。多个专业化Agent协同作业：

1. 客户画像Agent：整合客户行为数据、交易记录、风险测评，构建动态精准用户画像
2. 市场分析Agent：实时接入行情数据、研报、资讯，进行市场解读与趋势研判
3. 产品匹配Agent：基于客户画像与市场判断，动态生成个性化资产配置建议
4. 合规审查Agent：内嵌合规规则引擎，对每一条建议进行合规校验
5. 话术生成Agent：生成个性化营销话术与合规化服务内容

从需求识别到方案输出的完整作战单元。
"""
from agents.base_agent import BaseAgent
from agents.customer_profile_agent import CustomerProfileAgent
from agents.market_analysis_agent import MarketAnalysisAgent
from agents.product_matching_agent import ProductMatchingAgent
from agents.compliance_agent import ComplianceAgent
from agents.dialogue_agent import DialogueAgent
from agents.orchestrator import AgentOrchestrator

__all__ = [
    "BaseAgent",
    "CustomerProfileAgent",
    "MarketAnalysisAgent",
    "ProductMatchingAgent",
    "ComplianceAgent",
    "DialogueAgent",
    "AgentOrchestrator",
]
