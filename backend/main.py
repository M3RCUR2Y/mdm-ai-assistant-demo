import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import config
from backend.intent_router import IntentRouter
from backend.workflows.rule_query import RuleQueryWorkflow
from backend.workflows.data_query import DataQueryWorkflow
from backend.workflows.dual_query import DualQueryWorkflow
from backend.workflows.clarification import ClarificationWorkflow
from backend.tools.knowledge_tool import KnowledgeTool
from backend.tools.mdm_query_tool import MdmQueryTool
from backend.tools.entity_verify_tool import EntityVerifyTool
from backend.tools.bad_case_tool import BadCaseTool
from backend.llm.base import create_llm

app = FastAPI(title="主数据AI助手（数智管家）- Demo")

# --- Init ---
kb_tool = KnowledgeTool()
mdm_tool = MdmQueryTool()
entity_tool = EntityVerifyTool()
bad_case_tool = BadCaseTool()
llm = create_llm()

intent_router = IntentRouter(llm=llm)

workflows = {
    "Intent_Rule": RuleQueryWorkflow(kb_tool, bad_case_tool, llm),
    "Intent_Data": DataQueryWorkflow(entity_tool, mdm_tool, bad_case_tool, llm),
    "Intent_Dual": DualQueryWorkflow(entity_tool, kb_tool, mdm_tool, bad_case_tool, llm),
    "Intent_Clarify": ClarificationWorkflow(llm),
}


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class ChatResponse(BaseModel):
    message: str
    intent: str
    sources: list[dict] = []
    is_bad_case: bool = False
    session_id: str = ""


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())[:8]

    intent, confidence = intent_router.classify(req.message)

    if intent not in workflows:
        intent = "Intent_Clarify"

    workflow = workflows[intent]
    result = workflow.execute(req.message, session_id)

    return ChatResponse(
        message=result["message"],
        intent=intent,
        sources=result.get("sources", []),
        is_bad_case=result.get("is_bad_case", False),
        session_id=session_id,
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "llm_mode": config.LLM_MODE}


@app.get("/api/examples")
async def examples():
    return {
        "examples": [
            {"label": "字段枚举查询（意图A）", "text": "物料申请里「来源类型」字段有哪些枚举值？"},
            {"label": "命名规范修改（意图A）", "text": "申请被退回，原因是命名规范不符，我应该怎么改？"},
            {"label": "实体状态查询（意图B）", "text": "物料编码 PART-2024-001 现在的状态是什么？"},
            {"label": "双库联动查询（意图C）", "text": "物料 PART-2024-003 是冻结状态，还能发起采购申请吗？"},
            {"label": "澄清反问（意图D）", "text": "物料状态怎么查？"},
            {"label": "实体不存在（边界测试）", "text": "物料编码 FAKE-9999-XX 现在什么状态？"},
        ]
    }


# Mount frontend static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")


@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
