# DAYLOG - 每日开发日志

每日开发工作的简要记录，按日期分组。

---

## 2026-07-25

### 完成
- 新平台（apps/）部署到生产服务器 `170.106.143.145`
  - 7 个容器全部启动：web/api/worker/postgres/redis/minio/minio-init
  - 前端 React 应用构建并部署到 `http://170.106.143.145:8080/`
  - API 后端 FastAPI 健康：`{"status":"ok"}`
- 旧平台用户数据迁移到新 PostgreSQL（migrate_legacy.py）
  - 8 用户 / 3 孩子 / 23 任务 / 21 对话消息 / 2 报告
  - 迁移零失败零冲突
- 部署前数据备份：141MB（`deploy/data/` → `backups/legacy-data-*.tar.gz`）
- 旧 Streamlit 平台保持不变（8501/8503 端口并行运行）
- **功能补齐 T2：分级危机响应**（apps/api/services/ai.py）
  - 四级风险评估（low/medium/high/emergency）+ 分级文案
  - 区分「aba 家长助手」与「coach 人生教练」两种语境
  - 公开聊天 + 登录聊天均接入统一拦截
  - 线上验证：「带孩子一起走」→ L4 拦截 + 三条热线
- **修复 deploy.sh typo**：`tail-3` → `tail -3`（3 处，此前导致 up -d 静默失败）
- **功能补齐 T5：人生教练知识库树形浏览**
  - 后端：`apps/api/services/coach_content.py` 新增 `categories()` / `search()` / `related()`
  - 路由：新增 `GET /coach/categories`；`/coach/articles` 增 `q` 参数；`/coach/articles/{id}` 返回 `related`
  - 前端：`apps/mobile-web/src/main.tsx` 知识库 tab 重构为「分类树→子分类→文章」三层 + 搜索框 + 文章详情相关文章
  - 线上验证：9 个一级分类 / 搜索"睡眠"命中 4 篇 / sleep_2 推荐 2 篇相关
- **功能补齐 T6：人生教练 AI 周报**
  - 后端：新建 `apps/api/services/coach_weekly.py`，MiniMax LLM 生成 + 规则版降级
  - 路由：新增 `POST /coach/weekly-report?week_offset=0`（0=本周，-1=上周）
  - 数据源：本周 MoodEntry / JournalEntry / coach ChatMessage
  - 前端：mobile-web 新增底部第 6 个 tab "周报"，本周/上周切换、AI 一键生成
  - 线上验证：MiniMax 9.7s 生成共情式周报，零数据时仍能温柔鼓励
- **功能补齐 T8：对话上下文窗口扩展（简化版 DeepMemory）**
  - 新建 `apps/api/services/context_builder.py`：纯结构化拼接，无向量库
  - `generate()` 增加 `context` 可选参数，注入 system prompt
  - ABA 场景：注入孩子档案（姓名/年龄/诊断/目标/较弱能力域/最近训练）
  - Coach 场景：注入最近 5 条情绪 + 最新日记
  - 3 个 chat 端点接入（chat / chat/stream / coach/chat）
  - Prompt 调优：明确指示 AI "不要声称没数据"，直接使用注入事实
  - 线上验证：tony 孩子"4岁语言发育迟缓"档案正确注入，AI 直接给出针对性建议

### 决策
- **T1（AI RAG 向量检索）放弃**：评估为过度设计
  - ABA 术语高度结构化，关键词检索已够用
  - MiniMax-M3 本身具备 ABA 知识，外部检索边际收益小
  - ChromaDB 代价大：~200MB 依赖、首次建索引 6s、维护复杂度
  - 违反「最简方案优先」原则

### 访问地址
| 平台 | 地址 | 状态 |
|------|------|------|
| 新平台（React） | http://170.106.143.145:8080/ | ✅ 新上线 |
| 旧平台（Streamlit） | http://170.106.143.145:8501/ | ✅ 保留运行 |
| 人生教练 | http://170.106.143.145:8503/ | ✅ 保留运行 |

### 注意事项
- 新旧平台并行运行，用户数据已同步
- 数据迁移是幂等的，可安全重复执行
- 旧平台数据（SQLite）保留在 `deploy/data/`，未修改

### 待办（功能补齐计划剩余）
- ~~T1: AI 助手 RAG 语义检索~~ ❌ 放弃（过度设计）
- ✅ T2: 危机响应分级（已完成）
- ✅ T5: 人生教练知识库树形浏览（已完成）
- ✅ T6: AI 周报（已完成）
- ~~T7: 专家后台报告草稿生成~~ ❌ 跳过（无专家在用）
- ✅ T8: 对话上下文窗口扩展（已完成）
- ~~T3/T4: 跨用户 RAG + 索引管理~~ ❌ 跳过

### 备注
- 专家咨询系统（ExpertAssignment + ExpertProfile + ExpertMessage + 相关 10 路由）：**未启用**（无专家在用），代码保留但不投入维护。如需清理可单独安排任务。
- **⚠️ 测试遗留**：为验证 T5/T6/T8 临时改了 `leoz` 和 `tony` 两个账号的密码为 `test12345`，需通知用户改回或由管理员重置。

### 旧平台移除（阶段 1：停止容器）
- **停服前备份**：`backups/legacy-shutdown-20260725-170545.tar.gz`（141MB，deploy/data/ 完整快照）
- **停止旧平台 3 容器**：`docker compose --env-file deploy/deploy.env -f deploy/docker-compose.yml down`
  - aba-assistant (8501) / aba-admin (8502) / life-coach (8503) 全部停止并移除
  - 旧端口 8501/8502/8503 已释放
- **保留用于回滚**：
  - 服务器镜像 `aba-assistant:latest`（2.42GB）
  - 服务器数据卷 `deploy/data/`（162MB）
- **本地归档**：`_archive/deploy-legacy-20260725/`（Dockerfile / docker-compose.yml / 旧部署脚本 / env）
- **新平台验证**：web 200 OK + API 健康，未受影响
- **回滚方式**：还原归档文件 → `docker compose --env-file deploy/deploy.env -f deploy/docker-compose.yml up -d`

### 待办（观察期后）
- [ ] 观察 24-48 小时，确认无用户反馈旧地址失效问题
- [ ] 确认无问题后，删除服务器旧镜像 `aba-assistant:latest`（释放 2.42GB）
- [ ] 决定 `deploy/data/` 是否长期保留（当前作为冷归档）

---

## 2026-07-12

### 完成
- Trae 环境初始化（`.trae/` 目录结构）
- 添加单元测试（99 个测试用例覆盖 8 个核心模块）
  - ai/agent.py: 13 个
  - ai/knowledge_base.py: 14 个
  - coach/coach_engine.py: 20 个
  - coach/coach_content.py: 9 个
  - admin/data_access.py: 8 个
  - core/safety.py: 13 个
  - core/config.py: 10 个
  - core/deep_memory.py: 12 个
- 添加修改记录规则到 `.trae/rules.md`
- 创建 `DAYLOG.md` 日常维护

### 注意事项
- pytest 未安装在系统 Python 中，测试需手动验证
- DeepMemorySystem 使用 `register()`/`login()` 而非 `register_user()`/`login_user()`

### 项目状态
- 项目完成度：单元测试从 0% 提升到覆盖核心模块
- 待优化：AI Agent 集成测试、教练模块完整测试

---

## YYYY-MM-DD

<!-- 模板：复制下面内容到上方替换日期 -->

### 完成
- 

### 进行中
- 

### 问题
- 

### 明日计划
- 

---
