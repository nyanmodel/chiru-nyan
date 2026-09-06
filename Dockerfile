FROM python:3.11-slim
WORKDIR /bot
ENV PYTHONUNBUFFERED=1
COPY requirements.txt /bot/
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py awake.py /bot/
CMD ["python", "bot.py"]
