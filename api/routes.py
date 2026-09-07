"""
API路由 —— 对接适配层接口

对接银行现有系统：手机银行APP、小程序、客服系统
所有接口均经过数据脱敏处理
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from core.system import system
from data.user_data_adapter import user_data_adapter
from tools import tool_registry

router = APIRouter()


# ==================== 请求/响应模型 ====================

class ChatRequest(BaseModel):
    user_id: str = "demo_user"
    message: str = Field(..., description="用户消息")


class ChatResponse(BaseModel):
    response: str
    reasoning_chain: list[dict] = Field(default_factory=list)
    compliance_passed: bool
    compliance_violations: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    steps_executed: list[str] = Field(default_factory=list)
    user_risk_level: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class RiskAssessmentRequest(BaseModel):
    user_id: str = "demo_user"
    answers: list[int] = Field(..., description="风险测评答案数组(1-5)")


class YieldCalcRequest(BaseModel):
    mode: str = "compound"  # compound / sip / product
    principal: float = 10000
    monthly_invest: float = 1000
    annual_rate: float = 0.045
    years: int = 3
    term_days: int = 90


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict = {}


# ==================== 对话接口 ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    智能理财顾问对话接口
    多智能体协同 + 合规拦截 + 推理链可视化
    """
    try:
        orchestrator = system.get_orchestrator()
        result = await orchestrator.execute(req.user_id, req.message)

        return ChatResponse(
            response=result["response"],
            reasoning_chain=[
                {
                    "agent": t.agent_name,
                    "thought": t.thought,
                    "action": t.action,
                    "observation": t.observation,
                }
                for t in result["reasoning_chain"]
            ],
            compliance_passed=result["compliance_result"].passed,
            compliance_violations=result["compliance_result"].violated_rules,
            data_sources=result["data_sources"],
            steps_executed=result["steps_executed"],
            user_risk_level=result["user_risk_level"],
        )
    except Exception as e:
        logger.error(f"对话接口异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 风险测评接口 ====================

@router.post("/risk-assessment")
async def risk_assessment(req: RiskAssessmentRequest):
    """用户风险测评"""
    from tools.risk_assessment import RiskAssessmentTool
    tool = RiskAssessmentTool()
    result = await tool.execute(action="submit_answers", answers=req.answers)

    # 更新用户风险等级到银行系统
    # 从结果中提取风险等级
    import re
    level_match = re.search(r"风险等级：(.+?)（C", result)
    if level_match:
        risk_level = level_match.group(1)
        level_num = {"保守型": 1, "稳健型": 2, "平衡型": 3, "成长型": 4, "进取型": 5}
        num = level_num.get(risk_level, 1)
        user_data_adapter.update_risk_assessment(req.user_id, risk_level, num)

    return {"result": result, "user_id": req.user_id}


@router.get("/risk-assessment/questions")
async def get_risk_questions():
    """获取风险测评题库"""
    from tools.risk_assessment import RiskAssessmentTool
    tool = RiskAssessmentTool()
    result = await tool.execute(action="get_questions")
    return {"questions": result}


# ==================== 工具调用接口（MCP标准化） ====================

@router.get("/tools")
async def list_tools():
    """列出所有可用工具（MCP标准化）"""
    return {
        "tools": tool_registry.list_tools(),
        "schemas": tool_registry.all_schemas(),
    }


@router.post("/tools/call")
async def call_tool(req: ToolCallRequest):
    """调用工具（MCP标准化接口）"""
    try:
        result = await tool_registry.call(req.tool_name, req.arguments)
        return {"tool": req.tool_name, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 收益测算接口 ====================

@router.post("/yield-calculation")
async def calculate_yield(req: YieldCalcRequest):
    """收益测算"""
    from tools.calculators import YieldCalculationTool
    tool = YieldCalculationTool()
    result = await tool.execute(
        mode=req.mode,
        principal=req.principal,
        monthly_invest=req.monthly_invest,
        annual_rate=req.annual_rate,
        years=req.years,
        term_days=req.term_days,
    )
    return {"result": result}


# ==================== 用户画像接口（脱敏） ====================

@router.get("/user-profile/{user_id}")
async def get_user_profile(user_id: str):
    """获取用户脱敏画像（亮点九：数据脱敏访问）"""
    profile = user_data_adapter.get_user_profile(user_id)
    return {"profile": profile, "note": "数据已脱敏，智能体仅可访问风险标签等非敏感信息"}


# ==================== 审计接口（亮点八） ====================

@router.get("/audit/logs")
async def get_audit_logs(user_id: str = "", limit: int = 50):
    """查询审计日志（全链路留痕可审计）"""
    orchestrator = system.get_orchestrator()
    audit_logger = orchestrator.compliance_agent.interceptor.audit_logger
    records = audit_logger.get_records(
        user_id=user_id or None, limit=limit
    )
    return {
        "records": [
            {
                "audit_id": r.audit_id,
                "timestamp": r.timestamp.isoformat(),
                "user_id": r.user_id,
                "agent": r.agent_name,
                "compliance_passed": r.compliance_result.passed if r.compliance_result else None,
                "violated_rules": r.compliance_result.violated_rules if r.compliance_result else [],
            }
            for r in records
        ],
        "stats": audit_logger.get_stats(),
    }


@router.get("/audit/export")
async def export_audit_trail(user_id: str = ""):
    """导出审计追溯链"""
    orchestrator = system.get_orchestrator()
    audit_logger = orchestrator.compliance_agent.interceptor.audit_logger
    trail = audit_logger.export_audit_trail(user_id=user_id or None)
    return {"audit_trail": trail, "note": "满足金融监管审计要求，保留期限≥20年"}


# ==================== 系统状态接口 ====================

@router.get("/system/status")
async def system_status():
    """系统状态"""
    return system.get_status()


@router.get("/system/architecture")
async def architecture():
    """系统架构信息"""
    return {
        "name": "智慧银行理财顾问智能体",
        "layers": [
            {"name": "底层基座层", "description": "国产大模型API（通义千问/文心/智谱）+ 私有化部署"},
            {"name": "Agent智能体核心层", "description": "多智能体协同 + 工具调用 + 记忆模块 + 规划拆解"},
            {"name": "RAG知识库层", "description": "银行专属知识库 + 文档切片向量化 + Agentic RAG"},
            {"name": "合规风控拦截层", "description": "独立规则引擎 + 全链路审计留痕 + 强制风险提示"},
            {"name": "对接适配层", "description": "FastAPI接口 + MCP标准化 + 对接银行系统"},
            {"name": "前端交互层", "description": "对话界面 + 理财报告展示"},
        ],
        "highlights": [
            "多智能体协同架构",
            "Agentic RAG增强检索",
            "大小模型协同",
            "可解释AI（XAI）与合规内置",
            "动态用户记忆与个性化引擎",
            "轻量化部署与成本控制",
            "RAG + 业务规则双轮驱动抑制幻觉",
            "金融合规硬隔离架构",
            "用户隐私数据脱敏访问机制",
        ],
        "agents": list(system.orchestrator.agents.keys()) if system.orchestrator else [],
        "compliance_rules": [
            "禁止承诺保本/保证收益",
            "风险等级匹配校验",
            "敏感话术拦截",
            "强制风险提示",
            "产品来源校验（抑制幻觉）",
        ],
    }
