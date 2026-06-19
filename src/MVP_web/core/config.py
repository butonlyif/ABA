# ====================================
# ABA智能助手 - 配置文件
# ====================================

import os
from pathlib import Path
from dotenv import load_dotenv

# config.py 位于 core/ 子目录，项目根（MVP_web/）是它的上一级。
# data/、.env、知识库等都以 MVP_web/ 为基准，故 BASE_DIR 取 parent.parent。
BASE_DIR = Path(__file__).resolve().parent.parent

_env_file = BASE_DIR / ".env"
load_dotenv(dotenv_path=_env_file)


def _resolve_path(*candidates: str) -> str:
    """Return the first existing candidate path, falling back to the first one."""
    paths = [Path(candidate) for candidate in candidates]
    for path in paths:
        resolved = path if path.is_absolute() else BASE_DIR / path
        if resolved.exists():
            return str(resolved)
    fallback = paths[0]
    return str(fallback if fallback.is_absolute() else BASE_DIR / fallback)

# ====================================
# AI模型配置
# ====================================

# 支持的AI模型
AI_MODELS = {
    "minimax": {
        "name": "MiniMax-M2.7",
        "provider": "openai",
        "model": "MiniMax-M2.7",
        "api_key_env": "MINIMAX_API_KEY",
        "base_url": "https://api.minimaxi.com/v1",
        "free": True,
        "description": "MiniMax M2.7，支持长上下文"
    },
    "doubao": {
        "name": "豆包 (Doubao)",
        "provider": "volcengine",
        "model": "doubao-pro-32k-260428",
        "api_key_env": "DOUBAO_API_KEY",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "free": True,
        "description": "字节跳动免费AI，支持32K上下文"
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
        "free": False,
        "description": "OpenAI轻量版，便宜快速"
    },
    "claude-3-haiku": {
        "name": "Claude 3 Haiku",
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "api_key_env": "ANTHROPIC_API_KEY",
        "free": False,
        "description": "Anthropic轻量版，快速便宜"
    }
}

# 默认使用的模型
DEFAULT_MODEL = "minimax"

# ====================================
# 知识库配置
# ====================================

# 知识库路径（兼容新旧目录结构）
# 新结构：src/MVP_web/ + docs/知识库/ 平级
# 旧结构：MVP_web/ + 知识库/ 平级（兼容客户安装包）
KNOWLEDGE_BASE_PATH = _resolve_path("./知识库", "../知识库", "../../docs/知识库")

# 知识库文档
KNOWLEDGE_FILES = [
    "01_安全边界与禁忌.md",
    "02_核心概念定义.md",
    "03_常见问题.md",
    "04_循证方法介绍.md",
    "05_活动方案库.md",
    "06_场景化干预方案库.md",
]

# 向量数据库配置
# 默认放在 data/（本地开发持久化）；生产镜像里用 ABA_VECTOR_DB_PATH 指到镜像内
# 一个独立路径（构建时预建索引、不落在用户数据 volume 上，避免被空 volume 遮盖、
# 也避免多进程同时读写同一 sqlite）。
VECTOR_DB_PATH = os.getenv("ABA_VECTOR_DB_PATH") or str(BASE_DIR / "data" / "chromadb")
# 远程 API embedding 用的 collection（维度由模型决定，不能与本地混用）
COLLECTION_NAME = "aba_knowledge_semantic_v2"
# 本地 embedding（MiniLM, 384维）用的 collection。两者隔离，避免维度冲突。
COLLECTION_NAME_LOCAL = "aba_knowledge_local_v1"

# 检索参数
RETRIEVAL_TOP_K = 5
RETRIEVAL_CANDIDATE_K = 16
# 这是「召回下限」，过滤明显无关的候选；真正的精排交给后续 LLM rerank。
# 本地 MiniLM(余弦) 的相关片段 score 约 0.55~0.8，设 0.35 保证召回不被误杀。
RETRIEVAL_SCORE_THRESHOLD = 0.35

# 语义检索配置
# 优先使用 OpenAI-compatible embeddings 接口（配置了 EMBEDDING_API_KEY/OPENAI_API_KEY 时）；
# 未配置任何 embedding key 时，自动退回「本地 MiniLM」（chromadb 内置，onnxruntime 驱动，
# 无需任何 API Key、可离线运行）。可在 .env 中覆盖：
# EMBEDDING_API_KEY / EMBEDDING_BASE_URL / EMBEDDING_MODEL
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
# "api" = 用上面的远程 embeddings；"local" = 用本地 MiniLM。
EMBEDDING_MODE = "api" if EMBEDDING_API_KEY else "local"
ENABLE_LLM_RERANK = os.getenv("ENABLE_LLM_RERANK", "true").lower() in ("1", "true", "yes", "on")

# ====================================
# 记忆配置
# ====================================

# 用户数据存储路径
USER_DATA_PATH = str(BASE_DIR / "data" / "users")
MEMORY_FILE = "memory.json"

# 最大历史对话条数
MAX_HISTORY_MESSAGES = 50

# ====================================
# 安全配置
# ====================================

# 危险关键词
DANGER_KEYWORDS = [
    # 紧急情况
    "自杀", "自伤", "想死", "不想活了", "活着没意思",
    "割腕", "跳楼", "吃药", "上吊",
    "轻生", "活不下去了", "不想活了", "死了算了",

    # 攻击行为
    "杀人", "弄死", "打死", "伤害孩子",
    "体罚", "打孩子", "惩罚孩子", "强制控制",

    # 自伤行为
    "撞头", "打自己", "咬自己", "自伤",
    "撞墙", "抓自己", "拔头发",

    # 极端情况
    "不吃饭", "不喝水", "绝食", "拒食",
    "拒药", "呕吐", "催吐",
    "走失", "跑到马路上", "冲出马路", "乱跑",

    # 高风险场景
    "霸凌", "被欺负", "校园欺凌",
    "性行为", "疑似虐待", "被性侵",
    "癫痫", "抽搐", "痉挛",
]

# 严重程度阈值
SAFETY_LEVEL_EMERGENCY = 4  # 立即建议就医
SAFETY_LEVEL_HIGH = 3       # 建议尽快咨询专业
SAFETY_LEVEL_MEDIUM = 2     # 提供支持性回答
SAFETY_LEVEL_LOW = 1        # 正常回答

# ====================================
# 应用配置
# ====================================

# 应用标题
APP_TITLE = "🌟 ABA智能助手"
APP_SUBTITLE = "面向需要特别支持的孩子家长的专业AI助手"

# 默认用户信息
DEFAULT_USER = {
    "child_name": "",
    "child_age": "",
    "child_diagnosis": "",
    "intervention_goals": "",
    "parent_name": "",
    "notes": ""
}

# ====================================
# 提示词配置
# ====================================

# 系统提示词
SYSTEM_PROMPT = """【你是一位专业、温暖的ABA智能助手】

你专为需要特别支持的孩子（{"有发展特点的孩子"}）的家长提供支持，帮助他们理解孩子、提供干预建议。

【你的使命】
• 提供专业、准确的ABA（应用行为分析）知识
• 帮助家长理解孩子的行为背后的原因
• 给出实用、可操作的干预建议
• 始终确保回答的安全性和专业性

【核心原则】

1. 准确性第一
   - 只提供基于循证实践的ABA知识
   - 不确定时明确建议家长咨询专业人士
   - 引用知识库中的专业内容
   - 区分"一般建议"和"专业指导"

2. 安全性保障
   ⚠️ 遇到以下情况必须转介专业：
   - 孩子有自伤或攻击行为
   - 疑似共病障碍
   - 睡眠饮食严重问题
   
   🚨 遇到紧急情况建议立即就医：
   - 孩子表达自伤/自杀想法
   - 严重危及安全的行为

3. 家长友好
   - 用通俗易懂的语言解释专业概念
   - 提供具体可操作的建议
   - 语气平实、友好、就事论事
   - emoji 克制使用

4. 个性化支持
   - 根据孩子的年龄和能力调整建议
   - 提供多个选项让家长选择
   - 记住之前的对话内容

【安全边界】
❌ 你不能：
- 诊断或评估孩子
- 替代专业医疗建议
- 提供涉及安全的重大决策

✅ 你应该：
- 始终强调专业支持的重要性
- 鼓励家长咨询BCBA或专业医生
- 明确AI的能力边界

【知识库说明】
- 如果知识库有相关内容，优先参考知识库内容回答
- 如果提示让你使用search_web工具搜索网络，你必须调用search_web工具获取最新信息后再回答
- 当知识库内容和用户问题不相关时，不要强行使用知识库内容，应搜索网络获取准确信息
- 用户的问题如果涉及服务机构、最新政策、实时信息等，知识库很可能没有，此时务必使用search_web搜索

【回答风格】
- 用平常心对待提问者：默认对方情绪正常、只是想了解信息。不要预设对方焦虑、辛苦或有情绪困扰，不要主动安抚情绪，也不要夸奖"你能来问已经很棒了"之类
- 把孩子当作普通孩子看待：就事论事地谈具体行为，不要暗示孩子"有问题"、不要给孩子贴标签
- 只有当对方明确表达了情绪（着急、难过、崩溃等）时，才简短回应一下情绪；否则直接回答问题
- 语气平实、友好、就事论事，像一个懂行的朋友在客观答疑，不煽情
- 结构清晰：先直接回答问题，再按需补充原因/做法/注意
- 复杂问题可提供多个选项
- emoji 克制使用，能不用就不用
- 保持回复简洁

【高风险场景回答模板】
当问题涉及以下类型时，必须严格按此模板回答：
- 自伤（撞头、咬手、拔头发等）
- 走失、冲到马路上
- 拒食、呕吐、药物
- 攻击他人、自伤
- 性行为、疑似虐待
- 家长想体罚或强制控制

模板：
1. 【风险判断】先判断是否需要立即就医/报警
2. 【立即怎么做】先说不要让孩子独处、移走危险物品等紧急措施
3. 【联系谁】给出具体可拨打的电话
4. 【ABA建议】在确保安全后，才提供行为干预建议
5. 【免责声明】本建议仅供参考，请务必咨询BCBA/医生/治疗师

【语言一致性】
- 所有回答必须使用中文，禁止使用英文词汇
- 专业术语必须括号附注中文解释，例如：
  · BCBA（注册行为分析师）
  · FBA（功能性行为评估）
  · AAC（辅助沟通设备）
  · SLP（语言治疗师）
  · FCT（功能性沟通训练）
  · DTT（回合式教学）
  · PRT（关键反应训练）
- 禁止在回答中出现 supermarket、routine、feeding 等英文词汇

【专业术语表】（必须使用中文全称，括号附注简称或英文缩写）
- ABA = 应用行为分析
- BCBA = 注册行为分析师
- FBA = 功能性行为评估
- AAC = 辅助沟通设备
- SLP = 语言治疗师
- DTT = 回合式教学法
- PRT = 关键反应训练
- FCT = 功能性沟通训练
- VB = 言语行为
- ESDM = 早期密集干预
"""

# 安全提示词（紧急情况）
EMERGENCY_PROMPT = """
🚨 【重要提示 - 需要立即关注】

您提到的情况涉及孩子安全，我非常重视。以下是立即可以采取的步骤：

1. 【保护孩子安全】（最优先）
   - 确保孩子身边有人看护，不要让孩子独处
   - 移走环境中可能的危险物品（尖锐物、药物等）
   - 如果有紧急危险，立即拨打120

2. 【联系专业人员】
   - 孩子的治疗师 / 督导
   - 儿童精神科或儿科医生
   - 当地医院的急诊科

3. 【可以立即拨打的电话】
   - 心理援助热线：400-161-9995（全国24小时）
   - 儿童保护热线：12355
   - 紧急情况请拨打120或110

⚠️ 【免责声明】
本AI助手的内容仅供参考，不能替代医生、康复治疗师、BCBA（注册行为分析师）等专业人士的诊断和干预。

遇到任何紧急或严重情况，请立即寻求专业帮助！您已经在主动寻找解决方案，这非常重要。
"""

# ====================================
# 风格配置
# ====================================

# 对话气泡样式
USER_MESSAGE_STYLE = {
    "background_color": "#DCF8C6",
    "text_color": "#000000",
    "avatar_color": "#4CAF50"
}

BOT_MESSAGE_STYLE = {
    "background_color": "#FFFFFF",
    "text_color": "#333333", 
    "avatar_color": "#2196F3"
}

# ====================================
# 日志配置
# ====================================

LOG_LEVEL = "INFO"
LOG_FILE = "./logs/app.log"
