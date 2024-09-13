import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
NAME, PHONE, BRAND, COMPLAINT, QUESTION = range(5)

# Admin chat ID and Admin user IDs
ADMIN_CHAT_ID = -4552641612
ADMIN_IDS = [6077554635]  # Впиши сюда user_id администраторов
# File to store registered users
USERS_FILE = "users.json"

def load_users():
    """Load users from a JSON file."""
    try:
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_users(users):
    """Save users to a JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)
# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.chat_id
    if 'users' not in context.bot_data:
        context.bot_data['users'] = load_users()
    context.bot_data['users'].add(user_id)
    save_users(context.bot_data['users'])

    await update.message.reply_text(
        f"Добро Пожаловать в Платформу улучшений ТРЦ Chimgan!\n"
        f"\n"
        f"Пожалуйста, введите ваше Ф.И.О."

    )
    return NAME


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(f"Ваш ID: {user_id}")


# Name handler
async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    await update.message.reply_text('Пожалуйста, введите ваш номер телефона.')
    return PHONE


# Phone handler
async def phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['phone'] = update.message.text
    await update.message.reply_text('Пожалуйста, введите название бренда.')
    return BRAND


# Brand handler
async def brand_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['brand'] = update.message.text
    await update.message.reply_text('Пожалуйста, напишите вашу жалобу или предложение.')
    return COMPLAINT


# Complaint handler
async def complaint_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['complaint'] = update.message.text
    await update.message.reply_text('Хотите задать вопрос? Напишите его или нажмите /skip если не хотите.')
    return QUESTION


# Question handler
async def question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['question'] = update.message.text
    await send_to_admin_group(update, context)
    await update.message.reply_text('Спасибо за ваш отзыв! Ваше сообщение было отправлено.')
    return ConversationHandler.END


# Skip question handler
async def skip_question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['question'] = None
    await send_to_admin_group(update, context)
    await update.message.reply_text('Спасибо за ваш отзыв! Ваше сообщение было отправлено.')
    return ConversationHandler.END


# Send collected data to the admin group
async def send_to_admin_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    message = (
        f"Новый отзыв:\n"
        f"Ф.И.О: {user_data['name']}\n"
        f"Номер телефона: {user_data['phone']}\n"
        f"Название бренда: {user_data['brand']}\n"
        f"Жалоба/Предложение: {user_data['complaint']}\n"
        f"Вопрос: {user_data.get('question', 'Не задан')}"
    )

    sent_message = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)
    context.bot_data[sent_message.message_id] = update.message.from_user.id


# Announcement handler
async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in ADMIN_IDS:
        message = update.message.text[len('/announce '):].strip()
        if not message:
            await update.message.reply_text("Сообщение не должно быть пустым.")
            return

        if 'users' in context.bot_data:
            for user_id in context.bot_data['users']:
                await context.bot.send_message(chat_id=user_id, text=message)
        else:
            await update.message.reply_text("Нет зарегистрированных пользователей.")
    else:
        await update.message.reply_text("У вас нет прав на использование этой команды.")


# Acknowledge callback
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)


# Handle group reply
async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message and update.message.reply_to_message.message_id in context.bot_data:
        user_id = context.bot_data[update.message.reply_to_message.message_id]
        reply_message = update.message.text
        await context.bot.send_message(chat_id=user_id, text=f"Ответ на ваш отзыв:\n{reply_message}")
    else:
        await update.message.reply_text("Не могу найти пользователя для ответа.")


# List users command to check registered users
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'users' in context.bot_data:
        users = "\n".join([str(user) for user in context.bot_data['users']])
        await update.message.reply_text(f"Зарегистрированные пользователи:\n{users}")
    else:
        await update.message.reply_text("Нет зарегистрированных пользователей.")


# Error handler
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("7232645470:AAF3Ac2_msgZFxvjKOCfer8qL_wyb0qbPS4").build()

    # Add handlers
    application.add_handler(CommandHandler('id', get_id))
    application.add_handler(CommandHandler('announce', announce))
    application.add_handler(CommandHandler('list_users', list_users))
    application.add_handler(CallbackQueryHandler(button))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_handler)],
            BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, brand_handler)],
            COMPLAINT: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_handler)],
            QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, question_handler),
                CommandHandler('skip', skip_question_handler)
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.COMMAND, start))
    application.add_handler(MessageHandler(filters.REPLY & filters.ChatType.GROUP, handle_group_reply))

    # Log all errors
    application.add_error_handler(error)

    # Start the Bot
    application.run_polling()


if __name__ == '__main__':
    main()