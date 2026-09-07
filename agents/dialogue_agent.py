"""
话术生成Agent（亮点一）

生成个性化营销话术与合规化服务内容。
最终面向用户的对话输出由该Agent负责。
"""
from __future__ import annotations

from loguru import logger

from agents.base_agent import BaseAgent
from core.models import RiskLevel, RecommendationItem, WealthPlan, AgentThought
from config.settings import settings


class DialogueAgent(BaseAgent):
    name = "dialogue_agent"
    role = "话术生成Agent"
    description = "生成个性化营销话术与合规化服务内容"

    def get_system_prompt(self) -> str:
        return (
            "你是银行理财顾问智能体的「话术生成Agent」，负责面向用户的最终对话输出。\n"
            "职责：\n"
            "1. 整合其他Agent的分析结果，生成用户可理解的回复\n"
            "2. 个性化营销话术，匹配用户认知水平（入门/进阶/专业）\n"
            "3. 确保语言通俗、专业、合规\n"
            "4. 附加必要的信息来源标注和风险提示\n\n"
            "输出规范：\n"
            "- 对入门用户：用通俗语言解释概念，避免专业术语\n"
            "- 对进阶用户：可使用收益率、波动率等术语\n"
            "- 对专业用户：可使用夏普比率、VaR等专业指标\n"
            "- 所有推荐须标注数据来源\n"
            "- 末尾须附带风险提示语\n"
            "- 不承诺保本、保证收益"
        )

    async def generate_response(
        self,
        user_id: str,
        user_input: str,
        profile_summary: str = "",
        market_analysis: str = "",
        product_recommendation: str = "",
        recommendations: list[RecommendationItem] | None = None,
    ) -> str:
        """
        生成最终对话回复
        """
        # 获取用户记忆上下文
        memory_context = self.memory.get_profile_summary(user_id)
        conversation_history = self.memory.get_context(user_id)

        # 构建综合上下文
        system_prompt = self.get_system_prompt()
        context_parts = []
        if profile_summary:
            context_parts.append(f"【客户画像】\n{profile_summary}")
        if market_analysis:
            context_parts.append(f"【市场分析】\n{market_analysis}")
        if product_recommendation:
            context_parts.append(f"【资产配置建议】\n{product_recommendation}")
        if recommendations:
            rec_text = "\n".join(
                f"- {r.product_name}({r.product_type}, {r.risk_level}, "
                f"配置{r.allocation_ratio*100:.1f}%)"
                for r in recommendations
            )
            context_parts.append(f"【推荐产品】\n{rec_text}")
        context = "\n\n".join(context_parts)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"【用户长期记忆】\n{memory_context}"},
            {"role": "system", "content": context},
        ]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_input})

        response = await self.llm.chat(messages)

        # 强制附加风险提示（双重保障）
        if "理财非存款" not in response:
            response += "\n\n" + settings.compliance.risk_disclosure_text

        self.thoughts.append(AgentThought(
            agent_name=self.name,
            thought="整合各Agent结果生成最终回复",
            action="llm_generate",
            observation=response[:200],
        ))
        logger.info("话术生成Agent完成回复生成")
        return response

    async def generate_wealth_report(
        self,
        user_id: str,
        risk_level: RiskLevel,
        market_analysis: str,
        recommendation_text: str,
        recommendations: list[RecommendationItem],
        reasoning_chain: list,
    ) -> str:
        """生成结构化理财报告"""
        from datetime import datetime
        report = f"""
╔══════════════════════════════════════════╗
║        智慧银行理财顾问 - 理财配置报告       ║
╚══════════════════════════════════════════╝

报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
用户风险等级：{risk_level.value}
报告编号：RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
一、市场环境分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{market_analysis}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二、个性化资产配置方案
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{recommendation_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
三、配置明细与推荐理由（XAI可解释）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        for rec in recommendations:
            report += (
                f"\n■ {rec.product_name} ({rec.product_type})\n"
                f"  风险等级：{rec.risk_level}\n"
                f"  配置比例：{rec.allocation_ratio*100:.1f}%\n"
                f"  推荐理由：{rec.recommended_reason}\n"
                f"  数据来源：{rec.data_source}\n"
                f"  合规校验：{'通过' if rec.compliance_passed else '未通过'}\n"
            )

        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
四、推理过程（XAI推理链可视化）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        for i, thought in enumerate(reasoning_chain, 1):
            report += f"\n步骤{i} [{thought.agent_name}]:\n  {thought.thought}\n"
            if thought.action:
                report += f"  动作: {thought.action}\n"
            if thought.observation:
                report += f"  观察: {thought.observation[:150]}\n"

        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
五、风险提示
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{settings.compliance.risk_disclosure_text}

本报告由智慧银行理财顾问智能体生成，仅供参考，不构成投资建议。
理财最终决策由用户自行负责。

╔══════════════════════════════════════════╗
║  审计追溯链已记录 | 全链路可审计 | 满足监管要求 ║
╚══════════════════════════════════════════╝
"""
        return report.strip()
