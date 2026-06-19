# ABA智能助手 Windows 使用说明

## 1. 启动

1. 解压 `ABA智能助手_Windows_vX.X.X.zip` 到任意位置（建议放到 D 盘，避免桌面同步软件锁文件）
2. 进入解压后的文件夹
3. 双击 **`Start_ABA_Assistant.bat`**
4. 首次启动 Windows Defender / 360 等可能弹出安全提示：
   - 勾选「允许此应用运行」或「不再提示」即可
5. 启动器命令行窗口会显示日志，浏览器自动打开 <http://127.0.0.1:8501>

## 2. 首次配置 API Key

包目录里有一份**可见的**配置示例 `env.example.txt`。

**最简单的做法**：
1. 用「记事本」打开 `env.example.txt`
2. 至少填入一个模型的 API Key：
   - `MINIMAX_API_KEY=xxx`（推荐，国内最快）
   - 或 `OPENAI_API_KEY=xxx`
   - 或 `ANTHROPIC_API_KEY=xxx`
3. 「文件 → 另存为」，文件名输入 `".env"`（**带引号**，否则会自动加 .txt 后缀），保存到同一目录
4. 再次双击 `Start_ABA_Assistant.bat`

> 启动器首次运行也会自动把 `env.example.txt` 复制为 `.env`，但 `.env` 是隐藏文件——资源管理器默认不显示。可以在资源管理器顶部菜单「查看 → 显示 → 隐藏的项目」打开后直接编辑它。

## 3. 关闭

回到启动器打开的命令行窗口，按 `Ctrl + C`，确认 `Y`。直接关掉窗口也能停止服务。

## 4. 数据位置

所有用户/孩子档案、对话记录、向量库都存在包目录下：

```
ABA智能助手_Windows_vX.X.X\
├── data\users\     ← 用户与孩子档案
├── data\chromadb\  ← 知识检索向量库
└── logs\           ← 运行日志
```

换电脑前请整体拷贝这个文件夹，账号和记忆都会跟着走。

## 5. 常见问题

**Q：双击 .bat 一闪而过**
A：在 PowerShell 里手动跑可看到错误：
```powershell
cd D:\ABA智能助手_Windows_vX.X.X
.\启动\ ABA智能助手.bat
```

**Q：浏览器没自动打开**
A：手动访问 <http://127.0.0.1:8501>

**Q：8501 端口被占用**
A：用记事本编辑 `.env`，把 `ABA_PORT=8501` 改成 `ABA_PORT=8502` 或其他空闲端口。

**Q：杀毒软件拦截 `python.exe`**
A：把整个解压目录加入白名单。这是误报，应用本身不联网（除了 AI API）。

**Q：路径里有中文导致启动失败**
A：建议把解压目录路径换成全英文，例如 `D:\ABA_Assistant\`。

## 6. 系统要求

- Windows 10 (64 位) 1809 或以上 / Windows 11
- 至少 4 GB 内存、800 MB 磁盘
- 联网（用于调用 AI API；应用本体与依赖均已内置）
