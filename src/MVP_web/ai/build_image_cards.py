"""
开放版权图片卡生成脚本（OpenMoji 图标版）
==========================================
从 OpenMoji（开源 emoji 图标库，CC BY-SA 4.0）拉取干净、风格统一的图标，
处理成方形卡片，按类别存入 aba/图片卡_网络素材/，并生成 ATTRIBUTION.md 记录
来源与许可（CC BY-SA 要求署名）。

为什么用 OpenMoji 而不是网络照片：
  ABA 教学卡片要求「主题明确、画面干净、风格一致」。聚合照片站（如 Openverse）
  的可商用图片是真实世界照片，背景杂乱、主体不突出，不适合做辨识卡。OpenMoji
  是统一线条风格的矢量图标，识别度高、版权清晰，正是教学卡片需要的。

这些目录会被 flashcards.py 自动识别为新的卡片类别，无需改动主程序。

用法：
    python3 build_image_cards.py                 # 生成全部类别
    python3 build_image_cards.py 情绪表情 天气    # 只生成指定类别

注意：脚本需要联网。无网环境会优雅跳过并报告失败条目。
"""

import io
import os
import sys
import time
import urllib.request
from typing import List, Tuple, Optional, Dict

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("缺少 Pillow，请先安装：pip3 install pillow")
    sys.exit(1)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 本脚本在 ai/ 子目录：素材库在 src/aba/（上两级），故用两个 ".."。
OUT_DIR = os.path.join(_BASE_DIR, "..", "..", "aba", "图片卡_网络素材")

# OpenMoji 618x618 彩色 PNG —— 主用 jsdelivr CDN，失败回退 GitHub raw
_CDN_URLS = [
    "https://cdn.jsdelivr.net/gh/hfg-gmuend/openmoji@master/color/618x618/{code}.png",
    "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/618x618/{code}.png",
]
CARD_SIZE = 600
PADDING = 60                # 图标四周留白，避免顶边
REQUEST_TIMEOUT = 15
USER_AGENT = "ABA-Assistant-CardBuilder/2.0 (educational; OpenMoji)"

# ─── 卡片目录 ──────────────────────────────────────────────
# 每个词条：(中文标签, OpenMoji 码点)。码点可带 '-' 连接的 ZWJ 序列。
# 选取的都是现有 PDF 卡片未覆盖、且属于高价值 ABA 教学目标的主题。
Item = Tuple[str, str]

CATALOG: Dict[str, List[Item]] = {
    "情绪表情": [
        ("开心", "1F600"),     # 咧嘴笑
        ("伤心", "1F622"),     # 流泪
        ("生气", "1F620"),     # 生气
        ("害怕", "1F628"),     # 害怕
        ("惊讶", "1F632"),     # 吃惊
        ("累了", "1F62B"),     # 疲惫
    ],
    "职业人物": [
        ("医生", "1F468-200D-2695-FE0F"),
        ("护士", "1F469-200D-2695-FE0F"),
        ("老师", "1F468-200D-1F3EB"),
        ("警察", "1F46E"),
        ("消防员", "1F468-200D-1F692"),
        ("厨师", "1F468-200D-1F373"),
    ],
    "天气": [
        ("晴天", "2600"),      # 太阳
        ("下雨", "1F327"),     # 下雨云
        ("下雪", "1F328"),     # 下雪云
        ("多云", "2601"),      # 云
        ("刮风", "1F32C"),     # 风
        ("彩虹", "1F308"),     # 彩虹
    ],
    "水果": [
        ("苹果", "1F34E"),
        ("香蕉", "1F34C"),
        ("橙子", "1F34A"),
        ("葡萄", "1F347"),
        ("西瓜", "1F349"),
        ("草莓", "1F353"),
    ],
    "蔬菜": [
        ("胡萝卜", "1F955"),
        ("番茄", "1F345"),
        ("西兰花", "1F966"),
        ("土豆", "1F954"),
        ("黄瓜", "1F952"),
        ("玉米", "1F33D"),
    ],
    "日常自理活动": [
        ("刷牙", "1FAA5"),     # 牙刷
        ("洗手", "1F9FC"),     # 肥皂
        ("吃饭", "1F374"),     # 刀叉
        ("睡觉", "1F6CF"),     # 床
        ("穿衣", "1F455"),     # T 恤
        ("洗澡", "1F6C1"),     # 浴缸
    ],
}


def _download_icon(code: str) -> Optional[bytes]:
    """下载某码点的 OpenMoji PNG，尝试多个 CDN 与文件名变体，带轻量重试。"""
    # 文件名变体：原样 / 去掉 -FE0F / 补 -FE0F
    variants = [code]
    if code.endswith("-FE0F"):
        variants.append(code[:-5])
    else:
        variants.append(code + "-FE0F")
    for variant in variants:
        for tmpl in _CDN_URLS:
            url = tmpl.format(code=variant)
            for attempt in range(2):
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                try:
                    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
                        data = r.read()
                    if data[:8] == b"\x89PNG\r\n\x1a\n":
                        return data
                except Exception:
                    time.sleep(0.5)
    return None


def make_card(raw_bytes: bytes, label: str) -> Optional[bytes]:
    """把透明底图标合成成统一白底方卡，底部加中文标签条。"""
    try:
        icon = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
    except Exception:
        return None

    inner = CARD_SIZE - 2 * PADDING
    icon.thumbnail((inner, inner), Image.LANCZOS)

    band_h = 90
    canvas = Image.new("RGB", (CARD_SIZE, CARD_SIZE + band_h), "white")
    # 居中粘贴图标（用自身 alpha 作为蒙版）
    x = (CARD_SIZE - icon.width) // 2
    y = (CARD_SIZE - icon.height) // 2
    canvas.paste(icon, (x, y), icon)

    draw = ImageDraw.Draw(canvas)
    font = _load_cjk_font(54)
    _draw_centered_text(draw, label, CARD_SIZE, CARD_SIZE, band_h, font)

    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _load_cjk_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_centered_text(draw, text, width, y_top, band_h, font):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        oy = bbox[1]
    except Exception:
        tw, th, oy = len(text) * 30, 40, 0
    x = (width - tw) // 2
    y = y_top + (band_h - th) // 2 - oy
    draw.text((x, y), text, fill="#222222", font=font)


def build_category(name: str, items: List[Item]) -> None:
    cat_dir = os.path.join(OUT_DIR, name)
    os.makedirs(cat_dir, exist_ok=True)
    print(f"\n▶ 生成类别「{name}」（{len(items)} 个词条）")

    attributions: List[str] = []
    idx = 0
    for label, code in items:
        raw = _download_icon(code)
        if not raw:
            print(f"  ⚠ 「{label}」({code}) 下载失败")
            continue
        card = make_card(raw, label)
        if not card:
            print(f"  ⚠ 「{label}」({code}) 处理失败")
            continue
        idx += 1
        fname = f"{idx:02d}_{label}.png"
        with open(os.path.join(cat_dir, fname), "wb") as f:
            f.write(card)
        attributions.append(f"- **{fname}** — OpenMoji `{code}`")
        print(f"  ✓ {label}")
        time.sleep(0.2)

    if attributions:
        _write_attribution(cat_dir, name, attributions)
        print(f"  「{name}」完成，共 {idx} 张")
    else:
        print(f"  ✗ 「{name}」一张都没生成（可能无网络）")


def _write_attribution(cat_dir: str, name: str, lines: List[str]) -> None:
    content = (
        f"# 「{name}」图片来源与许可\n\n"
        "本目录图标来自 [OpenMoji](https://openmoji.org) —— 开源 emoji 图标项目，"
        "许可证 **CC BY-SA 4.0**。按协议要求保留以下署名：\n\n"
        "> All emojis designed by OpenMoji – the open-source emoji and icon project. "
        "License: CC BY-SA 4.0\n\n"
        + "\n".join(lines) + "\n"
    )
    with open(os.path.join(cat_dir, "ATTRIBUTION.md"), "w", encoding="utf-8") as f:
        f.write(content)


def main():
    targets = sys.argv[1:] or list(CATALOG.keys())
    unknown = [t for t in targets if t not in CATALOG]
    if unknown:
        print(f"未知类别：{unknown}\n可用类别：{list(CATALOG.keys())}")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    for name in targets:
        build_category(name, CATALOG[name])
    print("\n全部完成。新类别会自动出现在「图片卡片」页面。")


if __name__ == "__main__":
    main()
