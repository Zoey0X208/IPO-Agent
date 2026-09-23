# IPO Agent CLI

此目录是命令行程序入口。项目整体说明、数据边界、Skill逻辑和运行方式请见仓库根目录的 [README](../README.md)。

快速运行：

```powershell
cd ipo-agent-cli
$python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
& $python main.py --input data\example-batch.json --output output\evidence.json --dry-run
```

企业输入JSON仅允许使用 Excel 中“纳入需求（投行）=√”字段；具体白名单在 [input.py](ipo_agent/input.py)，筛选规则在 [中文 Skill](../ipo-project-screening/SKILL.md)。
