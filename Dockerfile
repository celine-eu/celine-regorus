FROM rust:1.93.0-slim

# Install Python and build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9.27 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync
ENV PATH="/root/.local/bin/:/app/.venv/bin:$PATH"


# Copy build script
COPY main.py /app/main.py
COPY celine_regorus_builder/ /app/celine_regorus_builder/
COPY stubs/ /app/stubs/

# Create dist directory
RUN mkdir -p /app/dist

CMD ["python3", "/app/main.py", "--output-dir", "/app/dist"]