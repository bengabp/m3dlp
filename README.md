<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=90&size=53&pause=1000&color=F7E618&center=true&vCenter=true&repeat=false&width=204&height=80&lines=m3dlp" alt="Typing SVG" />
</p>
<p align="center">
  <i>opensource yt-dlp inspired media downloader Telegram bot</i>
</p>

<p align="center">
  <a href="https://t.me/m3dlpBot">
    <img src="https://img.shields.io/badge/Chat-Telegram-2CA5E0?style=for-the-badge&logo=telegram" alt="Telegram Chat">
  </a>
</p>

# Setting up
Run a redis container locally
```bash
docker run -d --name redis -p 6379:6379 redis:latest
```
Clone this repository and install the dependencies using uv
```bash
uv sync
```

Running a worker
This project uses dramatiq to queue download tasks so as to prevent too many tasks from being processed at once
```bash
uv run dramatiq-gevent --queues=media_download m3dlp.tasks
```

Running with docker compose
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

