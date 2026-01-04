import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application, ContextTypes, MessageHandler, CallbackQueryHandler, filters, TypeHandler
)
import re
from telegram.constants import ParseMode
from database import (
    init_database, log_user, log_command, log_message,
    get_daily_stats, get_message_counts, get_top_chatter, start_flush_loop
)
from charts import generate_stats_chart

logging.basicConfig(
    format='[+] %(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

PERIOD_MAP = {
    'graph_7d': (7, '7 days'),
    'graph_30d': (30, '30 days'),
    'graph_all': (None, 'All Time')
}

def get_stats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Graph", callback_data="show_graph")]])

def get_graph_keyboard(selected: str = 'graph_7d') -> InlineKeyboardMarkup:
    buttons = []
    for key, (_, label) in PERIOD_MAP.items():
        short_label = '7d' if key == 'graph_7d' else ('30d' if key == 'graph_30d' else 'All Time')
        if key == selected:
            short_label = f"• {short_label} •"
        buttons.append(InlineKeyboardButton(short_label, callback_data=key))
    return InlineKeyboardMarkup([buttons])

def parse_command(text: str) -> tuple:
    if not text:
        return None, []
    match = re.match(r'^[/,](\w+)(?:\s+(.*))?$', text)
    if match:
        cmd = match.group(1).lower()
        args = match.group(2).split() if match.group(2) else []
        return cmd, args
    return None, []

async def log_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.text:
        logger.info(f"RAW UPDATE: chat={update.effective_chat.id if update.effective_chat else 'N/A'} text='{update.message.text}'")
    elif update.message:
        logger.info(f"RAW UPDATE: non-text message type")

async def command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    logger.info(f"command_handler received: '{text}'")
    
    if not text.startswith('/') and not text.startswith(','):
        logger.info(f"Text does not start with / or ,: '{text[:10]}'")
        return
    
    cmd, args = parse_command(text)
    logger.info(f"Parsed command: cmd='{cmd}', args={args}")
    
    if not cmd:
        return
    
    user = update.effective_user
    log_user(user.id, user.username, user.first_name, user.last_name)
    
    if cmd == 'help':
        log_command(user.id, "help")
        help_text = (
            "<b>Commands:</b>\n"
            "<code>/stats</code> or <code>,stats</code> - View message statistics\n"
            "<code>/stats graph</code> or <code>,stats graph</code> - View message trend graph"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    elif cmd == 'stats':
        log_command(user.id, "stats")
        await handle_stats(update, args)

async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.effective_user and update.effective_chat:
        user = update.effective_user
        chat = update.effective_chat
        
        if chat.type in ['group', 'supergroup']:
            log_user(user.id, user.username, user.first_name, user.last_name)
            log_message(user.id, chat.id)

async def handle_stats(update: Update, args: list) -> None:
    chat = update.effective_chat
    
    if args and args[0].lower() == 'graph':
        await send_graph(update.message, chat.id, 'graph_7d')
        return
    
    count_1d, count_7d, count_all = get_message_counts(chat.id)
    top_user_id, top_username, top_count = get_top_chatter(chat.id)
    
    if top_user_id and top_username:
        top_chatter = f"<a href='tg://user?id={top_user_id}'>@{top_username}</a> [{top_count}]"
    elif top_user_id:
        top_chatter = f"<a href='tg://user?id={top_user_id}'>User</a> [{top_count}]"
    else:
        top_chatter = "No data"
    
    stats_text = (
        f"<b>Messages (1d):</b> {count_1d}\n"
        f"<b>Messages (7d):</b> {count_7d}\n"
        f"<b>Messages (all-time):</b> {count_all}\n"
        f"<b>Top Chatter:</b> {top_chatter}"
    )
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_stats_keyboard()
    )

async def send_graph(message, chat_id: int, period_key: str, edit: bool = False):
    days, period_label = PERIOD_MAP[period_key]
    daily_stats = get_daily_stats(chat_id, days)
    
    chart_buffer = generate_stats_chart(
        daily_stats=daily_stats,
        period_label=period_label
    )
    
    if edit:
        await message.edit_media(
            media=InputMediaPhoto(media=chart_buffer),
            reply_markup=get_graph_keyboard(period_key)
        )
    else:
        await message.reply_photo(
            photo=chart_buffer,
            reply_markup=get_graph_keyboard(period_key)
        )

async def graph_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    chat = update.effective_chat
    
    if callback_data == "show_graph":
        daily_stats = get_daily_stats(chat.id, 7)
        chart_buffer = generate_stats_chart(daily_stats=daily_stats, period_label="7 days")
        
        await query.message.reply_photo(
            photo=chart_buffer,
            reply_markup=get_graph_keyboard('graph_7d')
        )
        return
    
    if callback_data in PERIOD_MAP:
        try:
            await send_graph(query.message, chat.id, callback_data, edit=True)
        except Exception as e:
            logger.error(f"Error updating graph: {e}")

def main():
    init_database()
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    application = Application.builder().token(token).build()
    application.add_handler(TypeHandler(Update, log_all_updates), group=-1)
    application.add_handler(MessageHandler(
        filters.TEXT,
        command_handler
    ))
    
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & ~filters.StatusUpdate.ALL,
        track_message
    ), group=1)
    
    application.add_handler(CallbackQueryHandler(graph_callback))
    
    async def post_init(application):
        await start_flush_loop()
    
    application.post_init = post_init
    
    logger.info("Starting...")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
