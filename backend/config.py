import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    LLM_MODE: str = os.getenv("LLM_MODE", "mock")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    KB_DIR: str = os.path.join(BASE_DIR, "data", "knowledge_base")
    MDM_DATA_PATH: str = os.path.join(BASE_DIR, "data", "mdm_data.json")
    BAD_CASE_LOG_PATH: str = os.path.join(BASE_DIR, "data", "bad_cases.json")
    PROMPTS_DIR: str = os.path.join(BASE_DIR, "prompts")

    INTENT_CONFIDENCE_THRESHOLD: float = 0.7
    KB_TOP_K: int = 5
    KB_SIMILARITY_THRESHOLD: float = 0.1


config = Config()
