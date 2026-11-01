# Launch Kit

## Product Positioning

Use this sentence consistently:

> ReMe remembers what happened. SemanticMemory tracks what is still true.

SemanticMemory is a community companion, not an official ReMe package. The
integration is deliberately loose: ReMe keeps episodic evidence, while
SemanticMemory keeps reviewed current facts, source quotes, and related tasks.

## One-Line Descriptions

- Short: `Evidence-first current facts and tasks for agents, designed to pair with ReMe.`
- GitHub: `Community ReMe companion for evidence-first current facts and tasks | Markdown + CLI + MCP`
- MCP directory: `Keep current facts, decisions, and tasks in Markdown with verifiable source quotes and optional ReMe evidence pointers.`

## 60-Second Demo

```bash
python -m pip install \
  https://github.com/star-nebula/SemanticMemory/releases/download/v0.1.1/semantic_memory_reme-0.1.1-py3-none-any.whl
semantic-memory demo
```

The demo shows:

1. a source sentence;
2. a current claim with an exact quote;
3. a related task pointing at the claim;
4. a search result that returns the current fact.

The temporary workspace is discarded automatically.

## ReMe Show and Tell

Title:

> SemanticMemory: a current-fact companion for ReMe

Body:

> ReMe is very good at keeping the evidence: sessions, daily notes, digests, and
> resources. I kept running into a second problem after retrieval, though: an old
> decision and a current decision can both be present in memory.
>
> I built SemanticMemory as a small community companion for that layer. It stores
> reviewed current facts, preferences, constraints, decisions, and tasks as plain
> Markdown. Every claim includes a source quote and can point back to ReMe through
> an optional `reme_ref`.
>
> The split is:
>
> - ReMe: what happened, and where is the evidence?
> - SemanticMemory: what should the agent treat as true now, and what still needs action?
>
> It ships with a CLI and a read-only-by-default MCP sidecar. It does not import
> ReMe core code or start a separate service.
>
> Quick demo:
>
> ```bash
> python -m pip install \
>   https://github.com/star-nebula/SemanticMemory/releases/download/v0.1.1/semantic_memory_reme-0.1.1-py3-none-any.whl
> semantic-memory demo
> ```
>
> Repository: https://github.com/star-nebula/SemanticMemory
>
> This is an independent community project, not an official ReMe package. I would
> especially value feedback on the evidence boundary and the ReMe integration
> workflow.

## MCP Directory Entry

Name:

> SemanticMemory for ReMe

Description:

> Evidence-first Markdown store for current facts and tasks, with source quotes,
> lifecycle review, CLI access, and an optional MCP stdio server.

Install:

```bash
python -m pip install \
  https://github.com/star-nebula/SemanticMemory/releases/download/v0.1.1/semantic_memory_reme-0.1.1-py3-none-any.whl
```

Configuration:

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

## Show HN

Title:

> Show HN: SemanticMemory – current facts and tasks for AI agents

Body:

> Agent memory systems are good at retrieving history, but history is not the same
> as current truth. A project can contain an old decision and a new decision at the
> same time.
>
> SemanticMemory keeps the current layer as plain Markdown: claims, source quotes,
> review state, lifecycle history, and tasks. It also has an optional pointer back
> to ReMe evidence, without depending on ReMe core code.
>
> The project includes a CLI and MCP stdio server. `semantic-memory demo` creates a
> temporary end-to-end example without leaving files behind.
>
> I am interested in feedback on the data model and on whether a separate
> current-fact layer is useful for other agent-memory systems.

## Reddit

Title:

> I separated “what happened” from “what is true now” in my agent memory stack

Opening:

> Most memory tools optimize retrieval over history. I wanted a deterministic layer
> for reviewed current facts and tasks, with evidence links back to the history.
>
> SemanticMemory stores claims and tasks as Markdown, requires a source quote for
> every claim, and can point to ReMe evidence with `reme_ref`. It does not depend on
> ReMe at runtime.

Use this opening for `r/LocalLLaMA` or `r/AI_Agents`, adapting the body to each
community's rules. Do not post the same text to multiple communities without
disclosure or adaptation.

## V2EX / Chinese Communities

Title:

> 给 Agent 记忆加一层“当前事实”：ReMe 负责证据，SemanticMemory 负责现在为真

Opening:

> 很多 Agent 记忆系统擅长检索历史，但历史里同时存在旧决定和新决定。SemanticMemory
> 把当前事实、偏好、约束、决策和任务单独存成 Markdown，每条 claim 都要求来源
> quote，并可通过 `reme_ref` 指回 ReMe 原文。
>
> 它不 import ReMe 核心代码，可以独立使用，也提供 CLI 和默认只读的 MCP sidecar。
>
> 一条命令看完整流程：
>
> ```bash
> python -m pip install \
>   https://github.com/star-nebula/SemanticMemory/releases/download/v0.1.1/semantic_memory_reme-0.1.1-py3-none-any.whl
> semantic-memory demo
> ```

## Launch Checklist

- [ ] GitHub Release wheel install succeeds
- [ ] GitHub release is public
- [ ] ReMe Show and tell post is published
- [ ] ReMe documentation PR is coordinated with maintainers
- [ ] MCP directory submissions are sent
- [ ] Launch post links to a working quick start
- [ ] Questions and issues receive a response within one day

