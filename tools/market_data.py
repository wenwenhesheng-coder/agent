"""
市场行情数据工具

亮点二：通过API网关接入市场行情、基金净值等结构化数据，
与大模型RAG向量化处理的长文本（研报）融合。
"""
from __future__ import annotations

from datetime import datetime, timedelta
import random

from tools.base import BaseTool
from loguru import logger


# 模拟市场行情数据（实际对接银行行情API）
def _mock_market_data() -> dict:
    """生成模拟市场行情快照（带时间戳）"""
    random.seed(int(datetime.now().timestamp()) % 1000)
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "indices": {
            "上证指数": {"value": round(3100 + random.uniform(-50, 50), 2), "change_pct": round(random.uniform(-1.5, 1.5), 2)},
            "深证成指": {"value": round(9500 + random.uniform(-100, 100), 2), "change_pct": round(random.uniform(-1.8, 1.8), 2)},
            "沪深300": {"value": round(3600 + random.uniform(-60, 60), 2), "change_pct": round(random.uniform(-1.5, 1.5), 2)},
            "创业板指": {"value": round(1900 + random.uniform(-40, 40), 2), "change_pct": round(random.uniform(-2.0, 2.0), 2)},
        },
        "bonds": {
            "10年国债收益率": f"{round(2.30 + random.uniform(-0.05, 0.05), 2)}%",
            "10年国开债收益率": f"{round(2.45 + random.uniform(-0.05, 0.05), 2)}%",
        },
        "gold": {
            "上海金(Au99.99)": f"{round(580 + random.uniform(-10, 10), 2)}元/克",
        },
        "funds_nav": {
            "天天盈货币7日年化": f"{round(2.20 + random.uniform(-0.1, 0.1), 3)}%",
            "鑫鑫稳利90天业绩比较基准": "3.8%-4.2%",
            "臻享纯债180天成立以来年化": f"{round(4.50 + random.uniform(-0.2, 0.2), 2)}%",
        },
        "macro": {
            "货币政策": "稳健偏宽松，LPR维持低位",
            "通胀": "CPI温和回升，PPI降幅收窄",
            "汇率": "人民币汇率双向波动",
        },
    }


class MarketDataTool(BaseTool):
    """市场行情数据工具"""

    name = "get_market_data"
    description = (
        "获取实时市场行情数据，包括股票指数、债券收益率、黄金价格、"
        "基金净值等。大模型结合市场数据与研报分析市场环境。"
        "数据来源：银行行情API网关（演示为模拟数据）。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["all", "indices", "bonds", "gold", "funds", "macro"],
                "description": "查询类别，默认all",
                "default": "all",
            },
        },
        "required": [],
    }

    async def execute(self, category: str = "all") -> str:
        logger.info(f"市场数据查询: category={category}")
        data = _mock_market_data()

        if category == "all":
            lines = [f"【市场行情快照 {data['timestamp']}】\n"]
            for cat_name, cat_data in data.items():
                if cat_name == "timestamp":
                    continue
                lines.append(f"▸ {self._cat_label(cat_name)}：")
                for k, v in cat_data.items():
                    if isinstance(v, dict):
                        lines.append(f"  {k}: {v['value']} ({'+' if v['change_pct']>=0 else ''}{v['change_pct']}%)")
                    else:
                        lines.append(f"  {k}: {v}")
                lines.append("")
            lines.append("来源：银行行情API网关（演示为模拟数据）")
            return "\n".join(lines)

        cat_data = data.get(category, {})
        if not cat_data:
            return f"未知类别: {category}"

        lines = [f"【{self._cat_label(category)}行情 {data['timestamp']}】\n"]
        for k, v in cat_data.items():
            if isinstance(v, dict):
                lines.append(f"{k}: {v['value']} ({'+' if v['change_pct']>=0 else ''}{v['change_pct']}%)")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

    def _cat_label(self, cat: str) -> str:
        return {
            "indices": "股票指数",
            "bonds": "债券收益率",
            "gold": "贵金属",
            "funds": "基金净值/业绩",
            "macro": "宏观面",
        }.get(cat, cat)
