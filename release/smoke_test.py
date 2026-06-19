"""
冒烟自检脚本
============
打包前/改动后跑一遍，校验「数据与模块是否自洽」，无需启动 Streamlit。
覆盖：核心模块可导入、知识库文件齐全、图片卡类别可渲染、课程技能引用的
图片卡类别全部真实存在（防止断链）、向量检索后端可用、AI 问答已接知识库。

用法：
    python3 release/smoke_test.py

退出码：0 = 全部通过（warning 不计失败）；1 = 有硬性失败。
"""

import os
import re
import sys
import traceback

_THIS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_THIS)
_MVP = os.path.join(_ROOT, "src", "MVP_web")
_KB = os.path.join(_ROOT, "docs", "知识库")
sys.path.insert(0, _MVP)

_failures = []
_warnings = []


def check(name, fn):
    try:
        fn()
        print(f"  ✓ {name}")
    except AssertionError as e:
        _failures.append(f"{name}: {e}")
        print(f"  ✗ {name}: {e}")
    except Exception as e:
        _failures.append(f"{name}: {e}")
        print(f"  ✗ {name}: {e}")
        traceback.print_exc()


def warn(msg):
    _warnings.append(msg)
    print(f"  ⚠ {msg}")


def test_imports():
    # 重构后为 package 结构，按包路径导入
    from core import config, safety  # noqa
    from utils import curriculum, assessment, intervention, task_generator, charts  # noqa
    from training import flashcards, training_data  # noqa
    from ai import knowledge_base, agent  # noqa


def test_knowledge_base_files():
    assert os.path.isdir(_KB), "知识库目录不存在"
    mds = [f for f in os.listdir(_KB) if f.endswith(".md")]
    assert len(mds) >= 6, f"知识库 md 文件不足，仅 {len(mds)} 个"


def test_flashcards_render():
    from training import flashcards as fc
    cats = fc.get_categories()
    assert cats, "未发现任何图片卡类别"
    # 抽查每个类别首张可渲染
    for c in cats:
        n = fc.get_page_count(c)
        assert n > 0, f"类别「{c}」没有卡片"
        assert fc.render_page_as_png_bytes(c, 0) is not None, f"类别「{c}」首张渲染失败"
    print(f"      （{len(cats)} 个类别均可渲染）")


def test_curriculum_integrity():
    from utils import curriculum as cur
    ids = [s["skill_id"] for s in cur.SKILLS]
    assert len(ids) == len(set(ids)), "存在重复 skill_id"
    # next 指针必须指向真实技能或 None
    idset = set(ids)
    for s in cur.SKILLS:
        nxt = s.get("next")
        assert nxt is None or nxt in idset, f"技能「{s['name']}」的 next={nxt} 不存在"


def test_no_broken_flashcard_refs():
    from utils import curriculum as cur
    from training import flashcards as fc
    cats = set(fc.get_categories())
    broken = [
        (s["name"], s["flashcard_category"])
        for s in cur.SKILLS
        if s.get("flashcard_category") and s["flashcard_category"] not in cats
    ]
    assert not broken, f"课程引用了不存在的图片卡类别：{broken}"


def test_embedding_backend_available():
    """向量检索后端必须可用（远程 API 或本地 MiniLM），否则 AI 问答用不上书。"""
    from ai.knowledge_base import KnowledgeBase
    from core.config import KNOWLEDGE_BASE_PATH, VECTOR_DB_PATH
    kb = KnowledgeBase(knowledge_path=KNOWLEDGE_BASE_PATH, vector_db_path=VECTOR_DB_PATH)
    assert kb.embedding_enabled, "embedding 后端不可用（远程 key 和本地 onnxruntime 都没就绪）"
    try:
        count = kb.collection.count()
    except Exception:
        count = 0
    if count <= 0:
        warn("向量库为空——请先运行 python3 src/tools/ingest_kb.py 建索引，否则问答检索不到书的内容")
    else:
        print(f"      （向量库条目数 {count}，模式 {kb.embedding_mode}）")


def test_agent_wired_to_kb():
    """守护回归：app 必须把知识库传给 ABAAgent，否则 RAG 检索是死代码。"""
    src = os.path.join(_MVP, "app_prototype.py")
    with open(src, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"ABAAgent\((.*?)\)", text, re.DOTALL)
    assert m, "未找到 ABAAgent(...) 调用"
    assert "knowledge_base" in m.group(1), \
        "ABAAgent 创建时未传 knowledge_base —— 知识库未接入问答（RAG 失效）"


def main():
    print("ABA 智能助手 — 冒烟自检")
    print("-" * 40)
    check("核心模块可导入", test_imports)
    check("知识库文件齐全", test_knowledge_base_files)
    check("图片卡类别可渲染", test_flashcards_render)
    check("课程数据自洽", test_curriculum_integrity)
    check("无断链图片卡引用", test_no_broken_flashcard_refs)
    check("向量检索后端可用", test_embedding_backend_available)
    check("AI问答已接知识库", test_agent_wired_to_kb)
    print("-" * 40)
    if _warnings:
        print(f"⚠ {len(_warnings)} 项提醒")
    if _failures:
        print(f"❌ {len(_failures)} 项失败")
        sys.exit(1)
    print("✅ 全部通过")


if __name__ == "__main__":
    main()
