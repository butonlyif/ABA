# 家长陪伴（Coach）

面向家长本人的心理成长产品线：基于 ACT（接纳承诺疗法）的成长路径、情绪追踪、反思日记、AI 陪伴对话、周报。

## 目录结构

| 目录 | 说明 | 迁移状态 |
|------|------|----------|
| `knowledge/` | 家长陪伴知识库（34 篇文章，9 个分类：方法论、情绪管理、自我认知、关系经营、职业、健康、习惯、养育支持、正念练习） | ✅ 已从 `src/MVP_web/coach/coach_content.py` 的 `KB_ARTICLES` 外化为独立 md |
| `specs/` | 本项目专属流程文档（spec / tasks / checklist） | ⬜ 新建；跨产品的 `peter-customer-guide` spec 见 `.trae/specs/` |
| `backend/` | FastAPI 后端（`/api/v1/coach/*` 路由、模型、服务、alembic 迁移） | ⬜ 待迁移（当前在 `apps/api`） |
| `frontend/` | React PWA 前端（家长陪伴界面：chat / emotion / growth / record / knowledge） | ⬜ 待迁移（当前在 `apps/mobile-web`） |
| `legacy/` | 旧平台 Coach 模块（coach_content、coach_engine、coach_styles） | ⬜ 待迁移（当前在 `src/MVP_web/coach`） |

## 迁移阶段

- [x] 阶段 1：目录骨架 + 知识库外化
- [ ] 阶段 2：共享层抽取（`packages/shared`：User / 认证 / DB / 存储）
- [ ] 阶段 3：后端拆分为独立 FastAPI 进程；知识库加载逻辑改造为从 `knowledge/*.md` 读取（替代当前 import Python dict）
- [ ] 阶段 4：前端拆分为独立 PWA
- [ ] 阶段 5：部署配置（docker-compose 双服务）

## 与其他模块的关系

- 共享层：`packages/shared`（认证、数据库基座、对象存储、AI 客户端）—— Coach 与 ABA 共用同一套 `users` 表与登录
- Coach 业务表（`coach_mood_entries` / `coach_journal_entries` / `coach_growth_progress` / `coach_growth_states`）仅挂 `user_id`，不引用 `child_id`，与 ABA 数据天然隔离
- 知识库：`knowledge/INDEX.md` 为总索引；文章正文已外化，加载逻辑改造见阶段 3
