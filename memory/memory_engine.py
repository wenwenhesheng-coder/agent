"""
记忆引擎 —— 短期记忆 + 长期记忆

亮点五核心：
- 短期对话记忆：多轮聊天上下文（滑动窗口）
- 长期用户档案记忆：风险等级、收入、偏好、认知水平
- 通过持续对话真正理解用户的现金流、负债、储蓄习惯
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from typing import Any

from loguru import logger

from config.settings import settings
from core.models import ChatMessage


class ShortTermMemory:
    """短期对话记忆（滑动窗口）"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._messages: deque[ChatMessage] = deque(
            maxlen=settings.agent.short_term_window * 2  # 双向（user+assistant）
        )

    def add(self, message: ChatMessage) -> None:
        self._messages.append(message)

    def get_context(self, max_messages: int | None = None) -> list[dict]:
        """获取对话上下文（OpenAI消息格式）"""
        msgs = list(self._messages)
        if max_messages:
            msgs = msgs[-max_messages:]
        return [{"role": m.role, "content": m.content} for m in msgs]

    def clear(self) -> None:
        self._messages.clear()

    def summary(self) -> str:
        """生成对话摘要（供长期记忆使用）"""
        if not self._messages:
            return ""
        lines = []
        for m in self._messages:
            lines.append(f"[{m.role}] {m.content[:100]}")
        return " | ".join(lines)


class LongTermMemory:
    """长期用户档案记忆"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.risk_level: str = "保守型"
        self.income_range: str = ""
        self.holding_products: list[str] = []
        self.preferences: list[str] = []
        self.knowledge_level: str = "入门"
        self.facts: dict[str, Any] = {}  # 自由格式事实记忆
        self.last_updated: datetime = datetime.now()

    def update(self, **kwargs) -> None:
        """更新长期记忆字段"""
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                self.facts[k] = v
            logger.debug(f"长期记忆更新: {k}={v}")
        self.last_updated = datetime.now()

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "risk_level": self.risk_level,
            "income_range": self.income_range,
            "holding_products": self.holding_products,
            "preferences": self.preferences,
            "knowledge_level": self.knowledge_level,
            "facts": self.facts,
            "last_updated": self.last_updated.isoformat(),
        }


class MemoryEngine:
    """
    记忆引擎总入口
    - 管理每个用户的短期 + 长期记忆
    - 支持上下文检索与记忆注入
    """

    def __init__(self):
        self._short_term: dict[str, ShortTermMemory] = {}
        self._long_term: dict[str, LongTermMemory] = {}

    def get_short_term(self, user_id: str) -> ShortTermMemory:
        if user_id not in self._short_term:
            self._short_term[user_id] = ShortTermMemory(user_id)
        return self._short_term[user_id]

    def get_long_term(self, user_id: str) -> LongTermMemory:
        if user_id not in self._long_term:
            self._long_term[user_id] = LongTermMemory(user_id)
        return self._long_term[user_id]

    def add_message(self, user_id: str, role: str, content: str) -> None:
        """添加对话消息到短期记忆"""
        stm = self.get_short_term(user_id)
        stm.add(ChatMessage(role=role, content=content))

    def get_context(self, user_id: str) -> list[dict]:
        """获取短期对话上下文"""
        return self.get_short_term(user_id).get_context()

    def update_profile(self, user_id: str, **kwargs) -> None:
        """更新长期用户档案"""
        self.get_long_term(user_id).update(**kwargs)

    def get_profile_summary(self, user_id: str) -> str:
        """获取长期用户档案摘要（注入LLM上下文）"""
        ltm = self.get_long_term(user_id)
        lines = ["【用户长期记忆档案】"]
        lines.append(f"  风险等级：{ltm.risk_level}")
        if ltm.income_range:
            lines.append(f"  收入区间：{ltm.income_range}")
        if ltm.holding_products:
            lines.append(f"  持有产品：{', '.join(ltm.holding_products)}")
        if ltm.preferences:
            lines.append(f"  投资偏好：{', '.join(ltm.preferences)}")
        lines.append(f"  认知水平：{ltm.knowledge_level}")
        if ltm.facts:
            for k, v in ltm.facts.items():
                lines.append(f"  {k}：{v}")
        return "\n".join(lines)
