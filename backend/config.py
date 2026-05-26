import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    LLM_MODE: str = os.getenv("LLM_MODE", "mock")

    # DeepSeek
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    # 通义千问 (Qwen)
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    QWEN_BASE_URL: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode")
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen-plus")

    # MiMo (小米)
    MIMO_API_KEY: str = os.getenv("MIMO_API_KEY", "")
    MIMO_BASE_URL: str = os.getenv("MIMO_BASE_URL", "https://api.mimo.ai/v1")
    MIMO_MODEL: str = os.getenv("MIMO_MODEL", "MiMo-7B-RL")

    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    KB_DIR: str = os.path.join(BASE_DIR, "data", "knowledge_base")
    MDM_DATA_PATH: str = os.path.join(BASE_DIR, "data", "mdm_data.json")
    BAD_CASE_LOG_PATH: str = os.path.join(BASE_DIR, "data", "bad_cases.json")
    PROMPTS_DIR: str = os.path.join(BASE_DIR, "prompts")

    INTENT_CONFIDENCE_THRESHOLD: float = 0.7
    KB_TOP_K: int = 5
    KB_SIMILARITY_THRESHOLD: float = 0.1


config = Config()
