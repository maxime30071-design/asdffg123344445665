import asyncio
import logging
import os  # <--- ВАЖНО: Добавлен этот импорт
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message

# --- НАСТРОЙКИ ---
# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверка наличия токена
if not BOT_TOKEN:
    raise ValueError("Токен бота не найден! Установите переменную окружения BOT_TOKEN.")

ADMIN_ID = 8039191347  # Вставьте ВАШ ID (число)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('support_bot.db')
    cursor = conn.cursor()
    # Создаем таблицу, если её нет
    cursor.execute('''CREATE TABLE IF NOT EXISTS connections 
                      (admin_msg_id INTEGER PRIMARY KEY, user_id INTEGER)''')
    conn.commit()
    conn.close()


def save_connection(admin_msg_id, user_id):
    conn = sqlite3.connect('support_bot.db')
    cursor = conn.cursor()
    # Сохраняем связь между ID сообщения у админа и ID пользователя
    cursor.execute("INSERT OR REPLACE INTO connections (admin_msg_id, user_id) VALUES (?, ?)",
                   (admin_msg_id, user_id))
    conn.commit()
    conn.close()


def get_user_by_admin_msg(admin_msg_id):
    conn = sqlite3.connect('support_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM connections WHERE admin_msg_id = ?", (admin_msg_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


# Инициализируем БД при запуске
init_db()


# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Напишите свой вопрос, и я передам его администратору.")
    try:
        # Уведомляем админа о новом пользователе (опционально)
        await bot.send_message(ADMIN_ID, f"🟢 Новый пользователь начал диалог: {message.from_user.full_name} (ID: {message.from_user.id})")
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление админу: {e}")


@dp.message(F.chat.type == "private")
async def handle_all_private_messages(message: Message):
    """Этот обработчик ловит ВСЕ личные сообщения"""

    sender_id = message.from_user.id
    sender_name = message.from_user.full_name

    # Логирование для отладки
    logger.debug(f"Получено сообщение от: {sender_name} (ID: {sender_id})")

    # 1. Если пишет АДМИН
    if sender_id == ADMIN_ID:
        logger.info("Обработка сообщения от АДМИНА")

        # Админ должен отвечать через Reply (Ответить) на пересланное сообщение
        if message.reply_to_message:
            replied_id = message.reply_to_message.message_id
            logger.debug(f"Админ ответил на сообщение ID: {replied_id}")

            user_id = get_user_by_admin_msg(replied_id)

            if user_id:
                try:
                    # Копируем сообщение админа пользователю
                    await message.copy_to(user_id)
                    logger.info(f"Сообщение успешно отправлено пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения пользователю: {e}")
                    await message.answer(f"❌ Ошибка при отправке: {e}")
            else:
                logger.warning(f"Пользователь для сообщения {replied_id} не найден в базе.")
                await message.answer("⚠️ Не могу найти пользователя. Возможно, это старое сообщение или база данных была очищена.")
        else:
            # Если админ просто написал сообщение без Reply
            logger.warning("Админ написал сообщение без использования Reply.")
            # Можно раскомментировать следующую строку, чтобы бот напоминал админу
            # await message.answer("ℹ️ Пожалуйста, используйте функцию 'Ответить' (Reply) на сообщении пользователя.")

    # 2. Если пишет ПОЛЬЗОВАТЕЛЬ
    else:
        logger.info(f"Обработка сообщения от ПОЛЬЗОВАТЕЛЯ {sender_id}")
        
        # Игнорируем команды, если они не /start (так как /start уже обработан выше, 
        # но aiogram может передать его и сюда, если нет строгого фильтра. 
        # Однако Command фильтр обычно приоритетнее. Для надежности можно проверить текст.)
        if message.text and message.text.startswith('/'):
             return 

        try:
            # Пересылаем сообщение админу
            sent_msg = await message.forward(ADMIN_ID)
            
            # Сохраняем в базу: ID пересланного сообщения у админа <-> ID пользователя
            save_connection(sent_msg.message_id, sender_id)
            
            logger.info(f"Сообщение переслано админу. MsgID у админа: {sent_msg.message_id}")
            
            # Опционально: подтвердить пользователю, что сообщение доставлено
            # await message.answer("✅ Ваше сообщение отправлено администратору.")
            
        except Exception as e:
            logger.error(f"Ошибка пересылки сообщения админу: {e}")
            await message.answer("❌ Произошла ошибка при отправке вашего сообщения. Попробуйте позже.")


async def main():
    logger.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")
