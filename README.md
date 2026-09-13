# ReproFlow

Turn bug reports into verified reproductions.

> A bug report is a claim. A reproduction is evidence.

ReproFlow is an open-source runtime and emerging specification for executable bug reports. It runs candidate reproductions inside isolated Docker environments, captures execution evidence, and verifies that the expected failure happens repeatedly.

AI may propose experiments. ReproFlow verifies them.

[中文说明](#中文)

## Why ReproFlow?

Maintainers often receive reports like:

> “This crashes with some Unicode input.”

A useful result is not another paragraph of speculation. A useful result is an executable artifact:

```text
Bug report / GitHub Issue
   ↓
Candidate experiment
   ↓
Isolated execution
   ↓
stdout / stderr / exit code / timeout
   ↓
Failure matching
   ↓
Repeat verification
   ↓
VERIFIED REPRODUCTION
```

ReproFlow is evidence-first: model output is never treated as proof by itself.

## Status

`v0.1.2` hardens failure targets so unrelated experiment failures are less likely to be mistaken for the reported bug. The current tree also includes maintainer and CI workflows:

- `exception` targets require an exception identity or distinctive stderr marker
- `exception_class` can match the final Python exception type directly
- `crash` targets require a signal, exact exit code, or distinctive output marker
- `signal` understands Linux/container `128 + signal` statuses such as `139` for `SIGSEGV`
- `nonzero_exit` remains the explicit broad matcher when any failing command is intentionally sufficient
- deterministic Verifier remains the only component allowed to declare success
- `init`, `list`, and `verify-all` commands for day-to-day capsule workflows
- machine-readable run results, Markdown evidence reports, and pytest regression generation

Evidence is exported as the versioned `reproflow/evidence/v1` JSON contract. Use `reproflow evidence` to inspect it and `reproflow badge` to generate an embeddable SVG status badge.

Existing evidence-first features remain available: GitHub Issue ingestion, bounded issue-aware repository context, repeated Docker verification, testcase minimization, and automation-friendly JSON diagnostics.

See [`docs/failure-targets.md`](docs/failure-targets.md) for the hardened matching rules.

## Requirements

- Python 3.11+
- Docker

## Install for development

```bash
git clone https://github.com/Ab-123-c/reproflow.git
cd reproflow
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Quick start

Inspect a Python repository:

```bash
reproflow inspect .
```

Validate a reproduction capsule:

```bash
reproflow validate examples/unicode-username/repro.yaml
```

Run and verify it:

```bash
reproflow run examples/unicode-username/repro.yaml
```

Check the local runtime:

```bash
reproflow doctor
```

Create a starter capsule:

```bash
reproflow init repro.yaml --id my-bug --title "My bug"
```

List or verify every capsule in a repository (useful in CI):

```bash
reproflow list .
reproflow verify-all examples --repo . --json
```

Minimize a file in a verified capsule:

```bash
reproflow minimize examples/unicode-username/repro.yaml \
  --file repro.py \
  --max-checks 40
```

Every accepted reduction is verified again in Docker; the original capsule remains untouched by default.

Save machine-readable evidence and a Markdown report from a run:

```bash
reproflow run repro.yaml --output .repro/my-bug
reproflow report .repro/my-bug
```

After a capsule is verified, generate a reviewable pytest regression test:

```bash
reproflow generate-regression repro.yaml --repo .
```

Run a capsule that depends on a source repository:

```bash
reproflow run examples/planner-demo/repro.yaml \
  --repo examples/planner-demo
```

## AI-assisted reproduction

Install the optional OpenAI provider:

```bash
pip install -e ".[ai]"
export OPENAI_API_KEY="..."
```

### Local bug report

```bash
reproflow reproduce \
  --repo examples/planner-demo \
  --issue examples/planner-demo/issue.md \
  --max-attempts 5
```

### GitHub Issue URL

```bash
reproflow reproduce \
  --repo . \
  --issue https://github.com/OWNER/REPO/issues/123 \
  --max-attempts 5
```

By default ReproFlow loads up to 20 Issue comments. To load only the Issue body:

```bash
reproflow reproduce \
  --repo . \
  --issue https://github.com/OWNER/REPO/issues/123 \
  --github-max-comments 0
```

Public Issues can be loaded without GitHub authentication. For private repositories or a higher API allowance, set a token in the environment instead of putting it on the command line:

```bash
export GH_TOKEN="..."
# or: export GITHUB_TOKEN="..."
```

The provider may parse the Issue and propose experiments, but it cannot mark an attempt as successful. Every proposed command is executed in the sandbox and checked by the deterministic Verifier. On success, ReproFlow writes evidence under `.repro/`.

See [`docs/github-issues.md`](docs/github-issues.md) for the GitHub input trust boundary and limits.

See [`docs/ci.md`](docs/ci.md) for batch verification, JSON output, and CI artifact handling.

### Preview repository context — available in v0.1.2

Before spending model tokens or starting Docker, inspect the bounded repository snapshot that ReproFlow would expose to the planner:

```bash
reproflow context \
  --repo . \
  --issue https://github.com/OWNER/REPO/issues/123
```

The preview shows selected file paths, deterministic relevance scores, and the bounded Issue terms used for ranking. A high score is only a context-selection hint; it is not evidence that the file caused the bug.

See [`docs/repository-context.md`](docs/repository-context.md) for the selector rules and threat model.

## `repro.yaml`

```yaml
schema: reproflow/v1
metadata:
  id: demo-unicode-username
  title: Unicode username crashes ASCII normalization
environment:
  image: python:3.12-slim
  variables:
    LC_ALL: C.UTF-8
files:
  repro.py: |
    "你".encode("ascii")
run:
  command: python repro.py
  timeout_seconds: 10
failure:
  type: exception
  stderr_contains:
    - UnicodeEncodeError
verification:
  repetitions: 3
  required_failures: 3
```

For deterministic output regressions, use `type: output_mismatch` with one of
`stdout_equals`, `stderr_equals`, `stdout_not_contains`, or `stderr_not_contains`.
The command must exit successfully and the declared output condition must fail.

The important separation is between how to run the experiment and what counts as the target failure. A random non-zero exit should not automatically count as a successful reproduction.

## Security model

Repository content, Issue text/comments, and generated experiments are untrusted input.

The GitHub Issue fetch happens in the CLI process before sandbox execution and is restricted to GitHub.com URLs. The reproduction phase continues to run Docker with networking disabled, a read-only root filesystem, no Docker socket mount, dropped Linux capabilities, `no-new-privileges`, CPU/memory/PID limits, a timeout, and an ephemeral container lifecycle.

Setup commands are baked into an ephemeral image before the reproduction phase. Do not pass host secrets into build arguments or capsule files. See [`SECURITY.md`](SECURITY.md).

## Project philosophy

ReproFlow deliberately separates exploration from proof:

```text
LLM / planner → proposes an experiment
Sandbox       → executes it
Verifier      → decides whether the target failure was reproduced
```

The long-term goal is for `reproflow/v1` to remain useful even without any AI provider: a portable, executable bug-report format that humans, CI systems, and agents can all run and verify.

## Roadmap

- [x] Repository inspector
- [x] `reproflow/v1` schema
- [x] Docker sandbox runner
- [x] deterministic verifier
- [x] repeated verification
- [x] local Issue text through provider interface
- [x] provider-neutral AI interface
- [x] bounded reproduction planner
- [x] attempt history and evidence ledger
- [x] GitHub Issue URL input
- [x] smarter repository context selection
- [x] testcase minimizer
- [x] regression-test generation
- [x] CI-friendly JSON evidence and Markdown reports
- [x] capsule discovery and batch verification
- [x] GitHub Action

## Contributing

Issues and pull requests are welcome. Early contributions that improve schema validation, platform detection, failure signatures, logging, input hardening, and sandbox hardening are especially useful.

## License

Apache-2.0.

---

# 中文

把 Bug 报告变成经过验证、可以真正运行的复现。

> Bug 报告是一项主张；可执行复现才是证据。

ReproFlow 是一个开源的 Bug 复现运行时，并正在探索一种“可执行 Bug 报告”的开放规范。它会在隔离的 Docker 环境中运行候选复现，记录执行证据，并验证目标故障能否稳定、重复地出现。

AI 可以提出实验，但由 ReproFlow 来验证。

## 为什么做 ReproFlow？

维护者经常收到这样的 Issue：

> “某些 Unicode 输入会崩溃。”

真正有价值的结果不应该只是另一段 AI 推测，而应该是可以执行的证据：

```text
Bug 报告 / GitHub Issue
   ↓
候选实验
   ↓
隔离环境真实执行
   ↓
stdout / stderr / exit code / timeout
   ↓
匹配目标故障
   ↓
重复验证
   ↓
VERIFIED REPRODUCTION
```

ReproFlow 坚持 evidence-first：模型输出本身永远不等于证明。

## 当前状态

`v0.1.2` 强化 failure target，避免把与目标 Bug 无关的非零退出误判为成功复现：

- `exception` 必须提供异常类型或明确的 stderr 特征
- 新增 `exception_class`，可以直接匹配最终 Python 异常类型
- `crash` 必须提供 signal、精确 exit code 或明确的输出特征
- 新增 `signal`，支持 Linux / 容器常见的 `128 + signal` 退出码，例如 `139 = SIGSEGV`
- 如果“任意非零退出”本来就是目标，仍然可以显式使用 `nonzero_exit`
- 是否复现成功仍然只能由 deterministic Verifier 判断

GitHub Issue 输入、bounded repository context、重复 Docker 验证、testcase minimization 和 JSON 诊断输出继续保留。详细规则见 [`docs/failure-targets.md`](docs/failure-targets.md)。

不使用任何 AI Provider 时，原来的 `reproflow/v1` runtime 仍然可以独立运行。

## 环境要求

- Python 3.11+
- Docker

## 开发安装

```bash
git clone https://github.com/Ab-123-c/reproflow.git
cd reproflow
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## 快速开始

识别 Python 仓库：

```bash
reproflow inspect .
```

校验一个 reproduction capsule：

```bash
reproflow validate examples/unicode-username/repro.yaml
```

真实执行并验证：

```bash
reproflow run examples/unicode-username/repro.yaml
```

## GitHub Issue 输入

先安装可选 OpenAI Provider：

```bash
pip install -e ".[ai]"
export OPENAI_API_KEY="..."
```

本地 Issue 文件仍然可以这样运行：

```bash
reproflow reproduce \
  --repo examples/planner-demo \
  --issue examples/planner-demo/issue.md \
  --max-attempts 5
```

现在也可以直接给 GitHub Issue URL：

```bash
reproflow reproduce \
  --repo . \
  --issue https://github.com/OWNER/REPO/issues/123 \
  --max-attempts 5
```

默认最多载入 20 条 Issue 评论。只想使用 Issue 正文时：

```bash
reproflow reproduce \
  --repo . \
  --issue https://github.com/OWNER/REPO/issues/123 \
  --github-max-comments 0
```

公开 Issue 不要求 GitHub Token。私有仓库或希望使用更高 API 配额时，把 Token 放在环境变量，而不是命令行参数里：

```bash
export GH_TOKEN="..."
# 或：export GITHUB_TOKEN="..."
```

Issue 正文、评论、仓库内容和实验输出都按不可信数据处理。模型只能提出结构化实验；真正的成功判定来自 Docker 中的真实执行证据与 Verifier。

更多细节见 [`docs/github-issues.md`](docs/github-issues.md)。

### v0.1.2：先预览 Planner 上下文

在消耗模型请求或启动 Docker 之前，可以先看 ReproFlow 最终会选哪些仓库文件：

```bash
reproflow context \
  --repo . \
  --issue https://github.com/OWNER/REPO/issues/123
```

输出会展示选中文件、确定性的相关性分数和用于排序的有限 Issue 关键词。分数只代表“更值得放进上下文”，不代表这个文件已经被证明与 Bug 有关。

选择规则和威胁模型见 [`docs/repository-context.md`](docs/repository-context.md)。

## 安全模型

GitHub Issue 抓取发生在 sandbox 运行之前的 CLI 进程，并且只接受 GitHub.com Issue URL。Reproduction phase 仍然默认禁止网络、根文件系统只读、不挂载 Docker socket、丢弃 Linux capabilities、启用 `no-new-privileges`、CPU/内存/PID 限制和执行超时。

依赖安装命令仍会在 reproduction phase 之前构建进临时镜像。不要通过 build args 或 capsule 文件把宿主机密钥传入构建过程。详见 [`SECURITY.md`](SECURITY.md)。

## 项目哲学

ReproFlow 刻意把“探索”和“证明”分离：

```text
LLM / Planner → 提出实验
Sandbox       → 真实执行
Verifier      → 判断目标故障是否确实复现
```

长期目标是：即使完全不用 AI，`reproflow/v1` 也依然有独立价值——成为一种人类、CI 和 Agent 都能够执行、交换和验证的可移植 Bug Report 格式。

## Roadmap

- [x] Repository inspector
- [x] `reproflow/v1` schema
- [x] Docker sandbox runner
- [x] deterministic verifier
- [x] repeated verification
- [x] local Issue text parser through provider interface
- [x] provider-neutral AI interface
- [x] bounded reproduction planner
- [x] attempt history and evidence ledger
- [x] GitHub Issue URL input
- [x] smarter repository context selection
- [x] testcase minimizer
- [x] regression-test generation
- [x] CI-friendly JSON evidence and Markdown reports
- [x] capsule discovery and batch verification
- [x] GitHub Action

## 参与贡献

欢迎提交 Issue 和 Pull Request。项目早期尤其欢迎 Schema 校验、项目环境识别、失败签名、日志输出、输入安全和 Sandbox 安全加固方面的贡献。

## License

Apache-2.0。
