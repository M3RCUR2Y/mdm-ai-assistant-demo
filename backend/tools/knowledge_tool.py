import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.config import config


class KnowledgeTool:
    """知识库检索工具 — 基于 TF-IDF + 余弦相似度"""

    def __init__(self):
        self.chunks: list[dict] = []
        self.vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(1, 3))
        self.chunk_vectors = None
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        kb_dir = config.KB_DIR
        if not os.path.exists(kb_dir):
            return

        documents = []
        for fname in sorted(os.listdir(kb_dir)):
            if fname.endswith(".md"):
                fpath = os.path.join(kb_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                doc_chunks = self._chunk_document(content, fname)
                for ch in doc_chunks:
                    documents.append(ch["content"])
                    self.chunks.append(ch)

        if documents:
            self.chunk_vectors = self.vectorizer.fit_transform(documents)

    def _chunk_document(self, content: str, source: str) -> list[dict]:
        """按 ## 标题切分文档，保留层级元数据"""
        chunks = []
        sections = re.split(r"\n##\s+", content)

        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            lines = section.split("\n")
            title = lines[0].strip() if lines else ""
            body = "\n".join(lines)

            if i == 0:
                title = "概述"

            chunks.append({
                "content": body,
                "source": source,
                "section": title,
                "chunk_id": f"chunk_{source.replace('.md', '')}_{i:03d}",
            })

        return chunks

    def search(self, query: str) -> tuple[list[dict], float]:
        """
        检索知识库：TF-IDF 字符 n-gram 相似度 + 关键词直接匹配加权
        返回 (匹配chunks列表, 最高相似度)
        """
        if not self.chunks or self.chunk_vectors is None:
            return [], 0.0

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.chunk_vectors)[0]

        # 关键词加权：直接包含查询词的 chunk 获得额外权重
        keyword_boost = 0.3
        query_chars = set(query)
        for i, chunk in enumerate(self.chunks):
            content = chunk.get("content", "")
            match_chars = sum(1 for c in query_chars if c in content)
            boost = (match_chars / max(len(query_chars), 1)) * keyword_boost
            similarities[i] += boost

        top_k = min(config.KB_TOP_K, len(self.chunks))
        top_indices = similarities.argsort()[::-1][:top_k]

        results = []
        max_score = 0.0
        threshold = config.KB_SIMILARITY_THRESHOLD
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= threshold:
                results.append({**self.chunks[idx], "score": round(score, 3)})
                max_score = max(max_score, score)

        # 降低阈值兜底：如果没有结果但最高分 > 0，取最高分的结果
        if not results:
            best_idx = top_indices[0]
            best_score = float(similarities[best_idx])
            if best_score > 0.01:
                results.append({**self.chunks[best_idx], "score": round(best_score, 3)})
                max_score = best_score

        return results, max_score
