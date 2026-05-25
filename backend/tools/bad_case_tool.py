import json
import os
import time
from backend.config import config


class BadCaseTool:
    """Bad Case 标记工具 — 将无法解答的问题写入运营反馈队列"""

    def __init__(self):
        self.log_path = config.BAD_CASE_LOG_PATH

    def log(self, user_query: str, reason: str, session_id: str, kb_version: str = "KB_v1.0"):
        """
        静默记录 Bad Case（不影响主流程响应时延）。
        reason: 失败类型
          - "knowledge_no_result": 知识库检索无结果
          - "mdm_no_data": MDM 中无该实体
          - "intent_unclear": 意图无法识别
          - "out_of_scope": 超出主数据范围
        """
        entry = {
            "user_query": user_query,
            "failure_reason": reason,
            "session_id": session_id,
            "kb_version": kb_version,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        existing = []
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []

        existing.append(entry)

        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
