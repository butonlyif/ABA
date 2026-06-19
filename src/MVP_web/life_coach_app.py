"""
====================================
人生教练模块 - 主应用
====================================

面向自闭症儿童家长的 AI 人生教练。
理论基础：ACT（接纳与承诺疗法）+ 正念 + 积极心理学

使用方式：streamlit run life_coach_app.py --server.port 8503
支持通过 URL 参数自动登录：?user=用户名
"""

import streamlit as st
import os
import sys
import json
from collections import defaultdict
from datetime import datetime, timedelta, date, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coach.coach_styles import apply_coach_styles, get_coach_card, get_kb_item_html, get_progress_bar, get_badge, THEME
from core.session_memory import memory_system
from coach.coach_content import (
    KB_ARTICLES, KB_CATEGORIES, TASK_ACTIONS, GROWTH_STAGES,
    ISSUE_TYPE_KEYWORDS, ISSUE_STAGES_TEMPLATES,
    MOOD_EMOJIS, MOOD_SCORES, EMOTION_KEYWORDS, EMOTION_COACH_STRATEGIES,
)
from coach.coach_engine import (
    detect_emotion, detect_issue_type, generate_coach_response_v2, assess_risk,
    verify_coach_sso_token,
)

# ====================================
# 页面配置
# ====================================
st.set_page_config(
    page_title="🌿 人生教练 - 陪伴你成长",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="expanded",
)

apply_coach_styles()

# ====================================
# 用户认证 & 数据持久化
# ====================================
def auto_login_from_query():
    """从 URL 参数自动登录（主 ABA iframe 传入用户名 + 签名 token）。

    公开 8503 后，仅凭用户名登录会被冒充，因此必须校验主应用用同一
    COACH_SSO_SECRET 签发的 token；未配置密钥或 token 无效时不自动登录，
    回退到正常的账号密码登录页。
    """
    query_params = st.query_params
    username = query_params.get("user", "")
    token = query_params.get("token", "")
    if username and verify_coach_sso_token(username, token):
        # token 校验通过，直接查库建立会话
        try:
            import sqlite3
            conn = sqlite3.connect(str(memory_system.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, username FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                memory_system.current_user_id = row[0]
                memory_system.current_username = row[1]
                st.session_state["logged_in"] = True
                st.session_state["coach_auto_logged"] = True
                # 凭证只消费一次：清掉 URL 里的 user/token，否则退出登录后会被立刻自动登录回去
                try:
                    st.query_params.clear()
                except Exception:
                    pass
                # 更新最后登录时间
                try:
                    conn2 = memory_system._safe_connect()  # 带 busy_timeout，避免登录高峰并发写 locked
                    c2 = conn2.cursor()
                    c2.execute(
                        "UPDATE users SET last_login = ? WHERE user_id = ?",
                        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row[0])
                    )
                    conn2.commit()
                    conn2.close()
                except Exception:
                    pass
                return True
        except Exception:
            pass
    return False


def render_login_page():
    """显示登录界面（与 ABA 助手共享用户系统）"""
    st.markdown("""
    <div class="login-hero">
        <div style="font-size:3rem;">🌿</div>
        <h1>人生教练</h1>
        <p>登录你的 ABA 智能助手账号，即可使用人生教练</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["登录", "注册"])

    with tab1:
        username = st.text_input("用户名", key="coach_login_user")
        password = st.text_input("密码", type="password", key="coach_login_pass")
        if st.button("登录", use_container_width=True, type="primary", key="coach_login_btn"):
            if username and password:
                success, msg = memory_system.login(username, password)
                if success:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("请输入用户名和密码")

    with tab2:
        new_user = st.text_input("用户名", key="coach_reg_user")
        new_pass = st.text_input("密码", type="password", key="coach_reg_pass")
        new_pass2 = st.text_input("确认密码", type="password", key="coach_reg_pass2")
        if st.button("注册", use_container_width=True, key="coach_reg_btn"):
            if new_user and new_pass:
                if new_pass != new_pass2:
                    st.error("两次密码不一致")
                elif len(new_pass) < 4:
                    st.error("密码至少 4 位")
                else:
                    success, msg = memory_system.register(new_user, new_pass)
                    if success:
                        st.success("注册成功！请登录")
                    else:
                        st.error(msg)
            else:
                st.warning("请填写完整信息")


def init_session_state():
    """初始化 session state"""
    defaults = {
        "coach_view": "home",
        "coach_sub_view": "",
        "coach_messages": [],
        "mood_log": [],
        "journal_entries": [],
        "personal_records": [],       # 综合记录（情绪记录、反思笔记、练习记录等）
        "growth_projects": [],  # 成长议题项目列表
        "growth_stage": 1,        # 兼容旧数据
        "growth_tasks_done": [],  # 兼容旧数据
        "emotion_tasks_done": [],
        "kb_favorites": [],           # 收藏的文章 id
        "kb_read": [],                # 已读的文章 id
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
    load_coach_data()


def save_coach_data():
    """持久化教练数据到用户目录（原子写入，防止多会话并发冲突）"""
    if not memory_system.current_user_id:
        return
    try:
        data = {
            "mood_log": st.session_state.mood_log,
            "journal_entries": st.session_state.journal_entries,
            "personal_records": st.session_state.personal_records,
            "growth_projects": st.session_state.growth_projects,
            "growth_stage": st.session_state.growth_stage,
            "growth_tasks_done": st.session_state.growth_tasks_done,
            "emotion_tasks_done": st.session_state.get("emotion_tasks_done", []),
            "kb_favorites": st.session_state.get("kb_favorites", []),
            "kb_read": st.session_state.get("kb_read", []),
            "coach_messages": st.session_state.coach_messages[-100:],  # 保存最近100条
        }
        user_dir = os.path.join(os.getenv("USER_DATA_PATH", "./data/users"), memory_system.current_user_id)
        os.makedirs(user_dir, exist_ok=True)
        coach_path = os.path.join(user_dir, "coach_data.json")
        # 原子写入：先写临时文件，再 os.replace（POSIX 原子操作）
        tmp_path = coach_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, coach_path)
    except Exception:
        pass


def load_coach_data():
    """从持久化加载教练数据"""
    if not memory_system.current_user_id:
        return
    try:
        user_dir = os.path.join(os.getenv("USER_DATA_PATH", "./data/users"), memory_system.current_user_id)
        path = os.path.join(user_dir, "coach_data.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("mood_log"):
                st.session_state.mood_log = data["mood_log"]
            if data.get("journal_entries"):
                st.session_state.journal_entries = data["journal_entries"]
            if data.get("personal_records"):
                st.session_state.personal_records = data["personal_records"]
            if data.get("growth_projects"):
                st.session_state.growth_projects = data["growth_projects"]
            elif data.get("growth_stage") or data.get("growth_tasks_done"):
                # 兼容旧数据：将旧的单项目进度迁移为项目
                old_project = {
                    "id": f"proj_migrated_{datetime.now().strftime('%Y%m%d%H%M')}",
                    "issue": "我的成长之旅",
                    "created_at": data.get("coach_messages", [["", "", ""]])[0][2] if data.get("coach_messages") else datetime.now().strftime("%Y-%m-%d"),
                    "stage": data.get("growth_stage", 1),
                    "tasks_done": data.get("growth_tasks_done", []),
                    "status": "active",
                }
                st.session_state.growth_projects = [old_project]
            if data.get("growth_stage"):
                st.session_state.growth_stage = data["growth_stage"]
            if data.get("growth_tasks_done"):
                st.session_state.growth_tasks_done = list(data["growth_tasks_done"])
            if data.get("emotion_tasks_done"):
                st.session_state["emotion_tasks_done"] = list(data["emotion_tasks_done"])
            if data.get("kb_favorites"):
                st.session_state["kb_favorites"] = list(data["kb_favorites"])
            if data.get("kb_read"):
                st.session_state["kb_read"] = list(data["kb_read"])
            if data.get("coach_messages"):
                st.session_state.coach_messages = data["coach_messages"]
    except Exception:
        pass


# ====================================
# 知识库完整数据
# ====================================

# 知识库分类体系


def get_articles_for_subcategory(cat_id, subcat_name):
    """获取某个子分类下的所有文章"""
    results = []
    for art_id, art in KB_ARTICLES.items():
        if art["category"] == cat_id and art["subcategory"] == subcat_name:
            results.append((art_id, art))
    return results


def get_articles_for_category(cat_id):
    """获取某个分类下的所有文章"""
    results = []
    for art_id, art in KB_ARTICLES.items():
        if art["category"] == cat_id:
            results.append((art_id, art))
    return results


# ====================================
# 成长路径 / 议题项目（数据 GROWTH_STAGES / TASK_ACTIONS / ISSUE_* 已移至 coach_content.py）
# ====================================

def get_project_stages(proj):
    """获取项目应使用的 stages（优先自定义，回退到默认）"""
    if proj.get("custom_stages"):
        return proj["custom_stages"]
    return GROWTH_STAGES


def get_project_total_tasks(proj):
    """获取项目的总任务数"""
    stages = get_project_stages(proj)
    return sum(len(s["tasks"]) for s in stages)


def generate_custom_stages(issue_text: str, issue_type: str):
    """根据议题类型从模板库生成个性化的6阶段任务"""
    template = ISSUE_STAGES_TEMPLATES.get(issue_type, None)
    if template:
        return template
    return None



# 教练对话引擎（情绪检测、安全分流、LLM、脚本兜底）已抽离到 coach_engine.py
# detect_emotion / detect_issue_type / generate_coach_response_v2 由顶部 import 引入。


def render_emotion_tasks():
    """渲染情绪教练任务面板"""
    st.markdown(f"""
    <div class="coach-hero-small">
        <h2>🎯 教练任务</h2>
        <p>根据你的情绪，完成这些小任务来帮助自己</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 从情绪记录推断当前主要情绪
    recent_moods = st.session_state.mood_log[-5:] if st.session_state.mood_log else []
    
    # 也从最近对话推断
    recent_msgs = st.session_state.coach_messages[-4:] if st.session_state.coach_messages else []
    detected_emotions = set()
    for msg in recent_msgs:
        if msg["role"] == "user":
            emo, _ = detect_emotion(msg["content"])
            if emo:
                detected_emotions.add(emo)
    
    # 推荐主要情绪的任务
    if detected_emotions:
        primary_emotion = list(detected_emotions)[-1]
        strategy = EMOTION_COACH_STRATEGIES.get(primary_emotion)
        if strategy:
            st.markdown(f'<div class="section-title">针对你的「{primary_emotion}」推荐任务</div>', unsafe_allow_html=True)
            
            # 从 session state 获取已完成的情绪任务
            emotion_tasks_done = st.session_state.get("emotion_tasks_done", [])
            
            for task in strategy.get("tasks", []):
                is_done = task["id"] in emotion_tasks_done
                type_icon = {"practice": "🧘", "reflect": "📝", "learn": "📖"}.get(task["type"], "📋")
                
                col1, col2, col3 = st.columns([0.6, 0.25, 0.15])
                with col1:
                    check = "✅" if is_done else "⬜"
                    st.markdown(f'{check} {type_icon} {task["text"]}', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div style="font-size:0.8rem;color:{THEME["text_light"]};padding-top:0.3rem;">约{task["duration"]}</div>', unsafe_allow_html=True)
                with col3:
                    if not is_done:
                        if st.button("完成", key=f"etask_{task['id']}", use_container_width=True):
                            emotion_tasks_done.append(task["id"])
                            st.session_state["emotion_tasks_done"] = emotion_tasks_done
                            save_coach_data()
                            st.success(f"太棒了！完成了一个任务 💚")
                            st.rerun()
    
    # 显示所有情绪的任务分类
    st.markdown(f'<div class="section-title">全部情绪任务</div>', unsafe_allow_html=True)
    
    emotion_tasks_done = st.session_state.get("emotion_tasks_done", [])
    
    for emo_name, strategy in EMOTION_COACH_STRATEGIES.items():
        with st.expander(f"{emo_name}（{len(strategy.get('tasks', []))}个任务）"):
            for task in strategy.get("tasks", []):
                is_done = task["id"] in emotion_tasks_done
                type_icon = {"practice": "🧘", "reflect": "📝", "learn": "📖"}.get(task["type"], "📋")
                
                if is_done:
                    st.markdown(f'✅ {type_icon} ~~{task["text"]}~~（已完成）')
                else:
                    col1, col2 = st.columns([0.85, 0.15])
                    with col1:
                        st.markdown(f'⬜ {type_icon} {task["text"]}')
                    with col2:
                        if st.button("完成", key=f"etask_all_{task['id']}", use_container_width=True):
                            emotion_tasks_done.append(task["id"])
                            st.session_state["emotion_tasks_done"] = emotion_tasks_done
                            save_coach_data()
                            st.rerun()


# ====================================
# 侧边栏
# ====================================
def render_sidebar():
    """人生教练侧边栏"""
    with st.sidebar:
        # 品牌区域
        st.markdown(f"""
        <div style="text-align:center;padding:1rem 0 0.5rem 0;">
            <div style="font-size:2rem;">🌿</div>
            <div style="font-size:1.2rem;font-weight:700;color:{THEME['primary']};">人生教练</div>
            <div style="font-size:0.8rem;color:{THEME['text_light']};margin-top:0.2rem;">陪伴你成长的 AI 伙伴</div>
        </div>
        """, unsafe_allow_html=True)

        # 返回 ABA 助手（整页跳回主应用；顶层锚点，同标签导航）
        # 带签名 token，主应用据此免密自动登录，回程不必重新登录
        from urllib.parse import quote as _quote
        from coach.coach_engine import coach_sso_token as _sso
        _aba_base = os.getenv("ABA_APP_URL", "http://localhost:8501").rstrip("/")
        _uname = memory_system.current_username or ""
        _atok = _sso(_uname) or ""
        _aba_url = f"{_aba_base}?user={_quote(_uname)}&token={_atok}" if _atok else _aba_base
        st.markdown(
            f'''<a href="{_aba_url}" target="_self" style="
                display:block; text-align:center; text-decoration:none;
                color:{THEME['primary']}; border:1px solid {THEME['primary']};
                padding:0.4rem 0.8rem; border-radius:8px; font-size:0.85rem;
                margin:0.3rem 0 0.5rem 0;
            ">← 返回 ABA 助手</a>''',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # 用户信息
        if memory_system.current_username:
            st.markdown(f'<div style="font-size:0.85rem;color:{THEME["text_secondary"]};">👤 {memory_system.current_username}</div>', unsafe_allow_html=True)
        st.markdown("---")

        # 导航
        st.markdown(f'<div style="font-size:0.75rem;color:{THEME["text_light"]};font-weight:600;margin-bottom:0.5rem;">导 航</div>', unsafe_allow_html=True)

        nav_items = [
            ("🏠", "首页", "home"),
            ("💬", "教练对话", "chat"),
            ("📚", "知识库", "knowledge"),
            ("🎯", "教练任务", "emotion_tasks"),
            ("😊", "情绪追踪", "emotion"),
            ("🌱", "成长路径", "growth"),
            ("📝", "我的记录", "journal"),
            ("📊", "进展报告", "report"),
        ]

        for icon, label, view in nav_items:
            is_active = st.session_state.coach_view == view
            btn_type = "primary" if is_active else "secondary"
            if st.button(f"{icon}  {label}", use_container_width=True, type=btn_type, key=f"nav_{view}"):
                st.session_state.coach_view = view
                st.session_state.coach_sub_view = ""
                st.rerun()

        st.markdown("---")

        # 退出登录
        if st.button("🚪 退出登录", use_container_width=True):
            memory_system.current_user_id = None
            memory_system.current_username = None
            st.session_state["logged_in"] = False
            st.session_state.coach_view = "home"
            st.rerun()

        st.markdown("---")
        st.markdown(f'<div style="font-size:0.75rem;color:{THEME["text_light"]};text-align:center;">人生教练 v0.2 · 温暖陪伴</div>', unsafe_allow_html=True)


# ====================================
# 首页
# ====================================
def render_home():
    """渲染人生教练首页"""
    china_tz = timezone(timedelta(hours=8))
    hour = datetime.now(china_tz).hour
    if hour < 6:
        greeting = "夜深了"
    elif hour < 9:
        greeting = "早上好"
    elif hour < 12:
        greeting = "上午好"
    elif hour < 14:
        greeting = "中午好"
    elif hour < 18:
        greeting = "下午好"
    else:
        greeting = "晚上好"

    username = memory_system.current_username or "朋友"
    mood_count = len(st.session_state.mood_log)
    records_count = len(st.session_state.personal_records)
    _all_done = []
    for _p in st.session_state.growth_projects:
        _all_done.extend(_p.get("tasks_done", []))
    tasks_done = len(set(_all_done)) if _all_done else len(st.session_state.growth_tasks_done)

    st.markdown(f"""
    <div class="coach-hero">
        <h1>{greeting}，{username} 🌿</h1>
        <p>在照顾孩子的同时，别忘了也照顾好自己。<br>我是你的人生教练，在这里陪你。</p>
    </div>
    """, unsafe_allow_html=True)

    # 今日概览统计
    st.markdown(f'<div class="section-title">你的成长足迹</div>', unsafe_allow_html=True)
    stat_cols = st.columns(3)
    with stat_cols[0]:
        st.markdown(f'''
        <div class="report-stat-card">
            <div style="font-size:1.5rem;">😊</div>
            <div class="report-stat-number">{mood_count}</div>
            <div class="report-stat-label">情绪记录</div>
        </div>
        ''', unsafe_allow_html=True)
    with stat_cols[1]:
        st.markdown(f'''
        <div class="report-stat-card">
            <div style="font-size:1.5rem;">🌱</div>
            <div class="report-stat-number">{tasks_done}</div>
            <div class="report-stat-label">任务完成</div>
        </div>
        ''', unsafe_allow_html=True)
    with stat_cols[2]:
        st.markdown(f'''
        <div class="report-stat-card">
            <div style="font-size:1.5rem;">📝</div>
            <div class="report-stat-number">{records_count}</div>
            <div class="report-stat-label">个人记录</div>
        </div>
        ''', unsafe_allow_html=True)

    # 每日建议
    st.markdown(get_coach_card(
        "💡 今日教练建议",
        "试着花 3 分钟做一次「呼吸空间」练习：先停下来，感受 5 次呼吸，觉察此刻的身体感受和情绪状态。不需要改变什么，只是简单地「在这里」。",
        card_type="orange", icon="🌅"
    ), unsafe_allow_html=True)

    # 快捷入口
    st.markdown(f'<div class="section-title">此刻你需要帮助的是…</div>', unsafe_allow_html=True)

    emotion_items = [
        ("😔 焦虑", "chat", "焦虑"), ("😢 悲伤", "chat", "悲伤"), ("😤 愤怒", "chat", "愤怒"),
        ("😩 疲惫", "chat", "累"), ("🤔 困惑", "chat", "迷茫"), ("🫂 孤独", "chat", "孤独"),
        ("😊 感恩", "chat", "感恩"),
    ]
    life_items = [
        ("💑 伴侣关系", "knowledge", "partner_1"), ("👨‍👩‍👧 家庭关系", "knowledge", "communication_1"),
        ("🤝 朋友社交", "knowledge", "lonely_1"), ("💼 工作与平衡", "knowledge", "work_balance_1"),
        ("🧘 自我认知", "knowledge", "self_grow_1"), ("🧠 核心理论", "knowledge", "acceptance_1"),
    ]
    body_items = [
        ("😴 睡眠", "knowledge", "sleep_1"), ("🏃 运动", "knowledge", "exercise_1"),
        ("💨 正念", "knowledge", "mindfulness_breath_1"), ("⏰ 习惯", "knowledge", "habits_1"),
    ]
    autism_items = [
        ("🧒 养育压力", "knowledge", "parenting_emotion_1"), ("🏪 公共场合", "knowledge", "public_1"),
        ("💡 自我关怀", "knowledge", "selfcare_parent_1"), ("🤝 支持网络", "knowledge", "network_1"),
    ]

    def render_quick_tags(items, tag_class):
        cols = st.columns(min(len(items), 4))
        for i, (label, view, art_kw) in enumerate(items):
            with cols[i % len(cols)]:
                if st.button(label, use_container_width=True, key=f"quick_{label}_{i}"):
                    st.session_state.coach_view = view
                    if view == "chat":
                        # 情绪快捷入口：发送消息到对话
                        st.session_state.coach_messages.append({"role": "user", "content": art_kw, "time": datetime.now().strftime("%m-%d %H:%M")})
                        response = generate_coach_response_v2(art_kw, st.session_state.coach_messages)
                        st.session_state.coach_messages.append({"role": "assistant", "content": response, "time": datetime.now().strftime("%m-%d %H:%M")})
                        save_coach_data()
                    else:
                        # 知识库快捷入口：跳转到对应文章
                        st.session_state.coach_sub_view = f"article_{art_kw}"
                    st.rerun()

    st.markdown('<div style="font-size:0.8rem;color:#636E72;font-weight:500;margin:0.8rem 0 0.5rem 0;">── 我的情绪 ──</div>', unsafe_allow_html=True)
    render_quick_tags(emotion_items, "emotion")
    st.markdown('<div style="font-size:0.8rem;color:#636E72;font-weight:500;margin:0.8rem 0 0.5rem 0;">── 生活 & 关系 & 知识 ──</div>', unsafe_allow_html=True)
    render_quick_tags(life_items + body_items, "life")
    st.markdown('<div style="font-size:0.8rem;color:#636E72;font-weight:500;margin:0.8rem 0 0.5rem 0;">── 自闭症养育 ──</div>', unsafe_allow_html=True)
    render_quick_tags(autism_items, "autism")

    # 核心功能入口
    st.markdown(f'<div class="section-title">常用功能</div>', unsafe_allow_html=True)
    func_cols = st.columns(3)
    with func_cols[0]:
        if st.button("💬 教练对话", use_container_width=True):
            st.session_state.coach_view = "chat"
            st.rerun()
    with func_cols[1]:
        if st.button("😊 记录心情", use_container_width=True):
            st.session_state.coach_view = "emotion"
            st.rerun()
    with func_cols[2]:
        if st.button("📊 查看报告", use_container_width=True):
            st.session_state.coach_view = "report"
            st.rerun()


# ====================================
# 教练对话
# ====================================
# generate_coach_response 旧版已被 generate_coach_response_v2 替代
# 保留旧函数名作为兼容
def generate_coach_response(user_input):
    """兼容旧版调用，委托给 v2"""
    return generate_coach_response_v2(user_input, st.session_state.get("coach_messages", []))


def render_chat():
    """教练对话界面 v2 — 带连贯性和教练方法论"""
    st.markdown(f"""
    <div class="coach-hero-small">
        <h2>💬 教练对话</h2>
        <p>说出你此刻的感受，我在这里倾听并陪伴你</p>
    </div>
    """, unsafe_allow_html=True)

    # 情绪快捷入口
    st.markdown(f'<div style="font-size:0.8rem;color:{THEME["text_secondary"]};margin-bottom:0.5rem;">此刻你的感受是…</div>', unsafe_allow_html=True)
    quick_moods = [
        ("😔", "焦虑"), ("😢", "想哭"), ("😤", "生气"),
        ("😩", "累了"), ("🤔", "迷茫"), ("😔", "自责"),
        ("🫂", "孤独"), ("😊", "还好"),
    ]
    mood_cols = st.columns(len(quick_moods))
    for i, (emoji, label) in enumerate(quick_moods):
        with mood_cols[i]:
            if st.button(f"{emoji} {label}", use_container_width=True, key=f"quick_mood_{i}"):
                msg_text = f"{label}"
                st.session_state.coach_messages.append({"role": "user", "content": msg_text, "time": datetime.now().strftime("%m-%d %H:%M")})
                response = generate_coach_response_v2(msg_text, st.session_state.coach_messages)
                st.session_state.coach_messages.append({"role": "assistant", "content": response, "time": datetime.now().strftime("%m-%d %H:%M")})
                save_coach_data()
                st.rerun()

    st.markdown("---")

    # 消息列表
    if not st.session_state.coach_messages:
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-emoji">🤗</div>
            <div class="empty-state-text">你可以告诉我任何此刻的感受<br>不需要组织语言，想到什么说什么就好</div>
            <div style="margin-top:1rem;font-size:0.85rem;color:{THEME['text_light']};">
                💡 我会根据教练方法来回应你，引导你自己思考和找到方向<br>
                对话是连贯的，我会记住我们聊过的内容
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg_idx, msg in enumerate(st.session_state.coach_messages):
            with st.chat_message(msg["role"]):
                # 检测是否有知识库推荐，渲染为可点击按钮
                content = msg["content"]
                kb_refs_marker = None
                if "__KB_REFS__:" in content:
                    parts = content.split("__KB_REFS__:")
                    display_content = parts[0]
                    kb_refs_marker = parts[1].strip() if len(parts) > 1 else None
                else:
                    display_content = content

                st.markdown(display_content)

                # 渲染知识库推荐按钮
                if kb_refs_marker and msg["role"] == "assistant":
                    ref_ids = [r.strip() for r in kb_refs_marker.split(",") if r.strip()]
                    for ref_id in ref_ids:
                        article = KB_ARTICLES.get(ref_id)
                        if article:
                            col1, col2 = st.columns([0.7, 0.3])
                            with col1:
                                st.markdown(f'<div style="font-size:0.85rem;padding:0.3rem 0;">📚 {article["title"]}</div>', unsafe_allow_html=True)
                            with col2:
                                if st.button("📖 阅读", key=f"kbref_{msg_idx}_{ref_id}", use_container_width=True):
                                    st.session_state.coach_view = "knowledge"
                                    st.session_state.coach_sub_view = f"article_{ref_id}"
                                    st.rerun()

                if msg.get("time"):
                    st.caption(msg["time"])

    # 输入框
    user_input = st.chat_input("说出你此刻的感受…")
    if user_input:
        st.session_state.coach_messages.append({"role": "user", "content": user_input, "time": datetime.now().strftime("%m-%d %H:%M")})
        response = generate_coach_response_v2(user_input, st.session_state.coach_messages)
        st.session_state.coach_messages.append({"role": "assistant", "content": response, "time": datetime.now().strftime("%m-%d %H:%M")})
        save_coach_data()
        st.rerun()


# ====================================
# 知识库（完整重写）
# ====================================
def render_knowledge():
    """知识库浏览与搜索"""
    st.markdown(f"""
    <div class="coach-hero-small">
        <h2>📚 人生教练知识库</h2>
        <p>在这里查找任何你感兴趣的话题</p>
    </div>
    """, unsafe_allow_html=True)

    # 检查是否有从成长任务跳转过来的文章
    kb_open = st.session_state.pop("kb_open_article", None)
    if kb_open and KB_ARTICLES.get(kb_open):
        st.markdown(f'<div style="background:{THEME["primary_light"]};border-radius:8px;padding:0.5rem 1rem;margin-bottom:0.8rem;font-size:0.85rem;color:{THEME["primary"]};">📖 来自成长任务推荐的文章</div>', unsafe_allow_html=True)
        render_article(kb_open)
        return

    # 搜索
    search_query = st.text_input("🔍 搜索知识库", placeholder="输入关键词，如：焦虑、接纳、正念、睡眠…", key="kb_search")

    if search_query:
        render_search_results(search_query)
        return

    # 子视图路由
    sub_view = st.session_state.coach_sub_view

    if sub_view and sub_view.startswith("article_"):
        render_article(sub_view.replace("article_", ""))
        return

    if sub_view and sub_view.startswith("cat_"):
        # cat_methodology_接纳
        parts = sub_view.replace("cat_", "").split("_", 1)
        if len(parts) == 2:
            render_subcategory_articles(parts[0], parts[1])
            return
        else:
            render_category_detail(parts[0])
            return

    # 展示分类列表
    st.markdown(f'<div class="section-title">知识领域（{len(KB_ARTICLES)} 篇文章）</div>', unsafe_allow_html=True)

    for cat in KB_CATEGORIES:
        # 计算该分类的文章数
        article_count = len(get_articles_for_category(cat["id"]))

        cols = st.columns([0.08, 0.72, 0.20])
        with cols[0]:
            st.markdown(f'<div style="font-size:1.5rem;text-align:center;padding-top:0.3rem;">{cat["icon"]}</div>', unsafe_allow_html=True)
        with cols[1]:
            color_var = THEME.get(cat["color"] + "_light", THEME["primary_light"])
            st.markdown(f'''
            <div class="kb-category" style="border-left:3px solid {color_var};">
                <div style="font-weight:600;">{cat["name"]}</div>
                <div style="font-size:0.8rem;color:{THEME["text_secondary"]};">{cat["desc"]}</div>
            </div>
            ''', unsafe_allow_html=True)
        with cols[2]:
            if st.button(f"查看 {article_count}篇", use_container_width=True, key=f"cat_btn_{cat['id']}"):
                st.session_state.coach_sub_view = f"cat_{cat['id']}"
                st.rerun()

    # 推荐阅读
    st.markdown(f'<div class="section-title">推荐阅读</div>', unsafe_allow_html=True)
    recommended = ["acceptance_1", "mindfulness_breath_1", "anxiety_1", "selfcare_parent_1", "defusion_1"]
    for art_id in recommended:
        article = KB_ARTICLES.get(art_id)
        if not article:
            continue
        # 提取摘要
        summary = article.get("summary", article["content"].split("\n")[2][:60] + "…")
        st.markdown(get_kb_item_html(
            article["title"],
            summary,
            f"{get_badge(article['level'], 'green')} · {article['read_time']}",
            "green"
        ), unsafe_allow_html=True)
        if st.button("📖 阅读全文", key=f"read_{art_id}"):
            st.session_state.coach_sub_view = f"article_{art_id}"
            st.rerun()


def render_category_detail(cat_id):
    """展示知识库分类详情（含子分类链接）"""
    cat = next((c for c in KB_CATEGORIES if c["id"] == cat_id), None)
    if not cat:
        st.session_state.coach_sub_view = ""
        st.rerun()
        return

    if st.button("← 返回知识库", key="back_kb"):
        st.session_state.coach_sub_view = ""
        st.rerun()

    st.markdown(f'<div style="font-size:1.5rem;font-weight:700;color:{THEME["text_primary"]};margin-bottom:0.3rem;">{cat["icon"]} {cat["name"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.9rem;color:{THEME["text_secondary"]};margin-bottom:1rem;">{cat["desc"]}</div>', unsafe_allow_html=True)

    # 子分类（可点击）
    for child in cat.get("children", []):
        articles = get_articles_for_subcategory(cat_id, child["name"].split("（")[0].split("/")[0].strip())
        article_count = len(articles)

        st.markdown(f'''
        <div class="subcategory-card">
            <div style="display:flex;align-items:center;gap:0.5rem;">
                <span style="font-size:1.2rem;">{child["icon"]}</span>
                <div style="flex:1;">
                    <div style="font-weight:600;font-size:0.95rem;">{child["name"]}</div>
                    <div style="font-size:0.8rem;color:{THEME["text_secondary"]};">{child["desc"]} · {article_count} 篇</div>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        # 如果有文章，列出
        if articles:
            for art_id, art in articles:
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    st.markdown(f'''
                    <div style="font-size:0.88rem;color:{THEME["text_primary"]};margin:0.3rem 0 0 2rem;">
                        📄 {art["title"]}
                        <span style="font-size:0.75rem;color:{THEME["text_light"]};"> · {art["read_time"]}</span>
                    </div>
                    ''', unsafe_allow_html=True)
                with col2:
                    if st.button("阅读", key=f"subcat_{art_id}", use_container_width=True):
                        st.session_state.coach_sub_view = f"article_{art_id}"
                        st.rerun()
        else:
            st.markdown(f'<div style="font-size:0.8rem;color:{THEME["text_light"]};margin:0.2rem 0 0.5rem 2rem;">暂无文章，内容建设中…</div>', unsafe_allow_html=True)

        st.markdown("")  # 间距


def render_subcategory_articles(cat_id, subcat_name):
    """展示某个子分类的文章列表"""
    articles = get_articles_for_subcategory(cat_id, subcat_name)
    cat = next((c for c in KB_CATEGORIES if c["id"] == cat_id), None)

    if st.button(f"← 返回 {cat['name'] if cat else '知识库'}", key="back_subcat"):
        st.session_state.coach_sub_view = f"cat_{cat_id}"
        st.rerun()

    # 也显示该分类下的所有文章
    if not articles:
        articles = [(aid, a) for aid, a in KB_ARTICLES.items() if a["category"] == cat_id and subcat_name in a.get("subcategory", "")]

    st.markdown(f'<div style="font-size:1.1rem;font-weight:600;color:{THEME["text_primary"]};margin-bottom:0.5rem;">{subcat_name}</div>', unsafe_allow_html=True)

    for art_id, art in articles:
        st.markdown(get_kb_item_html(
            art["title"],
            art.get("summary", ""),
            f"{get_badge(art['level'], 'green')} · {art['read_time']}",
            "green"
        ), unsafe_allow_html=True)
        if st.button("📖 阅读全文", key=f"subart_{art_id}"):
            st.session_state.coach_sub_view = f"article_{art_id}"
            st.rerun()

    if not articles:
        st.markdown(f'''
        <div class="empty-state">
            <div class="empty-state-emoji">📝</div>
            <div class="empty-state-text">该分类暂无文章<br>内容正在建设中</div>
        </div>
        ''', unsafe_allow_html=True)


def render_search_results(query):
    """展示搜索结果"""
    if st.button("← 返回知识库", key="back_search"):
        st.session_state.coach_sub_view = ""
        st.rerun()

    st.markdown(f'<div style="font-size:1rem;color:{THEME["text_secondary"]};margin-bottom:1rem;">搜索："{query}" 的结果</div>', unsafe_allow_html=True)

    results = []
    for art_id, article in KB_ARTICLES.items():
        if query in article["title"] or query in article.get("category", "") or query in article.get("subcategory", "") or query in article.get("summary", "") or query in article["content"]:
            results.append((art_id, article))

    if not results:
        st.markdown(f'''
        <div class="empty-state">
            <div class="empty-state-emoji">🔍</div>
            <div class="empty-state-text">暂未找到与"{query}"相关的内容<br>知识库正在持续扩充中</div>
        </div>
        ''', unsafe_allow_html=True)
    else:
        for art_id, article in results:
            st.markdown(get_kb_item_html(
                article["title"],
                article.get("summary", article["content"].split("\n")[2][:50]),
                f"{get_badge(article['level'], 'green')} · {article['category']} · {article['read_time']}"
            ), unsafe_allow_html=True)
            if st.button("📖 阅读全文", key=f"search_read_{art_id}"):
                st.session_state.coach_sub_view = f"article_{art_id}"
                st.rerun()


def _ask_coach_about_article(article, intent_msg):
    """从文章页跳到教练对话，并立刻生成一条结合本文的回应。"""
    st.session_state.coach_messages.append({
        "role": "user",
        "content": intent_msg,
        "time": datetime.now().strftime("%m-%d %H:%M"),
    })
    context = f"《{article['title']}》\n{article.get('content', '')}"
    resp = generate_coach_response_v2(
        intent_msg, st.session_state.coach_messages, extra_context=context
    )
    st.session_state.coach_messages.append({
        "role": "assistant",
        "content": resp,
        "time": datetime.now().strftime("%m-%d %H:%M"),
    })
    st.session_state.coach_view = "chat"
    st.session_state.coach_sub_view = ""
    save_coach_data()
    st.rerun()


def _related_articles(art_id, article, limit=4):
    """同子分类优先、再同大类，给出相关文章 [(id, art)]，不含自己。"""
    same_sub = [(i, a) for i, a in get_articles_for_subcategory(article["category"], article["subcategory"]) if i != art_id]
    same_cat = [(i, a) for i, a in get_articles_for_category(article["category"]) if i != art_id and (i, a) not in same_sub]
    seen, out = set(), []
    for i, a in same_sub + same_cat:
        if i not in seen:
            seen.add(i)
            out.append((i, a))
        if len(out) >= limit:
            break
    return out


def render_article(art_id):
    """展示知识条目详情"""
    article = KB_ARTICLES.get(art_id)
    if not article:
        st.session_state.coach_sub_view = ""
        st.rerun()
        return

    # 打开即标记为已读
    if art_id not in st.session_state.get("kb_read", []):
        st.session_state.setdefault("kb_read", []).append(art_id)
        save_coach_data()

    if st.button("← 返回知识库", key="back_article"):
        st.session_state.coach_sub_view = ""
        st.rerun()

    # 文章头部
    st.markdown(f'''
    <div style="margin-bottom:0.6rem;">
        <div style="font-size:1.3rem;font-weight:700;color:{THEME["text_primary"]};">{article["title"]}</div>
        <div style="font-size:0.8rem;color:{THEME["text_light"]};margin-top:0.3rem;">
            {get_badge(article["level"], "green")} · {article["read_time"]} · ✓ 已读
        </div>
    </div>
    ''', unsafe_allow_html=True)
    if article.get("summary"):
        st.markdown(
            f'<div style="font-size:0.95rem;color:{THEME["text_secondary"]};font-style:italic;'
            f'border-left:3px solid {THEME["primary_light"]};padding-left:0.8rem;margin-bottom:1rem;">'
            f'{article["summary"]}</div>', unsafe_allow_html=True)

    # 文章内容（用漂亮的卡片包裹）
    st.markdown(f'<div class="article-content">', unsafe_allow_html=True)
    st.markdown(article["content"])
    st.markdown('</div>', unsafe_allow_html=True)

    # === 让教练结合这篇文章帮我（C）===
    st.markdown(f'<div class="section-title">💬 让教练陪我把这篇用起来</div>', unsafe_allow_html=True)
    coach_cols = st.columns(3)
    with coach_cols[0]:
        if st.button("💡 结合我的情况举个例子", use_container_width=True, key=f"coach_eg_{art_id}"):
            _ask_coach_about_article(article, f"我刚读了《{article['title']}》。能结合我作为家长的处境，给我举一个具体、贴近生活的例子吗？")
    with coach_cols[1]:
        if st.button("🧘 带我做一次这个练习", use_container_width=True, key=f"coach_do_{art_id}"):
            _ask_coach_about_article(article, f"我刚读了《{article['title']}》。请像教练一样，一步一步带我现在做一次里面的练习。")
    with coach_cols[2]:
        if st.button("🔄 没太懂，换个说法讲", use_container_width=True, key=f"coach_re_{art_id}"):
            _ask_coach_about_article(article, f"《{article['title']}》这篇我没太看懂。能用更简单、更口语的方式，重新讲讲核心意思吗？")

    # === 底部操作（A：真正可用）===
    st.markdown("---")
    favs = st.session_state.setdefault("kb_favorites", [])
    is_fav = art_id in favs
    action_cols = st.columns(2)
    with action_cols[0]:
        if st.button("⭐ 已收藏" if is_fav else "🔖 收藏", use_container_width=True, key=f"fav_{art_id}"):
            if is_fav:
                favs.remove(art_id)
            else:
                favs.append(art_id)
            save_coach_data()
            st.rerun()
    with action_cols[1]:
        if st.button("💬 和教练自由聊聊这个话题", use_container_width=True, key=f"chat_{art_id}"):
            _ask_coach_about_article(article, f"我刚读了《{article['title']}》，想和你聊聊我的感受。")

    # === 相关文章 + 上/下一篇（A）===
    related = _related_articles(art_id, article)
    if related:
        st.markdown(f'<div class="section-title">📎 相关文章</div>', unsafe_allow_html=True)
        for rid, rart in related:
            read_mark = "✓ " if rid in st.session_state.get("kb_read", []) else ""
            col1, col2 = st.columns([0.78, 0.22])
            with col1:
                st.markdown(
                    f'<div style="padding:0.35rem 0;">{read_mark}<strong>{rart["title"]}</strong>'
                    f'<span style="font-size:0.8rem;color:{THEME["text_light"]};"> · {rart["read_time"]}</span><br>'
                    f'<span style="font-size:0.82rem;color:{THEME["text_secondary"]};">{rart.get("summary", "")}</span></div>',
                    unsafe_allow_html=True)
            with col2:
                if st.button("阅读 →", use_container_width=True, key=f"rel_{art_id}_{rid}"):
                    st.session_state.coach_sub_view = f"article_{rid}"
                    st.rerun()


# ====================================
# 情绪追踪
# ====================================
def render_emotion():
    """情绪追踪页面 — 记录并理解你的情绪变化"""
    st.markdown(f"""
    <div class="coach-hero-small">
        <h2>😊 情绪追踪</h2>
        <p>记录情绪不是目的，看见自己的模式才是</p>
    </div>
    """, unsafe_allow_html=True)

    # 初始化状态
    if "emotion_selected" not in st.session_state:
        st.session_state.emotion_selected = None
    if "emotion_just_saved" not in st.session_state:
        st.session_state.emotion_just_saved = False

    # 解释意义
    with st.expander("🤔 为什么要记录情绪？", expanded=(len(st.session_state.mood_log) == 0)):
        st.markdown(f'''
        <div style="font-size:0.9rem;line-height:1.8;color:{THEME["text_primary"]};">
            作为孩子的家长，你每天都在经历各种情绪——焦虑、疲惫、自责、偶尔的喜悦。
            这些情绪往往是<strong>自动发生的</strong>，你可能没来得及注意到就已经被影响了。<br><br>
            情绪追踪的价值在于：<br>
            <strong>1. 发现模式</strong> —— 哪些情境最容易触发焦虑？疲劳和情绪之间有关联吗？<br>
            <strong>2. 提前预警</strong> —— 当你开始注意到连续几天情绪下滑，可以提前采取措施<br>
            <strong>3. 看见变化</strong> —— 回顾时你会发现，原来自己比想象中更坚强<br>
            <strong>4. 和教练对话的线索</strong> —— 你的情绪记录帮助教练更准确地理解你的状态<br><br>
            <em>你只需要选一个心情，写一两句话就好。不需要长篇大论，诚实最重要。</em>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("---")

    # === 新建情绪记录 ===
    st.markdown(f'<div class="section-title">记录此刻的心情</div>', unsafe_allow_html=True)

    # 显示保存成功提示
    if st.session_state.emotion_just_saved:
        st.success(f"情绪记录已保存 💚")
        st.session_state.emotion_just_saved = False

    # 情绪选择 — 用 selectbox 代替 button，避免 rerun 丢失状态
    mood_options = [(emoji, label) for emoji, label in MOOD_EMOJIS.items()]
    mood_labels = [f"{emoji}  {label}" for emoji, label in mood_options]

    selected_index = st.selectbox(
        "选择你现在的心情",
        range(len(mood_options)),
        format_func=lambda i: mood_labels[i],
        key="emotion_mood_select",
        label_visibility="collapsed",
    )

    if selected_index is not None:
        selected_mood = mood_options[selected_index]

        # 详细记录表单
        detail_cols = st.columns(2)
        with detail_cols[0]:
            trigger = st.text_input("发生了什么？（触发事件）", placeholder="如：带孩子去超市，他突然大哭...", key="emotion_trigger")
            intensity = st.slider("情绪强度", 1, 10, 5, key="emotion_intensity",
                                  help="1=很轻微，10=非常强烈")
        with detail_cols[1]:
            body_feeling = st.text_input("身体的感受", placeholder="如：心跳加速、肩膀紧绷、胃不舒服...", key="emotion_body")
            thought = st.text_input("当时的想法", placeholder="如：别人都在看我，我是不是做错了...", key="emotion_thought")

        note = st.text_area("想补充的话（可选）", height=60, placeholder="任何你想记录的...", key="emotion_note")

        save_cols = st.columns([0.7, 0.3])
        with save_cols[1]:
            if st.button("✅ 保存记录", use_container_width=True, type="primary", key="save_mood"):
                entry = {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "emoji": selected_mood[0],
                    "label": selected_mood[1],
                    "score": MOOD_SCORES.get(selected_mood[0], 4),
                    "intensity": intensity,
                    "trigger": trigger,
                    "body_feeling": body_feeling,
                    "thought": thought,
                    "note": note,
                }
                st.session_state.mood_log.append(entry)
                # 同时存一份到综合记录
                st.session_state.personal_records.append({
                    "id": f"emo_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "type": "情绪记录",
                    "type_icon": "😊",
                    "time": entry["time"],
                    "title": f"{selected_mood[0]} {selected_mood[1]}（强度{intensity}/10）",
                    "content": f"触发：{trigger or '未记录'}\n身体感受：{body_feeling or '未记录'}\n想法：{thought or '未记录'}",
                    "emoji": selected_mood[0],
                    "mood_score": entry["score"],
                })
                save_coach_data()
                st.session_state.emotion_just_saved = True
                st.rerun()

    st.markdown("---")

    # === 历史记录 & 趋势分析 ===
    st.markdown(f'<div class="section-title">情绪历史与趋势</div>', unsafe_allow_html=True)

    if not st.session_state.mood_log:
        st.markdown(f'''
        <div class="empty-state">
            <div class="empty-state-emoji">📝</div>
            <div class="empty-state-text">还没有记录<br>选一个心情，开始你的第一次记录吧</div>
        </div>
        ''', unsafe_allow_html=True)
    else:
        # 趋势摘要
        mood_log = st.session_state.mood_log
        total = len(mood_log)
        avg_score = sum(m.get("score", 4) for m in mood_log) / total
        avg_intensity = sum(m.get("intensity", 5) for m in mood_log) / total

        # 最常见的触发
        triggers = [m.get("trigger", "").strip() for m in mood_log if m.get("trigger", "").strip()]
        trigger_counts = {}
        for t in triggers:
            # 归类相似触发
            t_short = t[:15] + ("..." if len(t) > 15 else "")
            trigger_counts[t_short] = trigger_counts.get(t_short, 0) + 1
        top_triggers = sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        # 最常见的想法模式
        thoughts = [m.get("thought", "").strip() for m in mood_log if m.get("thought", "").strip()]

        # 最近的趋势
        if total >= 3:
            recent_3 = mood_log[-3:]
            recent_avg = sum(m.get("score", 4) for m in recent_3) / 3
            if recent_avg > avg_score + 0.5:
                trend_text = "📈 最近情绪在好转"
                trend_color = THEME["calm"]
            elif recent_avg < avg_score - 0.5:
                trend_text = "📉 最近情绪有些下滑，建议和教练聊聊"
                trend_color = THEME["accent"]
            else:
                trend_text = "➡️ 情绪比较稳定"
                trend_color = THEME["primary"]
        else:
            trend_text = "📊 继续记录，就能看到趋势变化"
            trend_color = THEME["text_secondary"]

        # 展示分析摘要
        st.markdown(f'''
        <div style="background:white;border-radius:12px;padding:1rem 1.25rem;box-shadow:0 2px 8px {THEME["shadow"]};margin-bottom:1rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
                <span style="font-weight:600;color:{THEME["text_primary"]};">共 {total} 次记录</span>
                <span style="font-size:0.85rem;color:{trend_color};font-weight:500;">{trend_text}</span>
            </div>
            <div style="display:flex;gap:1.5rem;margin-top:0.5rem;flex-wrap:wrap;">
                <span style="font-size:0.85rem;color:{THEME["text_secondary"]};">平均心情：<strong>{avg_score:.1f}</strong>/7</span>
                <span style="font-size:0.85rem;color:{THEME["text_secondary"]};">平均强度：<strong>{avg_intensity:.1f}</strong>/10</span>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        # 触发模式分析
        if top_triggers:
            st.markdown(f'<div style="font-size:0.9rem;font-weight:600;color:{THEME["text_primary"]};margin-bottom:0.5rem;">🔍 常见情绪触发</div>', unsafe_allow_html=True)
            for trigger_text, count in top_triggers:
                st.markdown(f'<div style="font-size:0.85rem;color:{THEME["text_secondary"]};margin-bottom:0.3rem;padding-left:0.5rem;border-left:2px solid {THEME["primary_light"]};">"{trigger_text}" 出现 {count} 次</div>', unsafe_allow_html=True)

            st.markdown("")

        # 情绪时间线（最近20条）
        display_count = min(20, len(mood_log))
        st.markdown(f'<div style="font-size:0.9rem;font-weight:600;color:{THEME["text_primary"]};margin-bottom:0.5rem;">📋 最近记录</div>', unsafe_allow_html=True)

        for entry in reversed(mood_log[-display_count:]):
            intensity_bar = entry.get("intensity", 5)
            bar_color = THEME["warm"] if intensity_bar >= 8 else THEME["accent"] if intensity_bar >= 6 else THEME["primary"]
            trigger_text = entry.get("trigger", "")
            thought_text = entry.get("thought", "")

            st.markdown(f'''
            <div class="journal-entry">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div class="journal-entry-date">{entry["time"]}</div>
                    <div style="display:flex;align-items:center;gap:0.3rem;">
                        <span style="font-size:0.75rem;color:{THEME["text_light"]};">强度</span>
                        <div style="width:50px;height:6px;background:{THEME["border"]};border-radius:3px;overflow:hidden;">
                            <div style="width:{intensity_bar*10}%;height:100%;background:{bar_color};border-radius:3px;"></div>
                        </div>
                        <span style="font-size:0.75rem;color:{THEME["text_light"]};">{intensity_bar}/10</span>
                    </div>
                </div>
                <div class="journal-entry-content">
                    {entry["emoji"]} <strong>{entry["label"]}</strong>
                    {f' · 触发：{trigger_text}' if trigger_text else ""}
                    {f' · 想法：{thought_text}' if thought_text else ""}
                    {f' · {entry.get("note", "")}' if entry.get("note") else ""}
                </div>
            </div>
            ''', unsafe_allow_html=True)


# ====================================
# 成长路径
# ====================================
def render_growth():
    """成长路径页面 — ACT 六大核心过程 + 议题驱动的成长项目"""
    st.markdown(f"""
    <div class="coach-hero-small">
        <h2>🌱 成长路径</h2>
        <p>选择一个困扰你的议题，通过 ACT 六大核心过程逐步成长</p>
    </div>
    """, unsafe_allow_html=True)

    # ACT 六大核心过程说明
    with st.expander("🧠 了解 ACT 六大核心过程 — 为什么要有这 6 个阶段？", expanded=False):
        act_html = f'''
        <div style="font-size:0.88rem;line-height:1.9;color:{THEME["text_primary"]};">
            <p style="margin-bottom:1rem;">
            ACT（接纳承诺疗法）是现代心理教练中最有科学验证的方法之一。
            它的核心思想很简单：<strong>痛苦无法消除，但你可以选择为重要的事而行动。</strong>
            ACT 有六个相互关联的核心过程，像一个六边形的六个角，共同帮助你实现"心理灵活性"。
            </p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;margin:1rem 0;">
                <div style="background:{THEME["primary_light"]};border-radius:8px;padding:0.7rem 0.9rem;">
                    <strong>1. 接纳 Acceptance</strong><br>
                    <span style="font-size:0.82rem;">不是"放弃"，而是<strong>主动为不舒适的感觉腾出空间</strong>。当你越想消灭焦虑，焦虑反而越强。接纳是停止和自己的感受对抗。</span>
                </div>
                <div style="background:#FFF3E0;border-radius:8px;padding:0.7rem 0.9rem;">
                    <strong>2. 认知解离 Defusion</strong><br>
                    <span style="font-size:0.82rem;">你的想法不等于事实。<strong>"我是一个糟糕的家长"只是一个想法，不是现实。</strong>解离帮你和想法拉开距离，不再被它们绑架。</span>
                </div>
                <div style="background:#E8F5E9;border-radius:8px;padding:0.7rem 0.9rem;">
                    <strong>3. 当下觉察 Present</strong><br>
                    <span style="font-size:0.82rem;">焦虑是对未来的，后悔是对过去的。<strong>当下是你唯一能行动的地方。</strong>正念训练帮你回到"此时此地"，不被思绪裹走。</span>
                </div>
                <div style="background:#F3E5F5;border-radius:8px;padding:0.7rem 0.9rem;">
                    <strong>4. 观察者自我 Self-as-Context</strong><br>
                    <span style="font-size:0.82rem;">你不是你的想法，也不是你的情绪。<strong>你是那个"观察"想法和情绪的存在。</strong>当你能退后一步观察自己，就会获得更大的空间和自由。</span>
                </div>
                <div style="background:#E3F2FD;border-radius:8px;padding:0.7rem 0.9rem;">
                    <strong>5. 价值观 Values</strong><br>
                    <span style="font-size:0.82rem;">什么对你真正重要？<strong>价值观是你想成为的家长、想拥有的关系、想活出的人生。</strong>不是目标（可以达成），而是方向（永远指向前方）。</span>
                </div>
                <div style="background:#FFF8E1;border-radius:8px;padding:0.7rem 0.9rem;">
                    <strong>6. 承诺行动 Committed Action</strong><br>
                    <span style="font-size:0.82rem;">知道价值观不够，需要<strong>即使带着痛苦也朝价值观方向行动</strong>。行动是连接"你知道的"和"你活出来的"之间的桥梁。</span>
                </div>
            </div>
            <p style="margin-top:1rem;padding:0.6rem;background:#F0F4F0;border-radius:6px;font-size:0.82rem;">
            💡 <strong>为什么要围绕一个"议题"？</strong><br>
            在 ACT 教练中，你不需要一次性解决所有问题。选择一个当前最困扰你的议题（比如"孩子发脾气时的焦虑"或"社交场合的不自在"），围绕这个议题走完六个阶段。完成一个议题后，你会发现自己有了新的心理灵活性，再面对下一个议题时会更加从容。
            </p>
        </div>
        '''
        st.markdown(act_html, unsafe_allow_html=True)

    st.markdown("---")

    projects = st.session_state.growth_projects
    active_project = None
    for p in projects:
        if p["status"] == "active":
            active_project = p
            break

    if not projects:
        st.markdown(f'''
        <div style="text-align:center;padding:2rem 1rem;">
            <div style="font-size:3rem;margin-bottom:1rem;">🌱</div>
            <div style="font-size:1.1rem;font-weight:600;color:{THEME["text_primary"]};margin-bottom:0.5rem;">开始你的第一个成长议题</div>
            <div style="font-size:0.9rem;color:{THEME["text_secondary"]};max-width:500px;margin:0 auto;">
                选择一个当前最困扰你的具体议题，系统会围绕这个议题为你定制 6 个 ACT 阶段的练习和任务。
            </div>
        </div>
        ''', unsafe_allow_html=True)

    # 已完成项目
    completed_projects = [p for p in projects if p["status"] == "completed"]
    if completed_projects:
        with st.expander(f"🏆 已完成的议题（{len(completed_projects)}个）"):
            for p in completed_projects:
                total_t = get_project_total_tasks(p)
                done_t = len(p.get("tasks_done", []))
                st.markdown(f'''
                <div style="display:flex;justify-content:space-between;align-items:center;padding:0.4rem 0;border-bottom:1px solid {THEME["border"]};">
                    <div>
                        <span style="font-weight:500;color:{THEME["text_primary"]};">{p["issue"]}</span>
                        <span style="font-size:0.8rem;color:{THEME["text_secondary"]};margin-left:0.5rem;">{done_t}/{total_t} 任务</span>
                    </div>
                    <span style="font-size:0.8rem;color:{THEME["calm"]};">{p.get("created_at", "")}</span>
                </div>
                ''', unsafe_allow_html=True)

    # 没有活跃项目时显示创建表单
    if not active_project:
        st.markdown(f'<div class="section-title">创建新的成长议题</div>', unsafe_allow_html=True)
        st.markdown(f'''
        <div style="background:white;border-radius:10px;padding:1rem 1.2rem;box-shadow:0 2px 8px {THEME["shadow"]};">
            <div style="font-size:0.88rem;color:{THEME["text_secondary"]};margin-bottom:0.8rem;">
                选择一个当前最困扰你的具体情境或问题。越具体越好，比如：
            </div>
            <div style="font-size:0.82rem;color:{THEME["text_light"]};margin-bottom:1rem;">
                「孩子在外面突然哭闹时我的焦虑」「带孩子看医生前的紧张」「感到作为家长永远不够好」
            </div>
        </div>
        ''', unsafe_allow_html=True)

        issue_input = st.text_input("描述你的议题", placeholder="比如：孩子在公共场所发脾气时我感到的焦虑和无力感...", key="new_project_issue", label_visibility="collapsed")

        if issue_input and st.button("🌱 开启成长之旅", type="primary", use_container_width=True, key="create_project"):
            issue_text = issue_input.strip()
            issue_type = detect_issue_type(issue_text)
            custom_stages = generate_custom_stages(issue_text, issue_type)
            new_proj = {
                "id": f"proj_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "issue": issue_text,
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "stage": 1,
                "tasks_done": [],
                "status": "active",
                "issue_type": issue_type,
                "custom_stages": custom_stages,
            }
            st.session_state.growth_projects.append(new_proj)
            st.session_state.growth_stage = 1
            st.session_state.growth_tasks_done = []
            save_coach_data()
            st.session_state.personal_records.append({
                "id": f"rec_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "type": "目标/计划",
                "type_icon": "🎯",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "title": f"开始新议题：{issue_text}",
                "content": f"成长议题：{issue_text}\n议题类型：{issue_type}\n{'已为你生成个性化练习路径' if custom_stages else '使用通用练习路径'}\n目标：通过 ACT 六个阶段找到面对这个议题的新方式。",
                "emoji": "🌱",
            })
            save_coach_data()
            st.rerun()

    else:
        # 有活跃项目：显示议题进度 + 六阶段
        proj = active_project
        current_stage = proj["stage"]
        proj_tasks_done = proj.get("tasks_done", [])
        issue_text = proj["issue"]

        # 项目头部卡片
        st.markdown(f'''
        <div style="background:white;border-radius:12px;padding:1rem 1.25rem;box-shadow:0 2px 8px {THEME["shadow"]};margin-bottom:1rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;">
                <div>
                    <div style="font-size:0.8rem;color:{THEME["text_light"]};">当前议题</div>
                    <div style="font-weight:600;font-size:1.05rem;color:{THEME["text_primary"]};">「{proj["issue"]}」</div>
                </div>
                <div style="font-size:0.8rem;color:{THEME["text_secondary"]};">创建于 {proj.get("created_at", "")}</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        # 获取项目的个性化 stages
        proj_stages = get_project_stages(proj)

        total_tasks = get_project_total_tasks(proj)
        done_tasks = len(proj_tasks_done)
        progress_pct = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # 个性化标签
        issue_type_label = proj.get("issue_type", "default")
        type_badge = ""
        if issue_type_label and issue_type_label != "default":
            type_badge_map = {
                "焦虑": "🟡 焦虑方向", "自责": "🟠 自责方向", "疲惫": "🔴 疲惫方向",
                "社交": "🔵 社交方向", "亲子关系": "🟢 亲子关系方向",
            }
            type_badge = f'<span style="font-size:0.78rem;background:{THEME["primary_light"]};border-radius:4px;padding:0.15rem 0.5rem;margin-left:0.5rem;">{type_badge_map.get(issue_type_label, issue_type_label)}</span>'

        st.markdown(f'''
        <div style="background:white;border-radius:12px;padding:1rem 1.25rem;box-shadow:0 2px 8px {THEME["shadow"]};margin-bottom:1rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;">
                <div>
                    <div style="font-size:0.8rem;color:{THEME["text_light"]};">当前议题</div>
                    <div style="font-weight:600;font-size:1.05rem;color:{THEME["text_primary"]};">「{proj["issue"]}」{type_badge}</div>
                </div>
                <div style="font-size:0.8rem;color:{THEME["text_secondary"]};">创建于 {proj.get("created_at", "")}</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown(f'''
        <div style="background:white;border-radius:12px;padding:1rem 1.25rem;box-shadow:0 2px 8px {THEME["shadow"]};margin-bottom:1rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                <span style="font-weight:600;color:{THEME["text_primary"]};">议题进度</span>
                <span style="font-size:0.85rem;color:{THEME["text_secondary"]};">{done_tasks}/{total_tasks} 已完成</span>
            </div>
            {get_progress_bar(progress_pct)}
        </div>
        ''', unsafe_allow_html=True)

        for stage in proj_stages:
            stage_num = stage["id"]
            stage_tasks = stage["tasks"]
            stage_done = sum(1 for t in stage_tasks if t["id"] in proj_tasks_done)
            stage_pct = (stage_done / len(stage_tasks) * 100) if stage_tasks else 0

            is_active = stage_num == current_stage
            is_locked = stage_num > current_stage
            is_done = stage_pct == 100

            with st.expander(
                f"{stage['icon']}  阶段{stage_num}：{stage['name']}"
                f"  {'✅' if is_done else '🔓 进行中' if is_active else '🔒'}"
                f"  ({stage_done}/{len(stage_tasks)})"
            ):
                guidance = stage.get("guidance", "")
                if guidance:
                    issue_hint = ""
                    if is_active:
                        issue_hint = f'<br><br><span style="color:{THEME["primary"]};font-weight:500;">📌 你的议题：「{issue_text}」— 在这个阶段，试着把上面的方法应用到这个具体的情境中。</span>'
                    st.markdown(f'''
                    <div style="background:linear-gradient(135deg, {THEME["primary_light"]}, {THEME["calm_light"]});border-radius:8px;padding:0.8rem 1rem;margin-bottom:1rem;font-size:0.88rem;line-height:1.7;color:{THEME["text_primary"]};">
                        💡 <strong>阶段指导</strong><br>{guidance}{issue_hint}
                    </div>
                    ''', unsafe_allow_html=True)

                st.markdown(f'<div style="font-size:0.85rem;color:{THEME["text_secondary"]};margin-bottom:0.8rem;">{stage["desc"]}</div>', unsafe_allow_html=True)

                for task in stage_tasks:
                    is_completed = task["id"] in proj_tasks_done
                    task_icon = {"practice": "🧘", "track": "📊", "learn": "📖", "reflect": "📝"}.get(task["type"], "📋")
                    task_detail = task.get("detail", "")

                    cols = st.columns([0.05, 0.65, 0.15, 0.15])
                    with cols[0]:
                        st.markdown("✅" if is_completed else "⬜")
                    with cols[1]:
                        text_style = f"color:#999;text-decoration:line-through;" if is_completed else f"color:{THEME['text_primary']};" if not is_locked else f"color:{THEME['text_secondary']};"
                        st.markdown(f'<span style="font-size:0.9rem;{text_style}">{task_icon} {task["text"]}</span>', unsafe_allow_html=True)
                    with cols[2]:
                        if task_detail:
                            if st.button("详情", key=f"detail_{task['id']}", use_container_width=True):
                                st.session_state[f"show_detail_{task['id']}"] = not st.session_state.get(f"show_detail_{task['id']}", False)
                                st.rerun()
                    with cols[3]:
                        if not is_completed and not is_locked:
                            if st.button("完成", key=f"task_{task['id']}", use_container_width=True):
                                proj_tasks_done.append(task["id"])
                                proj["tasks_done"] = proj_tasks_done
                                save_coach_data()
                                st.rerun()
                        elif is_locked:
                            st.markdown(f'<div style="color:{THEME["text_light"]};font-size:0.8rem;text-align:center;">🔒</div>', unsafe_allow_html=True)

                    if st.session_state.get(f"show_detail_{task['id']}", False) and task_detail:
                        st.markdown(f'''
                        <div style="background:#F8F9FA;border-radius:6px;padding:0.7rem 1rem;margin:0.2rem 0 0.5rem 1.5rem;font-size:0.85rem;line-height:1.6;color:{THEME["text_primary"]};border-left:3px solid {THEME["primary_light"]};">
                            {task_detail}
                        </div>
                        ''', unsafe_allow_html=True)

                    task_action = TASK_ACTIONS.get(task["id"])
                    # 对自定义任务，根据类型生成通用跳转
                    if not task_action:
                        t_type = task.get("type", "")
                        if t_type in ("reflect", "practice") and task.get("detail"):
                            task_action = {
                                "type": "journal",
                                "label": "📝 去记录",
                                "prefill_type": {"reflect": "反思总结", "practice": "练习记录"}.get(t_type, "随笔/感悟"),
                                "prefill_title": task["text"],
                                "prefill_content": f"练习/反思：{task['text']}\n\n我的体验和感受：\n",
                            }
                        elif t_type == "track":
                            task_action = {"type": "emotion", "label": "😊 去记录情绪"}
                        elif t_type == "learn":
                            task_action = {"type": "kb", "label": "📖 去知识库"}
                    if task_action:
                        action_cols = st.columns([0.65, 0.35])
                        with action_cols[1]:
                            if st.button(task_action["label"], key=f"go_{task['id']}", use_container_width=True):
                                if task_action["type"] == "kb":
                                    st.session_state.coach_view = "knowledge"
                                    st.session_state["kb_open_article"] = task_action["kb_ref"]
                                elif task_action["type"] == "journal":
                                    st.session_state.coach_view = "journal"
                                    st.session_state["journal_prefill"] = {
                                        "type": task_action.get("prefill_type", "随笔/感悟"),
                                        "title": task_action.get("prefill_title", "") + f"（议题：{issue_text}）",
                                        "content": task_action.get("prefill_content", ""),
                                    }
                                elif task_action["type"] == "emotion":
                                    st.session_state.coach_view = "emotion"
                                st.rerun()

                if not is_locked and is_done:
                    st.markdown(f'''
                    <div style="background:linear-gradient(135deg, #E8F5E9, #F1F8E9);border-radius:8px;padding:0.8rem 1rem;margin-top:0.8rem;font-size:0.9rem;line-height:1.6;color:{THEME["text_primary"]};">
                        🎉 <strong>恭喜完成「{stage["name"]}」阶段！</strong><br>
                        你已经在「{issue_text}」这个议题上掌握了{stage["name"]}的能力。继续前进，下一个阶段在前方等你！
                    </div>
                    ''', unsafe_allow_html=True)

                if is_done and stage_num == current_stage:
                    if len(stage_tasks) > 0:
                        if st.button(f"✨ 进入下一阶段", use_container_width=True, type="primary", key=f"next_stage_{stage_num}"):
                            proj["stage"] = stage_num + 1
                            st.session_state.growth_stage = stage_num + 1
                            save_coach_data()
                            st.rerun()

                # 第六阶段全部完成
                if is_done and stage_num == 6:
                    st.markdown(f'''
                    <div style="background:linear-gradient(135deg, #FFF9C4, #F1F8E9);border-radius:10px;padding:1rem 1.2rem;margin-top:1rem;font-size:0.95rem;line-height:1.7;color:{THEME["text_primary"]};border:2px solid {THEME["primary"]};">
                        🎊 <strong>太棒了！你完成了「{issue_text}」这个议题的全部成长旅程！</strong><br><br>
                        你已经走过了 ACT 的六个核心过程。回顾一下，你现在面对「{issue_text}」时的感受和之前有什么不同？<br><br>
                        成长不是终点，而是持续的过程。你可以：
                    </div>
                    ''', unsafe_allow_html=True)
                    finish_cols = st.columns(2)
                    with finish_cols[0]:
                        if st.button("📝 写一篇总结反思", key="finish_journal", use_container_width=True):
                            st.session_state.coach_view = "journal"
                            st.session_state["journal_prefill"] = {
                                "type": "反思总结",
                                "title": f"完成议题「{issue_text}」的总结",
                                "content": f"议题：{issue_text}\n\n走完6个阶段后，我的变化：\n\n最有收获的阶段：\n\n我现在面对「{issue_text}」时的感受：\n\n我学到的最重要的东西：\n\n我想继续探索的议题：\n",
                            }
                            st.rerun()
                    with finish_cols[1]:
                        if st.button("🏁 完成并开始新议题", key="finish_project", type="primary", use_container_width=True):
                            proj["status"] = "completed"
                            save_coach_data()
                            st.rerun()

        # 项目管理按钮
        st.markdown("---")
        mng_cols = st.columns(3)
        with mng_cols[0]:
            if st.button("⏸️ 暂停当前议题", key="pause_project", use_container_width=True):
                proj["status"] = "paused"
                save_coach_data()
                st.rerun()
        with mng_cols[1]:
            if st.button("🔄 换一套练习", key="regen_project", use_container_width=True):
                st.session_state["show_regen_confirm"] = True
                st.rerun()
        with mng_cols[2]:
            if st.button("➕ 开始新议题", key="add_project", use_container_width=True):
                st.session_state["show_new_project_form"] = True
                st.rerun()

        # 重新生成确认
        if st.session_state.get("show_regen_confirm"):
            current_type = proj.get("issue_type", "default")
            st.markdown(f'''
            <div style="background:#FFF8E1;border-radius:8px;padding:0.8rem 1rem;margin:0.5rem 0;font-size:0.88rem;color:{THEME["text_primary"]};">
                🔄 <strong>选择新的练习模板</strong><br>
                当前使用的是{f"「{current_type}方向」" if current_type != "default" else "通用模板"}。你可以切换到其他模板，或使用通用练习路径。
            </div>
            ''', unsafe_allow_html=True)
            type_options = {
                "自动检测": None,
                "焦虑方向": "焦虑",
                "自责方向": "自责",
                "疲惫方向": "疲惫",
                "社交方向": "社交",
                "亲子关系方向": "亲子关系",
                "通用模板": "default",
            }
            sel_cols = st.columns([0.6, 0.4])
            with sel_cols[0]:
                regen_choice = st.selectbox("选择模板", list(type_options.keys()), key="regen_type_select", label_visibility="collapsed")
            with sel_cols[1]:
                regen_btn_cols = st.columns(2)
                with regen_btn_cols[0]:
                    if st.button("✅ 应用", type="primary", key="confirm_regen"):
                        chosen_type = type_options[regen_choice]
                        if chosen_type is None:
                            chosen_type = detect_issue_type(proj["issue"])
                        if chosen_type == "default":
                            proj["custom_stages"] = None
                            proj["issue_type"] = "default"
                        else:
                            proj["custom_stages"] = generate_custom_stages(proj["issue"], chosen_type)
                            proj["issue_type"] = chosen_type
                        save_coach_data()
                        st.session_state["show_regen_confirm"] = False
                        st.rerun()
                with regen_btn_cols[1]:
                    if st.button("❌ 取消", key="cancel_regen"):
                        st.session_state["show_regen_confirm"] = False
                        st.rerun()

        if st.session_state.get("show_new_project_form"):
            st.markdown(f'<div class="section-title">新议题</div>', unsafe_allow_html=True)
            new_issue = st.text_input("描述你的新议题", placeholder="比如：感到社交孤立...", key="new_parallel_issue", label_visibility="collapsed")
            if new_issue and st.button("🌱 开启", type="primary", key="create_parallel"):
                proj["status"] = "paused"
                new_issue_text = new_issue.strip()
                new_issue_type = detect_issue_type(new_issue_text)
                new_custom_stages = generate_custom_stages(new_issue_text, new_issue_type)
                new_proj = {
                    "id": f"proj_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "issue": new_issue_text,
                    "created_at": datetime.now().strftime("%Y-%m-%d"),
                    "stage": 1,
                    "tasks_done": [],
                    "status": "active",
                    "issue_type": new_issue_type,
                    "custom_stages": new_custom_stages,
                }
                st.session_state.growth_projects.append(new_proj)
                st.session_state.growth_stage = 1
                st.session_state.growth_tasks_done = []
                st.session_state["show_new_project_form"] = False
                save_coach_data()
                st.rerun()

    # 暂停中的项目
    paused_projects = [p for p in projects if p["status"] == "paused"]
    if paused_projects:
        with st.expander(f"⏸️ 暂停中的议题（{len(paused_projects)}个）"):
            for p in paused_projects:
                total_t = get_project_total_tasks(p)
                done_t = len(p.get("tasks_done", []))
                pcols = st.columns([0.7, 0.3])
                with pcols[0]:
                    st.markdown(f'''
                    <div style="padding:0.3rem 0;">
                        <span style="font-weight:500;color:{THEME["text_primary"]};">{p["issue"]}</span>
                        <span style="font-size:0.8rem;color:{THEME["text_secondary"]};margin-left:0.5rem;">{done_t}/{total_t} · 阶段{p.get("stage", 1)}</span>
                    </div>
                    ''', unsafe_allow_html=True)
                with pcols[1]:
                    if st.button("恢复", key=f"resume_{p['id']}", use_container_width=True):
                        for pp in projects:
                            if pp["status"] == "active":
                                pp["status"] = "paused"
                        p["status"] = "active"
                        st.session_state.growth_stage = p["stage"]
                        st.session_state.growth_tasks_done = p.get("tasks_done", [])
                        save_coach_data()
                        st.rerun()


def render_journal():
    """我的记录 — 综合记录中心，支持多种类型的记录"""
    st.markdown(f"""
    <div class="coach-hero-small">
        <h2>📝 我的记录</h2>
        <p>把想法、感受、练习都记录下来，回头看看自己的变化</p>
    </div>
    """, unsafe_allow_html=True)

    # === 新建记录 ===
    # 检查是否有从成长任务跳转过来的预填内容
    prefill = st.session_state.pop("journal_prefill", None)
    if prefill:
        st.markdown(f'<div style="background:{THEME["primary_light"]};border-radius:8px;padding:0.5rem 1rem;margin-bottom:0.8rem;font-size:0.85rem;color:{THEME["primary"]};">📋 来自成长任务的引导，内容已预填，你可以直接修改或补充</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="section-title">新建记录</div>', unsafe_allow_html=True)

    rec_cols = st.columns(2)
    with rec_cols[0]:
        type_options = ["📝 随笔/感悟", "😊 情绪记录", "🧘 练习记录", "📖 阅读笔记", "💡 反思总结", "🎯 目标/计划"]
        # 预填记录类型
        default_type_idx = 0
        if prefill and prefill.get("type"):
            for i, opt in enumerate(type_options):
                if prefill["type"] in opt:
                    default_type_idx = i
                    break
        record_type = st.selectbox("记录类型", type_options, index=default_type_idx, key="record_type")
    with rec_cols[1]:
        record_mood = st.selectbox("此刻心情", [
            "🌟 很好", "😌 平静", "😊 不错", "🙂 还好",
            "😐 一般", "😟 不好", "😢 很差",
        ], key="record_mood")

    record_title = st.text_input("标题（可选）", placeholder="给这条记录起个名字，方便以后查找",
                                 value=prefill.get("title", "") if prefill else "", key="record_title")
    record_content = st.text_area("记录内容", height=150,
                                  placeholder="写下你想记录的任何内容…\n\n可以是一段感受、一次练习的体验、对一篇文章的思考、一个目标、或者随想。",
                                  value=prefill.get("content", "") if prefill else "", key="record_content")

    # 标签（可选）
    record_tags = st.text_input("标签（用逗号分隔，如：焦虑, 练习, 呼吸）", placeholder="添加标签方便日后搜索", key="record_tags")

    save_cols = st.columns([0.7, 0.3])
    with save_cols[1]:
        if st.button("📝 保存记录", use_container_width=True, type="primary", key="save_record"):
            if record_content.strip():
                type_icon = record_type.split(" ")[0]
                type_name = record_type.split(" ", 1)[1] if " " in record_type else record_type
                tags = [t.strip() for t in record_tags.split(",") if t.strip()] if record_tags else []

                entry = {
                    "id": f"rec_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "type": type_name,
                    "type_icon": type_icon,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "title": record_title.strip() or f"{type_name} {datetime.now().strftime('%m-%d')}",
                    "content": record_content.strip(),
                    "mood": record_mood,
                    "tags": tags,
                }
                st.session_state.personal_records.append(entry)
                # 同时保留到 journal_entries（兼容旧逻辑）
                st.session_state.journal_entries.append({
                    "time": entry["time"],
                    "mood": entry["mood"],
                    "content": f"[{type_name}] {entry['title']}\n{entry['content']}",
                })
                save_coach_data()
                st.success("记录已保存 💚")
                st.rerun()

    st.markdown("---")

    # === 搜索和筛选 ===
    st.markdown(f'<div class="section-title">所有记录</div>', unsafe_allow_html=True)

    all_records = st.session_state.personal_records

    # 搜索框
    search_col, filter_col = st.columns([0.7, 0.3])
    with search_col:
        search_query = st.text_input("🔍 搜索记录", placeholder="搜索标题、内容、标签…", key="record_search")
    with filter_col:
        type_filter = st.selectbox("筛选类型", [
            "全部类型",
            "随笔/感悟", "情绪记录", "练习记录",
            "阅读笔记", "反思总结", "目标/计划",
        ], key="record_type_filter")

    # 筛选
    filtered_records = all_records
    if type_filter != "全部类型":
        filtered_records = [r for r in filtered_records if r.get("type", "") == type_filter]
    if search_query.strip():
        q = search_query.strip().lower()
        filtered_records = [r for r in filtered_records
                           if q in r.get("title", "").lower()
                           or q in r.get("content", "").lower()
                           or q in str(r.get("tags", [])).lower()
                           or q in r.get("type", "").lower()]

    # 统计
    total_records = len(all_records)
    type_counts = {}
    for r in all_records:
        t = r.get("type", "未分类")
        type_counts[t] = type_counts.get(t, 0) + 1

    if total_records > 0:
        count_parts = [f"{v}条{ k}" for k, v in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:4]]
        st.markdown(f'<div style="font-size:0.8rem;color:{THEME["text_light"]};margin-bottom:0.8rem;">共 {total_records} 条记录（{", ".join(count_parts)}…）</div>', unsafe_allow_html=True)

    # 展示记录列表
    if not filtered_records:
        if all_records:
            st.info("没有匹配的记录，试试其他关键词？")
        else:
            st.markdown(f'''
            <div class="empty-state">
                <div class="empty-state-emoji">✨</div>
                <div class="empty-state-text">还没有任何记录<br>写下你的第一篇记录，开始记录你的成长</div>
            </div>
            ''', unsafe_allow_html=True)
    else:
        # 展示最新的 50 条
        display_records = list(reversed(filtered_records[-50:]))
        for i, entry in enumerate(display_records):
            rec_id = entry.get("id", f"rec_{i}")
            title = entry.get("title", "无标题")
            content = entry.get("content", "")
            rec_type = entry.get("type", "")
            type_icon = entry.get("type_icon", "📝")
            rec_time = entry.get("time", "")
            rec_mood = entry.get("mood", "")
            rec_tags = entry.get("tags", [])

            # 内容预览
            preview = content[:120] + ("…" if len(content) > 120 else "")

            tags_html = ""
            if rec_tags:
                tags_html = " " + " ".join([f'<span style="background:{THEME["primary_light"]};color:{THEME["primary"]};font-size:0.7rem;padding:0.1rem 0.4rem;border-radius:10px;">#{t}</span>' for t in rec_tags[:5]])

            st.markdown(f'''
            <div class="journal-entry">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="display:flex;align-items:center;gap:0.4rem;">
                        <span>{type_icon}</span>
                        <span class="journal-entry-date">{rec_time}</span>
                        <span style="font-size:0.8rem;color:{THEME["text_light"]};">· {rec_type}</span>
                    </div>
                    <span style="font-size:0.85rem;">{rec_mood}</span>
                </div>
                <div style="font-weight:500;font-size:0.95rem;color:{THEME["text_primary"]};margin:0.3rem 0;">{title}</div>
                <div class="journal-entry-content">{preview}</div>
                {tags_html}
            </div>
            ''', unsafe_allow_html=True)

            # 查看全文按钮
            col_full, col_del = st.columns([0.5, 0.5])
            with col_full:
                if st.button("📖 查看全文", key=f"view_rec_{rec_id}", use_container_width=True):
                    st.session_state[f"expand_rec_{rec_id}"] = True
                    st.rerun()
            with col_del:
                if st.button("🗑️ 删除", key=f"del_rec_{rec_id}", use_container_width=True):
                    st.session_state.personal_records = [r for r in st.session_state.personal_records if r.get("id") != rec_id]
                    save_coach_data()
                    st.rerun()

            # 全文展示
            if st.session_state.get(f"expand_rec_{rec_id}", False):
                st.markdown(f'''
                <div style="background:#F8F9FA;border-radius:8px;padding:1rem 1.2rem;margin:0.3rem 0;font-size:0.9rem;line-height:1.8;color:{THEME["text_primary"]};white-space:pre-wrap;">{content}</div>
                ''', unsafe_allow_html=True)
                if st.button("收起", key=f"collapse_rec_{rec_id}"):
                    st.session_state[f"expand_rec_{rec_id}"] = False
                    st.rerun()


# ====================================
# 进展报告（新增）
# ====================================
def render_report():
    """进展报告页面 — 按周分组 + AI 生成周报总结"""
    st.markdown(f"""
    <div class="coach-hero-small">
        <h2>📊 我的成长报告</h2>
        <p>回顾你的教练旅程，看见自己的变化</p>
    </div>
    """, unsafe_allow_html=True)

    mood_log = st.session_state.mood_log
    personal_records = st.session_state.personal_records
    _all_done_r = []
    for _p in st.session_state.growth_projects:
        _all_done_r.extend(_p.get("tasks_done", []))
    tasks_done = list(set(_all_done_r)) if _all_done_r else st.session_state.growth_tasks_done
    coach_messages = st.session_state.coach_messages
    total_tasks = sum(get_project_total_tasks(_p) for _p in st.session_state.growth_projects) if st.session_state.growth_projects else sum(len(s["tasks"]) for s in GROWTH_STAGES)

    # === 核心数据卡片 ===
    st.markdown(f'<div class="section-title">核心数据</div>', unsafe_allow_html=True)
    stat_cols = st.columns(5)
    with stat_cols[0]:
        st.markdown(f'''
        <div class="report-stat-card">
            <div style="font-size:1.5rem;">😊</div>
            <div class="report-stat-number">{len(mood_log)}</div>
            <div class="report-stat-label">情绪记录</div>
        </div>
        ''', unsafe_allow_html=True)
    with stat_cols[1]:
        st.markdown(f'''
        <div class="report-stat-card">
            <div style="font-size:1.5rem;">📝</div>
            <div class="report-stat-number">{len(personal_records)}</div>
            <div class="report-stat-label">个人记录</div>
        </div>
        ''', unsafe_allow_html=True)
    with stat_cols[2]:
        st.markdown(f'''
        <div class="report-stat-card">
            <div style="font-size:1.5rem;">🌱</div>
            <div class="report-stat-number">{len(tasks_done)}/{total_tasks}</div>
            <div class="report-stat-label">成长任务</div>
        </div>
        ''', unsafe_allow_html=True)
    with stat_cols[3]:
        st.markdown(f'''
        <div class="report-stat-card">
            <div style="font-size:1.5rem;">🎯</div>
            <div class="report-stat-number">{len(st.session_state.get("emotion_tasks_done", []))}</div>
            <div class="report-stat-label">教练任务</div>
        </div>
        ''', unsafe_allow_html=True)
    with stat_cols[4]:
        st.markdown(f'''
        <div class="report-stat-card">
            <div style="font-size:1.5rem;">💬</div>
            <div class="report-stat-number">{len(coach_messages)//2}</div>
            <div class="report-stat-label">教练对话</div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("---")

    # === AI 生成周报按钮 ===
    st.markdown(f'<div class="section-title">AI 周报总结</div>', unsafe_allow_html=True)

    week_col1, week_col2 = st.columns([0.4, 0.6])
    with week_col1:
        # 获取所有有数据的周列表
        all_dates = []
        for r in personal_records:
            if r.get("time"):
                try:
                    all_dates.append(datetime.strptime(r["time"], "%Y-%m-%d %H:%M").date())
                except:
                    pass
        for m in mood_log:
            if m.get("time"):
                try:
                    all_dates.append(datetime.strptime(m["time"], "%Y-%m-%d %H:%M").date())
                except:
                    pass

        unique_weeks = []
        seen = set()
        for d in sorted(set(all_dates), reverse=True):
            wk = d.strftime("%Y-W%W")
            if wk not in seen:
                seen.add(wk)
                unique_weeks.append(wk)

        if unique_weeks:
            week_options = [w for w in unique_weeks]
            selected_week = st.selectbox("选择周", range(len(week_options)),
                                          format_func=lambda i: week_options[i],
                                          key="report_week_select")
        else:
            st.info("还没有记录数据，无法生成周报")
            selected_week = None

    with week_col2:
        if selected_week is not None:
            wk_str = week_options[selected_week]
            year, wk_num = wk_str.split("-W")
            wk_num = int(wk_num)
            # 计算该周的日期范围
            first_day = date(int(year), 1, 1)
            if first_day.weekday() > 0:
                first_day = first_day + timedelta(days=7 - first_day.weekday())
            week_start = first_day + timedelta(weeks=wk_num - 1)
            week_end = week_start + timedelta(days=6)
            week_label = f"{week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}"

            if st.button(f"✨ 生成 {week_label} 的周报", use_container_width=True, type="primary", key="gen_weekly"):
                st.session_state["_weekly_report_wk"] = wk_str
                st.rerun()

    # 生成周报内容
    if st.session_state.get("_weekly_report_wk"):
        wk_str = st.session_state["_weekly_report_wk"]
        year, wk_num = wk_str.split("-W")
        wk_num = int(wk_num)
        first_day = date(int(year), 1, 1)
        if first_day.weekday() > 0:
            first_day = first_day + timedelta(days=7 - first_day.weekday())
        week_start = first_day + timedelta(weeks=wk_num - 1)
        week_end = week_start + timedelta(days=6)
        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end_str = (week_end + timedelta(days=1)).strftime("%Y-%m-%d")

        # 筛选该周数据
        week_moods = [m for m in mood_log if m.get("time", "") >= week_start_str and m.get("time", "") < week_end_str]
        week_records = [r for r in personal_records if r.get("time", "") >= week_start_str and r.get("time", "") < week_end_str]
        week_msgs = [m for m in coach_messages if m.get("time", "") >= week_start_str and m.get("time", "") < week_end_str and m["role"] == "user"]

        # 生成 AI 总结
        summary_parts = []
        summary_parts.append(f"**{week_start.strftime('%m月%d日')} - {week_end.strftime('%m月%d日')} 周报**\n")

        if week_moods:
            avg_mood = sum(m.get("score", 4) for m in week_moods) / len(week_moods)
            avg_intensity = sum(m.get("intensity", 5) for m in week_moods) / len(week_moods)
            mood_labels_7 = {1: "很差", 2: "不好", 3: "一般", 4: "还好", 5: "不错", 6: "平静", 7: "很好"}
            mood_name = "不错"
            for k, v in mood_labels_7.items():
                if avg_mood <= k:
                    mood_name = v
                    break
            summary_parts.append(f"**情绪概况**：本周记录了 {len(week_moods)} 次情绪，整体心情为「{mood_name}」（{avg_mood:.1f}/7），平均情绪强度 {avg_intensity:.1f}/10。")

            if avg_intensity >= 7:
                summary_parts.append("本周情绪波动较大，建议多关注自己的状态，适当增加自我关怀时间。")
            elif avg_intensity >= 5:
                summary_parts.append("情绪强度中等，这是正常的——作为照护者，允许自己有情绪波动很重要。")
            else:
                summary_parts.append("情绪相对平稳，这说明你在觉察和自我调节方面做得很好。")

            # 高频情绪
            emoji_cnt = {}
            for m in week_moods:
                e = m.get("emoji", "")
                emoji_cnt[e] = emoji_cnt.get(e, 0) + 1
            top_emoji = sorted(emoji_cnt.items(), key=lambda x: x[1], reverse=True)[:3]
            if top_emoji:
                emoji_desc = "、".join([f"{e}（{c}次）" for e, c in top_emoji])
                summary_parts.append(f"最常出现的情绪：{emoji_desc}。")

            # 触发
            triggers = [m.get("trigger", "").strip() for m in week_moods if m.get("trigger", "").strip()]
            if triggers:
                summary_parts.append(f"本周的情绪触发包括：{'、'.join(triggers[:3])}。")
        else:
            summary_parts.append("本周暂无情绪记录。记录情绪是理解自己模式的第一步，建议每天至少记录一次。")

        if week_records:
            type_cnt = {}
            for r in week_records:
                t = r.get("type", "未分类")
                type_cnt[t] = type_cnt.get(t, 0) + 1
            rec_summary = "、".join([f"{t}（{c}条）" for t, c in sorted(type_cnt.items(), key=lambda x: x[1], reverse=True)])
            summary_parts.append(f"**记录活动**：本周写了 {len(week_records)} 条记录，包括 {rec_summary}。")

        if week_msgs:
            summary_parts.append(f"本周与教练进行了 {len(week_msgs)} 次对话。")
            if len(week_msgs) >= 3:
                summary_parts.append("你保持了很好的对话频率，和教练交流是觉察情绪、获得支持的重要方式。")

        # 生成建议
        summary_parts.append("\n**💡 本周建议**")
        if len(week_moods) < 3:
            summary_parts.append("- 增加情绪记录的频率，至少每天一次。只有积累足够的数据，才能看到自己的情绪模式。")
        if len(week_records) < 2:
            summary_parts.append("- 试着在「我的记录」中多写一些随笔和反思。写作本身就是一种觉察和疗愈。")
        if week_moods:
            avg_mood = sum(m.get("score", 4) for m in week_moods) / len(week_moods)
            if avg_mood <= 3:
                summary_parts.append("- 本周整体心情偏低，建议每天做一次3分钟呼吸练习，给自己更多关怀。如果持续低落，可以多和教练聊聊。")
            if avg_mood >= 6:
                summary_parts.append("- 本周状态不错！保持让你感到平静和喜悦的那些活动，在记录中写下是什么帮助你保持好状态的。")
        summary_parts.append("- 回顾本周的成长任务进度，哪怕只完成一个小任务也是进步。")
        summary_parts.append("- 记住：成长不是直线，波动是正常的。重要的是你一直在努力。")

        # 展示周报
        st.markdown('---')
        st.markdown(f'''
        <div style="background:white;border-radius:12px;padding:1.2rem 1.5rem;box-shadow:0 2px 12px {THEME["shadow"]};border-left:4px solid {THEME["primary"]};">
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.8rem;">
                <span style="font-size:1.3rem;">🤖</span>
                <span style="font-weight:600;color:{THEME["text_primary"]};">AI 周报总结</span>
            </div>
            <div style="font-size:0.9rem;line-height:1.9;color:{THEME["text_primary"]};white-space:pre-wrap;">{chr(10).join(summary_parts)}</div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("---")

    # === 按周分组的详细记录 ===
    st.markdown(f'<div class="section-title">按周回顾</div>', unsafe_allow_html=True)

    # 合并所有数据并按时间排序
    all_items = []

    for m in mood_log:
        try:
            dt = datetime.strptime(m["time"], "%Y-%m-%d %H:%M")
            all_items.append({
                "dt": dt,
                "type": "mood",
                "time": m["time"],
                "data": m,
            })
        except:
            pass

    for r in personal_records:
        try:
            dt = datetime.strptime(r["time"], "%Y-%m-%d %H:%M")
            all_items.append({
                "dt": dt,
                "type": "record",
                "time": r["time"],
                "data": r,
            })
        except:
            pass

    for t_id in tasks_done:
        all_items.append({
            "dt": datetime.now(),  # 任务完成时间未记录，排在最后
            "type": "task",
            "time": "",
            "data": {"id": t_id},
        })

    # 按周分组
    week_groups = defaultdict(list)
    for item in sorted(all_items, key=lambda x: x["dt"], reverse=True):
        wk = item["dt"].strftime("%Y-W%W")
        week_groups[wk].append(item)

    if not week_groups:
        st.markdown(f'''
        <div class="empty-state">
            <div class="empty-state-emoji">🌱</div>
            <div class="empty-state-text">还没有任何记录<br>开始你的教练之旅吧！</div>
        </div>
        ''', unsafe_allow_html=True)
    else:
        # 最多显示最近 8 周
        for wk in sorted(week_groups.keys(), reverse=True)[:8]:
            items = week_groups[wk]
            year_s, wk_n = wk.split("-W")
            wk_n = int(wk_n)
            first_d = date(int(year_s), 1, 1)
            if first_d.weekday() > 0:
                first_d = first_d + timedelta(days=7 - first_d.weekday())
            ws = first_d + timedelta(weeks=wk_n - 1)
            we = ws + timedelta(days=6)
            week_label = f"{ws.strftime('%Y年%m月%d日')} - {we.strftime('%m月%d日')}"

            # 周摘要统计
            week_mood_items = [i for i in items if i["type"] == "mood"]
            week_rec_items = [i for i in items if i["type"] == "record"]
            week_task_items = [i for i in items if i["type"] == "task"]

            week_avg = "-"
            if week_mood_items:
                week_avg = f"{sum(i['data'].get('score', 4) for i in week_mood_items) / len(week_mood_items):.1f}"

            with st.expander(
                f"📅 {week_label}"
                f"  （{len(week_mood_items)}条情绪 · {len(week_rec_items)}条记录 · {len(week_task_items)}个任务）"
                f"  平均心情 {week_avg}"
            ):
                for item in items:
                    if item["type"] == "mood":
                        m = item["data"]
                        intensity_bar = m.get("intensity", 5)
                        bar_color = THEME["warm"] if intensity_bar >= 8 else THEME["accent"] if intensity_bar >= 6 else THEME["primary"]
                        trigger_text = m.get("trigger", "")
                        thought_text = m.get("thought", "")
                        st.markdown(f'''
                        <div class="journal-entry">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <div class="journal-entry-date">{m["time"]}</div>
                                <div style="display:flex;align-items:center;gap:0.3rem;">
                                    <span style="font-size:0.75rem;color:{THEME["text_light"]};">强度</span>
                                    <div style="width:50px;height:6px;background:{THEME["border"]};border-radius:3px;overflow:hidden;">
                                        <div style="width:{intensity_bar*10}%;height:100%;background:{bar_color};border-radius:3px;"></div>
                                    </div>
                                    <span style="font-size:0.75rem;color:{THEME["text_light"]};">{intensity_bar}/10</span>
                                </div>
                            </div>
                            <div class="journal-entry-content">
                                {m["emoji"]} <strong>{m["label"]}</strong>
                                {f' · 触发：{trigger_text}' if trigger_text else ""}
                                {f' · 想法：{thought_text}' if thought_text else ""}
                            </div>
                        </div>
                        ''', unsafe_allow_html=True)
                    elif item["type"] == "record":
                        r = item["data"]
                        title = r.get("title", "无标题")
                        content_preview = r.get("content", "")[:100] + ("..." if len(r.get("content", "")) > 100 else "")
                        tags_html = ""
                        if r.get("tags"):
                            tags_html = " " + " ".join([f'<span style="background:{THEME["primary_light"]};font-size:0.7rem;padding:0.1rem 0.3rem;border-radius:8px;">#{t}</span>' for t in r["tags"][:3]])
                        st.markdown(f'''
                        <div class="journal-entry">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <div style="display:flex;align-items:center;gap:0.4rem;">
                                    <span>{r.get("type_icon", "📝")}</span>
                                    <span class="journal-entry-date">{r.get("time", "")}</span>
                                    <span style="font-size:0.8rem;color:{THEME["text_light"]};">· {r.get("type", "")}</span>
                                </div>
                                <span style="font-size:0.85rem;">{r.get("mood", "")}</span>
                            </div>
                            <div style="font-weight:500;font-size:0.95rem;color:{THEME["text_primary"]};margin:0.3rem 0;">{title}</div>
                            <div class="journal-entry-content">{content_preview}</div>
                            {tags_html}
                        </div>
                        ''', unsafe_allow_html=True)
                    elif item["type"] == "task":
                        task_id = item["data"]["id"]
                        # 找到任务名称
                        task_name = task_id
                        for proj_item in st.session_state.growth_projects:
                            for stage in get_project_stages(proj_item):
                                for task in stage["tasks"]:
                                    if task["id"] == task_id:
                                        task_name = task["text"]
                                        break
                        st.markdown(f'''
                        <div style="font-size:0.85rem;color:{THEME["calm"]};padding:0.3rem 0;">
                            ✅ 完成任务：{task_name}
                        </div>
                        ''', unsafe_allow_html=True)



def main():
    """主函数"""

    # 自动登录
    if not st.session_state.get("logged_in", False):
        auto_login_from_query()

    # 未登录显示登录页
    if not st.session_state.get("logged_in", False):
        render_login_page()
        return

    # 已登录，初始化
    init_session_state()
    render_sidebar()

    # 路由
    view = st.session_state.get("coach_view", "home")

    if view == "home":
        render_home()
    elif view == "chat":
        render_chat()
    elif view == "knowledge":
        render_knowledge()
    elif view == "emotion_tasks":
        render_emotion_tasks()
    elif view == "emotion":
        render_emotion()
    elif view == "growth":
        render_growth()
    elif view == "journal":
        render_journal()
    elif view == "report":
        render_report()


if __name__ == "__main__":
    main()
