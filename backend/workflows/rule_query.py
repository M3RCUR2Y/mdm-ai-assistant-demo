class RuleQueryWorkflow:
    """意图A：规则咨询工作流"""

    def __init__(self, kb_tool, bad_case_tool, llm):
        self.kb_tool = kb_tool
        self.bad_case_tool = bad_case_tool
        self.llm = llm

    def execute(self, user_query: str, session_id: str) -> dict:
        chunks, max_score = self.kb_tool.search(user_query)

        if not chunks or max_score < 0.05:
            self.bad_case_tool.log(user_query, "knowledge_no_result", session_id)
            message = self.llm.generate_rule_answer(user_query, [], no_result=True)
            return {
                "message": message,
                "sources": [],
                "is_bad_case": True,
            }

        message = self.llm.generate_rule_answer(user_query, chunks, no_result=False)

        sources = []
        for ch in chunks[:3]:
            sources.append({
                "type": "knowledge",
                "doc": ch.get("source", "").replace(".md", ""),
                "section": ch.get("section", ""),
                "score": round(ch.get("score", 0), 3),
            })

        return {
            "message": message,
            "sources": sources,
            "is_bad_case": False,
        }
