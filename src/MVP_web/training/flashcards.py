"""
图片卡片模块
- 扫描 aba/图片/ 目录（PDF 类别），用 PyMuPDF 渲染页面
- 扫描 aba/图片卡_网络素材/ 目录（图片文件夹类别），每个子目录=一个类别，每张图片=一张卡
- PNG 磁盘缓存：第一次渲染后保存为 .png，之后直接读文件（大幅提速）
- 提供卡片列表和单张卡片获取接口；PDF 类别与图片类别对调用方完全透明
"""

import os
from typing import List, Optional, Tuple

# 本模块在 training/ 子目录下：MVP_web/ 是上一级，src/ 是上两级，素材在 src/aba/。
# 容器内素材挂载/拷贝在 /app/src/aba/（见 deploy/Dockerfile 与 docker-compose.yml）。
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_PATH = os.path.join(_BASE_DIR, "..", "..", "aba", "图片")
_CONTAINER_PATH = "/app/src/aba/图片"
ABA_IMAGES_DIR = _CONTAINER_PATH if os.path.isdir(_CONTAINER_PATH) else _LOCAL_PATH

# aba/图片卡_网络素材/ 路径：开放版权素材生成的图片卡（图片文件夹，非 PDF）
_LOCAL_IMG_PATH = os.path.join(_BASE_DIR, "..", "..", "aba", "图片卡_网络素材")
_CONTAINER_IMG_PATH = "/app/src/aba/图片卡_网络素材"
IMAGE_CARDS_DIR = _CONTAINER_IMG_PATH if os.path.isdir(_CONTAINER_IMG_PATH) else _LOCAL_IMG_PATH

# 支持的位图后缀（图片文件夹类别）
_IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp")

# PNG 缓存目录：MVP_web/data/flashcard_cache/（与用户数据同级，容器重建后保留）
_CACHE_DIR = os.path.join(_BASE_DIR, "..", "data", "flashcard_cache")

# 卡片输出格式：WebP 体积约为同尺寸 PNG 的 1/16，浏览器/Streamlit 均可直接显示。
# 同时限制最大边长，1754px 对卡片显示是过剩的，缩到 ~1000px 视觉无差但体积再降一截。
_CARD_FORMAT = "webp"   # 输出/缓存格式
_CARD_QUALITY = 80      # WebP 质量（80 对线稿/照片均够清晰）
_MAX_CARD_PX = 1000     # 渲染后若长边超过此值则等比缩小


def _get_fitz():
    """延迟导入 fitz，兼容不同版本的 PyMuPDF"""
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        pass
    try:
        import fitz
        return fitz
    except ImportError:
        raise ImportError(
            "未找到 PyMuPDF。请在终端运行：\n"
            "  pip3 install pymupdf\n"
            "如果仍然报错，请尝试：\n"
            "  pip3 install --upgrade pymupdf"
        )


# ─── 图片文件夹类别（开放版权素材）────────────────────────────

def _image_category_dir(category: str) -> Optional[str]:
    """若该类别是「图片文件夹类别」，返回其目录路径，否则返回 None。"""
    if not os.path.isdir(IMAGE_CARDS_DIR):
        return None
    cat_dir = os.path.join(IMAGE_CARDS_DIR, category)
    if os.path.isdir(cat_dir) and _list_card_images(cat_dir):
        return cat_dir
    return None


def _list_card_images(cat_dir: str) -> List[str]:
    """返回某图片类别目录下的卡片图片文件名（按名称排序）。"""
    return sorted(
        f for f in os.listdir(cat_dir)
        if f.lower().endswith(_IMG_EXTS)
    )


def _image_label_from_filename(filename: str) -> str:
    """从文件名解析卡片标签：去掉序号前缀和扩展名。
    例：'01_苹果.png' → '苹果'；'苹果.jpg' → '苹果'。"""
    name = os.path.splitext(filename)[0]
    if "_" in name:
        prefix, rest = name.split("_", 1)
        if prefix.isdigit() and rest:
            return rest
    return name


# ─── PDF 类别（支持两种结构）─────────────────────────────────
#   扁平：  类别/X.pdf
#   嵌套：  类别/子集A/A.pdf, 类别/子集B/B.pdf …（多本书里「根据功能分类物品」
#           「相同和不同」「20个问题游戏」等就是这种）
#   两种结构对调用方完全透明：一个类别 = 一串连续页码，跨多个 PDF 累计编号。

_pdf_len_cache = {}


def _category_pdfs(category: str) -> List[str]:
    """返回某 PDF 类别下的 PDF 文件列表（按名称排序）。扁平结构返回 1 个，
    嵌套结构把各子集的 PDF 依次拼接。非 PDF 类别返回 []。"""
    cat_dir = os.path.join(ABA_IMAGES_DIR, category)
    if not os.path.isdir(cat_dir):
        return []
    direct = sorted(
        os.path.join(cat_dir, f) for f in os.listdir(cat_dir) if f.endswith(".pdf")
    )
    if direct:
        return direct
    nested = []
    for sub in sorted(os.listdir(cat_dir)):
        sub_dir = os.path.join(cat_dir, sub)
        if os.path.isdir(sub_dir):
            for f in sorted(os.listdir(sub_dir)):
                if f.endswith(".pdf"):
                    nested.append(os.path.join(sub_dir, f))
    return nested


def _pdf_len(pdf_path: str) -> int:
    if pdf_path not in _pdf_len_cache:
        fitz = _get_fitz()
        doc = fitz.open(pdf_path)
        _pdf_len_cache[pdf_path] = len(doc)
        doc.close()
    return _pdf_len_cache[pdf_path]


def _locate_page(category: str, page_index: int) -> Optional[Tuple[str, int]]:
    """把类别内的「全局页码」映射到 (具体PDF路径, 该PDF内的局部页码)。"""
    if page_index < 0:
        return None
    for pdf_path in _category_pdfs(category):
        n = _pdf_len(pdf_path)
        if page_index < n:
            return pdf_path, page_index
        page_index -= n
    return None


def get_categories() -> List[str]:
    """返回所有卡片类别（PDF 类别 + 图片文件夹类别，按名称排序去重）"""
    cats = set()
    if os.path.isdir(ABA_IMAGES_DIR):
        for name in os.listdir(ABA_IMAGES_DIR):
            if name.startswith("."):
                continue
            if os.path.isdir(os.path.join(ABA_IMAGES_DIR, name)) and _category_pdfs(name):
                cats.add(name)
    if os.path.isdir(IMAGE_CARDS_DIR):
        for name in os.listdir(IMAGE_CARDS_DIR):
            path = os.path.join(IMAGE_CARDS_DIR, name)
            if os.path.isdir(path) and _list_card_images(path):
                cats.add(name)
    return sorted(cats)


# ─── 分类归组（关键词规则，自动覆盖新增类别）──────────────────
# 127 个类别平铺成一长串不便浏览，这里按技能领域归成约 10 个大组。
# 用关键词匹配而非手工映射：新增 PDF 类别也会自动落入对应大组，无需改代码。
# 规则按顺序匹配，命中即停；都不命中落入「📦 其他」。
_GROUP_RULES = [
    ("🗣️ 语言理解与命名", ("接受性", "表达性")),
    ("📖 读写·字母·阅读", ("阅读", "写作", "字母", "发音")),
    ("🔢 数学与数量", ("数学", "数量", "乘法")),
    ("🧩 配对", ("配对",)),
    ("🔄 排序与序列", ("排序", "排列", "序列", "顺序")),
    ("🗂️ 分类与归类", ("分类", "类别", "同类", "相同和不同", "相似")),
    ("😊 社交·情绪·行为", ("情绪", "情感", "行为", "社交", "考虑", "谈判",
                          "脱敏", "急救", "安全", "职业", "社会服务", "妥协", "友善")),
    ("👁️ 认知·视觉·理解", ("视觉", "空间", "部分与整体", "功能", "荒谬",
                          "常识", "完形", "记忆", "理解", "声音")),
    ("🍎 生活与常识", ("水果", "蔬菜", "天气", "食物", "饮料", "自理",
                      "购物", "驾驶", "美术", "健康", "吃")),
    ("💬 语法·句子·提问", ("复数", "时态", "动词", "句子", "描述", "比喻",
                          "提问", "回答", "抽象", "问题", "名词")),
]
_OTHER_GROUP = "📦 其他"


def group_of(category: str) -> str:
    """返回某类别所属的大组名。"""
    for group, keywords in _GROUP_RULES:
        if any(k in category for k in keywords):
            return group
    return _OTHER_GROUP


def get_grouped_categories() -> "OrderedDict":
    """把所有类别按大组归类，返回 OrderedDict{大组名: [类别,...]}。
    大组按 _GROUP_RULES 顺序排列，组内类别按名称排序；空组不出现。"""
    from collections import OrderedDict
    buckets = {g: [] for g, _ in _GROUP_RULES}
    buckets[_OTHER_GROUP] = []
    for cat in get_categories():
        buckets[group_of(cat)].append(cat)
    result = OrderedDict()
    for group, _ in _GROUP_RULES:
        if buckets[group]:
            result[group] = sorted(buckets[group])
    if buckets[_OTHER_GROUP]:
        result[_OTHER_GROUP] = sorted(buckets[_OTHER_GROUP])
    return result


def get_pdf_path(category: str) -> Optional[str]:
    """返回该类别的第一个 PDF（向后兼容；多 PDF 类别请用 _category_pdfs）。"""
    pdfs = _category_pdfs(category)
    return pdfs[0] if pdfs else None


def get_page_count(category: str) -> int:
    img_dir = _image_category_dir(category)
    if img_dir is not None:
        return len(_list_card_images(img_dir))
    return sum(_pdf_len(p) for p in _category_pdfs(category))


def _cache_path(category: str, page_index: int, dpi: int) -> str:
    """返回该页卡片缓存文件的路径（格式见 _CARD_FORMAT）"""
    safe_cat = category.replace(os.sep, "_")
    cache_dir = os.path.join(_CACHE_DIR, safe_cat)
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"p{page_index}_dpi{dpi}.{_CARD_FORMAT}")


def _encode_card(png_bytes: bytes) -> bytes:
    """把渲染出的 PNG 字节转成压缩后的卡片字节（WebP，长边不超过 _MAX_CARD_PX）。
    PIL 不可用时回退为原始 PNG，保证功能不中断。"""
    try:
        import io
        from PIL import Image
    except ImportError:
        return png_bytes
    im = Image.open(io.BytesIO(png_bytes))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    w, h = im.size
    longest = max(w, h)
    if longest > _MAX_CARD_PX:
        scale = _MAX_CARD_PX / longest
        im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))))
    out = io.BytesIO()
    # method=4：压缩率与 6 几乎一样，但编码快得多，缓存未命中时不至于卡住
    im.save(out, _CARD_FORMAT.upper(), quality=_CARD_QUALITY, method=4)
    return out.getvalue()


def render_page_as_png_bytes(category: str, page_index: int, dpi: int = 150) -> Optional[bytes]:
    """返回某张卡片的图片 bytes。
    图片文件夹类别：直接读取该图片文件（已是成品 PNG/JPG）。
    PDF 类别：用 PyMuPDF 渲染该页，优先从磁盘缓存读取。"""
    img_dir = _image_category_dir(category)
    if img_dir is not None:
        images = _list_card_images(img_dir)
        if page_index < 0 or page_index >= len(images):
            return None
        with open(os.path.join(img_dir, images[page_index]), "rb") as f:
            return f.read()

    cache_file = _cache_path(category, page_index, dpi)

    # 缓存命中：直接读文件，跳过 PDF 渲染
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            return f.read()

    # 缓存未命中：定位到具体 PDF 的局部页码后渲染并写入缓存
    located = _locate_page(category, page_index)
    if not located:
        return None
    pdf_path, local_index = located
    fitz = _get_fitz()
    doc = fitz.open(pdf_path)
    if local_index >= len(doc):
        doc.close()
        return None
    page = doc[local_index]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    data = _encode_card(pix.tobytes("png"))
    doc.close()

    # 写缓存（写失败不影响返回结果）
    try:
        with open(cache_file, "wb") as f:
            f.write(data)
    except OSError:
        pass

    return data


def get_card_label(category: str, page_index: int) -> str:
    """获取卡片文字标签。图片文件夹类别从文件名解析；PDF 类别取页面首行文字。"""
    img_dir = _image_category_dir(category)
    if img_dir is not None:
        images = _list_card_images(img_dir)
        if page_index < 0 or page_index >= len(images):
            return f"卡片 {page_index + 1}"
        return _image_label_from_filename(images[page_index])

    cache_file = _cache_path(category, page_index, 0).replace(f"_dpi0.{_CARD_FORMAT}", "_label.txt")

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return f.read().strip()

    located = _locate_page(category, page_index)
    if not located:
        return f"卡片 {page_index + 1}"
    pdf_path, local_index = located
    fitz = _get_fitz()
    doc = fitz.open(pdf_path)
    if local_index >= len(doc):
        doc.close()
        return f"卡片 {page_index + 1}"
    text = doc[local_index].get_text().strip()
    doc.close()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    label = f"卡片 {page_index + 1}"
    if lines:
        label = lines[0]
        if "Copyright" in label and len(lines) > 1:
            label = lines[1]

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(label)
    except OSError:
        pass

    return label


def get_all_cards(category: str) -> List[Tuple[int, str]]:
    n = get_page_count(category)
    return [(i, get_card_label(category, i)) for i in range(n)]


def warm_cache(category: str, dpi: int = 150) -> int:
    """预热指定类别的全部页面缓存，返回渲染的页数。
    可在后台线程或启动时调用，提前把 PDF 全部渲染好。
    图片文件夹类别本身就是成品图片，无需渲染，直接返回 0。"""
    if _image_category_dir(category) is not None:
        return 0
    n = get_page_count(category)
    rendered = 0
    for i in range(n):
        cache_file = _cache_path(category, i, dpi)
        if not os.path.exists(cache_file):
            render_page_as_png_bytes(category, i, dpi)
            rendered += 1
    return rendered
