# demo-project-junit5

The same four utility classes as [`../demo-project`](../demo-project), but on
**JUnit 5 / Java 17** instead of JUnit 4 / Java 8.

It exists to verify one thing: that testgen-agent **follows the project it is
pointed at** rather than imposing a framework. Same agent, two projects:

| Project | Detected as | Generated tests use |
|---------|-------------|---------------------|
| `../demo-project` | Java 8 / JUnit 4 | `org.junit.Test`, `org.junit.Assert` |
| `demo-project-junit5` | Java 17 / JUnit 5 | `org.junit.jupiter.api.Test`, `org.junit.jupiter.api.Assertions` |

Detection is automatic (`--junit auto` / `--java auto`, the defaults). It reads
the compiler level from `pom.xml` and the framework from the resolved test
classpath — see `target_profile.py`.

## Reproduction

```bash
# From the repo root
python main.py analyze examples/demo-project-junit5   # shows the detected target
python main.py generate examples/demo-project-junit5 \
  --provider anthropic --model deepseek-v4-flash --max-per-method 2 --no-coverage
cd examples/demo-project-junit5 && mvn clean test
```

## Measured results (2026-10)

One run on DeepSeek `deepseek-v4-flash`. **A single run, not a guarantee** — the
LLM does not repeat itself, so treat these as a sample, not a benchmark.

| Metric | Result |
|--------|--------|
| Detected target | Java 17 / JUnit 5 |
| Test files generated | 40 |
| Compile pass rate | 40 / 40 (100%) |
| Tests executed (surefire) | 43 |
| **Mutation score (PiTest)** | **66 / 80 (82.5%)** |
| Assertion density | 2.30 per `@Test` method |
| Empty test classes | 1 |

Sample generated exception assertion:

```java
Assertions.assertThrows(IllegalArgumentException.class, new Executable() {
    @Override
    public void execute() throws Throwable {
        account.withdraw(0.0);
    }
});
```

## Why `pitest-junit5-plugin` is declared in this pom

PiTest cannot see JUnit 5 tests without it, and the plugin dependency **cannot
be passed on the Maven command line** — only the pom can supply it. testgen-agent
invokes PiTest as a fully-qualified plugin GAV with bare `-D` properties, so when
this dependency is missing the agent now detects that and skips mutation analysis
with an explicit message rather than letting Maven fail opaquely.

That is why the declaration lives here, in a project we own, instead of the agent
editing the pom of a project it was pointed at.

## Known limitations observed in this run

- The 2 `BankAccount.isOverdrawn` tests fail for the same reason as in the JUnit 4
  demo: the constructor rejects negative balances, so an overdrawn state is
  unreachable through the public API and the generated tests try to construct one.
  The LLM understands the signature but not the class invariant.
- 1 of 40 generated files was an empty test class (compiles, no `@Test`).
- **No generated test used `assertThrows`.** These classes declare no `throws`
  clause, and `[Exception]` targets are only generated for *declared* checked
  exceptions — so the JUnit 5 exception idiom is never requested for them, and the
  LLM falls back to `try/catch`. Generating targets for unchecked exceptions
  thrown in the method body (`throw new X(...)`) is the follow-up that would fix
  this; it changes what targets get generated, so it was left out of the
  framework-version change deliberately.
