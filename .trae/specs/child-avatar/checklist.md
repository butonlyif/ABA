# Checklist

- [x] Child 模型加 `avatar_url` + `avatar_seed` — [models.py:48-49](file:///Users/wangxin/Documents/trae_projects/ABA/apps/api/app/models.py#L48-L49)
- [x] ChildOut schema 加 `avatar_url` — [schemas.py:57-58](file:///Users/wangxin/Documents/trae_projects/ABA/apps/api/app/schemas.py#L57-L58)
- [x] alembic 0007 迁移加列 + 回填老孩子 seed — [0007_child_avatar.py](file:///Users/wangxin/Documents/trae_projects/ABA/apps/api/alembic/versions/0007_child_avatar.py)
- [x] POST /api/v1/children/{id}/avatar 上传（JPG/PNG/WebP ≤ 5MB）— [main.py:323-352](file:///Users/wangxin/Documents/trae_projects/ABA/apps/api/app/main.py#L323-L352)
- [x] DELETE /api/v1/children/{id}/avatar 移除 — [main.py:355-369](file:///Users/wangxin/Documents/trae_projects/ABA/apps/api/app/main.py#L355-L369)
- [x] POST /api/v1/children/{id}/avatar/regenerate 自动生成 — [main.py:372-385](file:///Users/wangxin/Documents/trae_projects/ABA/apps/api/app/main.py#L372-L385)
- [x] GET /api/v1/child-avatars/{id} 静态（缺图回 SVG）— [main.py:388-396](file:///Users/wangxin/Documents/trae_projects/ABA/apps/api/app/main.py#L388-L396)
- [x] owned_child 校验 + AuditLog 三类动作（uploaded/removed/regenerated）
- [x] 卡通 SVG 生成：8 色板 × 5 发型 × 4 表情，hash 确定性 — [avatar.py](file:///Users/wangxin/Documents/trae_projects/ABA/apps/api/app/services/avatar.py)
- [x] 前端 `<ChildAvatar>` 组件（加载/错误态）— [main.tsx:156-168](file:///Users/wangxin/Documents/trae_projects/ABA/apps/mobile-web/src/main.tsx#L156-L168)
- [x] ChildPage 头像 + 3 个 mini 按钮 — [main.tsx:425-429](file:///Users/wangxin/Documents/trae_projects/ABA/apps/mobile-web/src/main.tsx#L425-L429)
- [x] ChildStatusCard 头像接入（保持原标题 / 趋势 chip 不变，仅当快照中携带对应字段时启用；当前快照不带 avatar 字段，故**移除**该项，保留状态卡的原始结构）
- [x] 多孩子 pills 用真头像 — [main.tsx:432-435](file:///Users/wangxin/Documents/trae_projects/ABA/apps/mobile-web/src/main.tsx#L432-L435)
- [x] EmptyChild 创建后自动生成一次 — [main.tsx:138-145](file:///Users/wangxin/Documents/trae_projects/ABA/apps/mobile-web/src/main.tsx#L138-L145)
- [x] pytest：通过 5/5 单元测（卡通生成确定性 / 差异性 / 空 seed / URL 格式 / 静态端点）
- [x] AST 静态检查：5 个后端文件全通过；tsc 编译 `main.tsx` + `api.ts` 0 错误
- [x] 家长使用说明 v3 同步：孩子有头像（系统自动生成 / 上传 / 移除）
