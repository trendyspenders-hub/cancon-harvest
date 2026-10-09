FROM python:3.12-slim
RUN pip install --no-cache-dir yt-dlp
WORKDIR /app
COPY server.py artists.txt ./
EXPOSE 8080
CMD ["python3", "server.py"]
