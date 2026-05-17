FROM python:3.11-slim

LABEL maintainer="MyClover.Tech <support@myclover.tech>"
LABEL description="CloverMarket — On-device app marketplace for mycloverOS"

# Install system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl docker.io && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
RUN pip install --no-cache-dir pyyaml

# Copy server code
WORKDIR /app
COPY server/ /app/

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

CMD ["python3", "app.py"]
