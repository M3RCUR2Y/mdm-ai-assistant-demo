import time
from backend.llm.base import LLMBase


class MockLLM(LLMBase):
    """模拟 LLM — 基于模板生成，无需 API Key"""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """返回一个占位标记，实际内容由各工作流的模板逻辑生成"""
        return "[MOCK_LLM_GENERATE]"

    def classify_intent(self, user_message: str, has_entity: bool) -> tuple[str, float]:
        """基于关键词规则的意图分类（模拟 LLM 的 few-shot 分类）"""
        msg = user_message.lower()

        # 检测实体编码（宽松匹配：标准前缀 + 通用编码模式）
        import re
        has_code = bool(re.search(r"(PART|SUP|SKU)[-\s]*[\w\d]", msg, re.IGNORECASE))
        # 也检测通用编码模式（如 FAKE-9999-XX）
        if not has_code:
            has_code = bool(re.search(r"[A-Z]{2,}[\s-]*\d[\d\-]*[A-Za-z\d]*", msg, re.IGNORECASE))

        # 规则类关键词（询问知识/规范/流程）
        rule_keywords = [
            "字段", "流程", "规范", "怎么填", "怎么改", "退回", "修改",
            "区别", "有哪些", "枚举", "含义", "定义", "规则",
            "步骤", "怎么申请", "需要什么", "提交哪些", "材料", "资质",
            "准入", "禁止", "能不能", "有没有办法", "可不可以用",
            "编码规则", "命名", "格式", "缩写", "采购", "申请",
            "还能", "可以", "是否可以", "能否", "下一步", "怎么处理",
            "怎么操作", "怎么办", "上架", "发布",
        ]
        # 数据类关键词（查询具体实体的状态/属性）
        data_keywords = [
            "状态", "编码.*查询", "有没有.*编码", "负责.*是谁",
            "查一下.*物料", "查一下.*供应商", "系统里有没有",
            "叫什么", "是哪家",
        ]
        # 澄清触发词（模糊，需要用户补充信息）
        clarify_keywords = [
            "怎么查", "帮我看看", "帮我判断",
        ]
        # 纯数据信号：有编码 + 只问状态 → 不是规则
        pure_data_signals = [
            "状态是什么", "什么状态", "的状态", "状态$",
        ]

        is_rule = any(re.search(kw, msg) for kw in rule_keywords)
        is_data = any(re.search(kw, msg) for kw in data_keywords)
        is_clarify = any(re.search(kw, msg) for kw in clarify_keywords)
        is_pure_data = any(re.search(kw, msg) for kw in pure_data_signals)

        # 有编码 + 只问状态/属性 → 纯数据查询
        if has_code and is_pure_data and not any(re.search(kw, msg) for kw in ["采购", "申请", "还能", "能不能", "能否", "下一步", "怎么处理"]):
            return ("Intent_Data", 0.90)

        # 双库联动：有编码 + 规则问题
        if has_code and is_rule:
            return ("Intent_Dual", 0.85)

        # 数据查询：有编码 + 数据问题
        if has_code and (is_data or not is_rule):
            return ("Intent_Data", 0.85)

        # 数据查询：有编码但无明确意图 → 默认为数据查询
        if has_code:
            return ("Intent_Data", 0.70)

        # 规则咨询：明确的规则问题
        if is_rule:
            return ("Intent_Rule", 0.85)

        # 澄清：模糊输入
        if is_clarify and not has_code:
            return ("Intent_Clarify", 0.60)

        # 默认：规则咨询
        return ("Intent_Rule", 0.55)

    def generate_rule_answer(self, user_query: str, chunks: list[dict], no_result: bool) -> str:
        """生成规则咨询回答"""
        if no_result or not chunks:
            return self._out_of_scope_or_no_result(user_query)

        best = chunks[0]
        source = best.get("source", "未知文档").replace(".md", "")
        section = best.get("section", "相关章节")

        lines = [self._build_answer_from_chunk(best, source, section)]
        return "\n\n".join(lines)

    def generate_data_answer(self, entity_data: dict, user_query: str) -> str:
        """生成数据查询回答"""
        status = entity_data.get("status", "未知")
        eid = entity_data.get("entity_id", "")
        etype = entity_data.get("entity_type", "")
        name = entity_data.get("name", "")
        owner = entity_data.get("owner", "")
        query_time = entity_data.get("query_time", "")
        department = entity_data.get("department", "")
        category = entity_data.get("category", "")

        lines = [
            f"{etype} {eid}（{name}）当前状态为【{status}】。",
            f"- 负责工程师：{owner}",
            f"- 所属部门：{department}",
            f"- 物料分类：{category}",
            f"【MDM】查询时间：{query_time}，编码：{eid}",
        ]
        return "\n".join(lines)

    def generate_dual_answer(self, entity_data: dict, chunks: list[dict], user_query: str) -> str:
        """生成双库联动回答"""
        status = entity_data.get("status", "未知")
        eid = entity_data.get("entity_id", "")
        etype = entity_data.get("entity_type", "")
        name = entity_data.get("name", "")
        query_time = entity_data.get("query_time", "")
        owner = entity_data.get("owner", "")

        # 结论
        status_map = {
            "冻结": f"{etype} {eid}（{name}）当前为【冻结】状态。根据物料状态管理规则，冻结状态下**不可发起新的采购申请**。",
            "量产": f"{etype} {eid}（{name}）当前为【量产】状态。该状态下可正常发起采购申请。",
            "开发中": f"{etype} {eid}（{name}）当前为【开发中】状态。该状态下仅可发起研发用途的采购申请，不可用于量产 BOM。",
            "报废": f"{etype} {eid}（{name}）当前为【报废】状态。该状态下不可发起任何采购申请，物料已永久停用。",
            "已发布": f"{etype} {eid}（{name}）当前为【已发布】状态。该状态满足上架基础条件。",
        }
        conclusion = status_map.get(status, f"{etype} {eid}（{name}）当前状态为【{status}】。")

        # 知识库规则
        rule_text = ""
        if chunks:
            best = chunks[0]
            source = best.get("source", "").replace(".md", "")
            section = best.get("section", "")
            content = best.get("content", "")
            relevant = self._extract_relevant_rule(content, status)
            rule_text = f"【知识库】依据规则：{relevant}\n来源：《{source}》{section}"

        # 下一步建议
        next_step = self._get_next_step(status)

        parts = [conclusion]
        parts.append(f"\n【MDM】查询时间：{query_time}，编码：{eid}")
        if owner:
            parts.append(f"负责工程师：{owner}")
        if rule_text:
            parts.append(f"\n{rule_text}")
        if next_step:
            parts.append(f"\n{next_step}")

        return "\n".join(parts)

    def generate_clarification(self, user_query: str, attempt: int) -> str:
        """生成澄清反问"""
        if attempt >= 2:
            return (
                "我可以帮您解决以下几类问题，您可以直接提问：\n\n"
                "1. 主数据规则咨询（如「XX字段怎么填」、「退回原因是XX，怎么修改」）\n"
                "2. 实体状态查询（如「物料编码12345现在什么状态」）\n"
                "3. 规则+数据联动（如「物料12345是冻结状态，能否采购？」）\n\n"
                "如问题比较复杂，建议联系数据 BP。"
            )
        return (
            "您的问题涉及到主数据规则查询还是某个具体编码的状态查询？\n\n"
            "- 如果是规则查询（如「字段怎么填」「流程是什么」），请补充您想了解的主数据类型\n"
            "- 如果是实体查询（如「某个物料/供应商的状态」），请提供编码或名称"
        )

    def _build_answer_from_chunk(self, chunk: dict, source: str, section: str) -> str:
        """从检索到的 chunk 构建格式化回答"""
        content = chunk.get("content", "")

        # 提取关键信息
        lines = content.strip().split("\n")
        summary_parts = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith(">"):
                clean = line.lstrip("- *").strip()
                if clean and len(clean) > 3:
                    summary_parts.append(clean)
                if len(summary_parts) >= 5:
                    break

        summary = "\n".join(f"- {p}" if not p.startswith("-") else p for p in summary_parts[:5])
        answer = f"{summary}\n\n【知识库】来源：《{source}》{section}"

        return answer

    def _extract_relevant_rule(self, content: str, status: str) -> str:
        """从 chunk 内容中提取与当前状态最相关的规则"""
        # 查找状态相关的规则描述
        lines = content.split("\n")
        relevant_lines = []
        capture = False
        status_map = {
            "冻结": "冻结",
            "量产": "量产",
            "开发中": "开发中",
            "报废": "报废",
            "已发布": "已发布",
        }
        target = status_map.get(status, status)

        for line in lines:
            if target in line:
                capture = True
            if capture and line.strip():
                relevant_lines.append(line.strip())
                if len(relevant_lines) >= 4:
                    break

        if relevant_lines:
            return " ".join(relevant_lines)
        return content[:200].strip()

    def _get_next_step(self, status: str) -> str:
        next_steps = {
            "冻结": "【下一步建议】如需使用该物料，需先提交《物料解冻申请表》并附整改完成的证明材料，经质量部门审核通过后由主数据管理员执行解冻操作。",
            "开发中": "【下一步建议】该物料完成 DVT/PVT 验证并通过 PDT 评审后，可申请转为量产状态。",
            "报废": "【下一步建议】该物料已永久停用，请寻找替代物料。如需查询替代建议，可联系负责工程师。",
            "已发布": "【下一步建议】确认销售区域和渠道后，可关联商品目录编码。如需上架新渠道，请提交 SKU 创建申请。",
        }
        return next_steps.get(status, "【下一步建议】如有疑问，请联系所属领域数据 BP 确认。")

    def _out_of_scope_or_no_result(self, user_query: str) -> str:
        """处理超出范围或无结果的情况"""
        # 检测是否为超出主数据范围的问题
        out_of_scope_keywords = ["ERP", "HR", "财务", "会计", "绩效", "薪资", "社保"]
        for kw in out_of_scope_keywords:
            if kw in user_query:
                return (
                    f"我是主数据 AI 助手，专注于主数据规则咨询和实体查询。\n"
                    f"「{kw}」相关问题超出了我的服务范围，建议联系对应部门或查阅相关制度文档。"
                )

        return (
            f"当前知识库中未找到与您问题相关的信息。\n"
            f"建议联系数据 BP 或主数据管理团队确认。\n"
            f"【知识库】未找到匹配的知识片段（知识库版本：KB_v1.0）"
        )
