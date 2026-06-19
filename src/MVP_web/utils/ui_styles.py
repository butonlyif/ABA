"""
====================================
ABA智能助手 - 样式美化模块
====================================

包含：
- 自定义CSS样式
- 主题颜色配置
- Streamlit样式增强
"""

THEME_COLORS = {
    "primary": "#4A90D9",
    "secondary": "#6C757D",
    "success": "#28A745",
    "warning": "#FFC107",
    "danger": "#DC3545",
    "info": "#17A2B8",
    "light": "#F8F9FA",
    "dark": "#343A40",
    "background": "#FFFFFF",
    "card_bg": "#F8F9FA",
    "border": "#DEE2E6",
}

CUSTOM_CSS = f"""
<style>
/* ── 视口 & 全局重置 ──────────────────────────── */
.stApp {{
    background-color: {THEME_COLORS["background"]};
}}

/* ────────────────────────────────────────────────
   移动端适配（屏幕宽度 ≤ 768px）
   ──────────────────────────────────────────────── */
@media (max-width: 768px) {{
    /* 全局字体：手机上调大些，更易读 */
    html, body, .stApp {{
        font-size: 17px !important;
    }}
    /* 正文/段落/列表/输入显式放大，避免被组件内联样式压回去 */
    .stApp p, .stApp li, .stApp label,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li {{
        font-size: 1.02rem !important;
        line-height: 1.6 !important;
    }}

    /* 标题缩小 */
    .page-title {{
        font-size: 1.3rem !important;
    }}
    h2 {{
        font-size: 1.25rem !important;
    }}
    h3 {{
        font-size: 1.1rem !important;
    }}
    h4 {{
        font-size: 1rem !important;
    }}

    /* 卡片无左内边距 */
    .task-card, .stMetric {{
        padding: 0.75rem !important;
        margin-bottom: 0.5rem !important;
    }}

    /* 按钮变大，适合手指点击（最小 44px 触控区域） */
    .stButton > button {{
        font-size: 0.95rem !important;
        padding: 0.65rem 1rem !important;
        min-height: 44px !important;
        border-radius: 10px !important;
    }}

    /* Radio 横排 → 竖排 + 大触控目标 */
    .stRadio [role="radiogroup"] {{
        flex-direction: column !important;
        gap: 0.5rem !important;
    }}
    .stRadio label {{
        padding: 0.5rem 0.75rem !important;
        font-size: 0.95rem !important;
        min-height: 42px !important;
        display: flex !important;
        align-items: center !important;
    }}

    /* Checkbox 触控区域增大 */
    .stCheckbox label {{
        padding: 0.4rem 0 !important;
        font-size: 0.95rem !important;
        min-height: 40px !important;
    }}

    /* Selectbox / TextInput 输入框全宽无截断 */
    .stSelectbox, .stTextInput, .stTextArea, .stNumberInput {{
        font-size: 0.95rem !important;
    }}

    /* 侧边栏在移动端缩小上边距 */
    [data-testid="stSidebar"] {{
        padding-top: 0.5rem !important;
    }}
    [data-testid="stSidebar"] .stButton > button {{
        width: 100% !important;
    }}

    /* 顶栏保留（不隐藏），其内的工具栏操作由全局规则用 visibility 隐藏；
       侧边栏「展开」按钮也在 stToolbar 内，绝不能对 stToolbar 用 display:none，
       否则按钮被压成 0×0，侧栏收起后再也打不开（=看不到登录）。*/

    /* 展开器（expander）标题触控优化 */
    .streamlit-expanderHeader {{
        font-size: 0.95rem !important;
        padding: 0.6rem 0.75rem !important;
        min-height: 44px !important;
    }}

    /* Tab 导航缩小，避免横向溢出 */
    .stTabs [data-baseweb="tab"] {{
        padding: 0.5rem 0.75rem !important;
        font-size: 0.85rem !important;
    }}

    /* 指标卡片全宽 */
    [data-testid="stMetric"] {{
        padding: 0.75rem !important;
    }}

    /* ★ st.columns 手机端单列堆叠（Streamlit 默认横向不换行，小屏会被挤窄到没法看）
       行容器 stHorizontalBlock 允许换行，列 stColumn 占满整行——
       图片卡片 [1,3] 布局会变成「类别在上、卡片在下」，3 列卡片网格变成单列大图。*/
    [data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
        gap: 0.5rem !important;
    }}
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 100% !important;
    }}

    /* ★ 主内容区左右留白收窄，给小屏更多横向空间 */
    [data-testid="stMainBlockContainer"] {{
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-top: 1rem !important;
    }}

    /* ★ 保险：侧边栏在手机端自动收起后，确保「展开」按钮始终可见可点，导航不至于打不开 */
    [data-testid="stExpandSidebarButton"] {{
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 1000 !important;
    }}
    /* 手机上把展开按钮放大，更好点（按钮本身就是该 testid 元素）*/
    [data-testid="stExpandSidebarButton"] {{
        width: 46px !important;
        height: 46px !important;
    }}
    [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {{
        font-size: 1.8rem !important;
    }}
}}

/* ★ 侧边栏「展开」按钮默认是很淡的灰色双箭头，不显眼。做成醒目的蓝色圆角按钮，
   收起侧栏后用户一眼能找到入口（含登录）。桌面/手机都生效。
   注意：stExpandSidebarButton 本身就是 <button>，图标是内部 Material span。*/
[data-testid="stExpandSidebarButton"] {{
    background: {THEME_COLORS["primary"]} !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 8px rgba(74,144,217,0.5) !important;
}}
[data-testid="stExpandSidebarButton"]:hover {{
    background: #3A7BC8 !important;
}}
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
[data-testid="stExpandSidebarButton"] span {{
    color: #FFFFFF !important;
}}

/* ────────────────────────────────────────────────
   极小屏（≤ 480px）：进一步缩小
   ──────────────────────────────────────────────── */
@media (max-width: 480px) {{
    html, body, .stApp {{
        font-size: 14px !important;
    }}
    .page-title {{
        font-size: 1.15rem !important;
    }}
    .stButton > button {{
        font-size: 0.9rem !important;
        padding: 0.55rem 0.75rem !important;
    }}
    .stApp .block-container {{
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }}
}}

/* 标题样式 */
.main-header {{
    font-size: 2.5rem;
    font-weight: 700;
    color: {THEME_COLORS["primary"]};
    text-align: center;
    padding: 1rem 0;
    border-bottom: 3px solid {THEME_COLORS["primary"]};
    margin-bottom: 2rem;
}}

/* 卡片样式 */
.css-1r6slz0 {{
    background-color: {THEME_COLORS["card_bg"]};
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border: 1px solid {THEME_COLORS["border"]};
}}

/* 按钮样式 */
.stButton > button {{
    background-color: {THEME_COLORS["primary"]};
    color: white;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    font-weight: 600;
    border: none;
    transition: all 0.3s ease;
}}

.stButton > button:hover {{
    background-color: #3A7BC8;
    box-shadow: 0 4px 12px rgba(74, 144, 217, 0.4);
    transform: translateY(-2px);
}}

/* 成功按钮 */
.success-button > button {{
    background-color: {THEME_COLORS["success"]};
}}

/* 输入框样式 */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select {{
    border-radius: 8px;
    border: 2px solid {THEME_COLORS["border"]};
    padding: 0.75rem;
}}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
    border-color: {THEME_COLORS["primary"]};
    box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.2);
}}

/* 选项卡样式 */
.stTabs [data-baseweb="tab-list"] {{
    gap: 1rem;
    background-color: {THEME_COLORS["light"]};
    padding: 0.5rem;
    border-radius: 12px;
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    font-weight: 600;
}}

.stTabs [aria-selected="true"] {{
    background-color: {THEME_COLORS["primary"]} !important;
    color: white !important;
}}

/* 指标卡片样式 */
.stMetric {{
    background-color: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-left: 4px solid {THEME_COLORS["primary"]};
}}

/* 展开器样式 */
.streamlit-expanderHeader {{
    background-color: {THEME_COLORS["card_bg"]};
    border-radius: 8px;
    font-weight: 600;
}}

/* 进度条样式 */
.stProgress > div > div > div {{
    background-color: {THEME_COLORS["primary"]};
}}

/* 成功/警告/错误消息样式 */
.stSuccess {{
    background-color: #D4EDDA;
    border-color: {THEME_COLORS["success"]};
    border-radius: 8px;
}}

.stWarning {{
    background-color: #FFF3CD;
    border-color: {THEME_COLORS["warning"]};
    border-radius: 8px;
}}

.stError {{
    background-color: #F8D7DA;
    border-color: {THEME_COLORS["danger"]};
    border-radius: 8px;
}}

/* 侧边栏样式 */
.css-1d391kg {{
    background-color: {THEME_COLORS["light"]};
}}

/* 表单样式 */
.stForm {{
    background-color: {THEME_COLORS["card_bg"]};
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid {THEME_COLORS["border"]};
}}

/* 导航按钮组 */
.nav-button {{
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
}}

/* 统计卡片 */
.stat-card {{
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    transition: transform 0.3s ease;
}}

.stat-card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}}

/* 标签样式 */
.tag {{
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
    margin: 0.25rem;
}}

.tag-primary {{
    background-color: #E7F1FF;
    color: {THEME_COLORS["primary"]};
}}

.tag-success {{
    background-color: #D4EDDA;
    color: {THEME_COLORS["success"]};
}}

.tag-warning {{
    background-color: #FFF3CD;
    color: #856404;
}}

/* 分隔线 */
.custom-divider {{
    border-top: 2px dashed {THEME_COLORS["border"]};
    margin: 1.5rem 0;
}}

/* 页面标题 */
.page-title {{
    font-size: 1.8rem;
    font-weight: 700;
    color: {THEME_COLORS["dark"]};
    margin-bottom: 1.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid {THEME_COLORS["primary"]};
}}

/* 副标题 */
.subtitle {{
    font-size: 1.2rem;
    color: {THEME_COLORS["secondary"]};
    margin-bottom: 1rem;
}}

/* ═══════════════════════════════════════════════════
   深色模式（prefers-color-scheme: dark）
   覆盖所有浅色背景/文字，保证高对比度可读
   ═══════════════════════════════════════════════════ */
@media (prefers-color-scheme: dark) {{
    /* ── 全局底色 + 文字 ── */
    .stApp, body, html, .main {{
        background-color: #1A1A2E !important;
        color: #E0E0E0 !important;
    }}

    /* 所有段落/列表/标题/标签文字强制浅色 */
    .stApp p, .stApp li, .stApp label, .stApp span,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span,
    .element-container p, .element-container li, .element-container span,
    .markdown-text-container p {{
        color: #E0E0E0 !important;
    }}

    /* 页面标题保留主题色 */
    .page-title {{
        color: #7EB8FF !important;
        border-bottom-color: #4A90D9 !important;
    }}

    /* ── 卡片 ── */
    .task-card, .stMetric, .css-1r6slz0, .stForm,
    .stat-card, .chart-container, .report-preview {{
        background-color: #222244 !important;
        border-color: #3A3A5C !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
    }}
    .task-card:hover {{
        box-shadow: 0 4px 16px rgba(0,0,0,0.6) !important;
    }}

    /* ── 输入框 ── */
    .stTextInput input, .stTextArea textarea, .stSelectbox select,
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    input, textarea, select {{
        background-color: #2A2A4A !important;
        color: #E0E0E0 !important;
        border-color: #4A4A6A !important;
    }}

    /* ── 展开器标题 ── */
    .streamlit-expanderHeader {{
        background-color: #222244 !important;
        color: #E0E0E0 !important;
    }}

    /* ── 侧边栏 ── */
    [data-testid="stSidebar"] {{
        background-color: #16162A !important;
    }}
    [data-testid="stSidebar"] * {{
        color: #D0D0D0 !important;
    }}
    [data-testid="stSidebar"] .stButton > button {{
        background-color: #2A2A4A !important;
        border-color: #4A4A6A !important;
    }}

    /* ── Tab 导航 ── */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: #1E1E3A !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: #B0B0C0 !important;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: #4A90D9 !important;
        color: white !important;
    }}

    /* ── 聊天气泡 ── */
    .stChatMessageContent p,
    .stChatMessageContent div,
    [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessageContent"] div,
    .st-emotion-cache-1n4x3ug p,
    .st-emotion-cache-h4xj5i p {{
        color: #E8E8E8 !important;
    }}

    /* ── 消息框 ── */
    .stSuccess {{
        background-color: #1A3A1A !important;
        border-color: #2A5A2A !important;
    }}
    .stWarning {{
        background-color: #3A3A0A !important;
        border-color: #5A5A2A !important;
    }}
    .stError {{
        background-color: #3A1A1A !important;
        border-color: #5A2A2A !important;
    }}
    .stInfo {{
        background-color: #1A2A3A !important;
        border-color: #2A4A5A !important;
    }}

    /* ── Radio / Checkbox（已在移动端竖排） ── */
    .stRadio label, .stCheckbox label {{
        color: #E0E0E0 !important;
    }}

    /* ── 分隔线 ── */
    hr, .custom-divider {{
        border-color: #3A3A5C !important;
    }}

    /* ── Caption / 辅助文字 ── */
    .stCaption, small, caption {{
        color: #9090A0 !important;
    }}
}}

/* 图表容器 */
.chart-container {{
    background: white;
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}}

/* 报告预览样式 */
.report-preview {{
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.1);
    border: 1px solid {THEME_COLORS["border"]};
}}

/* 隐藏默认的Streamlit元素 */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
/* 不再整体隐藏 header / stToolbar：侧边栏「展开」按钮在 stToolbar 内（收起后靠它重开侧栏）。
   只隐藏工具栏里的操作区（菜单/运行指示器）和「Deploy」按钮，展开按钮在另一子树，不受影响。*/
[data-testid="stToolbarActions"] {{visibility: hidden;}}
[data-testid="stAppDeployButton"] {{display: none !important;}}

/* 进度指示器 */
.spinner {{
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 2rem;
}}

/* 任务卡片样式 */
.task-card {{
    background: white;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-left: 4px solid {THEME_COLORS["primary"]};
    transition: transform 0.2s ease;
}}

.task-card:hover {{
    transform: translateX(4px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}}

.task-card.completed {{
    border-left-color: {THEME_COLORS["success"]};
    opacity: 0.85;
}}

.task-name {{
    font-size: 1.1rem;
    font-weight: 600;
    color: {THEME_COLORS["dark"]};
    margin-bottom: 0.5rem;
}}

.task-desc {{
    font-size: 0.9rem;
    color: {THEME_COLORS["secondary"]};
    margin-bottom: 0.5rem;
    line-height: 1.5;
}}

.task-meta {{
    font-size: 0.8rem;
    color: #888;
}}
</style>
"""


def apply_custom_styles():
    """应用自定义样式（含视口 meta 标签）"""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    # 注入 viewport meta 标签（Streamlit 默认不设置，导致移动端缩放到桌面版宽度）
    st.markdown("""
    <script>
    (function() {
        if (!document.querySelector('meta[name="viewport"]')) {
            var m = document.createElement('meta');
            m.name = 'viewport';
            m.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
            document.head.appendChild(m);
        }
    })();
    </script>
    """, unsafe_allow_html=True)


def get_card_html(title, content, border_color=None):
    """生成卡片HTML"""
    border = border_color or THEME_COLORS["primary"]
    return f"""
    <div style="
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid {border};
        margin: 1rem 0;
    ">
        <h4 style="margin: 0 0 1rem 0; color: {THEME_COLORS['dark']};">{title}</h4>
        <div>{content}</div>
    </div>
    """


def get_badge(text, badge_type="primary"):
    """生成徽章HTML"""
    colors = {
        "primary": ("#E7F1FF", THEME_COLORS["primary"]),
        "success": ("#D4EDDA", THEME_COLORS["success"]),
        "warning": ("#FFF3CD", "#856404"),
        "danger": ("#F8D7DA", THEME_COLORS["danger"]),
        "info": ("#D1ECF1", THEME_COLORS["info"]),
    }
    bg, color = colors.get(badge_type, colors["primary"])
    return f'<span style="background:{bg};color:{color};padding:0.25rem 0.75rem;border-radius:20px;font-size:0.85rem;margin:0.25rem;display:inline-block;">{text}</span>'


def get_progress_bar(percentage, color=None):
    """生成分隔线HTML"""
    bar_color = color or THEME_COLORS["primary"]
    return f"""
    <div style="background:#E9ECEF;border-radius:10px;height:10px;overflow:hidden;">
        <div style="width:{percentage}%;background:{bar_color};height:100%;border-radius:10px;"></div>
    </div>
    """
