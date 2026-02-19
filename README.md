# celine-regorus

Python wheels for **regorus** built and published by the CELINE project.

This repository is **not** the upstream source code of regorus.
It is an automated packaging repository whose only responsibility is to:

- track upstream releases of `microsoft/regorus`
- build Python wheels
- publish them to PyPI under the name **`celine-regorus`**

---

## Scope and guarantees

- **Supported platforms**
  - Linux x86_64 ✅
- **Not supported (by design)**
  - macOS ❌
  - Windows ❌
  - Other architectures ❌

If you need additional platforms, please open a PR.

---

## Build model (important)

This project uses a **single source of truth for builds**:

➡️ **The Dockerfile**

All CI builds:
- use the Dockerfile
- run the exact same commands you can run locally
- produce the same wheel artifacts

There is intentionally **no multi-platform matrix**, no cibuildwheel, and no detached build logic.

If CI succeeds, local Docker builds will succeed too.

---

## How wheels are built

1. A scheduled or manual workflow checks upstream `microsoft/regorus` releases
2. If a new version is found:
   - the Docker image is built
   - the container runs the build
   - wheels are written to `/app/dist`
3. The resulting Linux wheel is published to PyPI

Publishing uses **PyPI Trusted Publishing** (OIDC).  
No PyPI tokens are stored in this repository.

---

## Local build (reproduce CI exactly)

Requirements:
- Docker

Build and run:

```bash
docker build -t celine-regorus-builder .
docker run --rm -v "$PWD/dist:/app/dist" celine-regorus-builder
```

The wheel will be available in:

```text
dist/
```

---

## Installation

```bash
pip install celine-regorus
```

> Note: Only Linux and MacOS wheels are provided.  
> On other platforms, installation may fail or attempt a source build.

---

## Versioning

- The published version matches the upstream `regorus` version
- No additional semantic versioning is introduced
- If upstream tags `v0.5.0`, PyPI publishes `celine-regorus==0.5.0`

---

## Why this repo exists

This repo is intended as a temporary fix waiting for official python releases, will be deprecated afterwards.

See https://github.com/microsoft/regorus/issues/168 for udpates


---

## Contributing

PRs are welcome for:
- macOS / Windows support
- additional Linux architectures
- build optimizations
- documentation improvements

Please keep the **Dockerfile as the canonical build definition**.
