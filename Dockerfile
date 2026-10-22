FROM python:3.12-slim

ARG APP_VERSION=0.0.0
ARG VCS_REF=unknown
ARG SOURCE=unknown
ARG BUILD_DATE=unknown

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py VERSION ./

LABEL org.opencontainers.image.title="student-ml-api" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="${SOURCE}" \
      org.opencontainers.image.created="${BUILD_DATE}"

EXPOSE 5000

CMD ["python", "app.py"]
