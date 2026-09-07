"""
大模型客户端 —— 支持通义千问 / 文心一言 / 智谱AI / 私有化部署

亮点三：大模型负责语义理解、意图识别、对话生成、策略解读
亮点六：支持私有化部署、vLLM加速
"""
from __future__ import annotations

import json
import re
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from core.exceptions import LLMCallError
from loguru import logger


# ==================== Mock模式（无API Key时演示用） ====================

MOCK_RESPONSES: dict[str, str] = {
    "风险测评": (
        "根据您的回答，您的风险测评结果为：\n"
        "- 风险承受能力：稳健型（C2）\n"
        "- 投资期限偏好：1-3年\n"
        "- 收益预期：年化4%-6%\n"
        "- 建议配置方向：以固收类产品为主，辅以少量权益类。"
    ),
    "市场分析": (
        "当前市场环境分析：\n"
        "1. 宏观面：国内经济温和复苏，货币政策保持稳健偏宽松，利率中枢下行。\n"
        "2. 债市：中高等级信用债配置价值较高，长久期利率债波动加大。\n"
        "3. 权益市场：A股估值处于历史偏低区间，结构性机会值得关注。\n"
        "4. 黄金：地缘风险与美元实际利率下行支撑避险配置价值。\n"
        "结论：当前环境下，固收+策略较适配稳健型投资者。"
    ),
    "资产配置": (
        "基于您的稳健型风险等级与当前市场环境，建议配置方案：\n"
        "- 活期/货基类：10%（应对流动性需求）\n"
        "- 固收理财/债券基金：60%（核心底仓，获取稳定票息）\n"
        "- 固收+ / 混合基金：20%（增强收益弹性）\n"
        "- 黄金/REITs：5%（分散风险）\n"
        "- 权益类（指数/蓝筹）：5%（长期增值）\n"
        "注：以上为科普性配置参考，非具体产品推荐。"
    ),
}


def _match_mock_response(prompt: str) -> str | None:
    """根据提示词匹配mock回复（用于无API Key演示）"""
    for key, resp in MOCK_RESPONSES.items():
        if key in prompt:
            return resp
    return None


# ==================== 大模型客户端 ====================

class LLMClient:
    """
    统一大模型客户端
    - 支持多Provider切换（通义千问/文心/智谱/私有化）
    - 统一Async接口，支持流式/非流式
    - Mock模式：无API Key时自动启用，保证演示可运行
    """

    def __init__(self):
        self._config = settings.llm.get_active_config()
        self._mock = settings.llm.mock_mode or not self._config["api_key"]
        if self._mock:
            logger.warning("LLM运行于Mock模式（未配置API Key），使用预设回复进行演示")

        if not self._mock:
            self._client = AsyncOpenAI(
                api_key=self._config["api_key"],
                base_url=self._config["base_url"],
                timeout=settings.llm.timeout,
            )
        else:
            self._client = None
        self._model = self._config["model"]

    # --- 核心调用 ---

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> str:
        """
        对话接口（非流式）
        Args:
            messages: [{"role":"system/user/assistant","content":"..."}]
            tools: 函数调用定义（可选）
        Returns:
            模型回复文本
        """
        # Mock模式
        if self._mock:
            return self._mock_chat(messages)

        try:
            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature or settings.llm.temperature,
                "max_tokens": max_tokens or settings.llm.max_tokens,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            resp = await self._client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise LLMCallError(f"大模型调用失败: {e}") from e

    async def chat_with_thought(
        self,
        messages: list[dict[str, str]],
        system_prompt: str = "",
    ) -> tuple[str, str]:
        """
        带推理链的对话（XAI可解释，亮点四）
        返回: (最终回复, 推理过程)
        """
        thought_prompt = system_prompt + (
            "\n\n请先输出推理过程（用<thought>...</thought>包裹），"
            "再输出最终回复（用<answer>...</answer>包裹）。"
        )
        full_messages = [{"role": "system", "content": thought_prompt}] + messages
        raw = await self.chat(full_messages)

        thought = ""
        answer = raw
        t_match = re.search(r"<thought>(.*?)</thought>", raw, re.DOTALL)
        a_match = re.search(r"<answer>(.*?)</answer>", raw, re.DOTALL)
        if t_match:
            thought = t_match.group(1).strip()
        if a_match:
            answer = a_match.group(1).strip()
        return answer, thought

    async def function_call(
        self,
        messages: list[dict[str, str]],
        tools: list[dict],
    ) -> dict | None:
        """
        函数调用（工具调用能力）
        Returns: {"name":..., "arguments":{...}} 或 None
        """
        if self._mock:
            # Mock模式：根据消息内容简单匹配工具
            return self._mock_function_call(messages, tools)

        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=settings.llm.temperature,
            )
            tc = resp.choices[0].message.tool_calls
            if tc and len(tc) > 0:
                return {
                    "name": tc[0].function.name,
                    "arguments": json.loads(tc[0].function.arguments),
                }
        except Exception as e:
            logger.error(f"函数调用失败: {e}")
        return None

    # --- Mock实现 ---

    def _mock_chat(self, messages: list[dict[str, str]]) -> str:
        """Mock对话回复"""
        # 合并所有用户消息
        user_content = " ".join(
            m["content"] for m in messages if m["role"] == "user"
        )
        # 匹配预设回复
        for key, resp in MOCK_RESPONSES.items():
            if key in user_content:
                return resp
        # 通用回复
        return (
            "您好！我是智慧银行理财顾问智能体。\n"
            "基于您的风险等级和市场分析，我可以为您提供个性化的资产配置科普建议。\n"
            "请问您目前的风险等级是什么？或者您可以告诉我您的月收入和理财目标，"
            "我来为您做风险测评。\n\n"
            "（当前为Mock演示模式，配置API Key后可启用完整大模型能力）"
        )

    def _mock_function_call(
        self,
        messages: list[dict[str, str]],
        tools: list[dict],
    ) -> dict | None:
        """Mock函数调用"""
        user_content = " ".join(
            m["content"] for m in messages if m["role"] == "user"
        )
        tool_map = {t["function"]["name"]: t["function"] for t in tools}

        # 简单关键词匹配
        for name, func in tool_map.items():
            if name.replace("_", "") in user_content.replace(" ", ""):
                return {"name": name, "arguments": {"query": user_content[:50]}}
            # 检查描述关键词
            desc = func.get("description", "")
            for kw in ["风险", "产品", "收益", "资产配置", "市场", "监管"]:
                if kw in user_content and kw in desc:
                    return {"name": name, "arguments": {"query": kw}}
        # 默认返回第一个工具
        if tools:
            first = tools[0]["function"]["name"]
            return {"name": first, "arguments": {"query": user_content[:50]}}
        return None


# 全局单例
llm_client = LLMClient()
