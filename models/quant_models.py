"""
量化小模型模块 —— 亮点三：大小模型协同

大模型负责语义理解、意图识别、对话生成；
小模型负责资产配置计算、风险量化、收益预测等数值计算任务。
通过API被大模型Agent调用，实现协同。
"""
from __future__ import annotations

import numpy as np
from typing import Any
from pydantic import BaseModel, Field

from core.models import RiskLevel
from loguru import logger


# ==================== 资产配置小模型 ====================

class AssetAllocationResult(BaseModel):
    """资产配置计算结果"""
    strategy: str
    allocations: dict[str, float] = Field(default_factory=dict)  # {产品类别: 比例}
    expected_return: float = 0.0       # 预期年化收益
    expected_volatility: float = 0.0   # 预期波动率
    max_drawdown_estimate: float = 0.0 # 预估最大回撤
    sharpe_ratio: float = 0.0          # 夏普比率
    risk_explanation: str = ""         # 风险解释（XAI）


# 经典资产类别预期参数（示例数据，实际应从市场数据接口获取）
ASSET_CLASS_PARAMS: dict[str, dict[str, float]] = {
    "货币基金/活期理财": {"expected_return": 0.025, "volatility": 0.003, "risk_score": 1},
    "银行理财R1-R2(固收)": {"expected_return": 0.045, "volatility": 0.015, "risk_score": 2},
    "纯债基金": {"expected_return": 0.050, "volatility": 0.025, "risk_score": 2},
    "固收+基金": {"expected_return": 0.065, "volatility": 0.045, "risk_score": 3},
    "混合型基金": {"expected_return": 0.085, "volatility": 0.120, "risk_score": 3},
    "股票型/指数基金": {"expected_return": 0.110, "volatility": 0.220, "risk_score": 4},
    "黄金/贵金属": {"expected_return": 0.060, "volatility": 0.150, "risk_score": 4},
    "REITs": {"expected_return": 0.070, "volatility": 0.130, "risk_score": 3},
    "QDII海外权益": {"expected_return": 0.090, "volatility": 0.180, "risk_score": 4},
    "权益类衍生品": {"expected_return": 0.150, "volatility": 0.350, "risk_score": 5},
}


# 各风险等级对应的资产配置权重模板（教科书经典策略）
RISK_ALLOCATION_TEMPLATES: dict[RiskLevel, dict[str, float]] = {
    RiskLevel.CONSERVATIVE: {
        "货币基金/活期理财": 0.20,
        "银行理财R1-R2(固收)": 0.50,
        "纯债基金": 0.20,
        "黄金/贵金属": 0.05,
        "固收+基金": 0.05,
    },
    RiskLevel.STEADY: {
        "货币基金/活期理财": 0.10,
        "银行理财R1-R2(固收)": 0.45,
        "纯债基金": 0.15,
        "固收+基金": 0.20,
        "混合型基金": 0.05,
        "黄金/贵金属": 0.05,
    },
    RiskLevel.BALANCED: {
        "货币基金/活期理财": 0.05,
        "银行理财R1-R2(固收)": 0.30,
        "纯债基金": 0.10,
        "固收+基金": 0.25,
        "混合型基金": 0.15,
        "股票型/指数基金": 0.10,
        "黄金/贵金属": 0.05,
    },
    RiskLevel.GROWTH: {
        "银行理财R1-R2(固收)": 0.15,
        "固收+基金": 0.20,
        "混合型基金": 0.25,
        "股票型/指数基金": 0.25,
        "黄金/贵金属": 0.10,
        "REITs": 0.05,
    },
    RiskLevel.AGGRESSIVE: {
        "固收+基金": 0.10,
        "混合型基金": 0.25,
        "股票型/指数基金": 0.35,
        "QDII海外权益": 0.15,
        "黄金/贵金属": 0.10,
        "REITs": 0.05,
    },
}


class AssetAllocationModel:
    """
    资产配置计算小模型
    实现均值-方差框架 + 风险等级约束
    大模型Agent通过API调用此小模型完成精准计算
    """

    def calculate(
        self,
        risk_level: RiskLevel,
        total_assets: float | None = None,
        preferences: list[str] | None = None,
    ) -> AssetAllocationResult:
        """
        计算资产配置方案
        Args:
            risk_level: 用户风险等级
            total_assets: 总资产（可选，脱敏场景可不传）
            preferences: 用户偏好（影响权重微调）
        """
        logger.info(f"资产配置小模型计算: risk_level={risk_level.value}")

        # 获取模板权重
        weights = RISK_ALLOCATION_TEMPLATES.get(risk_level, RISK_ALLOCATION_TEMPLATES[RiskLevel.STEADY]).copy()

        # 用户偏好微调
        if preferences:
            weights = self._adjust_for_preferences(weights, preferences)

        # 归一化
        total_w = sum(weights.values())
        weights = {k: round(v / total_w, 4) for k, v in weights.items()}

        # 计算预期收益与波动率
        expected_return = sum(
            weights[k] * ASSET_CLASS_PARAMS.get(k, {}).get("expected_return", 0)
            for k in weights
        )
        # 简化波动率（假设资产类间相关性较低，取加权平均的近似）
        weighted_vol = sum(
            weights[k] * ASSET_CLASS_PARAMS.get(k, {}).get("volatility", 0)
            for k in weights
        )
        # 分散效应修正
        n = len(weights)
        expected_volatility = weighted_vol * (0.6 + 0.4 / n)  # 简化分散效应

        # 夏普比率（假设无风险利率2%）
        risk_free = 0.02
        sharpe = (
            (expected_return - risk_free) / expected_volatility
            if expected_volatility > 0 else 0
        )

        # 预估最大回撤（经验公式）
        max_dd = expected_volatility * 2.5

        # 风险解释（XAI）
        risk_explanation = self._generate_risk_explanation(
            risk_level, expected_return, expected_volatility, max_dd
        )

        return AssetAllocationResult(
            strategy=f"{risk_level.value}配置策略",
            allocations=weights,
            expected_return=round(expected_return, 4),
            expected_volatility=round(expected_volatility, 4),
            max_drawdown_estimate=round(max_dd, 4),
            sharpe_ratio=round(sharpe, 4),
            risk_explanation=risk_explanation,
        )

    def _adjust_for_preferences(
        self,
        weights: dict[str, float],
        preferences: list[str],
    ) -> dict[str, float]:
        """根据用户偏好微调权重"""
        prefs = "".join(preferences)
        if "流动性" in prefs or "灵活" in prefs:
            weights["货币基金/活期理财"] = weights.get("货币基金/活期理财", 0) + 0.10
        if "稳健" in prefs or "保守" in prefs:
            for k in weights:
                if "权益" in k or "基金" in k and "固收" not in k:
                    weights[k] *= 0.8
        if "黄金" in prefs:
            weights["黄金/贵金属"] = weights.get("黄金/贵金属", 0) + 0.05
        return weights

    def _generate_risk_explanation(
        self,
        risk_level: RiskLevel,
        ret: float,
        vol: float,
        max_dd: float,
    ) -> str:
        """生成风险解释（XAI可解释，亮点四）"""
        return (
            f"配置策略匹配风险等级「{risk_level.value}」。"
            f"预期年化收益率约{ret*100:.1f}%，预期年化波动率约{vol*100:.1f}%，"
            f"极端情形下最大回撤可能达到约{max_dd*100:.1f}%。"
            f"收益与风险成正比，该配置以固收类资产为底仓获取稳定票息，"
            f"并通过少量权益/另类资产增强收益弹性。"
            f"过往业绩不预示未来表现，实际收益与波动可能偏离预期。"
        )


# ==================== 收益测算小模型 ====================

class YieldCalculationModel:
    """收益测算小模型：复利计算、定投测算、到期收益测算"""

    def calculate_compound(
        self,
        principal: float,
        annual_rate: float,
        years: int,
    ) -> dict:
        """复利计算"""
        final = principal * (1 + annual_rate) ** years
        interest = final - principal
        return {
            "本金": principal,
            "年化收益率": annual_rate,
            "投资期限": years,
            "到期本息": round(final, 2),
            "利息收入": round(interest, 2),
        }

    def calculate_sip(
        self,
        monthly_invest: float,
        annual_rate: float,
        years: int,
    ) -> dict:
        """定投测算（月定投复利）"""
        monthly_rate = annual_rate / 12
        n = years * 12
        # 定投终值公式: PMT * [((1+r)^n - 1) / r]
        if monthly_rate == 0:
            final = monthly_invest * n
        else:
            factor = ((1 + monthly_rate) ** n - 1) / monthly_rate
            final = monthly_invest * factor
        total_invest = monthly_invest * n
        interest = final - total_invest
        return {
            "月定投金额": monthly_invest,
            "年化收益率": annual_rate,
            "定投年限": years,
            "累计投入": round(total_invest, 2),
            "到期总额": round(final, 2),
            "利息收入": round(interest, 2),
        }

    def calculate_product_yield(
        self,
        principal: float,
        product_rate: float,
        term_days: int,
        is_compound: bool = False,
    ) -> dict:
        """理财产品到期收益测算"""
        if is_compound:
            final = principal * (1 + product_rate) ** (term_days / 365)
        else:
            final = principal * (1 + product_rate * term_days / 365)
        interest = final - principal
        return {
            "本金": principal,
            "产品年化": product_rate,
            "期限(天)": term_days,
            "到期本息": round(final, 2),
            "利息收入": round(interest, 2),
            "日均收益": round(interest / term_days, 2),
        }


# ==================== 风险量化小模型 ====================

class RiskQuantificationModel:
    """风险量化小模型：VaR、压力测试"""

    def calculate_var(
        self,
        portfolio_value: float,
        volatility: float,
        confidence: float = 0.95,
        holding_days: int = 1,
    ) -> dict:
        """
        VaR（在险价值）计算
        Args:
            portfolio_value: 组合价值
            volatility: 年化波动率
            confidence: 置信度（0.90/0.95/0.99）
            holding_days: 持有期天数
        """
        from scipy.stats import norm

        z_scores = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
        z = z_scores.get(confidence, 1.645)
        daily_vol = volatility / np.sqrt(252)
        var = portfolio_value * z * daily_vol * np.sqrt(holding_days)
        return {
            "组合价值": portfolio_value,
            "年化波动率": volatility,
            "置信度": confidence,
            "持有期(天)": holding_days,
            "VaR": round(var, 2),
            "VaR占比": f"{var/portfolio_value*100:.2f}%",
            "解释": (
                f"在{confidence*100:.0f}%置信度下，持有{holding_days}天，"
                f"组合最大可能损失不超过{var:.2f}元（占比{var/portfolio_value*100:.2f}%）。"
            ),
        }

    def stress_test(
        self,
        portfolio_value: float,
        allocations: dict[str, float],
        scenario: str = "中度压力",
    ) -> dict:
        """压力测试"""
        # 简化压力场景下的资产类别冲击幅度
        stress_impacts: dict[str, dict[str, float]] = {
            "轻度压力": {"货币基金/活期理财": -0.01, "银行理财R1-R2(固收)": -0.02,
                        "纯债基金": -0.03, "固收+基金": -0.05, "混合型基金": -0.08,
                        "股票型/指数基金": -0.12, "黄金/贵金属": -0.06, "REITs": -0.05},
            "中度压力": {"货币基金/活期理财": -0.01, "银行理财R1-R2(固收)": -0.04,
                        "纯债基金": -0.06, "固收+基金": -0.10, "混合型基金": -0.15,
                        "股票型/指数基金": -0.25, "黄金/贵金属": -0.10, "REITs": -0.08},
            "极端压力": {"货币基金/活期理财": -0.02, "银行理财R1-R2(固收)": -0.08,
                        "纯债基金": -0.12, "固收+基金": -0.20, "混合型基金": -0.30,
                        "股票型/指数基金": -0.40, "黄金/贵金属": -0.15, "REITs": -0.12},
        }
        impacts = stress_impacts.get(scenario, stress_impacts["中度压力"])
        total_loss = sum(
            portfolio_value * allocations.get(k, 0) * impacts.get(k, -0.10)
            for k in allocations
        )
        return {
            "场景": scenario,
            "组合价值": portfolio_value,
            "预估损失": round(total_loss, 2),
            "损失占比": f"{total_loss/portfolio_value*100:.2f}%",
            "解释": f"在「{scenario}」场景下，组合预估损失约{total_loss:.2f}元"
                    f"（占比{total_loss/portfolio_value*100:.2f}%）。",
        }


# 全局单例
asset_allocation_model = AssetAllocationModel()
yield_model = YieldCalculationModel()
risk_quant_model = RiskQuantificationModel()
