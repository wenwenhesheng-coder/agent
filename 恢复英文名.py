"""把中文文件名改回英文，修复打不开的问题"""
import os
from pathlib import Path

# 中文→英文映射表
RENAME_MAP = {
    # agents
    "agents/智能体基类.py": "agents/base_agent.py",
    "agents/客户画像智能体.py": "agents/customer_profile_agent.py",
    "agents/市场分析智能体.py": "agents/market_analysis_agent.py",
    "agents/产品匹配智能体.py": "agents/product_matching_agent.py",
    "agents/合规审查智能体.py": "agents/compliance_agent.py",
    "agents/话术生成智能体.py": "agents/dialogue_agent.py",
    "agents/协调器.py": "agents/orchestrator.py",
    # api
    "api/主应用.py": "api/main.py",
    "api/路由.py": "api/routes.py",
    # compliance
    "compliance/规则引擎.py": "compliance/rule_engine.py",
    "compliance/拦截器.py": "compliance/interceptor.py",
    "compliance/审计日志.py": "compliance/audit_logger.py",
    # config
    "config/配置.py": "config/settings.py",
    # core
    "core/数据模型.py": "core/models.py",
    "core/异常定义.py": "core/exceptions.py",
    "core/系统容器.py": "core/system.py",
    # data
    "data/数据脱敏.py": "data/data_masking.py",
    "data/用户数据适配器.py": "data/user_data_adapter.py",
    # memory
    "memory/记忆引擎.py": "memory/memory_engine.py",
    "memory/用户画像.py": "memory/user_profile.py",
    # models
    "models/大模型客户端.py": "models/llm_client.py",
    "models/量化小模型.py": "models/quant_models.py",
    # rag
    "rag/向量存储.py": "rag/vector_store.py",
    "rag/文档处理器.py": "rag/document_processor.py",
    "rag/检索器.py": "rag/retriever.py",
    # tools
    "tools/工具基类.py": "tools/base.py",
    "tools/产品知识库.py": "tools/product_kb.py",
    "tools/风险测评.py": "tools/risk_assessment.py",
    "tools/资产计算器.py": "tools/calculators.py",
    "tools/市场数据.py": "tools/market_data.py",
    "tools/监管条文库.py": "tools/regulation_kb.py",
    # 根目录
    "启动入口.py": "run.py",
    "生成Word文档.py": "generate_word_doc.py",
}

# import语句替换映射
IMPORT_MAP = {
    "agents.智能体基类": "agents.base_agent",
    "agents.客户画像智能体": "agents.customer_profile_agent",
    "agents.市场分析智能体": "agents.market_analysis_agent",
    "agents.产品匹配智能体": "agents.product_matching_agent",
    "agents.合规审查智能体": "agents.compliance_agent",
    "agents.话术生成智能体": "agents.dialogue_agent",
    "agents.协调器": "agents.orchestrator",
    "api.主应用": "api.main",
    "api.路由": "api.routes",
    "compliance.规则引擎": "compliance.rule_engine",
    "compliance.拦截器": "compliance.interceptor",
    "compliance.审计日志": "compliance.audit_logger",
    "config.配置": "config.settings",
    "core.数据模型": "core.models",
    "core.异常定义": "core.exceptions",
    "core.系统容器": "core.system",
    "data.数据脱敏": "data.data_masking",
    "data.用户数据适配器": "data.user_data_adapter",
    "memory.记忆引擎": "memory.memory_engine",
    "memory.用户画像": "memory.user_profile",
    "models.大模型客户端": "models.llm_client",
    "models.量化小模型": "models.quant_models",
    "rag.向量存储": "rag.vector_store",
    "rag.文档处理器": "rag.document_processor",
    "rag.检索器": "rag.retriever",
    "tools.工具基类": "tools.base",
    "tools.产品知识库": "tools.product_kb",
    "tools.风险测评": "tools.risk_assessment",
    "tools.资产计算器": "tools.calculators",
    "tools.市场数据": "tools.market_data",
    "tools.监管条文库": "tools.regulation_kb",
}

SORTED_KEYS = sorted(IMPORT_MAP.keys(), key=len, reverse=True)


def main():
    root = Path(".")
    renamed = 0

    # 1. 重命名文件
    for cn, en in RENAME_MAP.items():
        cn_path = root / cn
        en_path = root / en
        if cn_path.exists():
            cn_path.rename(en_path)
            print(f"  {cn} -> {en}")
            renamed += 1
    print(f"[1/3] 重命名完成: {renamed} 个文件")

    # 2. 修改所有import语句
    changed = 0
    for py_file in root.rglob("*.py"):
        if py_file.name in ("恢复英文名.py",):
            continue
        if "__pycache__" in py_file.parts:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue
        original = content
        for cn_key in SORTED_KEYS:
            en_key = IMPORT_MAP[cn_key]
            content = content.replace(cn_key, en_key)
        if content != original:
            py_file.write_text(content, encoding="utf-8")
            changed += 1
    print(f"[2/3] import语句修改完成: {changed} 个文件")

    # 3. 清理__pycache__
    cleaned = 0
    for cache_dir in root.rglob("__pycache__"):
        if cache_dir.is_dir():
            for f in cache_dir.iterdir():
                f.unlink()
            cache_dir.rmdir()
            cleaned += 1
    print(f"[3/3] 清理__pycache__: {cleaned} 个目录")

    print("\n[OK] 全部恢复完成！现在文件可以用IDE正常打开了。")


if __name__ == "__main__":
    main()
