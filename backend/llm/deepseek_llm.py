from openai import OpenAI
from backend.config import config
from backend.llm.base import LLMBase


class DeepSeekLLM(LLMBase):
    """DeepSeek API 实现"""

    def __init__(self):
        self.client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
        self.model = config.DEEPSEEK_MODEL

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            # 降级到 MockLLM
            from backend.llm.mock_llm import MockLLM
            mock = MockLLM()
            return mock.generate(system_prompt, user_prompt)

    def classify_intent(self, user_message: str, has_entity: bool) -> tuple[str, float]:
        """使用 DeepSeek few-shot 进行意图分类"""
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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=32,
            )
            result = response.choices[0].message.content.strip()

            for intent in ["Intent_Rule", "Intent_Data", "Intent_Dual", "Intent_Clarify"]:
                if intent in result:
                    return (intent, 0.9)

            return ("Intent_Clarify", 0.5)
        except Exception:
            from backend.llm.mock_llm import MockLLM
            mock = MockLLM()
            return mock.classify_intent(user_message, has_entity)
