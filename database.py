import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Tuple

logger = logging.getLogger(__name__)

DB_FILE = "data.db"

def init_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS command_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            command TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_chat_timestamp ON messages(chat_id, timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_chat_user ON messages(chat_id, user_id)')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def log_user(user_id: int, username: str, first_name: str, last_name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()

def log_command(user_id: int, command: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO command_logs (user_id, command)
        VALUES (?, ?)
    ''', (user_id, command))
    conn.commit()
    conn.close()

def log_message(user_id: int, chat_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (user_id, chat_id)
        VALUES (?, ?)
    ''', (user_id, chat_id))
    conn.commit()
    conn.close()

def get_daily_stats(chat_id: int, days: int = None) -> List[Tuple[str, int, int]]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if days:
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT DATE(timestamp) as date,
                   COUNT(*) as message_count,
                   COUNT(DISTINCT user_id) as contributor_count
            FROM messages
            WHERE chat_id = ? AND DATE(timestamp) >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        ''', (chat_id, start_date))
    else:
        cursor.execute('''
            SELECT DATE(timestamp) as date,
                   COUNT(*) as message_count,
                   COUNT(DISTINCT user_id) as contributor_count
            FROM messages
            WHERE chat_id = ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        ''', (chat_id,))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_total_stats(chat_id: int, days: int = None) -> Tuple[int, int]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if days:
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) as total_messages,
                   COUNT(DISTINCT user_id) as total_contributors
            FROM messages
            WHERE chat_id = ? AND DATE(timestamp) >= ?
        ''', (chat_id, start_date))
    else:
        cursor.execute('''
            SELECT COUNT(*) as total_messages,
                   COUNT(DISTINCT user_id) as total_contributors
            FROM messages
            WHERE chat_id = ?
        ''', (chat_id,))
    
    result = cursor.fetchone()
    conn.close()
    return result if result else (0, 0)

def get_message_counts(chat_id: int) -> Tuple[int, int, int]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    now = datetime.now()
    day_ago = (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    week_ago = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('SELECT COUNT(*) FROM messages WHERE chat_id = ? AND timestamp >= ?', (chat_id, day_ago))
    count_1d = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM messages WHERE chat_id = ? AND timestamp >= ?', (chat_id, week_ago))
    count_7d = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM messages WHERE chat_id = ?', (chat_id,))
    count_all = cursor.fetchone()[0]
    
    conn.close()
    return count_1d, count_7d, count_all

def get_top_chatter(chat_id: int) -> Tuple[int, str, int]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT m.user_id, u.username, COUNT(*) as msg_count
        FROM messages m
        LEFT JOIN users u ON m.user_id = u.user_id
        WHERE m.chat_id = ?
        GROUP BY m.user_id
        ORDER BY msg_count DESC
        LIMIT 1
    ''', (chat_id,))
    
    result = cursor.fetchone()
    conn.close()
    return result if result else (None, None, 0)
