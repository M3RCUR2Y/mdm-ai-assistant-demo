import re
from backend.config import config


class IntentRouter:
    """
    意图识别路由器 — 三级策略：
    1. 正则提取实体编码
    2. 关键词规则匹配
    3. LLM 降级分类
    """

    def __init__(self, llm):
        self.llm = llm
        self.threshold = config.INTENT_CONFIDENCE_THRESHOLD

    def classify(self, user_message: str) -> tuple[str, float]:
        """返回 (intent_label, confidence)"""
        has_entity = self._has_entity_code(user_message)

        # 通过 MockLLM 内置的关键词规则分类（confidence 已经反映规则匹配度）
        intent, confidence = self.llm.classify_intent(user_message, has_entity)

        # 如果规则匹配置信度高，直接返回
        if confidence >= self.threshold:
            return (intent, confidence)

        # 尝试优化：某些强信号可以直接用规则
        if has_entity and self._is_dual_query(user_message):
            return ("Intent_Dual", 0.80)

        if has_entity:
            return ("Intent_Data", 0.70)

        # 降级到 LLM few-shot（MockLLM 已经处理过了，这里作为最后一层）
        return (intent, confidence)

    def _has_entity_code(self, text: str) -> bool:
        pattern = r"(PART|SUP|SKU)[-\s]*[\w\d]"
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _is_dual_query(self, text: str) -> bool:
        """判断是否同时有实体编码和规则/下一步询问"""
        dual_keywords = [
            "还能", "能不能", "可以", "是否可以", "能否",
            "怎么处理", "怎么操作", "怎么办", "下一步",
            "采购", "申请", "上架", "发布", "怎么改",
        ]
        return any(kw in text for kw in dual_keywords)
