from backend.config import config
from backend.llm.base import OpenAICompatibleLLM


class QwenLLM(OpenAICompatibleLLM):
    """通义千问 (Qwen) API 实现"""

    def __init__(self):
        super().__init__(
            api_key=config.QWEN_API_KEY,
            base_url=config.QWEN_BASE_URL,
            model=config.QWEN_MODEL,
        )
