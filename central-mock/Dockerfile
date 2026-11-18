FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir fastapi==0.115.6 pydantic==2.10.4 "uvicorn[standard]==0.34.0" httpx==0.28.1
COPY central.py .
EXPOSE 9000
CMD ["uvicorn", "central:app", "--host", "0.0.0.0", "--port", "9000", "--log-level", "warning"]
