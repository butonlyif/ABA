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
