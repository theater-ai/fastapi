FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# entrypoint 실행 권한 부여
RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["sh", "./entrypoint.sh"]
