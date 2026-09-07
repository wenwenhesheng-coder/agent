"""
监管条文库查询工具

智能体可调用此工具查询监管条文，
用于回答合规问题、生成风险提示、校验输出合规性。
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.base import BaseTool
from config.settings import BASE_DIR
from loguru import logger

_REGULATIONS_FILE = BASE_DIR / "data" / "samples" / "regulations.json"


def _load_regulations() -> list[dict]:
    if _REGULATIONS_FILE.exists():
        with open(_REGULATIONS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


class RegulationKnowledgeBaseTool(BaseTool):
    """监管条文库查询工具"""

    name = "query_regulation_kb"
    description = (
        "查询银行理财相关监管条文知识库，可获取资管新规、适当性管理办法、"
        "金融营销宣传规定等监管要求。用于回答合规问题、校验输出合规性。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "查询关键词，如'保本''适当性''刚性兑付'",
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str = "") -> str:
        regulations = _load_regulations()
        logger.info(f"监管KB查询: query='{query}'")

        if not query:
            lines = ["【监管条文库目录】\n"]
            for reg in regulations:
                lines.append(f"- [{reg['regulation_id']}] {reg['title']}")
                lines.append(f"  发布机构：{reg['issuer']}，生效：{reg['effective_date']}")
            return "\n".join(lines)

        # 关键词匹配监管条文与规则
        matched_rules = []
        for reg in regulations:
            title_match = query in reg["title"]
            rule_matches = [
                (reg, rule) for rule in reg["key_rules"] if query in rule
            ]
            if title_match or rule_matches:
                matched_rules.append((reg, rule_matches))

        if not matched_rules:
            return f"未找到与'{query}'相关的监管条文。"

        lines = [f"【查询结果：'{query}'相关监管条文】\n"]
        for reg, rules in matched_rules:
            lines.append(f"■ {reg['title']}（{reg['regulation_id']}）")
            lines.append(f"  发布：{reg['issuer']}，生效：{reg['effective_date']}")
            if rules:
                for _, rule in rules:
                    lines.append(f"  ▸ {rule}")
            else:
                for rule in reg["key_rules"]:
                    lines.append(f"  ▸ {rule}")
            lines.append(f"  来源：{reg['source']}\n")

        return "\n".join(lines)
