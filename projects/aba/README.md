# ABA 家庭训练

面向自闭症谱系（ASD）儿童家庭的产品线：能力评估、DTT 分步训练、图片卡、进展报告、AI 干预咨询。

## 目录结构

| 目录 | 说明 | 迁移状态 |
|------|------|----------|
| `knowledge/` | ABA 干预专业知识库（安全边界、核心概念、循证方法、活动方案、场景化干预、课程指南等） | ✅ 已从 `docs/知识库` 迁入 |
| `specs/` | 本项目专属流程文档（spec / tasks / checklist） | ⬜ 新建；现有 Trae 托管的 `child-avatar` spec 见 `.trae/specs/` |
| `backend/` | FastAPI 后端（ABA 路由、模型、服务、alembic 迁移） | ⬜ 待迁移（当前在 `apps/api`） |
| `frontend/` | React PWA 前端（ABA 家庭训练界面） | ⬜ 待迁移（当前在 `apps/mobile-web`） |
| `legacy/` | 旧平台 ABA 模块（assessment、flashcards、ai、core） | ⬜ 待迁移（当前在 `src/MVP_web`） |

## 迁移阶段

- [x] 阶段 1：目录骨架 + 知识库迁入
- [ ] 阶段 2：共享层抽取（`packages/shared`：User / 认证 / DB / 存储）
- [ ] 阶段 3：后端拆分为独立 FastAPI 进程
- [ ] 阶段 4：前端拆分为独立 PWA
- [ ] 阶段 5：部署配置（docker-compose 双服务）

## 与其他模块的关系

- 共享层：`packages/shared`（认证、数据库基座、对象存储、AI 客户端）—— ABA 与 Coach 共用同一套 `users` 表与登录
- API 契约：`packages/contracts`
- 运营后台：`packages/admin-web`（跨产品）
- 知识库路径配置：`apps/api/app/config.py` 的 `knowledge_path` 已指向 `projects/aba/knowledge`
