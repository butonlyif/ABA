# ABA智能助手 macOS 使用说明

## 1. 启动

1. 解压 `ABA智能助手_macOS_vX.X.X.zip` 到任意位置（建议放到「应用程序」或桌面）
2. 进入解压后的文件夹
3. **首次双击 `Start_ABA_Assistant.command`** 时，macOS 可能提示「无法打开未签名应用」：
   - 解决方法：在文件上**右键 → 打开 → 再次点击「打开」**
   - 之后双击即可正常启动
4. 启动器会在终端窗口显示日志，并自动打开浏览器到 <http://127.0.0.1:8501>

## 2. 首次配置 API Key

包目录里有一份**可见的**配置示例 `env.example.txt`。

**最简单的做法**：
1. 用「文本编辑」打开 `env.example.txt`
2. 至少填入一个模型的 API Key：
   - `MINIMAX_API_KEY=xxx`（推荐，国内最快）
   - 或 `OPENAI_API_KEY=xxx`
   - 或 `ANTHROPIC_API_KEY=xxx`
3. 「文件 → 另存为」，把名字改成 `.env`（开头是个点）保存到同一目录
4. 再次双击 `Start_ABA_Assistant.command`

> 启动器首次运行也会自动把 `env.example.txt` 复制为 `.env`，但 `.env` 是隐藏文件——Finder 默认不显示。可以在 Finder 里按 **⌘ + Shift + .** 临时显示隐藏文件来直接编辑它。

## 3. 关闭

回到启动器打开的终端窗口，按 `Ctrl + C` 即可退出。直接关掉终端窗口也能停止服务。

## 4. 数据位置

所有用户/孩子档案、对话记录、向量库都存在包目录下：

```
ABA智能助手_macOS_vX.X.X/
├── data/users/     ← 用户与孩子档案
├── data/chromadb/  ← 知识检索向量库
└── logs/           ← 运行日志
```

更换电脑前请整体复制这个文件夹，账号和记忆都会跟着走。

## 5. 常见问题

**Q：双击没反应 / 启动一闪而过**
A：在终端里手动运行可看到错误：
```bash
cd /path/to/ABA智能助手_macOS_vX.X.X
./启动\ ABA智能助手.command
```

**Q：提示「应用已损坏」**
A：执行下面这条命令一次性解除隔离：
```bash
xattr -dr com.apple.quarantine "/path/to/ABA智能助手_macOS_vX.X.X"
```

**Q：浏览器没自动打开**
A：手动打开 <http://127.0.0.1:8501>

**Q：8501 端口被占用**
A：编辑 `.env`，把 `ABA_PORT=8501` 改成 `ABA_PORT=8502`（或其他空闲端口），再启动。

## 6. 系统要求

- macOS 11 (Big Sur) 及以上
- Apple Silicon（M1/M2/M3/M4）
- 至少 4 GB 内存、800 MB 磁盘
- 联网（用于调用 AI API；应用本体与依赖均已内置）
