"""
智慧银行理财顾问智能体 - 启动入口

使用方法：
    python run.py          # 启动Web服务
    python run.py --demo   # 运行命令行演示
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def run_demo():
    """命令行演示模式"""
    from core.system import system
    await system.initialize()

    print("\n" + "=" * 60)
    print("  智慧银行理财顾问智能体 - 命令行演示")
    print("=" * 60)
    print(f"  系统状态: {system.get_status()}")
    print("=" * 60)

    orchestrator = system.get_orchestrator()
    user_id = "user_001"

    # 演示对话
    demo_questions = [
        "我月薪5000怎么理财？",
        "帮我分析一下当前市场环境",
        "我是稳健型投资者，推荐适合我的理财产品",
    ]

    for question in demo_questions:
        print(f"\n{'─' * 60}")
        print(f"用户: {question}")
        print(f"{'─' * 60}")
        result = await orchestrator.execute(user_id, question)
        print(f"\n智能体回复:\n{result['response'][:500]}...")
        print(f"\n[合规] {'通过' if result['compliance_result'].passed else '拦截'}")
        print(f"[步骤] {result['steps_executed']}")
        print(f"[来源] {result['data_sources']}")

    # 审计统计
    print(f"\n{'=' * 60}")
    print("审计统计:")
    audit_logger = orchestrator.compliance_agent.interceptor.audit_logger
    print(f"  {audit_logger.get_stats()}")
    print(f"{'=' * 60}\n")


def run_server():
    """启动Web服务"""
    import uvicorn
    from config.settings import settings

    print("\n" + "=" * 60)
    print("  智慧银行理财顾问智能体 - Web服务启动")
    print(f"  地址: http://{settings.api.host}:{settings.api.port}")
    print(f"  文档: http://{settings.api.host}:{settings.api.port}/docs")
    print("=" * 60 + "\n")

    uvicorn.run(
        "api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=False,
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        asyncio.run(run_demo())
    else:
        run_server()
