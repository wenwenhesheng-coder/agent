"""
计算器工具集 —— 资产配置、收益测算、风险量化

亮点三：大小模型协同，大模型Agent通过工具调用小模型完成精准计算
"""
from __future__ import annotations

from tools.base import BaseTool
from models.quant_models import (
    asset_allocation_model,
    yield_model,
    risk_quant_model,
)
from core.models import RiskLevel
from loguru import logger


class AssetAllocationTool(BaseTool):
    """资产配置计算工具"""

    name = "calculate_asset_allocation"
    description = (
        "基于用户风险等级调用量化模型计算资产配置方案。"
        "返回各类资产配置比例、预期收益、波动率、夏普比率等。"
        "大模型负责解读结果并生成可读建议。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "risk_level": {
                "type": "string",
                "description": "风险等级：保守型/稳健型/平衡型/成长型/进取型",
            },
            "preferences": {
                "type": "array",
                "items": {"type": "string"},
                "description": "用户偏好关键词，如['流动性','稳健','黄金']",
            },
        },
        "required": ["risk_level"],
    }

    async def execute(
        self,
        risk_level: str = "稳健型",
        preferences: list[str] | None = None,
    ) -> str:
        logger.info(f"资产配置计算: risk={risk_level}, prefs={preferences}")
        try:
            level = RiskLevel(risk_level)
        except ValueError:
            level = RiskLevel.STEADY

        result = asset_allocation_model.calculate(level, None, preferences)

        lines = [
            f"【资产配置方案 - {result.strategy}】\n",
            "配置比例：",
        ]
        for k, v in result.allocations.items():
            lines.append(f"  {k}: {v*100:.1f}%")
        lines.extend([
            f"\n预期年化收益率：{result.expected_return*100:.2f}%",
            f"预期年化波动率：{result.expected_volatility*100:.2f}%",
            f"预估最大回撤：{result.max_drawdown_estimate*100:.2f}%",
            f"夏普比率：{result.sharpe_ratio:.2f}",
            f"\n【风险解释】{result.risk_explanation}",
        ])
        return "\n".join(lines)


class YieldCalculationTool(BaseTool):
    """收益测算工具"""

    name = "calculate_yield"
    description = (
        "收益测算工具，支持三种计算模式：\n"
        "1. compound - 一次性投资复利计算\n"
        "2. sip - 月定投复利测算\n"
        "3. product - 理财产品到期收益测算"
    )
    parameters = {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["compound", "sip", "product"],
                "description": "计算模式",
            },
            "principal": {"type": "number", "description": "本金（元）"},
            "monthly_invest": {"type": "number", "description": "月定投金额(sip模式)"},
            "annual_rate": {"type": "number", "description": "年化收益率(小数,如0.045)"},
            "years": {"type": "integer", "description": "投资年限"},
            "term_days": {"type": "integer", "description": "产品期限天数(product模式)"},
        },
        "required": ["mode", "annual_rate"],
    }

    async def execute(
        self,
        mode: str = "compound",
        principal: float = 10000,
        monthly_invest: float = 1000,
        annual_rate: float = 0.045,
        years: int = 3,
        term_days: int = 90,
    ) -> str:
        logger.info(f"收益测算: mode={mode}, rate={annual_rate}")

        if mode == "compound":
            r = yield_model.calculate_compound(principal, annual_rate, years)
        elif mode == "sip":
            r = yield_model.calculate_sip(monthly_invest, annual_rate, years)
        elif mode == "product":
            r = yield_model.calculate_product_yield(principal, annual_rate, term_days)
        else:
            return f"未知模式: {mode}"

        return self._format_result(r)


class RiskQuantificationTool(BaseTool):
    """风险量化工具"""

    name = "calculate_risk_quant"
    description = (
        "风险量化计算工具，支持：\n"
        "1. var - VaR在险价值计算（估算组合最大可能损失）\n"
        "2. stress - 压力测试（不同市场压力场景下的组合预估损失）"
    )
    parameters = {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["var", "stress"],
                "description": "计算模式",
            },
            "portfolio_value": {"type": "number", "description": "组合价值(元)"},
            "volatility": {"type": "number", "description": "年化波动率(var模式)"},
            "confidence": {"type": "number", "description": "置信度0.90/0.95/0.99"},
            "holding_days": {"type": "integer", "description": "持有期天数"},
            "allocations": {
                "type": "object",
                "description": "资产配置比例字典(stress模式)",
            },
            "scenario": {
                "type": "string",
                "enum": ["轻度压力", "中度压力", "极端压力"],
                "description": "压力场景",
            },
        },
        "required": ["mode", "portfolio_value"],
    }

    async def execute(
        self,
        mode: str = "var",
        portfolio_value: float = 100000,
        volatility: float = 0.05,
        confidence: float = 0.95,
        holding_days: int = 1,
        allocations: dict | None = None,
        scenario: str = "中度压力",
    ) -> str:
        logger.info(f"风险量化: mode={mode}, value={portfolio_value}")

        if mode == "var":
            r = risk_quant_model.calculate_var(
                portfolio_value, volatility, confidence, holding_days
            )
        elif mode == "stress":
            if not allocations:
                allocations = {"银行理财R1-R2(固收)": 0.6, "固收+基金": 0.3, "混合型基金": 0.1}
            r = risk_quant_model.stress_test(portfolio_value, allocations, scenario)
        else:
            return f"未知模式: {mode}"

        return self._format_result(r)
