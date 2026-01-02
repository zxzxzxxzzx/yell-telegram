# 📊 Yell (for Telegram)

## 🔥 Description
A lightweight Telegram stats bot that tracks group messages and generates visual statistics. Built with Python and SQLite for efficient data persistence using long polling.

In group chats, it's difficult to see engagement trends without proper analytics. This bot provides transparent message tracking with interactive charts, helping group admins understand activity patterns and identify top contributors.

## 🔨 Backend
The bot uses SQLite with WAL (Write-Ahead Logging) mode for optimal performance. Key optimizations include:

- **Connection Pooling** - Single persistent database connection
- **Message Batching** - Queue-based inserts flushed every 1 second
- **User Caching** - Skip redundant user inserts
- **Async Offloading** - Database operations run in executor threads

## ✨ Features
- **Message Tracking** - Logs all group messages automatically
- **Statistics** - View message counts (1d/7d/all-time) and top chatter
- **Interactive Graphs** - Line charts with period selection (7d / 30d / All Time)
- **Dual Prefix** - Commands work with both `/` and `,` prefixes
- **SQLite Storage** - Lightweight, no external database required

## 📂 Project Structure
```text
telegram-stats-bot/
├── bot.py              # Main bot application
├── database.py         # SQLite database functions
├── charts.py           # Matplotlib chart generation
└── data.db             # SQLite database (auto-generated)
```

## ⚙️ Commands
| Command | Description |
|---------|-------------|
| `/help` or `,help` | Show available commands |
| `/stats` or `,stats` | View message statistics with Graph button |
| `/stats graph` or `,stats graph` | Show message trend chart directly |

## ⭐ Credits
https://matplotlib.org/
https://docs.python-telegram-bot.org/en/stable/

https://replit.com/  
https://code.visualstudio.com/  

Debugging assisted by https://replit.com/ai & https://chatgpt.com/ (_minor usage_)  
Final release in https://github.com/  

This project was developed by Souritra Samanta  
souritrasamanta@gmail.com  
Commonwealth Secondary School
