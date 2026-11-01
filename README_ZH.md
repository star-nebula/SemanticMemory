# SemanticMemory

简体中文 | [English](README.md)

[![CI](https://github.com/star-nebula/SemanticMemory/actions/workflows/ci.yml/badge.svg)](https://github.com/star-nebula/SemanticMemory/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

SemanticMemory 是一个 evidence-first、local-first 的“当前事实与任务”存储层。
它把 Agent 现在应当相信的 claim、仍需执行的 task 保存为可读 Markdown，并通过
轻量 CLI 与 MCP stdio server 提供访问。

它适合作为 [ReMe](https://github.com/agentscope-ai/ReMe) 的配套项目：

| 层次 | 回答的问题 | 存储内容 |
|---|---|---|
| ReMe | 发生过什么、讨论过程是什么、证据在哪？ | 原始会话、daily、digest、resource |
| SemanticMemory | 现在什么是真的、接下来还要做什么？ | claim、task、来源 quote |

SemanticMemory 不 import ReMe 核心代码。可选字段 `reme_ref` 只负责把当前 claim
指回 ReMe 证据，不成为运行时硬依赖。

本项目是 ReMe 的社区配套项目，不是 ReMe 官方包。PyPI 发行名为
`semantic-memory-reme`，Python import 命名空间为 `semantic_memory_reme`。

## 为什么

Agent 记忆经常混在一起的三件事是：

1. 原始证据；
2. 当前事实；
3. 仍需执行的任务。

SemanticMemory 把后两者保存为确定性文件，并显式记录来源、评审状态、生命周期和
替代关系。任何派生索引都不是权威数据。

## 安装

需要 Python 3.11 或更高版本。

发行包名规划为 `semantic-memory-reme`：

```bash
python -m pip install semantic-memory-reme
```

在首个 PyPI 版本发布前，请从源码安装：

```bash
git clone https://github.com/star-nebula/SemanticMemory.git
cd SemanticMemory
python -m pip install -e ".[dev]"
```

## 快速开始

先运行一个不落盘、可完整查看的示例：

```bash
semantic-memory demo
```

demo 会在临时目录创建 claim、来源 quote、关联 task，并立即返回搜索结果。

初始化私有工作区：

```bash
semantic-memory init --root .semantic-memory
```

创建来源与候选 claim：

```bash
mkdir -p sources .semantic-memory/inbox
printf '%s\n' 'I prefer concise explanations in English.' > sources/profile.md
cp templates/Memory-Claim.md .semantic-memory/inbox/pref-concise-explanations.md
```

把候选改为唯一 `id`，设置 `status: active`，并把 `sources[].path` 指向
`../sources/profile.md`，然后晋升：

```bash
semantic-memory add .semantic-memory/inbox/pref-concise-explanations.md \
  --root .semantic-memory
```

搜索当前事实：

```bash
semantic-memory search "concise" --root .semantic-memory --json
```

管理任务：

```bash
semantic-memory task add \
  --root .semantic-memory \
  --project demo \
  --title "验证第一条 claim"
semantic-memory task list --root .semantic-memory --json
```

## 工作区布局

```text
.semantic-memory/
  claims/<kind>/<id>.md
  tasks/open/
  tasks/done/
  inbox/
  archive/
```

工作区根目录解析顺序：

1. `--root`
2. `SEMANTIC_MEMORY_ROOT`
3. `./.semantic-memory`

相对 source path 从工作区根目录解析。私有本地环境允许绝对路径。

## CLI

```text
semantic-memory init
semantic-memory demo
semantic-memory validate
semantic-memory search QUERY
semantic-memory get CLAIM_ID
semantic-memory trace CLAIM_ID
semantic-memory changes --since YYYY-MM-DD
semantic-memory add FILE
semantic-memory transition CLAIM_ID --status STATUS
semantic-memory review CLAIM_ID --status STATUS
semantic-memory set-validity CLAIM_ID --valid-to YYYY-MM-DD
semantic-memory maintenance
semantic-memory task validate|list|add|complete|cancel
```

支持机器读取的命令可加 `--json`。

## MCP

推荐默认只读：

```json
{
  "mcpServers": {
    "semantic-memory": {
      "command": "semantic-memory-mcp",
      "args": ["--root", ".semantic-memory", "--read-only"]
    }
  }
}
```

只有确实需要写 claim/task 时才移除 `--read-only`。

只读工具：

- `semantic_status`
- `semantic_search`
- `semantic_get`
- `semantic_trace`
- `semantic_changes`
- `semantic_validate`
- `semantic_maintenance`
- `task_list`
- `task_validate`

## 证据规则

- 每条 claim 至少有一个 source path 和可核对 quote。
- `human_review: pending` 不是已接受事实。
- 替代旧 claim 时保留旧文件，并双向记录替代关系。
- 同一 `single` 槽位的 `subject + predicate + scope` 只能有一条 active claim。
- `valid_to` 表示时效，由 validate 与 maintenance 检查。

详见 [Schema.md](schema/Schema.md) 与 [architecture.md](docs/architecture.md)。

## ReMe 配套方式

ReMe 负责原始会话、时间线、Markdown memory 与证据检索；SemanticMemory 只保存
当前结论与证据指针，例如：

```yaml
reme_ref: reme/session/example.jsonl
```

推荐流程见 [docs/reme-integration.md](docs/reme-integration.md)。

## 隐私

SemanticMemory 不加密，可能包含敏感个人信息或商业信息。工作区应保持私有、定期
备份，并按环境设置文件权限。默认工作区目录已写入 `.gitignore`，
`semantic-memory init` 还会在工作区内再写一层忽略文件。

发布前运行：

```bash
python scripts/audit_release.py .
```

## 开发

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python -m build
python scripts/audit_release.py .
```

校验合成示例：

```bash
semantic-memory validate --root examples/minimal --json
semantic-memory task validate --root examples/minimal --json
```

## 许可证

Apache License 2.0。见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。
