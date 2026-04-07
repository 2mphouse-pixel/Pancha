import asyncio
import logging
import os # Добавили для работы с переменными окружения
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
# Рекомендую на сервере создать переменную окружения BOT_TOKEN
API_TOKEN = os.getenv('BOT_TOKEN', '8626140283:AAHLXVoserqHbLiTSchTxxgCbZ26tWbWTHs')
ADMIN_ID = 5821724767
CHANNEL_ID = "@pancher_best"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class WorkoutStates(StatesGroup):
    waiting_for_result = State()

@dp.message(F.text == "/start")
async def start(message: types.Message):
    await message.answer("Привет! Пришли видео своего рекорда, и после проверки оно появится в канале.")

@dp.message(F.video)
async def handle_video(message: types.Message):
    # Добавили ID сообщения в callback_data, чтобы точнее идентифицировать видео
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{message.from_user.id}")
        ]
    ])

    await bot.send_video(
        chat_id=ADMIN_ID,
        video=message.video.file_id,
        caption=f"Новый результат от {message.from_user.full_name} (ID: {message.from_user.id})",
        reply_markup=markup
    )
    await message.answer("Видео получено и отправлено на модерацию. Ожидай!")

@dp.callback_query(F.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    user_id = int(callback.data.split("_")[1])
    
    # Сохраняем данные, чтобы не потерять, пока вводим число
    await state.update_data(
        target_user_id=user_id,
        video_id=callback.message.video.file_id
    )

    await state.set_state(WorkoutStates.waiting_for_result)
    await callback.message.answer(f"Введите результат для пользователя {user_id} (просто число):")
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    user_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(user_id, "К сожалению, твое видео отклонено модератором.")
    except Exception:
        pass # Если пользователь заблокировал бота

    await callback.message.edit_caption(caption="❌ Видео отклонено")
    await callback.answer("Отклонено")

@dp.message(WorkoutStates.waiting_for_result)
async def process_result(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    if not message.text.replace('.', '', 1).isdigit(): # Проверка на число (в т.ч. дробное)
        await message.answer("Пожалуйста, введи только число.")
        return

    data = await state.get_data()
    video_id = data.get("video_id")
    user_id = data.get("target_user_id")

    text = f"🔥 Новый рекорд!\n\nРезультат: **{message.text}**"

    try:
        await bot.send_video(
            chat_id=CHANNEL_ID,
            video=video_id,
            caption=text,
            parse_mode="Markdown"
        )
        await bot.send_message(user_id, f"Поздравляем! Твоё видео опубликовано с результатом {message.text}!")
        await message.answer("Опубликовано!")
    except Exception as e:
        await message.answer(f"Ошибка при публикации: {e}")

    await state.clear()

async def main():
    # Удаляем старые обновления перед запуском, чтобы бот не "сходил с ума" от старых сообщений
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())