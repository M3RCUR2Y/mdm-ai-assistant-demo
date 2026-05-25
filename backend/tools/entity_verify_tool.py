import json
import re
from backend.config import config


class EntityVerifyTool:
    """实体真实性核查工具 — 验证实体编码是否存在于 MDM 中"""

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
        index = {}
        for e in self._entities:
            index[e["entity_id"]] = e
        return index

    def verify(self, entity_type: str, entity_id: str) -> dict:
        """
        核查实体是否存在。
        返回: {"exists": bool, "entity_id": str, "entity_type": str, "message": str}
        """
        entity_type = entity_type.upper()

        if entity_id in self._entity_index:
            entity = self._entity_index[entity_id]
            if entity["entity_type"].upper() == entity_type or not entity_type:
                return {
                    "exists": True,
                    "entity_id": entity["entity_id"],
                    "entity_type": entity["entity_type"],
                    "message": f"{entity_type} {entity_id} 存在于 MDM 中",
                }

        return {
            "exists": False,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "message": f"MDM 中未查到编码 {entity_id}，该编码可能不存在或尚未录入 MDM。请确认编码是否有误，或联系数据 BP 确认该实体的录入状态。",
        }


def extract_entity_from_query(text: str) -> tuple[str | None, str | None]:
    """
    从用户输入中尝试提取实体编码和类型。
    返回 (entity_type, entity_id) 或 (None, None)
    """
    # 标准前缀匹配
    patterns = [
        (r"PART-\d{4}-\d{3,}", "PART"),
        (r"SUP-\d{4}-\d{3,}", "SUPPLIER"),
        (r"SKU-[A-Z]+-\d{4}-[A-Za-z]+", "SKU"),
    ]

    for pattern, etype in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return (etype, match.group(0).upper())

    # 宽松匹配：任意2+大写字母前缀 + 数字的编码模式 (如 FAKE-9999-XX)
    loose = re.search(r"([A-Z]{2,})[\s-]*(\d[\d\-]*[A-Za-z\d]*)", text)
    if loose:
        prefix = loose.group(1).upper()
        rest = loose.group(2)
        entity_id = f"{prefix}-{rest}"
        type_map = {"PART": "PART", "SUP": "SUPPLIER", "SKU": "SKU"}
        etype = type_map.get(prefix, "PART")
        return (etype, entity_id)

    # 兜底：尝试匹配 PART/SUP/SKU 后跟内容
    for etype, prefix in [("PART", "PART"), ("SUPPLIER", "SUP"), ("SKU", "SKU")]:
        m = re.search(rf"{prefix}[-\s]*([\w\d][-\w\d]*)", text, re.IGNORECASE)
        if m:
            raw = f"{prefix}-{m.group(1)}"
            return (etype, raw)

    return (None, None)
