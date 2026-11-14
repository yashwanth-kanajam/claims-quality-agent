# claims-quality-agent
#
# Synthetic data only.
#
# NOT BUILT OR RUN: Docker was not available where this file was written;
# treat it as untested.
#
# Usage:
#   docker build -t claims-quality-agent .
#   docker run --rm -i -v "$PWD/data:/data:ro" claims-quality-agent
#
# Evaluation:
#   docker run --rm claims-quality-agent python -m claims_agent.evaluate --out /tmp/results

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY vendor/ vendor/
COPY pyproject.toml README.md ./
COPY src/ src/

# Vendored wheel first (pulls duckdb==1.4.3 from PyPI), then the package itself.
RUN pip install --no-cache-dir vendor/healthcare_claims_quality-0.3.0-py3-none-any.whl \
    && pip install --no-cache-dir .

# Non-root user. Installed packages live in system site-packages (readable by all).
RUN useradd --create-home --uid 10001 appuser \
    && mkdir /data \
    && chown appuser /data

USER appuser

ENV CLAIMS_DATA_DIR=/data

# Dataset is expected to be mounted read-only at /data.
VOLUME ["/data"]

CMD ["python", "-m", "claims_agent.server"]
