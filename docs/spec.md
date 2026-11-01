# 规格：SemanticMemory 开源 v0.1.0

## 目标

把 SemanticMemory 从私有知识库中拆出，发布为一个可独立使用、也可作为 ReMe
配套项目的本地优先开源项目。

SemanticMemory 负责“当前事实层”：

- claim 回答“现在什么是真的”；
- task 回答“接下来要做什么”；
- `sources[].quote` 保留可核对证据，可选 `reme_ref` 指向原始上下文。

ReMe 负责“原文与情景证据层”：

- 原始会话、daily/digest、resource 与时间线；
- 对证据的检索、归纳和演化。

首版必须把边界写清楚，并保持低耦合。SemanticMemory 不 import ReMe 核心代码。

### 用户

- 使用 Codex、Claude Code、Qoder 或其他 MCP 客户端的开发者；
- 已使用 ReMe、希望在其上增加可审阅当前状态层的用户；
- 已用 Markdown 管理笔记、需要确定性 claim/task 存储的个人用户。

### 成功

新用户无需 API Key 或网络，即可安装项目、初始化空工作区、写入带证据的
claim、通过 CLI 与 MCP 搜索、管理 task，并运行完整测试套件。

## 技术栈

- Python 3.11+
- 标准库 + PyYAML
- `unittest`
- 基于 newline-delimited JSON-RPC 2.0 的 MCP stdio sidecar
- `pyproject.toml` + setuptools
- GitHub Actions CI
- Apache License 2.0

首版不包含 GUI、embedding、LLM 依赖、数据库或常驻后台服务。

## 命令

以下命令属于公开契约：

```bash
# 开发安装
python -m pip install -e ".[dev]"

# 全部测试
python -m unittest discover -s tests -v

# 校验
semantic-memory init --root .semantic-memory
semantic-memory validate --root examples/minimal --json
semantic-memory task validate --root examples/minimal --json

# 搜索与读取
semantic-memory search "language preference" --root examples/minimal --json
semantic-memory get pref-language-zh --root examples/minimal --json
semantic-memory trace pref-language-zh --root examples/minimal --json

# MCP sidecar
semantic-memory-mcp --root examples/minimal --read-only

# 构建发布物
python -m build
```

工作区根目录解析顺序：

1. `--root`
2. `SEMANTIC_MEMORY_ROOT`
3. 当前目录下的 `.semantic-memory`

任何默认行为都不得指向私有知识库或其他机器专属路径。

## 项目结构

```text
SemanticMemory/
  src/semantic_memory_reme/
    __init__.py
    claims.py          # claim schema、证据、生命周期、搜索
    tasks.py           # Markdown task 生命周期
    mcp.py             # 只读/可写 MCP stdio sidecar
    cli.py             # 统一 CLI 入口
  schema/
    Schema.md
    claim.schema.json
    task.schema.json
  templates/
    Memory-Claim.md
    AGENTS.md
  examples/
    minimal/
      claims/
      tasks/open/
      tasks/done/
      inbox/
      sources/
  docs/
    architecture.md
    reme-integration.md
    privacy.md
    migration.md
  tests/
    fixtures/
    test_claims.py
    test_tasks.py
    test_mcp.py
    test_cli.py
    test_security.py
  scripts/
    audit_release.py
  .github/workflows/ci.yml
  README.md
  README_ZH.md
  CONTRIBUTING.md
  CODE_OF_CONDUCT.md
  SECURITY.md
  CHANGELOG.md
  LICENSE
  NOTICE
  pyproject.toml
  .gitignore
```

`examples/minimal` 只含合成数据。真实 claim、task、inbox、Archive、备份和本机
Agent 配置不得复制进仓库。

## 代码风格

使用 Python 3.11+ 类型标注、`pathlib.Path`、小而明确的公开函数和显式错误。
所有文件写入必须原子化，所有用户可控路径必须限制在预期根目录内。

```python
def resolve_workspace_root(value: str | None) -> Path:
    raw = value or os.environ.get("SEMANTIC_MEMORY_ROOT") or ".semantic-memory"
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise WorkspaceError(f"workspace does not exist: {root}")
    return root
```

其他约定：

- 中文文档是一等公民；README 同时提供中文与英文。
- CLI JSON 输出稳定、UTF-8、可机器读取。
- 公开错误不包含秘密或完整私有来源正文。
- 公开行为变化必须同步 schema、CLI 与迁移文档。

## 测试策略

- 单元测试覆盖 claim 解析、证据校验、生命周期、替代关系、搜索、task
  生命周期和根目录解析。
- 集成测试覆盖 CLI 与 MCP stdio，使用临时工作区。
- 安全测试覆盖路径穿越、候选文件 containment、只读 MCP、畸形 frontmatter
  与发布审计检测。
- 测试不得依赖网络、API Key、ReMe 安装或任何私有文件。
- CI 在 Ubuntu 与 Windows 上运行 Python 3.11、3.12、3.13。
- 当前 26 个测试是迁移基线；重组前必须全部通过。

## 边界

### 始终

- 保持 evidence-first：每条 claim 必须有 source path 与 quote。
- 保持 `human_review: pending` 不等于已接受事实。
- 写入使用原子替换。
- 提交前运行测试、发布审计并检查 `git diff`。
- ReMe 集成只走文档与可选指针，不成为硬依赖。
- 示例只使用合成或公共领域内容。

### 先询问

- 修改许可证。
- 创建或推送公开 GitHub 仓库。
- 发布到 PyPI。
- 增加 LLM、embedding、数据库或网络依赖。
- 把任何现有用户 claim/task 复制进公开仓库。

### 永不

- 发布知识库中的 `claims/`、`tasks/`、`inbox/`、`Archive/`、`.backup/` 或私有集成。
- 提交用户名、本机绝对路径、token、Cookie、密码、私钥、求职数据、公司数据或无关 PII。
- 把 ReMe 核心代码 import 进 SemanticMemory。
- 自动把 `human_review: pending` 改成 accepted。
- 未经用户明确批准创建 remote 或 push。

## 首版内容

公开仓库包含：

- claim store 与 task store 核心逻辑；
- 统一 CLI 与 MCP stdio sidecar；
- Markdown schema 与模板；
- 合成的 minimal workspace；
- ReMe 作为证据层的配套说明；
- security、privacy、contribution 与 release-audit 文档；
- CI 与包元数据。

公开仓库排除：

- 当前私有 SemanticMemory 数据；
- 本机 `integrations/AI工具自定义指令*.md`；
- 含机器绝对路径的本机 `mcp.example.json`；
- 与私有知识库绑定的迁移和归档脚本。

## 兼容契约

- 保持 `semantic-memory/v1` 与 `semantic-memory-task/v1`。
- 保持既有 status、review state、claim kind 与 task state 稳定。
- CLI 可重组，但等价行为必须继续可用。
- `reme_ref` 只作 opaque pointer，SemanticMemory 不解析、不 import。
- MCP 写模式继续 opt-in；推荐默认只读。

## 隐私与安全

- 发布审计扫描 Windows/用户绝对路径、私钥标记、常见凭据模式、个人邮箱和已知私有名称。
- candidate claim 必须解析到 `<root>/inbox` 内。
- 本地使用允许绝对 source path；公开示例只使用相对合成路径。
- MCP 只读模式不得暴露写工具。
- 文档必须提醒：SemanticMemory 数据可能包含敏感个人信息，应自行备份与限权。

## 成功标准

- 在批准路径下存在干净 Git 仓库。
- tracked files 不含私有数据或机器专属路径。
- `python -m unittest discover -s tests -v` 全部通过。
- `python -m build` 生成 wheel 与 sdist。
- `pip install -e ".[dev]"` 后两个 CLI 入口可用。
- 示例工作区校验为零错误。
- 只读 MCP 只列出读工具，且不产生写入。
- README 中英文、schema、ReMe 配套指南、安全政策与贡献指南完整。
- CI 覆盖 Linux/Windows 与支持的 Python 版本。
- 仓库可由人工创建 GitHub remote 并发布。

## 已确认基线

用户已批准默认发布基线：Apache-2.0，仓库
`star-nebula/SemanticMemory`，独立本地仓库，版本 `0.1.0`，
首版 core-only。
