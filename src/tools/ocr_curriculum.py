"""
课程指南文本提取（4 本书）
=========================
- 基础书：课程指南 PDF 自带文本，直接提取（干净）。
- 初级/中级/高级：扫描件，用 tesseract OCR（DPI400 + 二值化 + psm6，中文）。
原始文本保存到 docs/课程指南文本/{book}.txt，供后续结构化解析与知识库收录。

依赖：tesseract（brew install tesseract tesseract-lang）、PyMuPDF、Pillow、numpy。
用法：python3 src/tools/ocr_curriculum.py
"""
import os, sys, subprocess, io, re
import fitz
import numpy as np
from PIL import Image

# 行首各种被 OCR 成符号的项目符号（•）
_BULLET_RE = re.compile(r"^\s*[口ロDdEe。品了\]\|！!·•\*　]+\s*")


def clean_text(raw: str) -> str:
    """规整 OCR 文本：统一项目符号为「- 」，丢弃明显噪声行。"""
    out = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        had_bullet = bool(_BULLET_RE.match(s))
        s = _BULLET_RE.sub("", s).strip()
        if not s or s in {"1", "了", "人", "JE", "Da", "oa", "本"}:
            continue
        out.append(("- " + s) if had_bullet else s)
    return "\n".join(out)

_THIS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_THIS))
OUT_DIR = os.path.join(_ROOT, "docs", "课程指南文本")

# book_key -> (pdf路径, 是否扫描件需OCR)
BOOKS = {
    "基础": (os.path.join(_ROOT, "src/aba/课程指南/课程指南.pdf"), False),
    "初级": (os.path.join(_ROOT, "初级技能分步训练/课程指南/课程指南.pdf"), True),
    "中级": (os.path.join(_ROOT, "中级技能分步训练/应用行为分析（ABA）完整教程：中级技能分步训练/课程指南/课程指南.pdf"), True),
    "高级": (os.path.join(_ROOT, "高级技能分步训练/应用行为分析（ABA）完整教程：高级技能分步训练(光盘)/课程指南/课程指南.pdf"), True),
}

_TMP = os.path.join(_ROOT, "_ocr_tmp.png")


def ocr_image(png_bytes: bytes, psm: int = 6) -> str:
    img = Image.open(io.BytesIO(png_bytes)).convert("L")
    a = np.array(img)
    thr = a.mean() - 10              # 简单二值化，提升扫描件对比度
    a = np.where(a > thr, 255, 0).astype("uint8")
    Image.fromarray(a).save(_TMP)
    try:
        r = subprocess.run(
            ["tesseract", _TMP, "stdout", "-l", "chi_sim", "--psm", str(psm)],
            capture_output=True,
        )
        return r.stdout.decode("utf-8", "replace")
    finally:
        if os.path.exists(_TMP):
            os.remove(_TMP)


def ocr_page_2col(page, dpi: int = 400) -> str:
    """扫描件按 2 栏切分后分别 OCR，保证「程序→步骤」阅读顺序不被左右栏交错打乱。"""
    png = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72)).tobytes("png")
    img = Image.open(io.BytesIO(png))
    W, H = img.size
    mid = W // 2
    left = img.crop((0, 0, mid + 30, H))
    right = img.crop((mid - 30, 0, W, H))
    lt = clean_text(ocr_image(_to_png(left)))
    rt = clean_text(ocr_image(_to_png(right)))
    return lt + "\n" + rt


def _to_png(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def extract_book(pdf_path: str, need_ocr: bool, dpi: int = 400) -> str:
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        if need_ocr:
            txt = ocr_page_2col(page, dpi)
        else:
            txt = clean_text(page.get_text())
        pages.append(f"\n\n===== 第{i+1}页 =====\n{txt.strip()}")
    doc.close()
    return "".join(pages).strip()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for key, (pdf, need_ocr) in BOOKS.items():
        if not os.path.exists(pdf):
            print(f"⚠️ 缺失: {key} -> {pdf}")
            continue
        mode = "OCR" if need_ocr else "embedded"
        print(f"[{key}] {mode} 提取中 …", flush=True)
        text = extract_book(pdf, need_ocr)
        out = os.path.join(OUT_DIR, f"{key}.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  ✓ {key}: {len(text)} 字符 -> {out}")


if __name__ == "__main__":
    main()
