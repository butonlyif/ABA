"""
====================================
人生教练模块 - 样式模块
====================================

包含：
- 人生教练专用CSS样式
- 温暖绿色调主题
- 卡片、按钮、标签等组件样式
"""

THEME = {
    "primary": "#5B8C5A",        # 温暖的森林绿
    "primary_light": "#E8F0E8",  # 浅绿背景
    "primary_dark": "#3D6B3C",   # 深绿
    "accent": "#F4A261",          # 温暖橙色点缀
    "accent_light": "#FFF3E6",   # 浅橙背景
    "warm": "#E07A5F",            # 暖红/珊瑚色
    "warm_light": "#FDECEA",     # 浅珊瑚背景
    "calm": "#81B29A",            # 宁静薄荷
    "calm_light": "#E8F4EF",     # 浅薄荷背景
    "lavender": "#9B8EC1",        # 薰衣草紫
    "lavender_light": "#EDE9F3",  # 浅紫背景
    "sky": "#6FA8C9",             # 天空蓝
    "sky_light": "#E5F0F6",      # 浅蓝背景
    "sandy": "#D4A574",           # 沙金色
    "text_primary": "#2D3436",    # 主文字
    "text_secondary": "#636E72",  # 次文字
    "text_light": "#B2BEC3",      # 浅文字
    "bg": "#FAFBF9",              # 页面背景
    "card_bg": "#FFFFFF",         # 卡片背景
    "border": "#E8ECE8",          # 边框
    "shadow": "rgba(91, 140, 90, 0.08)",
    "shadow_hover": "rgba(91, 140, 90, 0.15)",
}

CUSTOM_CSS = f"""
<style>
/* ===== 全局样式 ===== */
.stApp {{
    background-color: {THEME["bg"]} !important;
}}

/* 隐藏默认 Streamlit 元素 */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
/* 不整体隐藏 header：侧边栏「展开」按钮在 header/stToolbar 内，整体隐藏会导致
   侧栏收起后无法重新打开。只隐藏工具栏操作区与 Deploy 按钮。*/
[data-testid="stToolbarActions"] {{visibility: hidden;}}
[data-testid="stAppDeployButton"] {{display: none !important;}}

/* 「展开侧边栏」按钮：默认是很淡的灰色双箭头，不显眼。做成醒目的绿色圆角按钮，
   收起侧栏后一眼能找到（stExpandSidebarButton 本身就是 button，图标是内部 Material span）。*/
[data-testid="stExpandSidebarButton"] {{
    background: {THEME["primary"]} !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 8px rgba(91,140,90,0.45) !important;
}}
[data-testid="stExpandSidebarButton"]:hover {{
    background: {THEME["primary_dark"]} !important;
}}
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
[data-testid="stExpandSidebarButton"] span {{
    color: #FFFFFF !important;
}}

/* ===== 顶部 Hero 区域 ===== */
.coach-hero {{
    background: linear-gradient(135deg, {THEME["primary"]}, {THEME["calm"]});
    color: white;
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    text-align: center;
    box-shadow: 0 4px 20px {THEME["shadow"]};
}}

.coach-hero h1 {{
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0 0 0.5rem 0;
    letter-spacing: 0.5px;
}}

.coach-hero p {{
    font-size: 1rem;
    opacity: 0.9;
    margin: 0;
}}

.coach-hero-small {{
    background: linear-gradient(135deg, {THEME["primary"]}, {THEME["calm"]});
    color: white;
    padding: 1.2rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1rem;
    box-shadow: 0 2px 12px {THEME["shadow"]};
}}

.coach-hero-small h2 {{
    font-size: 1.2rem;
    font-weight: 600;
    margin: 0 0 0.3rem 0;
}}

.coach-hero-small p {{
    font-size: 0.85rem;
    opacity: 0.9;
    margin: 0;
}}

/* ===== 卡片样式 ===== */
.coach-card {{
    background: {THEME["card_bg"]};
    border-radius: 14px;
    padding: 1.25rem;
    box-shadow: 0 2px 10px {THEME["shadow"]};
    border: 1px solid {THEME["border"]};
    transition: all 0.25s ease;
    cursor: pointer;
}}

.coach-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 20px {THEME["shadow_hover"]};
}}

.coach-card-green {{
    background: {THEME["primary_light"]};
    border: 1px solid {THEME["primary"]};
    border-radius: 14px;
    padding: 1.25rem;
    box-shadow: 0 2px 10px {THEME["shadow"]};
}}

.coach-card-orange {{
    background: {THEME["accent_light"]};
    border: 1px solid {THEME["accent"]};
    border-radius: 14px;
    padding: 1.25rem;
    box-shadow: 0 2px 10px {THEME["shadow"]};
}}

.coach-card-warm {{
    background: {THEME["warm_light"]};
    border: 1px solid {THEME["warm"]};
    border-radius: 14px;
    padding: 1.25rem;
    box-shadow: 0 2px 10px {THEME["shadow"]};
}}

.coach-card-calm {{
    background: {THEME["calm_light"]};
    border: 1px solid {THEME["calm"]};
    border-radius: 14px;
    padding: 1.25rem;
    box-shadow: 0 2px 10px {THEME["shadow"]};
}}

.coach-card-lavender {{
    background: {THEME["lavender_light"]};
    border: 1px solid {THEME["lavender"]};
    border-radius: 14px;
    padding: 1.25rem;
    box-shadow: 0 2px 10px {THEME["shadow"]};
}}

.coach-card-sky {{
    background: {THEME["sky_light"]};
    border: 1px solid {THEME["sky"]};
    border-radius: 14px;
    padding: 1.25rem;
    box-shadow: 0 2px 10px {THEME["shadow"]};
}}

/* ===== 情绪快捷按钮 ===== */
.emotion-btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.6rem 1rem;
    border-radius: 25px;
    font-size: 0.9rem;
    font-weight: 500;
    border: 2px solid transparent;
    cursor: pointer;
    transition: all 0.2s ease;
    text-decoration: none;
    color: {THEME["text_primary"]};
}}

.emotion-btn:hover {{
    transform: scale(1.05);
    box-shadow: 0 2px 8px {THEME["shadow_hover"]};
}}

.emotion-btn-anxiety {{ background: {THEME["warm_light"]}; border-color: {THEME["warm"]}; }}
.emotion-btn-sadness {{ background: {THEME["sky_light"]}; border-color: {THEME["sky"]}; }}
.emotion-btn-anger {{ background: #FDE8E5; border-color: #E07A5F; }}
.emotion-btn-fatigue {{ background: {THEME["lavender_light"]}; border-color: {THEME["lavender"]}; }}
.emotion-btn-confusion {{ background: {THEME["accent_light"]}; border-color: {THEME["accent"]}; }}
.emotion-btn-lonely {{ background: #E8E8F0; border-color: #8E8EB0; }}
.emotion-btn-gratitude {{ background: {THEME["calm_light"]}; border-color: {THEME["calm"]}; }}

/* ===== 话题分类标签 ===== */
.topic-tag {{
    display: inline-block;
    padding: 0.5rem 1rem;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    text-decoration: none;
}}

.topic-tag:hover {{
    transform: translateY(-1px);
    box-shadow: 0 3px 10px {THEME["shadow_hover"]};
}}

.topic-tag-emotion {{ background: {THEME["warm_light"]}; color: {THEME["warm"]}; }}
.topic-tag-life {{ background: {THEME["calm_light"]}; color: {THEME["primary_dark"]}; }}
.topic-tag-body {{ background: {THEME["primary_light"]}; color: {THEME["primary"]}; }}
.topic-tag-autism {{ background: {THEME["accent_light"]}; color: #B87A3A; }}
.topic-tag-more {{ background: {THEME["lavender_light"]}; color: {THEME["lavender"]}; }}

/* ===== 知识库列表条目 ===== */
.kb-item {{
    background: {THEME["card_bg"]};
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.6rem;
    border-left: 4px solid {THEME["primary"]};
    box-shadow: 0 1px 4px {THEME["shadow"]};
    transition: all 0.2s ease;
    cursor: pointer;
}}

.kb-item:hover {{
    transform: translateX(4px);
    box-shadow: 0 4px 12px {THEME["shadow_hover"]};
}}

.kb-item-orange {{ border-left-color: {THEME["accent"]}; }}
.kb-item-warm {{ border-left-color: {THEME["warm"]}; }}
.kb-item-calm {{ border-left-color: {THEME["calm"]}; }}
.kb-item-lavender {{ border-left-color: {THEME["lavender"]}; }}
.kb-item-sky {{ border-left-color: {THEME["sky"]}; }}

.kb-item-title {{
    font-size: 1rem;
    font-weight: 600;
    color: {THEME["text_primary"]};
    margin-bottom: 0.3rem;
}}

.kb-item-desc {{
    font-size: 0.85rem;
    color: {THEME["text_secondary"]};
    line-height: 1.5;
    margin-bottom: 0.3rem;
}}

.kb-item-meta {{
    font-size: 0.75rem;
    color: {THEME["text_light"]};
}}

/* ===== 成长路径进度 ===== */
.path-step-number-active {{
    background: {THEME["primary"]};
    color: white;
    box-shadow: 0 2px 8px {THEME["shadow_hover"]};
}}

.path-step-number-done {{
    background: {THEME["calm"]};
    color: white;
}}

.path-step-number-locked {{
    background: {THEME["border"]};
    color: {THEME["text_light"]};
}}

/* ===== 日志卡片 ===== */
.journal-entry {{
    background: {THEME["card_bg"]};
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.6rem;
    border: 1px solid {THEME["border"]};
    box-shadow: 0 1px 4px {THEME["shadow"]};
}}

.journal-entry-date {{
    font-size: 0.8rem;
    color: {THEME["text_light"]};
    margin-bottom: 0.3rem;
}}

.journal-entry-content {{
    font-size: 0.9rem;
    color: {THEME["text_primary"]};
    line-height: 1.6;
}}

/* ===== 徽章 ===== */
.coach-badge {{
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 15px;
    font-size: 0.75rem;
    font-weight: 500;
}}

.coach-badge-green {{ background: {THEME["primary_light"]}; color: {THEME["primary_dark"]}; }}
.coach-badge-orange {{ background: {THEME["accent_light"]}; color: #B87A3A; }}
.coach-badge-warm {{ background: {THEME["warm_light"]}; color: {THEME["warm"]}; }}
.coach-badge-calm {{ background: {THEME["calm_light"]}; color: {THEME["calm"]}; }}
.coach-badge-lavender {{ background: {THEME["lavender_light"]}; color: {THEME["lavender"]}; }}

/* ===== 空状态 ===== */
.empty-state {{
    text-align: center;
    padding: 3rem 2rem;
    color: {THEME["text_light"]};
}}

.empty-state-emoji {{
    font-size: 3rem;
    margin-bottom: 1rem;
}}

.empty-state-text {{
    font-size: 1rem;
    color: {THEME["text_secondary"]};
}}

/* ===== 进度条 ===== */
.coach-progress {{
    background: {THEME["border"]};
    border-radius: 10px;
    height: 8px;
    overflow: hidden;
}}

.coach-progress-bar {{
    height: 100%;
    border-radius: 10px;
    background: linear-gradient(90deg, {THEME["primary"]}, {THEME["calm"]});
    transition: width 0.5s ease;
}}

/* ===== 分区标题 ===== */
.section-title {{
    font-size: 1rem;
    font-weight: 600;
    color: {THEME["text_primary"]};
    margin: 1.5rem 0 0.8rem 0;
    padding-left: 0.5rem;
    border-left: 3px solid {THEME["primary"]};
}}

/* ===== 知识库分类树 ===== */
.kb-category {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.8rem 1rem;
    border-radius: 10px;
    margin-bottom: 0.4rem;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 0.9rem;
    font-weight: 500;
    background: {THEME["card_bg"]};
    color: {THEME["text_primary"]};
    border: 1px solid {THEME["border"]};
}}

.kb-category:hover {{
    background: {THEME["primary_light"]};
    border-color: {THEME["primary"]};
}}

/* ===== 报告样式 ===== */
.report-stat-card {{
    background: {THEME["card_bg"]};
    border-radius: 14px;
    padding: 1.2rem;
    box-shadow: 0 2px 10px {THEME["shadow"]};
    border: 1px solid {THEME["border"]};
    text-align: center;
}}

.report-stat-number {{
    font-size: 2rem;
    font-weight: 700;
    color: {THEME["primary"]};
    margin: 0.3rem 0;
}}

.report-stat-label {{
    font-size: 0.85rem;
    color: {THEME["text_secondary"]};
}}

.report-section {{
    background: {THEME["card_bg"]};
    border-radius: 14px;
    padding: 1.5rem;
    box-shadow: 0 2px 10px {THEME["shadow"]};
    border: 1px solid {THEME["border"]};
    margin-bottom: 1rem;
}}

.report-section h3 {{
    font-size: 1rem;
    font-weight: 600;
    color: {THEME["text_primary"]};
    margin: 0 0 0.8rem 0;
}}

.report-mood-row {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0;
    border-bottom: 1px solid {THEME["border"]};
}}

.report-mood-bar {{
    height: 20px;
    border-radius: 10px;
    background: linear-gradient(90deg, {THEME["primary"]}, {THEME["calm"]});
    min-width: 20px;
}}

/* ===== 登录页 ===== */
.login-container {{
    max-width: 400px;
    margin: 4rem auto 0 auto;
    padding: 2rem;
    background: {THEME["card_bg"]};
    border-radius: 16px;
    box-shadow: 0 4px 20px {THEME["shadow"]};
}}

.login-hero {{
    text-align: center;
    padding: 1rem 0;
    margin-bottom: 1.5rem;
}}

.login-hero h1 {{
    font-size: 1.5rem;
    color: {THEME["primary"]};
    margin: 0.5rem 0;
}}

.login-hero p {{
    font-size: 0.9rem;
    color: {THEME["text_secondary"]};
    margin: 0;
}}

/* ===== 侧边栏覆盖（人生教练专用） ===== */
.css-1d391kg {{
    background: linear-gradient(180deg, {THEME["primary_light"]} 0%, {THEME["bg"]} 100%) !important;
}}

/* ===== 文章内容样式 ===== */
.article-content {{
    background: {THEME["card_bg"]};
    border-radius: 14px;
    padding: 1.5rem 2rem;
    box-shadow: 0 2px 10px {THEME["shadow"]};
    border: 1px solid {THEME["border"]};
    line-height: 1.8;
    color: {THEME["text_primary"]};
}}

.article-content h3 {{
    font-size: 1.05rem;
    font-weight: 600;
    color: {THEME["primary_dark"]};
    margin: 1.2rem 0 0.5rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 2px solid {THEME["primary_light"]};
}}

.article-content p {{
    font-size: 0.95rem;
    line-height: 1.8;
    margin: 0.5rem 0;
}}

.article-content ul, .article-content ol {{
    padding-left: 1.5rem;
    margin: 0.5rem 0;
}}

.article-content li {{
    font-size: 0.9rem;
    line-height: 1.7;
    margin: 0.3rem 0;
}}

.article-content table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0.8rem 0;
    font-size: 0.85rem;
}}

.article-content th, .article-content td {{
    padding: 0.6rem 0.8rem;
    border: 1px solid {THEME["border"]};
    text-align: left;
}}

.article-content th {{
    background: {THEME["primary_light"]};
    color: {THEME["primary_dark"]};
    font-weight: 600;
}}

.article-content blockquote {{
    border-left: 4px solid {THEME["calm"]};
    padding: 0.8rem 1rem;
    margin: 0.8rem 0;
    background: {THEME["calm_light"]};
    border-radius: 0 8px 8px 0;
    font-style: italic;
    color: {THEME["text_secondary"]};
}}

/* 子分类卡片 - 可点击 */
.subcategory-card {{
    background: {THEME["card_bg"]};
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
    border: 1px solid {THEME["border"]};
    box-shadow: 0 1px 4px {THEME["shadow"]};
    cursor: pointer;
    transition: all 0.2s ease;
}}

.subcategory-card:hover {{
    border-color: {THEME["primary"]};
    box-shadow: 0 4px 12px {THEME["shadow_hover"]};
    transform: translateX(2px);
}}
</style>
"""


def apply_coach_styles():
    """应用人生教练样式"""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def get_coach_card(title, content, card_type="default", icon=""):
    """生成人生教练卡片 HTML"""
    card_class = {
        "default": "coach-card",
        "green": "coach-card-green",
        "orange": "coach-card-orange",
        "warm": "coach-card-warm",
        "calm": "coach-card-calm",
        "lavender": "coach-card-lavender",
        "sky": "coach-card-sky",
    }.get(card_type, "coach-card")

    icon_html = f'<div style="font-size:1.5rem;margin-bottom:0.5rem;">{icon}</div>' if icon else ""

    return f"""
    <div class="{card_class}">
        {icon_html}
        <div style="font-size:1.05rem;font-weight:600;color:{THEME['text_primary']};margin-bottom:0.3rem;">{title}</div>
        <div style="font-size:0.85rem;color:{THEME['text_secondary']};line-height:1.5;">{content}</div>
    </div>
    """


def get_kb_item_html(title, description, meta="", item_type="default"):
    """生成知识库条目 HTML"""
    item_class = f"kb-item kb-item-{item_type}" if item_type != "default" else "kb-item"
    return f"""
    <div class="{item_class}">
        <div class="kb-item-title">{title}</div>
        <div class="kb-item-desc">{description}</div>
        <div class="kb-item-meta">{meta}</div>
    </div>
    """


def get_progress_bar(percentage):
    """生成进度条 HTML"""
    return f"""
    <div class="coach-progress">
        <div class="coach-progress-bar" style="width: {min(percentage, 100)}%"></div>
    </div>
    """


def get_badge(text, badge_type="green"):
    """生成徽章 HTML"""
    return f'<span class="coach-badge coach-badge-{badge_type}">{text}</span>'
