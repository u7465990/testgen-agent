---
name: generate-tests
description: 为 Java 项目自动生成 JUnit 4 单元测试：发现方法、生成测试目标、调 LLM 写测试、编译修复、出报告。当用户提到「生成测试」「写单元测试」「JUnit」「测试覆盖率」「给这个项目加测试」时使用。
---

# TestGen Agent

把 `testgen_demo` 流水线封装成 Claude Code skill。

> 使用前请把下面的 `<REPO>` 替换成 `testgen_demo` 的实际绝对路径（如 `D:/anu/testgen_demo`）。

## 前置检查（不满足就停下告诉用户要设什么，不要硬跑）

1. `javac -version` 能跑，且 `JAVA_HOME` 指向 **JDK 不是 JRE**
2. 有 API key：
   - Anthropic / DeepSeek：`ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`
   - 或 `ANTHROPIC_API_KEY`
   - 或 OpenAI：`OPENAI_API_KEY`

## 执行

### 第一步：analyze（不烧 token，秒出）

```bash
python <REPO>/main.py analyze <project-path>
```

把发现的方法列表给用户看，**等确认**再往下走。如果方法数量很大（>100），提醒用户可以用 `--package` 收窄范围。

### 第二步：generate（慢、烧钱，确认后才跑）

```bash
python <REPO>/main.py generate <project-path> \
  --provider anthropic --model deepseek-v4-flash \
  --max-per-method 2
```

长任务（几分钟到几十分钟）。跑之前告诉用户预计耗时。

## 读取结果

跑完读 `target/testgen-agent/report.json`，重点看：

- `tests_generated` / `tests_compiled` / `tests_runnable` —— 编译率、可运行率
- `compilation_rate`
- `method_reports` 里哪些方法 **0 编译成功**

## 呈现给用户

1. **一句话总结**（生成 N 个，编译率 X%，可运行 Y%）
2. **编译失败的方法单独列出并分析原因** —— 是缺依赖？私有方法没用反射？还是 LLM 幻觉了不存在的类？
3. **主动提出下一步**：比如「有 3 个方法编译失败，看起来是缺 Mockito 依赖，要不要我看看」

不要只复述数字。CC 的价值就在于能对结果做**后续动作**。

## 陷阱（避免踩）

- 用了 `--no-coverage` 时**没有覆盖率数字**，不要编
- 生成的测试命名是 `ClassName_method_ParamType_Test_Type_N`，Maven 项目必须配 surefire `<includes>**/*_Test_*.java</includes>` 才会被执行
- 可能生成**空测试类**（编译通过但没有 `@Test` 方法）—— 编译率 100% 不代表测试有效
- Windows 下 `mvn` 是 `mvn.cmd`，脚本内部会走 `cmd /c`，但手动跑命令时要注意
- 大项目耗时长、烧 token，先用 `--package` / `--max-per-method` 探路

## 已知局限（用户问起时如实说明）

- 只支持 **JUnit 4 + Java 8**，不支持 JUnit 5 / lambda
- **不支持 mocking**（prompt 里禁了 Mockito），有依赖注入的类基本生成不出可运行测试
- 覆盖率补测（Phase B）需要目标项目配好 Maven + JaCoCo
- 没有 mutation testing，无法证明测试的**断言**有效
