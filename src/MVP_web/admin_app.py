"""
ABA 智能助手 - 专家后台

独立 Streamlit 应用，默认端口 8502。
启动：
    export ABA_ADMIN_PASSWORD='密码'
    streamlit run admin_app.py --server.port 8502
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from admin import data_access, exporter, similarity, draft
from admin.llm import AdminLLM, LLMUnavailable

DB_PATH = Path(os.environ.get(
    "ABA_MEMORY_DB",
    Path(__file__).parent / "data" / "users" / "memory.db",
))
EXPORTS_ROOT = Path(os.environ.get(
    "ABA_EXPORTS_ROOT",
    Path(__file__).parent / "data" / "users" / "exports",
))
VECTORS_PATH = Path(os.environ.get(
    "ABA_ADMIN_VECTORS",
    Path(__file__).parent / "data" / "users" / "admin_vectors",
))
DRAFTS_ROOT = Path(os.environ.get(
    "ABA_DRAFTS_ROOT",
    Path(__file__).parent / "data" / "users" / "drafts",
))
ADMIN_PASSWORD = os.environ.get("ABA_ADMIN_PASSWORD", "")

CHINA_TZ = timezone(timedelta(hours=8))


# ====================================
# 登录
# ====================================
def require_login():
    if not ADMIN_PASSWORD:
        st.error("未设置环境变量 `ABA_ADMIN_PASSWORD`。请在服务器上执行：`export ABA_ADMIN_PASSWORD='密码'`")
        st.stop()
    if st.session_state.get("authed"):
        return
    st.title("🔐 ABA 专家后台")
    pwd = st.text_input("管理员密码", type="password")
    if st.button("登录"):
        if pwd == ADMIN_PASSWORD:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()


# ====================================
# 用户列表
# ====================================
def page_user_list():
    st.subheader("👥 用户列表")
    if not DB_PATH.exists():
        st.error(f"找不到数据库：{DB_PATH}")
        return

    users = data_access.list_users(DB_PATH)
    if not users:
        st.info("暂无用户。")
        return

    coach_summary = data_access.get_coach_summary(DB_PATH)

    rows = []
    for u in users:
        uid = u["user_id"]
        info = u.get("user_info") or {}
        coach = coach_summary.get(uid, {})

        rows.append({
            "用户名": u["username"],
            "孩子姓名": info.get("child_name", "-"),
            "ABA对话": u["conversation_count"],
            "ABA报告": u["report_count"],
            "心情记录": coach.get("mood_count", 0),
            "个人记录": coach.get("records_count", 0),
            "成长项目": coach.get("projects_count", 0),
            "最近登录": (u["last_login"] or "")[:16],
            "user_id": uid,
        })

    st.dataframe(
        [{k: v for k, v in r.items() if k != "user_id"} for r in rows],
        use_container_width=True,
        hide_index=True,
        column_config={
            "最近登录": st.column_config.TextColumn("最近登录", width="medium"),
        },
    )

    options = {f"{u['username']}  ({u['user_id'][:8]}…)": u["user_id"] for u in users}
    label = st.selectbox("选择用户查看详情：", list(options.keys()))
    if st.button("打开详情 →", type="primary"):
        st.session_state["selected_user_id"] = options[label]
        st.session_state["page"] = "user_detail"
        st.rerun()


# ====================================
# 用户详情
# ====================================
def page_user_detail():
    user_id = st.session_state.get("selected_user_id")
    if not user_id:
        st.info("请先在「用户列表」选一个用户。")
        return

    user = data_access.get_user(DB_PATH, user_id)
    if not user:
        st.error("用户不存在或已被删除。")
        return

    bundle = data_access.collect_user_bundle(DB_PATH, user_id)

    st.subheader(f"📂 {user['username']} — 用户数据")
    st.caption(f"user_id: `{user_id}`")

    coach = bundle.get("coach") or {}
    mood_log = coach.get("mood_log", [])
    records = coach.get("personal_records", [])
    projects = coach.get("growth_projects", [])

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("ABA对话", len(bundle["conversations"]))
    c2.metric("孩子档案", len(bundle["children"]))
    c3.metric("历史报告", len(bundle["reports"]))
    c4.metric("心情记录", len(mood_log))
    c5.metric("个人记录", len(records))
    c6.metric("成长项目", len(projects))

    st.divider()

    # ── 删除用户（危险操作，需确认） ──
    with st.expander("🗑️ 删除此用户及全部数据", expanded=False):
        st.warning(
            "⚠️ **此操作不可撤销！** 将删除该用户的全部数据，包括：\n\n"
            "- 用户账户及密码\n"
            "- 所有对话记录\n"
            "- 孩子档案、进展记录、报告\n"
            "- 训练任务数据\n"
            "- 人生教练数据（成长项目、情绪日志、反思日记等）\n"
            "- 上传文件及向量索引"
        )

        confirm_text = st.text_input(
            "请输入要删除的用户名以确认：",
            placeholder=f"输入「{user['username']}」确认删除",
            key="del_confirm"
        )

        col_del1, col_del2 = st.columns([1, 3])
        if col_del1.button("🗑️ 确认删除", type="primary", use_container_width=True):
            if confirm_text == user["username"]:
                result = data_access.delete_user_by_admin(DB_PATH, user_id)
                if result["success"]:
                    st.success(result["message"])

                    # 显示详细清理清单
                    with st.expander("📋 清理明细"):
                        for label, count in result["deleted"].items():
                            if count > 0 or label in ("用户账户",):
                                st.write(f"- {label}：{count} 条")
                        st.write(f"- 文件目录：{'已清理' if result.get('dir_removed') else '无或已不存在'}")

                    # 清除选中状态
                    st.session_state.pop("selected_user_id", None)
                    st.info("用户已删除。3 秒后返回用户列表…")
                    import time; time.sleep(3)
                    st.session_state["page"] = "user_list"
                    st.rerun()
                else:
                    st.error(result["message"])
            elif confirm_text:
                st.error("用户名不匹配，未执行删除。")
            else:
                st.error("请先输入用户名确认。")

    # ── 一级导航：selectbox（完全扁平，无任何嵌套容器） ──
    section = st.selectbox("选择查看区域",
                           ["📋 ABA 数据", "🧘 人生教练", "📤 导出", "🤖 AI 草稿"],
                           key="detail_section")

    # ========== ABA 数据 ==========
    if section == "📋 ABA 数据":
        aba_view = st.radio("ABA 子导航", ["孩子档案", "对话记录", "任务", "进展记录", "历史报告"],
                            horizontal=True, key="aba_view")
        st.markdown("---")
        if aba_view == "孩子档案":
            if bundle["children"]:
                st.dataframe(bundle["children"], use_container_width=True, hide_index=True)
            else:
                st.info("无孩子档案。")
        elif aba_view == "对话记录":
            if bundle["conversations"]:
                for c in bundle["conversations"][-40:]:
                    role = c.get("role", "?")
                    ts = c.get("timestamp", "")
                    role_label = "👤 家长" if role == "user" else "🤖 AI"
                    content = c.get("content", "")
                    st.markdown(f"**{role_label}** · {ts}")
                    if len(content) > 500:
                        st.text(content[:500] + f"\n... (共{len(content)}字，已截断)")
                    else:
                        st.text(content)
                    st.markdown("---")
                st.caption(f"显示最近 40 条 / 共 {len(bundle['conversations'])} 条")
            else:
                st.info("无对话记录。")
        elif aba_view == "任务":
            if bundle["tasks"]:
                st.dataframe(bundle["tasks"], use_container_width=True, hide_index=True)
            else:
                st.info("无任务。")
        elif aba_view == "进展记录":
            if bundle["progress_logs"]:
                st.dataframe(bundle["progress_logs"], use_container_width=True, hide_index=True)
            else:
                st.info("无进展记录。")
        elif aba_view == "历史报告":
            if bundle["reports"]:
                for idx, r in enumerate(bundle["reports"]):
                    st.markdown(f"#### 📄 {r.get('title', '报告')} — {r.get('created_at', '')}")
                    st.caption(f"类型: {r.get('report_type')} | 周期: {r.get('period_start')} → {r.get('period_end')}")
                    summary = r.get("summary", "")
                    if summary:
                        st.markdown(summary)
                        st.markdown("---")
                    st.markdown(r.get("content", ""))
                    if idx < len(bundle["reports"]) - 1:
                        st.divider()
            else:
                st.info("无历史报告。")

    # ========== 人生教练 ==========
    elif section == "🧘 人生教练":
        if not coach:
            st.info("该用户尚未使用人生教练模块。")
        else:
            coach_view = st.radio("教练子导航", ["📊 概览", "💭 心情记录", "📝 个人记录", "🌱 成长项目", "💬 教练对话"],
                                  horizontal=True, key="coach_view")
            st.markdown("---")
            if coach_view == "📊 概览":
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("心情记录数", len(mood_log))
                    st.metric("个人记录数", len(records))
                    st.metric("日记条目", len(coach.get("journal_entries", [])))
                with col_b:
                    st.metric("成长项目数", len(projects))
                    st.metric("对话消息", len(coach.get("coach_messages", [])))
                    st.metric("收藏文章", len(coach.get("kb_favorites", [])))
                if mood_log:
                    scores = [m.get("score", 4) for m in mood_log if m.get("score")]
                    if scores:
                        st.metric("平均心情分", f"{sum(scores)/len(scores):.1f} / 4")
                    labels = {}
                    for m in mood_log:
                        lbl = m.get("label", "未知")
                        labels[lbl] = labels.get(lbl, 0) + 1
                    if labels:
                        st.caption("心情分布: " + " | ".join(f"{k} ×{v}" for k, v in sorted(labels.items(), key=lambda x: -x[1])))

            elif coach_view == "💭 心情记录":
                if not mood_log:
                    st.info("暂无心情记录。")
                else:
                    st.dataframe(
                        [{"时间": m.get("time", ""), "心情": f"{m.get('emoji', '')} {m.get('label', '')}",
                          "评分": m.get("score", ""), "强度": m.get("intensity", ""),
                          "触发": (m.get("trigger", "")[:30] + "..." if len(m.get("trigger", "")) > 30 else m.get("trigger", "")),
                          "身体感受": m.get("body_feeling", "")[:20],
                          "备注": m.get("note", "")[:30]} for m in mood_log],
                        use_container_width=True, hide_index=True)

            elif coach_view == "📝 个人记录":
                if not records:
                    st.info("暂无个人记录。")
                else:
                    st.dataframe(
                        [{"时间": r.get("time", ""), "类型": f"{r.get('type_icon', '')} {r.get('type', '')}",
                          "标题": r.get("title", ""),
                          "内容": (r.get("content", "")[:80] + "..." if len(r.get("content", "")) > 80 else r.get("content", ""))}
                         for r in records],
                        use_container_width=True, hide_index=True)

            elif coach_view == "🌱 成长项目":
                if not projects:
                    st.info("暂无成长项目。")
                else:
                    tasks_done = coach.get("_tasks_done_root", [])
                    emotion_done = coach.get("_emotion_done_root", [])
                    stage = coach.get("growth_stage", 0)
                    st.caption(f"成长阶段: {stage} | 已完成任务: {len(tasks_done)} | 情绪练习: {len(emotion_done)}")
                    for pidx, proj in enumerate(projects):
                        issue_type = proj.get("issue_type", "")
                        issue = proj.get("issue", "未命名项目")
                        done = len(proj.get("tasks_done", []))
                        stages = len(proj.get("stages", []))
                        total_tasks = stages
                        progress = f"{done}/{total_tasks}" if total_tasks > 0 else f"{done} 项"
                        st.markdown(f"### {'🏷️' if issue_type else '🌱'} {issue[:40]}")
                        c1p, c2p, c3p = st.columns(3)
                        c1p.metric("状态", proj.get("status", ""))
                        c2p.metric("进度", progress)
                        c3p.metric("创建时间", (proj.get("created_at") or "")[:10])
                        if done > 0:
                            st.markdown("**已完成任务：**")
                            for task in tasks_done:
                                st.markdown(f"  ✅ {task.get('text', task.get('id', ''))}")
                        if pidx < len(projects) - 1:
                            st.divider()

            elif coach_view == "💬 教练对话":
                msgs = coach.get("coach_messages", [])
                if not msgs:
                    st.info("暂无教练对话。")
                else:
                    for m in msgs:
                        role = "👤 用户" if m.get("role") == "user" else "🤖 教练"
                        st.markdown(f"**{role}** · {m.get('time','')}")
                        st.text(m.get("content","")[:500])
                        st.markdown("---")
                    st.caption(f"共 {len(msgs)} 条对话")

    # ========== 导出 ==========
    elif section == "📤 导出":
        st.caption("导出 user_data.md / user_data.json 到 data/users/exports/")
        if st.button("立即导出 →", type="primary"):
            md_path, json_path = exporter.export_user(bundle, EXPORTS_ROOT)
            st.success(f"已导出到 `{md_path.parent}`")
            st.session_state["last_export"] = {"md": str(md_path), "json": str(json_path)}
        last = st.session_state.get("last_export")
        if last:
            md_path = Path(last["md"])
            json_path = Path(last["json"])
            col1, col2 = st.columns(2)
            col1.download_button("⬇️ user_data.md", data=md_path.read_bytes(), file_name=md_path.name, mime="text/markdown")
            col2.download_button("⬇️ user_data.json", data=json_path.read_bytes(), file_name=json_path.name, mime="application/json")
            st.markdown("#### 预览")
            st.markdown(md_path.read_text(encoding="utf-8")[:5000])

    # ========== AI 草稿 ==========
    elif section == "🤖 AI 草稿":
        st.caption("调用 LLM 生成专家视角报告草稿。")
        stats = similarity.collection_stats(VECTORS_PATH)
        total = sum(stats.values())
        use_rag = st.checkbox("使用跨用户相似案例（RAG）", value=(total > 0), disabled=(total == 0))
        if use_rag:
            coll_options = {
                "孩子档案": similarity.CHILDREN_COLL,
                "历史报告": similarity.REPORTS_COLL,
                "对话记录": similarity.CONVERSATIONS_COLL,
            }
            chosen_labels = st.multiselect("检索子集", list(coll_options.keys()),
                                           default=[k for k, v in coll_options.items() if stats.get(v, 0) > 0])
            top_k = st.number_input("Top K", 1, 10, 3)
            chosen_collections = [coll_options[l] for l in chosen_labels]
        else:
            chosen_collections = []
            top_k = 3
        if st.button("生成草稿 →", type="primary"):
            try:
                llm = AdminLLM()
                if not llm.available:
                    st.error(f"LLM 未配置：provider={llm.provider}")
                else:
                    similar_ctx = []
                    if use_rag and chosen_collections:
                        query_text = similarity.build_query_from_bundle(bundle)
                        similar_ctx = similarity.find_similar(VECTORS_PATH, query_text, chosen_collections,
                                                               top_k=top_k, exclude_user_id=user_id)
                    with st.spinner("生成中..."):
                        draft_md = draft.generate_draft(bundle, similar_ctx, llm)
                    draft_path = draft.save_draft(bundle, draft_md, DRAFTS_ROOT, similar_ctx)
                    st.session_state["last_draft"] = {"path": str(draft_path), "md": draft_md, "similar": similar_ctx}
                    st.success(f"草稿已保存：`{draft_path.parent}`")
            except LLMUnavailable as e:
                st.error(f"LLM 错误：{e}")
            except Exception as e:
                st.exception(e)
        last_draft = st.session_state.get("last_draft")
        if last_draft:
            if last_draft.get("similar"):
                st.markdown(f"#### 🔎 参考案例（{len(last_draft['similar'])} 条）")
                for i, item in enumerate(last_draft["similar"], 1):
                    meta = item.get("metadata") or {}
                    st.markdown(f"**{i}** `{item['collection']}` | `{meta.get('username')}` | dist=`{item['distance']:.3f}`")
                    st.code(item.get("document", "")[:500], language="text")
            st.download_button("⬇️ draft.md", data=last_draft["md"].encode("utf-8"), file_name="draft.md", mime="text/markdown")
            st.markdown("---")
            st.markdown(last_draft["md"])


# ====================================
# 索引管理
# ====================================
def page_index_management():
    st.subheader("📚 索引管理（跨用户相似案例）")
    st.caption("向量库：data/users/admin_vectors/，与主 app RAG 隔离。")

    stats = similarity.collection_stats(VECTORS_PATH)
    c1, c2, c3 = st.columns(3)
    c1.metric("孩子档案", stats.get(similarity.CHILDREN_COLL, 0))
    c2.metric("历史报告", stats.get(similarity.REPORTS_COLL, 0))
    c3.metric("对话记录", stats.get(similarity.CONVERSATIONS_COLL, 0))

    if st.button("🔄 重建索引", type="primary"):
        try:
            with st.spinner("重建中..."):
                result = similarity.rebuild_index(DB_PATH, VECTORS_PATH)
            st.success(
                f"children={result[similarity.CHILDREN_COLL]}  "
                f"reports={result[similarity.REPORTS_COLL]}  "
                f"conversations={result[similarity.CONVERSATIONS_COLL]}"
            )
        except Exception as e:
            st.exception(e)


# ====================================
# 全局统计
# ====================================
def page_overview():
    st.subheader("📊 全局统计")
    if not DB_PATH.exists():
        st.info("数据库不存在。")
        return

    users = data_access.list_users(DB_PATH)
    coach_summary = data_access.get_coach_summary(DB_PATH)

    total_aba_conv = sum(u["conversation_count"] for u in users)
    total_reports = sum(u["report_count"] for u in users)
    total_moods = sum(c.get("mood_count", 0) for c in coach_summary.values())
    total_projects = sum(c.get("projects_count", 0) for c in coach_summary.values())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("总用户数", len(users))
    c2.metric("ABA对话", total_aba_conv)
    c3.metric("历史报告", total_reports)
    c4.metric("心情记录", total_moods)
    c5.metric("成长项目", total_projects)

    st.divider()
    st.caption(f"数据路径: `{DB_PATH}`")


# ====================================
# 主入口
# ====================================
PAGES = {
    "📊 全局统计": "overview",
    "👥 用户列表": "user_list",
    "📂 用户详情": "user_detail",
    "📚 索引管理": "index_mgmt",
}


def main():
    st.set_page_config(page_title="ABA 专家后台", page_icon="🩺", layout="wide")
    require_login()

    st.sidebar.title("🩺 ABA 专家后台")
    st.sidebar.caption(f"DB: `{DB_PATH}`")

    current = st.session_state.get("page", "overview")
    page_label = st.sidebar.radio(
        "导航",
        list(PAGES.keys()),
        index=list(PAGES.values()).index(current) if current in PAGES.values() else 0,
    )
    st.session_state["page"] = PAGES[page_label]

    try:
        _llm = AdminLLM()
        if _llm.available:
            st.sidebar.success(f"LLM: {_llm.provider}")
        else:
            st.sidebar.warning(f"LLM: {_llm.provider} 未配置")
    except Exception:
        st.sidebar.warning("LLM 未配置")

    if st.sidebar.button("登出"):
        st.session_state.clear()
        st.rerun()

    page = st.session_state["page"]
    if page == "overview":
        page_overview()
    elif page == "user_list":
        page_user_list()
    elif page == "user_detail":
        page_user_detail()
    elif page == "index_mgmt":
        page_index_management()

    st.sidebar.divider()
    now = datetime.now(CHINA_TZ)
    st.sidebar.caption(f"服务器时间: {now.strftime('%Y-%m-%d %H:%M')} (CST)")


if __name__ == "__main__":
    main()
