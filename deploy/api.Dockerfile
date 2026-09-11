FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.31
COPY pyproject.toml uv.lock* ./
COPY apps/api ./apps/api
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH="/app/apps/api/src"
CMD ["uvicorn", "unibiz.main:app", "--host", "0.0.0.0", "--port", "8000"]
