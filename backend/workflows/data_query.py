from backend.tools.entity_verify_tool import extract_entity_from_query


class DataQueryWorkflow:
    """意图B：数据查询工作流"""

    def __init__(self, entity_tool, mdm_tool, bad_case_tool, llm):
        self.entity_tool = entity_tool
        self.mdm_tool = mdm_tool
        self.bad_case_tool = bad_case_tool
        self.llm = llm

    def execute(self, user_query: str, session_id: str) -> dict:
        entity_type, entity_id = extract_entity_from_query(user_query)

        if not entity_id:
            # 用户提供了名称而非编码，尝试验证
            self.bad_case_tool.log(user_query, "intent_unclear", session_id)
            return {
                "message": "请提供需要查询的实体编码（如 PART-2024-001、SUP-2023-456），以便我为您查询当前状态。",
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

        # Step 2: MDM 查询
        entity_data = self.mdm_tool.query(verify_result["entity_id"])

        if entity_data is None:
            self.bad_case_tool.log(user_query, "mdm_no_data", session_id)
            return {
                "message": f"MDM 中未查到编码 {entity_id}，请确认编码是否正确。",
                "sources": [],
                "is_bad_case": True,
            }

        # Step 3: 格式化输出
        message = self.llm.generate_data_answer(entity_data, user_query)

        return {
            "message": message,
            "sources": [{
                "type": "mdm",
                "entity_id": entity_data.get("entity_id", ""),
                "query_time": entity_data.get("query_time", ""),
            }],
            "is_bad_case": False,
        }
