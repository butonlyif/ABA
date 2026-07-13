# ABA - Applied Behavior Analysis AI Codex

## 项目描述
ABA AI Codex 是一个基于应用行为分析（Applied Behavior Analysis, ABA）的智能助手项目，包含知识库管理、课程指南生成、数据分析等功能。

## 主要功能
- ABA 知识库管理
- 课程指南生成系统
- 智能对话助手
- 数据收集与分析
- 商业计划书生成

## 技术栈
- Python (后端 + AI)
- React/Vue (可选前端)
- Docker (部署)
- SQLite/PostgreSQL (数据库)
- LLM APIs (AI 能力)

## 项目结构
```
AI_codex/
├── CLAUDE.md                 # 项目说明
├── _archive/                 # 存档文件
├── deploy/                   # 部署配置
│   ├── deploy.sh
│   └── tunnel.sh
├── docs/                     # 文档
│   ├── 知识库/              # 知识库内容
│   ├── 课程指南文本/         # 课程指南
│   └── 产品文档
├── release/                  # 发布版本
├── src/                      # 源代码
│   ├── MVP_web/             # Web 应用
│   ├── aba/                 # ABA 核心模块
│   │   ├── 数据收集表/
│   │   ├── 数据表/
│   │   └── 课程指南/
│   ├── tools/               # 工具脚本
│   └── 初级技能分步训练/
└── 初级技能分步训练/         # 训练材料
```

## 开发注意事项
- 知识库内容存储在 docs/知识库/ 目录
- 使用 LLM API 进行智能对话
- 遵循 ABA 教学方法论
- 支持 Docker 部署
- 注意数据隐私和安全

## 修改记录规则

**每次代码修改必须记录**，包括但不限于：
- 功能新增/修改/删除
- Bug 修复
- 重构和优化
- 配置变更

### 记录位置
| 变更类型 | 记录位置 |
|---------|---------|
| 跨项目通用经验 | `~/.trae/roles-memory/domains/<领域>/` |
| 本项目特定经验 | `.trae/roles/memory/builder/journal.md` |
| 项目决策变更 | `.trae/roles/memory/project.md` 的「关键决策记录」表格 |
| 文档更新 | `.trae/roles/memory/docs/journal.md` |

### 记录格式（参考）
```markdown
## YYYY-MM-DD 修改记录

### 新增
- [文件/功能]: [简要说明]

### 修复
- [Bug描述]: [修复方式]

### 注意事项
- [踩过的坑/教训]
```

### 触发记录的场景
1. 完成一个新功能
2. 修复一个 Bug
3. 发现并解决了技术难题
4. 引入了新的依赖或工具
5. 架构调整或重构

### 日常维护
- 维护 `DAYLOG.md` — 每日开发工作的简要记录
  - 每次开发会话结束时更新
  - 按日期分组，包含：完成事项、进行中事项、问题、明日计划
  - 便于追踪项目进展和问题
