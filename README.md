# IPO / Pre-IPO 企业池筛选 Agent

基于 AgentScope 的投行承揽预研工具：从一批企业中形成“优先接触、条件跟进、培育、风险整改优先、观察或暂缓”的相对建议，并给出待验证假设、风险核验闭环和下一步动作。

它不判断企业是否满足IPO条件，不承诺融资或上市结果，也不使用数值打分。

## 核心原则

- 企业输入只能来自《数据表信息项-需求-数据探查v2.xlsx》中标记为“纳入需求（投行）=√”的字段。
- JSON 输入按需选择字段；仅 `qymc`、`uniscid` 必填。非勾选字段会被程序拒绝。
- Python 不负责企业排序或路径分流，只做字段白名单校验、实体归一和中立证据整理。
- 中文 Skill 在运行时由 AgentScope 加载，负责整批企业的相对筛选、最大待验证假设和核验动作。
- 不将流水、税额、专利数量或登记信息直接等同于营业收入、利润、估值、融资需求或上市能力。

## 项目结构

```text
IPO-Agent/
├─ README.md                         # 仓库首页说明
├─ .gitignore
├─ ipo-agent-cli/                    # Python / AgentScope 命令行程序
│  ├─ config/agent.config.json       # 模型、Skill路径和运营方配置
│  ├─ data/                          # JSON 示例及可提交的企业数据
│  ├─ ipo_agent/                     # 输入校验、证据整理、调用与输出校验
│  ├─ scripts/generate_demo_batch.py
│  └─ main.py
└─ ipo-project-screening/            # 运行时加载的中文 Skill
   ├─ SKILL.md
   └─ references/
```

## 判断逻辑

```mermaid
flowchart LR
    A[已勾选Excel字段导出JSON] --> B[字段白名单与实体归一]
    B --> C[中立证据包：不排序]
    C --> D[AgentScope加载中文Skill]
    D --> E[批量比较、路径与行动]
    E --> F[证据引用和JSON校验]
```

Skill 仅对输入已有线索建立以下预研风险模块，而非完整IPO尽调或红黄绿评级：

- M1：主体与出资
- M2：股权出质与控制权待核
- M3：年报、税务、纳税和银行流水的口径核验
- M8：行政处罚、严重违法失信、失信被执行、海关失信与专利权属待核

每家 `engage_now` 企业须输出一个“最大待验证假设”，说明该假设对是否继续投入承揽预研资源的影响、支撑证据和最短核验动作。

## 运行

环境：Python 3.12、AgentScope 2.x、OpenAI Chat Completions 兼容接口。

```powershell
cd "C:\Users\GY\Desktop\IPO Agent\ipo-agent-cli"
$python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
& $python -m pip install -r requirements.txt
```

只整理证据、不调用模型：

```powershell
& $python main.py --input data\example-batch.json --output output\evidence.json --dry-run
```

调用模型做完整筛选：

```powershell
& $python main.py --input data\example-batch.json --output output\selection.json
```

默认 endpoint 与模型位于 [agent.config.json](ipo-agent-cli/config/agent.config.json)：

- endpoint：`https://api.chatanywhere.tech/v1/chat/completions`
- model：`deepseek-v4-flash`

API Key 通过 `IPO_AGENT_API_KEY`、`CHATANYWHERE_API_KEY` 或 `ipo-agent-cli/api_key.txt` 读取；不得提交到仓库。

## 关键文档

- [完整 CLI 输入、运行与输出说明](ipo-agent-cli/README.md)
- [企业输入字段白名单](ipo-agent-cli/ipo_agent/input.py)
- [中文筛选 Skill](ipo-project-screening/SKILL.md)
- [Excel勾选字段映射](ipo-project-screening/references/excel-selected-data-boundary.md)
- [预研风险模块与核验闭环](ipo-project-screening/references/pre-screen-risk-modules.md)
- [模型输出JSON契约](ipo-project-screening/references/output-templates.md)

## 数据与合规

企业 JSON 可以纳入仓库；密钥、Excel 原始文件和运行输出会被 `.gitignore` 排除。真实企业数据入库前，应确认数据授权、敏感信息最小化和团队访问权限。
