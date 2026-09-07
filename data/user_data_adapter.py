"""
用户数据适配器

对接银行现有系统（手机银行APP、小程序、客服系统），
读取用户风险测评结果（权限可控，数据安全脱敏）。
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from data.data_masking import DataMasking


# 模拟银行用户数据库（实际对接银行API）
MOCK_USER_DB: dict[str, dict] = {
    "user_001": {
        "user_id": "user_001",
        "name": "张三",
        "phone": "13812345678",
        "id_card": "310101199001011234",
        "bank_account": "6222021234567890123",
        "age": 35,
        "income": 15000,
        "balance": 85000,
        "risk_level": "稳健型",
        "risk_level_num": 2,
        "has_experience": True,
        "knowledge_level": "进阶",
        "holding_products": ["天天盈货币基金", "鑫鑫稳利90天理财"],
    },
    "user_002": {
        "user_id": "user_002",
        "name": "李四",
        "phone": "13987654321",
        "id_card": "440101199203034567",
        "bank_account": "622202987654321098",
        "age": 28,
        "income": 8000,
        "balance": 23000,
        "risk_level": "保守型",
        "risk_level_num": 1,
        "has_experience": False,
        "knowledge_level": "入门",
        "holding_products": [],
    },
}


class UserDataAdapter:
    """
    用户数据适配器
    - 对接银行系统API（演示为模拟数据）
    - 读取用户风险测评结果
    - 数据脱敏后才返回给智能体
    - 权限可控：智能体只能访问脱敏后的风险标签
    """

    def __init__(self):
        self._db = MOCK_USER_DB

    def get_user_profile(self, user_id: str) -> dict:
        """
        获取脱敏后的用户画像
        智能体只能访问此方法返回的数据
        """
        raw = self._db.get(user_id, {
            "user_id": user_id,
            "risk_level": "保守型",
            "risk_level_num": 1,
            "has_experience": False,
            "knowledge_level": "入门",
        })
        # 只返回脱敏后的安全画像
        safe_profile = DataMasking.generate_safe_profile(raw)
        safe_profile["holding_products"] = raw.get("holding_products", [])
        logger.info(f"用户数据适配器返回脱敏画像: {safe_profile}")
        return safe_profile

    def get_risk_level(self, user_id: str) -> tuple[str, int]:
        """获取用户风险等级（脱敏访问）"""
        profile = self.get_user_profile(user_id)
        return profile.get("risk_level", "保守型"), profile.get("risk_level_num", 1)

    def get_holding_products(self, user_id: str) -> list[str]:
        """获取用户持有产品列表"""
        profile = self._db.get(user_id, {})
        return profile.get("holding_products", [])

    def update_risk_assessment(self, user_id: str, risk_level: str, risk_num: int) -> None:
        """更新用户风险测评结果（写回银行系统）"""
        if user_id in self._db:
            self._db[user_id]["risk_level"] = risk_level
            self._db[user_id]["risk_level_num"] = risk_num
            logger.info(f"用户{user_id}风险测评已更新: {risk_level}(R{risk_num})")


# 全局单例
user_data_adapter = UserDataAdapter()
