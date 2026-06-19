"""
====================================
ABA智能助手 - 知识库模块
====================================

负责加载和管理ABA专业知识库
支持文档检索和RAG
"""

import os
from typing import List, Dict, Optional
from pathlib import Path
import re
import hashlib

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("警告: ChromaDB未安装，语义向量检索功能将受限")

try:
    from core.config import (
        EMBEDDING_API_KEY,
        EMBEDDING_BASE_URL,
        EMBEDDING_MODEL,
        EMBEDDING_MODE,
        RETRIEVAL_CANDIDATE_K,
        COLLECTION_NAME,
        COLLECTION_NAME_LOCAL,
    )
except ImportError:
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
    EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_MODE = "api" if EMBEDDING_API_KEY else "local"
    RETRIEVAL_CANDIDATE_K = 16
    COLLECTION_NAME = "aba_knowledge_semantic_v2"
    COLLECTION_NAME_LOCAL = "aba_knowledge_local_v1"


class KnowledgeBase:
    """知识库管理器"""
    
    def __init__(
        self,
        knowledge_path: str = "./knowledge_base",
        vector_db_path: str = "./data/chromadb",
        collection_name: str = None
    ):
        """
        初始化知识库

        Args:
            knowledge_path: 知识库文档路径
            vector_db_path: 向量数据库存储路径
            collection_name: Collection名称（默认按 embedding 模式自动选择，
                             api 模式用 COLLECTION_NAME，本地模式用 COLLECTION_NAME_LOCAL，
                             两者隔离避免向量维度冲突）
        """
        self.knowledge_path = Path(knowledge_path)
        self.vector_db_path = Path(vector_db_path)
        # embedding 模式："api"（远程）/"local"（本地 MiniLM）/"none"（不可用）
        self.embedding_mode = "none"
        self.embedding_client = None
        self._local_ef = None
        self.embedding_enabled = False
        if collection_name is None:
            collection_name = COLLECTION_NAME_LOCAL if EMBEDDING_MODE == "local" else COLLECTION_NAME
        self.collection_name = collection_name
        self.documents = []
        self.chunks = []
        self.vector_db = None
        self.collection = None

        # 确保目录存在
        self.vector_db_path.mkdir(parents=True, exist_ok=True)

        # 先确定 embedding 模式（本地模式需把 embedding_function 传给 collection），
        # 再初始化向量库。
        if CHROMADB_AVAILABLE:
            self._init_embedding_client()
            self._init_vector_db()

    def _init_vector_db(self):
        """初始化向量数据库"""
        try:
            self.vector_db = chromadb.PersistentClient(
                path=str(self.vector_db_path)
            )

            kwargs = {
                "name": self.collection_name,
                # 余弦空间，使 score=1/(1+distance) 落在可预期区间
                "metadata": {"description": "ABA专业知识库", "hnsw:space": "cosine"},
            }
            # 本地模式：把内置 embedding_function 绑到 collection 上，
            # 之后 add(documents=)/query(query_texts=) 由 chroma 自动向量化。
            if self.embedding_mode == "local" and self._local_ef is not None:
                kwargs["embedding_function"] = self._local_ef

            self.collection = self.vector_db.get_or_create_collection(**kwargs)
            print(f"✅ 向量数据库初始化成功，Collection: {self.collection_name}（{self.embedding_mode}）")

        except Exception as e:
            print(f"⚠️ 向量数据库初始化失败: {e}")
            self.vector_db = None

    def _init_embedding_client(self):
        """初始化语义检索的 embedding 后端。

        优先远程 API（配置了 key）；否则退回本地 MiniLM（无需 key，可离线）。
        """
        # 1) 远程 API embedding
        if EMBEDDING_API_KEY:
            try:
                from openai import OpenAI
                self.embedding_client = OpenAI(
                    api_key=EMBEDDING_API_KEY,
                    base_url=EMBEDDING_BASE_URL
                )
                self.embedding_enabled = True
                self.embedding_mode = "api"
                print(f"✅ 语义检索已启用（远程 API），Embedding模型: {EMBEDDING_MODEL}")
                return
            except Exception as e:
                print(f"⚠️ 远程 Embedding 客户端初始化失败，尝试本地: {e}")

        # 2) 本地 MiniLM（chromadb 内置，onnxruntime 驱动）
        try:
            from chromadb.utils import embedding_functions
            self._local_ef = embedding_functions.DefaultEmbeddingFunction()
            self.embedding_enabled = True
            self.embedding_mode = "local"
            print("✅ 语义检索已启用（本地 MiniLM，无需 API Key）")
        except Exception as e:
            print(f"⚠️ 本地 Embedding 初始化失败，语义检索不可用: {e}")
            self.embedding_enabled = False
            self.embedding_mode = "none"
    
    def load_documents(self) -> int:
        """
        加载知识库文档
        
        Returns:
            加载的文档数量
        """
        if not self.knowledge_path.exists():
            print(f"⚠️ 知识库路径不存在: {self.knowledge_path}")
            return 0
        
        self.documents = []
        
        # 支持的文件扩展名
        extensions = [".md", ".txt", ".pdf", ".docx"]
        
        # 遍历目录加载文档
        for ext in extensions:
            for file_path in self.knowledge_path.rglob(f"*{ext}"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    doc_info = {
                        "source": str(file_path.relative_to(self.knowledge_path)),
                        "content": content,
                        "title": file_path.stem,
                        "type": ext[1:]
                    }
                    
                    self.documents.append(doc_info)
                    print(f"✅ 加载文档: {doc_info['source']}")
                    
                except Exception as e:
                    print(f"⚠️ 加载文档失败 {file_path}: {e}")
        
        # 文档分块不依赖第三方库；向量索引在配置可用时增量创建。
        if self.documents:
            self._create_chunks()
            if self.vector_db and self.collection:
                self._create_embeddings()
        
        return len(self.documents)
    
    def _create_chunks(self):
        """将文档分割成小块"""
        if not self.documents:
            return
        
        self.chunks = []
        
        for doc in self.documents:
            # 按段落分割
            sections = doc["content"].split("\n\n")
            
            current_chunk = ""
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                
                # 如果当前块加上这个section太大，则保存当前块
                if len(current_chunk) + len(section) > 500:
                    if current_chunk:
                        self.chunks.append({
                            "content": current_chunk.strip(),
                            "source": doc["source"],
                            "title": doc["title"],
                            "doc_type": doc.get("type", "md")
                        })
                    current_chunk = section
                else:
                    if current_chunk:
                        current_chunk += "\n\n" + section
                    else:
                        current_chunk = section
            
            # 保存最后一个块
            if current_chunk:
                self.chunks.append({
                    "content": current_chunk.strip(),
                    "source": doc["source"],
                    "title": doc["title"],
                    "doc_type": doc.get("type", "md")
                })
        
        print(f"✅ 创建 {len(self.chunks)} 个文档块")
    
    def _create_embeddings(self):
        """创建向量嵌入并存储"""
        if not self.chunks or not self.collection:
            return

        if not self.embedding_enabled:
            print("⚠️ 语义检索未启用：缺少可用的 Embedding 配置")
            return

        existing_ids = set()
        try:
            existing = self.collection.get(include=[])
            existing_ids = set(existing.get("ids", []))
        except Exception as e:
            print(f"⚠️ 读取向量索引失败，将继续尝试增量创建: {e}")

        # 本地模式：交给 collection 自带的 embedding_function 批量向量化
        if self.embedding_mode == "local":
            new_ids, new_docs, new_meta = [], [], []
            for i, chunk in enumerate(self.chunks):
                chunk_id = self._chunk_id(chunk, i)
                chunk["id"] = chunk_id
                if chunk_id in existing_ids:
                    continue
                new_ids.append(chunk_id)
                new_docs.append(chunk["content"])
                new_meta.append({
                    "source": chunk["source"],
                    "title": chunk["title"],
                    "doc_type": chunk.get("doc_type", "md"),
                })
            added_count = 0
            BATCH = 64
            for start in range(0, len(new_ids), BATCH):
                try:
                    self.collection.add(
                        ids=new_ids[start:start + BATCH],
                        documents=new_docs[start:start + BATCH],
                        metadatas=new_meta[start:start + BATCH],
                    )
                    added_count += len(new_ids[start:start + BATCH])
                except Exception as e:
                    print(f"⚠️ 本地向量批量写入失败: {e}")
            print(f"✅ 语义向量索引准备完成（本地），新增 {added_count} 个文档块")
            return

        # 远程 API 模式：自己算 embedding 再写入
        added_count = 0
        for i, chunk in enumerate(self.chunks):
            chunk_id = self._chunk_id(chunk, i)
            chunk["id"] = chunk_id
            if chunk_id in existing_ids:
                continue

            embedding = self._embed_text(self._embedding_text(chunk))
            if not embedding:
                continue

            try:
                self.collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk["content"]],
                    metadatas=[{
                        "source": chunk["source"],
                        "title": chunk["title"],
                        "doc_type": chunk.get("doc_type", "md")
                    }]
                )
                added_count += 1
            except Exception as e:
                print(f"⚠️ 写入向量索引失败 {chunk_id}: {e}")

        print(f"✅ 语义向量索引准备完成，新增 {added_count} 个文档块")

    def _chunk_id(self, chunk: Dict, index: int) -> str:
        raw = f"{chunk.get('source','')}::{index}::{chunk.get('content','')}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def _embedding_text(self, chunk: Dict) -> str:
        return f"标题：{chunk.get('title', '')}\n来源：{chunk.get('source', '')}\n内容：{chunk.get('content', '')}"

    def _embed_text(self, text: str) -> Optional[List[float]]:
        if not self.embedding_client:
            return None

        try:
            response = self.embedding_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text[:8000]
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️ Embedding生成失败: {e}")
            return None
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        搜索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            相关文档列表
        """
        if not self.collection or not self.embedding_enabled:
            print("⚠️ 语义检索不可用：请检查 Embedding 配置")
            return []

        n_results = max(top_k, RETRIEVAL_CANDIDATE_K)

        try:
            if self.embedding_mode == "local":
                # 本地模式：collection 自带 embedding_function，直接传文本
                raw_results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"]
                )
            else:
                query_embedding = self._embed_text(query)
                if not query_embedding:
                    return []
                raw_results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"]
                )
        except Exception as e:
            print(f"⚠️ 语义检索失败: {e}")
            return []

        results = []
        documents = raw_results.get("documents", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0]
        distances = raw_results.get("distances", [[]])[0]

        for idx, content in enumerate(documents):
            metadata = metadatas[idx] if idx < len(metadatas) else {}
            distance = distances[idx] if idx < len(distances) else None
            score = 1 / (1 + distance) if isinstance(distance, (int, float)) else 0
            results.append({
                "content": content,
                "source": metadata.get("source", ""),
                "title": metadata.get("title", ""),
                "score": score,
                "distance": distance
            })

        return results[:n_results]

    def get_semantic_rerank_candidates(self, limit: int = 80) -> List[Dict]:
        """
        获取供大模型语义重排的候选片段。
        仅在 embedding 不可用时兜底使用，不做关键词匹配。
        """
        grouped = {}
        for i, chunk in enumerate(self.chunks):
            source = chunk.get("source", "")
            grouped.setdefault(source, []).append((i, chunk))

        if not grouped:
            return []

        per_source = max(1, limit // len(grouped))
        candidates = []
        for source in sorted(grouped):
            for i, chunk in grouped[source][:per_source]:
                candidates.append({
                    "content": chunk["content"],
                    "source": chunk["source"],
                    "title": chunk["title"],
                    "score": 0,
                    "candidate_index": i
                })
                if len(candidates) >= limit:
                    return candidates
        return candidates
    
    def get_document_count(self) -> int:
        """获取文档数量"""
        return len(self.documents)
    
    def get_chunk_count(self) -> int:
        """获取文档块数量"""
        return len(self.chunks)
    
    def format_context(self, search_results: List[Dict]) -> str:
        """
        格式化搜索结果为上下文
        
        Args:
            search_results: 搜索结果
            
        Returns:
            格式化的上下文字符串
        """
        if not search_results:
            return ""
        
        context = "\n\n## 相关知识库内容：\n\n"
        
        for i, result in enumerate(search_results, 1):
            context += f"**来源 {i}** [{result['title']}]\n"
            context += f"{result['content']}\n\n"
        
        context += "---\n"

        return context

    def get_recommended_documents(self, intervention_goals: str, top_k: int = 3) -> List[Dict]:
        """
        根据干预目标推荐相关文档

        Args:
            intervention_goals: 干预目标
            top_k: 返回数量

        Returns:
            推荐的文档列表（含标题和来源）
        """
        if not intervention_goals or not self.chunks:
            return []

        search_results = self.search(intervention_goals, top_k=max(top_k * 2, RETRIEVAL_CANDIDATE_K))

        if not search_results:
            return []

        doc_map = {}
        for result in search_results:
            source = result["source"]
            if source not in doc_map:
                doc_map[source] = {
                    "title": result["title"],
                    "source": source,
                    "score": result["score"],
                    "preview": result["content"][:150] + "..."
                }
            else:
                doc_map[source]["score"] += result["score"]

        sorted_docs = sorted(doc_map.values(), key=lambda x: x["score"], reverse=True)
        return sorted_docs[:top_k]

    def get_all_documents_info(self) -> List[Dict]:
        """
        获取所有文档的信息

        Returns:
            文档信息列表
        """
        return [
            {
                "title": doc["title"],
                "source": doc["source"],
                "type": doc.get("type", "md")
            }
            for doc in self.documents
        ]
