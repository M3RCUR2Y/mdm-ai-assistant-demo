from backend.tools.entity_verify_tool import extract_entity_from_query


class DualQueryWorkflow:
    """意图C：双库联动工作流"""

    def __init__(self, entity_tool, kb_tool, mdm_tool, bad_case_tool, llm):
        self.entity_tool = entity_tool
        self.kb_tool = kb_tool
        self.mdm_tool = mdm_tool
        self.bad_case_tool = bad_case_tool
        self.llm = llm

    def execute(self, user_query: str, session_id: str) -> dict:
        entity_type, entity_id = extract_entity_from_query(user_query)

        if not entity_id:
            return {
                "message": "请提供需要查询的实体编码（如 PART-2024-001），以便我同时查询实体状态和对应规则。",
                "sources": [],
                "is_bad_case": True,
            }

        # Step 1: 实体核查
        verify_result = self.entity_tool.verify(entity_type or "PART", entity_id)

        if not verify_result["exists"]:
            self.bad_case_tool.log(user_query, "mdm_no_data", session_id)
            return {
                "message": verify_result["message"],
                "sources": [],
                "is_bad_case": True,
            }

        # Step 2: 并行查询（知识库 + MDM）
        entity_data = self.mdm_tool.query(verify_result["entity_id"])
        rule_query_clean = self._clean_query_for_kb(user_query)
        chunks, _ = self.kb_tool.search(rule_query_clean)

        if entity_data is None:
            return {
                "message": f"当前 MDM 数据查询暂时不可用，请稍后重试或直接登录 MDM 系统查询。\n以下规则来自知识库，实体当前数据请手动确认。",
                "sources": [],
                "is_bad_case": True,
            }

        # Step 3: 融合推理 + 格式化输出
        message = self.llm.generate_dual_answer(entity_data, chunks, user_query)

        sources = []
        sources.append({
            "type": "mdm",
            "entity_id": entity_data.get("entity_id", ""),
            "query_time": entity_data.get("query_time", ""),
        })
        for ch in chunks[:2]:
            sources.append({
                "type": "knowledge",
                "doc": ch.get("source", "").replace(".md", ""),
                "section": ch.get("section", ""),
                "score": round(ch.get("score", 0), 3),
            })

        is_bad_case = len(chunks) == 0
        if is_bad_case:
            self.bad_case_tool.log(user_query, "knowledge_no_result", session_id)

        return {
            "message": message,
            "sources": sources,
            "is_bad_case": is_bad_case,
        }

    def _clean_query_for_kb(self, query: str) -> str:
        """去除查询中的实体编码，聚焦规则语义"""
        import re
        cleaned = re.sub(r"(PART|SUP|SKU)[-\s]*[\d\-]+", "", query, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or query
