"""
跨用户相似案例检索

向量库位置：data/users/admin_vectors/（与主 app 的 vectors/ 完全隔离，
避免污染面向用户的 RAG）。

三个 collection：
- admin_children       孩子档案（按 children 表每行一份文档）
- admin_reports        历史专家/AI 报告（按 reports 表每行一份文档）
- admin_conversations  对话切片（按 conversation id 一行一份）

每个文档都带 user_id / username 元数据，检索时支持 exclude_user_id
过滤掉目标用户自己，避免"自己抄自己"。

嵌入模型：使用 ChromaDB 默认（all-MiniLM-L6-v2）。中文质量一般但够用，
未来可通过 chromadb embedding_function 参数替换为 BGE-zh。
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import data_access


CHILDREN_COLL = "admin_children"
REPORTS_COLL = "admin_reports"
CONVERSATIONS_COLL = "admin_conversations"
ALL_COLLECTIONS = [CHILDREN_COLL, REPORTS_COLL, CONVERSATIONS_COLL]


def _get_client(vectors_path: Path):
    """延迟 import，避免在没装 chromadb 的环境下整个模块炸掉。"""
    import chromadb

    vectors_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(vectors_path))


def _safe_meta(d: Dict) -> Dict:
    """ChromaDB 的 metadata 只接受 str/int/float/bool。把所有值转 str，None 跳过。"""
    out = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = json.dumps(v, ensure_ascii=False)
    return out


def _child_doc(child: Dict, username: str) -> Tuple[str, Dict]:
    parts = [
        f"姓名：{child.get('name', '')}",
        f"出生日期：{child.get('birth_date', '') or '未知'}",
        f"诊断：{child.get('diagnosis', '') or '未知'}",
        f"诊断日期：{child.get('diagnosis_date', '') or '未知'}",
        f"干预目标：{child.get('intervention_goals', '') or '未设置'}",
        f"备注：{child.get('notes', '') or ''}",
    ]
    text = "\n".join(parts)
    meta = _safe_meta({
        "type": "child",
        "user_id": child.get("user_id"),
        "username": username,
        "child_id": child.get("child_id"),
        "child_name": child.get("name"),
        "diagnosis": child.get("diagnosis"),
        "created_at": child.get("created_at"),
    })
    return text, meta


def _report_doc(report: Dict, username: str) -> Tuple[str, Dict]:
    parts = [
        f"标题：{report.get('title', '')}",
        f"类型：{report.get('report_type', '')}",
        f"周期：{report.get('period_start', '')} → {report.get('period_end', '')}",
        f"摘要：{report.get('summary', '') or ''}",
        "",
        report.get("content", "") or "",
    ]
    text = "\n".join(parts)
    meta = _safe_meta({
        "type": "report",
        "user_id": report.get("user_id"),
        "username": username,
        "child_id": report.get("child_id"),
        "report_id": report.get("report_id"),
        "report_type": report.get("report_type"),
        "title": report.get("title"),
        "period_start": report.get("period_start"),
        "period_end": report.get("period_end"),
    })
    return text, meta


def _conv_doc(conv: Dict, user_id: str, username: str) -> Tuple[str, Dict]:
    role = conv.get("role", "?")
    role_label = {"user": "家长", "assistant": "AI助手", "system": "系统"}.get(role, role)
    text = f"[{role_label}] {conv.get('content', '') or ''}"
    meta = _safe_meta({
        "type": "conversation",
        "user_id": user_id,
        "username": username,
        "role": role,
        "timestamp": conv.get("timestamp"),
        "conv_id": conv.get("id"),
    })
    return text, meta


def rebuild_index(db_path: Path, vectors_path: Path) -> Dict[str, int]:
    """
    重建三个 collection。先删后建，简单可靠。
    返回每个 collection 的最终条数。
    """
    client = _get_client(vectors_path)

    # 删旧
    for name in ALL_COLLECTIONS:
        try:
            client.delete_collection(name)
        except Exception:
            pass

    # 新建
    children_coll = client.create_collection(name=CHILDREN_COLL)
    reports_coll = client.create_collection(name=REPORTS_COLL)
    conv_coll = client.create_collection(name=CONVERSATIONS_COLL)

    users = data_access.list_users(db_path)

    for u in users:
        uid = u["user_id"]
        username = u["username"]

        # children
        children = data_access.get_children(db_path, uid)
        if children:
            ids, docs, metas = [], [], []
            for c in children:
                cid = c.get("child_id") or f"row_{len(ids)}"
                doc_id = f"{uid}::{cid}::{c.get('updated_at') or c.get('created_at') or len(ids)}"
                text, meta = _child_doc(c, username)
                ids.append(doc_id)
                docs.append(text)
                metas.append(meta)
            if ids:
                children_coll.add(ids=ids, documents=docs, metadatas=metas)

        # reports
        reports = data_access.get_reports(db_path, uid)
        if reports:
            ids, docs, metas = [], [], []
            for r in reports:
                rid = r.get("report_id") or f"row_{len(ids)}"
                doc_id = f"{uid}::report::{rid}"
                text, meta = _report_doc(r, username)
                ids.append(doc_id)
                docs.append(text)
                metas.append(meta)
            if ids:
                reports_coll.add(ids=ids, documents=docs, metadatas=metas)

        # conversations
        convs = data_access.get_conversations(db_path, uid)
        if convs:
            ids, docs, metas = [], [], []
            for c in convs:
                cid = c.get("id")
                doc_id = f"{uid}::conv::{cid}"
                text, meta = _conv_doc(c, uid, username)
                ids.append(doc_id)
                docs.append(text)
                metas.append(meta)
            if ids:
                conv_coll.add(ids=ids, documents=docs, metadatas=metas)

    return {
        CHILDREN_COLL: children_coll.count(),
        REPORTS_COLL: reports_coll.count(),
        CONVERSATIONS_COLL: conv_coll.count(),
    }


def collection_stats(vectors_path: Path) -> Dict[str, int]:
    """读当前索引规模，UI 显示用。索引不存在时返回 0。"""
    try:
        client = _get_client(vectors_path)
    except Exception:
        return {name: 0 for name in ALL_COLLECTIONS}
    result = {}
    for name in ALL_COLLECTIONS:
        try:
            result[name] = client.get_collection(name).count()
        except Exception:
            result[name] = 0
    return result


def find_similar(
    vectors_path: Path,
    query_text: str,
    collections: List[str],
    top_k: int = 3,
    exclude_user_id: Optional[str] = None,
) -> List[Dict]:
    """
    在指定的 collection 中检索，按相似度倒序返回。

    返回元素格式：
        {
            "collection": "admin_children",
            "document": "...",
            "metadata": {...},
            "distance": 0.32,
        }
    """
    client = _get_client(vectors_path)
    results = []
    for name in collections:
        try:
            coll = client.get_collection(name)
        except Exception:
            continue
        if coll.count() == 0:
            continue

        where = None
        if exclude_user_id:
            # chromadb where 不支持 !=，所以用 $ne
            where = {"user_id": {"$ne": exclude_user_id}}

        # top_k 取多一些再过滤，防止过滤后不够
        n = top_k * 3 if exclude_user_id else top_k
        n = min(n, coll.count())
        if n == 0:
            continue

        try:
            res = coll.query(query_texts=[query_text], n_results=n, where=where)
        except Exception:
            # 某些 chromadb 版本对 $ne 处理不一致，退回到 python 端过滤
            res = coll.query(query_texts=[query_text], n_results=n)

        for doc, meta, dist in zip(
            res.get("documents", [[]])[0],
            res.get("metadatas", [[]])[0],
            res.get("distances", [[]])[0],
        ):
            if exclude_user_id and meta and meta.get("user_id") == exclude_user_id:
                continue
            results.append({
                "collection": name,
                "document": doc,
                "metadata": meta or {},
                "distance": dist,
            })

    results.sort(key=lambda x: x["distance"])
    return results[: top_k * len(collections)]


def build_query_from_bundle(bundle: Dict) -> str:
    """
    从一个用户的 bundle 拼出"用来检索相似案例"的查询文本。
    优先级：最近的孩子档案 > user_info > 最近一次对话主题。
    """
    children = bundle.get("children") or []
    if children:
        latest = children[-1]
        parts = [
            f"诊断：{latest.get('diagnosis', '')}",
            f"干预目标：{latest.get('intervention_goals', '')}",
            f"备注：{latest.get('notes', '')}",
        ]
        return "\n".join(p for p in parts if p.strip().split("：", 1)[-1])

    user_info = (bundle.get("user") or {}).get("user_info") or {}
    if user_info:
        return "\n".join(
            f"{k}：{v}" for k, v in user_info.items() if v
        )

    convs = bundle.get("conversations") or []
    if convs:
        return convs[-1].get("content", "")[:500]

    return bundle.get("user", {}).get("username", "")
