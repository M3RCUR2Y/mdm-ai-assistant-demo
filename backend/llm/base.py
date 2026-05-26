from abc import ABC, abstractmethod
from backend.config import config


class LLMBase(ABC):
    """LLM 抽象接口"""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """生成回答"""
        ...

    @abstractmethod
    def classify_intent(self, user_message: str, has_entity: bool) -> tuple[str, float]:
        """意图分类"""
        ...

    @abstractmethod
    def generate_rule_answer(self, user_query: str, chunks: list[dict], no_result: bool) -> str:
        """生成规则咨询回答"""
        ...

    @abstractmethod
    def generate_data_answer(self, entity_data: dict, user_query: str) -> str:
        """生成数据查询回答"""
        ...

    @abstractmethod
    def generate_dual_answer(self, entity_data: dict, chunks: list[dict], user_query: str) -> str:
        """生成双库联动回答"""
        ...

    @abstractmethod
    def generate_clarification(self, user_query: str, attempt: int) -> str:
        """生成澄清反问"""
        ...


class OpenAICompatibleLLM(LLMBase):
    """OpenAI 兼容 API 的通用实现，适用于 DeepSeek / Qwen / MiMo 等"""

    def __init__(self, api_key: str, base_url: str, model: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)
        self.model = model

    def _chat(self, messages: list[dict], temperature: float = 0.3, max_tokens: int = 4096) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            return self._chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception:
            from backend.llm.mock_llm import MockLLM
            return MockLLM().generate(system_prompt, user_prompt)

    def classify_intent(self, user_message: str, has_entity: bool) -> tuple[str, float]:
        prompt = f"""你是荣耀主数据AI助手（数智管家）的意图路由模块。
分析用户的最新输入，将其准确分类到以下意图之一。

[意图定义]
- Intent_Rule: 规则咨询。询问主数据流程、字段定义、申请规则等知识，不依赖具体实体编码的当前数据
- Intent_Data: 数据查询。给出具体实体标识（编码或名称），询问该实体在MDM中的当前状态或字段值
- Intent_Dual: 双库联动。同时关注某具体实体的当前状态，且期望获得规则解读或下一步操作指引
- Intent_Clarify: 需要澄清。无法明确判断上述三类，或缺少关键信息

[Few-shot 示例]
User: "SKU 和 SPU 有什么区别？" → Intent_Rule
User: "物料编码 12345 现在的状态是什么？" → Intent_Data
User: "物料 12345 是冻结状态，还能发起采购申请吗？" → Intent_Dual
User: "物料状态怎么查？" → Intent_Clarify

[用户输入]
User: "{user_message}"

请只返回意图标签（Intent_Rule / Intent_Data / Intent_Dual / Intent_Clarify），不要其他内容。"""

        try:
            result = self._chat(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            result = result.strip()

            for intent in ["Intent_Rule", "Intent_Data", "Intent_Dual", "Intent_Clarify"]:
                if intent in result:
                    return (intent, 0.9)

            return ("Intent_Clarify", 0.5)
        except Exception:
            from backend.llm.mock_llm import MockLLM
            return MockLLM().classify_intent(user_message, has_entity)

    def generate_rule_answer(self, user_query: str, chunks: list[dict], no_result: bool) -> str:
        if no_result or not chunks:
            from backend.llm.mock_llm import MockLLM
            return MockLLM().generate_rule_answer(user_query, chunks, no_result)

        context = self._format_knowledge_chunks(chunks)
        system_prompt = (
            "你是荣耀主数据 AI 助手（数智管家），负责回答主数据规则、流程、字段定义和操作指引问题。"
            "必须只依据给定知识库片段回答，不要编造。回答要简洁、可执行，并在末尾标注【知识库】来源。"
        )
        user_prompt = f"""用户问题：
{user_query}

知识库片段：
{context}

请基于上述片段回答。若片段不足以回答，请直接说明当前知识库未找到足够信息，并建议联系数据 BP。"""

        return self._generate_business_answer(
            system_prompt,
            user_prompt,
            lambda: self._mock().generate_rule_answer(user_query, chunks, no_result),
        )

    def generate_data_answer(self, entity_data: dict, user_query: str) -> str:
        system_prompt = (
            "你是荣耀主数据 AI 助手（数智管家），负责把 MDM 查询结果整理成准确答复。"
            "只能使用给定实体数据，不要补充不存在的字段或推测。回答末尾必须包含【MDM】来源信息。"
        )
        user_prompt = f"""用户问题：
{user_query}

MDM 实体数据：
{self._format_entity_data(entity_data)}

请用中文给出结构化回答。"""

        return self._generate_business_answer(
            system_prompt,
            user_prompt,
            lambda: self._mock().generate_data_answer(entity_data, user_query),
        )

    def generate_dual_answer(self, entity_data: dict, chunks: list[dict], user_query: str) -> str:
        system_prompt = (
            "你是荣耀主数据 AI 助手（数智管家），负责融合 MDM 当前数据与知识库规则。"
            "先给明确结论，再给 MDM 状态、规则依据和下一步建议。只能依据给定数据和规则片段回答，"
            "必须标注【MDM】和【知识库】来源。"
        )
        user_prompt = f"""用户问题：
{user_query}

MDM 实体数据：
{self._format_entity_data(entity_data)}

知识库片段：
{self._format_knowledge_chunks(chunks)}

请判断用户关心的操作是否可行，并说明规则依据和下一步建议。"""

        return self._generate_business_answer(
            system_prompt,
            user_prompt,
            lambda: self._mock().generate_dual_answer(entity_data, chunks, user_query),
        )

    def generate_clarification(self, user_query: str, attempt: int) -> str:
        system_prompt = (
            "你是荣耀主数据 AI 助手（数智管家）。当用户问题不完整时，用一句到两句中文反问澄清。"
            "不要展开长篇说明，不要编造答案。"
        )
        user_prompt = f"""用户问题：
{user_query}

这是当前会话第 {attempt} 次澄清。请引导用户补充主数据类型、实体编码或想了解的规则范围。"""

        return self._generate_business_answer(
            system_prompt,
            user_prompt,
            lambda: self._mock().generate_clarification(user_query, attempt),
        )

    def _generate_business_answer(self, system_prompt: str, user_prompt: str, fallback) -> str:
        try:
            answer = self._chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            ).strip()
            return answer or fallback()
        except Exception:
            return fallback()

    def _format_knowledge_chunks(self, chunks: list[dict]) -> str:
        if not chunks:
            return "无匹配知识库片段。"

        lines = []
        for index, chunk in enumerate(chunks[:3], start=1):
            source = chunk.get("source", "未知文档").replace(".md", "")
            section = chunk.get("section", "相关章节")
            score = chunk.get("score", 0)
            content = chunk.get("content", "").strip()
            lines.append(
                f"[片段{index}] 来源：《{source}》{section}，相似度：{score:.3f}\n{content}"
            )
        return "\n\n".join(lines)

    def _format_entity_data(self, entity_data: dict) -> str:
        return "\n".join(
            f"- {key}: {value}"
            for key, value in entity_data.items()
            if value not in ("", None)
        )

    def _mock(self):
        from backend.llm.mock_llm import MockLLM
        return MockLLM()


def create_llm() -> LLMBase:
    """工厂函数：根据 LLM_MODE 创建对应实例"""
    mode = config.LLM_MODE.lower()

    if mode == "deepseek" and config.DEEPSEEK_API_KEY:
        from backend.llm.deepseek_llm import DeepSeekLLM
        return DeepSeekLLM()

    if mode == "qwen" and config.QWEN_API_KEY:
        from backend.llm.qwen_llm import QwenLLM
        return QwenLLM()

    if mode == "mimo" and config.MIMO_API_KEY:
        from backend.llm.mimo_llm import MiMoLLM
        return MiMoLLM()

    from backend.llm.mock_llm import MockLLM
    return MockLLM()
