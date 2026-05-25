import json
import time
from backend.config import config


class MdmQueryTool:
    """MDM 结构化数据库查询工具 — 模拟"""

    def __init__(self):
        self._entities = self._load_entities()
        self._entity_index = self._build_index()

    def _load_entities(self) -> list[dict]:
        try:
            with open(config.MDM_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("entities", [])
        except Exception:
            return []

    def _build_index(self) -> dict[str, dict]:
        return {e["entity_id"]: e for e in self._entities}

    def query(self, entity_id: str, user_id: str = "demo_user") -> dict | None:
        """
        查询 MDM 数据库中的实体信息。
        参数:
          entity_id: 实体编码
          user_id: 用户身份标识（用于权限过滤）
        返回: 实体数据 dict 或 None
        """
        time.sleep(0.1)
        entity = self._entity_index.get(entity_id)

        if entity is None:
            return None

        # 模拟权限过滤：demo_user 有全部权限
        return {
            **entity,
            "query_time": time.strftime("%Y-%m-%d %H:%M"),
        }

    def search_by_name(self, name: str, entity_type: str = "PART") -> list[dict]:
        """按名称模糊搜索实体"""
        results = []
        for e in self._entities:
            if e.get("entity_type") == entity_type and name.lower() in e.get("name", "").lower():
                results.append({
                    **e,
                    "query_time": time.strftime("%Y-%m-%d %H:%M"),
                })
        return results
