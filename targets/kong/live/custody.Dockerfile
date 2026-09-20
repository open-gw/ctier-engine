FROM python:3.12-slim
WORKDIR /opt/ctier
COPY engine/ /opt/ctier/
RUN pip install --no-cache-dir ".[serve]" \
    && mkdir -p /data /var/ctier/ledger \
    && chmod 777 /var/ctier/ledger
ENV CTIER_SQLITE=/data/custody.sqlite
ENV CTIER_LEDGER_FALLBACK=/var/ctier/ledger/attempts.jsonl
EXPOSE 8080
CMD ["uvicorn", "ctier.custody.app:app", "--host", "0.0.0.0", "--port", "8080"]
