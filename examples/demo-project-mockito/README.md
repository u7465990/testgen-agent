# demo-project-mockito

The four utility classes from [`../demo-project`](../demo-project) **plus** a
class with constructor-injected collaborators, which is the case the other two
demos cannot exercise at all: `Calculator`, `TextUtil`, `PasswordValidator` and
`BankAccount` have no dependencies, so there is nothing to mock.

It exists to verify testgen-agent's Mockito support end to end.

```
PaymentGateway        (interface)   charge(String, double) / refund(String, double)
NotificationService   (interface)   notify(String, String)
PaymentService        (class)       PaymentService(PaymentGateway, NotificationService, String)
```

`PaymentService.pay` branches on what `gateway.charge(...)` returns, so a stub
is genuinely required — not decoration.

## Reproduction

```bash
# From the repo root. Mockito is already declared in this project's pom.
python main.py generate examples/demo-project-mockito \
  --provider anthropic --model deepseek-v4-flash --max-per-method 2 --no-coverage
cd examples/demo-project-mockito && mvn clean test

# The mock tests on their own
mvn clean test -Dtest='*_Test_Mock_*'
```

## Measured results (2026-10)

One run on DeepSeek `deepseek-v4-flash`:

| Metric | Result |
|--------|--------|
| Detected target | Java 8 / JUnit 4, Mockito 4.11.0 |
| Test files generated | 49 |
| Compile pass rate | 49 / 49 (100%) |
| Tests executed (surefire) | 49 |
| **Mutation score (PiTest)** | **77 / 95 (81.1%)** |
| `[Mock]` targets / mock test files | 3 / 3 |
| Mock tests passing | 3 / 3 |

Sample generated mock test — the whole point of this project:

```java
public class PaymentService_pay_Str_Dbl_Test_Mock_32 {

    @Test
    public void testPayWithMockedCollaborators() {
        com.demo.PaymentGateway gateway = Mockito.mock(com.demo.PaymentGateway.class);
        com.demo.NotificationService notifier = Mockito.mock(com.demo.NotificationService.class);
        PaymentService service = new PaymentService(gateway, notifier, "merchant-1");

        Mockito.when(gateway.charge(ArgumentMatchers.anyString(),
                                    ArgumentMatchers.anyDouble())).thenReturn(true);

        boolean result = service.pay("customer-1", 500.0);

        Assert.assertTrue(result);
        Mockito.verify(gateway).charge("customer-1", 500.0);
        Mockito.verify(notifier).notify("customer-1", "Charged 500.0");
    }
}
```

## Why the explicit `mock()` form, and not `@Mock` / `@InjectMocks`

An earlier revision of this feature instructed the annotation idiom
(`@Mock` + `@InjectMocks`, with `@RunWith(MockitoJUnitRunner.class)` on JUnit 4
or `@ExtendWith(MockitoExtension.class)` on JUnit 5). The generated tests then
dropped the runner annotation while keeping the `@Mock` fields — and that is
**not a compile error**. The fields simply stay `null` and every mock test fails
at runtime. The repair loop only recompiles, so it cannot recover from it: all
three generated mock tests errored on the first attempt.

`Mockito.mock(...)` has no annotation to forget. It needs nothing beyond
`mockito-core` — no runner, no extension, no strictness setting — and it is
identical for JUnit 4 and JUnit 5. The trade-off is verbosity, which is a much
better trade than a silent all-null test.

This is also why `MockitoJUnitRunner.Silent` / `Strictness.LENIENT` were in the
original design: strict stubs throw `UnnecessaryStubbingException` on the
over-stubbing that LLM-written tests do routinely, and a single red test stops
PiTest from running at all, costing the entire mutation phase. The explicit form
sidesteps that concern too.

## Scope limits, by design

- **Constructor and field injection only.** No `mockStatic` (that needs
  `mockito-inline`), and no stand-ins for HTTP, databases or message queues —
  those are project-level infrastructure, not something to invent per test.
- **A collaborator must resolve to project source and be an interface or
  abstract class.** A concrete project class used as a constructor parameter
  (`RetryPolicy`, `Money`) is *not* treated as mockable; a test cannot
  meaningfully stub it. The consequence is that a class whose constructor mixes
  a mockable collaborator with a concrete project type gets **no** mock target
  at all, rather than a half-mocked skeleton that cannot compile. Relaxing this
  is a deliberate follow-up, not an oversight.
- **The Mockito dependency must be in the pom.** testgen-agent is read-only by
  default; it warns and skips when Mockito is absent. `--add-mock-deps` is the
  opt-in that writes it (idempotent, with a one-time `pom.xml.testgen-backup`).
  It can only do this for Maven projects.
