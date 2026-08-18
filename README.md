# ReproFlow

**Turn bug reports into verified reproductions.**

> A bug report is a claim. A reproduction is evidence.

ReproFlow is an open-source runtime and emerging specification for executable bug reports. It runs candidate reproductions inside isolated Docker environments, captures execution evidence, and verifies that the expected failure happens repeatedly.

**AI may propose experiments. ReproFlow verifies them.**

[中文说明](#中文)

## Why ReproFlow?

Maintainers often receive reports like:

> “This crashes with some Unicode input.”

A useful result is not another paragraph of speculation. A useful result is an executable artifact:

```text
Bug report
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

`v0.1.0-alpha.1` implements the deterministic runtime foundation:

- Python repository inspection
- `reproflow/v1` YAML schema validation
- isolated Docker execution
- no network during the reproduction phase
- CPU, memory, PID, capability and filesystem restrictions
- stdout / stderr / exit-code / timeout capture
- expected-failure matching
- repeated verification
- a Unicode failure demo

The AI issue parser and bounded experiment planner are the next milestone.

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

Expected result:

```text
Run 1/3: MATCH
Run 2/3: MATCH
Run 3/3: MATCH

VERIFIED REPRODUCTION
Repeatability: 3/3
```

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

The important separation is between **how to run the experiment** and **what counts as the target failure**. A random non-zero exit should not automatically count as a successful reproduction.

## Security model

Repository content, issue text, and generated experiments should be treated as untrusted input.

The current reproduction phase runs Docker with:

- networking disabled
- read-only root filesystem
- no Docker socket mount
- all Linux capabilities dropped
- `no-new-privileges`
- 1 GiB memory limit
- 1 CPU limit
- PID limit
- execution timeout
- ephemeral container lifecycle

Setup commands are baked into an ephemeral image before the reproduction phase. Do not pass host secrets into build arguments or capsule files.

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
- [x] Unicode demo
- [ ] GitHub Issue parser
- [ ] provider-neutral AI interface
- [ ] bounded reproduction planner
- [ ] testcase minimizer
- [ ] regression-test generation
- [ ] GitHub Action

## Contributing

Issues and pull requests are welcome. Early contributions that improve schema validation, platform detection, failure signatures, logging, and sandbox hardening are especially useful.

## License

Apache-2.0.

---

<a id="中文"></a>

# 中文

**把 Bug 报告变成经过验证、可以真正运行的复现。**

> Bug 报告是一项主张；可执行复现才是证据。

ReproFlow 是一个开源的 Bug 复现运行时，并正在探索一种“可执行 Bug 报告”的开放规范。它会在隔离的 Docker 环境中运行候选复现，记录执行证据，并验证目标故障能否稳定、重复地出现。

**AI 可以提出实验，但由 ReproFlow 来验证。**

## 为什么做 ReproFlow？

维护者经常收到这样的 Issue：

> “某些 Unicode 输入会崩溃。”

真正有价值的结果不应该只是另一段 AI 推测，而应该是可以执行的证据：

```text
Bug 报告
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

ReproFlow 坚持 evidence-first：**模型输出本身永远不等于证明。**

## 当前状态

`v0.1.0-alpha.1` 先完成不依赖 AI 的确定性运行时基础：

- Python 仓库识别
- `reproflow/v1` YAML Schema 校验
- Docker 隔离执行
- 复现阶段默认断网
- CPU、内存、PID、Linux capability 与文件系统限制
- 捕获 stdout / stderr / exit code / timeout
- 目标失败条件匹配
- 多次重复验证
- Unicode 崩溃 Demo

下一阶段再加入 AI Issue parser 和有预算上限的实验 Planner。

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

预期结果：

```text
Run 1/3: MATCH
Run 2/3: MATCH
Run 3/3: MATCH

VERIFIED REPRODUCTION
Repeatability: 3/3
```

## `repro.yaml` 是什么？

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

其中最重要的是把两件事分开：

1. **实验怎么运行**；
2. **出现什么证据才算复现了目标 Bug**。

因此，程序因为另一个无关原因返回非零退出码，并不会自动被认定为“成功复现”。

## 安全模型

代码仓库内容、GitHub Issue 文本，以及未来由 AI 生成的实验，都应该被视为不可信输入。

当前 reproduction phase 默认使用：

- 禁止网络访问
- 根文件系统只读
- 不挂载 Docker socket
- 丢弃全部 Linux capabilities
- `no-new-privileges`
- 1 GiB 内存限制
- 1 CPU 限制
- PID 数量限制
- 执行超时
- 临时容器，用完销毁

依赖安装命令会在 reproduction phase 之前构建进临时镜像。不要通过 build args 或 capsule 文件把宿主机密钥传入构建过程。

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
- [x] Unicode demo
- [ ] GitHub Issue parser
- [ ] provider-neutral AI interface
- [ ] bounded reproduction planner
- [ ] testcase minimizer
- [ ] regression-test generation
- [ ] GitHub Action

## 参与贡献

欢迎提交 Issue 和 Pull Request。项目早期尤其欢迎 Schema 校验、项目环境识别、失败签名、日志输出和 Sandbox 安全加固方面的贡献。

## License

Apache-2.0。
