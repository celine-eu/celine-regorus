# celine-regorus

Unofficial Python bindings for [Regorus](https://github.com/microsoft/regorus) - a fast, lightweight Rego interpreter written in Rust.

This repository automatically builds and publishes Python wheels from the official [microsoft/regorus](https://github.com/microsoft/regorus) releases.

## Installation

```bash
pip install celine-regorus
```

## Why this package?

The official `regorus` package may not always have up-to-date Python wheels published to PyPI. This package:

- Automatically monitors the official repository for new releases
- Builds wheels for multiple platforms (Linux, macOS, Windows) and architectures (x86_64, aarch64)
- Publishes to PyPI within hours of a new upstream release

## Usage

```python
import regorus

# Create an engine
engine = regorus.Engine()

# Load a Rego policy
engine.add_policy_from_file("policy.rego")

# Set input data
engine.set_input({"user": "alice", "action": "read"})

# Evaluate a query
result = engine.eval_query("data.authz.allow")
print(result)
```

## Supported Platforms

| Platform | Architecture | Status |
|----------|--------------|--------|
| Linux | x86_64 | ✅ |
| Linux | aarch64 | ✅ |
| macOS | x86_64 | ✅ |
| macOS | Apple Silicon | ✅ |
| Windows | x86_64 | ✅ |

## Version Tracking

This package tracks the official `microsoft/regorus` releases. The version number matches the upstream version.

| celine-regorus | regorus upstream |
|----------------|------------------|
| 0.x.y | v0.x.y |

## How it works

1. A GitHub Actions workflow runs every 6 hours
2. It checks the latest release tag from `microsoft/regorus`
3. Compares with the latest version on PyPI
4. If a new version is available, it:
   - Clones the upstream repo at the release tag
   - Builds wheels using maturin
   - Publishes to PyPI using trusted publishing

## Manual Trigger

Maintainers can manually trigger a build:

1. Go to Actions → "Build and Publish"
2. Click "Run workflow"
3. Optionally specify a tag or force a rebuild

## Development

### Local Build

```bash
# Install dependencies
pip install maturin

# Check for new versions
python scripts/build_release.py --check-only

# Build locally
python scripts/build_release.py --force

# Build a specific tag
python scripts/build_release.py --tag v0.2.0
```

### Repository Setup

1. **PyPI Trusted Publishing**: Configure trusted publishing in PyPI project settings:
   - Publisher: GitHub Actions
   - Repository: `your-username/celine-regorus`
   - Workflow: `build-publish.yml`
   - Environment: `pypi`

2. **GitHub Environment**: Create a `pypi` environment in repository settings for deployment protection.

## Monitoring Approach

The workflow uses a polling strategy:

- **Frequency**: Every 6 hours (configurable via cron)
- **Method**: Compares GitHub release tags with PyPI versions
- **Efficiency**: Only builds when a new version is detected

Alternative approaches considered:
- **Webhooks**: Would require a server to receive GitHub webhooks
- **GitHub Actions `repository_dispatch`**: Would require a webhook receiver
- **Manual monitoring**: Not automated

The polling approach is simple, requires no infrastructure, and 6-hour intervals are sufficient for a library that releases infrequently.

## License

This build automation is provided under the MIT License.

The Regorus library itself is licensed under the MIT License by Microsoft. See the [upstream repository](https://github.com/microsoft/regorus) for details.

## Disclaimer

This is an unofficial package. For official support, please refer to the [microsoft/regorus](https://github.com/microsoft/regorus) repository.