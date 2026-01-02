import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, PrefixHandler
from telegram.constants import ParseMode
from database import init_database, log_user, log_command

logging.basicConfig(
    format='[+] %(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    log_user(user.id, user.username, user.first_name, user.last_name)
    log_command(user.id, "help")
    
    await update.message.reply_text(
        "<b>Hi</b>",
        parse_mode=ParseMode.HTML
    )

def main():
    init_database()
    
    token = "token"
    application = Application.builder().token(token).build()
    application.add_handler(PrefixHandler(["/", ","], "help", help_command))
    
    logger.info("[+] Starting...")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
