"""孩子头像：自动生成卡通 SVG（兜底用）。

特点：
- 不依赖 LLM / 第三方服务
- 纯哈希选色板/发型/表情，结果确定
- 安全：只输出静态 SVG，不内嵌任何外部资源
"""
from __future__ import annotations

import hashlib

# 8 个温暖色板（背景 + 头发 + 皮肤 + 衬衫）
PALETTES = [
    {"bg": "#FFF5EB", "hair": "#4A3728", "skin": "#FFDAB9", "shirt": "#E8A87C"},
    {"bg": "#F0F7E6", "hair": "#3D2810", "skin": "#FFE4C9", "shirt": "#90B882"},
    {"bg": "#FFF0F3", "hair": "#1F100A", "skin": "#FFDCC8", "shirt": "#D4919E"},
    {"bg": "#FFF9E6", "hair": "#331E0A", "skin": "#FFE4C9", "shirt": "#D4A84B"},
    {"bg": "#EEF4FA", "hair": "#0F0A05", "skin": "#FFDFBF", "shirt": "#82ADD4"},
    {"bg": "#F5EEFA", "hair": "#241708", "skin": "#FFE0CA", "shirt": "#B09AC4"},
    {"bg": "#EDF8F6", "hair": "#1A0F08", "skin": "#FFDDC5", "shirt": "#7BBFB6"},
    {"bg": "#FFF8EC", "hair": "#2A1A0A", "skin": "#FFDAB9", "shirt": "#D4A24B"},
]

# 5 个发型（路径相对坐标）
HAIR_STYLES = [
    "short",     # 短发
    "long",      # 长发
    "bowl",      # 锅盖头
    "twin",      # 双马尾
    "bald",      # 短寸
]

# 4 个表情
EXPRESSIONS = ["smile", "calm", "happy", "curious"]


def _stable_hash(seed: str) -> int:
    """基于 MD5 取前 4 字节（更稳，避免 FNV-1a 在中文字符上碰撞）。"""
    return int(hashlib.md5(seed.encode("utf-8")).hexdigest()[:8], 16)


def _pick(seed: str, options: list) -> int:
    return _stable_hash(seed) % len(options)


def _hair_path(style: str, hair_color: str) -> str:
    """返回 <path> 字符串（不含颜色 fill，外部填）。"""
    if style == "short":
        return ('<path d="M30 60 Q30 30 60 26 Q90 30 90 60 L88 56 '
                'Q86 38 60 36 Q34 38 32 56 Z" fill="{c}"/>')
    if style == "long":
        return ('<path d="M22 70 Q18 40 40 24 Q60 14 80 24 Q102 40 98 70 '
                'L96 64 L92 64 L92 72 L28 72 L28 64 L24 64 Z" fill="{c}"/>')
    if style == "bowl":
        return ('<path d="M28 60 Q26 32 60 24 Q94 32 92 60 L88 56 '
                'Q86 34 60 32 Q34 34 32 56 Z" fill="{c}"/>')
    if style == "twin":
        return ('<path d="M30 60 Q30 28 60 24 Q90 28 90 60 L88 56 '
                'Q86 38 60 36 Q34 38 32 56 Z" fill="{c}"/>'
                '<circle cx="32" cy="56" r="8" fill="{c}"/>'
                '<circle cx="88" cy="56" r="8" fill="{c}"/>')
    # bald / 短寸
    return ('<path d="M32 56 Q34 40 60 38 Q86 40 88 56 Z" fill="{c}"/>')


def _eyes(expr: str) -> str:
    if expr == "happy":
        return ('<path d="M40 66 Q48 56 56 66" stroke="#3D2810" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
                '<path d="M64 66 Q72 56 80 66" stroke="#3D2810" stroke-width="3.5" fill="none" stroke-linecap="round"/>')
    if expr == "curious":
        return ('<circle cx="48" cy="64" r="5" fill="#3D2810"/>'
                '<circle cx="72" cy="64" r="5" fill="#3D2810"/>'
                '<path d="M42 72 Q48 78 54 72" stroke="#3D2810" stroke-width="3" fill="none" stroke-linecap="round"/>')
    if expr == "calm":
        return ('<path d="M40 64 L56 64" stroke="#3D2810" stroke-width="3.5" stroke-linecap="round"/>'
                '<path d="M64 64 L80 64" stroke="#3D2810" stroke-width="3.5" stroke-linecap="round"/>')
    # smile 默认
    return ('<circle cx="48" cy="64" r="4.5" fill="#3D2810"/>'
            '<circle cx="72" cy="64" r="4.5" fill="#3D2810"/>')


def _mouth(expr: str) -> str:
    if expr == "happy":
        return '<path d="M46 78 Q60 90 74 78" stroke="#3D2810" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
    if expr == "curious":
        return '<circle cx="60" cy="82" r="3.5" fill="#3D2810"/>'
    if expr == "calm":
        return '<path d="M48 80 L72 80" stroke="#3D2810" stroke-width="3.5" stroke-linecap="round"/>'
    # smile
    return '<path d="M46 78 Q60 88 74 78" stroke="#3D2810" stroke-width="3.5" fill="none" stroke-linecap="round"/>'


def generate_avatar_svg(seed: str) -> str:
    """基于 seed 生成 120×120 卡通头像 SVG。简单白底，完整内容，不做裁剪。"""
    if not seed:
        seed = "星"
    palette = PALETTES[_pick(seed + ":p", PALETTES)]
    hair = HAIR_STYLES[_pick(seed + ":h", HAIR_STYLES)]
    expr = EXPRESSIONS[_pick(seed + ":e", EXPRESSIONS)]

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120" role="img" aria-label="头像">'
        f'<rect width="120" height="120" fill="{palette["bg"]}"/>'
        # 衬衫
        f'<path d="M30 110 Q40 90 60 88 Q80 90 90 110 Z" fill="{palette["shirt"]}"/>'
        # 脸
        f'<circle cx="60" cy="62" r="26" fill="{palette["skin"]}"/>'
        # 头发
        + _hair_path(hair, palette["hair"]).replace("{c}", palette["hair"])
        # 眼睛
        + _eyes(expr)
        # 嘴
        + _mouth(expr)
        + '</svg>'
    )


def avatar_url_for(child_id: str, seed: str | None) -> str:
    """统一的对外 URL。"""
    return f"/api/v1/child-avatars/{child_id}"
