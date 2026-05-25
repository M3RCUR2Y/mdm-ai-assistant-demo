from abc import ABC, abstractmethod
from backend.config import config


class LLMBase(ABC):
    """LLM 抽象接口"""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """生成回答"""
        ...


def create_llm() -> LLMBase:
    """工厂函数：根据配置创建 LLM 实例"""
    if config.LLM_MODE == "deepseek" and config.DEEPSEEK_API_KEY:
        from backend.llm.deepseek_llm import DeepSeekLLM
        return DeepSeekLLM()
    else:
        from backend.llm.mock_llm import MockLLM
        return MockLLM()
