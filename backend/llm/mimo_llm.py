from backend.config import config
from backend.llm.base import OpenAICompatibleLLM


class MiMoLLM(OpenAICompatibleLLM):
    """MiMo (小米) API 实现"""

    def __init__(self):
        super().__init__(
            api_key=config.MIMO_API_KEY,
            base_url=config.MIMO_BASE_URL,
            model=config.MIMO_MODEL,
        )
