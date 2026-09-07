"""
动态用户记忆与个性化引擎（亮点五）

构建多维度用户记忆系统：
- 短期对话记忆（多轮聊天上下文）
- 长期用户档案记忆（风险等级、收入情况、持有产品）
- 用户投资风格画像 + 认知水平画像
- 支持千人千面服务场景的精准识别与落地
"""
from memory.memory_engine import MemoryEngine
from memory.user_profile import UserProfileManager

__all__ = ["MemoryEngine", "UserProfileManager"]
