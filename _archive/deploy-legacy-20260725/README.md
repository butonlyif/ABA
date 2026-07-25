# 旧平台部署文件归档（2026-07-25）

这些文件是 Streamlit 旧平台（端口 8501/8502/8503）的部署配置。
旧平台已于 2026-07-25 停止运行，新平台（apps/, docker-compose.modern.yml）取而代之。

## 包含文件
- `Dockerfile` — 旧平台镜像构建（基于 src/MVP_web/）
- `docker-compose.yml` — 旧平台 3 容器（aba-assistant / aba-admin / life-coach）
- `_deploy_manual.sh` — 旧平台手动部署脚本
- `_deploy_modern.sh` / `deploy-modern.sh` — 早期并行部署脚本（已被 deploy.sh 取代）
- `tunnel.sh` — SSH 隧道（旧 admin 后台访问，新平台改用 nginx /admin/）
- `aba-assistant-deploy.tar.gz` — 旧平台镜像导出包
- `deploy.env` / `deploy.env.example` — 旧平台环境变量

## 回滚方式（如需临时恢复旧平台）
1. 服务器上镜像 `aba-assistant:latest` 仍保留（2.42GB）
2. 服务器上数据卷 `deploy/data/` 仍保留（162MB，已备份到 backups/legacy-shutdown-*.tar.gz）
3. 把这些文件还原到 deploy/，执行：
   `docker compose --env-file deploy/deploy.env -f deploy/docker-compose.yml up -d`

## 数据备份位置
- `backups/legacy-data-*.tar.gz` — 迁移前备份
- `backups/legacy-shutdown-20260725-170545.tar.gz` — 停服前最终备份
