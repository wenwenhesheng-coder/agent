"""
FastAPI 主入口 —— 对接适配层

亮点六：轻量化部署与成本控制
- 支持私有化部署
- MCP标准化体系简化大模型与金融工具对接
- 对接银行现有系统：手机银行APP、小程序、客服系统
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from loguru import logger

from config.settings import settings
from core.system import system


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化系统"""
    await system.initialize()
    logger.info("智慧银行理财顾问智能体服务已启动")
    yield
    logger.info("服务关闭")


app = FastAPI(
    title="智慧银行理财顾问智能体",
    description=(
        "基于大模型技术的智慧银行理财顾问智能体\n\n"
        "核心亮点：\n"
        "1. 多智能体协同架构\n"
        "2. Agentic RAG增强检索\n"
        "3. 大小模型协同\n"
        "4. 可解释AI（XAI）与合规内置\n"
        "5. 动态用户记忆与个性化引擎\n"
        "6. 轻量化部署与成本控制\n"
        "7. RAG + 业务规则双轮驱动抑制幻觉\n"
        "8. 金融合规硬隔离架构\n"
        "9. 用户隐私数据脱敏访问机制"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件（前端）
static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 导入路由
from api.routes import router
app.include_router(router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径返回前端页面"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as f:
            return f.read()
    return '<h1>智慧银行理财顾问智能体</h1><p>前端页面未找到</p>'


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "system": system.get_status()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=False,
    )
