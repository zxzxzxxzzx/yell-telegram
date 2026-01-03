import sqlite3
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from collections import deque

logger = logging.getLogger(__name__)

DB_FILE = "data.db"

_connection: Optional[sqlite3.Connection] = None
_lock = threading.Lock()

_message_queue: deque = deque()
_user_cache: dict = {}
_flush_task: Optional[asyncio.Task] = None

def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DB_FILE, check_same_thread=False)
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA synchronous=NORMAL")
        _connection.execute("PRAGMA busy_timeout=5000")
        _connection.execute("PRAGMA cache_size=-8000")
    return _connection

def init_database():
    conn = get_connection()
    with _lock:
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
    logger.info("Database initialized with WAL mode")

def _sync_log_user(user_id: int, username: str, first_name: str, last_name: str):
    cache_key = user_id
    cached = _user_cache.get(cache_key)
    if cached == (username, first_name, last_name):
        return
    
    conn = get_connection()
    with _lock:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        conn.commit()
    _user_cache[cache_key] = (username, first_name, last_name)

def log_user(user_id: int, username: str, first_name: str, last_name: str):
    cache_key = user_id
    cached = _user_cache.get(cache_key)
    if cached == (username, first_name, last_name):
        return
    asyncio.get_event_loop().run_in_executor(
        None, _sync_log_user, user_id, username, first_name, last_name
    )

def _sync_log_command(user_id: int, command: str):
    conn = get_connection()
    with _lock:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO command_logs (user_id, command) VALUES (?, ?)', (user_id, command))
        conn.commit()

def log_command(user_id: int, command: str):
    asyncio.get_event_loop().run_in_executor(None, _sync_log_command, user_id, command)

def log_message(user_id: int, chat_id: int):
    _message_queue.append((user_id, chat_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

def _flush_messages():
    if not _message_queue:
        return
    
    messages = []
    while _message_queue:
        try:
            messages.append(_message_queue.popleft())
        except IndexError:
            break
    
    if not messages:
        return
    
    conn = get_connection()
    with _lock:
        cursor = conn.cursor()
        cursor.executemany(
            'INSERT INTO messages (user_id, chat_id, timestamp) VALUES (?, ?, ?)',
            messages
        )
        conn.commit()
    logger.debug(f"Flushed {len(messages)} messages to database")

async def start_flush_loop():
    global _flush_task
    async def flush_loop():
        while True:
            await asyncio.sleep(1.0)
            if _message_queue:
                await asyncio.get_event_loop().run_in_executor(None, _flush_messages)
    
    _flush_task = asyncio.create_task(flush_loop())
    logger.info("Message flush loop started")

def get_daily_stats(chat_id: int, days: int = None) -> List[Tuple[str, int, int]]:
    conn = get_connection()
    with _lock:
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
        
        return cursor.fetchall()

def get_total_stats(chat_id: int, days: int = None) -> Tuple[int, int]:
    conn = get_connection()
    with _lock:
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
        return result if result else (0, 0)

def get_message_counts(chat_id: int) -> Tuple[int, int, int]:
    conn = get_connection()
    with _lock:
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
        
        return count_1d, count_7d, count_all

def get_top_chatter(chat_id: int) -> Tuple[int, str, int]:
    conn = get_connection()
    with _lock:
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
        return result if result else (None, None, 0)
