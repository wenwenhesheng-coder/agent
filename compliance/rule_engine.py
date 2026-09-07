"""
合规规则引擎（亮点七核心：RAG + 业务规则双轮驱动）

所有大模型输出先过合规校验，拦截违规输出：
- 禁止承诺保本、保证收益
- 校验输出是否匹配用户风险等级
- 敏感话术拦截
- 强制风险提示
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from loguru import logger

from config.settings import settings
from core.models import (
    ComplianceCheckResult,
    RiskLevel,
    RecommendationItem,
)


# ==================== 合规规则 ====================

class ComplianceRule:
    """合规规则基类"""

    name: str = ""
    description: str = ""

    def check(
        self,
        content: str,
        user_risk_level: RiskLevel = RiskLevel.CONSERVATIVE,
        recommendations: list[RecommendationItem] | None = None,
    ) -> list[str]:
        """执行校验，返回违规规则名称列表"""
        return []


class ProhibitGuaranteeRule(ComplianceRule):
    """规则1：禁止承诺保本/保证收益"""

    name = "prohibit_guarantee"
    description = "禁止承诺保本、保证收益、刚性兑付等违规表述"

    GUARANTEE_PATTERNS = [
        r"保本", r"保证本金", r"保证收益", r"确定收益",
        r"稳赚不赔", r"零风险", r"绝对安全", r"无风险",
        r"刚性兑付", r"兜底", r"包赚", r"百分百赚",
        r"保证升值", r"稳赚", r"一定赚", r"必定赚",
        r"投资无任何风险", r"没有任何风险",
    ]

    def check(self, content, user_risk_level=RiskLevel.CONSERVATIVE, recommendations=None):
        violations = []
        text = content
        for pattern in self.GUARANTEE_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                violations.append(
                    f"违规话术[{pattern}]出现{len(matches)}次，"
                    f"监管禁止承诺保本/保证收益"
                )
        return violations


class RiskLevelMatchRule(ComplianceRule):
    """规则2：风险等级匹配校验"""

    name = "risk_level_match"
    description = "校验输出推荐的产品是否超出用户风险承受能力"

    RISK_LEVEL_MAP = {
        "R1": 1, "R2": 2, "R3": 3, "R4": 4, "R5": 5,
        "低风险": 1, "中低风险": 2, "中风险": 3, "中高风险": 4, "高风险": 5,
        "谨慎型": 1, "稳健型": 2, "平衡型": 3, "进取型": 4, "激进型": 5,
    }

    def check(self, content, user_risk_level=RiskLevel.CONSERVATIVE, recommendations=None):
        violations = []
        user_level = user_risk_level.level_num

        # 检查推荐项中的产品风险等级
        if recommendations:
            for rec in recommendations:
                product_level = self._extract_risk_level(rec.risk_level)
                if product_level and product_level > user_level:
                    violations.append(
                        f"产品[{rec.product_name}]风险等级{rec.risk_level}"
                        f"超出用户风险等级({user_risk_level.value})，违反适当性管理"
                    )
                    rec.compliance_passed = False

        # 检查文本中提到的风险等级
        # 匹配"R数字"模式
        r_matches = re.findall(r"R([1-5])", content)
        for r_num in r_matches:
            if int(r_num) > user_level:
                violations.append(
                    f"输出提及R{r_num}产品，超出用户风险等级({user_risk_level.value})"
                )

        return violations

    def _extract_risk_level(self, text: str) -> int | None:
        for pattern, level in self.RISK_LEVEL_MAP.items():
            if pattern in text:
                return level
        return None


class SensitiveWordsRule(ComplianceRule):
    """规则3：敏感话术拦截"""

    name = "sensitive_words"
    description = "拦截诱导性、欺诈性、内幕信息等敏感话术"

    def check(self, content, user_risk_level=RiskLevel.CONSERVATIVE, recommendations=None):
        violations = []
        for word in settings.compliance.sensitive_words:
            if word in content:
                violations.append(
                    f"敏感话术[{word}]被拦截，违反金融营销宣传规定"
                )
        # 内幕信息
        if "内部消息" in content or "内幕" in content or "内部信息" in content:
            violations.append("违规提及内幕信息，违反证券法")
        # 无风险套利诱导
        if "无风险套利" in content or "稳赚套利" in content:
            violations.append("违规诱导无风险套利")
        return violations


class RiskDisclosureRule(ComplianceRule):
    """规则4：强制风险提示"""

    name = "risk_disclosure"
    description = "输出必须附带监管要求的风险提示语"

    REQUIRED_KEYWORDS = ["理财非存款", "产品有风险", "投资需谨慎"]

    def check(self, content, user_risk_level=RiskLevel.CONSERVATIVE, recommendations=None):
        violations = []
        # 只在有产品推荐/收益讨论时才强制
        needs_disclosure = any(
            kw in content for kw in
            ["收益", "推荐", "配置", "建议购买", "产品", "投资"]
        )
        if needs_disclosure:
            missing = [kw for kw in self.REQUIRED_KEYWORDS if kw not in content]
            if missing:
                violations.append(
                    f"输出缺少强制风险提示语（缺少：{','.join(missing)}）"
                )
        return violations


class ProductSourceRule(ComplianceRule):
    """规则5：产品信息来源校验（抑制幻觉）"""

    name = "product_source_check"
    description = "涉及产品推荐须标注数据来源，防止模型编造产品"

    def check(self, content, user_risk_level=RiskLevel.CONSERVATIVE, recommendations=None):
        violations = []
        if recommendations:
            for rec in recommendations:
                if not rec.data_source:
                    violations.append(
                        f"产品[{rec.product_name}]未标注数据来源，"
                        f"可能为模型编造（幻觉风险）"
                    )
        return violations


# ==================== 规则引擎 ====================

class ComplianceRuleEngine:
    """
    合规规则引擎
    - RAG + 业务规则双轮驱动
    - 所有规则独立配置，可扩展
    - 对Agent输出进行实时校验拦截
    """

    def __init__(self):
        self.rules: list[ComplianceRule] = []
        self._init_default_rules()

    def _init_default_rules(self):
        if settings.compliance.enable_prohibit_guarantee:
            self.rules.append(ProhibitGuaranteeRule())
        if settings.compliance.enable_risk_match_check:
            self.rules.append(RiskLevelMatchRule())
        if settings.compliance.enable_sensitive_words:
            self.rules.append(SensitiveWordsRule())
        if settings.compliance.enable_risk_disclosure:
            self.rules.append(RiskDisclosureRule())
        self.rules.append(ProductSourceRule())
        logger.info(f"合规规则引擎已加载 {len(self.rules)} 条规则")

    def check(
        self,
        content: str,
        user_risk_level: RiskLevel = RiskLevel.CONSERVATIVE,
        recommendations: list[RecommendationItem] | None = None,
    ) -> ComplianceCheckResult:
        """
        执行合规校验
        Returns: ComplianceCheckResult
        """
        all_violations: list[str] = []
        for rule in self.rules:
            violations = rule.check(content, user_risk_level, recommendations)
            all_violations.extend(violations)
            if violations:
                logger.warning(f"合规规则[{rule.name}]触发: {violations}")

        # 拦截违规内容
        sanitized = self._sanitize(content)
        # 强制附加风险提示
        if settings.compliance.enable_risk_disclosure:
            if "理财非存款" not in sanitized:
                sanitized = sanitized + "\n\n" + settings.compliance.risk_disclosure_text

        import uuid
        audit_id = f"AUD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

        return ComplianceCheckResult(
            passed=len(all_violations) == 0,
            violated_rules=all_violations,
            intercepted_content=content if all_violations else "",
            sanitized_content=sanitized,
            risk_warnings=[
                settings.compliance.risk_disclosure_text
            ] if all_violations else [],
            audit_id=audit_id,
        )

    def _sanitize(self, content: str) -> str:
        """对违规内容进行脱敏/替换处理"""
        sanitized = content
        for word in settings.compliance.sensitive_words:
            if word in sanitized:
                # 替换为合规表述
                replacement_map = {
                    "保本": "非保本（理财产品不保证本金安全）",
                    "保证收益": "预期收益（不构成承诺）",
                    "稳赚不赔": "投资有风险",
                    "零风险": "存在风险",
                    "绝对安全": "风险可控",
                    "无风险": "存在风险",
                    "刚性兑付": "禁止刚性兑付（已打破）",
                    "兜底": "不兜底",
                }
                replacement = replacement_map.get(word, f"[已拦截:{word}]")
                sanitized = sanitized.replace(word, replacement)
        return sanitized
