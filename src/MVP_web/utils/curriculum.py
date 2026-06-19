"""
ABA 课程技能树
整理自课程指南，按领域→技能组→具体目标分层排列。
每个技能有唯一 skill_id，支持按年龄/水平推荐起点。
"""

from typing import List, Dict, Optional

# ─── 技能树 ──────────────────────────────────────────────────
# 结构：领域 → 技能组（list，有顺序）→ 每个技能 dict
#   skill_id: 唯一标识
#   name:     显示名称
#   domain:   所属领域
#   group:    技能组
#   level:    难度 1-3（1=入门，2=基础，3=进阶）
#   next:     掌握后推荐的下一个 skill_id（同组内）
#   description: 给家长看的简短说明
#   flashcard_category: 对应图片卡片的类别名（如有）

SKILLS: List[Dict] = [

    # ══════════════════════════════════════════════════════
    # 参与技能
    # ══════════════════════════════════════════════════════
    {
        "skill_id": "sit_5s",
        "name": "安坐5秒",
        "domain": "参与技能",
        "group": "安坐",
        "level": 1,
        "next": "sit_10s",
        "description": "孩子能安静坐在椅子上5秒。坐好后立即给予强化物。",
        "flashcard_category": None,
    },
    {
        "skill_id": "sit_10s",
        "name": "安坐10秒",
        "domain": "参与技能",
        "group": "安坐",
        "level": 1,
        "next": "sit_30s",
        "description": "孩子能安静坐在椅子上10秒。",
        "flashcard_category": None,
    },
    {
        "skill_id": "sit_30s",
        "name": "安坐30秒并参与活动",
        "domain": "参与技能",
        "group": "安坐",
        "level": 2,
        "next": "sit_3min",
        "description": "孩子能坐30秒并参与训练师选择的活动。",
        "flashcard_category": None,
    },
    {
        "skill_id": "sit_3min",
        "name": "安坐3分钟参与活动",
        "domain": "参与技能",
        "group": "安坐",
        "level": 2,
        "next": None,
        "description": "孩子能持续坐3分钟配合桌面教学活动。",
        "flashcard_category": None,
    },
    {
        "skill_id": "name_response",
        "name": "呼名有眼神回应",
        "domain": "参与技能",
        "group": "呼名反应",
        "level": 1,
        "next": "name_response_activity",
        "description": "叫孩子名字时，孩子能转头并有至少1秒眼神接触。",
        "flashcard_category": None,
    },
    {
        "skill_id": "name_response_activity",
        "name": "活动中呼名有回应",
        "domain": "参与技能",
        "group": "呼名反应",
        "level": 2,
        "next": None,
        "description": "孩子在做其他事情时被叫名字，能转移注意力并有眼神接触。",
        "flashcard_category": None,
    },
    {
        "skill_id": "visual_tracking",
        "name": "视觉追踪（喜欢物品）",
        "domain": "参与技能",
        "group": "视觉追踪",
        "level": 1,
        "next": "visual_tracking_disliked",
        "description": "将孩子喜欢的物品移动到左/右/上/下，孩子能用眼睛追视2秒。",
        "flashcard_category": None,
    },
    {
        "skill_id": "visual_tracking_disliked",
        "name": "视觉追踪（不喜欢物品）",
        "domain": "参与技能",
        "group": "视觉追踪",
        "level": 2,
        "next": None,
        "description": "用不喜欢的物品做视觉追踪练习，泛化追视能力。",
        "flashcard_category": None,
    },

    # 参与技能：进阶
    {
        "skill_id": "follow_1step",
        "name": "听从一步指令",
        "domain": "参与技能",
        "group": "听从指令",
        "level": 1,
        "next": "follow_2step",
        "description": "发出简单指令（坐下/站起/拍手），孩子能在5秒内完成。",
        "flashcard_category": None,
    },
    {
        "skill_id": "follow_2step",
        "name": "听从两步指令",
        "domain": "参与技能",
        "group": "听从指令",
        "level": 2,
        "next": "follow_3step",
        "description": "发出两步连续指令（'拿书，放桌上'），孩子能依次完成。",
        "flashcard_category": None,
    },
    {
        "skill_id": "follow_3step",
        "name": "听从三步指令",
        "domain": "参与技能",
        "group": "听从指令",
        "level": 3,
        "next": None,
        "description": "发出三步指令（'去拿杯子，倒水，放回去'），孩子能独立完成。",
        "flashcard_category": None,
    },
    {
        "skill_id": "group_sit",
        "name": "小组中安坐参与",
        "domain": "参与技能",
        "group": "小组参与",
        "level": 2,
        "next": "group_turn_taking",
        "description": "在2-3人小组中，孩子能安坐等待轮到自己，不干扰他人。",
        "flashcard_category": None,
    },
    {
        "skill_id": "group_turn_taking",
        "name": "小组中轮流等待",
        "domain": "参与技能",
        "group": "小组参与",
        "level": 3,
        "next": None,
        "description": "小组活动中，孩子能理解并遵守轮流规则，等待自己的回合。",
        "flashcard_category": None,
    },

    # ══════════════════════════════════════════════════════
    # 模仿技能
    # ══════════════════════════════════════════════════════
    {
        "skill_id": "gross_motor_imitation",
        "name": "粗大动作模仿（举手/鼓掌）",
        "domain": "模仿技能",
        "group": "粗大动作模仿",
        "level": 1,
        "next": "gross_motor_imitation2",
        "description": "家长做举手、鼓掌等动作，孩子能模仿。每次只示范一个动作，等待3秒。",
        "flashcard_category": None,
    },
    {
        "skill_id": "gross_motor_imitation2",
        "name": "粗大动作模仿（跺脚/转身）",
        "domain": "模仿技能",
        "group": "粗大动作模仿",
        "level": 2,
        "next": None,
        "description": "扩展到更多粗大动作：跺脚、转身、跳跃等。",
        "flashcard_category": None,
    },
    {
        "skill_id": "object_imitation",
        "name": "使用物品模仿（积木/敲鼓）",
        "domain": "模仿技能",
        "group": "物品模仿",
        "level": 1,
        "next": "fine_motor_imitation",
        "description": "家长用积木、鼓等玩具做动作，孩子能模仿同样的操作。",
        "flashcard_category": None,
    },
    {
        "skill_id": "fine_motor_imitation",
        "name": "精细动作模仿（摸鼻/弯手指）",
        "domain": "模仿技能",
        "group": "精细动作模仿",
        "level": 2,
        "next": None,
        "description": "模仿摸鼻子、弯手指、搓手等精细动作。",
        "flashcard_category": None,
    },

    # 模仿技能：进阶
    {
        "skill_id": "oral_motor_imitation",
        "name": "口腔动作模仿",
        "domain": "模仿技能",
        "group": "口腔动作模仿",
        "level": 1,
        "next": "vocal_imitation",
        "description": "模仿张嘴、伸舌、噘嘴、吹气等口腔动作，为语音发展打基础。",
        "flashcard_category": None,
    },
    {
        "skill_id": "vocal_imitation",
        "name": "声音模仿（仿说）",
        "domain": "模仿技能",
        "group": "口腔动作模仿",
        "level": 2,
        "next": "vocal_imitation_words",
        "description": "模仿单个元音/辅音或简单音节（如'啊''ba''ma'），每次示范后等待5秒。",
        "flashcard_category": None,
    },
    {
        "skill_id": "vocal_imitation_words",
        "name": "仿说单词",
        "domain": "模仿技能",
        "group": "口腔动作模仿",
        "level": 3,
        "next": None,
        "description": "听到单词后立即模仿说出，覆盖孩子日常生活中常用词汇。",
        "flashcard_category": None,
    },
    {
        "skill_id": "sequential_imitation",
        "name": "序列动作模仿（2步）",
        "domain": "模仿技能",
        "group": "序列模仿",
        "level": 2,
        "next": "sequential_imitation3",
        "description": "模仿连续两个动作的序列（如：拍手→摸头），强化工作记忆。",
        "flashcard_category": None,
    },
    {
        "skill_id": "sequential_imitation3",
        "name": "序列动作模仿（3步）",
        "domain": "模仿技能",
        "group": "序列模仿",
        "level": 3,
        "next": None,
        "description": "模仿三步动作序列，提升顺序记忆与动作规划能力。",
        "flashcard_category": None,
    },

    # ══════════════════════════════════════════════════════
    # 视觉空间技能
    # ══════════════════════════════════════════════════════
    {
        "skill_id": "match_same_objects",
        "name": "配对相同物品",
        "domain": "视觉空间技能",
        "group": "配对",
        "level": 1,
        "next": "match_same_pictures",
        "description": "桌上放一个物品，给孩子一个相同的，让他放到对应位置。",
        "flashcard_category": None,
    },
    {
        "skill_id": "match_same_pictures",
        "name": "配对相同图片",
        "domain": "视觉空间技能",
        "group": "配对",
        "level": 1,
        "next": "match_colors",
        "description": "展示图片卡，孩子能将相同的图片配对在一起。",
        "flashcard_category": "配对相同的图片",
    },
    {
        "skill_id": "match_colors",
        "name": "配对颜色",
        "domain": "视觉空间技能",
        "group": "配对",
        "level": 1,
        "next": "match_shapes",
        "description": "将相同颜色的卡片配对（红-红、蓝-蓝等）。",
        "flashcard_category": "配对颜色",
    },
    {
        "skill_id": "match_shapes",
        "name": "配对形状",
        "domain": "视觉空间技能",
        "group": "配对",
        "level": 2,
        "next": "match_numbers",
        "description": "配对圆形、正方形、三角形等形状卡片。",
        "flashcard_category": "配对形状",
    },
    {
        "skill_id": "match_numbers",
        "name": "配对数字",
        "domain": "视觉空间技能",
        "group": "配对",
        "level": 2,
        "next": "match_letters",
        "description": "配对1-10的数字卡片。",
        "flashcard_category": "配对数字",
    },
    {
        "skill_id": "match_letters",
        "name": "配对字母",
        "domain": "视觉空间技能",
        "group": "配对",
        "level": 2,
        "next": "match_different_pictures",
        "description": "配对相同的大写字母卡片。",
        "flashcard_category": "配对相同的图片",
    },
    {
        "skill_id": "match_different_pictures",
        "name": "配对不同图片（同类别）",
        "domain": "视觉空间技能",
        "group": "配对",
        "level": 3,
        "next": "classify_category",
        "description": "配对同一类别的不同图片，如大卡车和小卡车都属于'卡车'。",
        "flashcard_category": "配对不同的图片",
    },
    {
        "skill_id": "classify_category",
        "name": "根据类别分类",
        "domain": "视觉空间技能",
        "group": "分类",
        "level": 3,
        "next": None,
        "description": "将图片或物品按照动物/食物/交通工具等类别分组放置。",
        "flashcard_category": "根据类别分类",
    },
    {
        "skill_id": "classify_color",
        "name": "根据颜色分类",
        "domain": "视觉空间技能",
        "group": "分类",
        "level": 2,
        "next": "classify_size",
        "description": "把不同物品按颜色分成几组。",
        "flashcard_category": "根据颜色给图片分类",
    },
    {
        "skill_id": "classify_size",
        "name": "根据大小分类",
        "domain": "视觉空间技能",
        "group": "分类",
        "level": 2,
        "next": "classify_category",
        "description": "将物品/图片按大/小两组分类。",
        "flashcard_category": "根据大小给图片分类",
    },

    # 视觉空间：进阶
    {
        "skill_id": "sequence_2",
        "name": "排序（2步顺序）",
        "domain": "视觉空间技能",
        "group": "排序",
        "level": 2,
        "next": "sequence_3",
        "description": "将两张有顺序关系的图片（如早上/晚上，小种子/大树）按正确顺序排列。",
        "flashcard_category": None,
    },
    {
        "skill_id": "sequence_3",
        "name": "排序（3-4步顺序）",
        "domain": "视觉空间技能",
        "group": "排序",
        "level": 3,
        "next": None,
        "description": "将3-4步事件序列图片（如刷牙步骤、做三明治）按正确顺序排列。",
        "flashcard_category": None,
    },
    {
        "skill_id": "puzzles_4",
        "name": "完成拼图（4块）",
        "domain": "视觉空间技能",
        "group": "拼图",
        "level": 1,
        "next": "puzzles_8",
        "description": "独立完成4块简单拼图，培养视觉空间推理和手眼协调。",
        "flashcard_category": None,
    },
    {
        "skill_id": "puzzles_8",
        "name": "完成拼图（8块以上）",
        "domain": "视觉空间技能",
        "group": "拼图",
        "level": 2,
        "next": None,
        "description": "独立完成8块及以上拼图，进一步提升视觉空间能力。",
        "flashcard_category": None,
    },

    # ══════════════════════════════════════════════════════
    # 语言技能
    # ══════════════════════════════════════════════════════
    # 接受性：进阶
    {
        "skill_id": "receptive_animals",
        "name": "接受性语言：指认动物",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 1,
        "next": "receptive_food",
        "description": "摆出3张动物图片，说'指狗'，孩子能正确指认。从2选1开始，逐步增加干扰项。",
        "flashcard_category": "接受性和表达性语言技能（动物）",
    },
    {
        "skill_id": "receptive_food",
        "name": "接受性语言：指认食物",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 1,
        "next": "receptive_fruit",
        "description": "摆出食物图片，孩子能根据指令指认正确的食物。",
        "flashcard_category": "接受性和表达性语言技能（食物和饮料）",
    },
    {
        "skill_id": "receptive_fruit",
        "name": "接受性语言：指认水果",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 1,
        "next": "receptive_vegetable",
        "description": "摆出水果图片（苹果/香蕉/橙子等），说'指苹果'，孩子能正确指认。",
        "flashcard_category": "水果",
    },
    {
        "skill_id": "receptive_vegetable",
        "name": "接受性语言：指认蔬菜",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 1,
        "next": "receptive_body",
        "description": "摆出蔬菜图片（胡萝卜/番茄/玉米等），孩子能根据指令指认正确的蔬菜。",
        "flashcard_category": "蔬菜",
    },
    {
        "skill_id": "receptive_body",
        "name": "接受性语言：身体部位",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 2,
        "next": "receptive_actions",
        "description": "说'摸鼻子/摸耳朵'等，孩子能正确触摸对应部位。",
        "flashcard_category": "接受性和表达性语言技能（身体部位）",
    },
    {
        "skill_id": "receptive_actions",
        "name": "接受性语言：理解动作词",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 2,
        "next": "receptive_colors",
        "description": "展示动作图片（跑/跳/吃饭），孩子能根据指令指认。",
        "flashcard_category": "接受性和表达性语言技能（动作）",
    },
    {
        "skill_id": "receptive_colors",
        "name": "接受性语言：颜色",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 2,
        "next": "receptive_weather",
        "description": "说出颜色名，孩子能从多张卡中指认正确的颜色。",
        "flashcard_category": "接受性和表达性语言技能（颜色）",
    },
    {
        "skill_id": "receptive_weather",
        "name": "接受性语言：认识天气",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 2,
        "next": "receptive_occupation",
        "description": "展示天气图片（晴天/下雨/下雪等），孩子能根据指令指认对应天气。",
        "flashcard_category": "天气",
    },
    {
        "skill_id": "receptive_occupation",
        "name": "接受性语言：认识职业",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 2,
        "next": "receptive_places",
        "description": "展示职业人物图片（医生/老师/警察等），孩子能根据指令指认对应职业。",
        "flashcard_category": "职业人物",
    },
    {
        "skill_id": "receptive_places",
        "name": "接受性语言：场所",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 3,
        "next": None,
        "description": "指认学校、医院、超市等场所图片。",
        "flashcard_category": "接受性和表达性语言技能（场所）",
    },

    {
        "skill_id": "receptive_prepositions",
        "name": "接受性语言：方位词",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 2,
        "next": "receptive_adjectives",
        "description": "根据指令将物品放到'上面/下面/里面/旁边'，理解方位概念。",
        "flashcard_category": None,
    },
    {
        "skill_id": "receptive_adjectives",
        "name": "接受性语言：形容词",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 3,
        "next": "receptive_wh",
        "description": "根据指令指认大/小、热/冷、快/慢等对立形容词对应的图片或物品。",
        "flashcard_category": None,
    },
    {
        "skill_id": "receptive_wh",
        "name": "接受性语言：理解特殊疑问词",
        "domain": "语言技能",
        "group": "接受性语言",
        "level": 3,
        "next": None,
        "description": "理解'谁/什么/在哪里'等疑问词的含义，并从图片中做出正确选择。",
        "flashcard_category": None,
    },

    # 语言技能：表达性（进阶）
    {
        "skill_id": "expressive_animals",
        "name": "表达性语言：命名动物",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 2,
        "next": "expressive_food",
        "description": "展示动物图片，问'这是什么'，孩子能说出名称（或用手势/AAC）。",
        "flashcard_category": "接受性和表达性语言技能（动物）",
    },
    {
        "skill_id": "expressive_food",
        "name": "表达性语言：命名食物",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 2,
        "next": "expressive_fruit",
        "description": "展示食物图片，孩子能说出食物名称。",
        "flashcard_category": "接受性和表达性语言技能（食物和饮料）",
    },
    {
        "skill_id": "expressive_fruit",
        "name": "表达性语言：命名水果",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 2,
        "next": "expressive_vegetable",
        "description": "展示水果图片，孩子能说出水果名称（苹果/香蕉/西瓜等）。",
        "flashcard_category": "水果",
    },
    {
        "skill_id": "expressive_vegetable",
        "name": "表达性语言：命名蔬菜",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 2,
        "next": "expressive_body",
        "description": "展示蔬菜图片，孩子能说出蔬菜名称（胡萝卜/番茄/玉米等）。",
        "flashcard_category": "蔬菜",
    },
    {
        "skill_id": "expressive_body",
        "name": "表达性语言：命名身体部位",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 2,
        "next": "expressive_colors",
        "description": "指着身体部位，孩子能说出名称。",
        "flashcard_category": "接受性和表达性语言技能（身体部位）",
    },
    {
        "skill_id": "expressive_colors",
        "name": "表达性语言：命名颜色",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 3,
        "next": "expressive_actions",
        "description": "展示颜色卡，孩子能说出颜色名称。",
        "flashcard_category": "接受性和表达性语言技能（颜色）",
    },
    {
        "skill_id": "expressive_actions",
        "name": "表达性语言：描述动作",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 3,
        "next": "expressive_weather",
        "description": "展示动作图片，孩子能用词语描述（如'跑''跳'）。",
        "flashcard_category": "接受性和表达性语言技能（动作）",
    },
    {
        "skill_id": "expressive_weather",
        "name": "表达性语言：描述天气",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 3,
        "next": "expressive_occupation",
        "description": "展示天气图片，孩子能说出天气名称（晴天/下雨/刮风等）。",
        "flashcard_category": "天气",
    },
    {
        "skill_id": "expressive_occupation",
        "name": "表达性语言：命名职业",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 3,
        "next": None,
        "description": "展示职业人物图片，孩子能说出职业名称（医生/老师/消防员等）。",
        "flashcard_category": "职业人物",
    },
    {
        "skill_id": "expressive_attributes",
        "name": "表达性语言：描述属性",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 3,
        "next": "expressive_function",
        "description": "说出物品的颜色+名称（'红色苹果'）或大小+名称（'大狗'），两词组合。",
        "flashcard_category": None,
    },
    {
        "skill_id": "expressive_function",
        "name": "表达性语言：描述功能",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 3,
        "next": "expressive_category",
        "description": "问'杯子用来做什么'，孩子能说出功能（'喝水'）。",
        "flashcard_category": None,
    },
    {
        "skill_id": "expressive_category",
        "name": "表达性语言：说出类别",
        "domain": "语言技能",
        "group": "表达性语言",
        "level": 3,
        "next": None,
        "description": "问'狗是什么类别的？'孩子能回答'动物'；问'苹果属于什么？'能回答'水果/食物'。",
        "flashcard_category": None,
    },

    # 语言技能：提要求（Mand）
    {
        "skill_id": "mand_reach",
        "name": "提要求：伸手/眼神示意",
        "domain": "语言技能",
        "group": "提要求",
        "level": 1,
        "next": "mand_gesture",
        "description": "孩子能通过伸手、眼神或靠近物品来表达需求，家长及时回应并命名物品。",
        "flashcard_category": None,
    },
    {
        "skill_id": "mand_gesture",
        "name": "提要求：用手势/指点",
        "domain": "语言技能",
        "group": "提要求",
        "level": 1,
        "next": "mand_single_word",
        "description": "孩子能用指点或手势明确表达想要某个物品或活动。",
        "flashcard_category": None,
    },
    {
        "skill_id": "mand_single_word",
        "name": "提要求：单词提要求",
        "domain": "语言技能",
        "group": "提要求",
        "level": 2,
        "next": "mand_phrase",
        "description": "孩子能用单个词语主动提出需求（'饼干''出去''要'）。",
        "flashcard_category": None,
    },
    {
        "skill_id": "mand_phrase",
        "name": "提要求：短语提要求",
        "domain": "语言技能",
        "group": "提要求",
        "level": 2,
        "next": "mand_help",
        "description": "孩子能用短语提要求（'我要饼干''帮我打开'）。",
        "flashcard_category": None,
    },
    {
        "skill_id": "mand_help",
        "name": "提要求：请求帮助",
        "domain": "语言技能",
        "group": "提要求",
        "level": 2,
        "next": "mand_break",
        "description": "孩子遇到困难时能主动说'帮忙'或'帮我'，而不是哭闹或放弃。",
        "flashcard_category": None,
    },
    {
        "skill_id": "mand_break",
        "name": "提要求：请求休息",
        "domain": "语言技能",
        "group": "提要求",
        "level": 3,
        "next": None,
        "description": "孩子感到疲惫或不想继续时能说'休息'或使用休息卡，而非用行为问题表达。",
        "flashcard_category": None,
    },

    # 语言技能：对话/问答（Intraverbal）
    {
        "skill_id": "intraverbal_greetings",
        "name": "对话：打招呼回应",
        "domain": "语言技能",
        "group": "对话与问答",
        "level": 1,
        "next": "intraverbal_name",
        "description": "别人说'你好'时能回应'你好'；别人说'再见'能说'再见'。",
        "flashcard_category": None,
    },
    {
        "skill_id": "intraverbal_name",
        "name": "对话：回答姓名",
        "domain": "语言技能",
        "group": "对话与问答",
        "level": 1,
        "next": "intraverbal_age",
        "description": "被问'你叫什么名字？'能正确说出自己的名字。",
        "flashcard_category": None,
    },
    {
        "skill_id": "intraverbal_age",
        "name": "对话：回答年龄",
        "domain": "语言技能",
        "group": "对话与问答",
        "level": 2,
        "next": "intraverbal_fill",
        "description": "被问'你几岁了？'能正确说出年龄，可配合手指数字。",
        "flashcard_category": None,
    },
    {
        "skill_id": "intraverbal_fill",
        "name": "对话：填充句子",
        "domain": "语言技能",
        "group": "对话与问答",
        "level": 2,
        "next": "intraverbal_wh",
        "description": "完成熟悉的句子（'小猫叫___''苹果是___色的'），培养联想和语言流畅性。",
        "flashcard_category": None,
    },
    {
        "skill_id": "intraverbal_wh",
        "name": "对话：回答特殊疑问",
        "domain": "语言技能",
        "group": "对话与问答",
        "level": 3,
        "next": "intraverbal_conversation",
        "description": "正确回答'什么/谁/在哪里/做什么'等问题（如'狗住在哪里？'→'狗窝'）。",
        "flashcard_category": None,
    },
    {
        "skill_id": "intraverbal_conversation",
        "name": "对话：简单双向对话",
        "domain": "语言技能",
        "group": "对话与问答",
        "level": 3,
        "next": None,
        "description": "能就熟悉话题（喜欢的食物/游戏）进行2-3个来回的对话交流。",
        "flashcard_category": None,
    },

    # ══════════════════════════════════════════════════════
    # 游戏技能（基于 VB-MAPP Play Skill Milestones）
    # ══════════════════════════════════════════════════════
    {
        "skill_id": "play_sensory",
        "name": "感觉游戏：探索玩具",
        "domain": "游戏技能",
        "group": "独立游戏",
        "level": 1,
        "next": "play_functional",
        "description": "孩子能自发地触摸、摇晃、探索玩具至少1分钟，无需大人持续引导。",
        "flashcard_category": None,
    },
    {
        "skill_id": "play_functional",
        "name": "功能性玩耍",
        "domain": "游戏技能",
        "group": "独立游戏",
        "level": 1,
        "next": "play_independent_5min",
        "description": "以正确方式使用玩具（推车、叠积木、推小汽车），而非无目的地摆弄。",
        "flashcard_category": None,
    },
    {
        "skill_id": "play_independent_5min",
        "name": "独立玩耍5分钟",
        "domain": "游戏技能",
        "group": "独立游戏",
        "level": 2,
        "next": "play_independent_15min",
        "description": "无大人陪伴的情况下，孩子能独立进行喜欢的活动至少5分钟。",
        "flashcard_category": None,
    },
    {
        "skill_id": "play_independent_15min",
        "name": "独立玩耍15分钟",
        "domain": "游戏技能",
        "group": "独立游戏",
        "level": 3,
        "next": None,
        "description": "孩子能独自玩耍15分钟，期间能自行切换不同活动。",
        "flashcard_category": None,
    },
    {
        "skill_id": "play_pretend_single",
        "name": "假装游戏：单步动作",
        "domain": "游戏技能",
        "group": "假装游戏",
        "level": 2,
        "next": "play_pretend_sequence",
        "description": "假装给玩具娃娃喂食、打电话等单步假装动作，模仿日常生活场景。",
        "flashcard_category": None,
    },
    {
        "skill_id": "play_pretend_sequence",
        "name": "假装游戏：情景序列",
        "domain": "游戏技能",
        "group": "假装游戏",
        "level": 3,
        "next": "play_pretend_peer",
        "description": "演示有情节的假装游戏（如给娃娃洗澡→穿衣→哄睡），包含3步以上。",
        "flashcard_category": None,
    },
    {
        "skill_id": "play_pretend_peer",
        "name": "假装游戏：与同伴共同假装",
        "domain": "游戏技能",
        "group": "假装游戏",
        "level": 3,
        "next": None,
        "description": "与同伴进行角色扮演游戏（医生/病人、厨师/顾客），能跟随游戏情节。",
        "flashcard_category": None,
    },
    {
        "skill_id": "play_parallel",
        "name": "平行游戏",
        "domain": "游戏技能",
        "group": "社交游戏",
        "level": 2,
        "next": "play_cooperative",
        "description": "孩子能在同伴旁边玩相似的活动（各自搭积木），无需互动，但能容忍靠近。",
        "flashcard_category": None,
    },
    {
        "skill_id": "play_cooperative",
        "name": "合作游戏（轮流）",
        "domain": "游戏技能",
        "group": "社交游戏",
        "level": 3,
        "next": "play_board_game",
        "description": "和1-2个同伴进行需要轮流的游戏（传球、棋盘游戏），能等待轮到自己。",
        "flashcard_category": None,
    },
    {
        "skill_id": "play_board_game",
        "name": "桌游规则游戏",
        "domain": "游戏技能",
        "group": "社交游戏",
        "level": 3,
        "next": None,
        "description": "能遵守简单桌游规则（如记忆翻牌、捕鱼游戏），包括赢/输的接受。",
        "flashcard_category": None,
    },

    # ══════════════════════════════════════════════════════
    # 社交技能（基于 VB-MAPP Social Skills & Joint Attention）
    # ══════════════════════════════════════════════════════
    {
        "skill_id": "jt_follow_point",
        "name": "共同注意：跟随他人指点",
        "domain": "社交技能",
        "group": "共同注意",
        "level": 1,
        "next": "jt_point_request",
        "description": "大人指着远处物品时，孩子能转头看向同一方向（而不是只看手指）。",
        "flashcard_category": None,
    },
    {
        "skill_id": "jt_point_request",
        "name": "共同注意：指点提要求",
        "domain": "社交技能",
        "group": "共同注意",
        "level": 1,
        "next": "jt_point_share",
        "description": "孩子能用食指指向想要的物品来提要求，同时看向大人确认。",
        "flashcard_category": None,
    },
    {
        "skill_id": "jt_point_share",
        "name": "共同注意：分享性指点",
        "domain": "社交技能",
        "group": "共同注意",
        "level": 2,
        "next": "jt_show",
        "description": "孩子主动指向有趣的事物并看向大人，分享兴趣（不是为了获得物品）。",
        "flashcard_category": None,
    },
    {
        "skill_id": "jt_show",
        "name": "共同注意：展示物品",
        "domain": "社交技能",
        "group": "共同注意",
        "level": 2,
        "next": None,
        "description": "孩子主动把物品拿给大人看，等待对方的反应，体现分享注意力的意愿。",
        "flashcard_category": None,
    },
    {
        "skill_id": "social_greet",
        "name": "社交：主动问好",
        "domain": "社交技能",
        "group": "基础社交",
        "level": 1,
        "next": "social_eye_contact",
        "description": "进入房间或遇到熟悉的人时，孩子能主动说'你好/早上好'（或点头/挥手）。",
        "flashcard_category": None,
    },
    {
        "skill_id": "social_eye_contact",
        "name": "社交：交流中维持眼神",
        "domain": "社交技能",
        "group": "基础社交",
        "level": 1,
        "next": "social_name_call",
        "description": "在对话或游戏互动中，孩子能自发地（不需提示）看向对方的脸部1-2秒。",
        "flashcard_category": None,
    },
    {
        "skill_id": "social_name_call",
        "name": "社交：叫同伴名字",
        "domain": "社交技能",
        "group": "基础社交",
        "level": 2,
        "next": "social_initiate_play",
        "description": "孩子能用名字或'喂'来呼唤同伴，吸引对方注意（而非直接拉拽）。",
        "flashcard_category": None,
    },
    {
        "skill_id": "social_initiate_play",
        "name": "社交：主动邀请同伴游戏",
        "domain": "社交技能",
        "group": "同伴互动",
        "level": 2,
        "next": "social_respond_peer",
        "description": "孩子能主动说'一起玩''要不要玩XXX'来邀请同伴，而非等待被邀请。",
        "flashcard_category": None,
    },
    {
        "skill_id": "social_respond_peer",
        "name": "社交：回应同伴互动",
        "domain": "社交技能",
        "group": "同伴互动",
        "level": 2,
        "next": "social_share",
        "description": "同伴发起互动（递玩具、问问题）时，孩子能做出适当的语言或行为回应。",
        "flashcard_category": None,
    },
    {
        "skill_id": "social_share",
        "name": "社交：主动分享",
        "domain": "社交技能",
        "group": "同伴互动",
        "level": 3,
        "next": "social_comfort",
        "description": "孩子能主动把食物、玩具或活动机会分给同伴，无需大人提示。",
        "flashcard_category": None,
    },
    {
        "skill_id": "social_comfort",
        "name": "社交：安慰他人",
        "domain": "社交技能",
        "group": "同伴互动",
        "level": 3,
        "next": None,
        "description": "看到他人哭泣或难过时，孩子能做出安慰性行为（拍拍背、说'没关系'）。",
        "flashcard_category": None,
    },

    # ══════════════════════════════════════════════════════
    # 情绪调节技能
    # ══════════════════════════════════════════════════════
    {
        "skill_id": "emotion_id_basic",
        "name": "识别基本情绪（图片）",
        "domain": "情绪调节技能",
        "group": "情绪识别",
        "level": 1,
        "next": "emotion_id_real",
        "description": "从表情图片中指认开心/难过/生气/害怕4种基本情绪。",
        "flashcard_category": "情绪表情",
    },
    {
        "skill_id": "emotion_id_real",
        "name": "识别真实情境中的情绪",
        "domain": "情绪调节技能",
        "group": "情绪识别",
        "level": 2,
        "next": "emotion_express",
        "description": "在日常情境中能识别他人的情绪（'妈妈在笑，她开心'）。",
        "flashcard_category": "情绪表情",
    },
    {
        "skill_id": "emotion_express",
        "name": "表达自己的情绪",
        "domain": "情绪调节技能",
        "group": "情绪表达",
        "level": 2,
        "next": "emotion_cause",
        "description": "孩子能用词语表达当前的感受（'我很开心''我不喜欢'），而非用哭闹表达。",
        "flashcard_category": "情绪表情",
    },
    {
        "skill_id": "emotion_cause",
        "name": "理解情绪原因",
        "domain": "情绪调节技能",
        "group": "情绪理解",
        "level": 3,
        "next": None,
        "description": "能说出情绪的原因（'因为得到了糖果所以开心''因为玩具被拿走了所以生气'）。",
        "flashcard_category": None,
    },
    {
        "skill_id": "wait_5s",
        "name": "等待5秒",
        "domain": "情绪调节技能",
        "group": "等待与延迟",
        "level": 1,
        "next": "wait_1min",
        "description": "要求等待时（说'等一下'），孩子能安静等待5秒再得到强化物。",
        "flashcard_category": None,
    },
    {
        "skill_id": "wait_1min",
        "name": "等待1分钟",
        "domain": "情绪调节技能",
        "group": "等待与延迟",
        "level": 2,
        "next": "accept_no",
        "description": "孩子能等待1分钟，期间可以用等待卡或做其他活动过渡。",
        "flashcard_category": None,
    },
    {
        "skill_id": "accept_no",
        "name": "接受拒绝/接受'不'",
        "domain": "情绪调节技能",
        "group": "等待与延迟",
        "level": 2,
        "next": "cope_strategy",
        "description": "听到'不行/没有'时，孩子能接受并继续当前活动，不出现激烈的问题行为。",
        "flashcard_category": None,
    },
    {
        "skill_id": "cope_strategy",
        "name": "使用应对策略",
        "domain": "情绪调节技能",
        "group": "自我调节",
        "level": 3,
        "next": None,
        "description": "沮丧或焦虑时，孩子能使用已学的策略（深呼吸、找人帮助、去安静角落）。",
        "flashcard_category": None,
    },

    # ══════════════════════════════════════════════════════
    # 学业前技能（Pre-academic，基于 ABLLS-R 学业技能）
    # ══════════════════════════════════════════════════════
    {
        "skill_id": "pre_color_name",
        "name": "说出颜色名称",
        "domain": "学业前技能",
        "group": "颜色与形状",
        "level": 1,
        "next": "pre_shape_name",
        "description": "看到颜色块/物品时能说出名称（红/黄/蓝/绿4种基础颜色）。",
        "flashcard_category": "接受性和表达性语言技能（颜色）",
    },
    {
        "skill_id": "pre_shape_name",
        "name": "说出形状名称",
        "domain": "学业前技能",
        "group": "颜色与形状",
        "level": 1,
        "next": "pre_count_5",
        "description": "能说出圆形、正方形、三角形、长方形的名称。",
        "flashcard_category": "接受性和表达性语言技能（形状）",
    },
    {
        "skill_id": "pre_count_5",
        "name": "口头数数1-5",
        "domain": "学业前技能",
        "group": "数概念",
        "level": 1,
        "next": "pre_count_10",
        "description": "按顺序说出1-5，可配合手指。",
        "flashcard_category": None,
    },
    {
        "skill_id": "pre_count_10",
        "name": "口头数数1-10",
        "domain": "学业前技能",
        "group": "数概念",
        "level": 2,
        "next": "pre_count_objects",
        "description": "按顺序说出1-10，流畅无中断。",
        "flashcard_category": None,
    },
    {
        "skill_id": "pre_count_objects",
        "name": "点数实物1-5",
        "domain": "学业前技能",
        "group": "数概念",
        "level": 2,
        "next": "pre_number_id",
        "description": "用手逐个点数眼前的实物，说出总数（'一共有3个'）。",
        "flashcard_category": None,
    },
    {
        "skill_id": "pre_number_id",
        "name": "认识数字1-5",
        "domain": "学业前技能",
        "group": "数概念",
        "level": 2,
        "next": "pre_number_id10",
        "description": "看到数字卡片能说出对应的数字名称（1-5）。",
        "flashcard_category": "配对数字",
    },
    {
        "skill_id": "pre_number_id10",
        "name": "认识数字1-10",
        "domain": "学业前技能",
        "group": "数概念",
        "level": 3,
        "next": None,
        "description": "认识1-10的阿拉伯数字，能从一组数字中指出指定数字。",
        "flashcard_category": "配对数字",
    },
    {
        "skill_id": "pre_letter_id",
        "name": "认识字母A-E",
        "domain": "学业前技能",
        "group": "字母与文字",
        "level": 2,
        "next": "pre_letter_id_full",
        "description": "从字母卡中识别A/B/C/D/E，能说出字母名称。",
        "flashcard_category": "配对大写字母和小写字母",
    },
    {
        "skill_id": "pre_letter_id_full",
        "name": "认识全部大写字母",
        "domain": "学业前技能",
        "group": "字母与文字",
        "level": 3,
        "next": "pre_write_name",
        "description": "识别A-Z全部26个大写字母，指认正确率≥80%。",
        "flashcard_category": "配对大写字母和小写字母",
    },
    {
        "skill_id": "pre_write_name",
        "name": "书写自己的名字",
        "domain": "学业前技能",
        "group": "字母与文字",
        "level": 3,
        "next": None,
        "description": "孩子能独立书写自己名字的首字母或全名（根据能力设定目标）。",
        "flashcard_category": None,
    },

    # ══════════════════════════════════════════════════════
    # 自理技能（Daily Living Skills，基于 ABLLS-R 自理领域）
    # ══════════════════════════════════════════════════════
    {
        "skill_id": "self_wash_hands",
        "name": "独立洗手",
        "domain": "自理技能",
        "group": "个人卫生",
        "level": 1,
        "next": "self_brush_teeth",
        "description": "独立完成洗手全流程：开水→涂皂→搓手→冲洗→擦干（可用图示提示）。",
        "flashcard_category": None,
    },
    {
        "skill_id": "self_brush_teeth",
        "name": "配合刷牙",
        "domain": "自理技能",
        "group": "个人卫生",
        "level": 1,
        "next": "self_brush_independent",
        "description": "孩子能配合他人帮助刷牙，不逃跑、不激烈抗拒，持续约2分钟。",
        "flashcard_category": "日常自理活动",
    },
    {
        "skill_id": "self_brush_independent",
        "name": "独立刷牙",
        "domain": "自理技能",
        "group": "个人卫生",
        "level": 2,
        "next": None,
        "description": "孩子能独立完成刷牙（前后左右各刷），家长只需监督不需辅助。",
        "flashcard_category": "日常自理活动",
    },
    {
        "skill_id": "self_dress_help",
        "name": "配合穿脱衣物",
        "domain": "自理技能",
        "group": "穿衣",
        "level": 1,
        "next": "self_dress_simple",
        "description": "孩子能配合大人穿脱衣物，能举手、抬脚等动作配合。",
        "flashcard_category": "日常自理活动",
    },
    {
        "skill_id": "self_dress_simple",
        "name": "独立穿脱简单衣物",
        "domain": "自理技能",
        "group": "穿衣",
        "level": 2,
        "next": "self_dress_full",
        "description": "能独立穿脱没有扣子的上衣、松紧裤、袜子。",
        "flashcard_category": None,
    },
    {
        "skill_id": "self_dress_full",
        "name": "独立穿脱全套衣物",
        "domain": "自理技能",
        "group": "穿衣",
        "level": 3,
        "next": None,
        "description": "能独立穿脱包含拉链/扣子的衣物，并能整理好衣领、衣角。",
        "flashcard_category": None,
    },
    {
        "skill_id": "self_eat_utensil",
        "name": "用餐具进食",
        "domain": "自理技能",
        "group": "进食",
        "level": 1,
        "next": "self_eat_variety",
        "description": "能用勺子或叉子独立进食，将食物从碗里送入嘴中，洒漏不超过30%。",
        "flashcard_category": None,
    },
    {
        "skill_id": "self_eat_variety",
        "name": "接受多样食物",
        "domain": "自理技能",
        "group": "进食",
        "level": 2,
        "next": None,
        "description": "孩子能接受至少10种不同食物，包括不同质地、颜色和味道的食物。",
        "flashcard_category": None,
    },
    {
        "skill_id": "self_toilet_indicate",
        "name": "如厕：表达需求",
        "domain": "自理技能",
        "group": "如厕",
        "level": 1,
        "next": "self_toilet_independent",
        "description": "孩子能在需要上厕所时主动表达（说'厕所'、拉大人或使用如厕卡），而非直接尿湿。",
        "flashcard_category": None,
    },
    {
        "skill_id": "self_toilet_independent",
        "name": "如厕：独立如厕",
        "domain": "自理技能",
        "group": "如厕",
        "level": 2,
        "next": None,
        "description": "孩子能独立完成如厕全流程：去厕所→脱裤→上厕所→擦拭→提裤→冲水→洗手。",
        "flashcard_category": None,
    },
]

# ── 接入新增三本书（初级/中级/高级）的自动生成技能 ──────────────
# 这些技能由卡片类别名自动生成（见 utils/curriculum_extra.py）。
# level 3=初级 / 4=中级 / 5=高级（比 basic 书更进阶；起点推荐 get_starter_skills
# 上限为 level≤3，故 4/5 不会被当作「起点」推荐，但可在技能选择器/任务里手动选用）。
try:
    from utils.curriculum_extra import build_extra_skills
    SKILLS.extend(build_extra_skills(SKILLS))
except Exception as _e:  # 数据缺失时不影响基础课程
    print(f"⚠️ 加载扩展课程失败（仅影响新增书本技能）: {_e}")

# ── 快速查询工具 ─────────────────────────────────────────────

_skill_by_id: Dict[str, Dict] = {s["skill_id"]: s for s in SKILLS}


def get_skill(skill_id: str) -> Optional[Dict]:
    return _skill_by_id.get(skill_id)


def get_next_skill(skill_id: str) -> Optional[Dict]:
    s = _skill_by_id.get(skill_id)
    if s and s.get("next"):
        return _skill_by_id.get(s["next"])
    return None


def get_skills_by_domain(domain: str) -> List[Dict]:
    return [s for s in SKILLS if s["domain"] == domain]


def get_all_domains() -> List[str]:
    seen, domains = set(), []
    for s in SKILLS:
        if s["domain"] not in seen:
            domains.append(s["domain"])
            seen.add(s["domain"])
    return domains


def get_starter_skills(age: int, existing_skill_ids: List[str] = None,
                       max_per_domain: int = 1, max_total: int = 9) -> List[Dict]:
    """
    按年龄和领域优先级推荐起点技能，每个领域各选一个。
    覆盖所有9个领域，总数不超过 max_total。

    领域优先级（从基础到进阶）：
      参与→模仿→语言→游戏→社交→视觉空间→情绪调节→自理→学业前

    age: 孩子年龄（岁）
    existing_skill_ids: 已在任务/已掌握的技能id，不重复推荐
    """
    existing = set(existing_skill_ids or [])

    # 按年龄决定允许的最大 level
    if age <= 2:
        max_level = 1
    elif age <= 4:
        max_level = 2
    else:
        max_level = 3

    # 领域优先级顺序
    domain_priority = [
        "参与技能", "模仿技能", "语言技能", "游戏技能", "社交技能",
        "视觉空间技能", "情绪调节技能", "自理技能", "学业前技能",
    ]
    # 补充 get_all_domains() 中有但 priority 列表里没有的领域（容错）
    for d in get_all_domains():
        if d not in domain_priority:
            domain_priority.append(d)

    selected = []
    for domain in domain_priority:
        domain_skills = [
            s for s in get_skills_by_domain(domain)
            if s["skill_id"] not in existing and s["level"] <= max_level
        ]
        if domain_skills:
            domain_skills.sort(key=lambda x: (x["level"], SKILLS.index(x)))
            for s in domain_skills[:max_per_domain]:
                selected.append(s)
        if len(selected) >= max_total:
            break

    return selected[:max_total]


def get_all_skills_grouped() -> Dict[str, Dict[str, List[Dict]]]:
    """返回 {domain: {group: [skills]}} 用于技能选择器展示"""
    result: Dict[str, Dict] = {}
    for s in SKILLS:
        d, g = s["domain"], s["group"]
        if d not in result:
            result[d] = {}
        if g not in result[d]:
            result[d][g] = []
        result[d][g].append(s)
    return result
