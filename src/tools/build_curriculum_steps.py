"""
从 OCR/文本化的课程指南里，为每个「卡片类别(=训练项目)」抽取真实的分步骤列表。
输出 utils/curriculum_steps_data.py: STEPS = {类别名: [步骤, ...]}。

做法：把指南文本切成「(标题行, [步骤bullet...])」序列，再用模糊匹配把已知的
干净类别名对到最相近的标题，取其步骤。已知类别名来自 curriculum_extra_data
（文件夹名，无 OCR 噪声），因此最终技能名是干净的，只有步骤文本带少量 OCR 噪声。
"""
import os, re, sys
from difflib import SequenceMatcher

_THIS = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.dirname(_THIS)
_ROOT = os.path.dirname(_SRC)
sys.path.insert(0, os.path.join(_SRC, "MVP_web"))

from utils.curriculum_extra_data import NEW_BOOK_CATEGORIES  # noqa

TEXT_DIR = os.path.join(_ROOT, "docs", "课程指南文本")
LEVEL_FILE = {3: "初级.txt", 4: "中级.txt", 5: "高级.txt"}

# 人工校订的覆盖项：自动匹配漏掉/匹配不准的类别（标题与正文差异大、或为
# 叶子条目而非带子步骤的标题）。取自课程指南，已轻度修正明显 OCR 错字。
OVERRIDES = {
    # —— 初级：卡片名是「接受性和表达性…（X）」，指南里分「理解X/命名X」两块 ——
    "接受性和表达性语言技能（三维形状）": ["圆锥体", "立方体", "角锥体（金字塔状）", "球体", "圆柱体"],
    "接受性和表达性语言技能（反义词）": ["大/小", "亮/暗", "白天/黑夜", "开/关", "打开/关上",
                            "高/矮", "厚/薄", "深/浅", "快乐/悲伤", "姐妹/兄弟"],
    "接受性和表达性语言技能（属性）": ["破的", "空的/满的", "脏的/干净的", "圆的", "高的/矮的",
                           "大的/小的", "湿的/干的", "热的/冷的", "硬的/软的", "暗的/亮的",
                           "旧的/新的", "年轻的/年老的"],
    "接受性和表达性语言技能（性别）": ["男孩", "女孩", "男人", "女人"],
    "接受性和表达性语言技能（情感）": ["快乐", "悲伤", "生气", "害怕", "疲惫", "滑稽",
                           "惊讶", "不舒服", "放松", "害羞"],
    "接受性和表达性语言技能（社会服务人员）": ["医生", "教师", "飞行员", "消防员", "牙医",
                               "警察", "邮递员", "护士", "图书管理员", "宇航员", "农民"],
    "接受性和表达性语言技能（钱）": ["1分钱硬币", "5分钱硬币", "1角硬币", "5角硬币",
                          "1元纸币", "5元纸币", "10元纸币", "20元纸币"],
    "阅读：将字母发音与相关图片配对": ["A/apple", "B/boy", "C/cat", "D/dog",
                          "依次到 Z/elephant~zebra（字母发音↔对应图片）"],
    "阅读：将文字与图片配对": ["使用受训者感兴趣的物品/动作的简单词汇", "文字↔图片配对"],
    # —— 中级 ——
    "将来时态": ["将要做：喝饮料", "将要做：骑车", "将要做：写字", "将要做：吃饭",
              "将要做：潜水", "将要做：睡觉", "将要做：工作", "将要做：切割"],
    # —— 高级：数学为叶子条目，步骤即其细目 ——
    "数学：识别故事题中的关键词": ["加法：合并/和/加/全部",
                       "减法：多多少/少多少/丢失了/拿走了/失去/花了/差别",
                       "乘法：总的/每个/两倍/三倍/行/列/组",
                       "除法：每个/行/列/组/一半/三分之一/分数/共享/分开/平均"],
    "数学：故事题——加法": ["个位数加法", "两位数加法", "三位数加法", "四位数加法",
                     "与钱有关的加法故事题"],
    "数学：故事题——减法": ["个位数减法", "两位数减法", "三位数减法", "四位数减法",
                     "与钱有关的减法故事题"],
    "数学：熟练性": ["数学问题卡片", "工作表", "0~12以内的数字乘法"],
}
DOMAINS = ["参与技能", "模仿技能", "视觉空间技能", "语言技能", "游戏技能",
           "社交技能", "情绪调节技能", "学业前技能", "自理技能"]


# 高置信 OCR 纠错（子串替换）。仅收录上下文明确、几乎不可能误纠的；
# 含糊的（如 受氛/六从/铃匀/效击/距/本圆机/杀子/冷囊垫/wB）留原样并保持〔auto〕待人工核。
CORRECTIONS = {
    "和式龙": "恐龙", "各龙": "恐龙", "晴笔": "蜡笔", "螨笔": "蜡笔",
    "辟掌": "鼓掌", "鼓学": "鼓掌", "正在探拭": "正在擦拭", "毛由": "毛巾",
    "探手": "擦手", "扫蚌": "扫帚", "扫晕": "扫帚", "押鼻涕": "擤鼻涕",
    "蚁蝠侠": "蝙蝠侠", "加非猫": "加菲猫", "辩识": "辨识",
    "天头左右晃动": "摇头左右晃动", "男而所": "男厕所", "票了": "累了",
    "绷市": "绷带", "字航员": "宇航员", "视党": "视觉", "睡党": "睡觉",
    "竺在": "待在", "长绒鹿": "长颈鹿", "云采": "云彩", "亮饪": "烹饪",
    "可以研的东西": "可以舔的东西", "尺才": "尺寸", "玫手山季": "烫手山芋",
    "冷行冰霜": "冷若冰霜", "birqs": "birds", "耳共": "耳朵", "磁触": "触摸",
    "路室": "卧室", "打喷呈": "打喷嚏", "果桨": "果酱", "正在足球": "正在踢足球",
    "下十时": "下雨时", "比陈": "比萨", "救生和": "救生圈", "能等动物": "熊等动物",
    # —— 人工确认的 10 个含糊项 ——
    "铃匀": "铃声", "婴儿岚": "婴儿哭", "效击": "敲击", "训击": "拍击", "距": "跳",
    "棒子": "凳子", "受氛": "受挫", "六从": "孤独", "冷囊垫": "冷敷袋",
    "杀子": "镊子", "本圆机": "椭圆机",
}


# 误抓进来的步骤（OCR 把邻近别的程序的内容串进来了），按类别剔除。
REMOVALS = {
    "吃健康食物": {"椭圆机", "跑步机"},
}


def fix_ocr(s: str) -> str:
    for wrong, right in CORRECTIONS.items():
        if wrong in s:
            s = s.replace(wrong, right)
    return s


def _norm(s: str) -> str:
    return re.sub(r"[\s（）()【】\[\]：:，,。．\.、_/“”\"'·]+", "", s)


def parse_blocks(text: str):
    """切成 [(标题, [步骤...])]，跳过页码/领域标题行。"""
    blocks = []
    cur_title, cur_steps = None, []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("====="):
            continue
        if s.startswith("- "):
            step = s[2:].strip()
            if step and cur_title is not None:
                cur_steps.append(step)
            continue
        # 非 bullet = 新标题（领域标题也作为分隔，但不作为 program）
        if cur_title is not None and cur_steps:
            blocks.append((cur_title, cur_steps))
        cur_title, cur_steps = s, []
    if cur_title is not None and cur_steps:
        blocks.append((cur_title, cur_steps))
    return blocks


def best_match(cat: str, blocks):
    """在 blocks 标题里找与 cat 最相近的，返回 steps 或 None。"""
    ncat = _norm(cat)
    best, best_score = None, 0.0
    for title, steps in blocks:
        nt = _norm(title)
        if not nt:
            continue
        if ncat and (ncat in nt or nt in ncat):
            score = 0.9
        else:
            score = SequenceMatcher(None, ncat, nt).ratio()
        if score > best_score:
            best, best_score = steps, score
    if best_score >= 0.5:
        # 去重并限制长度，剔除过长的噪声步骤
        seen, out = set(), []
        for st in best:
            st = st.strip()
            if 1 <= len(st) <= 40 and st not in seen:
                seen.add(st)
                out.append(st)
        return out[:20] if out else None
    return None


def main():
    result = {}
    source = {}   # cat -> "auto" / "校订"
    coverage = {}
    for level, fname in LEVEL_FILE.items():
        path = os.path.join(TEXT_DIR, fname)
        if not os.path.exists(path):
            print(f"⚠️ 缺失 {path}")
            continue
        text = open(path, encoding="utf-8").read()
        blocks = parse_blocks(text)
        cats = NEW_BOOK_CATEGORIES[level]
        hit = 0
        for cat in cats:
            drop = REMOVALS.get(cat, set())
            if cat in OVERRIDES:
                result[cat] = [fix_ocr(s) for s in OVERRIDES[cat] if s not in drop]
                source[cat] = "校订"
                hit += 1
                continue
            steps = best_match(cat, blocks)
            if steps:
                cleaned = [fix_ocr(s) for s in steps]
                cleaned = [s for s in cleaned if s not in drop]
                if cleaned:
                    result[cat] = cleaned
                    source[cat] = "auto"
                    hit += 1
        coverage[level] = (hit, len(cats))
        print(f"  level{level}: {hit}/{len(cats)} 类别有步骤；指南共解析出 {len(blocks)} 个程序块")

    out = os.path.join(_SRC, "MVP_web", "utils", "curriculum_steps_data.py")
    with open(out, "w", encoding="utf-8") as f:
        f.write('"""自动生成：课程指南中每个训练项目的分步骤（含少量 OCR 噪声，仅供参考）。\n')
        f.write('由 src/tools/build_curriculum_steps.py 生成，请勿手改。"""\n\n')
        f.write("STEPS = {\n")
        for cat in sorted(result):
            f.write(f"    {cat!r}: [\n")
            for st in result[cat]:
                f.write(f"        {st!r},\n")
            f.write("    ],\n")
        f.write("}\n")
    print(f"✓ 写出 {out}，共 {len(result)} 个项目带步骤")

    # —— 人工校对清单（列出每个类别 + 步骤 + 来源，便于逐条核对）——
    chk = os.path.join(TEXT_DIR, "步骤校对清单.md")
    label = {3: "初级", 4: "中级", 5: "高级"}
    with open(chk, "w", encoding="utf-8") as f:
        f.write("# 分步训练·步骤校对清单\n\n")
        f.write("> 步骤取自各书《课程指南》。`auto`=程序自动匹配（可能有 OCR 错字/串行），")
        f.write("`校订`=已人工修订。请逐条核对，发现错误直接在本文件改，再让我同步回 STEPS。\n\n")
        total = sum(len(v) for v in NEW_BOOK_CATEGORIES.values())
        f.write(f"覆盖：{len(result)}/{total} 个项目有步骤。\n\n")
        for level in sorted(NEW_BOOK_CATEGORIES):
            f.write(f"\n## {label[level]}技能\n\n")
            for cat in NEW_BOOK_CATEGORIES[level]:
                if cat in result:
                    f.write(f"### {cat}  〔{source[cat]}〕\n")
                    for i, st in enumerate(result[cat], 1):
                        f.write(f"{i}. {st}\n")
                    f.write("\n")
                else:
                    f.write(f"### {cat}  〔未提取·待补〕\n\n")
    print(f"✓ 写出校对清单 {chk}")


if __name__ == "__main__":
    main()
