import logging
import os
from datetime import time
import pytz
import random

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters,
)

TOKEN = os.getenv("TOKEN")

logging.basicConfig(level=logging.INFO)

STRESS, MOTIVATION, TEAMWORK, READY, MENU, CITY, SET_TIME, PHYSICAL = range(8)

users = {}

KZ_CITIES = {
    "Алматы": "Asia/Almaty",
    "Астана": "Asia/Almaty",
    "Шымкент": "Asia/Almaty",
    "Караганда": "Asia/Almaty",
    "Актобе": "Asia/Aqtobe",
    "Атырау": "Asia/Aqtau",
}

MOTIVATION_QUOTES = [
    "Слабость уходит через дисциплину.",
    "Ты устаешь — но не сдаешься.",
    "Рост начинается за пределами комфорта.",
    "Сегодня сложнее — завтра легче.",
    "Делай то, что другие не делают."
]

STATHAM_QUOTES = [
    "Работай молча. Пусть результат говорит.",
    "Никто не придет спасать тебя.",
    "Сила — это выбор.",
    "Дисциплина важнее мотивации."
]


def build_plan(user_id):
    user = users[user_id]
    gender = user["gender"]
    level = user["level"]
    day = user["day"]

    if gender == "men":
        pullups = max(3, level)
        run = 2 + level * 0.3
        base = f"День {day}\nПодтягивания 4x{pullups}\nБег {round(run,1)} км\n"
    else:
        press = 10 + level * 2
        run = 1.5 + level * 0.3
        base = f"День {day}\nПресс 4x{press}\nБег {round(run,1)} км\n"

    quotes = random.sample(MOTIVATION_QUOTES, 3)
    statham = random.choice(STATHAM_QUOTES)

    text = base + "\n"
    for q in quotes:
        text += f"• {q}\n"

    text += f"\nДжейсон Стэтхем:\n«{statham}»"
    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Оцени стрессоустойчивость от 1 до 10")
    return STRESS


async def stress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {"stress": update.message.text}
    await update.message.reply_text("Оцени мотивацию от 1 до 10")
    return MOTIVATION


async def motivation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["motivation"] = update.message.text
    await update.message.reply_text("Как ты работаешь в команде? (1-10)")
    return TEAMWORK


async def teamwork(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["teamwork"] = update.message.text
    await update.message.reply_text("Готовность к тренировкам (1-10)")
    return READY


async def ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await show_menu(update, context)


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Тренировки для мужчин"],
        ["Тренировки для женщин"],
        ["Военные ВУЗы РК"]
    ]
    await update.message.reply_text(
        "Выбери направление:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
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
            "3. Военный институт Сил воздушной обороны"
        )
        return MENU

    if text == "Тренировки для мужчин":
        users[user_id]["gender"] = "men"
        await update.message.reply_text("Сколько подтягиваний максимум?")
        return PHYSICAL

    if text == "Тренировки для женщин":
        users[user_id]["gender"] = "women"
        await update.message.reply_text("Сколько раз делаешь пресс без остановки?")
        return PHYSICAL


async def physical(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        level = int(update.message.text)
    except:
        await update.message.reply_text("Введите число")
        return PHYSICAL

    users[user_id]["level"] = level
    users[user_id]["day"] = 1

    keyboard = [[city] for city in KZ_CITIES.keys()]
    keyboard.append(["Главное меню"])

    await update.message.reply_text(
        "Выбери город:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CITY


async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city_name = update.message.text
    user_id = update.effective_user.id

    if city_name == "Главное меню":
        return await show_menu(update, context)

    if city_name not in KZ_CITIES:
        await update.message.reply_text("Выбери город из списка")
        return CITY

    tz = pytz.timezone(KZ_CITIES[city_name])
    users[user_id]["timezone"] = tz
    await update.message.reply_text("Введите время отправки (например 07:30)")
    return SET_TIME


async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Главное меню":
        return await show_menu(update, context)

    user_id = update.effective_user.id
    tz = users[user_id]["timezone"]

    try:
        hour, minute = map(int, update.message.text.split(":"))
        send_time = time(hour=hour, minute=minute, tzinfo=tz)
    except:
        await update.message.reply_text("Неверный формат")
        return SET_TIME

    users[user_id]["time"] = send_time

    text = build_plan(user_id)
    await update.message.reply_text(text)

    context.job_queue.run_daily(
        send_training,
        time=send_time,
        data=user_id,
        name=str(user_id),
    )

    return await show_menu(update, context)


async def send_training(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data
    if user_id not in users:
        return

    users[user_id]["day"] += 1
    text = build_plan(user_id)
    await context.bot.send_message(chat_id=user_id, text=text)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STRESS: [MessageHandler(filters.TEXT, stress)],
            MOTIVATION: [MessageHandler(filters.TEXT, motivation)],
            TEAMWORK: [MessageHandler(filters.TEXT, teamwork)],
            READY: [MessageHandler(filters.TEXT, ready)],
            MENU: [MessageHandler(filters.TEXT, menu)],
            PHYSICAL: [MessageHandler(filters.TEXT, physical)],
            CITY: [MessageHandler(filters.TEXT, city)],
            SET_TIME: [MessageHandler(filters.TEXT, set_time)],
        },
        fallbacks=[CommandHandler("menu", show_menu)],
    )

    app.add_handler(conv)
    app.run_polling()


import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running')

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    main()


