class ClarificationWorkflow:
    """意图D：澄清工作流"""

    def __init__(self, llm):
        self.llm = llm
        self.attempts: dict[str, int] = {}

    def execute(self, user_query: str, session_id: str) -> dict:
        attempt = self.attempts.get(session_id, 0) + 1
        self.attempts[session_id] = attempt

        message = self.llm.generate_clarification(user_query, attempt)

        return {
            "message": message,
            "sources": [],
            "is_bad_case": attempt >= 2,
        }
