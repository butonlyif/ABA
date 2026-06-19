"""
====================================
ABA智能助手 - Web界面主程序
====================================

使用Streamlit构建的Web界面
支持知识库问答、记忆系统、安全检查
"""

import streamlit as st
import time
from datetime import datetime
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    APP_TITLE, APP_SUBTITLE, DEFAULT_USER,
    SYSTEM_PROMPT, EMERGENCY_PROMPT, DEFAULT_MODEL, AI_MODELS,
    USER_DATA_PATH, MEMORY_FILE, KNOWLEDGE_BASE_PATH
)
from knowledge_base import KnowledgeBase
from agent import ABAAgent
from safety import SafetyChecker
from deep_memory import DeepMemorySystem, memory_system

# ====================================
# 页面配置
# ====================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================================
# 辅助函数
# ====================================

def load_css():
    """加载自定义CSS样式"""
    st.markdown("""
    <style>
    /* 主标题样式 */
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2196F3;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    /* 副标题样式 */
    .subtitle {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* 消息气泡 - 用户 */
    .user-message {
        background-color: #DCF8C6;
        padding: 1rem;
        border-radius: 15px 15px 0 15px;
        margin: 0.5rem 0;
        max-width: 80%;
        margin-left: auto;
    }
    
    /* 消息气泡 - AI */
    .ai-message {
        background-color: #FFFFFF;
        padding: 1rem;
        border-radius: 15px 15px 15px 0;
        margin: 0.5rem 0;
        max-width: 80%;
        border: 1px solid #E0E0E0;
    }
    
    /* 安全提示框 */
    .safety-alert {
        background-color: #FFF3CD;
        border: 1px solid #FFECB5;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* 紧急提示框 */
    .emergency-alert {
        background-color: #F8D7DA;
        border: 1px solid #F5C6CB;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* 信息卡片 */
    .info-card {
        background-color: #E3F2FD;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* 侧边栏样式 */
    .css-1d391kg {
        background-color: #F5F5F5;
    }
    </style>
    """, unsafe_allow_html=True)


def initialize_session_state():
    """初始化会话状态"""

    if "memory_system" not in st.session_state:
        st.session_state.memory_system = memory_system

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "user_info" not in st.session_state:
        st.session_state.user_info = DEFAULT_USER.copy()

    if "agent" not in st.session_state:
        st.session_state.agent = None

    if "knowledge_base" not in st.session_state:
        st.session_state.knowledge_base = None

    if "safety_checker" not in st.session_state:
        st.session_state.safety_checker = SafetyChecker()

    if "initialized" not in st.session_state:
        st.session_state.initialized = False

    if "selected_model" not in st.session_state:
        st.session_state.selected_model = DEFAULT_MODEL

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if "corpus_extracted_count" not in st.session_state:
        st.session_state.corpus_extracted_count = 0


def initialize_components():
    """初始化组件"""
    if not st.session_state.initialized:
        with st.spinner("🔄 正在初始化..."):
            try:
                st.session_state.knowledge_base = KnowledgeBase(
                    knowledge_path=KNOWLEDGE_BASE_PATH
                )
                st.session_state.knowledge_base.load_documents()

                st.session_state.agent = ABAAgent(
                    knowledge_base=st.session_state.knowledge_base,
                    model_name=st.session_state.selected_model
                )

                st.session_state.initialized = True

            except Exception as e:
                st.error(f"❌ 初始化失败: {str(e)}")
                st.info("请检查配置是否正确，特别是API密钥设置。")


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("## 🌟 ABA智能助手")
        st.markdown("---")

        if not st.session_state.logged_in:
            st.markdown("### 🔐 登录 / 注册")

            tab1, tab2 = st.tabs(["登录", "注册"])

            with tab1:
                login_username = st.text_input("用户名", key="login_user")
                login_password = st.text_input("密码", type="password", key="login_pass")
                if st.button("登录", use_container_width=True):
                    success, msg = st.session_state.memory_system.login(
                        login_username, login_password
                    )
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.corpus_extracted_count = 0

                        saved_profile = st.session_state.memory_system.get_user_info()
                        if saved_profile and saved_profile.get('user_info'):
                            st.session_state.user_info = saved_profile['user_info']
                        else:
                            st.session_state.user_info = DEFAULT_USER.copy()

                        st.success(f"✅ 登录成功！欢迎 {login_username}")
                        st.rerun()
                    else:
                        st.error(msg)

            with tab2:
                reg_username = st.text_input("用户名", key="reg_user")
                reg_password = st.text_input("密码", type="password", key="reg_pass")
                reg_password2 = st.text_input("确认密码", type="password", key="reg_pass2")
                if st.button("注册", use_container_width=True):
                    if reg_password != reg_password2:
                        st.error("两次密码不一致")
                    else:
                        success, msg = st.session_state.memory_system.register(
                            reg_username, reg_password
                        )
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.corpus_extracted_count = 0

                            saved_profile = st.session_state.memory_system.get_user_info()
                            if saved_profile and saved_profile.get('user_info'):
                                st.session_state.user_info = saved_profile['user_info']
                            else:
                                st.session_state.user_info = DEFAULT_USER.copy()

                            st.success("✅ 注册成功！")
                            st.rerun()
                        else:
                            st.error(msg)

            st.markdown("---")
            st.info("💡 登录后可保存对话历史，获得更个性化的服务")
            return {"child_name": "", "child_age": "", "child_diagnosis": "", "intervention_goals": ""}

        else:
            user_info = st.session_state.memory_system.get_user_info()
            st.success(f"✅ 已登录：{user_info.get('username', '')}")

            if st.button("退出登录", use_container_width=True):
                st.session_state.memory_system.logout()
                st.session_state.logged_in = False
                st.rerun()

            st.markdown("---")

            corpus_summary = st.session_state.memory_system.get_corpus_summary()
            if corpus_summary["total"] > 0:
                st.markdown("### 📊 语料统计")
                st.info(f"📚 提取语料: {corpus_summary['total']} 条")
                for corpus_type, count in corpus_summary["by_type"].items():
                    st.write(f"  • {corpus_type}: {count}")

            conv_count = st.session_state.memory_system.get_conversation_count()
            st.info(f"💬 对话记录: {conv_count} 条")

            st.markdown("---")

        st.markdown("### 🤖 AI模型")
        model_options = {k: v["name"] for k, v in AI_MODELS.items()}
        selected = st.selectbox(
            "选择AI模型",
            options=list(model_options.keys()),
            format_func=lambda x: f"{model_options[x]} {'(免费) ⭐' if AI_MODELS[x]['free'] else ''}",
            index=list(model_options.keys()).index(st.session_state.selected_model)
        )

        if selected != st.session_state.selected_model:
            st.session_state.selected_model = selected
            st.session_state.agent = ABAAgent(
                knowledge_base=st.session_state.knowledge_base,
                model_name=selected
            )
            st.rerun()

        model_info = AI_MODELS.get(st.session_state.selected_model, {})
        st.info(f"📝 {model_info.get('description', '')}")

        st.markdown("---")

        st.markdown("### 👶 孩子信息")

        child_name = st.text_input(
            "姓名/昵称",
            value=st.session_state.user_info.get("child_name", ""),
            placeholder="例如：小明"
        )

        child_age = st.text_input(
            "年龄",
            value=st.session_state.user_info.get("child_age", ""),
            placeholder="例如：5岁"
        )

        child_diagnosis = st.selectbox(
            "诊断情况",
            options=["", "自闭症谱系障碍（ASD）", "疑似自闭症", "发育迟缓", "其他"],
            index=0
        )

        intervention_goals = st.text_area(
            "当前干预目标",
            value=st.session_state.user_info.get("intervention_goals", ""),
            placeholder="例如：练习表达需求、提升社交技能",
            height=100
        )

        if st.button("💾 保存信息"):
            st.session_state.user_info = {
                "child_name": child_name,
                "child_age": child_age,
                "child_diagnosis": child_diagnosis,
                "intervention_goals": intervention_goals,
                "parent_name": st.session_state.user_info.get("parent_name", ""),
                "notes": st.session_state.user_info.get("notes", "")
            }
            if st.session_state.logged_in:
                st.session_state.memory_system.save_user_profile(st.session_state.user_info)
            st.success("✅ 信息已保存！")

        if intervention_goals and st.session_state.knowledge_base:
            st.markdown("---")
            st.markdown("### 📖 推荐阅读")

            recommended = st.session_state.knowledge_base.get_recommended_documents(
                intervention_goals, top_k=3
            )

            if recommended:
                for doc in recommended:
                    doc_title = doc["title"].replace("_", " ").replace("-", " ")
                    with st.expander(f"📄 {doc_title}", expanded=False):
                        st.markdown(f"**来源**: {doc['source']}")
                        st.markdown(f"**相关度**: {'⭐' * min(int(doc['score']), 5)}")
                        st.markdown(f"**预览**: {doc['preview']}")
            else:
                st.info("暂无相关推荐，请尝试完善干预目标")

        st.markdown("---")

        st.markdown("### ⚡ 快捷操作")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ 清空对话", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

        with col2:
            if st.button("📋 示例问题", use_container_width=True):
                pass

        st.markdown("---")

        st.markdown("### 📊 状态")
        if st.session_state.initialized:
            st.success("● 已连接")
            if st.session_state.knowledge_base:
                doc_count = st.session_state.knowledge_base.get_document_count()
                st.info(f"📚 知识库: {doc_count} 个文档")
        else:
            st.warning("○ 未连接")

        return {
            "child_name": child_name,
            "child_age": child_age,
            "child_diagnosis": child_diagnosis,
            "intervention_goals": intervention_goals
        }


def render_chat_messages():
    """渲染聊天消息"""
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant"):
                # 检查是否有安全提示
                if message.get("safety_level", 0) >= 3:
                    if message["safety_level"] >= 4:
                        st.warning(EMERGENCY_PROMPT)
                    else:
                        st.info("⚠️ **温馨提示**：以下情况建议咨询专业人员")
                
                st.markdown(message["content"])


def handle_user_input(user_input: str, user_context: dict):
    """处理用户输入"""
    if not user_input.strip():
        return

    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    safety_result = st.session_state.safety_checker.check(user_input)

    with st.chat_message("assistant"):
        with st.spinner("🤔 思考中..."):
            try:
                context = {
                    **user_context,
                    "conversation_history": st.session_state.messages[:-1]
                }

                if st.session_state.logged_in and st.session_state.agent:
                    rag_context = st.session_state.memory_system.get_context_for_rag(user_input)
                    context["rag_context"] = rag_context

                if safety_result["level"] >= 4:
                    response = EMERGENCY_PROMPT
                    st.warning("🚨 检测到紧急信号，已提供紧急帮助信息")
                else:
                    response = st.session_state.agent.generate_response(
                        user_input=user_input,
                        context=context,
                        safety_level=safety_result["level"]
                    )

                    if safety_result["level"] >= 2:
                        st.info("⚠️ **温馨提示**：如果情况持续或加重，建议咨询专业医生或BCBA。")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "safety_level": safety_result["level"],
                    "timestamp": datetime.now().isoformat()
                })

                st.markdown(response)

                if st.session_state.logged_in:
                    conv_id = st.session_state.memory_system.save_conversation(
                        role="user",
                        content=user_input
                    )
                    st.session_state.memory_system.save_conversation(
                        role="assistant",
                        content=response,
                        metadata={"safety_level": safety_result["level"]}
                    )

                    if st.session_state.corpus_extracted_count < 10:
                        import threading
                        def extract_corpus():
                            st.session_state.corpus_extracted_count += 1
                            if st.session_state.agent:
                                st.session_state.memory_system.extract_corpus_from_conversations(
                                    agent=st.session_state.agent
                                )

                        threading.Thread(target=extract_corpus, daemon=True).start()

            except Exception as e:
                error_msg = f"❌ 生成回答时出错: {str(e)}"
                st.error(error_msg)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "error": True,
                    "timestamp": datetime.now().isoformat()
                })


def render_main_content():
    """渲染主内容区域"""
    
    # 标题
    st.markdown(f'<p class="main-title">{APP_TITLE}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="subtitle">{APP_SUBTITLE}</p>', unsafe_allow_html=True)
    
    # 初始化组件
    initialize_components()
    
    # 渲染侧边栏获取用户上下文
    user_context = render_sidebar()
    
    st.markdown("---")
    
    # 欢迎消息（首次使用）
    if not st.session_state.messages:
        welcome_msg = """
        👋 **欢迎使用ABA智能助手！**

        我是一位专业、温暖的AI助手，专为需要特别支持的孩子家长提供支持。

        **我可以帮助你：**
        • 了解ABA基础知识
        • 解答关于孩子行为的疑惑
        • 提供实用的家庭干预建议
        • 分享日常干预的技巧
        
        **请先在左侧填写孩子的情况**，这样我可以给你更个性化的建议！
        
        **快捷问题示例：**
        - 什么是正强化？
        - 孩子发脾气怎么办？
        - 怎么教孩子说话？
        - 孩子2岁还不会说话，正常吗？
        """
        st.info(welcome_msg)
    
    # 渲染聊天历史
    render_chat_messages()
    
    # 聊天输入框
    st.markdown("---")
    
    # 快捷问题按钮
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🤔 什么是正强化？", use_container_width=True):
            handle_user_input("什么是正强化？", user_context)
    
    with col2:
        if st.button("😢 孩子发脾气怎么办？", use_container_width=True):
            handle_user_input("孩子发脾气怎么办？", user_context)
    
    with col3:
        if st.button("🗣️ 怎么教孩子说话？", use_container_width=True):
            handle_user_input("怎么教孩子说话？", user_context)
    
    # 主输入框
    user_input = st.chat_input(
        placeholder="输入你的问题，我会尽力帮助你...",
        key="user_input"
    )
    
    if user_input:
        handle_user_input(user_input, user_context)


def main():
    """主函数"""
    load_css()
    initialize_session_state()
    render_main_content()


if __name__ == "__main__":
    main()
