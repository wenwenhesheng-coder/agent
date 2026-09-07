"""
Agent基类 —— 所有专业Agent的统一抽象

核心能力：
- 工具调用能力（自主调用工具）
- 记忆模块（短期+长期）
- 规划拆解（复杂问题拆解）
- 推理链可视化（XAI可解释）
"""
from __future__ import annotations

import abc
from typing import Any

from loguru import logger

from config.settings import settings
from core.models import AgentThought, RiskLevel
from models.llm_client import llm_client
from memory.memory_engine import MemoryEngine
from tools import tool_registry
from rag.retriever import AgenticRetriever


class BaseAgent(abc.ABC):
    """
    Agent基类
    每个Agent有专属角色、系统提示词、可用工具
    """

    name: str = ""
    role: str = ""
    description: str = ""

    def __init__(
        self,
        memory_engine: MemoryEngine,
        retriever: AgenticRetriever | None = None,
    ):
        self.memory = memory_engine
        self.retriever = retriever
        self.llm = llm_client
        self.thoughts: list[AgentThought] = []

    @abc.abstractmethod
    def get_system_prompt(self) -> str:
        """返回该Agent的专属系统提示词"""
        pass

    async def think(
        self,
        user_id: str,
        user_input: str,
        context: str = "",
    ) -> AgentThought:
        """
        Agent思考（XAI可解释：记录推理过程）
        """
        thought = AgentThought(
            agent_name=self.name,
            thought=f"处理用户输入: {user_input[:100]}",
        )

        # 构建消息
        messages = [{"role": "system", "content": self.get_system_prompt()}]
        if context:
            messages.append({"role": "system", "content": context})
        # 加入对话历史
        messages.extend(self.memory.get_context(user_id))
        messages.append({"role": "user", "content": user_input})

        # 调用LLM（带推理链）
        answer, reasoning = await self.llm.chat_with_thought(
            messages=messages,
            system_prompt="",
        )

        thought.thought = reasoning or f"分析用户需求: {user_input[:80]}"
        thought.observation = answer
        self.thoughts.append(thought)
        return thought

    async def use_tool(self, tool_name: str, **kwargs) -> str:
        """调用工具"""
        thought = AgentThought(
            agent_name=self.name,
            thought=f"需要调用工具: {tool_name}",
            action=tool_name,
            action_input=str(kwargs),
        )
        result = await tool_registry.call(tool_name, kwargs)
        thought.observation = result[:500]
        self.thoughts.append(thought)
        return result

    async def retrieve_knowledge(self, query: str) -> str:
        """Agentic RAG检索知识"""
        if not self.retriever:
            return ""
        thought = AgentThought(
            agent_name=self.name,
            thought=f"检索知识库: {query[:50]}",
            action="rag_retrieve",
        )
        result = await self.retriever.retrieve(query)
        context = self.retriever.get_context_for_llm(result)
        thought.observation = f"检索到{len(result.chunks)}个片段, 来源: {result.sources}"
        self.thoughts.append(thought)
        return context

    def get_reasoning_chain(self) -> list[AgentThought]:
        """获取推理链（XAI可视化）"""
        return self.thoughts

    def clear_thoughts(self) -> None:
        self.thoughts.clear()
