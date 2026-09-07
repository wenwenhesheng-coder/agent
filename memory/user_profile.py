"""
用户画像管理器 —— 动态精准用户画像（亮点五）

融合用户行为数据（浏览/点击/提问）、交易数据（持仓/偏好）与风险测评结果，
构建用户投资风格画像 + 认知水平画像。
"""
from __future__ import annotations

import re
from typing import Any

from loguru import logger

from core.models import RiskLevel, UserProfile
from memory.memory_engine import MemoryEngine


class UserProfileManager:
    """
    动态用户画像管理器
    - 从对话中提取用户信息（风险等级、收入、偏好）
    - 构建投资风格画像 + 认知水平画像
    - 支持千人千面服务场景的精准识别
    """

    # 风险等级关键词映射
    RISK_KEYWORDS: dict[RiskLevel, list[str]] = {
        RiskLevel.CONSERVATIVE: ["保守", "保本", "不能亏", "低风险", "存款"],
        RiskLevel.STEADY: ["稳健", "稳定", "中低风险", "不追高"],
        RiskLevel.BALANCED: ["平衡", "中等", "兼顾", "稳健增长"],
        RiskLevel.GROWTH: ["成长", "增值", "较高收益", "中高风险"],
        RiskLevel.AGGRESSIVE: ["进取", "激进", "高风险", "高收益", "博收益"],
    }

    # 认知水平关键词
    KNOWLEDGE_KEYWORDS: dict[str, list[str]] = {
        "入门": ["什么是", "怎么理财", "不懂", "新手", "入门", "科普", "教我"],
        "进阶": ["收益率", "期限", "赎回", "配置", "组合", "夏普", "波动率"],
        "专业": ["VaR", "久期", "凸性", "Black-Litterman", "alpha", "beta",
                 "夏普比率", "信息比率", "回撤", "Beta", "Alpha"],
    }

    # 偏好关键词
    PREFERENCE_KEYWORDS: dict[str, list[str]] = {
        "流动性": ["随时", "灵活", "急用", "短期", "取用"],
        "稳健": ["稳健", "保本", "低波动", "安心"],
        "增值": ["增值", "高收益", "博取", "成长"],
        "黄金": ["黄金", "避险", "抗通胀"],
        "养老": ["养老", "退休", "长期"],
        "定投": ["定投", "定期", "每月", "每月存"],
    }

    def __init__(self, memory_engine: MemoryEngine):
        self.memory = memory_engine

    def extract_from_message(self, user_id: str, message: str) -> dict[str, Any]:
        """
        从用户消息中提取画像信息
        实现持续对话真正理解用户的深度信息
        """
        extracted: dict[str, Any] = {}

        # 1. 风险等级识别
        risk_level = self._detect_risk_level(message)
        if risk_level:
            extracted["risk_level"] = risk_level.value

        # 2. 收入区间识别（脱敏处理）
        income = self._detect_income(message)
        if income:
            extracted["income_range"] = income

        # 3. 认知水平识别
        knowledge = self._detect_knowledge_level(message)
        if knowledge:
            extracted["knowledge_level"] = knowledge

        # 4. 偏好识别
        prefs = self._detect_preferences(message)
        if prefs:
            existing_prefs = self.memory.get_long_term(user_id).preferences
            merged = list(set(existing_prefs + prefs))
            extracted["preferences"] = merged

        # 5. 月薪/金额识别
        salary = self._detect_amount(message)
        if salary:
            extracted["monthly_income"] = salary

        # 更新长期记忆
        if extracted:
            self.memory.update_profile(user_id, **extracted)
            logger.info(f"用户画像更新: {extracted}")

        return extracted

    def _detect_risk_level(self, message: str) -> RiskLevel | None:
        for level, keywords in self.RISK_KEYWORDS.items():
            for kw in keywords:
                if kw in message:
                    return level
        return None

    def _detect_income(self, message: str) -> str | None:
        # 匹配"月薪XXXX" "月收入XXXX" "XXXX元/月"
        patterns = [
            r"月薪\s*(\d+)",
            r"月收入\s*(\d+)",
            r"收入\s*(\d+)\s*[万]?",
            r"工资\s*(\d+)",
            r"每月\s*(\d+)",
        ]
        for p in patterns:
            m = re.search(p, message)
            if m:
                amount = int(m.group(1))
                # 脱敏：转为区间
                if amount < 5000:
                    return "5000元以下"
                elif amount < 10000:
                    return "5000-1万元"
                elif amount < 30000:
                    return "1万-3万元"
                elif amount < 100000:
                    return "3万-10万元"
                else:
                    return "10万元以上"
        return None

    def _detect_knowledge_level(self, message: str) -> str | None:
        for level, keywords in self.KNOWLEDGE_KEYWORDS.items():
            for kw in keywords:
                if kw in message:
                    return level
        return None

    def _detect_preferences(self, message: str) -> list[str]:
        prefs = []
        for pref, keywords in self.PREFERENCE_KEYWORDS.items():
            for kw in keywords:
                if kw in message:
                    prefs.append(pref)
                    break
        return prefs

    def _detect_amount(self, message: str) -> str | None:
        # 匹配具体金额
        m = re.search(r"(\d+)\s*[万元]", message)
        if m:
            return m.group(0)
        return None

    def get_profile(self, user_id: str) -> UserProfile:
        """获取脱敏后的用户画像"""
        ltm = self.memory.get_long_term(user_id)
        try:
            risk = RiskLevel(ltm.risk_level)
        except ValueError:
            risk = RiskLevel.CONSERVATIVE

        return UserProfile(
            user_id=user_id,
            nickname=f"用户{user_id[-4:] if len(user_id)>4 else user_id}***",
            risk_level=risk,
            income_range=ltm.income_range or "****",
            holding_products=ltm.holding_products,
            investment_preference=ltm.preferences,
            knowledge_level=ltm.knowledge_level,
            conversation_history_count=len(self.memory.get_short_term(user_id).get_context()),
        )
