# ABA智能助手 - 构建说明（开发者）

本目录是从源码到客户绿色包的**唯一**构建入口。

## 1. 一行命令构建

在 macOS（Apple Silicon）终端中：

```bash
cd /path/to/AI_codex
bash release/build_release.sh
```

约 2–4 分钟完成（首次需下载 ~120 MB 嵌入式 Python，会被缓存到 `release/build_cache/`）。

产物：

```
release/output/
├── ABA智能助手_macOS_v1.1.0.zip       ~300 MB
└── ABA智能助手_Windows_v1.1.0.zip     ~280 MB
```

把 zip 直接发给客户即可：客户解压 → 双击启动器 → 浏览器自动打开。**无需安装 Python 或任何依赖。**

## 2. 选项

```bash
VERSION=1.1.1 bash release/build_release.sh   # 自定义版本号
SKIP_MAC=1    bash release/build_release.sh   # 只构 Windows
SKIP_WIN=1    bash release/build_release.sh   # 只构 macOS
```

## 3. 工作原理

每个绿色包结构：

```
ABA智能助手_<平台>_v1.1.0/
├── runtime/                         # 嵌入式 CPython 3.10.20
│   ├── bin/python3.10  (mac)        # 入口；win 是 runtime/python.exe
│   ├── Lib/site-packages/           # 离线安装的所有依赖
│   └── bootstrap.py                 # 跨平台启动入口
├── app/                             # 应用代码 + 知识库
│   ├── app_prototype.py             # ABA 主程序（端口 8501）
│   ├── life_coach_app.py            # 人生教练（端口 8503）
│   ├── coach_content.py / coach_engine.py / coach_styles.py  # 人生教练数据/引擎/样式
│   ├── agent.py / config.py / ...   # 其他模块（含 v1.2 的 curriculum/flashcards 等）
│   └── 知识库/                       # 安全/概念/QA/方法/活动
├── aba/
│   └── 图片卡_网络素材/              # OpenMoji 开放版权图标卡（随包发，体积小）
│                                     # PDF 大图库（1.7GB）因体积单独分发，不进绿色包
├── data/                            # 用户数据（首次启动自动建）
│   ├── users/
│   └── chromadb/
├── logs/
├── .env.example                     # 首次启动复制为 .env
├── README.md                        # 客户使用说明
└── 启动 ABA智能助手.command/.bat    # 平台启动器
```

启动流程：客户双击启动器 → 启动器调 `runtime/bootstrap.py` → bootstrap 用 `runtime/bin/python3.10` **同时启动两个 Streamlit 进程**：主应用 `app_prototype.py`（8501）与人生教练 `life_coach_app.py`（8503）→ 主应用端口就绪后自动打开浏览器；退出时两个进程一起关闭。bootstrap 还会自动注入一个共享的 `COACH_SSO_SECRET`，使两应用间可免登录互跳。

## 4. 依赖锁定与 wheelhouse

* 全部 142 个 wheel 已经离线在 `dist/wheelhouse_macos/` 与 `dist/wheelhouse_windows_full/`
* 锁版本清单：`release/requirements.lock`（与 wheelhouse 完全一致）
* 平台轮：cp310-cp310 + abi3，仅支持 Python 3.10.x

升级依赖时：

```bash
# 1) 在 mac 上重新生成 wheelhouse
pip download -r release/requirements.lock -d dist/wheelhouse_macos \
    --platform macosx_11_0_arm64 --python-version 310 --only-binary=:all:

# 2) 在 win 上（或交叉）生成
pip download -r release/requirements.lock -d dist/wheelhouse_windows_full \
    --platform win_amd64 --python-version 310 --only-binary=:all:

# 3) 重新跑 build_release.sh
```

## 5. 升级嵌入式 Python

编辑 `build_release.sh` 顶部：

```bash
PYTHON_TAG="20260510"     # python-build-standalone release tag
PYTHON_VER="3.10.20"      # 必须 3.10.x，匹配 wheelhouse 的 cp310 平台轮
```

最新 tag 见：<https://github.com/astral-sh/python-build-standalone/releases>

## 6. 已知限制

* **只支持 Apple Silicon Mac**。Intel Mac 需要额外一套 x86_64 wheelhouse 和嵌入式 Python；产品定位决定了暂不覆盖
* **Windows 包用 unzip 解 wheel 装到 site-packages 的方式**完成"交叉构建"。少数依赖有 post-install 脚本的情况下，建议直接到 Windows 上手动跑一次 `python -m pip install --no-index --find-links wheelhouse -r requirements.lock` 验证。当前依赖清单经过验证不需要 post-install 脚本
* **首次启动较慢**（约 10–20 秒）。Streamlit + chromadb + onnxruntime 冷启动开销较大，正常
* **未做代码签名/公证**。macOS 首次右键-打开即可绕过 Gatekeeper；Windows SmartScreen 同理。后续若需进店分发再做签名

## 7. 故障排查

| 现象 | 排查 |
|---|---|
| 下载 Python 卡住 | 网络问题，确认能访问 github.com；或手动下载 tar.gz 到 `release/build_cache/` |
| pip install 报错 some-pkg | 大概率 wheelhouse 缺包；用 `pip download --no-deps` 单独补一个 |
| Mac 启动 `streamlit: command not found` | 用嵌入 Python 跑：`runtime/bin/python3.10 -m streamlit run app/app_prototype.py` |
| Win 启动器闪退 | 在 PowerShell 里手动跑 `.\runtime\python.exe runtime\bootstrap.py` 看异常 |
