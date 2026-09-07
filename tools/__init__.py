"""
Agent 工具集 —— 智能体可自主调用的工具

工具调用能力（架构层2核心）：
- 理财产品知识库查询
- 用户风险测评工具
- 资产计算器
- 收益测算工具
- 风险规则库
- 监管条文库
- 市场行情数据
"""
from tools.base import BaseTool, ToolRegistry
from tools.product_kb import ProductKnowledgeBaseTool
from tools.risk_assessment import RiskAssessmentTool
from tools.calculators import (
    AssetAllocationTool,
    YieldCalculationTool,
    RiskQuantificationTool,
)
from tools.regulation_kb import RegulationKnowledgeBaseTool
from tools.market_data import MarketDataTool

# 工具注册表全局实例
tool_registry = ToolRegistry()
tool_registry.register(ProductKnowledgeBaseTool())
tool_registry.register(RiskAssessmentTool())
tool_registry.register(AssetAllocationTool())
tool_registry.register(YieldCalculationTool())
tool_registry.register(RiskQuantificationTool())
tool_registry.register(RegulationKnowledgeBaseTool())
tool_registry.register(MarketDataTool())

__all__ = [
    "BaseTool", "ToolRegistry", "tool_registry",
    "ProductKnowledgeBaseTool", "RiskAssessmentTool",
    "AssetAllocationTool", "YieldCalculationTool",
    "RiskQuantificationTool", "RegulationKnowledgeBaseTool",
    "MarketDataTool",
]
