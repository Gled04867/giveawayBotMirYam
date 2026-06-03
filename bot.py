import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os

from database import init_db, check_code, add_participant, get_all_participants, get_participants_count, get_unique_users_count, load_codes_from_file, get_codes_count, get_user_codes_count

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_CHANNELS = [-1001234567890]  # заменим на реальные когда дадут доступ
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))
RESULTS_CHANNEL_ID = int(os.getenv("RESULTS_CHANNEL_ID", "0"))
WEBAPP_URL = os.getenv("WEBAPP_URL")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class GiveawayStates(StatesGroup):
    waiting_for_code = State()

async def check_subscription(user_id: int) -> bool:
    for channel_id in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status in ["left", "kicked", "banned"]:
                return False
        except Exception:
            return False
    return True

def giveaway_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎁 Участвовать в розыгрыше",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]
    ])

def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🎁 *Розыгрыш Yamaguchi!*\n\n"
        "Чтобы участвовать:\n"
        "— подпишитесь на каналы организаторов\n"
        "— зарегистрируйте свой код\n\n"
        "Нажми кнопку ниже 👇",
        parse_mode="Markdown",
        reply_markup=giveaway_keyboard()
    )

@dp.message(Command("giveaway"))
async def cmd_giveaway(message: Message):
    await message.answer(
        "🎁 *Розыгрыш Yamaguchi!*\n\n"
        "Условия участия:\n"
        "• Подписка на каналы организаторов\n"
        "• Наличие кода участника\n"
        "• Каждый код — один шанс на выигрыш\n\n"
        "Нажми кнопку чтобы участвовать 👇",
        parse_mode="Markdown",
        reply_markup=giveaway_keyboard()
    )

@dp.callback_query(F.data == "join_giveaway")
async def process_join(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    is_subscribed = True  # заменим когда будут реальные каналы

    if not is_subscribed:
        await callback.message.answer(
            "❌ Ты не подписан на каналы организаторов!\n\n"
            "Подпишись и попробуй снова."
        )
        return

    await state.set_state(GiveawayStates.waiting_for_code)
    await callback.message.answer(
        "✅ Подписка подтверждена!\n\n"
        "Введи свой код участника:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )

@dp.callback_query(F.data == "cancel")
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer("Отменено. Напиши /giveaway чтобы начать заново.")

@dp.message(GiveawayStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    full_name = message.from_user.full_name

    if not check_code(code):
        await message.answer(
            "❌ Код недействителен или уже использован.\n\n"
            "Попробуй другой код или нажми «Отмена».",
            reply_markup=cancel_keyboard()
        )
        return

    success = add_participant(user_id, username, full_name, code)

    if not success:
        await message.answer(
            "❌ Этот код уже использован.\n\n"
            "Попробуй другой код или нажми «Отмена».",
            reply_markup=cancel_keyboard()
        )
        return

    user_codes = get_user_codes_count(user_id)
    total = get_participants_count()
    await state.clear()
    await message.answer(
        f"🎉 *Ты в розыгрыше!*\n\n"
        f"Код *{code}* принят.\n"
        f"Твоих кодов в розыгрыше: *{user_codes}*\n"
        f"Всего участий: *{total}*\n\n"
        f"Хочешь добавить ещё код? Нажми /giveaway снова.\n\n"
        f"🏷 Скидка Yamaguchi: _(будет добавлена позже)_",
        parse_mode="Markdown"
    )

@dp.message(Command("results"))
async def cmd_results(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.")
        return

    participants = get_all_participants()

    if not participants:
        await message.answer("Участников пока нет.")
        return

    winner = random.choice(participants)
    user_id, username, full_name, code = winner

    result_text = (
        f"🏆 *Итоги розыгрыша Yamaguchi!*\n\n"
        f"Победитель: *{full_name}*\n"
        f"@{username}\n"
        f"Код: `{code}`\n\n"
        f"Поздравляем! 🎊\n\n"
        f"Следите за новостями в нашем канале!"
    )

    await bot.send_message(
        RESULTS_CHANNEL_ID,
        result_text,
        parse_mode="Markdown"
    )

    await message.answer(
        f"✅ Итоги опубликованы в канале!\n\n"
        f"Победитель: *{full_name}* (@{username})\n"
        f"Код: `{code}`",
        parse_mode="Markdown"
    )

@dp.message(Command("load_codes"))
async def cmd_load_codes(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.")
        return

    try:
        stats = load_codes_from_file("codes.txt")
        codes_info = get_codes_count()
        await message.answer(
            f"✅ Коды загружены!\n\n"
            f"Добавлено: *{stats['added']}*\n"
            f"Пропущено (дубли): *{stats['skipped']}*\n\n"
            f"Всего свободных кодов: *{codes_info['free']}*",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.")
        return

    codes_count = get_participants_count()
    users_count = get_unique_users_count()
    codes_info = get_codes_count()
    await message.answer(
        f"📊 *Статистика розыгрыша*\n\n"
        f"👥 Уникальных участников: *{users_count}*\n"
        f"🎟 Зарегистрировано кодов: *{codes_count}*\n"
        f"🔓 Свободных кодов: *{codes_info['free']}*\n"
        f"✅ Использованных кодов: *{codes_info['used']}*",
        parse_mode="Markdown"
    )

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())