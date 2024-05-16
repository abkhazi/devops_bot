FROM python:3.11.8 AS builder
COPY bot.py .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD [ "python", "-u", "./bot.py"]