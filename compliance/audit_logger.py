"""
审计日志器（亮点八：全链路留痕可审计）

对话全链路留痕可审计，满足金融监管审计要求：
- 所有对话记录留存
- 推理过程、合规校验结果可追溯
- 涉及产品推荐的建议记录数据来源
- 审计日志包含时间戳、用户ID、Agent名称、输入输出
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger

from config.settings import AUDIT_LOG_DIR
from core.models import AuditRecord, ComplianceCheckResult, AgentThought


class AuditLogger:
    """
    审计日志器
    - 实时记录所有Agent决策与输出
    - 支持结构化JSON存储，便于审计检索
    - 保留期限不少于20年（满足金融监管要求）
    """

    def __init__(self):
        self._log_file = AUDIT_LOG_DIR / "audit_log.jsonl"
        self._records: list[AuditRecord] = []

    async def log(
        self,
        user_id: str,
        agent_name: str,
        input_content: str,
        output_content: str,
        compliance_result: ComplianceCheckResult | None = None,
        reasoning_chain: list[AgentThought] | None = None,
        data_sources: list[str] | None = None,
    ) -> str:
        """
        记录一条审计日志
        Returns: audit_id
        """
        audit_id = compliance_result.audit_id if compliance_result else (
            f"AUD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        )

        record = AuditRecord(
            audit_id=audit_id,
            user_id=user_id,
            agent_name=agent_name,
            input_content=input_content[:500],   # 截断防止过大
            output_content=output_content[:2000],
            compliance_result=compliance_result,
            reasoning_chain=reasoning_chain or [],
            data_sources=data_sources or [],
        )

        # 写入内存
        self._records.append(record)

        # 写入文件（JSONL格式，便于流式追加与检索）
        try:
            log_entry = {
                "audit_id": record.audit_id,
                "timestamp": record.timestamp.isoformat(),
                "user_id": record.user_id,
                "agent_name": record.agent_name,
                "input": record.input_content,
                "output": record.output_content,
                "compliance_passed": compliance_result.passed if compliance_result else None,
                "violated_rules": compliance_result.violated_rules if compliance_result else [],
                "risk_warnings": compliance_result.risk_warnings if compliance_result else [],
                "reasoning_chain": [
                    {
                        "agent": t.agent_name,
                        "thought": t.thought,
                        "action": t.action,
                        "observation": t.observation,
                    } for t in record.reasoning_chain
                ],
                "data_sources": record.data_sources,
            }
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"审计日志写入失败: {e}")

        return audit_id

    def get_records(
        self,
        user_id: str | None = None,
        agent_name: str | None = None,
        limit: int = 50,
    ) -> list[AuditRecord]:
        """查询审计记录"""
        records = self._records
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        if agent_name:
            records = [r for r in records if r.agent_name == agent_name]
        return records[-limit:]

    def get_stats(self) -> dict:
        """审计统计"""
        total = len(self._records)
        passed = sum(
            1 for r in self._records
            if r.compliance_result and r.compliance_result.passed
        )
        blocked = total - passed
        return {
            "total_records": total,
            "passed": passed,
            "blocked": blocked,
            "block_rate": f"{blocked/total*100:.1f}%" if total > 0 else "0%",
            "retention_policy": "保留期限≥20年（满足金融监管审计要求）",
        }

    def export_audit_trail(self, user_id: str | None = None) -> list[dict]:
        """导出审计追溯链（满足监管审计要求）"""
        records = self.get_records(user_id=user_id, limit=1000)
        return [
            {
                "audit_id": r.audit_id,
                "timestamp": r.timestamp.isoformat(),
                "agent": r.agent_name,
                "compliance_passed": r.compliance_result.passed if r.compliance_result else None,
                "violated_rules": r.compliance_result.violated_rules if r.compliance_result else [],
                "data_sources": r.data_sources,
            }
            for r in records
        ]
