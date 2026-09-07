"""
数据脱敏访问机制（亮点九）

智能体不直接存储用户敏感资产数据，
仅通过接口按需调取脱敏后的用户风险标签，
符合金融数据安全要求，解决银行数据安全顾虑。
"""
from __future__ import annotations

import re
from typing import Any

from loguru import logger

from config.settings import settings


class DataMasking:
    """
    数据脱敏处理器
    - 手机号、身份证、银行卡号、余额等敏感字段脱敏
    - 智能体只能访问脱敏后的数据
    """

    # 脱敏规则
    MASK_RULES: dict[str, dict] = {
        "phone": {
            "patterns": [r"1[3-9]\d{9}"],
            "mask_func": lambda m: m.group(0)[:3] + "****" + m.group(0)[-4:],
        },
        "id_card": {
            "patterns": [r"\d{17}[\dXx]", r"\d{15}"],
            "mask_func": lambda m: m.group(0)[:6] + "********" + m.group(0)[-4:],
        },
        "bank_account": {
            "patterns": [r"\d{16,19}"],
            "mask_func": lambda m: m.group(0)[:4] + "****" + m.group(0)[-4:],
        },
        "balance": {
            # 金额脱敏：保留量级，模糊具体数值
            "patterns": [r"余额\s*[:：]?\s*[\d,]+\.?\d*\s*[元万]?"],
            "mask_func": lambda m: self._mask_amount(m.group(0)),
        },
        "email": {
            "patterns": [r"[\w.-]+@[\w.-]+\.\w+"],
            "mask_func": lambda m: m.group(0)[0] + "***@" + m.group(0).split("@")[1],
        },
    }

    @classmethod
    def mask_text(cls, text: str) -> str:
        """对文本中的敏感信息进行脱敏"""
        if not settings.api.enable_data_masking:
            return text
        masked = text
        for field, rule in cls.MASK_RULES.items():
            for pattern in rule["patterns"]:
                masked = re.sub(
                    pattern,
                    lambda m, f=rule["mask_func"]: f(m),
                    masked,
                )
        return masked

    @classmethod
    def _mask_amount(cls, text: str) -> str:
        """金额脱敏：转为区间"""
        nums = re.findall(r"\d+", text)
        if not nums:
            return text
        amount = int(nums[0])
        if "万" in text:
            amount *= 10000
        if amount < 10000:
            return "余额：1万元以下"
        elif amount < 50000:
            return "余额：1-5万元"
        elif amount < 100000:
            return "余额：5-10万元"
        elif amount < 500000:
            return "余额：10-50万元"
        elif amount < 1000000:
            return "余额：50-100万元"
        else:
            return "余额：100万元以上"

    @classmethod
    def mask_user_data(cls, user_data: dict) -> dict:
        """对用户数据字典进行脱敏"""
        masked = {}
        for k, v in user_data.items():
            if isinstance(v, str):
                masked[k] = cls.mask_text(v)
            elif isinstance(v, (int, float)) and k in ("balance", "assets", "income"):
                masked[k] = cls._mask_amount(str(v))
            elif isinstance(v, dict):
                masked[k] = cls.mask_user_data(v)
            else:
                masked[k] = v
        return masked

    @classmethod
    def generate_safe_profile(cls, raw_profile: dict) -> dict:
        """
        生成安全用户画像（仅风险标签，不含敏感数据）
        这是智能体唯一能访问的用户数据
        """
        return {
            "user_id": raw_profile.get("user_id", "anonymous"),
            "risk_level": raw_profile.get("risk_level", "保守型"),
            "risk_level_num": raw_profile.get("risk_level_num", 1),
            "age_range": cls._mask_range(raw_profile.get("age")),
            "income_range": cls._mask_range(raw_profile.get("income")),
            "has_investment_experience": raw_profile.get("has_experience", False),
            "knowledge_level": raw_profile.get("knowledge_level", "入门"),
            # 不包含：具体余额、银行卡号、身份证、手机号
        }

    @staticmethod
    def _mask_range(value: Any) -> str:
        """将具体数值转为区间"""
        if not value:
            return "****"
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            if value < 5000:
                return "5000以下"
            elif value < 30000:
                return "5000-3万"
            elif value < 100000:
                return "3万-10万"
            else:
                return "10万以上"
        return "****"
