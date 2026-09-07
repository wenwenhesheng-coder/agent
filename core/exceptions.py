"""
统一异常定义
"""


class WealthAdvisorError(Exception):
    """智能体基础异常"""
    pass


class LLMCallError(WealthAdvisorError):
    """大模型调用异常"""
    pass


class ComplianceViolationError(WealthAdvisorError):
    """合规违规异常（输出被风控拦截）"""
    def __init__(self, message: str, violated_rules: list[str] | None = None):
        super().__init__(message)
        self.violated_rules = violated_rules or []


class RAGRetrievalError(WealthAdvisorError):
    """RAG检索异常"""
    pass


class ToolCallError(WealthAdvisorError):
    """工具调用异常"""
    pass


class DataMaskingError(WealthAdvisorError):
    """数据脱敏异常"""
    pass
