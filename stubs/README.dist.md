# celine-regorus

Python wheels for **regorus** built and published by the CELINE project.

This repository is **not** the upstream source code of regorus.
It is an automated packaging repository whose only responsibility is to:

- track upstream releases of `microsoft/regorus`
- build Python wheels
- publish them to PyPI under the name **`celine-regorus`**


---

## Usage example

See official documentation for usage

```py

from regorus import Engine

engine = Engine()

engine.add_policy_from_file("./policy.rego")
engine.set_input({ hello: "world" })

# Evaluate rule
result = engine.eval_rule("my_rule")
print(result)
```

---

## Scope and guarantees

- **Supported platforms**
  - Linux x86_64 ✅
  - macOS ✅
- **Not supported (by design)**
  - Windows ❌
  - Other architectures ❌

If you need additional platforms, please open a PR.

---
