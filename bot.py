import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os

from database import init_db, check_code, add_participant, get_all_participants, get_participants_count, get_unique_users_count, load_codes_from_file, get_codes_count, get_user_codes_count, get_user_codes_list, remove_user_by_username, save_winner, get_winner

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_CHANNELS = [-1001510796913, -1003623085970]
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))
RESULTS_CHANNEL_ID = int(os.getenv("RESULTS_CHANNEL_ID", "0"))
PUBLISH_CHANNELS = [int(x) for x in os.getenv("PUBLISH_CHANNELS", str(RESULTS_CHANNEL_ID)).split(",") if x]
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

@dp.message(F.forward_from_chat)
async def get_chat_id(message: Message):
    await message.answer(f"ID чата: `{message.forward_from_chat.id}`", parse_mode="Markdown")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Осталось выполнить всего два простых условия:\n\n"
        "— Подпишись на Telegram-каналы организаторов\n"
        "— Введи и зарегистрируй свой код\n\n"
        "Удачи - пусть приз достанется именно тебе!\n\n"
        "Нажимая кнопку участия, я даю "
        "<a href='https://docs.google.com/document/d/1l-0TqovLM877mpf-7WQwONhPGQ4yURhw/edit'>согласие на обработку моих персональных данных</a> "
        "в соответствии с "
        "<a href='https://docs.google.com/document/d/1l6CwerdEEllCQ5oTuHzaJxqWFfAevJq2/edit'>Политикой обработки персональных данных</a> "
        "и подтверждаю, что ознакомлен(а) с условиями "
        "<a href='https://docs.google.com/document/d/1dO4V3yiXC3dc4PBJZkLKhryMXyPei6JL/edit'>оферты</a> "
        "и принимаю их.",
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=giveaway_keyboard()
    )

@dp.message(Command("publish"))
async def cmd_publish(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.")
        return

    text = (
        "<b>🔥 Розыгрыш Стейк&amp;Бургер Мираторг × Yamaguchi</b>\n\n"
        "<i>С 8 по 28 июня закажите Японский бургер в ресторанах "
        "<a href='https://t.me/burgers_by_miratorg'>Стейк&amp;Бургер Мираторг</a> "
        "и участвуйте в розыгрыше беговой дорожки "
        "<a href='https://t.me/yamaguchiwellnessclub'>Yamaguchi</a>.</i>\n\n"
        "Как участвовать?\n\n"
        "<b>Один код = один шанс на победу. Количество шансов не ограничено!</b>\n\n"
        "Победителя определим 29 июня. Жмите кнопку «Участвовать» 👇"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(
        text="🎁 Участвовать в розыгрыше",
        url="https://t.me/GiveawayLandingBot/giveaway"
    )]
])

    with open('static/start_image.jpg', 'rb') as f:
        photo_bytes = f.read()

    for channel in PUBLISH_CHANNELS:
        from aiogram.types import BufferedInputFile
        photo = BufferedInputFile(photo_bytes, filename="start_image.jpg")
        await bot.send_photo(
            channel,
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    await message.answer("✅ Пост опубликован в оба канала!")

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
    is_subscribed = await check_subscription(callback.from_user.id)
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
        f"Хочешь добавить ещё код? Нажми /giveaway снова.",
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
    save_winner(user_id, username, full_name, code)
    await message.answer(
        f"🎲 Победитель выбран!\n\n"
        f"Имя: {full_name}\n"
        f"Ник: @{username}\n"
        f"ID: {user_id}\n"
        f"Код: {code}\n\n"
        f"Если не отвечает — используй /reroll\n"
        f"Если подтвердил — используй /confirm_winner"
    )

@dp.message(Command("reroll"))
async def cmd_reroll(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.")
        return
    participants = get_all_participants()
    if not participants:
        await message.answer("Участников пока нет.")
        return
    winner = random.choice(participants)
    user_id, username, full_name, code = winner
    save_winner(user_id, username, full_name, code)
    await message.answer(
        f"🔄 Новый победитель выбран!\n\n"
        f"Имя: {full_name}\n"
        f"Ник: @{username}\n"
        f"ID: {user_id}\n"
        f"Код: {code}\n\n"
        f"Если не отвечает — используй /reroll\n"
        f"Если подтвердил — используй /confirm_winner"
    )

@dp.message(Command("confirm_winner"))
async def cmd_confirm_winner(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.")
        return
    winner = get_winner()
    if not winner:
        await message.answer("Победитель не выбран. Используй /results сначала.")
        return
    user_id, username, full_name, code = winner
    result_text = (
        f"🏆 Итоги розыгрыша Стейк&Бургер Мираторг × Yamaguchi!\n\n"
        f"Победитель: {full_name}\n"
        f"@{username}\n"
        f"Код: {code}\n\n"
        f"Поздравляем!\n\n"
        f"Следите за новостями в нашем канале!"
    )

    with open('static/promo.jpg', 'rb') as f:
        photo_bytes = f.read()

    for channel in PUBLISH_CHANNELS:
        from aiogram.types import BufferedInputFile
        photo = BufferedInputFile(photo_bytes, filename="promo.jpg")
        await bot.send_photo(
            channel,
            photo=photo,
            caption=result_text,
        )
    await message.answer(
        f"✅ Итоги опубликованы в каналах!\n\n"
        f"Победитель: {full_name} (@{username})\n"
        f"Код: {code}"
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
        f"🔓 Свободных кодов: *{codes_info['free']}*",
        parse_mode="Markdown"
    )

@dp.message(Command("participants"))
async def cmd_participants(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.")
        return
    participants = get_all_participants()
    if not participants:
        await message.answer("Участников пока нет.")
        return
    text = "👥 Список участников:\n\n"
    from collections import Counter
    user_codes = Counter(p[0] for p in participants)
    seen = {}
    for p in participants:
        user_id, username, full_name, code = p
        if user_id not in seen:
            seen[user_id] = (username, full_name, user_codes[user_id])
    for i, (user_id, (username, full_name, codes_count)) in enumerate(seen.items(), 1):
        text += f"{i}. {full_name} (@{username}) — {codes_count} код(ов)\n"
    await message.answer(text)

@dp.message(Command("user_codes"))
async def cmd_user_codes(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /user_codes username")
        return
    username = args[1].replace("@", "")
    codes = get_user_codes_list(username)
    if not codes:
        await message.answer(f"Участник @{username} не найден.")
        return
    text = f"🎟 *Коды участника @{username}:*\n\n"
    for code, joined_at in codes:
        text += f"• `{code}` — {joined_at}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("remove_user"))
async def cmd_remove_user(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /remove_user username")
        return
    username = args[1].replace("@", "")
    deleted = remove_user_by_username(username)
    if deleted == 0:
        await message.answer(f"Участник @{username} не найден.")
        return
    await message.answer(
        f"✅ Участник @{username} удалён.\n"
        f"Удалено записей: {deleted}",
        parse_mode="Markdown"
    )

@dp.message(Command("my_codes"))
async def cmd_my_codes(message: Message):
    user_id = message.from_user.id
    count = get_user_codes_count(user_id)
    if count == 0:
        await message.answer(
            "У тебя пока нет зарегистрированных кодов.\n\n"
            "Нажми кнопку ниже чтобы участвовать!",
            reply_markup=giveaway_keyboard()
        )
        return
    await message.answer(
        f"🎟 У тебя зарегистрировано кодов: *{count}*\n\n"
        f"Каждый код — отдельный шанс на победу!\n"
        f"Итоги розыгрыша 28 июня.",
        parse_mode="Markdown"
    )

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())