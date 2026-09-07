"""
用户风险测评工具

智能体可调用此工具对用户进行风险测评，
输出风险等级，用于后续产品匹配与适当性管理。
"""
from __future__ import annotations

from tools.base import BaseTool
from core.models import RiskLevel
from loguru import logger


# 风险测评题库
RISK_QUESTIONS: list[dict] = [
    {
        "question": "您的年龄段是？",
        "options": [
            {"text": "65岁以上", "score": 1},
            {"text": "55-65岁", "score": 2},
            {"text": "45-55岁", "score": 3},
            {"text": "35-45岁", "score": 4},
            {"text": "35岁以下", "score": 5},
        ],
    },
    {
        "question": "您的家庭可支配月收入约为？",
        "options": [
            {"text": "5000元以下", "score": 1},
            {"text": "5000-1万元", "score": 2},
            {"text": "1万-3万元", "score": 3},
            {"text": "3万-10万元", "score": 4},
            {"text": "10万元以上", "score": 5},
        ],
    },
    {
        "question": "您目前可用于理财的资金占家庭总资产比例？",
        "options": [
            {"text": "10%以下", "score": 1},
            {"text": "10%-30%", "score": 2},
            {"text": "30%-50%", "score": 3},
            {"text": "50%-70%", "score": 4},
            {"text": "70%以上", "score": 5},
        ],
    },
    {
        "question": "如果您的投资组合在一个月内下跌20%，您会？",
        "options": [
            {"text": "立即全部赎回，止损", "score": 1},
            {"text": "赎回部分，减少损失", "score": 2},
            {"text": "持有观望", "score": 3},
            {"text": "逢低加仓", "score": 4},
            {"text": "大幅加仓", "score": 5},
        ],
    },
    {
        "question": "您的理财首要目标是？",
        "options": [
            {"text": "保本，绝对不能亏", "score": 1},
            {"text": "稳健增值，可接受小幅波动", "score": 2},
            {"text": "平衡增长与风险", "score": 3},
            {"text": "追求较高收益，可承受中等波动", "score": 4},
            {"text": "追求高收益，可承受较大波动甚至本金损失", "score": 5},
        ],
    },
    {
        "question": "您计划的投资期限是？",
        "options": [
            {"text": "3个月以内", "score": 1},
            {"text": "3个月-1年", "score": 2},
            {"text": "1-3年", "score": 3},
            {"text": "3-5年", "score": 4},
            {"text": "5年以上", "score": 5},
        ],
    },
    {
        "question": "您是否有过投资亏损经历？亏损时您的反应是？",
        "options": [
            {"text": "无投资经验", "score": 1},
            {"text": "亏损后焦虑失眠，难以接受", "score": 2},
            {"text": "亏损后有些不安但能接受", "score": 3},
            {"text": "亏损后理性分析，调整策略", "score": 4},
            {"text": "亏损视为机会，继续加仓", "score": 5},
        ],
    },
]


def _score_to_level(total_score: int) -> RiskLevel:
    """分数转风险等级"""
    if total_score <= 8:
        return RiskLevel.CONSERVATIVE   # C1
    elif total_score <= 13:
        return RiskLevel.STEADY          # C2
    elif total_score <= 19:
        return RiskLevel.BALANCED        # C3
    elif total_score <= 26:
        return RiskLevel.GROWTH          # C4
    else:
        return RiskLevel.AGGRESSIVE     # C5


class RiskAssessmentTool(BaseTool):
    """用户风险测评工具"""

    name = "assess_risk"
    description = (
        "对用户进行风险承受能力测评。可通过answers参数直接传入答案数组"
        "（与题库顺序一致，值为1-5的选项序号），快速生成风险等级。"
        "也可通过action=get_questions获取题库内容。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get_questions", "submit_answers"],
                "description": "获取题库或提交答案",
                "default": "get_questions",
            },
            "answers": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "答案数组，值为1-5（对应每题选项序号）",
            },
        },
        "required": ["action"],
    }

    async def execute(
        self,
        action: str = "get_questions",
        answers: list[int] | None = None,
    ) -> str:
        logger.info(f"风险测评: action={action}")

        if action == "get_questions":
            lines = ["【风险测评题库】请逐题作答（选填1-5）：\n"]
            for i, q in enumerate(RISK_QUESTIONS, 1):
                lines.append(f"{i}. {q['question']}")
                for j, opt in enumerate(q["options"], 1):
                    lines.append(f"   {j}. {opt['text']}")
                lines.append("")
            lines.append("请按顺序回复7个数字（如：3 2 3 3 2 3 3），即可得出您的风险等级。")
            return "\n".join(lines)

        elif action == "submit_answers":
            if not answers or len(answers) != len(RISK_QUESTIONS):
                return f"答案数量不正确，需回答{len(RISK_QUESTIONS)}题。"

            total = 0
            for i, ans in enumerate(answers):
                idx = max(1, min(5, ans)) - 1
                total += RISK_QUESTIONS[i]["options"][idx]["score"]

            level = _score_to_level(total)
            return (
                f"【风险测评结果】\n"
                f"  总分：{total}分（满分35分）\n"
                f"  风险等级：{level.value}（C{level.level_num}）\n"
                f"  可购买产品风险等级：R1-R{level.level_num}\n"
                f"  含义：{self._level_description(level)}\n"
                f"\n提示：测评结果有效期1年，超期须重新测评。"
            )

        return "action参数无效，请使用get_questions或submit_answers"

    def _level_description(self, level: RiskLevel) -> str:
        descs = {
            RiskLevel.CONSERVATIVE: "不能接受本金损失，以保本为首要目标",
            RiskLevel.STEADY: "可接受小幅短期波动，追求稳定收益",
            RiskLevel.BALANCED: "可接受中等波动，追求较稳健增长",
            RiskLevel.GROWTH: "可接受较大波动，追求较高增值",
            RiskLevel.AGGRESSIVE: "可接受大幅波动甚至本金较大损失，追求高收益",
        }
        return descs.get(level, "")
