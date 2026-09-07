"""
工具基类与注册表 —— 统一工具调用接口

亮点六：采用MCP（模型上下文协议）标准化思路设计工具描述，
简化大模型与金融工具的对接流程。
"""
from __future__ import annotations

import abc
import json
from typing import Any

from core.exceptions import ToolCallError


class BaseTool(abc.ABC):
    """工具基类：所有Agent可调用工具的统一抽象"""

    name: str = ""
    description: str = ""
    parameters: dict = {}  # OpenAI function calling格式参数定义

    @abc.abstractmethod
    async def execute(self, **kwargs) -> str:
        """执行工具，返回结果文本"""
        pass

    def to_openai_schema(self) -> dict:
        """转换为OpenAI function calling格式（MCP标准化）"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def _format_result(self, data: dict) -> str:
        """格式化结果为可读文本"""
        lines = []
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False, indent=2)
            lines.append(f"{k}: {v}")
        return "\n".join(lines)


class ToolRegistry:
    """工具注册表：管理所有可用工具"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if not tool.name:
            raise ToolCallError(f"工具名称不能为空: {tool}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    async def call(self, name: str, arguments: dict) -> str:
        """调用工具"""
        tool = self._tools.get(name)
        if not tool:
            raise ToolCallError(f"工具不存在: {name}")
        try:
            result = await tool.execute(**arguments)
            return result
        except Exception as e:
            raise ToolCallError(f"工具[{name}]执行失败: {e}") from e

    def all_schemas(self) -> list[dict]:
        """获取所有工具的OpenAI格式定义"""
        return [t.to_openai_schema() for t in self._tools.values()]

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())
