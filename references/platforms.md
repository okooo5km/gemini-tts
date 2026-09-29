# 跨平台安装与执行

脚本要求 Python 3.10+，只依赖标准库，不需要 Bash、ffmpeg 或额外 pip 包。先确认执行端的系统、Shell 和 Python，再组装命令。运行时从实际技能文件位置定位脚本；不要把个人绝对路径写进技能。

## Windows PowerShell（5.1 / 7）

检查解释器：`py -3 --version`。若不可用，检查 `python --version` 并用 `python -X utf8` 替换下面的 `py -3 -X utf8`。不要把 Microsoft Store 的安装提示视为成功运行 Python。

首次安装到当前用户目录：

```powershell
$skillDir = Join-Path $HOME '.agents/skills/gemini-tts'
New-Item -ItemType Directory -Force (Split-Path $skillDir) | Out-Null
git clone https://github.com/okooo5km/gemini-tts.git "$skillDir"
New-Item -ItemType Directory -Force "$HOME/.codex/skills", "$HOME/.claude/skills" | Out-Null
New-Item -ItemType Junction -Path "$HOME/.codex/skills/gemini-tts" -Target "$skillDir"
New-Item -ItemType Junction -Path "$HOME/.claude/skills/gemini-tts" -Target "$skillDir"
```

仅在目标不存在时创建；已有安装先检查，不强制替换。对本地目录使用 Junction，避免普通 SymbolicLink 所需的开发者模式或管理员权限。若文件系统不支持链接，可把技能复制到 agent 技能目录，后续需同步更新。客户端能否识别链接仍取决于其发现机制。`$HOME` 在 PowerShell 是保留变量，不要重新赋值。

交互配置，不把密钥放进命令历史：

```powershell
py -3 -X utf8 "$skillDir/scripts/tts.py" configure
```

配置路径为 `$HOME/.config/gemini-tts/config.json`，和 macOS/Linux 的布局一致；需要改位置可设置 `$env:GEMINI_TTS_CONFIG`。已有密钥变量由 `$env:GEMINI_API_KEY` 或 `$env:GOOGLE_API_KEY` 读取。配置是明文，Windows 继承目录 ACL，不会自动安装或变更 ACL；自定义路径应放在受保护的当前用户目录。

在当前目录写入 UTF-8 正文并生成（支持空格和中文路径）：

```powershell
$scriptPath = Join-Path $skillDir 'scripts/tts.py'
$textPath = Join-Path (Get-Location) 'story.txt'
Set-Content -LiteralPath $textPath -Value '你好，今天想给你讲一个小故事。' -Encoding UTF8
$ttsArgs = @(
  $scriptPath, 'generate',
  '--file', $textPath,
  '--voice', 'Sulafat',
  '--delivery', '自然普通话，像坐在孩子身边讲故事',
  '--out', (Join-Path (Get-Location) 'story.wav')
)
py -3 -X utf8 @ttsArgs
```

5.1 的 `-Encoding UTF8` 写 BOM、7 通常不写；脚本都接受。默认 `>` 可能写 UTF-16，不能替代以上命令。若把示例保存为含中文的 `.ps1` 并用 PowerShell 5.1 运行，该脚本本身请保存为 UTF-8 BOM。

标准输入约定为 UTF-8。确实需要管道时先在当前会话设置 `$OutputEncoding = [System.Text.UTF8Encoding]::new($false)`，再管道传入；这不改变系统设置。推荐文件输入以避开旧 Shell 的编码转换。

## macOS / Linux

```bash
python3 --version
python3 "$HOME/.agents/skills/gemini-tts/scripts/tts.py" configure
python3 "$HOME/.agents/skills/gemini-tts/scripts/tts.py" generate --file "story.txt" --out "story.wav"
```

激活了虚拟环境时可使用其中的 Python。已有密钥通过进程环境传递，不写入 shell 脚本。文件路径由 pathlib 处理；`--file`、`--dialogue`、`--out` 和配置路径支持 `~`。脚本不会替你展开路径字符串中的 `$HOME` 或 `%USERPROFILE%`，请让相应 Shell 展开。

## 集成到其他 Agent

Python 调用方使用 `sys.executable` 和参数列表执行子进程，避免把路径和文本拼接成 shell 字符串；捕获输出时指定 `encoding="utf-8"`。CLI 输出和标准输入使用 UTF-8。引用代码/音频时遵循客户端的文件显示能力，不要求所有客户端都支持相同的音频嵌入。

`configure` 需要支持隐藏输入的交互终端；没有此能力时退出，不降级成回显密钥。自动化环境使用已注入的环境变量。macOS/Linux 检查配置权限；Windows 不用 POSIX 模式位判定 ACL。

## 依据

- [Agent Skills 脚本指南](https://github.com/agentskills/agentskills/blob/main/docs/skill-creation/using-scripts.mdx)：清晰的 CLI、可发现的帮助和脚本资源。
- [Microsoft 文件型技能示例](https://github.com/microsoft/agent-framework/tree/main/python/samples/02-agents/skills/file_based_skill)：按文件定位资源，子进程执行技能脚本。
- [Python Windows / UTF-8 模式](https://docs.python.org/3/using/windows.html#utf-8-mode)：解释器选择与旧编码差异。
- [PowerShell 编码](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_character_encoding)：5.1 与 7 的差异。
- [PowerShell New-Item](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-item)：Junction 与 SymbolicLink。

这些是本项目采用的设计依据，并不意味着参考项目替本项目验证了兼容性。验证范围由本仓库测试与 CI 给出。
