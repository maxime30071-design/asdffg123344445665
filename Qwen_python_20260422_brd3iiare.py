import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message

# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8557904029:AAEvrq67zmAZPcDpTgcC4GvgjkZ6UwEbKEI"  # Вставьте токен
ADMIN_ID = 8039191347  # Вставьте ВАШ ID (число)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('support_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS connections 
                      (admin_msg_id INTEGER PRIMARY KEY, user_id INTEGER)''')
    conn.commit()
    conn.close()


def save_connection(admin_msg_id, user_id):
    conn = sqlite3.connect('support_bot.db')
    cursor = conn.cursor()
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


init_db()


# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Напишите свой вопрос.")
    try:
        await bot.send_message(ADMIN_ID, f"🟢 Новый пользователь: {message.from_user.full_name}")
    except:
        pass


@dp.message(F.chat.type == "private")
async def handle_all_private_messages(message: Message):
    """Этот обработчик ловит ВСЕ личные сообщения"""

    sender_id = message.from_user.id
    sender_name = message.from_user.full_name

    print(f"\n[🔍 DEBUG] Получено сообщение от: {sender_name} (ID: {sender_id})")
    print(f"[🔍 DEBUG] Текст: {message.text}")
    print(f"[🔍 DEBUG] Это админ? {sender_id == ADMIN_ID}")

    # 1. Если пишет АДМИН
    if sender_id == ADMIN_ID:
        print("[👮 ADMIN] Обработка сообщения от админа...")

        if message.reply_to_message:
            replied_id = message.reply_to_message.message_id
            print(f"[👮 ADMIN] Это Reply на сообщение ID: {replied_id}")

            user_id = get_user_by_admin_msg(replied_id)

            if user_id:
                print(f"[👮 ADMIN] Найден пользователь: {user_id}. Отправляю...")
                try:
                    await message.copy_to(user_id)
                    print(f"[✅ SUCCESS] Сообщение отправлено пользователю {user_id}")
                except Exception as e:
                    print(f"[❌ ERROR] Ошибка отправки: {e}")
                    await message.answer(f"Ошибка: {e}")
            else:
                print(f"[⚠️ WARN] Пользователь для сообщения {replied_id} не найден в базе.")
                await message.answer("⚠️ Не могу найти пользователя. Пусть напишет заново.")
        else:
            print("[⚠️ WARN] Админ написал без Reply. Игнорирую.")
            # Раскомментируйте, если хотите напоминание:
            # await message.answer("ℹ️ Используйте 'Ответить' (Reply) на сообщение пользователя.")

    # 2. Если пишет ПОЛЬЗОВАТЕЛЬ
    else:
        print(f"[👤 USER] Обработка сообщения от пользователя {sender_id}...")
        try:
            sent_msg = await message.forward(ADMIN_ID)
            save_connection(sent_msg.message_id, sender_id)
            print(f"[📤 FORWARD] Переслано админу. MsgID: {sent_msg.message_id}")
        except Exception as e:
            print(f"[❌ ERROR] Ошибка пересылки: {e}")


async def main():
    logger.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
