# demo-project

A small Java 8 Maven library used to verify **testgen-agent** end-to-end.

Four classes exercise different testing challenges:

| Class | What it covers |
|-------|----------------|
| `Calculator` | arithmetic, boundary values, divide-by-zero exception |
| `TextUtil` | null handling, truncation boundaries, loops |
| `BankAccount` | stateful logic, validation invariants, exceptions |
| `PasswordValidator` | private helper methods (reflection-based testing) |

## Reproduction

```bash
# 1. Build the project (populates target/classes)
mvn -q compile

# 2. Generate tests with testgen-agent (from the agent/ directory)
cd ../..
python main.py generate examples/demo-project \
  --provider anthropic --model deepseek-v4-flash \
  --max-per-method 2 --no-coverage

# 3. Run the generated tests (surefire is configured to pick up *Test_*.java)
cd examples/demo-project
mvn test
```

## Verified Results (2026-08)

Run on DeepSeek `deepseek-v4-flash` via its Anthropic-compatible endpoint.

| Metric | Result |
|--------|--------|
| Test files generated | 40 |
| Compile pass rate | 40/40 (100%) |
| Tests executed (surefire) | 38 |
| Runtime pass rate | 36/38 (94.7%) |

Known limitations observed:

- `BankAccount.isOverdrawn()` has **no reachable overdrawn state** through the public API (the constructor rejects negative balances), so the two generated `isOverdrawn` tests fail at setup — the LLM did not model this class invariant.
- 2 of 40 generated files were empty test classes (compiled, no `@Test`) — the compilation check cannot detect these.

These are the honest failure modes of LLM-based test generation and are documented as-is.
