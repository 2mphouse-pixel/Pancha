import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, types
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- НАСТРОЙКИ ---
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5821724767
CHANNEL_ID = "@pancher_best"

if not API_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN в переменной окружения")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class WorkoutStates(StatesGroup):
    waiting_for_result = State()


@dp.message(F.text == "/start")
async def start(message: types.Message):
    await message.answer(
        "Привіт! Надішліть відео свого рекорду, і після перевірки воно з'явиться в каналі."
    )


@dp.message(F.video)
async def handle_video(message: types.Message):
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve_{message.from_user.id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_{message.from_user.id}"
                ),
            ]
        ]
    )

    username = f"@{message.from_user.username}" if message.from_user.username else "без username"

    await bot.send_video(
        chat_id=ADMIN_ID,
        video=message.video.file_id,
        caption=(
            f"Новий результат від {message.from_user.full_name}\n"
            f"ID: {message.from_user.id}\n"
            f"Username: {username}"
        ),
        reply_markup=markup
    )

    await message.answer("Відео отримано і відправлено на модерацію. Очікуй!")


@dp.callback_query(F.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Немає доступу", show_alert=True)
        return

    user_id = int(callback.data.split("_", 1)[1])

    if not callback.message or not callback.message.video:
        await callback.answer("Не вдалося знайти відео", show_alert=True)
        return

    await state.set_state(WorkoutStates.waiting_for_result)
    await state.update_data(
        target_user_id=user_id,
        video_id=callback.message.video.file_id,
        admin_message_id=callback.message.message_id
    )

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    try:
        old_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=f"{old_caption}\n\n✅ Одобрено. Очікується введення результату."
        )
    except TelegramBadRequest:
        pass

    await callback.message.answer(f"Введіть результат для користувача {user_id}:")
    await callback.answer("Одобрено")


@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Немає доступу", show_alert=True)
        return

    user_id = int(callback.data.split("_", 1)[1])

    try:
        await bot.send_message(user_id, "На жаль, твоє відео відхилено модератором.")
    except (TelegramForbiddenError, TelegramBadRequest):
        pass

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    try:
        await callback.message.edit_caption(caption="❌ Видео отклонено")
    except TelegramBadRequest:
        pass

    await callback.answer("Отклонено")


@dp.message(WorkoutStates.waiting_for_result)
async def process_result(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    if not message.text:
        await message.answer("Введи результат текстом.")
        return

    raw_val = message.text.strip().replace(",", ".")

    try:
        float(raw_val)
    except ValueError:
        await message.answer("Результат має бути числом. Наприклад: 12 або 12.5")
        return

    data = await state.get_data()
    video_id = data.get("video_id")
    user_id = data.get("target_user_id")

    if not video_id or not user_id:
        await message.answer("Дані загубилися. Спробуй схвалити відео ще раз.")
        await state.clear()
        return

    text = f"Новий результат: {raw_val}"

    try:
        await bot.send_video(
            chat_id=CHANNEL_ID,
            video=video_id,
            caption=text
        )
    except Exception as e:
        await message.answer(f"Помилка при публікації в канал: {e}")
        return

    try:
        await bot.send_message(
            user_id,
            f"Вітаємо! Твоє відео опубліковано з результатом {raw_val}!"
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        pass

    await message.answer("Опубліковано!")
    await state.clear()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
