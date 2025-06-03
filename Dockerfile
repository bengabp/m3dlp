# base image
FROM python:3.11-alpine

LABEL authors="bengabp"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=mwader/static-ffmpeg:7.0.1 /ffmpeg /usr/local/bin/
COPY --from=mwader/static-ffmpeg:7.0.1 /ffprobe /usr/local/bin/
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY . .

RUN uv sync --frozen

CMD ["python3", "-m", "m3dlp.main"]
