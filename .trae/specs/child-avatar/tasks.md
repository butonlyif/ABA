# Tasks

- [ ] Task 1: 头像后端（最小可测）
  - [ ] SubTask 1.1: `models.py` 给 Child 加 `avatar_url` + `avatar_seed`
  - [ ] SubTask 1.2: `schemas.py` 给 ChildOut 加 `avatar_url`
  - [ ] SubTask 1.3: `services/avatar.py` 卡通生成（hash → 色板/发型/表情 → SVG）
  - [ ] SubTask 1.4: 4 个路由：上传 / 移除 / 自动生成 / 静态 GET
  - [ ] SubTask 1.5: 迁移 0007：加列 + 回填兜底

- [ ] Task 2: 前端接入
  - [ ] SubTask 2.1: `api.ts` 加 4 个方法
  - [ ] SubTask 2.2: `<Avatar>` 组件封装 + 加载/错误态
  - [ ] SubTask 2.3: `ChildPage` 接入 3 个 mini 按钮
  - [ ] SubTask 2.4: ChildStatusCard 头像接入
  - [ ] SubTask 2.5: 多孩子 pills 用真头像
  - [ ] SubTask 2.6: `EmptyChild` 创建后自动生成一次

- [ ] Task 3: 验证
  - [ ] SubTask 3.1: 单元测：卡通生成确定性 + 长度边界
  - [ ] SubTask 3.2: 集成测：上传/删除/生成 路径
  - [ ] SubTask 3.3: pytest 跑通 + alembic upgrade head

# Task Dependencies
- Task 2 依赖 Task 1
- Task 3 依赖 Task 2
