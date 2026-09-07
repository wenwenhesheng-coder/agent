"""
理财产品知识库查询工具

智能体可调用此工具查询理财产品信息，
优先从知识库获取真实业务数据，抑制幻觉。
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.base import BaseTool
from config.settings import BASE_DIR, settings
from loguru import logger

# 加载产品数据
_PRODUCTS_FILE = BASE_DIR / "data" / "samples" / "products.json"


def _load_products() -> list[dict]:
    if _PRODUCTS_FILE.exists():
        with open(_PRODUCTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


class ProductKnowledgeBaseTool(BaseTool):
    """理财产品知识库查询工具"""

    name = "query_product_kb"
    description = (
        "查询银行理财产品知识库，可获取真实产品信息（风险等级、收益、期限、"
        "赎回规则等）。支持按产品名称、风险等级、类型查询。"
        "用于回答用户关于具体产品的问题，确保数据来自真实知识库而非模型生成。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "查询关键词，如产品名称、风险等级（R2）、类型（固收）",
            },
            "risk_level_max": {
                "type": "integer",
                "description": "用户风险等级对应的最大产品风险等级，用于适当性筛选",
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str = "", risk_level_max: int | None = None) -> str:
        products = _load_products()
        logger.info(f"产品KB查询: query='{query}', risk_max={risk_level_max}")

        # 风险等级筛选（适当性管理）
        if risk_level_max is not None:
            products = [p for p in products if p["risk_level_num"] <= risk_level_max]

        # 关键词匹配
        if query:
            q = query.lower()
            matched = []
            for p in products:
                if (q in p["product_name"].lower()
                    or q in p["product_type"].lower()
                    or q in p["risk_level"].lower()
                    or q in p.get("investment_scope", "").lower()):
                    matched.append(p)
            products = matched if matched else products[:5]

        if not products:
            return "未找到匹配的理财产品。请尝试其他关键词。"

        # 格式化输出（带来源标注，亮点二）
        lines = [f"共找到 {len(products)} 款匹配产品：\n"]
        for p in products[:5]:
            lines.append(
                f"【{p['product_name']}】({p['product_id']})\n"
                f"  类型：{p['product_type']}\n"
                f"  风险等级：{p['risk_level']}\n"
                f"  预期年化：{p['expected_annual_return']}\n"
                f"  期限：{p['term']}\n"
                f"  起购金额：{p['min_purchase_amount']}元\n"
                f"  赎回规则：{p['redemption_rule']}\n"
                f"  投资范围：{p['investment_scope']}\n"
                f"  来源：{p['disclosure_source']}\n"
            )
        return "\n".join(lines)
