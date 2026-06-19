"""
每会话独立的记忆系统代理。

背景：原本 `core.deep_memory.memory_system` 是模块级单例，整个 Streamlit 进程
只有一份，被所有浏览器会话共用。它的 `current_user_id` / `current_username`
是可变实例属性，于是 A 账户登录/注册会覆盖全局，B 账户的会话读到 A 的 id，
导致「新建账户在别的账户里也能看到」的数据串号。

修复：用代理对象转发所有属性访问到「当前会话」自己的 DeepMemorySystem 实例
（存在 st.session_state 里）。这样登录态按会话隔离，且根除并发竞态，而所有
调用点 `memory_system.xxx` 无需改动。底层 SQLite 文件仍是同一份，照常共享。
"""

import streamlit as st
from core.deep_memory import DeepMemorySystem


class _SessionMemoryProxy:
    def _instance(self) -> DeepMemorySystem:
        if "_memory_system" not in st.session_state:
            st.session_state["_memory_system"] = DeepMemorySystem()
        return st.session_state["_memory_system"]

    def __getattr__(self, name):
        return getattr(self._instance(), name)

    def __setattr__(self, name, value):
        setattr(self._instance(), name, value)


memory_system = _SessionMemoryProxy()
