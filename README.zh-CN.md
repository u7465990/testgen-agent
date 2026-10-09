<p align="right">
  <a href="README.md">English</a> | <b>简体中文</b>
</p>

# TestGen Agent
GitHub：https://github.com/u7465990/testgen-agent
**用 LLM 为 Java 项目自动生成 JUnit 4 测试。**

```
pip install testgen-agent
testgen-agent analyze  ./my-project
testgen-agent generate ./my-project
```

TestGen Agent 是一个独立的 Python 工具：输入一个 Java 项目，自动发现其中的方法，用 LLM（OpenAI、Anthropic，或任何 Anthropic 兼容端点如 DeepSeek）生成 JUnit 4 单元测试，编译并修复它们，**并度量这份结果到底好不好**。它把一套割裂的手工流程替换成单个自治的 agent。

> **度量正确的东西。** 编译通过只证明文件语法正确 —— 一个不含 `@Test` 的空类也能编译通过。因此 TestGen Agent 把 **mutation score（变异得分）** 作为头号指标：注入的故障中，生成的测试实际抓住了多大比例。这是 PiTest 测出来的。

> **验证状态：** 完整流水线已在随仓库附带的 `examples/demo-project` 上**端到端跑通并验证**（见[端到端验证](#端到端验证)）。设计上会自动识别 Maven、Ant、Gradle 和手工项目布局；但目前只有 **Maven** 路径在 demo 验证中实际跑过。

## 产出什么

所有产出都落在 `<项目>/.testgen-agent/` —— **刻意放在 `target/` 之外**，因为覆盖补测阶段会执行 `mvn clean`，放在里面会在运行途中被删掉。

| 产出 | 给谁看 | 内容 |
|---|---|---|
| `report.md` | **人** | mutation score 打头，然后是测试最弱的类、以及需要人工介入的地方 |
| `report.json` | CI / 工具 | 全部指标，机器可读 |
| `report.csv` | 表格软件 | 每个测试文件的明细 |
| `run.log` | **排查问题** | 控制台吞掉的诊断信息 —— javac 报错、LLM 重试、classpath 解析、各阶段耗时 |

此外还有生成的测试文件本身，写入项目的 `src/test/java/`。

## 功能

- **Java 项目发现** —— 自动识别 Maven、Ant、Gradle 或手工项目布局
- **方法提取** —— 解析源文件，抽出 FQN、签名、修饰符、参数类型、异常、分支条件、类上下文
- **仿 fuzzing 的测试目标** —— 每个方法生成 Normal / Boundary / Exception / Path 四类目标，保证覆盖多样
- **多 LLM 提供方** —— 支持 OpenAI（GPT-4o-mini）、Anthropic（Claude），或通过 `ANTHROPIC_BASE_URL` 接入任何 Anthropic 兼容端点（如 DeepSeek）
- **编译自愈** —— 生成的测试编译不过时，把诊断信息回灌给 LLM 自动修复（最多 3 轮）
- **覆盖率引导补测**（可选）—— 跑 JaCoCo，找出未覆盖的分支，定向补生成测试
- **测试质量度量** —— mutation score（PiTest）、断言密度、空测试类检测
- **可续跑** —— 中断的运行从 JSONL checkpoint 恢复，不必重新调用 LLM
- **人类可读的报告** —— 每次运行都写一份 Markdown 报告
- **常开运行日志** —— 每次运行都写 `.testgen-agent/run.log`，包含控制台从不显示的诊断（javac 报错、LLM 重试、classpath 解析）
- **结构化输出** —— Markdown、JSON、CSV 和控制台报告
- **Claude Code skill** —— 在 Claude Code 里以 `/generate-tests` 使用

## 端到端验证

流水线在 `examples/demo-project` 上执行过。这是一个小型 Maven Java 8 库，含 4 个类：`Calculator`、`TextUtil`、`BankAccount`、`PasswordValidator` —— 覆盖算术、字符串处理、有状态逻辑、异常分支和私有方法。运行使用 `deepseek-v4-flash`，通过 DeepSeek 的 Anthropic 兼容端点。

| 指标 | 结果 |
|--------|--------|
| 发现的源文件 | 4 |
| 提取的方法 | 22 |
| 目标方法 | 20 |
| 生成的测试文件 | 40 |
| 编译通过率 | 40 / 40 (100%) |
| Maven surefire 执行的测试 | 38 |
| 运行通过率 | 36 / 38 (94.7%) |
| **Mutation score（PiTest）** | **60–67 / 80 (75–84%)** |
| 断言密度 | 2.75–2.79 / 每个 `@Test` 方法 |
| 空测试类 | 0–2 |

mutation score 才是真正重要的数字：**能抓住 75–84% 注入的故障** —— 与 ICST 2026 复现研究中人工撰写测试的基线 83.98% 相当。

> 这些数字给的是**区间而不是单一数值**，因为每次运行都会从头重新生成测试，而 LLM 不会两次给出相同输出。本项目上两次实测分别是 83.8% (67/80) 和 75.0% (60/80)。把某一次的数字当作**唯一**结果来引用，恰恰是这个工具存在的意义所要反对的那种过度宣称。

按类拆分（取自 83.8% 那次运行）：

| 类 | Mutation score |
|-------|----------------|
| `com.demo.TextUtil` | 100.0% (20/20) |
| `com.demo.PasswordValidator` | 79.2% (19/24) |
| `com.demo.Calculator` | 78.9% (15/19) |
| `com.demo.BankAccount` | 76.5% (13/17) |

**如实说明的注意事项** —— 这些现在大多是*被度量出来的*，而不只是嘴上承认，而且会逐次运行变化：

- **40 个生成文件中有 0–2 个是空测试类**（能编译，但没有任何 `@Test` 方法）。编译检查抓不到这个；`empty_test_classes` 指标能，agent 现在会报告出来。
- **38 个执行过的测试中有 2 个失败**，原因是 LLM 误解了类不变量（`BankAccount` 的构造函数禁止负余额，因此"透支"状态通过公开 API 不可达 —— 生成的 `isOverdrawn` 测试却硬去构造了一个）。PiTest 要求测试全绿，所以这两个会被自动排除出 mutation 分析，并在报告里列出。
- **80 个 mutant 中有 5–12 个从未被任何测试执行到**（`NO_COVERAGE`）—— 这是覆盖缺口，不是断言缺口，报告会单独拆出来。
- demo 运行都带了 `--no-coverage`，所以覆盖率引导补测（Phase B）**没有被执行**；它已实现，并在底层的 Defects4J 实验中跑过。

运行产物（report.json / report.csv / surefire 结果 / 生成的测试）都在仓库里可供检查。复现步骤见 [demo README](examples/demo-project/README.md)。

## 快速开始

### 安装

```bash
pip install javalang openai anthropic pyyaml
```

### 配置 API Key

```bash
# OpenAI（默认）
export OPENAI_API_KEY="sk-..."

# 或 Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# 或任何 Anthropic 兼容端点（如 DeepSeek）
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="sk-..."
```

agent 会读取 `ANTHROPIC_BASE_URL`，并在 `ANTHROPIC_API_KEY` 未设置时回退到 `ANTHROPIC_AUTH_TOKEN`，因此 DeepSeek 及其他 Anthropic 兼容提供方开箱即用。

### 分析项目

先看看 agent 会针对哪些方法，不生成任何测试：

```bash
testgen-agent analyze ./my-java-project
```

### 生成测试

跑完整流水线：发现 → 提取 → 生成 → 修复 → 报告：

```bash
testgen-agent generate ./my-java-project
```

测试保存到 `./my-java-project/src/test/java/`。报告写入 `./my-java-project/.testgen-agent/`（`report.md`、`report.json`、`report.csv`）。

> 报告目录**刻意放在 `target/` 之外**：覆盖阶段会执行 `mvn clean`，放在里面会把报告删掉 —— 连带续跑用的 checkpoint 一起。

## 用法

### 命令

| 命令 | 说明 |
|---------|-------------|
| `analyze <path>` | 发现并列出方法（不生成） |
| `generate <path>` | 完整流水线：发现 → 提取 → 生成 → 修复 → 报告 |
| `repair <path>` | 重新编译已有的 `_Test_*.java` 文件并报告状态 |

### 选项

```
LLM:
  --provider {openai,anthropic}   LLM 提供方（默认 openai）
  --model MODEL                   模型名（默认 gpt-4o-mini）
  --api-key KEY                   API key（默认读环境变量）
  --temperature TEMP              温度（默认 0.2）

Method filtering:
  --package PACKAGE               只针对该包（可重复）
  --exclude METHOD                按名字排除方法（可重复）
  --skip-private                  跳过私有方法
  --include-constructors          把构造函数也作为目标
  --target-types [NORMAL ...]     要生成的目标类型（默认全部）

Repair:
  --max-repair N                  最大编译修复轮数（默认 3）
  --no-coverage                   跳过覆盖率引导补测
  --no-resume                     忽略 checkpoint，全部重新生成

Quality:
  --no-mutation                   跳过 PiTest mutation 分析（慢；需要 Maven）
  --pitest-version VERSION        pitest-maven 插件版本（默认 1.15.0）

Output:
  --output-dir DIR                测试输出目录（默认 src/test/java）
  --report-format {json,csv,both,md,all}
                                  报告格式（默认 all = md + json + csv）

Diagnostics:
  -v, --verbose                   同时把调试日志回显到控制台
```

## 排查一次运行

控制台是一个进度显示 —— 它告诉你*正在跑什么*，不告诉你*为什么失败*。每次运行还会写一份调试日志到 `.testgen-agent/run.log`，记录那些原本被吞掉的东西：交给修复循环的完整 javac 报错、LLM 重试及其响应、以及 classpath 最终解析成了什么。

```bash
# 那个失败的测试到底怎么了？
grep -A6 "FAILED (exit" .testgen-agent/run.log

# 控制台说：  [FAIL] BankAccount_deposit_Dbl_Test_Boundary_5.java
# 日志说：    -> FAILED (exit 1)
#             ...:3: 错误: 找不到符号
#             import com.demo.BankAccount;
#               符号:   类 BankAccount
#               位置: 程序包 com.demo

# 各阶段耗时（时间花在哪了？）
grep "since last phase" .testgen-agent/run.log

# classpath 解析结果
grep -A8 "classpath resolved" .testgen-agent/run.log
```

加 `-v` 可以把同样的内容实时输出到 stderr。日志每次运行都会被重写。

### 示例

```bash
# 快速分析一个项目
testgen-agent analyze ./my-project

# 只针对某个包生成测试
testgen-agent generate ./my-project --package org.example.service

# 使用 Anthropic Claude
testgen-agent generate ./my-project --provider anthropic --model claude-sonnet-4-20250514

# 使用 DeepSeek（Anthropic 兼容端点）
testgen-agent generate ./my-project --provider anthropic --model deepseek-v4-flash

# 跳过私有方法，只生成 normal + boundary 目标
testgen-agent generate ./my-project --skip-private --target-types normal boundary

# 只导出 CSV 报告
testgen-agent generate ./my-project --report-format csv

# 详细输出
testgen-agent generate ./my-project -v

# 复现已验证的 demo 运行（仓库自带的示例项目）
python main.py generate examples/demo-project \
  --provider anthropic --model deepseek-v4-flash --max-per-method 2 --no-coverage
cd examples/demo-project && mvn test   # 重跑需加 `clean`
```

> 不需要先跑 `mvn compile` —— agent 会在生成任何东西之前自己构建项目，否则 `javac` 看不到项目自己的类。（早先版本漏了这一步，导致任何未预先构建过的项目上所有测试都报 `cannot find symbol`。见下方修复 9。）

## 工作原理

### 流水线

```
项目目录
  │
  ▼
[1] 项目分析
  │  检测构建工具（Maven/Ant/Gradle/手工）
  │  遍历 src/main/java 找 .java 文件
  │  如果类还没构建就先构建项目 —— 否则 javac
  │  看不到项目自己的类型
  │  解析 classpath
  ▼
[2] 方法提取
  │  用 javalang 解析每个源文件
  │  提取：FQN、签名、修饰符、
  │  参数、异常、分支条件、
  │  类上下文、可用 import
  ▼
[3] 目标生成
  │  对每个方法：
  │    Normal  → 1 个目标（正常输入）
  │    Boundary → N 个目标（null、0、-1 等）
  │    Exception→ 每个声明的异常 1 个目标
  │    Path    → 每个分支 2 个目标（真/假）
  ▼
[4] LLM 生成测试
  │  用方法上下文 + 目标填充 prompt 模板
  │  调用 GPT-4o-mini 或 Claude
  │  从响应中抽取 Java 代码
  │  格式化：唯一类名、正确包名、
  │  去重 import
  ▼
[5] 编译修复（Phase A）
  │  用 javac 针对项目 classpath 编译
  │  失败 → 把报错 + 代码发给 LLM → 修 → 重试
  │  每个测试最多 3 轮
  ▼
[6] 覆盖率补测（Phase B）*
  │  带 JaCoCo 跑 mvn test
  │  找未覆盖的分支
  │  生成 [MissingBranch] 目标
  │  → 重复直到所有方法达标
  ▼
[7] 最终验证
  │  对 classpath 重新编译全部存活测试
  │  构建按方法拆分的报告
  ▼
[8] 测试质量
  │  空测试类（能编译但没有 @Test）
  │  断言密度（每个 @Test 方法的断言数）
  │  通过 PiTest 算 mutation score —— 失败的
  │  测试类会被排除并重试，因为 PiTest 要求全绿
  ▼
报告
    Markdown + JSON + CSV + 控制台摘要
```

*\*Phase B 要求目标项目已配置 Maven 和 JaCoCo*

### Prompt 模板

agent 使用两套 prompt 模板，改编自最初的作业：

- **`generate_system.txt`** / **`generate_user.txt`** —— 用于初次生成测试。定义了角色（资深 Java 测试开发者）、严格的 import 限制、JUnit 4 规则、反射规则和输出格式。
- **`repair_system.txt`** / **`repair_user.txt`** —— 用于编译修复。聚焦于解读报错、修 import、处理反射、保持测试结构不变。

从源码中提取的分支条件取代了早期方案使用的 Jimple IR，既省掉了 SootUp，又保留了 LLM 对控制流的可见性。

### 项目结构

约 3,800 行 Python，19 个模块 —— 全部在仓库根目录。

```
agent.py             566  TestGeneratorAgent —— 8 阶段编排器
repair_loop.py       413  编译修复循环 + 覆盖率补测
report_generator.py  401  Markdown / JSON / CSV / 控制台输出
java_analyzer.py     312  项目发现、构建工具检测、classpath
main.py              277  CLI 入口
quality_analyzer.py  251  空测试类、断言密度、PiTest 解析
coverage_analyzer.py 235  JaCoCo XML 解析
compiler.py          222  javac 调用 + 项目构建
target_generator.py  212  Normal / Boundary / Exception / Path / Reflection 目标
test_writer.py       186  测试格式化、命名、文件读写
method_extractor.py  166  基于 javalang 的方法提取
llm_client.py        104  统一的 OpenAI + Anthropic/DeepSeek 客户端
skill_entry.py        96  旧版 CLI 包装（见上方 skill 说明）
runlog.py             93  运行日志（.testgen-agent/run.log）
config.py             87  AgentConfig 数据类
prompt_manager.py     80  Prompt 模板加载与替换
checkpoint.py         60  JSONL 续跑支持
extractor/                可插拔的提取后端（javalang，可选 SootUp）
prompts/                  四个 prompt 模板（generate/repair × system/user）
examples/demo-project/    端到端验证用的示例（Maven、Java 8、4 个类）
references/               Skill 定义草稿
```

## 输出

### 控制台（demo 运行的真实输出）

```
───────────────────────────────────────────────────────
  Test Generation Agent — Summary
───────────────────────────────────────────────────────
  Project:        examples\demo-project
  Build tool:     maven
  Source files:   4
  Methods found:  22
  Methods targeted: 20
  Tests generated:   40
  Tests compiled:    40
  Compilation rate: 100.0%
  ---------------------------------------------------
  Test methods:     38
  Assertion density: 2.79 per test
  Empty test classes: 2 (compile, but contain no @Test)
  Mutation score:   83.8% (67/80 mutants killed)
    (5 mutants were never even reached by a test)
    (2 test class(es) excluded — they fail before mutation)
  Duration:       491.2s
───────────────────────────────────────────────────────

  Weakest classes (mutation score):
  com.demo.BankAccount                            76.5%  (13/17)
  com.demo.Calculator                             78.9%  (15/19)
  com.demo.PasswordValidator                      79.2%  (19/24)
  com.demo.TextUtil                              100.0%  (20/20)

  Per-method breakdown:
  Method                                              Gen  Cmp  Run
  ────────────────────────────────────────────────── ──── ──── ────
  com.demo.BankAccount.getBalance()                     2    2    2
  com.demo.BankAccount.deposit(double)                  2    2    2
  com.demo.Calculator.divide(int,int)                   2    2    2
  com.demo.PasswordValidator.isValid(String)            2    2    2
  com.demo.TextUtil.truncate(String,int)                2    2    2
  ... (20 methods, all compiled & runnable)
```

### Markdown 报告（`.testgen-agent/report.md`）

面向人的产物 —— 每次运行都写，可以直接提交或贴进评审。mutation score 打头：

```markdown
# TestGen Agent 报告 — demo-project

> 生成于 2026-10-09 13:40 · 耗时 491.2s · 构建工具 `maven`

## 核心指标
| 指标 | 值 |
|---|---|
| **Mutation score** | **83.8%** (67/80 mutants killed) |
| 编译通过率 | 100.0% (40/40) |
| 可运行率 | 95.0% (38/40) |
| 断言密度 | 2.79 / 测试 |
| 空测试类 | 2 |

**结论：良好 —— 与人工撰写测试的典型水平（约 80–85%）相当。**

## 最弱的类
| 类 | Mutation score | Killed |
|---|---|---|
| `com.demo.BankAccount` | 76.5% | 13/17 |
| `com.demo.Calculator` | 78.9% | 15/19 |

## 需要人工介入
**2 个测试运行时失败**（已排除出 mutation 分析，PiTest 要求测试全绿）:
- `com.demo.BankAccount_isOverdrawn_Test_Normal_8`
```

报告结尾会带上复现这次运行的确切命令。

### JSON 报告（`.testgen-agent/report.json`）

```json
{
  "project_path": "examples\\demo-project",
  "build_tool": "maven",
  "source_files_found": 4,
  "methods_found": 22,
  "methods_targeted": 20,
  "tests_generated": 40,
  "tests_compiled": 40,
  "tests_runnable": 40,
  "compilation_rate": 1.0,
  "branch_coverage": null,
  "line_coverage": null,
  "total_test_methods": 38,
  "empty_test_classes": 2,
  "empty_test_class_names": [
    "PasswordValidator_hasDigit_Str_Test_Boundary_29",
    "PasswordValidator_strength_Str_Test_Normal_30"
  ],
  "assertion_density": 2.789473684210526,
  "mutation_score": 0.8375,
  "mutations_killed": 67,
  "mutations_total": 80,
  "mutations_no_coverage": 5,
  "mutations_excluded_tests": [
    "com.demo.BankAccount_isOverdrawn_Test_Normal_8",
    "com.demo.BankAccount_isOverdrawn_Test_Path_9"
  ],
  "mutation_by_class": [
    { "name": "com.demo.TextUtil", "killed": 20, "total": 20, "score": 1.0 }
  ],
  "method_reports": [
    {
      "fqn": "com.demo.BankAccount.getBalance()",
      "signature": "double getBalance()",
      "modifiers": "public",
      "tests_generated": 2,
      "tests_compiled": 2,
      "tests_runnable": 2
    }
  ]
}
```

> `branch_coverage` / `line_coverage` 只在覆盖阶段（Phase B）运行时才有值（即不带 `--no-coverage`）。mutation 分析被跳过或不可用时，`mutation_score` 为 `null`。

### CSV 报告（`.testgen-agent/report.csv`）

列为：`Project`、`FQN`、`Signature`、`SourceCode`、`BranchConditions`、`ClassContext`、`AllowedImports`、`ThrowsExceptions`、`Modifiers`、`GenerationTarget`、`GeneratedCode`、`CodeAfterFormatting`、`SavedPath`、`Runnable`

## Claude Code Skill

可用的 skill 定义在 [`references/skill-draft-SKILL.md`](references/skill-draft-SKILL.md)。把它复制到位，并填入本仓库的绝对路径：

```bash
mkdir -p .claude/skills/generate-tests
cp references/skill-draft-SKILL.md .claude/skills/generate-tests/SKILL.md
# 然后把该文件里的 <REPO> 换成本仓库的绝对路径
```

开一个新的 Claude Code 会话，然后：

```
/generate-tests examples/demo-project
```

Claude 会读取 skill、运行流水线、读取 `report.json` 并汇报 —— 包括*为什么*某些测试编译失败，而不仅仅是数字。

> **关于 `skill.yaml` 的说明。** 本仓库早期版本附带的 `skill.yaml` 里含一个 `command:` 模板和一个 `arguments:` schema，README 也让你运行 `claude add skill ./agent/skill.yaml`。这两样都不是 Claude Code skill 的工作方式：skill 就是一个带 `name`/`description` frontmatter 加上 Markdown 指令正文的 `SKILL.md` —— 没有参数模板引擎，`claude add skill` 也不是真实存在的命令。按当初的样子，那个 skill 从未加载成功。`skill.yaml` 和 `skill_entry.py` 仅作为历史遗留的 CLI 包装保留；上面的定义已取代它们。

## 环境要求

- **Java 8+**（用于编译生成的测试 —— 被测项目需以 Java 8 为目标）
- **Python 3.10+**
- **Javac** —— 需在 `PATH` 上，或设置了 `JAVA_HOME`
- **Maven**（可选）—— classpath 解析、覆盖率（Phase B）和 mutation 分析（Phase 8）需要。mutation 分析还额外需要 **JDK 11+** 才能运行 PiTest。
- **API Key** —— OpenAI（`OPENAI_API_KEY`）或 Anthropic（`ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`）

在 Windows 上，`javac` 的定位要求 `JAVA_HOME` 指向 JDK（不是 JRE），且 agent 会自动通过 `cmd /c` 调用 `mvn.cmd`。

## 已知边界

- 生成的测试是 **JUnit 4**、兼容 Java 8 —— 不支持 JUnit 5、不支持 lambda、不使用 Java 8 以上的 API
- **不支持 mocking。** prompt 里禁止了 Mockito，因此有依赖注入的类（service、repository）通常生成不出可运行的测试。这是面对真实项目时最大的缺口。
- 生成的测试文件命名规则是 `ClassName_method_ParamType_Test_Type_N`。Maven 项目必须配置 surefire 的 `<includes>`（例如 `**/*_Test_*.java`）才会执行它们 —— 见 `examples/demo-project/pom.xml`。
- 分支条件是从**源码**提取的，而不是 Jimple IR（可能漏掉编译器生成的分支）
- Phase B（覆盖率补测）要求目标项目已配置 **Maven + JaCoCo**
- mutation 分析（Phase 8）需要 **Maven** 和 **JDK 11+** 才能运行 PiTest —— 它会按需解析 `pitest-maven`，版本可用 `--pitest-version` 固定。PiTest 还要求测试全绿才肯运行；失败的测试类会被自动排除并在报告中列出。
- 编译通过但是空类的测试会被报告出来，但**不会**被自动重新生成
- 含数百个方法的大型项目可能耗时较久、消耗较多 API token（目前是单线程）

## 已修复的真实问题

以下 bug 都是在 `examples/demo-project` 上实际运行流水线时发现并修复的：

1. **Windows 下 Maven 定位** —— Windows 上 `mvn` 实际是 `mvn.cmd`，subprocess 找不到它，classpath 静默解析为空。用 `shutil.which` + `cmd /c` 修复。
2. **缺少 test 作用域依赖** —— `mvn dependency:build-classpath` 默认不含 test 作用域，导致 JUnit 从不在编译 classpath 上。通过传 `-Dmdep.includeScope=test` 修复。
3. **Anthropic `ThinkingBlock` 处理** —— DeepSeek 会在文本块之前返回思考块；客户端在 `content[0].text` 上崩溃。改为只拼接 `type == "text"` 的块。
4. **`--max-per-method` 被忽略** —— `target_generator.py` 硬编码了 `targets[:10]`。现在会遵守配置的上限。
5. **Surefire 命名不匹配** —— 生成的测试文件不匹配 surefire 默认的 `*Test.java` 包含模式，导致 `mvn test` 跑了 0 个测试。已在 demo 的 `pom.xml` 中说明。
6. **checkpoint 和报告曾放在 `target/` 里** —— 覆盖阶段会执行 `mvn clean`，在运行途中把续跑 checkpoint 和所有报告删掉。已移到项目根的 `.testgen-agent/`，并支持自动迁移旧位置的 checkpoint。
7. **PiTest 要求测试全绿** —— 只要有测试失败，它就报 "did not pass without mutation" 中止，因此单个失败的生成测试就能卡死整个 mutation 阶段。现在 agent 会从 PiTest 输出里解析出问题测试类，排除后重试 —— 并在报告中记录这些排除项。
8. **只看编译的汇报是自我否定的** —— 头号指标曾是"100% 编译率"，但空测试类同样能编译通过。因此新增了 Phase 8：mutation score、断言密度和空类检测。
9. **流水线从不构建项目** —— `resolve_classpath()` 只在 `target/classes` 已存在时才把它加进 classpath，因此在未预先构建过的项目上，每个生成的测试都报 `cannot find symbol`。一次干净副本上的运行只有 45% 编译率（18/40），耗时还长了 7 倍，因为修复循环为每个测试白烧了 3 次 LLM 调用。这个问题一直被掩盖着，因为这些说明曾让你先跑 `mvn -q compile`。现在 `JavaCompiler.ensure_project_built()` 会在生成前先构建。
10. **`main.py repair` 每次调用都崩** —— 它用了 `JavaProjectAnalyzer` 却没导入，而且打印了对勾/叉号，在 GBK 控制台上会抛 `UnicodeEncodeError`。它在 Windows 上从未工作过。
11. **诊断信息不可见** —— javac 报错被交给修复循环后从不打印，所以一个失败的测试只显示 `[FAIL] <文件>`。现在每次运行都会写 `.testgen-agent/run.log`，包含完整 javac 报错、LLM 重试和 classpath 解析。正是这份日志暴露了随之一起修掉的 classpath 重复和命令行膨胀问题。

## 许可

MIT
