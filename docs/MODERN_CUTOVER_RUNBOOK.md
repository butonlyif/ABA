# 现代平台预发布与切流手册

## 原则

- 旧服务器数据先只读备份，再迁移，不删除源文件。
- 第一次迁移只在预发布数据库执行。
- 切流前必须同时具备：现代平台备份、旧数据迁移报告、逐用户校验通过。
- 不长期双写。正式切流窗口内旧用户端改为只读，新平台成为唯一写入端。

## 1. 创建现代平台备份

在 `apps/api` 目录、加载目标环境变量后执行：

```bash
./.venv/bin/python scripts/backup_state.py \
  --output ../../backups/pre-cutover-$(date +%Y%m%d-%H%M%S).tar.gz
```

备份包含数据库、报告/头像等对象文件和 SHA-256 清单。

## 2. 在预发布环境迁移旧客户

```bash
./.venv/bin/python scripts/migrate_legacy.py \
  --legacy-root ../../src/MVP_web/data \
  --report migration-report.json
```

先审阅 dry-run 报告，再执行：

```bash
./.venv/bin/python scripts/migrate_legacy.py \
  --legacy-root ../../src/MVP_web/data \
  --report migration-report.json \
  --apply
```

迁移工具会保存旧 SQLite、WAL、训练 JSON、教练 JSON，并输出源文件哈希、失败项、冲突和逐用户数量。

## 3. 发布门禁

在目标环境变量已加载的情况下执行：

```bash
bash deploy/preflight.sh \
  apps/api/migration-report.json \
  backups/pre-cutover-YYYYMMDD-HHMMSS.tar.gz
```

只有以下检查全部通过才允许切流：

- 数据库处于最新 Alembic 版本；
- PostgreSQL、Redis、对象存储可读写；
- 旧数据无失败、无账户冲突且逐用户校验通过；
- 备份内每个文件的 SHA-256 校验通过；
- 后端测试、安全预检、两个前端生产构建通过。

## 4. 切流顺序

1. 公告维护窗口，旧用户端进入只读。
2. 对旧服务器客户数据做最终备份。
3. 重跑幂等迁移，确认新增数量和逐用户校验。
4. 运行发布门禁。
5. 将反向代理流量切至新 PWA/API。
6. 用迁移用户抽样验证：登录、孩子、任务、训练统计、历史报告、教练记录。
7. 观察错误率、队列、AI 降级和数据库连接至少 30 分钟。
8. 旧服务继续只读保留，不立即删除。

## 5. 回滚

若关键流程失败：

1. 停止新平台写入；
2. 将流量切回旧只读服务并评估是否临时恢复写入；
3. 使用切流前归档在隔离环境验证恢复；
4. 明确确认目标后执行恢复：

```bash
./.venv/bin/python scripts/restore_state.py \
  --archive ../../backups/pre-cutover-YYYYMMDD-HHMMSS.tar.gz \
  --confirm RESTORE
```

恢复命令会先校验全部文件，校验失败时不会修改数据库。
