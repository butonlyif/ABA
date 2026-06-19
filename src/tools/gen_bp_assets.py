# -*- coding: utf-8 -*-
"""
商业计划书配图生成 —— 与产品配色一致（ABA 蓝 / 教练 青绿）
立论核心：一个自闭症孩子 → 冲击整个家庭 → 我们做"包裹式家庭支撑"
"""
import os
import matplotlib
matplotlib.rcParams['font.family'] = ['Noto Sans SC', 'Heiti SC', 'Arial Unicode MS', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch as FBP, FancyArrowPatch, Circle, Ellipse, Polygon
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

OUT = "/Users/wangxin/Documents/bjcontents/AI_codex/diagrams/"
os.makedirs(OUT, exist_ok=True)
DPI = 200

C_ABA   = "#3A7BC8"; C_ABA_D = "#1C3D5E"; C_ABA_L = "#E3EEFA"
C_COACH = "#0F766E"; C_COACH_D = "#0B4F4A"; C_COACH_L = "#D7EEEA"
C_GOLD  = "#F2B441"; C_CORAL = "#F0805A"; C_GREEN = "#2E9E6B"
C_RED   = "#E2674A"; C_GRAY = "#6B7C82"; C_DARK = "#1F2A2E"; C_INK_L = "#9AA7AB"


def save(fig, name):
    fig.savefig(OUT + name, dpi=DPI, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig); print("OK " + name)


# ============================================================
# 封面（整页）
# ============================================================
def cover():
    fig, ax = plt.subplots(figsize=(7.6, 12.1))
    ax.set_xlim(0, 7.6); ax.set_ylim(0, 12.1); ax.axis('off')
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    cmap = LinearSegmentedColormap.from_list("bg", [C_ABA_D, "#16406B", C_COACH_D])
    ax.imshow(grad, extent=[0, 7.6, 0, 12.1], aspect='auto', cmap=cmap, zorder=0)
    ax.add_patch(Circle((6.7, 10.8), 2.4, facecolor=C_ABA, edgecolor='none', alpha=0.40, zorder=1))
    ax.add_patch(Circle((0.5, 2.4), 2.1, facecolor=C_COACH, edgecolor='none', alpha=0.35, zorder=1))
    ax.add_patch(Circle((6.9, 2.8), 1.1, facecolor=C_CORAL, edgecolor='none', alpha=0.30, zorder=1))

    ax.add_patch(FBP((0.7, 10.2), 2.5, 0.6, boxstyle="round,pad=0.04",
                     facecolor="#FFFFFF", edgecolor='none', alpha=0.16, zorder=2))
    ax.text(0.95, 10.5, 'BUSINESS  PLAN', ha='left', va='center', fontsize=12,
            color='white', weight='bold', zorder=3)

    ax.text(0.7, 8.2, '让每一个', ha='left', fontsize=30, color="#BFE0DA", zorder=3)
    ax.text(0.7, 7.25, '"星星家庭"', ha='left', fontsize=40, color='white', weight='bold', zorder=3)
    ax.text(0.7, 6.35, '都被稳稳接住', ha='left', fontsize=30, color="#BFE0DA", zorder=3)

    ax.text(0.72, 5.5, '面向自闭症儿童家长的 AI 包裹式支撑平台', ha='left',
            fontsize=14, color='white', zorder=3)
    ax.text(0.72, 5.05, 'AI-powered Wrap-around Support for Autism Families', ha='left',
            fontsize=10, color="#9FD5CE", zorder=3)

    def chip(x, y, w, color, name, who):
        ax.add_patch(FBP((x, y), w, 1.05, boxstyle="round,pad=0.04", facecolor=color, edgecolor='none', zorder=2))
        ax.text(x + 0.32, y + 0.64, name, ha='left', fontsize=12.5, color='white', weight='bold', zorder=3)
        ax.text(x + 0.32, y + 0.28, who, ha='left', fontsize=9, color="#EAF3F1", zorder=3)
    chip(0.7, 3.4, 3.05, C_ABA, 'ABA 智能助手', '帮孩子 · 科学干预')
    chip(3.95, 3.4, 3.05, C_COACH, '人生教练', '顾家长 · 心理支撑')

    ax.add_patch(FBP((0.7, 1.0), 6.3, 0.62, boxstyle="round,pad=0.04",
                     facecolor="#FFFFFF", edgecolor='none', alpha=0.12, zorder=2))
    ax.text(0.95, 1.31, '商业计划书', ha='left', fontsize=11, color='white', weight='bold', zorder=3)
    ax.text(2.6, 1.31, '·   2026 ·   对外融资 / 政府公益合作', ha='left', fontsize=10, color="#CFE8E3", zorder=3)
    save(fig, "bp_cover.png")


# ============================================================
# 图：一个孩子 → 冲击整个家庭（核心立论）
# ============================================================
def family_impact():
    fig, ax = plt.subplots(figsize=(11, 8.2))
    ax.set_xlim(0, 11); ax.set_ylim(0, 8.2); ax.axis('off'); ax.set_aspect('equal')
    ax.text(5.5, 7.9, '一个自闭症孩子，冲击的是整个家庭系统', ha='center', fontsize=16, color=C_DARK, weight='bold')

    cx, cy = 5.5, 4.05
    ax.add_patch(Circle((cx, cy), 1.1, facecolor=C_ABA, edgecolor='white', lw=3, zorder=5))
    ax.text(cx, cy + 0.22, '自闭症', ha='center', va='center', fontsize=14, color='white', weight='bold', zorder=6)
    ax.text(cx, cy - 0.32, '孩子', ha='center', va='center', fontsize=14, color='white', weight='bold', zorder=6)

    items = [
        ("经济重担", "年均康复支出\n5–6 万元，常需\n一方辞职陪训", C_CORAL, 90),
        ("照护耗竭", "每周 20–40h\n高强度干预\n全年无休", C_RED, 30),
        ("心理危机", "家长焦虑、抑郁\n检出率远高于\n普通人群", C_GOLD, -30),
        ("婚姻压力", "分歧、指责\n离异风险上升", C_COACH, -90),
        ("社交孤立", "被误解、回避\n社交，支持\n网络萎缩", C_ABA_D, -150),
        ("职业中断", "晋升停滞\n收入下降\n返岗困难", C_GREEN, 150),
    ]
    R = 2.55
    for name, desc, color, ang in items:
        th = np.radians(ang)
        x, y = cx + R*np.cos(th), cy + R*np.sin(th)
        ax.annotate("", xy=(x - 0.62*np.cos(th), y - 0.62*np.sin(th)),
                    xytext=(cx + 1.15*np.cos(th), cy + 1.15*np.sin(th)),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=2.0), zorder=2)
        ax.add_patch(Circle((x, y), 0.86, facecolor='white', edgecolor=color, lw=2.4, zorder=3))
        ax.text(x, y + 0.30, name, ha='center', va='center', fontsize=10.5, color=color, weight='bold', zorder=4)
        ax.text(x, y - 0.34, desc, ha='center', va='center', fontsize=7.3, color=C_DARK, zorder=4)

    ax.text(5.5, 0.2, '现有市场几乎只服务"孩子的康复"——而家长，长期无人接住。',
            ha='center', fontsize=12, color=C_CORAL, weight='bold')
    save(fig, "bp_family_impact.png")


# ============================================================
# 图：市场规模 + 患者增长
# ============================================================
def market():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))

    # 左：康复市场规模（亿元/年）
    cats = ['小龄康复\n(0-6岁)', '0-18岁\n孤独症康复', '三项发展\n障碍康复']
    vals = [600, 1800, 9600]
    bars = a1.bar(cats, vals, color=[C_ABA_L, C_ABA, C_ABA_D], width=0.6, edgecolor='white')
    for b, v in zip(bars, vals):
        a1.text(b.get_x()+b.get_width()/2, v+150, f'{v:,} 亿', ha='center', fontsize=11, color=C_DARK, weight='bold')
    a1.set_title('中国康复市场规模（亿元 / 年）', fontsize=13, color=C_DARK, weight='bold', pad=12)
    a1.set_ylim(0, 11000); a1.spines[['top','right']].set_visible(False)
    a1.tick_params(labelsize=9.5); a1.set_yticks([])

    # 右：患者规模与增长
    a2.text(0.5, 0.92, '患者规模与缺口', ha='center', fontsize=13, color=C_DARK, weight='bold', transform=a2.transAxes)
    facts = [
        ("1300 万+", "孤独症患者总数", C_ABA),
        ("200–300 万", "0–14 岁儿童患者", C_COACH),
        ("≈20 万 / 年", "新增患者速度", C_CORAL),
        ("30 万", "康复师人才缺口", C_GOLD),
    ]
    a2.axis('off')
    for i, (big, small, color) in enumerate(facts):
        yy = 0.74 - i*0.20
        a2.add_patch(FBP((0.05, yy-0.07), 0.9, 0.16, boxstyle="round,pad=0.01",
                         facecolor=color+"18", edgecolor='none', transform=a2.transAxes))
        a2.text(0.10, yy, big, ha='left', va='center', fontsize=15, color=color, weight='bold', transform=a2.transAxes)
        a2.text(0.52, yy, small, ha='left', va='center', fontsize=11, color=C_DARK, transform=a2.transAxes)
    save(fig, "bp_market.png")


# ============================================================
# 图：TAM / SAM / SOM 漏斗
# ============================================================
def funnel():
    fig, ax = plt.subplots(figsize=(11, 6.0))
    ax.set_xlim(0, 11); ax.set_ylim(0, 6.0); ax.axis('off')
    ax.text(0.4, 5.65, '市场空间：TAM / SAM / SOM', ha='left', fontsize=16, color=C_DARK, weight='bold')

    # 连续漏斗：左侧绘制，右侧放数值卡片 + 引导线
    cx = 3.2                 # 漏斗中心 x
    y_bot, y_top = 0.5, 4.7  # 漏斗高度范围
    hw_top, hw_bot = 2.7, 0.7  # 顶/底半宽

    def half_w(y):
        return hw_bot + (hw_top - hw_bot) * (y - y_bot) / (y_top - y_bot)

    # 三层边界
    bounds = [y_bot, y_bot + (y_top - y_bot) / 3, y_bot + 2 * (y_top - y_bot) / 3, y_top]
    layers = [
        ("TAM", "整体市场", "约 1800 亿/年", "0–18 岁孤独症康复市场 +\n千万级家长心理支持需求", C_ABA_D),
        ("SAM", "可服务市场", "数字化 + SaaS", "数字化干预与家长支持 SaaS，\n2025 数字疗法破 10 亿并高增长", C_ABA),
        ("SOM", "可获取市场", "5–8 万付费家庭", "3 年内聚焦 6 城 + 政府购买\n（基于渗透率假设）", C_COACH),
    ]
    # 从上到下：TAM, SAM, SOM
    seg = [(bounds[2], bounds[3]), (bounds[1], bounds[2]), (bounds[0], bounds[1])]
    card_x, card_y = 6.6, [4.35, 2.85, 1.35]
    for i, ((y0, y1), (tag, name, big, desc, color)) in enumerate(zip(seg, layers)):
        pts = [(cx - half_w(y1), y1), (cx + half_w(y1), y1),
               (cx + half_w(y0), y0), (cx - half_w(y0), y0)]
        ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor='white', lw=2.5, zorder=2))
        ymid = (y0 + y1) / 2
        ax.text(cx, ymid + 0.16, tag, ha='center', va='center', fontsize=15, color='white', weight='bold', zorder=3)
        ax.text(cx, ymid - 0.32, name, ha='center', va='center', fontsize=9.5, color='white', zorder=3)

        # 引导线到右侧卡片
        ax.annotate("", xy=(card_x - 0.05, card_y[i] + 0.45), xytext=(cx + half_w(ymid), ymid),
                    arrowprops=dict(arrowstyle="-", color=color, lw=1.4, alpha=0.7), zorder=1)
        # 右侧卡片
        ax.add_patch(FBP((card_x, card_y[i] - 0.05), 4.0, 0.95, boxstyle="round,pad=0.02",
                         facecolor=color + "14", edgecolor=color, lw=1.4, zorder=2))
        ax.add_patch(FBP((card_x, card_y[i] - 0.05), 0.1, 0.95, boxstyle="square,pad=0",
                         facecolor=color, edgecolor='none', zorder=3))
        ax.text(card_x + 0.28, card_y[i] + 0.62, f'{tag}  ·  {big}', ha='left', va='center',
                fontsize=11.5, color=color, weight='bold', zorder=3)
        ax.text(card_x + 0.28, card_y[i] + 0.18, desc, ha='left', va='center',
                fontsize=8.3, color=C_DARK, zorder=3)
    save(fig, "bp_funnel.png")


# ============================================================
# 图：解决方案——包裹式双轮支撑
# ============================================================
def solution():
    fig, ax = plt.subplots(figsize=(11, 6.0))
    ax.set_xlim(0, 11); ax.set_ylim(0, 6.0); ax.axis('off')
    ax.text(5.5, 5.65, '包裹式家庭支撑：一个平台，两条线，托住整个家', ha='center', fontsize=15, color=C_DARK, weight='bold')

    # 外圈"家庭"
    ax.add_patch(FBP((0.5, 0.5), 10.0, 4.6, boxstyle="round,pad=0.05", facecolor="#F4F8FB", edgecolor=C_GRAY, lw=1.2))
    ax.text(5.5, 4.75, '自闭症孩子的家庭', ha='center', fontsize=12, color=C_GRAY, weight='bold')

    # 左轮：孩子 ABA
    ax.add_patch(FBP((1.0, 1.2), 4.0, 3.1, boxstyle="round,pad=0.04", facecolor=C_ABA, edgecolor='none'))
    ax.text(3.0, 3.85, '帮孩子', ha='center', fontsize=15, color='white', weight='bold')
    ax.text(3.0, 3.42, 'ABA 智能助手', ha='center', fontsize=12, color="#EAF2FB")
    for i, t in enumerate(['122 项技能评估与训练', 'DTT 标准记录 · 数据看板', 'AI 问答 · 自动训练计划', '结构化进展报告']):
        ax.text(3.0, 2.95 - i*0.42, '· ' + t, ha='center', fontsize=9.6, color='white')

    # 右轮：家长 教练
    ax.add_patch(FBP((6.0, 1.2), 4.0, 3.1, boxstyle="round,pad=0.04", facecolor=C_COACH, edgecolor='none'))
    ax.text(8.0, 3.85, '顾家长', ha='center', fontsize=15, color='white', weight='bold')
    ax.text(8.0, 3.42, '人生教练（ACT）', ha='center', fontsize=12, color="#E2F2EF")
    for i, t in enumerate(['情绪追踪 · 危机识别', '个性化成长路径', '24h AI 教练对话', '10 大主题知识库']):
        ax.text(8.0, 2.95 - i*0.42, '· ' + t, ha='center', fontsize=9.6, color='white')

    # 中间联结
    ax.add_patch(FancyArrowPatch((5.05, 2.75), (5.95, 2.75), arrowstyle='<->',
                                 color=C_GOLD, lw=2.6, mutation_scale=16))
    ax.text(5.5, 3.05, 'SSO', ha='center', fontsize=9, color=C_GOLD, weight='bold')
    ax.text(5.5, 2.45, '数据互通', ha='center', fontsize=8, color=C_GRAY)
    save(fig, "bp_solution.png")


# ============================================================
# 图：收入结构 + 三年预测
# ============================================================
def revenue():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))

    # 左：三年营收预测（万元，假设）
    yrs = ['第 1 年', '第 2 年', '第 3 年']
    c_rev = [180, 720, 2100]   # C端订阅
    b_rev = [120, 520, 1500]   # B端机构
    g_rev = [200, 600, 1600]   # G端政府购买
    x = np.arange(3)
    a1.bar(x, c_rev, 0.55, label='C 端家庭订阅', color=C_ABA)
    a1.bar(x, b_rev, 0.55, bottom=c_rev, label='B 端机构', color=C_COACH)
    a1.bar(x, g_rev, 0.55, bottom=[c+b for c,b in zip(c_rev,b_rev)], label='G 端政府购买', color=C_GOLD)
    tot = [c+b+g for c,b,g in zip(c_rev,b_rev,g_rev)]
    for i, t in enumerate(tot):
        a1.text(i, t+80, f'{t:,} 万', ha='center', fontsize=10.5, color=C_DARK, weight='bold')
    a1.set_xticks(x); a1.set_xticklabels(yrs, fontsize=10)
    a1.set_title('三年营收预测（万元 · 假设）', fontsize=12.5, color=C_DARK, weight='bold', pad=10)
    a1.set_ylim(0, 6000); a1.set_yticks([]); a1.spines[['top','right','left']].set_visible(False)
    a1.legend(fontsize=8.5, loc='upper left', frameon=False)

    # 右：收入结构（成熟期占比，假设）
    sizes = [40, 28, 32]; labels = ['C 端家庭订阅', 'B 端机构合作', 'G 端政府购买']
    colors = [C_ABA, C_COACH, C_GOLD]
    a2.pie(sizes, labels=labels, colors=colors, autopct='%d%%', startangle=90,
           textprops={'fontsize':10, 'color':C_DARK},
           wedgeprops={'edgecolor':'white','linewidth':2})
    a2.set_title('成熟期收入结构（假设）', fontsize=12.5, color=C_DARK, weight='bold', pad=10)
    save(fig, "bp_revenue.png")


# ============================================================
# 图：三步走落地路径
# ============================================================
def roadmap():
    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.set_xlim(0, 12); ax.set_ylim(0, 4.2); ax.axis('off')
    ax.text(6, 3.95, '三步走落地路径', ha='center', fontsize=15, color=C_DARK, weight='bold')
    phases = [
        ("第 1 年", "打磨与验证", ["双 App 上线 + 数据闭环", "3 城试点 1–2 万家庭", "联合 2–3 家头部机构"], C_ABA),
        ("第 2 年", "复制与合作", ["扩展至 6 城", "接入残联/政府购买", "B 端 SaaS 标准化"], C_COACH),
        ("第 3 年", "规模与壁垒", ["全国 15+ 城覆盖", "数据/算法壁垒成型", "家长社区生态"], C_GOLD),
    ]
    bw, gap, sx, yb, bh = 3.5, 0.6, 0.55, 0.5, 2.9
    for i, (yr, t, items, color) in enumerate(phases):
        x = sx + i*(bw+gap)
        ax.add_patch(FBP((x, yb), bw, bh, boxstyle="round,pad=0.06", facecolor='white', edgecolor=color, lw=2.2))
        ax.add_patch(FBP((x, yb+bh-0.7), bw, 0.7, boxstyle="round,pad=0.06", facecolor=color, edgecolor='none'))
        ax.text(x+bw/2, yb+bh-0.35, f'{yr}  ·  {t}', ha='center', va='center', fontsize=11.5, color='white', weight='bold')
        for j, it in enumerate(items):
            ax.text(x+0.3, yb+bh-1.15-j*0.55, '· ' + it, ha='left', fontsize=9.6, color=C_DARK)
        if i < len(phases)-1:
            ax.annotate("", xy=(x+bw+gap-0.08, yb+bh/2), xytext=(x+bw+0.08, yb+bh/2),
                        arrowprops=dict(arrowstyle="-|>", color=C_INK_L, lw=1.8))
    save(fig, "bp_roadmap.png")


if __name__ == "__main__":
    cover(); family_impact(); market(); funnel(); solution(); revenue(); roadmap()
    print("\n全部完成！")
