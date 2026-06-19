"""
====================================
ABA智能助手 - 统一主应用
====================================

包含：
- AI助手问答
- 孩子档案管理
- 任务清单
- 进展记录
- 报告中心
"""

import streamlit as st
import time
from datetime import datetime
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import (
    APP_TITLE, APP_SUBTITLE, DEFAULT_USER,
    SYSTEM_PROMPT, EMERGENCY_PROMPT, DEFAULT_MODEL, AI_MODELS,
    USER_DATA_PATH, MEMORY_FILE, KNOWLEDGE_BASE_PATH, VECTOR_DB_PATH
)
from ai.knowledge_base import KnowledgeBase
from ai.agent import ABAAgent
from core.safety import SafetyChecker
from core.session_memory import memory_system
from core.deep_memory_extended import ChildProfileManager
from report_generator import ReportGenerator, ProgressChart
from utils.ui_styles import apply_custom_styles
from utils.charts import (
    create_category_pie_chart,
    create_progress_line_chart,
    create_concern_bar_chart,
    create_activity_heatmap,
    create_category_comparison_chart
)
from ai.ai_report_generator import SmartReportGenerator
from utils.task_generator import TaskGenerator
import training.training_data as td
import training.flashcards as fc
import utils.curriculum as cur
import utils.intervention as iv
import utils.assessment as asmt

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded"
)

DEFAULT_USER_INFO = {
    "child_name": "",
    "child_age": "",
    "diagnosis": "",
    "intervention_goals": ""
}

def get_child_manager() -> ChildProfileManager:
    if "child_manager" not in st.session_state:
        st.session_state.child_manager = ChildProfileManager(USER_DATA_PATH)
    return st.session_state.child_manager


# ── 登录持久化（cookie）─────────────────────────────────────
# 登录态原本只存 st.session_state（内存、按 websocket 会话）。手机锁屏/切后台导致
# websocket 断开重连后会新建会话、状态清空 → 被动登出。这里把「用户名+签名 token」
# 写进浏览器 cookie，加载时校验后免密恢复会话，做到「保持登录直到手动退出」。
# token 复用人生教练的 HMAC 方案（COACH_SSO_SECRET），不引入新的密钥。
_LOGIN_COOKIE = "aba_auth"
_COOKIE_DAYS = 365


def get_cookie_manager():
    """返回单例 CookieManager（必须全局唯一 key，否则组件重复报错）。"""
    import extra_streamlit_components as stx
    if "_cookie_mgr" not in st.session_state:
        st.session_state._cookie_mgr = stx.CookieManager(key="aba_cookie_mgr")
    return st.session_state._cookie_mgr


def set_login_cookie(username: str):
    """登录成功后写 cookie：值为 'username|token'，有效期 _COOKIE_DAYS 天。"""
    try:
        from coach.coach_engine import coach_sso_token
        from datetime import datetime, timedelta
        token = coach_sso_token(username)
        if not token:
            return  # 未配置 COACH_SSO_SECRET 时不持久化，回退到仅会话内登录
        get_cookie_manager().set(
            _LOGIN_COOKIE, f"{username}|{token}",
            expires_at=datetime.now() + timedelta(days=_COOKIE_DAYS),
            key="set_login_cookie",
        )
    except Exception:
        pass


def clear_login_cookie():
    """手动退出时删除 cookie。用「写入一个立即过期的空值」来删除，比 delete() 更可靠
    （写入路径已验证有效；delete() 有时不执行）。"""
    try:
        from datetime import datetime, timedelta
        cm = get_cookie_manager()
        cm.set(_LOGIN_COOKIE, "", expires_at=datetime.now() - timedelta(days=1),
               key="clear_login_cookie")
        cm.delete(_LOGIN_COOKIE, key="del_login_cookie")  # 双保险
    except Exception:
        pass


def restore_login_from_cookie():
    """加载时若未登录，则校验 cookie 并免密恢复会话。"""
    if st.session_state.get("logged_in", False):
        return
    try:
        import sqlite3
        from coach.coach_engine import verify_coach_sso_token
        raw = get_cookie_manager().get(_LOGIN_COOKIE)
        if not raw or "|" not in raw:
            return
        username, token = raw.split("|", 1)
        if not verify_coach_sso_token(username, token):
            return
        conn = sqlite3.connect(str(memory_system.db_path))
        cur = conn.cursor()
        cur.execute("SELECT user_id, username FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return
        memory_system.current_user_id = row[0]
        memory_system.current_username = row[1]
        st.session_state.logged_in = True
        st.session_state.user_id = row[0]
        st.session_state.username = row[1]
        st.session_state.conversation_loaded = False
        saved = memory_system.get_user_info()
        st.session_state.user_info = (saved.get("user_info") if saved else None) or DEFAULT_USER_INFO.copy()
    except Exception:
        pass

def strip_thinking(content: str) -> str:
    """移除 AI 模型生成的 XML 工具调用和思考标记"""
    tool_tags = [
        'think', 'thinking', 'reasoning', 'thought',
        'search', 'search_web', 'search_web_query',
        'tool_call', 'tool', 'function_call',
        'query', 'action', 'minimax:tool_call',
        'web_search', 'mcp_call',
    ]
    for tag in tool_tags:
        content = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', content, flags=re.DOTALL)
    content = re.sub(r'<\w+[^>]*/>', '', content)
    return content.strip()

def format_ai_response(content: str):
    """格式化AI回复内容，优化排版"""
    if not content:
        return

    content = strip_thinking(content)
    if not content:
        return

    content = content.replace("\n\n", "\n")

    if content.startswith("# "):
        st.markdown(content)
        return
    elif "```" in content:
        st.markdown(content)
        return

    lines = content.split("\n")
    has_content = False

    for line in lines:
        line = line.strip()
        if not line:
            continue
        has_content = True
        if line.startswith("**") and line.endswith("**") and line.count("**") == 2:
            st.markdown(f"**{line[2:-2]}**")
        elif line.startswith("-"):
            st.markdown(f"- {line[1:].strip()}")
        elif line[0].isdigit() and "." in line[:3]:
            st.markdown(line)
        else:
            st.markdown(line)

    if not has_content:
        st.markdown(content)

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("## 🌟 ABA智能助手")
        st.markdown("---")

        if not st.session_state.get("logged_in", False):
            st.warning("⚠️ **隐私保护提示**：请勿在聊天中输入真实姓名、学校、住址、身份证号等敏感个人信息。\n\n所有数据按账户隔离，仅您本人可查看。")
            st.markdown("---")
            tab1, tab2 = st.tabs(["登录", "注册"])

            with tab1:
                login_username = st.text_input("用户名", key="login_user")
                login_password = st.text_input("密码", type="password", key="login_pass")
                if st.button("登录", use_container_width=True):
                    success, msg = memory_system.login(login_username, login_password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.user_id = memory_system.current_user_id
                        st.session_state.conversation_loaded = False
                        memory_system._ensure_quota_row()
                        memory_system.update_storage_used()
                        saved_profile = memory_system.get_user_info()
                        if saved_profile and saved_profile.get('user_info'):
                            st.session_state.user_info = saved_profile['user_info']
                        else:
                            st.session_state.user_info = DEFAULT_USER_INFO.copy()
                        # 记录用户名 + 触发 main() 在正常渲染流程里写持久化 cookie
                        st.session_state.username = login_username
                        st.session_state["_cookie_synced"] = False
                        st.success(f"✅ 登录成功！")
                        st.rerun()
                    else:
                        st.error(msg)

            with tab2:
                reg_username = st.text_input("用户名", key="reg_user")
                reg_password = st.text_input("密码", type="password", key="reg_pass")
                reg_password2 = st.text_input("确认密码", type="password", key="reg_pass2")
                if st.button("注册", use_container_width=True):
                    if reg_password != reg_password2:
                        st.error("两次密码不一致")
                    else:
                        success, msg = memory_system.register(reg_username, reg_password)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.user_id = memory_system.current_user_id
                            st.session_state.conversation_loaded = False
                            memory_system._ensure_quota_row()
                            memory_system.update_storage_used()
                            st.session_state.user_info = DEFAULT_USER_INFO.copy()
                            st.session_state.username = reg_username
                            st.session_state["_cookie_synced"] = False
                            st.success("✅ 注册成功！")
                            st.rerun()
                        else:
                            st.error(msg)

            st.markdown("---")
        else:
            st.success(f"✅ 已登录: {memory_system.current_username}")

            user_info = st.session_state.get("user_info", DEFAULT_USER_INFO)

            st.markdown("---")

            if st.button("🚪 退出登录", use_container_width=True):
                # 删 cookie 交给 main() 在正常渲染流程里做（避免 rerun 打断），并跳过本次恢复
                st.session_state["_force_logout"] = True
                st.session_state.pop("username", None)
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.conversation_loaded = False
                st.session_state.current_view = "chat"
                st.session_state.messages = []
                memory_system.current_user_id = None
                memory_system.current_username = None
                st.rerun()

        st.markdown("---")
        st.markdown("### 🤖 AI引擎")

        available_models = {}
        for model_id, model_config in AI_MODELS.items():
            api_key = os.getenv(model_config.get("api_key_env", ""))
            if api_key:
                available_models[model_id] = f"{model_config['name']} ✅"

        if not available_models:
            st.warning("未配置任何AI引擎")
        else:
            model_options = list(available_models.keys())
            model_labels = [available_models[m] for m in model_options]

            current_model = st.session_state.get("current_ai_model", DEFAULT_MODEL)
            if current_model not in model_options:
                current_model = model_options[0]

            selected = st.selectbox(
                "选择AI引擎",
                options=model_options,
                format_func=lambda x: available_models[x],
                index=model_options.index(current_model),
                key="ai_model_selector"
            )
            st.session_state.current_ai_model = selected

        st.markdown("---")
        st.markdown("### 📱 功能导航")

        if st.button("💬 AI助手", use_container_width=True, type="primary"):
            st.session_state.current_view = "chat"
            st.rerun()

        if st.session_state.get("logged_in", False):
            st.caption("── 建档 ──")
            if st.button("👶 孩子档案", use_container_width=True):
                st.session_state.current_view = "profile"
                st.rerun()
            if st.button("📋 评估", use_container_width=True):
                st.session_state.current_view = "assessment"
                st.rerun()

            st.caption("── 每日训练 ──")
            if st.button("✅ 任务清单", use_container_width=True):
                st.session_state.current_view = "tasks"
                st.rerun()
            if st.button("🎯 训练记录", use_container_width=True):
                st.session_state.current_view = "training"
                st.rerun()
            if st.button("🃏 图片卡片", use_container_width=True):
                st.session_state.current_view = "flashcards"
                st.rerun()

            st.caption("── 数据与报告 ──")
            if st.button("📊 进展记录", use_container_width=True):
                st.session_state.current_view = "progress"
                st.rerun()
            if st.button("📈 数据看板", use_container_width=True):
                st.session_state.current_view = "dashboard"
                st.rerun()
            if st.button("📝 报告中心", use_container_width=True):
                st.session_state.current_view = "reports"
                st.rerun()

        # 人生教练入口（登录后可见）
        if st.session_state.get("logged_in", False):
            st.markdown("---")
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #5B8C5A, #81B29A);
                border-radius: 12px;
                padding: 1rem;
                text-align: center;
                margin: 0.5rem 0;
                box-shadow: 0 2px 10px rgba(91, 140, 90, 0.2);
            ">
                <div style="font-size: 1.1rem; font-weight: 600; color: white; margin-bottom: 0.3rem;">🌿 人生教练</div>
                <div style="font-size: 0.75rem; color: rgba(255,255,255,0.85);">AI 陪伴你成长 · 情绪支持 · 个人成长</div>
            </div>
            """, unsafe_allow_html=True)
            # 直接做成顶层文档里的链接：点一下整个标签页跳到人生教练（独立应用），
            # 不再嵌 iframe。链接在主页面 DOM 里，无沙箱限制，默认同标签导航(_self)。
            import os as _os
            from urllib.parse import quote as _quote
            from coach.coach_engine import coach_sso_token as _sso
            _uname = memory_system.current_username or ""
            _base = _os.getenv("LIFE_COACH_URL", "http://localhost:8503").rstrip("/")
            _tok = _sso(_uname) or ""
            _coach_url = f"{_base}?user={_quote(_uname)}&token={_tok}"
            st.markdown(
                f'''<a href="{_coach_url}" target="_self" style="
                    display:block; text-align:center; text-decoration:none;
                    background:linear-gradient(135deg,#5B8C5A,#81B29A); color:white;
                    padding:0.55rem 1rem; border-radius:8px; font-weight:600; margin-top:0.3rem;
                ">🌱 进入人生教练</a>''',
                unsafe_allow_html=True,
            )

        # 存储使用量（登录后显示）
        if st.session_state.get("logged_in") and st.session_state.get("user_id"):
            st.markdown("---")
            st.markdown("### 💾 存储使用")
            memory_system.current_user_id = st.session_state.user_id
            usage = memory_system.get_storage_usage()
            if usage["total_bytes"] > 0:
                pct = usage["percent"]
                st.progress(min(1.0, pct / 100.0))
                parts = []
                for key, label in [
                    ("memory_db", "数据库"),
                    ("chroma", "向量索引"),
                    ("coach_data", "教练数据"),
                    ("cache", "缓存"),
                    ("files", "文件"),
                ]:
                    mb = usage["breakdown"].get(key, 0) / 1024 / 1024
                    if mb > 0.1:
                        parts.append(label + ": %.1fMB" % mb)
                st.caption(" / ".join(parts) if parts else "无数据")
                if pct > 80:
                    st.warning("存储已用 %sMB / %sMB，请及时清理" % (usage["total_mb"], usage["limit_mb"]))
                else:
                    st.caption("已用 %sMB / %sMB" % (usage["total_mb"], usage["limit_mb"]))
                if parts:
                    cols = st.columns(2)
                    with cols[0]:
                        if st.button("🧹 清理缓存", use_container_width=True, key="btn_clean_cache"):
                            freed = memory_system.cleanup_cache()
                            memory_system.update_storage_used()
                            st.rerun()
                    with cols[1]:
                        if st.button("📦 清理旧对话", use_container_width=True, key="btn_clean_old_conv"):
                            result = memory_system.cleanup_old_conversations()
                            memory_system.update_storage_used()
                            st.rerun()
                if usage["breakdown"].get("coach_data", 0) > 30 * 1024 * 1024:
                    if st.button("🌿 精简教练数据", use_container_width=True, key="btn_trim_coach"):
                        result = memory_system.trim_coach_messages()
                        memory_system.update_storage_used()
                        st.rerun()

            with st.expander("📋 数据管理"):
                if st.button("📥 导出我的数据", use_container_width=True, key="btn_export"):
                    export_data = memory_system.export_user_data()
                    if "error" not in export_data:
                        import json
                        st.download_button(
                            "下载 JSON",
                            data=json.dumps(export_data, ensure_ascii=False, indent=2),
                            file_name="aba_coach_data.json",
                            mime="application/json",
                            key="btn_download_json"
                        )
                st.caption("支持导出 ABA + 人生教练完整数据")
                if st.button("🔒 隐私与合规", use_container_width=True, key="btn_gdpr"):
                    st.session_state.current_view = "gdpr"
                    st.rerun()

                under_protection = memory_system.is_child_under_protection()
                if under_protection:
                    st.warning("已开启儿童数据保护模式（14岁以下）")

        st.markdown("---")
        st.markdown("### ℹ️ 关于")
        st.caption("ABA智能助手 v2.0")

    user_context = {
        "child_name": st.session_state.get("user_info", {}).get("child_name", ""),
        "child_age": st.session_state.get("user_info", {}).get("child_age", ""),
        "diagnosis": st.session_state.get("user_info", {}).get("diagnosis", ""),
        "intervention_goals": st.session_state.get("user_info", {}).get("intervention_goals", "")
    }

    return user_context

def initialize_session_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_info" not in st.session_state:
        st.session_state.user_info = DEFAULT_USER_INFO.copy()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_loaded" not in st.session_state:
        st.session_state.conversation_loaded = False
    if "current_view" not in st.session_state:
        st.session_state.current_view = "chat"
    if "safety_checker" not in st.session_state:
        st.session_state.safety_checker = SafetyChecker()

    if not st.session_state.conversation_loaded and st.session_state.logged_in and st.session_state.get("user_id"):
        memory_system.current_user_id = st.session_state.user_id
        try:
            history = memory_system.get_conversation_history(limit=50)
            if history:
                st.session_state.messages = history
        except Exception:
            pass
        st.session_state.conversation_loaded = True

    if st.session_state.user_id:
        memory_system.current_user_id = st.session_state.user_id

    # 知识库（向量检索）只构建一次并缓存：app 仅『打开』已建好的索引，
    # 不在此重建（重建用 src/tools/ingest_kb.py）。这样 AI 问答才能真正引用书的内容。
    if "knowledge_base" not in st.session_state:
        try:
            st.session_state.knowledge_base = KnowledgeBase(
                knowledge_path=KNOWLEDGE_BASE_PATH,
                vector_db_path=VECTOR_DB_PATH,
            )
        except Exception:
            st.session_state.knowledge_base = None

    current_model = st.session_state.get("current_ai_model", DEFAULT_MODEL)
    agent_model = st.session_state.get("agent_model", None)

    if "agent" not in st.session_state or agent_model != current_model:
        st.session_state.agent_model = current_model
        try:
            st.session_state.agent = ABAAgent(
                knowledge_base=st.session_state.get("knowledge_base"),
                model_name=current_model,
            )
        except Exception as e:
            st.session_state.agent = None

def render_landing_page():
    """未登录时的首页：丰富的欢迎页 + 功能介绍 + 登录引导（手机上不再一片空白）。"""
    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#4A90D9,#6FB1E3);color:#fff;
             border-radius:18px;padding:2rem 1.5rem;text-align:center;margin-bottom:1.2rem;
             box-shadow:0 6px 20px rgba(74,144,217,0.35);">
            <div style="font-size:3rem;line-height:1;">🌟</div>
            <h1 style="color:#fff;margin:0.6rem 0 0.4rem;font-size:1.7rem;">ABA 智能助手</h1>
            <p style="color:#EAF3FC;margin:0;font-size:1.02rem;line-height:1.6;">
                为需要特别支持的孩子家长，提供专业、温暖的<br>AI 干预指导 · 训练记录 · 家长陪伴
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 登录引导：手机上侧边栏默认收起，明确告诉用户点左上角按钮
    st.markdown(
        """
        <div style="background:#FFF8E6;border:1px solid #FFD666;border-radius:12px;
             padding:0.9rem 1.1rem;margin-bottom:1.3rem;font-size:1rem;color:#7A5A00;">
            👉 <b>开始使用</b>：点左上角的 <b>»</b> 按钮打开侧边栏，登录或注册账号。
            电脑端在左侧即可直接登录。
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 这个助手能帮你")
    features = [
        ("🧠", "ABA 干预指导", "解答孩子行为疑惑，给出可落地的家庭干预建议"),
        ("📊", "训练记录与进展", "按技能记录每次试次，自动算正确率、掌握度，生成报告"),
        ("🃏", "图片卡片教学", "上千张分类教学卡片，备课和练习随取随用"),
        ("🌿", "家长人生教练", "照顾孩子的同时，也照顾好你自己的情绪与成长"),
    ]
    cols = st.columns(2)  # 手机端会自动堆叠成单列
    for i, (icon, title, desc) in enumerate(features):
        with cols[i % 2]:
            st.markdown(
                f"""
                <div style="background:#fff;border:1px solid #E6ECF2;border-radius:14px;
                     padding:1.1rem 1.1rem;margin-bottom:0.9rem;min-height:118px;
                     box-shadow:0 2px 8px rgba(0,0,0,0.05);">
                    <div style="font-size:1.7rem;">{icon}</div>
                    <div style="font-weight:700;color:#2D3436;margin:0.35rem 0 0.25rem;
                         font-size:1.05rem;">{title}</div>
                    <div style="color:#6B7680;font-size:0.92rem;line-height:1.55;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.caption("🔒 所有数据按账户隔离，仅你本人可见。请勿在聊天中输入真实姓名、住址等敏感信息。")


# 快捷问题池：每次从中随机抽 QUICK_N 个展示，让提示更多样
QUICK_QUESTION_POOL = [
    ("自伤行为", "孩子撞头/咬手怎么办？"),
    ("走失问题", "孩子走失冲到马路上怎么办？"),
    ("拒食问题", "孩子不肯吃饭怎么办？"),
    ("发脾气", "孩子发脾气怎么处理？"),
    ("睡眠问题", "孩子不肯睡觉怎么办？"),
    ("社交沟通", "怎么教孩子说话/沟通？"),
    ("攻击行为", "孩子打人/攻击他人怎么办？"),
    ("入学问题", "孩子要入学了怎么准备？"),
    ("正强化", "什么是正强化？怎么用？"),
    ("如厕训练", "怎么帮孩子做如厕训练？"),
    ("刻板行为", "孩子重复同一个动作怎么办？"),
    ("注意力差", "孩子坐不住、注意力差怎么办？"),
    ("情绪表达", "怎么教孩子认识和表达情绪？"),
    ("不听指令", "孩子不听指令怎么办？"),
    ("分离焦虑", "孩子粘人、分离焦虑怎么办？"),
    ("感统问题", "孩子怕声音/抗拒触碰怎么办？"),
]
QUICK_N = 6  # 每次随机展示的按钮数量


def _refresh_quick_questions():
    """随机抽一批快捷问题存入 session_state（每轮问答后换一批）。"""
    import random
    st.session_state.quick_sample = random.sample(
        QUICK_QUESTION_POOL, k=min(QUICK_N, len(QUICK_QUESTION_POOL))
    )


def render_chat_view():
    """渲染AI聊天界面"""
    st.markdown(f'<p class="main-title">{APP_TITLE}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="subtitle">{APP_SUBTITLE}</p>', unsafe_allow_html=True)

    if not st.session_state.get("logged_in"):
        render_landing_page()
        return

    if not st.session_state.messages:
        welcome_msg = """
        👋 **欢迎使用ABA智能助手！**

        我是一位专业、温暖的AI助手，专为需要特别支持的孩子家长提供支持。

        **我可以帮助你：**
        • 了解ABA基础知识
        • 解答关于孩子行为的疑惑
        • 提供实用的家庭干预建议
        • 分享日常干预的技巧

        **请先在左侧填写孩子的情况**，这样我可以给你更个性化的建议！

        **快捷问题示例：**
        - 什么是正强化？
        - 孩子发脾气怎么办？
        - 怎么教孩子说话？
        - 孩子2岁还不会说话，正常吗？
        """
        st.info(welcome_msg)
    else:
        col_clear1, col_clear2 = st.columns([1, 5])
        with col_clear1:
            if st.button("🗑️ 清空对话", use_container_width=True, key="clear_all", type="secondary",
                         help="删除所有对话记录"):
                st.session_state.messages = []
                if st.session_state.get("logged_in"):
                    try:
                        memory_system.delete_all_conversations()
                    except Exception:
                        pass
                st.rerun()

    for i, message in enumerate(st.session_state.messages):
        msg_key = f"msg_{i}"
        if message["role"] == "user":
            with st.chat_message("user"):
                col_msg, col_del = st.columns([20, 1])
                with col_msg:
                    st.markdown(message["content"])
                with col_del:
                    if st.button("✕", key=f"del_user_{i}", help="删除此问题"):
                        user_msg = st.session_state.messages.pop(i)
                        asst_msg = None
                        if i < len(st.session_state.messages) and st.session_state.messages[i]["role"] == "assistant":
                            asst_msg = st.session_state.messages.pop(i)
                        if st.session_state.get("logged_in"):
                            try:
                                if asst_msg and asst_msg.get("id"):
                                    memory_system.delete_conversation(asst_msg["id"])
                                if user_msg.get("id"):
                                    memory_system.delete_conversation(user_msg["id"])
                            except Exception:
                                pass
                        st.rerun()
        else:
            with st.chat_message("assistant"):
                col_msg, col_del = st.columns([20, 1])
                with col_msg:
                    if message.get("safety_level", 0) >= 3:
                        if message["safety_level"] >= 4:
                            st.warning(EMERGENCY_PROMPT)
                        else:
                            st.info("⚠️ **温馨提示**：以下情况建议咨询专业人员")
                    format_ai_response(message["content"])
                with col_del:
                    if st.button("✕", key=f"del_asst_{i}", help="删除此回复"):
                        asst_msg = st.session_state.messages.pop(i)
                        user_msg = None
                        if i > 0 and st.session_state.messages[i-1]["role"] == "user":
                            user_msg = st.session_state.messages.pop(i-1)
                        if st.session_state.get("logged_in"):
                            try:
                                if asst_msg.get("id"):
                                    memory_system.delete_conversation(asst_msg["id"])
                                if user_msg and user_msg.get("id"):
                                    memory_system.delete_conversation(user_msg["id"])
                            except Exception:
                                pass
                        st.rerun()

    st.markdown("---")

    # ── 快捷问题：常驻显示，每轮随机一批，点击直接提问 ──
    if "quick_sample" not in st.session_state:
        _refresh_quick_questions()
    st.markdown("""
    <style>
    /* 快捷问题按钮：与侧边栏按钮同款实心蓝 + 白字，亮色/暗色模式都清晰可见 */
    [class*="st-key-quick_"] button {
        background-color: #4A90D9 !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        width: 100% !important;
    }
    [class*="st-key-quick_"] button:hover {
        background-color: #3A7BC8 !important;
        box-shadow: 0 4px 12px rgba(74,144,217,0.4) !important;
    }
    /* 强制按钮内文字为白色，避免暗色模式下被主题改成深色看不清 */
    [class*="st-key-quick_"] button,
    [class*="st-key-quick_"] button p,
    [class*="st-key-quick_"] button span,
    [class*="st-key-quick_"] button div {
        color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("💡 **常见问题（点一下直接问）**")
    quick_cols = st.columns(3)
    for i, (label, question) in enumerate(st.session_state.quick_sample):
        with quick_cols[i % 3]:
            if st.button(label, key=f"quick_{label}", use_container_width=True,
                         help=question):
                st.session_state._pending_q = question
                st.rerun()

    # 输入框输入，或快捷按钮带入的待处理问题，走同一条回答生成路径
    typed_input = st.chat_input("输入你的问题...")
    user_input = typed_input or st.session_state.pop("_pending_q", None)

    if user_input:
        _refresh_quick_questions()  # 换一批快捷问题，下轮显示不同的
        user_msg_id = None
        if st.session_state.get("logged_in"):
            try:
                user_msg_id = memory_system.save_conversation(role="user", content=user_input)
            except Exception:
                pass

        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
            "id": user_msg_id
        })

        with st.chat_message("user"):
            st.markdown(user_input)

        safety_result = st.session_state.safety_checker.check(user_input)

        with st.chat_message("assistant"):
            with st.spinner("🤔 思考中..."):
                try:
                    user_context = {
                        "child_name": "",
                        "child_age": "",
                        "diagnosis": "",
                        "intervention_goals": ""
                    }

                    if st.session_state.logged_in:
                        user_id = memory_system.current_user_id
                        manager = get_child_manager()
                        children = manager.get_children(user_id)
                        if children:
                            child = children[0]
                            user_context["child_name"] = child.get("name", "")
                            user_context["child_age"] = child.get("birth_date", "")[:10] if child.get("birth_date") else ""
                            user_context["diagnosis"] = child.get("diagnosis", "")
                            user_context["intervention_goals"] = child.get("intervention_goals", "")

                    if st.session_state.logged_in and st.session_state.agent:
                        rag_context = memory_system.get_context_for_rag(user_input)
                        user_context["rag_context"] = rag_context

                    if safety_result["level"] >= 4:
                        response = EMERGENCY_PROMPT
                        st.warning("🚨 检测到紧急信号，已提供紧急帮助信息")
                    else:
                        response = st.session_state.agent.generate_response(
                            user_input=user_input,
                            context=user_context,
                            safety_level=safety_result["level"]
                        )

                        if safety_result["level"] >= 2:
                            st.info("⚠️ **温馨提示**：如果情况持续或加重，建议咨询专业医生或BCBA。")

                    response = strip_thinking(response)

                    asst_msg_id = None
                    if st.session_state.logged_in:
                        try:
                            asst_msg_id = memory_system.save_conversation(
                                role="assistant",
                                content=response,
                                metadata={"safety_level": safety_result["level"]}
                            )
                        except Exception:
                            pass

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "safety_level": safety_result["level"],
                        "timestamp": datetime.now().isoformat(),
                        "id": asst_msg_id
                    })

                    format_ai_response(response)

                except Exception as e:
                    st.error(f"抱歉，发生了错误：{str(e)}")
                    response = "抱歉，我现在遇到了一些问题，请稍后再试。"
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "timestamp": datetime.now().isoformat()
                    })
                    format_ai_response(response)

def render_child_profile_page():
    """孩子档案管理页面"""
    st.markdown('<h2 class="page-title">👶 孩子档案管理</h2>', unsafe_allow_html=True)

    manager = get_child_manager()
    user_id = memory_system.current_user_id

    tab1, tab2 = st.tabs(["📋 档案列表", "➕ 添加档案"])

    with tab1:
        children = manager.get_children(user_id)

        if not children:
            st.info("暂无孩子档案，请添加")
        else:
            for child in children:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### 👤 {child['name']}")
                        st.markdown(f"**年龄**: {child.get('birth_date', '未填写')}")
                    with col2:
                        pass

                    with st.expander("查看详情"):
                        st.markdown(f"**诊断**: {child.get('diagnosis', '未填写')}")
                        st.markdown(f"**诊断时间**: {child.get('diagnosis_date', '未填写')}")
                        st.markdown(f"**干预目标**: {child.get('intervention_goals', '未填写')}")
                        st.markdown(f"**备注**: {child.get('notes', '无')}")
                        st.markdown(f"**创建时间**: {child.get('created_at', '未知')[:10] if child.get('created_at') else '未知'}")

                    st.markdown("---")

                    col_btn = st.columns([1, 1, 1, 1])
                    with col_btn[0]:
                        if st.button(f"✏️ 编辑", key=f"edit_{child['child_id']}"):
                            st.session_state[f"editing_child_{child['child_id']}"] = True
                    with col_btn[1]:
                        if st.button(f"✅ 任务", key=f"tasks_{child['child_id']}"):
                            st.session_state.current_view = "tasks"
                            st.session_state.selected_child_id = child['child_id']
                            st.rerun()
                    with col_btn[2]:
                        if st.button(f"📊 进展", key=f"progress_{child['child_id']}"):
                            st.session_state.current_view = "progress"
                            st.session_state.selected_child_id = child['child_id']
                            st.rerun()
                    with col_btn[3]:
                        if st.button(f"🗑️ 删除", key=f"delete_{child['child_id']}", type="primary"):
                            success, msg = manager.delete_child(child['child_id'], user_id)
                            if success:
                                st.success("✅ 档案已删除")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                    st.markdown("---")

    with tab2:
        with st.form("add_child_form"):
            name = st.text_input("孩子姓名 *", placeholder="请输入姓名")
            birth_date = st.date_input("出生日期", value=None)
            diagnosis = st.selectbox("诊断情况", ["", "自闭症", "发育迟缓", "感统失调", "语言发育迟缓", "其他"])
            diagnosis_date = st.date_input("诊断时间", value=None)
            intervention_goals = st.text_area("干预目标", placeholder="请描述当前的干预目标...")
            notes = st.text_area("备注", placeholder="其他补充信息...")

            if st.form_submit_button("➕ 添加档案", use_container_width=True):
                if name:
                    birth_date_str = birth_date.isoformat() if birth_date else None
                    diagnosis_date_str = diagnosis_date.isoformat() if diagnosis_date else None
                    success, msg, child_id = manager.add_child(
                        user_id=user_id,
                        name=name,
                        birth_date=birth_date_str,
                        diagnosis=diagnosis,
                        diagnosis_date=diagnosis_date_str,
                        intervention_goals=intervention_goals,
                        notes=notes
                    )
                    if success:
                        st.success("✅ 档案添加成功！")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.warning("请填写孩子姓名")

def _child_age_years(child_obj: dict, default: int = 4) -> int:
    """从档案推算孩子年龄（岁）。档案存的是 birth_date，没有现成的 age 字段。"""
    if not child_obj:
        return default
    # 兼容可能存在的直接年龄字段
    for key in ("age", "child_age"):
        v = child_obj.get(key)
        if v:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    bd = child_obj.get("birth_date")
    if bd:
        try:
            from datetime import date
            b = date.fromisoformat(str(bd)[:10])
            t = date.today()
            years = t.year - b.year - ((t.month, t.day) < (b.month, b.day))
            if 0 <= years <= 18:
                return years
        except Exception:
            pass
    return default


def _add_curriculum_tasks(manager, user_id, child_id, skills):
    """将课程技能列表批量加入任务清单，跳过重名的"""
    added = 0
    existing_tasks = manager.get_tasks(child_id, user_id, status=None)
    existing_names = {t["task_name"] for t in existing_tasks}
    for skill in skills:
        task_name = skill["name"]
        if task_name in existing_names:
            continue
        success, _, _ = manager.add_task(
            child_id=child_id,
            user_id=user_id,
            task_name=task_name,
            task_description=skill.get("description", ""),
            category=skill.get("domain", "认知训练"),
            is_auto_generated=True,
        )
        if success:
            added += 1
            existing_names.add(task_name)
    return added


def render_task_list_page():
    """任务清单页面 - 课程驱动版"""
    st.markdown('<h2 class="page-title">✅ 任务清单</h2>', unsafe_allow_html=True)

    manager = get_child_manager()
    user_id = memory_system.current_user_id

    children = manager.get_children(user_id)
    if not children:
        st.info("📝 请先在「孩子档案」中添加孩子信息")
        return

    child_options = {c["child_id"]: c["name"] for c in children}
    col_sel, col_btn = st.columns([2, 1])
    with col_sel:
        selected_child_id = st.selectbox(
            "👶 选择孩子",
            options=list(child_options.keys()),
            format_func=lambda x: child_options[x],
            key="task_child_select"
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        child_obj = next((c for c in children if c["child_id"] == selected_child_id), None)
        if st.button("✨ 自动生成训练任务", use_container_width=True, type="primary",
                     help="根据孩子年龄和训练记录，从ABA课程中自动选取合适的任务"):
            age = _child_age_years(child_obj)
            # 已有任务的技能名，用于去重
            existing = [t["task_name"] for t in manager.get_tasks(selected_child_id, user_id, status=None)]
            # 同时分析训练记录，找出已掌握的技能→推进下一技能
            sessions = td.get_sessions(user_id, child_id=selected_child_id, limit=200)
            mastered_skills, next_skills = [], []
            skill_history: dict = {}
            for s in sessions:
                if s.get("skill_id") and s.get("finished") and s["total"] > 0:
                    sid = s["skill_id"]
                    skill_history.setdefault(sid, []).append(s["percentage"])
            for sid, pcts in skill_history.items():
                last3 = pcts[-3:]
                if len(last3) >= 3 and all(p >= 80 for p in last3):
                    mastered_skills.append(sid)
                    nxt = cur.get_next_skill(sid)
                    if nxt:
                        next_skills.append(nxt)

            # 基础推荐：按年龄+领域优先级，覆盖所有9个领域
            starter = cur.get_starter_skills(age, existing, max_per_domain=1, max_total=9)
            # 合并：已掌握技能的"下一技能"优先，再补各领域起点，去重
            all_skills = {s["skill_id"]: s for s in next_skills}
            for s in starter:
                if s["skill_id"] not in all_skills:
                    all_skills[s["skill_id"]] = s
            to_add = list(all_skills.values())[:9]

            added = _add_curriculum_tasks(manager, user_id, selected_child_id, to_add)
            if added:
                st.success(f"✅ 已生成 {added} 个训练任务！")
            else:
                st.info("当前任务已是最新，无需重复生成")
            st.rerun()

    st.markdown("---")

    tab_pending, tab_done, tab_add = st.tabs(["🎯 当前任务", "✅ 已完成", "➕ 手动添加"])

    # ── Tab 1: 当前任务 ──────────────────────────────────────
    with tab_pending:
        # 报告中心借用 tasks 表存历史报告（category=报告），需从训练任务列表中排除，
        # 否则每生成一份报告就会冒出一条假任务。
        pending_tasks = [
            t for t in manager.get_tasks(selected_child_id, user_id, status="pending")
            if t.get("category") != "报告"
        ]

        if not pending_tasks:
            st.info("暂无进行中的任务。点击上方「自动生成训练任务」开始。")
        else:
            for task in pending_tasks:
                skill_info = next(
                    (s for s in cur.SKILLS if s["name"] == task["task_name"]), None
                )
                # 双层完成状态
                done_today = td.trained_today(user_id, selected_child_id, task["task_name"])
                mst = td.mastery_status(user_id, selected_child_id, task["task_name"])

                with st.container():
                    col_info, col_actions = st.columns([3, 2])
                    with col_info:
                        domain_tag = f"`{skill_info['domain']}`" if skill_info else f"`{task.get('category','')}`"
                        # 标题行：今日完成打勾
                        title_suffix = "  ✅ 今日已训练" if done_today else ""
                        st.markdown(f"**{task['task_name']}** {domain_tag}{title_suffix}")

                        desc = (skill_info["description"] if skill_info
                                else task.get("task_description", ""))
                        if desc:
                            st.caption(desc)

                        # 掌握进度条（3格）
                        if mst["sessions_count"] == 0:
                            st.caption("尚未开始训练")
                        elif mst["mastered"]:
                            st.success("🏆 已达掌握标准（连续3次≥80%）— 可推进下一技能")
                        else:
                            streak = mst["streak"]
                            latest = mst.get("latest_pct", 0)
                            # 3格进度条：每格代表一次连续≥80%
                            bar_icons = ""
                            for i in range(3):
                                bar_icons += "🟩 " if i < streak else "⬜ "
                            remaining = 3 - streak
                            if streak > 0:
                                st.markdown(
                                    f"掌握进度：{bar_icons}（连续 {streak}/3 次≥80%）"
                                )
                            else:
                                st.markdown(
                                    f"掌握进度：{bar_icons}  最近正确率 {latest}%"
                                )
                            st.caption(
                                f"共训练 {mst['sessions_count']} 次  |  "
                                f"再连续 {remaining} 次≥80% 即达掌握标准"
                            )

                    with col_actions:
                        # 核心按钮：开始训练
                        if st.button("🎯 开始训练", key=f"start_train_{task['task_id']}",
                                     use_container_width=True, type="primary"):
                            # 放弃之前可能遗留的未完成训练
                            st.session_state.pop("active_session_id", None)
                            st.session_state.pop("active_skill", None)
                            st.session_state["prefill_task_id"] = task["task_id"]
                            st.session_state["prefill_skill_name"] = task["task_name"]
                            st.session_state["prefill_skill_id"] = skill_info["skill_id"] if skill_info else None
                            st.session_state["prefill_child_id"] = selected_child_id
                            st.session_state["prefill_child_name"] = child_options[selected_child_id]
                            st.session_state["current_view"] = "training"
                            st.rerun()

                        col_d, col_skip = st.columns(2)
                        with col_d:
                            if st.button("🗑️", key=f"del_{task['task_id']}",
                                         use_container_width=True):
                                manager.delete_task(task["task_id"], user_id)
                                st.rerun()
                        with col_skip:
                            if st.button("⏭ 跳过", key=f"skip_{task['task_id']}",
                                         use_container_width=True,
                                         help="暂时跳过此任务"):
                                manager.update_task_feedback(
                                    task["task_id"], user_id, "not_done", "暂时跳过"
                                )
                                st.rerun()

                        # 已掌握：有下一技能→推进，没有→直接完成
                        if mst["mastered"]:
                            has_next = skill_info and skill_info.get("next")
                            if has_next:
                                next_s = cur.get_next_skill(skill_info["skill_id"])
                                if next_s and st.button(
                                    f"➡️ 推进到：{next_s['name']}",
                                    key=f"next_{task['task_id']}",
                                    use_container_width=True
                                ):
                                    manager.update_task_feedback(
                                        task["task_id"], user_id, "completed", "已掌握，推进下一技能"
                                    )
                                    _add_curriculum_tasks(
                                        manager, user_id, selected_child_id, [next_s]
                                    )
                                    st.success(f"✅ 已推进到：{next_s['name']}")
                                    st.rerun()
                            else:
                                # 末端技能：掌握即完成
                                st.caption("🎯 该技能已是此路径的最高级别")
                                if st.button(
                                    "✅ 标记为已完成",
                                    key=f"finish_{task['task_id']}",
                                    use_container_width=True
                                ):
                                    manager.update_task_feedback(
                                        task["task_id"], user_id, "completed", "已掌握（无后续技能）"
                                    )
                                    st.success("✅ 已完成！")
                                    st.rerun()

                st.markdown("---")

    # ── Tab 2: 已完成 ────────────────────────────────────────
    with tab_done:
        all_tasks = manager.get_tasks(selected_child_id, user_id, status=None)
        done = [t for t in all_tasks if t["status"] in ("completed", "not_done")]
        if not done:
            st.info("暂无已完成的任务")
        else:
            for task in done:
                icon = "✅" if task["status"] == "completed" else "⏭"
                feedback = task.get("feedback", "")
                st.markdown(f"{icon} **{task['task_name']}**  —  {feedback}")
                col_r, col_d2 = st.columns([1, 1])
                with col_r:
                    if st.button("🔄 重新加入", key=f"redo_{task['task_id']}"):
                        manager.update_task_feedback(task["task_id"], user_id, "pending", None)
                        st.rerun()
                with col_d2:
                    if st.button("🗑️ 删除", key=f"del_done_{task['task_id']}"):
                        manager.delete_task(task["task_id"], user_id)
                        st.rerun()
                st.markdown("---")

    # ── Tab 3: 手动添加（带课程选择器） ─────────────────────
    with tab_add:
        st.markdown("#### 从课程指南选择技能")
        grouped = cur.get_all_skills_grouped()
        domain = st.selectbox("领域", list(grouped.keys()), key="add_domain")
        if domain:
            group = st.selectbox("技能组", list(grouped[domain].keys()), key="add_group")
            if group:
                skills_in_group = grouped[domain][group]
                skill_names = [s["name"] for s in skills_in_group]
                chosen_name = st.selectbox("技能", skill_names, key="add_skill")
                chosen_skill = next(s for s in skills_in_group if s["name"] == chosen_name)
                st.info(f"💡 {chosen_skill['description']}")
                _steps = chosen_skill.get("steps")
                if _steps:
                    with st.expander(f"📑 分步目标（共 {len(_steps)} 步，来自课程指南）"):
                        for _i, _stp in enumerate(_steps, 1):
                            st.markdown(f"{_i}. {_stp}")
                if st.button("➕ 加入任务清单", use_container_width=True, type="primary"):
                    added = _add_curriculum_tasks(
                        manager, user_id, selected_child_id, [chosen_skill]
                    )
                    if added:
                        st.success(f"✅ 已添加：{chosen_name}")
                        st.rerun()
                    else:
                        st.warning("此技能已在任务清单中")

        st.markdown("---")
        st.markdown("#### 或者手动填写自定义任务")
        with st.form("add_custom_task_form"):
            task_name = st.text_input("任务名称 *")
            task_desc = st.text_area("描述（怎么做）")
            category = st.selectbox("类别",
                ["语言训练", "社交训练", "行为训练", "生活自理", "认知训练", "感统训练", "其他"])
            if st.form_submit_button("➕ 添加"):
                if task_name:
                    success, msg, _ = manager.add_task(
                        child_id=selected_child_id, user_id=user_id,
                        task_name=task_name, task_description=task_desc,
                        category=category, is_auto_generated=False
                    )
                    if success:
                        st.success("✅ 已添加")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("请填写任务名称")

def render_progress_page():
    """进展记录 — 从训练数据自动生成"""
    st.markdown('<h2 class="page-title">📊 进展记录</h2>', unsafe_allow_html=True)

    manager = get_child_manager()
    user_id = memory_system.current_user_id
    children = manager.get_children(user_id)
    if not children:
        st.info("📝 请先在「孩子档案」中添加孩子信息")
        return

    child_options = {c["child_id"]: c["name"] for c in children}
    selected_child_id = st.selectbox(
        "👶 选择孩子", list(child_options.keys()),
        format_func=lambda x: child_options[x], key="progress_child_select"
    )

    sessions = td.get_sessions(user_id, child_id=selected_child_id, limit=200)
    finished = [s for s in sessions if s.get("finished")]

    if not finished:
        st.info("完成训练并保存后，进展记录会自动生成在这里。")
        return

    # ── 按技能汇总 ────────────────────────────────────────────
    from collections import defaultdict
    import pandas as pd

    skill_map = defaultdict(list)
    for s in finished:
        skill_map[s["skill_name"]].append(s)

    tab_skills, tab_timeline, tab_notes = st.tabs(["📌 技能进展", "📅 训练时间线", "📝 备注汇总"])

    with tab_skills:
        st.markdown("每项技能的状态与下一步（基于训练数据自动判断）")
        st.caption("🟥 停滞 = 练了多次没进步，别硬练，按下面建议改方案；"
                   "🟢🟡🟠🔵🔴 = 独立/语言/示范/身体/错误，红点多说明任务可能太难。")
        # 按「需要关注」优先排序：停滞/假掌握排前面
        order = ["stalled", "false_mastery", "watch", "progressing", "emerging", "mastered"]
        items = []
        for skill_name, sk_sessions in skill_map.items():
            ss = sorted(sk_sessions, key=lambda x: x["date"])
            items.append((skill_name, ss, _classify_skill(ss)))
        items.sort(key=lambda x: order.index(x[2]["status"]))

        for skill_name, skill_sessions_sorted, c in items:
            pcts = [s["percentage"] for s in skill_sessions_sorted]
            latest = pcts[-1]
            n = len(pcts)

            with st.expander(
                f"{c['icon']} {skill_name}  —  {c['label']}  ·  "
                f"最近 {latest}%  |  共训练 {n} 次"
            ):
                st.markdown(f"**下一步：** {c['advice']}")
                # 趋势折线
                if n >= 2:
                    df = pd.DataFrame({
                        "日期": [s["date"] for s in skill_sessions_sorted],
                        "独立正确率(%)": pcts
                    })
                    st.line_chart(df.set_index("日期"))

                # 每次记录摘要
                for s in reversed(skill_sessions_sorted):
                    icons = {"I":"🟢","V":"🟡","M":"🟠","P":"🔵","E":"🔴","+":"🟢","-":"🔴"}
                    seq = " ".join(icons.get(t,"⚪") for t in s["trials"][:15])
                    note = f"  ·  {s['notes']}" if s.get("notes") else ""
                    st.caption(
                        f"{s['date']}  独立{s['percentage']}%  "
                        f"({s['total']}次){note}"
                    )
                    if seq:
                        st.caption(seq)

    with tab_timeline:
        st.markdown("按日期排列的所有训练记录")
        timeline = sorted(finished, key=lambda x: x["date"], reverse=True)
        for s in timeline:
            icons = {"I":"🟢","V":"🟡","M":"🟠","P":"🔵","E":"🔴","+":"🟢","-":"🔴"}
            seq = " ".join(icons.get(t,"⚪") for t in s["trials"][:10])
            more = f"+{len(s['trials'])-10}…" if len(s["trials"]) > 10 else ""
            st.markdown(
                f"**{s['date']}** · {s['skill_name']} · "
                f"独立 **{s['percentage']}%** ({s['total']}次)"
            )
            if seq:
                st.caption(seq + more)
            st.divider()

    with tab_notes:
        st.markdown("家长备注汇总（训练时填写的观察）")
        notes_sessions = [s for s in finished if s.get("notes")]
        if not notes_sessions:
            st.info("训练保存时填写备注后，会汇总在这里。")
        else:
            for s in sorted(notes_sessions, key=lambda x: x["date"], reverse=True):
                st.markdown(f"**{s['date']}** · {s['skill_name']}")
                st.info(s["notes"])
                st.divider()

def render_data_dashboard():
    """数据看板 — 训练数据驱动"""
    st.markdown('<h2 class="page-title">📈 数据看板</h2>', unsafe_allow_html=True)

    manager = get_child_manager()
    user_id = memory_system.current_user_id
    children = manager.get_children(user_id)
    if not children:
        st.info("📝 请先在「孩子档案」中添加孩子信息")
        return

    child_options = {c["child_id"]: c["name"] for c in children}
    selected_child_id = st.selectbox(
        "👶 选择孩子", list(child_options.keys()),
        format_func=lambda x: child_options[x], key="dashboard_child_select"
    )

    import pandas as pd
    from collections import defaultdict
    from datetime import date, timedelta

    sessions = td.get_sessions(user_id, child_id=selected_child_id, limit=500)
    finished = [s for s in sessions if s.get("finished")]

    if not finished:
        st.info("完成训练后数据看板将自动生成。")
        return

    # ── 按技能聚合（升序），供掌握曲线与周对比复用 ──
    skill_sessions = defaultdict(list)
    for s in finished:
        skill_sessions[s["skill_name"]].append(s)
    for sk in skill_sessions:
        skill_sessions[sk].sort(key=lambda x: x["date"])

    def _indep_rate(ss):
        t = sum(x["total"] for x in ss)
        return sum(x.get("independent", 0) for x in ss) / t * 100 if t else 0

    # ── 本周 vs 上周（把时间放进指标）──
    wk1_start = (date.today() - timedelta(days=7)).isoformat()
    wk2_start = (date.today() - timedelta(days=14)).isoformat()
    this_week = [s for s in finished if s["date"] >= wk1_start]
    prev_week = [s for s in finished if wk2_start <= s["date"] < wk1_start]

    mastery_dates = {sk: _mastery_date(ss) for sk, ss in skill_sessions.items()}
    mastered_count = sum(1 for d in mastery_dates.values() if d)
    new_mastered_week = sum(1 for d in mastery_dates.values()
                            if d and d >= wk1_start)
    this_rate = _indep_rate(this_week)
    prev_rate = _indep_rate(prev_week)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("累计训练", len(finished))
    c2.metric("本周训练", len(this_week),
              delta=(len(this_week) - len(prev_week)) if prev_week else None)
    c3.metric("训练技能数", len(skill_sessions))
    c4.metric("已掌握技能", mastered_count,
              delta=(f"本周+{new_mastered_week}" if new_mastered_week else None))
    c5.metric("本周独立正确率", f"{round(this_rate)}%",
              delta=(f"{round(this_rate - prev_rate):+d} pt" if prev_week else None))
    st.caption("绿色 ↑ 是比上周进步，红色 ↓ 要留意（结合下方备注找原因）。"
               "本周训练次数偏低时，先补训练量再谈方法 —— ABA 讲究高频短时。")

    st.markdown("---")

    # ── 累计掌握技能数（成长曲线，时间维度）──
    st.markdown("**📈 累计掌握技能数（随时间）**")
    events = sorted(d for d in mastery_dates.values() if d)
    if events:
        from collections import Counter
        cnt = Counter(events)
        cum, rows = 0, []
        for d in sorted(cnt):
            cum += cnt[d]
            rows.append((d, cum))
        df_cum = pd.DataFrame(rows, columns=["日期", "累计掌握技能数"]).set_index("日期")
        st.area_chart(df_cum)
        st.caption("这条线往上走 = 孩子在稳步进步；走平了说明近期没有新技能达标，"
                   "看看是不是练得太少，或卡在某一项（去「进展记录」找 🟥 停滞标记）。")
    else:
        st.info("还没有技能达到掌握标准（连续 3 次 ≥80% 独立），继续按计划训练。")

    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        # 每日训练频次（近30天）
        month_ago = (date.today() - timedelta(days=30)).isoformat()
        recent = [s for s in finished if s["date"] >= month_ago]
        if recent:
            daily = defaultdict(int)
            for s in recent:
                daily[s["date"]] += 1
            df_daily = pd.DataFrame(
                sorted(daily.items()), columns=["日期", "训练次数"]
            ).set_index("日期")
            st.markdown("**近30天每日训练频次**")
            st.bar_chart(df_daily)
            st.caption("规律的柱子 = 训练有节奏；大片空白说明断练了，进步会慢。")

    with col_right:
        # 各技能最新正确率
        skill_latest = {}
        for s in finished:
            skill_latest[s["skill_name"]] = s["percentage"]
        if skill_latest:
            df_skills = pd.DataFrame(
                sorted(skill_latest.items(), key=lambda x: -x[1]),
                columns=["技能", "最新正确率(%)"]
            ).set_index("技能")
            st.markdown("**各技能最新独立正确率**")
            st.bar_chart(df_skills)
            st.caption("排在后面的低分技能，优先翻报告看「下阶段建议」。")

    # 去辅助趋势（近10次，堆叠面积图）
    st.markdown("---")
    st.markdown("**🟢 去辅助趋势（近10次训练）**")
    recent10 = sorted(finished, key=lambda x: x["date"])[-10:]
    if recent10:
        trend_data = []
        for s in recent10:
            total = s["total"] or 1
            trend_data.append({
                "日期": s["date"][:10],
                "独立(%)": round(s.get("independent", 0) / total * 100),
                "语言提示(%)": round(s.get("verbal", 0) / total * 100),
                "示范(%)": round(s.get("model", 0) / total * 100),
                "身体辅助(%)": round(s.get("physical", 0) / total * 100),
                "错误(%)": round(s.get("errors", 0) / total * 100),
            })
        df_trend = pd.DataFrame(trend_data).set_index("日期")
        st.area_chart(df_trend)
        st.caption("绿色（独立）越占越多 = 在成功退辅助；若长期靠提示/示范/身体辅助，"
                   "说明还不能算掌握，要继续退辅助。")

def render_assessment_page():
    """评估页面 — 多阶段递进式，覆盖全部 210 个技能"""
    st.markdown('<h2 class="page-title">📋 评估</h2>', unsafe_allow_html=True)
    st.caption("39道是/否题，分5个阶段递进，覆盖9个核心领域全部210个技能。凭日常观察回答即可。")

    manager = get_child_manager()
    user_id = memory_system.current_user_id
    children = manager.get_children(user_id)
    if not children:
        st.info("请先在「孩子档案」中添加孩子信息")
        return

    child_options = {c["child_id"]: c["name"] for c in children}
    selected_child_id = st.selectbox("选择孩子", list(child_options.keys()),
                                     format_func=lambda x: child_options[x],
                                     key="asmt_child")

    saved_key = f"assessment_result_{selected_child_id}"
    existing = st.session_state.get(saved_key)

    if existing:
        st.success("✅ 已完成评估")
        _render_assessment_result(existing, selected_child_id, manager, user_id)
        if st.button("🔄 重新评估"):
            st.session_state.pop(saved_key)
            st.rerun()
        return

    # ── 多阶段控制 ──
    TOTAL_STAGES = 5
    if "asmt_stage" not in st.session_state:
        st.session_state.asmt_stage = 1
    current_stage = st.session_state.asmt_stage

    # 阶段进度条
    pct = current_stage / TOTAL_STAGES
    st.progress(pct, f"阶段 {current_stage} / {TOTAL_STAGES}")

    # 阶段描述
    stage_descriptions = {
        1: "基础筛查 — 所有领域的基本能力摸底",
        2: "能力探测 — 对基础较好的领域向上推进",
        3: "中级评估 — 进一步提升能力层级",
        4: "进阶评估 — 挑战较复杂技能",
        5: "高阶评估 — 对标典型发育水平",
    }
    st.caption(f"**{stage_descriptions.get(current_stage, '')}**")

    # ── 当前阶段的题目 ──
    stage_qs = asmt.get_stage_questions(current_stage)
    if not stage_qs:
        # 跳过空阶段
        if current_stage < TOTAL_STAGES:
            st.session_state.asmt_stage = current_stage + 1
            st.rerun()
        else:
            st.error("没有更多题目")
        return

    # 按领域分组展示当前阶段题目
    from collections import defaultdict
    by_domain = defaultdict(list)
    for q in stage_qs:
        by_domain[q["domain"]].append(q)

    domain_icons = {
        "participation": "🪑", "imitation": "🪞", "visual": "👁️",
        "language": "💬", "play": "🎮", "social": "🤝",
        "emotion": "😊", "preacademic": "📚", "selfcare": "🧼",
    }

    # 存储答案的 session key
    answers_key = f"asmt_answers_{selected_child_id}"
    if answers_key not in st.session_state:
        st.session_state[answers_key] = {}

    for domain_key in sorted(by_domain.keys(),
                             key=lambda d: asmt.DOMAIN_PRIORITY.get(d, 99)):
        qs = by_domain[domain_key]
        icon = domain_icons.get(domain_key, "📌")
        name = asmt.DOMAIN_NAMES[domain_key]
        st.markdown(f"#### {icon} {name}")
        for q in qs:
            current_val = st.session_state[answers_key].get(q["id"])
            if current_val is True:
                default_idx = 0
            elif current_val is False:
                default_idx = 1
            else:
                default_idx = 1  # 默认选"否"
            answer = st.radio(
                q["question"],
                options=["是", "否"],
                horizontal=True,
                key=f"asmt_{q['id']}",
                index=default_idx,
            )
            st.session_state[answers_key][q["id"]] = (answer == "是")

    st.markdown("---")

    # ── 导航按钮 ──
    col1, col2 = st.columns(2)
    if current_stage > 1:
        if col1.button("⬅ 上一阶段"):
            st.session_state.asmt_stage = current_stage - 1
            st.rerun()

    if current_stage < TOTAL_STAGES:
        if col2.button("下一阶段 ➡", use_container_width=True, type="primary"):
            st.session_state.asmt_stage = current_stage + 1
            st.rerun()
    else:
        if col2.button("📊 完成评估，查看结果", use_container_width=True, type="primary"):
            result = asmt.score_assessment(st.session_state[answers_key])
            st.session_state[saved_key] = result
            st.session_state.asmt_stage = 1  # 重置阶段
            st.rerun()

    # 快捷跳转
    st.caption("也可以点击下方直接跳转到任意阶段：")
    stage_cols = st.columns(TOTAL_STAGES)
    for i in range(1, TOTAL_STAGES + 1):
        label = f"第{i}阶段"
        if i == current_stage:
            label = f"**{label}**"
        if stage_cols[i-1].button(label, key=f"stage_btn_{i}", use_container_width=True):
            st.session_state.asmt_stage = i
            st.rerun()


def _render_assessment_result(result: dict, child_id: str, manager, user_id: str):
    """渲染评估结果和推荐"""
    level = result["overall_level"]
    st.markdown(f"**整体水平：Level {level}** — {asmt.get_level_description(level)}")
    st.markdown("---")

    # 9领域得分：3列×3行
    st.markdown("#### 各领域评估结果")
    domain_items = list(asmt.DOMAIN_NAMES.items())
    for row_start in range(0, len(domain_items), 3):
        cols = st.columns(3)
        for col_idx, (domain, name) in enumerate(domain_items[row_start:row_start+3]):
            pct = result["domain_scores"].get(domain, 0)
            advice = asmt.get_domain_advice(domain, pct)
            cols[col_idx].metric(name, f"{pct}%", help=advice)

    st.markdown("---")
    st.markdown("#### 推荐训练起点（按优先级排序）")
    skill_ids = result.get("recommended_skill_ids", [])
    if not skill_ids:
        st.info("各项技能均已具备基础，建议直接进入中级训练。")
        return

    skills_to_add = [s for sid in skill_ids if (s := cur.get_skill(sid))]
    if not skills_to_add:
        st.info("暂无推荐技能")
        return

    # 按领域分组展示
    by_domain: dict = {}
    for skill in skills_to_add:
        by_domain.setdefault(skill["domain"], []).append(skill)

    for domain, skills in by_domain.items():
        for skill in skills:
            with st.expander(f"📌 **{skill['name']}** · {skill['domain']} · Level {skill['level']}"):
                st.write(skill["description"])

    if st.button("✨ 一键生成全部训练任务", use_container_width=True, type="primary"):
        added = _add_curriculum_tasks(manager, user_id, child_id, skills_to_add)
        if added:
            st.success(f"✅ 已生成 {added} 个训练任务，请前往「任务清单」查看！")
        else:
            st.info("这些任务已在清单中")


def render_training_page():
    """训练记录页 - ABA按试次数据记录"""
    total_skills = len(cur.SKILLS)
    domains = cur.get_all_domains()
    st.markdown(f'<h2 class="page-title">📋 训练记录 <span style="font-size:0.6em;color:#888;">（{len(domains)} 个领域 · {total_skills} 个技能）</span></h2>', unsafe_allow_html=True)

    manager = get_child_manager()
    user_id = memory_system.current_user_id

    children = manager.get_children(user_id)
    if not children:
        st.info("📝 请先在「孩子档案」中添加孩子信息")
        return

    child_options = {c["child_id"]: c["name"] for c in children}

    tab_record, tab_history = st.tabs(["🎯 开始训练", "📊 历史数据"])

    # ── Tab 1: 当前训练 session ──────────────────────────────
    with tab_record:
        # 从任务清单跳转过来时预填（用 get 而非 pop，防止 Streamlit 因 widget
        # 值变化额外 rerun 时提前清空 prefill，导致回退到默认技能「安坐5秒」）
        prefill_task_id = st.session_state.get("prefill_task_id")
        prefill_skill = st.session_state.get("prefill_skill_name")
        prefill_skill_id = st.session_state.get("prefill_skill_id")
        prefill_child_id = st.session_state.get("prefill_child_id")
        prefill_child_name = st.session_state.get("prefill_child_name")

        col_left, col_right = st.columns([1, 1])

        # 若已有活跃 session，不显示新建表单（避免 rerun 后回退到默认技能）
        sid_active = st.session_state.get("active_session_id")

        with col_left:
            auto_next = st.session_state.pop("auto_next_task", None)
            if auto_next:
                st.success(f"✅ 上一个已保存，已自动带出下一个任务：**{auto_next}**")
            elif prefill_skill:
                st.success(f"📋 从任务跳转：**{prefill_skill}**")

            if sid_active:
                # 已有活跃 session —— 显示当前训练摘要
                sessions = td.get_sessions(user_id)
                current = next((s for s in sessions if s["session_id"] == sid_active), None)
                if current:
                    st.markdown("#### 🔄 当前训练")
                    st.info(f"**{current['skill_name']}**\n\n👶 {current['child_name']}  |  📅 {current['date']}")
                    if st.button("✖ 取消本次训练", key="cancel_session", use_container_width=True):
                        st.session_state.pop("active_session_id", None)
                        st.session_state.pop("active_skill", None)
                        st.rerun()
            else:
                st.markdown("#### 新建训练")
                # 孩子选择：若从任务跳来则预选
                child_default_idx = 0
                if prefill_child_id and prefill_child_id in child_options:
                    child_default_idx = list(child_options.keys()).index(prefill_child_id)
                selected_child_id = st.selectbox(
                    "孩子",
                    options=list(child_options.keys()),
                    format_func=lambda x: child_options[x],
                    index=child_default_idx,
                    key="train_child"
                )
                # ── 技能选择：从任务跳转时直接显示，手动新建时分级选 ──
                chosen_skill_id = prefill_skill_id
                if prefill_skill:
                    # 从任务跳转：直接显示，不需要重新选
                    skill_name = prefill_skill
                    skill_obj = cur.get_skill(prefill_skill_id) if prefill_skill_id else None
                    if skill_obj:
                        st.info(f"🏷️ {skill_obj['domain']} · {skill_obj['name']}\n\n{skill_obj.get('description','')}")
                else:
                    # 手动新建：领域 → 技能 两级选择
                    grouped = cur.get_all_skills_grouped()
                    domains = list(grouped.keys())

                    # 检测领域是否变更，若是则重置技能选择
                    sel_domain = st.selectbox("领域", domains, key="train_domain")
                    prev_domain = st.session_state.get("_train_prev_domain", "")
                    if sel_domain != prev_domain:
                        st.session_state["_train_prev_domain"] = sel_domain
                        st.session_state.pop("train_skill_id", None)

                    # 把该领域所有技能展平，按 group 分组显示
                    domain_skills = []
                    for grp, skills in grouped[sel_domain].items():
                        for s in skills:
                            domain_skills.append(s)

                    # 用 skill_id 作为选项值（而非数字索引），防止切领域时索引错乱
                    skill_options = [s["skill_id"] for s in domain_skills]
                    # 查找已选技能在当前领域的默认位置
                    cur_skill_id = st.session_state.get("train_skill_id", "")
                    default_idx = 0
                    if cur_skill_id and cur_skill_id in skill_options:
                        default_idx = skill_options.index(cur_skill_id)

                    def _skill_label(sid: str) -> str:
                        for s in domain_skills:
                            if s["skill_id"] == sid:
                                return f"{s['name']}（{s.get('group','')}）"
                        return sid

                    selected_skill_id = st.selectbox(
                        "技能",
                        options=skill_options,
                        format_func=_skill_label,
                        index=default_idx,
                        key="train_skill_id",
                    )
                    chosen = next(
                        s for s in domain_skills if s["skill_id"] == selected_skill_id
                    )
                    skill_name = chosen["name"]
                    chosen_skill_id = chosen["skill_id"]
                    st.caption(f"💡 {chosen.get('description', '')}")

                train_date = st.date_input("日期", key="train_date")

                if st.button("▶ 开始记录", use_container_width=True, type="primary"):
                    child_name = child_options[selected_child_id]
                    sid_new = td.create_session(
                        user_id, selected_child_id, child_name,
                        skill_name, train_date.isoformat(),
                        task_id=prefill_task_id,
                        skill_id=chosen_skill_id,
                    )
                    st.session_state["active_session_id"] = sid_new
                    st.session_state["active_skill"] = skill_name
                    # 清理 prefill（session 已创建，下次回到训练页不再显示旧 prefill）
                    for k in ("prefill_task_id", "prefill_skill_name",
                              "prefill_skill_id", "prefill_child_id",
                              "prefill_child_name"):
                        st.session_state.pop(k, None)
                    st.rerun()

        with col_right:
            sid = st.session_state.get("active_session_id")
            # 自动推进提示
            mastered_next = st.session_state.pop("mastered_next", None)
            if mastered_next:
                st.success(f"🏆 已掌握！已自动加入下一个任务：**{mastered_next}**")

            # 刚保存完，提示加入任务清单
            last = st.session_state.get("last_finished_session")
            if last and not sid:
                pct = last.get("percentage", 0)
                skill = last.get("skill_name", "")
                child_id_last = last.get("child_id", "")
                child_name_last = last.get("child_name", "")
                history = td.get_skill_history(user_id, child_id_last, skill)
                last3 = [h["percentage"] for h in history[-3:]]
                mastered = len(last3) >= 3 and all(p >= 80 for p in last3)

                if mastered:
                    st.success(f"🏆 **{skill}** 已达到掌握标准！建议推进下一目标。")
                    task_name = f"推进：{skill}"
                    task_desc = f"已连续3次≥80%（最近：{pct}%），建议提高难度或进入下一技能。"
                else:
                    task_name = f"继续练习：{skill}"
                    task_desc = f"今日正确率 {pct}%，明天继续安排训练。"

                if st.button("📋 加入任务清单", use_container_width=True, key="add_to_tasks"):
                    mgr = get_child_manager()
                    mgr.add_task(
                        child_id=child_id_last,
                        user_id=user_id,
                        task_name=task_name,
                        task_description=task_desc,
                        category="认知训练",
                        is_auto_generated=True
                    )
                    st.session_state.pop("last_finished_session", None)
                    st.success("✅ 已加入任务清单")
                    st.rerun()

                if st.button("跳过", key="skip_add_task"):
                    st.session_state.pop("last_finished_session", None)
                    st.rerun()

            if not sid:
                if not st.session_state.get("last_finished_session"):
                    st.info("👈 新建一个训练来开始记录")
            else:
                sessions = td.get_sessions(user_id)
                current = next((s for s in sessions if s["session_id"] == sid), None)
                if not current:
                    st.session_state.pop("active_session_id", None)
                    st.rerun()

                st.markdown(f"#### 🎯 {current['skill_name']}")
                st.caption(f"日期：{current['date']}  |  孩子：{current['child_name']}")

                skill_info = next(
                    (s for s in cur.SKILLS if s["name"] == current["skill_name"]), None
                )

                # ── 分步目标（来自课程指南）─────────────────────
                steps = skill_info.get("steps") if skill_info else None
                if steps:
                    with st.expander(f"📑 分步目标（共 {len(steps)} 步，来自课程指南）", expanded=False):
                        st.caption("按顺序逐步训练：上一步连续3次≥80%再进入下一步。")
                        for i, stp in enumerate(steps, 1):
                            st.markdown(f"{i}. {stp}")

                # ── 内嵌图片卡片 ─────────────────────────────
                fc_cat = skill_info.get("flashcard_category") if skill_info else None
                if fc_cat and fc.get_page_count(fc_cat) > 0:
                    n_cards = fc.get_page_count(fc_cat)
                    card_key = f"card_idx_{sid}"
                    if card_key not in st.session_state:
                        st.session_state[card_key] = 0
                    card_idx = st.session_state[card_key]

                    img_bytes = fc.render_page_as_png_bytes(fc_cat, card_idx, dpi=150)
                    card_label = fc.get_card_label(fc_cat, card_idx)

                    nav_l, nav_card, nav_r = st.columns([1, 4, 1])
                    with nav_l:
                        if st.button("◀", key="card_prev", use_container_width=True):
                            st.session_state[card_key] = (card_idx - 1) % n_cards
                            st.rerun()
                    with nav_card:
                        if img_bytes:
                            st.image(img_bytes, caption=f"{card_label}（{card_idx+1}/{n_cards}）",
                                     use_container_width=True)
                    with nav_r:
                        if st.button("▶", key="card_next", use_container_width=True):
                            st.session_state[card_key] = (card_idx + 1) % n_cards
                            st.rerun()

                    col_rand, col_blank = st.columns([1, 2])
                    with col_rand:
                        if st.button("🎲 随机", key="card_rand", use_container_width=True):
                            import random
                            st.session_state[card_key] = random.randint(0, n_cards - 1)
                            st.rerun()

                # 试次结果按钮（4级辅助体系）
                st.markdown("**记录本次试次：**")
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                with c1:
                    if st.button("🟢 独立", use_container_width=True, key="btn_I",
                                 help="孩子独立正确完成，无需任何提示"):
                        td.add_trial(user_id, sid, "I"); st.rerun()
                with c2:
                    if st.button("🟡 语言", use_container_width=True, key="btn_V",
                                 help="给了语言提示（如说出答案）后正确"):
                        td.add_trial(user_id, sid, "V"); st.rerun()
                with c3:
                    if st.button("🟠 示范", use_container_width=True, key="btn_M",
                                 help="家长先示范了动作/答案后孩子正确"):
                        td.add_trial(user_id, sid, "M"); st.rerun()
                with c4:
                    if st.button("🔵 辅助", use_container_width=True, key="btn_P",
                                 help="给了身体辅助（手把手）后正确"):
                        td.add_trial(user_id, sid, "P"); st.rerun()
                with c5:
                    if st.button("🔴 错误", use_container_width=True, key="btn_E",
                                 help="孩子回答错误或无反应"):
                        td.add_trial(user_id, sid, "E"); st.rerun()
                with c6:
                    if st.button("↩ 撤销", use_container_width=True, key="btn_undo"):
                        td.delete_trial(user_id, sid); st.rerun()

                # 当前 session 统计
                trials = current["trials"]
                total = current["total"]
                pct = current["percentage"]

                st.markdown("---")
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("总试次", total)
                m2.metric("🟢 独立", current.get("independent", 0))
                m3.metric("🔴 错误", current.get("errors", 0))
                m4.metric("辅助次数", current.get("prompted", 0))
                m5.metric("独立正确率", f"{pct}%")

                if total > 0:
                    st.progress(pct / 100, text=f"独立正确率 {pct}%")

                # 辅助构成小标签
                if total > 0:
                    parts = []
                    if current.get("verbal"):   parts.append(f"🟡语言×{current['verbal']}")
                    if current.get("model"):    parts.append(f"🟠示范×{current['model']}")
                    if current.get("physical"): parts.append(f"🔵辅助×{current['physical']}")
                    if parts:
                        st.caption("辅助构成：" + "  ".join(parts))

                # 试次序列可视化
                if trials:
                    icons = {"I": "🟢", "V": "🟡", "M": "🟠", "P": "🔵", "E": "🔴",
                             "+": "🟢", "-": "🔴"}
                    st.markdown("**序列：** " + " ".join(icons.get(t, "⚪") for t in trials))

                # ── 干预建议（实时） ──────────────────────────
                if total >= 5:
                    history = td.get_skill_history(user_id, current["child_id"], current["skill_name"])
                    hist_pcts = [h["percentage"] for h in history]
                    suggestions = iv.get_intervention_suggestions(trials, hist_pcts)
                    if suggestions:
                        st.markdown("---")
                        st.markdown("#### 💡 干预建议")
                        for sug in suggestions:
                            full = iv.format_suggestion_for_display(sug)
                            priority_tag = {1: "🔴 立即", 2: "🟡 建议", 3: "🟢 参考"}.get(
                                sug["priority"], "")
                            with st.expander(
                                f"{priority_tag} **{full['title']}**  —  {sug['reason'][:40]}…",
                                expanded=(sug["priority"] == 1)
                            ):
                                st.caption(f"📌 {sug['reason']}")
                                st.markdown(f"**适用时机：** {full['when']}")
                                st.markdown("**操作步骤：**")
                                for step in full["steps"]:
                                    st.markdown(step)
                                if full.get("notes"):
                                    st.info(f"💬 {full['notes']}")

                # ABA 掌握提示（连续3次>80%提醒）
                history = td.get_skill_history(user_id, current["child_id"], current["skill_name"])
                recent = [h["percentage"] for h in history[-3:]] if history else []
                if len(recent) >= 3 and all(p >= 80 for p in recent):
                    st.success("🏆 连续3次≥80%，达到掌握标准！可以考虑推进下一个目标。")

                st.markdown("---")
                notes = st.text_input("备注", placeholder="今天的观察...", key="train_notes")
                col_fin, col_new = st.columns(2)
                with col_fin:
                    if st.button("💾 完成并保存", use_container_width=True):
                        finished = td.finish_session(user_id, sid, notes)
                        st.session_state.pop("active_session_id", None)

                        linked_task_id = current.get("task_id")
                        linked_skill_id = current.get("skill_id")
                        child_id_done = current["child_id"]
                        mgr = get_child_manager()

                        # 如果关联了任务，检查是否达到掌握标准并自动推进
                        if linked_task_id:
                            history = td.get_skill_history(
                                user_id, child_id_done, current["skill_name"]
                            )
                            last3 = [h["percentage"] for h in history[-3:]]
                            mastered = len(last3) >= 3 and all(p >= 80 for p in last3)
                            if mastered:
                                mgr.update_task_feedback(
                                    linked_task_id, user_id, "completed", "已掌握（连续3次≥80%）"
                                )
                                # 自动加下一技能任务（若有）
                                if linked_skill_id:
                                    next_s = cur.get_next_skill(linked_skill_id)
                                    if next_s:
                                        _add_curriculum_tasks(
                                            mgr, user_id, child_id_done, [next_s]
                                        )
                                        st.session_state["mastered_next"] = next_s["name"]
                                    else:
                                        st.session_state["mastered_next"] = "（该技能已是最高级别，请回任务清单标记完成）"

                        # 从任务清单进入时：保存后自动带出「同一个孩子的下一个待办任务」并预填到
                        # 训练页，省去回清单再点一次。优先选今天还没训练过的任务。
                        next_task = None
                        if linked_task_id:
                            pend = [
                                t for t in mgr.get_tasks(child_id_done, user_id, status="pending")
                                if t.get("category") != "报告" and t["task_id"] != linked_task_id
                            ]
                            next_task = next(
                                (t for t in pend
                                 if not td.trained_today(user_id, child_id_done, t["task_name"])),
                                pend[0] if pend else None,
                            )

                        if next_task:
                            nskill = next(
                                (s for s in cur.SKILLS if s["name"] == next_task["task_name"]), None
                            )
                            st.session_state["prefill_task_id"] = next_task["task_id"]
                            st.session_state["prefill_skill_name"] = next_task["task_name"]
                            st.session_state["prefill_skill_id"] = nskill["skill_id"] if nskill else None
                            st.session_state["prefill_child_id"] = child_id_done
                            st.session_state["prefill_child_name"] = child_options.get(
                                child_id_done, current.get("child_name", "")
                            )
                            st.session_state["auto_next_task"] = next_task["task_name"]
                            # 自动带出下一个任务时不弹「加入任务清单」提示，避免打断连做
                            st.session_state.pop("last_finished_session", None)
                        else:
                            # 没有下一个待办：维持原行为，显示保存后的提示
                            st.session_state["last_finished_session"] = finished

                        st.success("✅ 训练记录已保存")
                        st.rerun()
                with col_new:
                    if st.button("🗑️ 放弃本次", use_container_width=True):
                        td.delete_session(user_id, sid)
                        st.session_state.pop("active_session_id", None)
                        st.rerun()

    # ── Tab 2: 历史数据 ──────────────────────────────────────
    with tab_history:
        h_child_id = st.selectbox(
            "孩子",
            options=list(child_options.keys()),
            format_func=lambda x: child_options[x],
            key="hist_child"
        )
        h_skill_filter = st.text_input("筛选技能（留空显示全部）", key="hist_skill_filter")

        sessions = td.get_sessions(
            user_id,
            child_id=h_child_id,
            skill_name=h_skill_filter.strip() or None
        )

        if not sessions:
            st.info("暂无训练记录")
        else:
            # 如果筛选了特定技能，显示趋势图
            if h_skill_filter.strip():
                history = td.get_skill_history(user_id, h_child_id, h_skill_filter.strip())
                if len(history) >= 2:
                    import pandas as pd
                    df = pd.DataFrame(history)
                    st.markdown(f"**📈 「{h_skill_filter.strip()}」正确率趋势**")
                    st.line_chart(df.set_index("date")["percentage"])

            # 历史列表
            for s in sessions:
                icons = {"+" : "🟢", "-": "🔴", "P": "🟡"}
                trial_str = " ".join(icons.get(t, t) for t in s["trials"][:20])
                if len(s["trials"]) > 20:
                    trial_str += f" …(共{len(s['trials'])}次)"

                label = f"📅 {s['date']}  |  {s['skill_name']}  |  {s['percentage']}%  ({s['total']}试次)"
                with st.expander(label):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("正确率", f"{s['percentage']}%")
                    c2.metric("✅", s["correct"])
                    c3.metric("❌", s["incorrect"])
                    c4.metric("🤝", s["prompted"])
                    if trial_str:
                        st.markdown("**序列：** " + trial_str)
                    if s.get("notes"):
                        st.caption(f"备注：{s['notes']}")
                    if st.button("🗑️ 删除", key=f"del_sess_{s['session_id']}"):
                        td.delete_session(user_id, s["session_id"])
                        st.rerun()


def render_flashcards_page():
    """图片卡片页 - 备课浏览 + 互动练习"""
    categories = fc.get_categories()
    total_cards = sum(fc.get_page_count(c) for c in categories)
    st.markdown(f'<h2 class="page-title">🃏 图片卡片 <span style="font-size:0.6em;color:#888;">（{len(categories)} 个类别 · {total_cards} 张卡片）</span></h2>', unsafe_allow_html=True)

    if not categories:
        st.error("未找到图片卡片目录，请确认 aba/图片/ 文件夹存在")
        return

    tab_browse, tab_practice = st.tabs(["📚 备课浏览", "🎯 互动练习"])

    # ── Tab 1: 备课浏览 ──────────────────────────────────────
    with tab_browse:
        col_cat, col_main = st.columns([1, 3])

        with col_cat:
            grouped = fc.get_grouped_categories()
            st.markdown("**领域**")
            selected_group = st.radio(
                "选择领域",
                options=list(grouped.keys()),
                label_visibility="collapsed",
                key="browse_group"
            )
            st.markdown("**类别**")
            selected_cat = st.radio(
                "选择类别",
                options=grouped[selected_group],
                label_visibility="collapsed",
                key="browse_cat"
            )

        with col_main:
            if selected_cat:
                n = fc.get_page_count(selected_cat)
                st.markdown(f"**{selected_cat}**（共 {n} 张）")

                # 每行显示3张
                cols_per_row = 3
                for row_start in range(0, n, cols_per_row):
                    cols = st.columns(cols_per_row)
                    for col_idx, page_idx in enumerate(range(row_start, min(row_start + cols_per_row, n))):
                        with cols[col_idx]:
                            img = fc.render_page_as_png_bytes(selected_cat, page_idx, dpi=150)
                            label = fc.get_card_label(selected_cat, page_idx)
                            if img:
                                st.image(img, caption=label, use_container_width=True)

    # ── Tab 2: 互动练习 ──────────────────────────────────────
    with tab_practice:
        manager = get_child_manager()
        user_id = memory_system.current_user_id
        children = manager.get_children(user_id)

        if not children:
            st.info("请先在「孩子档案」中添加孩子信息")
            return

        child_options = {c["child_id"]: c["name"] for c in children}

        col_setup, col_card = st.columns([1, 2])

        with col_setup:
            st.markdown("**设置**")
            p_child_id = st.selectbox(
                "孩子",
                options=list(child_options.keys()),
                format_func=lambda x: child_options[x],
                key="practice_child"
            )
            p_grouped = fc.get_grouped_categories()
            p_group = st.selectbox("领域", options=list(p_grouped.keys()), key="practice_group")
            p_cat = st.selectbox("卡片类别", options=p_grouped[p_group], key="practice_cat")
            p_n = fc.get_page_count(p_cat) if p_cat else 0

            if st.button("🎲 随机抽一张", use_container_width=True, type="primary"):
                import random
                if p_n > 0:
                    st.session_state["practice_page"] = random.randint(0, p_n - 1)
                    st.session_state["practice_cat_active"] = p_cat
                    st.session_state["practice_child_active"] = p_child_id

            if st.button("⏭ 下一张（顺序）", use_container_width=True):
                cur = st.session_state.get("practice_page", -1)
                st.session_state["practice_page"] = (cur + 1) % p_n if p_n > 0 else 0
                st.session_state["practice_cat_active"] = p_cat
                st.session_state["practice_child_active"] = p_child_id

        with col_card:
            active_cat = st.session_state.get("practice_cat_active")
            active_page = st.session_state.get("practice_page")
            active_child = st.session_state.get("practice_child_active")

            if active_cat is None:
                st.info("👈 选好类别后点击按钮开始")
            else:
                img = fc.render_page_as_png_bytes(active_cat, active_page, dpi=150)
                label = fc.get_card_label(active_cat, active_page)
                n_total = fc.get_page_count(active_cat)

                if img:
                    st.image(img, caption=f"{label}  （第 {active_page+1}/{n_total} 张）",
                             use_container_width=True)

                st.markdown("**记录反应：**")
                rc1, rc2, rc3 = st.columns(3)

                # 记录反应并联动数据表
                def _log_trial(result: str):
                    child_name = child_options.get(active_child, "")
                    skill = f"{active_cat}-{label}"
                    # 复用或新建当前练习 session
                    sess_key = f"practice_session_{active_child}_{active_cat}"
                    sid = st.session_state.get(sess_key)
                    if not sid:
                        sid = td.create_session(user_id, active_child, child_name, skill)
                        st.session_state[sess_key] = sid
                    td.add_trial(user_id, sid, result)

                with rc1:
                    if st.button("✅ 正确", use_container_width=True, key="prac_correct"):
                        _log_trial("+")
                        st.toast("已记录：正确 ✅")
                with rc2:
                    if st.button("❌ 错误", use_container_width=True, key="prac_wrong"):
                        _log_trial("-")
                        st.toast("已记录：错误 ❌")
                with rc3:
                    if st.button("🤝 辅助", use_container_width=True, key="prac_prompt"):
                        _log_trial("P")
                        st.toast("已记录：辅助 🤝")

                # 显示本次练习累计
                sess_key = f"practice_session_{active_child}_{active_cat}"
                sid = st.session_state.get(sess_key)
                if sid:
                    sessions = td.get_sessions(user_id)
                    cur = next((s for s in sessions if s["session_id"] == sid), None)
                    if cur and cur["total"] > 0:
                        st.markdown("---")
                        st.caption(
                            f"本轮：{cur['total']}次  ✅{cur['correct']}  ❌{cur['incorrect']}  🤝{cur['prompted']}  |  正确率 **{cur['percentage']}%**"
                        )
                        if st.button("💾 保存本轮记录", key="save_practice"):
                            td.finish_session(user_id, sid)
                            st.session_state.pop(sess_key, None)
                            st.success("✅ 已保存到训练记录")


# ─── 技能状态分类器（报告与进展记录共用）────────────────────────
# 把每项技能从「一个正确率」升级为「一个可执行的判断」。
# 依据：近 3 次训练聚合的 独立/辅助/错误 占比 + 整体趋势。
_SKILL_STATUS = {
    "mastered":      ("✅", "已掌握"),
    "false_mastery": ("⚠️", "假掌握（靠辅助）"),
    "stalled":       ("🟥", "停滞"),
    "progressing":   ("📈", "进步中"),
    "emerging":      ("🌱", "起步中"),
    "watch":         ("👀", "需观察"),
}


def _classify_skill(sessions_sorted: list) -> dict:
    """对单项技能分类并给出下一步建议。
    sessions_sorted: 该技能的 finished sessions，按日期升序。
    返回 {status, icon, label, advice, next_skill_name}。"""
    from utils.curriculum import get_next_skill

    pcts = [s["percentage"] for s in sessions_sorted]
    n = len(pcts)
    latest = pcts[-1] if pcts else 0

    # 近 3 次聚合，判断辅助依赖
    recent = sessions_sorted[-3:]
    tot = sum(s["total"] for s in recent) or 1
    indep = sum(s.get("independent", 0) for s in recent)
    prompts = sum(s.get("verbal", 0) + s.get("model", 0) + s.get("physical", 0)
                  for s in recent)
    errs = sum(s.get("errors", 0) for s in recent)
    indep_rate = indep / tot * 100
    prompt_rate = prompts / tot * 100
    error_rate = errs / tot * 100

    mastered = n >= 3 and all(p >= 80 for p in pcts[-3:])

    if mastered:
        status = "mastered"
    elif n < 3:
        status = "emerging"
    elif latest - pcts[0] >= 15:
        # 独立率较起点明显提升 → 进步中（即便仍有辅助）
        status = "progressing"
    elif n >= 5 and (pcts[-1] - pcts[-4]) <= 5 and latest < 80:
        # 5+ 次几乎无增长 → 停滞
        status = "stalled"
    elif indep_rate < 80 and prompt_rate >= 40 and error_rate <= 20:
        # 错误少但退不掉辅助 → 假掌握
        status = "false_mastery"
    elif latest > pcts[0]:
        status = "progressing"
    else:
        status = "watch"

    icon, label = _SKILL_STATUS[status]

    # 课程下一步（仅已掌握时有意义）
    next_name = None
    if status == "mastered":
        skill_id = next((s.get("skill_id") for s in reversed(sessions_sorted)
                         if s.get("skill_id")), None)
        if skill_id:
            nxt = get_next_skill(skill_id)
            if nxt:
                next_name = nxt["name"]

    advice_map = {
        "mastered": (
            f"转入维持期（每周回测 1 次保持不退步）"
            + (f"，可推进下一步：**{next_name}**" if next_name else "，可挑选同领域更难的新目标")
        ),
        "emerging": f"数据还少（仅 {n} 次），按计划继续训练，攒够 3 次再判断。",
        "false_mastery": (
            "能在辅助下完成、但还退不掉辅助。进入退辅助流程："
            "逐步减少身体/示范辅助，多给独立尝试的机会。"
        ),
        "stalled": (
            f"练了 {n} 次仍没进步，别硬练。改方案：拆成更小步骤 / "
            "换更有吸引力的强化物 / 调整辅助方式。"
        ),
        "progressing": "方法有效，保持当前策略，下周可适当加量。",
        "watch": "最近正确率有波动，结合备注看是任务太难还是状态问题。",
    }
    return {
        "status": status, "icon": icon, "label": label,
        "advice": advice_map[status], "next_skill_name": next_name,
    }


def _mastery_date(sessions_sorted: list):
    """返回该技能首次达成「连续3次≥80%」的日期；未掌握返回 None。"""
    pcts = [s["percentage"] for s in sessions_sorted]
    for i in range(2, len(pcts)):
        if all(p >= 80 for p in pcts[i - 2:i + 1]):
            return sessions_sorted[i]["date"]
    return None


def _build_report_text(child_name: str, sessions: list, tasks: list,
                        period_label: str, child_obj: dict) -> str:
    """从训练数据构建纯文本报告"""
    from collections import defaultdict
    from datetime import date, timedelta

    finished = [s for s in sessions if s.get("finished")]
    if not finished:
        return f"# {child_name} {period_label}训练报告\n\n暂无训练数据。"

    # 按技能聚合完整 session（分类器需要 独立/辅助/错误 明细）
    skill_sessions = defaultdict(list)
    for s in finished:
        skill_sessions[s["skill_name"]].append(s)
    for sk in skill_sessions:
        skill_sessions[sk].sort(key=lambda x: x["date"])

    total_sessions = len(finished)
    total_trials = sum(s["total"] for s in finished)
    overall_indep = (
        sum(s.get("independent", 0) for s in finished) / total_trials * 100
        if total_trials else 0
    )

    # 对每项技能分类
    classified = {sk: _classify_skill(ss) for sk, ss in skill_sessions.items()}
    # 排除借用 tasks 表存储的报告记录，否则会被当成训练任务列出
    pending_tasks = [t for t in tasks
                     if t["status"] == "pending" and t.get("category") != "报告"]

    lines = [
        f"# {child_name} {period_label}训练报告",
        f"生成时间：{date.today().isoformat()}",
        "",
        "> 📌 本报告不只是总结 —— 往下看「下阶段建议」，每项技能都给了下周具体该怎么做。",
        "",
        "## 训练概况",
        f"- 训练次数：{total_sessions} 次",
        f"- 总试次：{total_trials} 次",
        f"- 整体独立正确率：{round(overall_indep)}%",
        f"- 训练技能数：{len(skill_sessions)} 项",
        "",
        "## 各技能状态",
    ]
    for sk, ss in sorted(skill_sessions.items()):
        c = classified[sk]
        latest = ss[-1]["percentage"]
        n = len(ss)
        lines.append(f"- {c['icon']} **{sk}** — {c['label']}（最近 {latest}%，共 {n} 次）")

    # ── 核心：下阶段建议（处方）──
    lines += ["", "## 🎯 下阶段建议（按优先级）"]
    # 优先级：停滞/假掌握 先处理 → 已掌握推进 → 进步中保持 → 起步观察
    order = ["stalled", "false_mastery", "mastered", "progressing", "watch", "emerging"]
    ranked = sorted(skill_sessions.keys(),
                    key=lambda sk: order.index(classified[sk]["status"]))
    for sk in ranked:
        c = classified[sk]
        lines.append(f"- {c['icon']} **{sk}**：{c['advice']}")

    if pending_tasks:
        lines += ["", "## 当前任务清单"]
        for t in pending_tasks:
            lines.append(f"- 📌 {t['task_name']}")

    # 家长观察摘要
    notes_list = [s["notes"] for s in finished if s.get("notes")]
    if notes_list:
        lines += ["", "## 家长观察记录"]
        for note in notes_list[-5:]:  # 最近5条
            lines.append(f"> {note}")

    lines += [
        "", "---",
        "*本报告由 ABA智能助手 根据训练数据自动生成*"
    ]
    return "\n".join(lines)


_AUTO_REPORT_TYPE = "周报(自动)"


def _maybe_auto_weekly_report(manager, user_id, child_id, child_name, child_obj):
    """打开即补：进入新一周时，自动为「上一周」补生成一份周报。
    返回新报告覆盖的周区间字符串，未生成返回 None。"""
    from datetime import date, timedelta

    today = date.today()
    this_monday = today - timedelta(days=today.weekday())

    # 本周已自动生成过 → 跳过
    existing = manager.get_reports(child_id, user_id,
                                   report_type=_AUTO_REPORT_TYPE, limit=5)
    for r in existing:
        if r.get("created_at", "")[:10] >= this_monday.isoformat():
            return None

    # 覆盖上一周：上周一 ~ 本周一（不含）
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    sessions = td.get_sessions(user_id, child_id=child_id, limit=500)
    period = [s for s in sessions if s.get("finished")
              and last_monday.isoformat() <= s.get("date", "") < this_monday.isoformat()]
    if not period:
        return None  # 上周没训练，不生成空报告

    tasks = manager.get_tasks(child_id, user_id, status=None)
    report_text = _build_report_text(child_name, period, tasks, "周", child_obj)
    span = f"{last_monday.isoformat()}~{last_sunday.isoformat()}"
    manager.save_report(
        child_id=child_id, user_id=user_id, report_type=_AUTO_REPORT_TYPE,
        title=f"上周周报 {span}", content=report_text,
        period_start=last_monday.isoformat(), period_end=last_sunday.isoformat()
    )
    return span


def render_report_center_page():
    """报告中心 — 从训练数据自动生成"""
    st.markdown('<h2 class="page-title">📝 报告中心</h2>', unsafe_allow_html=True)
    st.caption("报告不只是总结 —— 每份报告底部的「🎯 下阶段建议」会告诉你下周每项技能具体怎么做。")

    manager = get_child_manager()
    user_id = memory_system.current_user_id
    children = manager.get_children(user_id)
    if not children:
        st.info("📝 请先在「孩子档案」中添加孩子信息")
        return

    child_options = {c["child_id"]: c["name"] for c in children}
    selected_child_id = st.selectbox(
        "👶 选择孩子", list(child_options.keys()),
        format_func=lambda x: child_options[x], key="report_child_select"
    )
    child_name = child_options[selected_child_id]
    child_obj = next((c for c in children if c["child_id"] == selected_child_id), {})

    from datetime import date, timedelta

    # 打开即补：进入新一周自动生成上周周报
    auto_span = _maybe_auto_weekly_report(
        manager, user_id, selected_child_id, child_name, child_obj
    )
    if auto_span:
        st.success(f"📬 已自动为你生成上周周报（{auto_span}），可在「历史报告」查看。")

    tab_gen, tab_history = st.tabs(["✨ 生成报告", "📋 历史报告"])

    with tab_gen:
        report_type = st.radio(
            "报告周期", ["本周", "本月", "全部数据"],
            horizontal=True, key="report_type"
        )

        # 确定时间范围
        today = date.today()
        if report_type == "本周":
            start = (today - timedelta(days=today.weekday())).isoformat()
            label = "周"
        elif report_type == "本月":
            start = today.replace(day=1).isoformat()
            label = "月"
        else:
            start = "2000-01-01"
            label = "阶段"

        sessions = td.get_sessions(user_id, child_id=selected_child_id, limit=500)
        period_sessions = [s for s in sessions if s.get("date", "") >= start]
        tasks = manager.get_tasks(selected_child_id, user_id, status=None)

        finished_count = len([s for s in period_sessions if s.get("finished")])
        st.caption(f"该周期内共有 {finished_count} 次已完成训练记录")

        if st.button("📄 生成报告", use_container_width=True, type="primary"):
            report_text = _build_report_text(
                child_name, period_sessions, tasks, label, child_obj
            )
            # 存入 session state 展示，同时保存到历史（独立 reports 表）
            st.session_state["current_report"] = report_text
            manager.save_report(
                child_id=selected_child_id, user_id=user_id, report_type=label,
                title=f"{label}报告 {today.isoformat()}", content=report_text,
                period_start=start, period_end=today.isoformat()
            )
            st.rerun()

        if st.session_state.get("current_report"):
            st.markdown("---")
            st.markdown(st.session_state["current_report"])
            if st.button("📋 复制到剪贴板提示"):
                st.info("请手动选中上方文字复制，或截图保存。")
            if st.button("关闭预览"):
                st.session_state.pop("current_report", None)
                st.rerun()

    with tab_history:
        # 展示已保存的报告（独立 reports 表）
        reports = manager.get_reports(selected_child_id, user_id, limit=50)
        if not reports:
            st.info("生成报告后会保存在这里。")
        else:
            for r in reports:
                icon = "📬" if r["report_type"] == _AUTO_REPORT_TYPE else "📄"
                with st.expander(f"{icon} {r['title']}  ·  {r['created_at'][:10]}"):
                    full = manager.get_report_content(r["report_id"], user_id)
                    st.markdown(full["content"] if full else "（内容缺失）")
                    if st.button("🗑️ 删除", key=f"del_rpt_{r['report_id']}"):
                        manager.delete_report(r["report_id"], user_id)
                        st.rerun()

def auto_login_from_query():
    """从 URL 参数 ?user=&token= 免登录建立会话。

    用于从人生教练「← 返回 ABA 助手」跳回时不必重新登录：校验与人生教练
    同一个 COACH_SSO_SECRET 签发的 token，通过才建立会话。
    """
    if st.session_state.get("logged_in", False):
        return
    try:
        import sqlite3
        from coach.coach_engine import verify_coach_sso_token
        username = st.query_params.get("user", "")
        token = st.query_params.get("token", "")
        if not (username and verify_coach_sso_token(username, token)):
            return
        conn = sqlite3.connect(str(memory_system.db_path))
        cur = conn.cursor()
        cur.execute("SELECT user_id, username FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()
        if row:
            memory_system.current_user_id = row[0]
            memory_system.current_username = row[1]
            st.session_state.logged_in = True
            st.session_state.user_id = row[0]
            st.session_state.username = row[1]
            st.session_state.conversation_loaded = False
            # 凭证只消费一次：清掉 URL 里的 user/token，否则退出登录后会被立刻自动登录回去
            try:
                st.query_params.clear()
            except Exception:
                pass
    except Exception:
        pass


def main():
    """主函数"""
    apply_custom_styles()
    initialize_session_state()
    get_cookie_manager().get_all()  # 先挂载 cookie 组件并读取，供下面恢复登录
    auto_login_from_query()  # 从人生教练带 token 返回时免登录

    if st.session_state.pop("_force_logout", False):
        # 退出登录：在正常渲染流程里删 cookie（避免删除后立刻 rerun 打断写入），
        # 且本次跳过 cookie 恢复，否则会被尚未删除的 cookie 立刻自动登录回去。
        clear_login_cookie()
        st.session_state["_cookie_synced"] = False
    else:
        restore_login_from_cookie()  # 凭 cookie 免密恢复会话，保持登录直到手动退出

    # 关键：登录成功后在「正常渲染流程」里写 cookie（不能在登录按钮回调里 set 后立刻
    # st.rerun()，那样组件来不及执行、cookie 写不进去——这正是之前仍会自动退出的原因）。
    # 每次进来都刷新有效期，做到「活跃就一直保持登录」。
    if (st.session_state.get("logged_in") and st.session_state.get("username")
            and not st.session_state.get("_cookie_synced")):
        set_login_cookie(st.session_state["username"])
        st.session_state["_cookie_synced"] = True

    user_context = render_sidebar()

    st.markdown("---")

    current_view = st.session_state.get("current_view", "chat")

    if not st.session_state.get("logged_in", False):
        st.session_state.current_view = "chat"
        current_view = "chat"

    if current_view == "chat":
        render_chat_view()
    elif current_view == "profile":
        render_child_profile_page()
    elif current_view == "tasks":
        render_task_list_page()
    elif current_view == "progress":
        render_progress_page()
    elif current_view == "dashboard":
        render_data_dashboard()
    elif current_view == "reports":
        render_report_center_page()
    elif current_view == "assessment":
        render_assessment_page()
    elif current_view == "training":
        render_training_page()
    elif current_view == "flashcards":
        render_flashcards_page()
    elif current_view == "life_coach":
        render_life_coach_view()


def render_life_coach_view():
    """嵌入人生教练模块 - 使用 iframe 加载独立应用"""
    import streamlit.components.v1 as components
    import streamlit as st

    # 隐藏默认 Streamlit 顶栏和侧边栏，给 iframe 全屏空间
    # 传递用户名到人生教练应用
    import os
    from coach.coach_engine import coach_sso_token

    username = memory_system.current_username or ""

    # iframe 由「用户浏览器」加载，必须用服务器公网地址（不能用 localhost）。
    # 公网地址通过 LIFE_COACH_URL 配置（如 http://<服务器IP>:8503），本地开发缺省 localhost。
    # 带上签名 token，人生教练侧据此免密自动登录，防止凭用户名冒充。
    from urllib.parse import quote
    public_base = os.getenv("LIFE_COACH_URL", "http://localhost:8503").rstrip("/")
    token = coach_sso_token(username) or ""
    coach_url = f"{public_base}?user={quote(username)}&token={token}"
    # 可用性检查在「服务器后端/容器内」执行：
    #  - 本地开发：localhost:8503
    #  - Docker：localhost 在容器内指自己，连不到另一个容器，必须用 compose 服务名 life-coach
    # 因此用 COACH_HEALTH_URL 配置（compose 里设为 http://life-coach:8503/_stcore/health）
    check_url = os.getenv("COACH_HEALTH_URL", "http://localhost:8503/_stcore/health")

    st.markdown("""
    <style>
        /* 全屏 iframe 容器 */
        .coach-iframe-container {
            width: 100%;
            height: calc(100vh - 60px);
            border: none;
            border-radius: 12px;
            overflow: hidden;
        }
        /* 提示信息 */
        .coach-launch-hint {
            background: linear-gradient(135deg, #E8F0E8, #E8F4EF);
            border: 1px solid #5B8C5A;
            border-radius: 14px;
            padding: 2rem;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)

    # 检查人生教练服务是否可用
    coach_available = False
    try:
        import urllib.request
        urllib.request.urlopen(check_url, timeout=2)
        coach_available = True
    except Exception:
        coach_available = False

    if coach_available:
        # 整页跳转到人生教练（独立应用）——把整个浏览器标签切过去，不再嵌在 ABA 里
        import json as _json
        components.html(
            f"""
            <script>
                window.top.location.href = {_json.dumps(coach_url)};
            </script>
            <p style="font-family:sans-serif;color:#3D6B3C;font-size:0.95rem;">
                正在进入人生教练…若没有自动跳转，
                <a href="{coach_url}" target="_top">请点此进入</a>。
            </p>
            """,
            height=60,
        )
    else:
        # 人生教练服务未运行，显示启动提示
        st.markdown("""
        <div class="coach-launch-hint">
            <div style="font-size:2.5rem;margin-bottom:1rem;">🌿</div>
            <h2 style="color:#3D6B3C;margin-bottom:0.5rem;">人生教练</h2>
            <p style="color:#636E72;margin-bottom:1.5rem;">AI 陪伴你成长 · 情绪支持 · 个人成长</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🚀 启动方式")

        st.info("""
        人生教练是一个独立的 Streamlit 应用，需要单独启动。

        **在终端中运行以下命令：**
        ```bash
        cd src/MVP_web
        streamlit run life_coach_app.py --server.port 8503
        ```

        启动后，刷新此页面即可自动加载。
        """, icon="💡")

        # 提供快速启动按钮（仅适用于单机/本地运行；Docker 部署下 life-coach 是独立容器，不会走到这里）
        if st.button("🚀 一键启动人生教练", use_container_width=True, type="primary"):
            import subprocess, sys
            try:
                here = os.path.dirname(os.path.abspath(__file__))
                script_path = os.path.join(here, "life_coach_app.py")
                subprocess.Popen(
                    # 用当前解释器的 streamlit，避免 PATH 里没有 streamlit 命令；
                    # 传当前环境，使 COACH_SSO_SECRET 等一并带给子进程（免密登录才生效）
                    [sys.executable, "-m", "streamlit", "run", script_path,
                     "--server.port", "8503", "--server.address", "127.0.0.1",
                     "--server.headless=true", "--browser.gatherUsageStats=false"],
                    cwd=here,
                    env=os.environ.copy(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                st.success("人生教练正在启动中，请等待 5-10 秒后刷新此页面。")
            except Exception as e:
                st.error(f"启动失败：{e}\n\n请手动在终端运行启动命令。")

if __name__ == "__main__":
    main()
