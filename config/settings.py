"""
============================================
 全局配置管理
============================================
 支持 .env 环境变量覆盖，适配私有化部署
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
KB_DIR = DATA_DIR / "knowledge_base"
USER_DB_DIR = DATA_DIR / "user_db"
AUDIT_LOG_DIR = DATA_DIR / "audit_logs"
SAMPLE_DIR = DATA_DIR / "samples"

for _d in (DATA_DIR, KB_DIR, USER_DB_DIR, AUDIT_LOG_DIR, SAMPLE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


class LLMSettings(BaseSettings):
    """大模型配置 —— 支持通义千问 / 文心一言 / 智谱 AI / 私有化部署"""

    # 默认使用通义千问（DashScope OpenAI兼容接口）
    llm_provider: Literal["qwen", "wenxin", "zhipu", "local"] = "qwen"

    # API Key（通过环境变量注入，不在代码中硬编码）
    qwen_api_key: str = Field(default="", alias="DASHSCOPE_API_KEY")
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"

    zhipu_api_key: str = Field(default="", alias="ZHIPU_API_KEY")
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipu_model: str = "glm-4"

    wenxin_api_key: str = Field(default="", alias="WENXIN_API_KEY")
    wenxin_secret_key: str = Field(default="", alias="WENXIN_SECRET_KEY")

    # 私有化部署（vLLM）
    local_base_url: str = "http://localhost:8000/v1"
    local_model: str = "Qwen2.5-14B-Instruct"

    # 通用参数
    temperature: float = 0.3
    max_tokens: int = 2048
    timeout: int = 30

    # 无API Key时使用的演示模式（mock LLM）
    mock_mode: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def get_active_config(self) -> dict:
        """获取当前激活的大模型配置"""
        if self.llm_provider == "qwen":
            return {
                "api_key": self.qwen_api_key,
                "base_url": self.qwen_base_url,
                "model": self.qwen_model,
            }
        elif self.llm_provider == "zhipu":
            return {
                "api_key": self.zhipu_api_key,
                "base_url": self.zhipu_base_url,
                "model": self.zhipu_model,
            }
        elif self.llm_provider == "local":
            return {
                "api_key": "EMPTY",
                "base_url": self.local_base_url,
                "model": self.local_model,
            }
        return {"api_key": "", "base_url": "", "model": ""}


class RAGSettings(BaseSettings):
    """RAG 向量检索配置"""

    # 向量库
    vector_db_path: str = str(USER_DB_DIR / "chroma")
    collection_name: str = "bank_finance_kb"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"  # 中文向量模型
    embedding_dim: int = 512

    # 文档切片
    chunk_size: int = 300
    chunk_overlap: int = 50

    # 检索
    top_k: int = 5
    similarity_threshold: float = 0.65

    model_config = SettingsConfigDict(extra="ignore")


class ComplianceSettings(BaseSettings):
    """合规风控配置"""

    # 合规规则开关
    enable_prohibit_guarantee: bool = True     # 禁止承诺保本/保证收益
    enable_risk_match_check: bool = True      # 风险等级匹配校验
    enable_sensitive_words: bool = True       # 敏感话术拦截
    enable_risk_disclosure: bool = True       # 强制风险提示
    enable_audit_log: bool = True             # 操作留痕

    # 敏感词库
    sensitive_words: List[str] = [
        "保本", "保证收益", "稳赚不赔", "零风险", "绝对安全",
        "无风险", "包赚", "百分百赚", "刚性兑付", "兜底",
        "内部消息", "内幕", "稳赚", "确定收益", "保证升值",
    ]

    # 强制风险提示语
    risk_disclosure_text: str = (
        "【风险提示】理财非存款，产品有风险，投资需谨慎。"
        "过往业绩不预示未来表现，不构成任何投资建议或承诺。"
    )

    model_config = SettingsConfigDict(extra="ignore")


class AgentSettings(BaseSettings):
    """Agent 智能体配置"""

    # 多智能体协同
    enabled_agents: List[str] = [
        "customer_profile",    # 客户画像Agent
        "market_analysis",     # 市场分析Agent
        "product_matching",    # 产品匹配Agent
        "compliance",          # 合规审查Agent
        "dialogue",            # 话术生成Agent
    ]

    # 记忆系统
    short_term_window: int = 10      # 短期对话轮数
    long_term_profile_ttl: int = 90  # 长期画像有效期（天）

    # 规划拆解
    max_planning_steps: int = 8
    enable_chain_visible: bool = True  # 推理链可视化（XAI）

    model_config = SettingsConfigDict(extra="ignore")


class APISettings(BaseSettings):
    """API 服务配置"""

    host: str = "0.0.0.0"
    port: int = 8200
    cors_origins: List[str] = ["*"]

    # 数据脱敏
    enable_data_masking: bool = True   # 亮点九：脱敏访问
    mask_char: str = "*"
    masked_fields: List[str] = ["phone", "id_card", "bank_account", "balance"]

    model_config = SettingsConfigDict(extra="ignore")


class Settings:
    """全局配置聚合"""

    llm = LLMSettings()
    rag = RAGSettings()
    compliance = ComplianceSettings()
    agent = AgentSettings()
    api = APISettings()


# 全局单例
settings = Settings()
