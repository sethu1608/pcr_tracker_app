FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install flask mysql-connector-python requests

CMD ["python", "web_app.py"]
