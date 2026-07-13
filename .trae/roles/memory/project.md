# 项目概要

## 项目信息

- **项目名称**: ABA智能助手
- **项目简介**: 面向自闭症儿童家长的AI辅助工具，基于应用行为分析（ABA）提供智能问答、训练记录、课程指南和心理支持
- **技术栈**: Python + Streamlit, ChromaDB, LLM APIs, Docker
- **创建日期**: 2026-05-16

## 领域归属

- **主要领域**: aichip / webapp
- **关联领域**: healthcare, education

## 产品线

| 应用 | 端口 | 定位 |
|------|------|------|
| ABA智能助手 | 8501 | 面向孩子：AI问答、评估、训练、记录 |
| 人生教练 | 8503 | 面向家长：ACT对话、情绪追踪 |
| 专家后台 | 8502 | 面向运营：数据管理、导出（SSH隧道） |

## 技术架构

```
src/MVP_web/
├── ai/           # AI问答、知识库、报告生成
├── coach/        # 人生教练（ACT框架）
├── core/         # 配置、安全、记忆管理
├── admin/        # 专家后台
└── data/         # ChromaDB、图片素材
```

## 关键文件

- `docs/产品结构文档.md` - 产品规格说明
- `docs/技术文档.md` - 技术实现细节
- `release/` - 构建和发布配置
- `deploy/` - Docker部署配置

## 关键决策记录

| 日期 | 决策 | 原因 | 影响 |
|------|------|------|------|
| 2026-05-30 | ABA训练闭环 | 产品核心功能 | 技能树/评估/任务/训练/看板 |
| 2026-06-05 | 评估系统v3 | 覆盖全部210技能 | 39题5阶段递进评估 |

## 角色日志

- Builder: `roles/memory/builder/journal.md`
- Optimizer: `roles/memory/optimizer/journal.md`
- Tester: `roles/memory/tester/journal.md`
- Docs: `roles/memory/docs/journal.md`
- PM: `roles/memory/pm/journal.md`
- Research: `roles/memory/research/journal.md`

## 任务列表

- `roles/memory/tasks/` — PM 派发的任务文档
