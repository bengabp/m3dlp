# m3dlp
yt-dlp inspired media downloader bot

# Setting up
Run a redis container locally
```bash
docker run -d --name redis -p 6379:6379 redis:latest
```
Clone this repository and install the dependencies using uv
```bash
uv sync
```

# Running a worker
This project uses dramatiq to queue download tasks so as to prevent too many tasks from being processed at once
```bash
uv run dramatiq-gevent --queues=media_download m3dlp.tasks
```

# Running with docker compose
Ive added a compose file to make everything easier. 
Just add a .env file at the root directory and make sure you have your
`TELEGRAM_BOT_TOKEN` set, then fire up the bot using this command

```bash
docker compose up -d 
```
The compose file includes 
- redis
- broker
- tgbot

