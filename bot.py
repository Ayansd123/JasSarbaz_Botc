import logging
from datetime import time
import pytz
import random

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters,
)

TOKEN = "8708103306:AAHzZ69oYkFWy11GdG03uAp1uPigH5dCqOg"

logging.basicConfig(level=logging.INFO)

(
    STRESS,
    MOTIVATION,
    READY,
    TEAMWORK,
    MENU,
    CITY,
    SET_TIME,
    PHYS1,
    PHYS2,
) = range(9)

users = {}

KZ_CITIES = {
    "Алматы": "Asia/Almaty",
    "Астана": "Asia/Almaty",
    "Шымкент": "Asia/Almaty",
    "Усть-Каменогорск": "Asia/Almaty",
    "Караганда": "Asia/Almaty",
    "Атырау": "Asia/Aqtau",
    "Актау": "Asia/Aqtau",
    "Актобе": "Asia/Aqtobe",
}

MOTIVATION_QUOTES = [
    "Слабость уходит через дисциплину.",
    "Ты устаёшь — но не сдаёшься.",
    "Рост начинается за пределами комфорта.",
    "Сегодня сложнее — завтра легче.",
    "Делай то, что другие не делают."
]

STATHAM_QUOTES = [
    "Работай молча. Пусть результат говорит.",
    "Никто не придёт спасать тебя.",
    "Сила — это выбор.",
    "Дисциплина важнее мотивации."
]


# ---------- План ----------

def build_plan(user):
    gender = user["gender"]

    if gender == "men":
        base_pull = int(user["pullups"])
        run = float(user["run"])
        pull_plan = max(4, base_pull // 2)
        run_plan = max(2, run)

        text = f"План на сегодня:\nПодтягивания 4x{pull_plan}\nБрусья 4x12\nКросс {run_plan} км\n"

    else:
        base_press = int(user["press"])
        run = float(user["run"])
        press_plan = max(15, base_press // 2)
        run_plan = max(2, run)

        text = f"План на сегодня:\nПресс 4x{press_plan}\nПриседания 4x20\nКросс {run_plan} км\n"

    quotes = random.sample(MOTIVATION_QUOTES, 3)
    statham = random.choice(STATHAM_QUOTES)

    text += "\n"
    for q in quotes:
        text += f"• {q}\n"

    text += f"\nДжейсон Стэтхем:\n«{statham}»"

    return text


# ---------- Старт ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Оцени стрессоустойчивость (1-10)")
    return STRESS


async def stress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {"stress": update.message.text}
    await update.message.reply_text("Оцени мотивацию (1-10)")
    return MOTIVATION


async def motivation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["motivation"] = update.message.text
    await update.message.reply_text("Оцени готовность (1-10)")
    return READY


async def ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["ready"] = update.message.text
    await update.message.reply_text("Как ты работаешь в команде? (1-10)")
    return TEAMWORK


async def teamwork(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["teamwork"] = update.message.text
    return await show_menu(update)


# ---------- Меню ----------

async def show_menu(update):
    keyboard = [
        ["Военные ВУЗы РК"],
        ["Тренировки для мужчин"],
        ["Тренировки для женщин"],
    ]
    await update.message.reply_text(
        "Выбери раздел:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return MENU


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "Военные ВУЗы РК":
        await update.message.reply_text(
            "Военные ВУЗы Казахстана:\n"
            "1. Военный институт Сухопутных войск\n"
            "2. Военно-инженерный институт радиоэлектроники и связи\n"
            "3. Военный институт Сил воздушной обороны\n"
        )
        return await show_menu(update)

    if text == "Тренировки для мужчин":
        users[user_id]["gender"] = "men"

    if text == "Тренировки для женщин":
        users[user_id]["gender"] = "women"

    keyboard = [[c] for c in KZ_CITIES.keys()]
    await update.message.reply_text(
        "Выбери город:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return CITY


# ---------- Город ----------

async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city_name = update.message.text
    user_id = update.effective_user.id

    if city_name not in KZ_CITIES:
        return CITY

    users[user_id]["timezone"] = pytz.timezone(KZ_CITIES[city_name])

    await update.message.reply_text(
        "Введите время отправки (например 07:30)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return SET_TIME


# ---------- Время ----------

async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        hour, minute = map(int, update.message.text.split(":"))
        tz = users[user_id]["timezone"]
        send_time = time(hour=hour, minute=minute, tzinfo=tz)
    except:
        await update.message.reply_text("Неверный формат времени")
        return SET_TIME

    users[user_id]["time"] = send_time

    if users[user_id]["gender"] == "men":
        await update.message.reply_text("Сколько максимум подтягиваний?")
    else:
        await update.message.reply_text("Сколько максимум повторений на пресс?")

    return PHYS1


# ---------- Физподготовка ----------

async def phys1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if users[user_id]["gender"] == "men":
        users[user_id]["pullups"] = update.message.text
    else:
        users[user_id]["press"] = update.message.text

    await update.message.reply_text("Сколько км бегаешь без остановки?")
    return PHYS2


async def phys2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id]["run"] = update.message.text

    # отправляем первый план сразу
    text = build_plan(users[user_id])
    await update.message.reply_text(text)

    # ежедневная отправка
    context.job_queue.run_daily(
        send_training,
        time=users[user_id]["time"],
        days=(0,1,2,3,4,5,6),
        data=user_id,
        name=str(user_id),
    )

    return await show_menu(update)


# ---------- Отправка ----------

async def send_training(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data
    if user_id not in users:
        return

    text = build_plan(users[user_id])
    await context.bot.send_message(chat_id=user_id, text=text)


# ---------- Запуск ----------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STRESS: [MessageHandler(filters.TEXT, stress)],
            MOTIVATION: [MessageHandler(filters.TEXT, motivation)],
            READY: [MessageHandler(filters.TEXT, ready)],
            TEAMWORK: [MessageHandler(filters.TEXT, teamwork)],
            MENU: [MessageHandler(filters.TEXT, menu)],
            CITY: [MessageHandler(filters.TEXT, city)],
            SET_TIME: [MessageHandler(filters.TEXT, set_time)],
            PHYS1: [MessageHandler(filters.TEXT, phys1)],
            PHYS2: [MessageHandler(filters.TEXT, phys2)],
        },
        fallbacks=[CommandHandler("menu", show_menu)],
    )

    app.add_handler(conv)
    app.run_polling()


if __name__ == "__main__":
    main()