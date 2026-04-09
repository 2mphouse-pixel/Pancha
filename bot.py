import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
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
    await message.answer("Привіт! Надішліть відео свого рекорду, і після перевірки воно з'явиться в каналі.")

@dp.message(F.video)
async def handle_video(message: types.Message):
    # Кнопки для админа оставлены на русском по твоему запросу
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{message.from_user.id}")
        ]
    ])

    await bot.send_video(
        chat_id=ADMIN_ID,
        video=message.video.file_id,
        caption=f"Новий результат від {message.from_user.full_name} (ID: {message.from_user.id})",
        reply_markup=markup
    )
    await message.answer("Відео отримано і відправлено на модерацію. Очікуй!")

@dp.callback_query(F.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    user_id = int(callback.data.split("_")[1])
    
    await state.update_data(
        target_user_id=user_id,
        video_id=callback.message.video.file_id
    )

    await state.set_state(WorkoutStates.waiting_for_result)
    await callback.message.answer(f"Введіть результат для користувача {user_id}:")
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    user_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(user_id, "На жаль, твоє відео відхилено модератором.")
    except Exception:
        pass 

    await callback.message.edit_caption(caption="❌ Видео отклонено")
    await callback.answer("Отклонено")

@dp.message(WorkoutStates.waiting_for_result)
async def process_result(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    val = message.text.replace(',', '.')

    data = await state.get_data()
    video_id = data.get("video_id")
    user_id = data.get("target_user_id")

    # Текст для канала на украинском
    text = f"Новий результат: {val}"

    try:
        await bot.send_video(
            chat_id=CHANNEL_ID,
            video=video_id,
            caption=text
        )
        await bot.send_message(user_id, f"Вітаємо! Твоє відео опубліковано з результатом {val}!")
        await message.answer("Опубліковано!")
    except Exception as e:
        await message.answer(f"Помилка при публікації: {e}")

    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
