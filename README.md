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

`v0.1.0-alpha.3` connects the bounded reproduction loop to GitHub Issue input:

- local Markdown/text bug reports still work
- `https://github.com/<owner>/<repo>/issues/<number>` can now be passed directly to `--issue`
- issue title, body, labels, author, and bounded comments are loaded through the GitHub REST API
- optional `GH_TOKEN` / `GITHUB_TOKEN` authentication
- `--github-max-comments` limits comment ingestion (default 20, max 100)
- remote input is allowlisted to GitHub.com and size-bounded before planner ingestion
- pull requests are rejected from the Issue input path
- deterministic Verifier remains the only component allowed to declare success

The original deterministic `reproflow/v1` runtime remains usable without any AI provider.

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

### GitHub Issue URL — new in alpha.3

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

## `repro.yaml`

```yaml
schema: reproflow/v1
metadata:
  id: demo-unicode-username
  title: Unicode username crashes ASCII normalization
environment:
  image: python:3.12-slim
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
- [ ] smarter repository context selection
- [ ] testcase minimizer
- [ ] regression-test generation
- [ ] GitHub Action

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

`v0.1.0-alpha.3` 把 alpha.2 的受限 Issue → Experiment 闭环接到了真实 GitHub Issue 输入：

- 原来的本地 Markdown / 文本 Issue 继续支持
- `--issue` 现在可以直接接收 `https://github.com/<owner>/<repo>/issues/<number>`
- 通过 GitHub REST API 获取标题、正文、标签、作者和受数量限制的评论
- 可选使用 `GH_TOKEN` / `GITHUB_TOKEN`
- `--github-max-comments` 控制最多载入多少条评论，默认 20、最高 100
- 远程 URL 只允许 GitHub.com，进入 Planner 前还会进行大小限制
- Pull Request 不会被当成 Issue 输入
- 是否复现成功仍然只能由 deterministic Verifier 判断

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

## alpha.3：直接读取 GitHub Issue

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
- [ ] smarter repository context selection
- [ ] testcase minimizer
- [ ] regression-test generation
- [ ] GitHub Action

## 参与贡献

欢迎提交 Issue 和 Pull Request。项目早期尤其欢迎 Schema 校验、项目环境识别、失败签名、日志输出、输入安全和 Sandbox 安全加固方面的贡献。

## License

Apache-2.0。
