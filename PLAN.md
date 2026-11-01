# SemanticMemory 开源 v0.1.0 实施计划

> 历史计划：v0.1.1 起 PyPI 发行名为 `semantic-memory-reme`，Python 包名为
> `semantic_memory_reme`。

## 概述

把现有 `build/lib` 工作区中的 claim/task 核心与 MCP sidecar 迁移为独立 Python
包，保留既有 schema 与行为，增加可安装 CLI、合成示例、发布审计、CI 与开源文档。
最终产物先在本机 Git 仓库验证，不创建 remote、不推送。

## 架构决策

- 发布包名使用 `semantic-memory`，Python 包名使用 `semantic_memory`。
- `claim`、`task`、`mcp` 分层为独立模块，保留原公开函数语义。
- 工作区根目录按 `--root` → `SEMANTIC_MEMORY_ROOT` → `./.semantic-memory`
  解析，禁止机器专属默认值。
- ReMe 仅通过 `reme_ref` 与文档集成，不增加 Python 依赖。
- 首版采用 Apache-2.0，与 ReMe 一致。
- 未安装包时，测试前先执行 editable install；CI 与本地验证使用同一路径。

## 任务列表

### Phase 1：基础与防泄漏

- [x] Task 1：创建仓库骨架、包元数据、许可证、忽略规则和发布审计脚本。
  - Acceptance：`pyproject.toml` 可解析；审计脚本能发现测试夹具中的本机路径与秘密模式。
  - Verify：`python -m compileall scripts`；运行审计负例测试。
  - Files：`pyproject.toml`、`LICENSE`、`NOTICE`、`.gitignore`、`scripts/audit_release.py`。
  - Estimated scope：Medium。

### Checkpoint 1

- [x] 仓库不含真实私有数据。
- [x] 发布审计正例通过、负例失败。

### Phase 2：Claim 与 Task 核心

- [x] Task 2：迁移 claim 核心到 `semantic_memory.claims`。
  - Acceptance：现有 claim 测试迁移后全部通过；根目录可参数化。
  - Verify：`python -m unittest tests.test_claims -v`。
  - Files：`src/semantic_memory/claims.py`、`src/semantic_memory/errors.py`、`tests/test_claims.py`。
  - Estimated scope：Medium。

- [x] Task 3：迁移 task 核心到 `semantic_memory.tasks`。
  - Acceptance：现有 task 测试迁移后全部通过；路径解析与 claim 共享。
  - Verify：`python -m unittest tests.test_tasks -v`。
  - Files：`src/semantic_memory/tasks.py`、`src/semantic_memory/paths.py`、`tests/test_tasks.py`。
  - Estimated scope：Small。

### Checkpoint 2

- [x] 原 26 个测试全部通过。
- [x] 无默认机器专属路径。

### Phase 3：CLI 与 MCP

- [x] Task 4：实现统一 CLI 与 `init`。
  - Acceptance：claim/task 子命令可用；`init` 创建空工作区；JSON 输出稳定。
  - Verify：CLI 集成测试。
  - Files：`src/semantic_memory/cli.py`、`src/semantic_memory/__main__.py`、`tests/test_cli.py`。
  - Estimated scope：Medium。

- [x] Task 5：迁移 MCP sidecar。
  - Acceptance：只读工具集不暴露写操作；读写模式协议测试通过。
  - Verify：`python -m unittest tests.test_mcp -v`。
  - Files：`src/semantic_memory/mcp.py`、`tests/test_mcp.py`。
  - Estimated scope：Medium。

### Checkpoint 3

- [x] `semantic-memory` 与 `semantic-memory-mcp` 入口可运行。
- [x] 只读 MCP 不产生文件修改。

### Phase 4：契约、示例与安全

- [x] Task 6：增加 schema、模板、合成示例和安全测试。
  - Acceptance：示例零错误；路径穿越、候选越界和秘密扫描有测试。
  - Verify：全量 unittest。
  - Files：`schema/`、`templates/`、`examples/minimal/`、`tests/test_security.py`。
  - Estimated scope：Medium。

### Checkpoint 4

- [x] 示例可通过 CLI 校验。
- [x] 发布审计无问题。

### Phase 5：文档与发布准备

- [x] Task 7：补齐开源文档、ADR、CI 与变更记录。
  - Acceptance：README 中英文、贡献/安全/隐私/ReMe 配套说明完整；CI 覆盖 Linux/Windows。
  - Verify：链接与路径检查；CI YAML 语法检查。
  - Files：`README*`、`CONTRIBUTING.md`、`SECURITY.md`、`docs/`、`.github/workflows/ci.yml`、`CHANGELOG.md`。
  - Estimated scope：Medium。

- [x] Task 8：构建、安装、端到端验证并初始化 Git。
  - Acceptance：wheel/sdist 构建成功；editable install 后示例与 MCP 冒烟通过；git 初始提交干净。
  - Verify：`python -m build`、安装 smoke、审计、`git status`。
  - Files：无新增，仅修复验证问题。
  - Estimated scope：Small。

### Checkpoint 5

- [x] 全量测试与构建通过。
- [x] Git tracked files 不含私有内容。
- [x] 仓库可移动到批准路径。

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 旧代码含本机路径或跨模块导入 | 高 | 第一阶段全仓扫描；根目录统一从 `paths.py` 解析 |
| 个人声明或任务被误带入公开仓库 | 高 | 只使用 `examples/minimal` 合成数据；发布审计阻断 |
| MCP 写操作默认暴露 | 中 | 保留 `--read-only`，默认文档推荐只读 |
| Windows/Linux 路径差异 | 中 | 全量测试在本机 Windows；CI 增加 Ubuntu |
| Apache 版权声明误沿用 ReMe 作者 | 中 | 使用 Apache-2.0 标准文本，NOTICE 写 SemanticMemory contributors |

## 开放问题

无。发布基线已由用户确认。
