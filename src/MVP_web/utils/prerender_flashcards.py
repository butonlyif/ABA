"""
图片卡预渲染脚本
部署后在服务器上手动运行一次，把所有 PDF 页面渲染成 PNG 缓存。
之后应用访问图片卡时直接读缓存，速度快 10-20 倍。

用法（在服务器上）：
  docker exec aba-assistant python prerender_flashcards.py

或本地开发时：
  cd src/MVP_web && python prerender_flashcards.py
"""

import sys
import time
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import training.flashcards as fc


def main():
    categories = fc.get_categories()
    if not categories:
        print(f"未找到图片卡目录：{fc.ABA_IMAGES_DIR}")
        sys.exit(1)

    print(f"找到 {len(categories)} 个类别，开始预渲染...\n")
    total_rendered = 0
    total_skipped = 0
    t0 = time.time()

    for i, cat in enumerate(categories, 1):
        n = fc.get_page_count(cat)
        rendered = fc.warm_cache(cat)
        skipped = n - rendered
        total_rendered += rendered
        total_skipped += skipped
        status = f"新渲染 {rendered} 张" if rendered else "全部已缓存"
        print(f"[{i:2d}/{len(categories)}] {cat}（{n} 页）— {status}")

    elapsed = time.time() - t0
    print(f"\n完成！新渲染 {total_rendered} 张，跳过 {total_skipped} 张（已有缓存）")
    print(f"耗时 {elapsed:.1f} 秒")


if __name__ == "__main__":
    main()
