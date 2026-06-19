# -*- coding: utf-8 -*-
"""
生成用户手册示意图 v4 — 对齐产品配色（ABA 蓝 / 人生教练 绿），修复重叠
规则：
  - 同级文字字号一致；小字不加粗，避免渲染不一致
  - 不用文字透明度，用浅实色代替
  - 留足间距，杜绝文字与图形重叠
"""
import os
import matplotlib
matplotlib.rcParams['font.family'] = ['Noto Sans SC', 'Heiti SC', 'Arial Unicode MS', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch as FBP, FancyArrowPatch, Circle, Ellipse
import numpy as np

OUT_DIR = "/Users/wangxin/Documents/bjcontents/AI_codex/diagrams/"
os.makedirs(OUT_DIR, exist_ok=True)
DPI = 200

# ========== 配色：与产品/PPT 一致 ==========
C_ABA    = "#3A7BC8"   # ABA 蓝（主应用）
C_ABA_D  = "#1C3D5E"   # 深蓝
C_ABA_L  = "#E3EEFA"   # 浅蓝底
C_COACH  = "#0F766E"   # 人生教练 青绿
C_COACH_D= "#0B4F4A"
C_COACH_L= "#D7EEEA"   # 浅青绿底
C_GOLD   = "#F2B441"   # 暖黄强调
C_CORAL  = "#F0805A"   # 珊瑚强调
C_GREEN  = "#2E9E6B"
C_RED    = "#E2674A"
C_GRAY   = "#6B7C82"
C_DARK   = "#1F2A2E"
C_INK_L  = "#9AA7AB"   # 浅灰文字


def save_clean(fig, name):
    fig.savefig(OUT_DIR + name, dpi=DPI, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    print("OK " + name)


def title(ax, x, y, text, color=C_DARK):
    ax.text(x, y, text, ha='center', fontsize=15, color=color, weight='bold')


# ============================================================
# 图1：产品结构（ABA 蓝 / 教练 绿，中间留宽间距放 SSO）
# ============================================================
def d1():
    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.6); ax.axis('off')

    title(ax, 5.5, 5.25, '一个账号，两个助手', C_DARK)

    # 平台层
    ax.add_patch(FBP((2.0, 4.05), 7.0, 0.85, boxstyle="round,pad=0.16",
                     facecolor="#F4F6F8", edgecolor=C_GRAY, lw=1.0))
    ax.text(5.5, 4.62, '同一账号 · 数据互通 · 个性化推荐', ha='center', fontsize=11, color=C_DARK, weight='bold')
    ax.text(5.5, 4.27, '登录一次，在「帮孩子」与「顾自己」间整页切换', ha='center', fontsize=9.5, color=C_GRAY)

    # 左：ABA（蓝）—— 宽 3.9，留出中间 1.6 间距
    lx, w = 0.5, 3.9
    ax.add_patch(FBP((lx, 0.45), w, 2.95, boxstyle="round,pad=0.02", facecolor=C_ABA, edgecolor='none'))
    ax.add_patch(Circle((lx + w/2, 2.78), 0.42, facecolor=C_ABA_D, edgecolor='none'))
    ax.text(lx + w/2, 2.78, 'ABA', ha='center', va='center', fontsize=15, color='white', weight='bold')
    ax.text(lx + w/2, 2.05, 'ABA 智能助手', ha='center', fontsize=13, color='white', weight='bold')
    ax.text(lx + w/2, 1.66, '主应用 · 网页 8501', ha='center', fontsize=9.5, color="#D7E6F7")
    ax.text(lx + w/2, 1.30, '服务对象：孩子', ha='center', fontsize=11, color='white')
    ax.text(lx + w/2, 0.78, 'AI 问答 · 训练记录 · 数据看板 · 报告', ha='center', fontsize=8.8, color="#EAF2FB")

    # 右：人生教练（绿）
    rx = 6.6
    ax.add_patch(FBP((rx, 0.45), w, 2.95, boxstyle="round,pad=0.02", facecolor=C_COACH, edgecolor='none'))
    ax.add_patch(Circle((rx + w/2, 2.78), 0.42, facecolor=C_COACH_D, edgecolor='none'))
    ax.text(rx + w/2, 2.78, 'LC', ha='center', va='center', fontsize=15, color='white', weight='bold')
    ax.text(rx + w/2, 2.05, '人生教练', ha='center', fontsize=13, color='white', weight='bold')
    ax.text(rx + w/2, 1.66, '独立应用 · 网页 8503', ha='center', fontsize=9.5, color="#CFE8E3")
    ax.text(rx + w/2, 1.30, '服务对象：家长本人', ha='center', fontsize=11, color='white')
    ax.text(rx + w/2, 0.78, '教练对话 · 成长路径 · 情绪追踪 · 知识库', ha='center', fontsize=8.8, color="#E2F2EF")

    # 中间间距 4.4–6.6（宽 2.2），放双向箭头 + SSO 文案（不与箱体重叠）
    midx = 5.5
    ax.add_patch(FancyArrowPatch((4.62, 1.9), (6.38, 1.9), arrowstyle='<->',
                                 color=C_GOLD, lw=2.6, mutation_scale=16))
    ax.text(midx, 2.34, 'SSO 免登录', ha='center', fontsize=9.5, color=C_GOLD, weight='bold')
    ax.text(midx, 1.46, '整页互跳', ha='center', fontsize=9, color=C_GRAY)

    save_clean(fig, "01_product_overview.png")


# ============================================================
# 图2：快速开始 5 步
# ============================================================
def d2():
    fig, ax = plt.subplots(figsize=(12, 3.0))
    ax.set_xlim(0, 12); ax.set_ylim(0, 3.0); ax.axis('off')
    title(ax, 6, 2.7, '新用户 5 步快速上手', C_DARK)

    steps = [
        ("1", "注册账号", "用户名 + 密码", C_ABA),
        ("2", "添加档案", "填写孩子信息", C_COACH),
        ("3", "入门评估", "27 道是/否题", C_GOLD),
        ("4", "生成任务", "自动推荐技能", C_GREEN),
        ("5", "开始训练", "DTT 标准记录", C_CORAL),
    ]
    start_x, gap, yc = 0.9, 2.2, 1.45
    for i, (num, t, desc, color) in enumerate(steps):
        x = start_x + i * gap
        ax.add_patch(Circle((x, yc), 0.5, color=color, zorder=2))
        ax.text(x, yc, num, ha='center', va='center', fontsize=17, color='white', weight='bold', zorder=3)
        ax.text(x, 0.68, t, ha='center', fontsize=11, color=color, weight='bold')
        ax.text(x, 0.32, desc, ha='center', fontsize=9, color=C_GRAY)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + gap - 0.62, yc), xytext=(x + 0.62, yc),
                        arrowprops=dict(arrowstyle="->", color=C_INK_L, lw=1.5))
    save_clean(fig, "02_quick_start.png")


# ============================================================
# 图3：DTT 四级辅助（蓝色系递进）
# ============================================================
def d3():
    fig, ax = plt.subplots(figsize=(13, 4.4))
    ax.set_xlim(0, 13); ax.set_ylim(0, 4.4); ax.axis('off')
    title(ax, 6.5, 4.1, 'DTT 四级辅助记录体系', C_DARK)

    levels = [
        ("I", "独立", "无需任何辅助\n独立完成", "Independent", "最理想", C_GREEN),
        ("V", "语言提示", "语言提示后\n正确完成", "Verbal", "较好", C_GOLD),
        ("M", "动作示范", "示范动作后\n正确完成", "Model", "需辅助", C_ABA),
        ("P", "身体辅助", "手把手辅助后\n完成", "Physical", "重度辅助", C_CORAL),
    ]
    box_w, gap, start_x, y_box, box_h = 2.7, 0.5, 0.6, 0.45, 3.1
    for i, (lv, name, desc, eng, badge, color) in enumerate(levels):
        x = start_x + i * (box_w + gap)
        ax.add_patch(FBP((x, y_box), box_w, box_h, boxstyle="round,pad=0.10",
                         facecolor='white', edgecolor=color, lw=2))
        ax.add_patch(FBP((x, y_box + box_h - 0.62), box_w, 0.62, boxstyle="round,pad=0.10",
                         facecolor=color, edgecolor='none'))
        ax.add_patch(Circle((x + box_w/2, y_box + box_h - 0.31), 0.21, color='white', zorder=3))
        ax.text(x + box_w/2, y_box + box_h - 0.31, lv, ha='center', va='center',
                fontsize=10, color=color, weight='bold', zorder=4)
        ax.text(x + box_w/2, y_box + box_h - 1.05, name, ha='center', fontsize=12, color=color, weight='bold')
        ax.text(x + box_w/2, y_box + box_h - 1.78, desc, ha='center', fontsize=9.5, color=C_DARK)
        ax.text(x + box_w/2, y_box + box_h - 2.45, eng, ha='center', fontsize=9, color=C_GRAY)
        ax.add_patch(FBP((x + (box_w-1.6)/2, y_box + 0.32), 1.6, 0.46, boxstyle="round,pad=0.08",
                         facecolor=color + "22", edgecolor='none'))
        ax.text(x + box_w/2, y_box + 0.55, badge, ha='center', fontsize=9.5, color=color, weight='bold')

    ax.text(6.5, 0.12, '正确率 = 独立(I)正确次数 / 总试次数 × 100%', ha='center', fontsize=10, color=C_DARK)
    save_clean(fig, "03_dtt_levels.png")


# ============================================================
# 图4：ACT 六边形（教练绿为中心色）
# ============================================================
def d4():
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(-4.5, 4.5); ax.set_ylim(-4.5, 4.5); ax.axis('off'); ax.set_aspect('equal')
    title(ax, 0, 4.15, 'ACT 六大核心过程', C_DARK)

    labels = [
        ("觉察\n接纳", C_GREEN), ("想法\n解离", C_ABA), ("当下\n觉察", C_GOLD),
        ("看见\n真我", C_COACH), ("价值\n探索", C_CORAL), ("承诺\n行动", C_ABA_D),
    ]
    R, r = 2.8, 0.85
    ax.add_patch(Ellipse((0, 0), 2.5, 1.7, facecolor=C_COACH_L, edgecolor=C_COACH, lw=1.2))
    ax.text(0, 0.18, '心理灵活性', ha='center', va='center', fontsize=13, color=C_COACH, weight='bold')
    ax.text(0, -0.35, 'Psychological\nFlexibility', ha='center', va='center', fontsize=9, color=C_GRAY)

    angles = [90 - i * 60 for i in range(6)]
    for i in range(6):
        a1, a2 = np.radians(angles[i]), np.radians(angles[(i+1) % 6])
        ax.plot([R*np.cos(a1), R*np.cos(a2)], [R*np.sin(a1), R*np.sin(a2)], color="#CBD5D8", lw=1.2, zorder=1)
    for i, (label, color) in enumerate(labels):
        th = np.radians(angles[i])
        x, y = R*np.cos(th), R*np.sin(th)
        ax.add_patch(Circle((x, y), r, facecolor=color, edgecolor='white', lw=2, zorder=3))
        ax.text(x, y, label, ha='center', va='center', fontsize=10.5, color='white', weight='bold', zorder=4)
    save_clean(fig, "04_act_process.png")


# ============================================================
# 图5：成长路径（议题驱动）
# ============================================================
def d5():
    fig, ax = plt.subplots(figsize=(13, 5.4))
    ax.set_xlim(0, 13); ax.set_ylim(0, 5.4); ax.axis('off')
    title(ax, 6.5, 5.1, '成长路径 · 个性化议题驱动', C_DARK)

    top = [
        ("1", "输入你的困扰", "描述当前最困扰\n你的一件事", C_ABA),
        ("2", "自动检测类型", "焦虑 / 自责 / 疲惫\n社交 / 亲子关系", C_GOLD),
        ("3", "生成专属路径", "6 阶段 × 3–5 个\n个性化练习", C_GREEN),
    ]
    box_w, gap, start_x, y_top, box_h = 3.5, 0.65, 0.85, 2.95, 1.5
    for i, (num, t, desc, color) in enumerate(top):
        x = start_x + i * (box_w + gap)
        ax.add_patch(FBP((x, y_top), box_w, box_h, boxstyle="round,pad=0.12",
                         facecolor='white', edgecolor=color, lw=2))
        ax.add_patch(Circle((x + box_w/2, y_top + box_h + 0.16), 0.24, color=color, zorder=3))
        ax.text(x + box_w/2, y_top + box_h + 0.16, num, ha='center', va='center',
                fontsize=11, color='white', weight='bold', zorder=4)
        ax.text(x + box_w/2, y_top + box_h - 0.42, t, ha='center', fontsize=12, color=color, weight='bold')
        ax.text(x + box_w/2, y_top + box_h - 1.02, desc, ha='center', fontsize=9.5, color=C_DARK)
        if i < len(top) - 1:
            ax.annotate("", xy=(x + box_w + gap - 0.12, y_top + box_h/2), xytext=(x + box_w + 0.12, y_top + box_h/2),
                        arrowprops=dict(arrowstyle="->", color=C_INK_L, lw=1.6))

    stages = [
        ("阶段 1", "觉察\n接纳", C_GREEN), ("阶段 2", "想法\n解离", C_ABA), ("阶段 3", "当下\n觉察", C_GOLD),
        ("阶段 4", "看见\n自我", C_COACH), ("阶段 5", "价值\n探索", C_CORAL), ("阶段 6", "承诺\n行动", C_ABA_D),
    ]
    s_w, s_gap, s_start, s_y, s_h = 1.75, 0.36, 0.6, 0.5, 1.55
    for i, (tag, name, color) in enumerate(stages):
        x = s_start + i * (s_w + s_gap)
        ax.add_patch(FBP((x, s_y), s_w, s_h, boxstyle="round,pad=0.08", facecolor=color, edgecolor='none'))
        ax.text(x + s_w/2, s_y + s_h - 0.32, tag, ha='center', fontsize=9, color='white')
        ax.text(x + s_w/2, s_y + s_h/2 - 0.12, name, ha='center', va='center', fontsize=10.5, color='white', weight='bold')
        if i < len(stages) - 1:
            ax.annotate("", xy=(x + s_w + s_gap - 0.04, s_y + s_h/2), xytext=(x + s_w + 0.04, s_y + s_h/2),
                        arrowprops=dict(arrowstyle="->", color=C_INK_L, lw=1.2))
    ax.text(6.5, 0.12, '完成后可「写总结反思」或「开始新议题」', ha='center', fontsize=9.5, color=C_GREEN, weight='bold')
    save_clean(fig, "05_growth_path.png")


# ============================================================
# 封面（整页 hero）
# ============================================================
def cover():
    # 比例贴合 A4 内容区（约 15.5 : 24.7）
    fig, ax = plt.subplots(figsize=(7.6, 12.1))
    ax.set_xlim(0, 7.6); ax.set_ylim(0, 12.1); ax.axis('off')

    # 深青绿渐变背景
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("bg", [C_COACH_D, "#0E5C53", C_ABA_D])
    ax.imshow(grad, extent=[0, 7.6, 0, 12.1], aspect='auto', cmap=cmap, zorder=0)

    # 装饰圆
    ax.add_patch(Circle((6.6, 11.0), 2.4, facecolor=C_COACH, edgecolor='none', alpha=0.45, zorder=1))
    ax.add_patch(Circle((0.6, 2.0), 2.0, facecolor=C_ABA, edgecolor='none', alpha=0.30, zorder=1))
    ax.add_patch(Circle((6.9, 2.6), 1.1, facecolor=C_CORAL, edgecolor='none', alpha=0.30, zorder=1))

    # 品牌点
    ax.add_patch(Circle((1.15, 10.55), 0.42, facecolor=C_CORAL, edgecolor='none', zorder=2))
    ax.text(1.15, 10.55, '🌱', ha='center', va='center', fontsize=20, zorder=3)
    ax.text(1.75, 10.5, 'ABA 智能助手', ha='left', va='center', fontsize=15, color='white', weight='bold', zorder=3)

    # 主标题
    ax.text(0.7, 7.7, '用户手册', ha='left', fontsize=46, color='white', weight='bold', zorder=3)
    ax.text(0.72, 6.85, 'User Manual', ha='left', fontsize=15, color="#9FD5CE", zorder=3)

    # 副标题
    ax.text(0.72, 6.0, '陪孩子成长，也照顾好你自己', ha='left', fontsize=16, color="#CFE8E3", zorder=3)

    # 两个产品 chip
    def chip(x, y, w, color, name, who, port):
        ax.add_patch(FBP((x, y), w, 1.15, boxstyle="round,pad=0.04", facecolor=color, edgecolor='none', zorder=2))
        ax.text(x + 0.35, y + 0.72, name, ha='left', fontsize=13, color='white', weight='bold', zorder=3)
        ax.text(x + 0.35, y + 0.32, who + ' · ' + port, ha='left', fontsize=9.5, color="#EAF3F1", zorder=3)
    chip(0.7, 4.2, 3.05, C_ABA, 'ABA 智能助手', '面向孩子', '网页 8501')
    chip(3.95, 4.2, 3.05, C_COACH, '人生教练', '面向家长', '网页 8503')

    # 版本信息条
    ax.add_patch(FBP((0.7, 1.05), 6.3, 0.62, boxstyle="round,pad=0.04",
                     facecolor="#FFFFFF", edgecolor='none', alpha=0.12, zorder=2))
    ax.text(0.95, 1.36, '版本 v1.4.0', ha='left', fontsize=10.5, color='white', weight='bold', zorder=3)
    ax.text(0.95, 1.36, '                       2026 年 5 月   ·   适用于自闭症儿童家庭',
            ha='left', fontsize=10.5, color="#CFE8E3", zorder=3)

    save_clean(fig, "00_cover.png")


if __name__ == "__main__":
    cover(); d1(); d2(); d3(); d4(); d5()
    print("\n全部完成！")
