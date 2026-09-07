"""
合规风控硬隔离层（亮点七、亮点八 - 重中之重）

不是简单提示词约束，而是独立一层规则引擎：
- RAG + 业务规则双轮驱动，抑制金融大模型幻觉
- 对话全链路留痕可审计
- 自动识别并拦截违规话术
- 输出强制附带监管要求的风险提示
"""
from compliance.rule_engine import ComplianceRuleEngine
from compliance.interceptor import ComplianceInterceptor
from compliance.audit_logger import AuditLogger

__all__ = ["ComplianceRuleEngine", "ComplianceInterceptor", "AuditLogger"]
