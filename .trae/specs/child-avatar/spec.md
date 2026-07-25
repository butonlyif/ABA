# 孩子头像 spec

## Why
当前 `Child` 模型没有 `avatar_url`，前端 `ChildPage` 只渲染 `child.name.slice(0, 1)` 当占位。家长给出的反馈是「孩子好像没有头像，可以做进去」。  
这一版做孩子头像：**手动上传 + 自动生成卡通头像**（兜底）。

## What Changes
- **后端**：给 `Child` 表加 `avatar_url` + `avatar_seed` 字段；增加 4 个接口；alembic 0007 迁移；旧孩子自动生成 seed
- **前端**：`ChildPage` 替换占位为真头像；提供「相机 / 自动生成 / 移除」三选
- **不引入**：LLM 生成、第三方服务（保证离线可用）

## Impact
- Affected specs: 无
- Affected code:
  - `apps/api/app/models.py`（Child）
  - `apps/api/app/schemas.py`（ChildOut）
  - `apps/api/app/main.py`（4 个新接口）
  - `apps/api/app/services/avatar.py`（**新文件**，卡通 SVG 生成）
  - `apps/api/alembic/versions/0007_child_avatar.py`（**新文件**）
  - `apps/mobile-web/src/main.tsx`（ChildPage + ChildStatusCard + EmptyChild + api.ts）
  - `apps/mobile-web/src/api.ts`（HTTP 调用）

---

## ADDED Requirements

### Requirement: 模型与字段
- `Child.avatar_url: str | None` — 上传 / 自动生成后的相对 URL
- `Child.avatar_seed: str | None` — 卡通头像生成种子（默认 = `name`）

#### Scenario: 老孩子迁移
- **WHEN** 迁移 0007 启动
- **THEN** 所有 `avatar_url IS NULL` 的孩子立刻被填上一个 seed（= `name`）+ 默认卡通 URL；前端立即可见，不再是占位

### Requirement: 上传头像
- `POST /api/v1/children/{child_id}/avatar`（multipart）
- 校验：JPG/PNG/WebP、≤ 5MB
- 存储：`{upload_root}/child_avatars/{child_id}.webp`
- 写入 `avatar_url = /api/v1/child-avatars/{child_id}`，记录 `AuditLog`

#### Scenario: 家长上传
- **WHEN** 家长在「孩子」页选「相机」上传一张照片
- **THEN** 头像立刻在档案卡、能力状态、所有列表显示

### Requirement: 移除头像
- `DELETE /api/v1/children/{child_id}/avatar`
- 删除 webp 文件 + 清空 `avatar_url`
- 之后回退到自动生成（用 seed 重新画）

#### Scenario: 家长移除
- **WHEN** 家长点「移除头像」
- **THEN** 真头像消失，立刻出现卡通头像，不出现空白

### Requirement: 自动生成卡通
- `POST /api/v1/children/{child_id}/avatar/regenerate`
- 不传图，基于 `seed` 哈希生成 SVG 卡通；返回 `avatar_url`（指向同一条静态 GET 路由 + `?seed=xxx`）
- 内置 8 个色板 + 5 个发型 + 4 个表情；哈希确定选哪个

#### Scenario: 家长点自动生成
- **WHEN** 家长点「自动生成」
- **THEN** 头像换成新的卡通（可能不同色），稳定性由 name 保证

### Requirement: 文件 / 静态读取
- `GET /api/v1/child-avatars/{child_id}?seed=...`
- 优先返回 webp 文件；缺失时返回卡通 SVG（content-type: image/svg+xml）
- 老孩子 / 无 file 也不报错

### Requirement: 前端 — ChildPage 头像替换
- 把 `child.name.slice(0,1)` 占位换成 `<Avatar url={child.avatar_url} name={child.name} />`
- 头像下方出现「�� / ✨ / ��」三个 mini 按钮
- 上传 / 移除 / 重新生成对应 3 个 mutation

### Requirement: 前端 — EmptyChild 头像
- 创建孩子后，自动触发一次「生成卡通」（基于刚填的名字）
- 家长不用再做一次

### Requirement: 视觉
- 头像走 80×80 圆角方形
- 上传中显示骨架屏
- 移除