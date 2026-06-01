import os
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage

# Инициализация бота
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не задана!")

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ID чата модераторов
MODERATOR_CHAT_ID = os.getenv("MODERATOR_CHAT_ID")

# Защита от флуда в памяти контейнера
user_cooldowns = {}
COOLDOWN_DURATION = timedelta(minutes=5)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот для фиксации рекордов ударов.\n"
        "Отправь мне видео своего удара, и модераторы проверят его результаты."
    )

@dp.message()
async def handle_video(message: types.Message):
    # Проверяем, что пришло именно видео
    if not message.video:
        await message.answer("Пожалуйста, отправь именно видеофайл.")
        return

    user_id = message.from_user.id
    now = datetime.now()

    # Защита от спама видеороликами
    if user_id in user_cooldowns:
        time_passed = now - user_cooldowns[user_id]
        if time_passed < COOLDOWN_DURATION:
            remaining_time = COOLDOWN_DURATION - time_passed
            minutes_left = int(remaining_time.total_seconds() // 60)
            seconds_left = int(remaining_time.total_seconds() % 60)
            await message.answer(
                f"Вы слишком часто отправляете видео. "
                f"Подождите еще {minutes_left} мин. {seconds_left} сек."
            )
            return

    # Фиксируем время отправки
    user_cooldowns[user_id] = now

    if not MODERATOR_CHAT_ID:
        await message.answer("Ошибка настройки бота: не задан чат модерации. Обратитесь к администратору.")
        return

    # Пересылаем видео в чат модераторов
    try:
        await bot.send_video(
            chat_id=MODERATOR_CHAT_ID,
            video=message.video.file_id,
            caption=f"Новое видео на модерацию!\nОтправитель: @{message.from_user.username or 'ID ' + str(user_id)}\nID файла: <code>{message.video.file_id}</code>"
        )
        await message.answer("Ваше видео успешно отправлено модераторам. Ожидайте проверки рекорда!")
    except Exception as e:
        await message.answer("Произошла ошибка при отправке видео. Попробуйте позже.")
        print(f"Ошибка отправки модераторам: {e}")

async def main():
    print("Бот успешно запущен и готов к работе на Northflank!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())