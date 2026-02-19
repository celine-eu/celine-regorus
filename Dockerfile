# Dockerfile
FROM ghcr.io/rust-lang/rust:nightly AS rust-base

# Use the manylinux2014 image as the actual build base
FROM quay.io/pypa/manylinux2014_x86_64

# Install Rust inside manylinux
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --default-toolchain 1.83.0 --profile minimal
ENV PATH="/root/.cargo/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9.27 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync
ENV PATH="/root/.local/bin/:/app/.venv/bin:$PATH"

COPY main.py /app/main.py
COPY celine_regorus_builder/ /app/celine_regorus_builder/
COPY stubs/ /app/stubs/

RUN mkdir -p /app/dist

CMD ["python3", "/app/main.py", "--output-dir", "/app/dist"]