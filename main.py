import discord
from discord.ext import commands
import psycopg2
import os
from datetime import datetime
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Подключение к базе данных
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_data (
        user_id TEXT PRIMARY KEY,
        начальный_баланс INTEGER DEFAULT 0
    );
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS доходы (
        id SERIAL PRIMARY KEY,
        user_id TEXT,
        сумма INTEGER,
        описание TEXT,
        дата TEXT
    );
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS расходы (
        id SERIAL PRIMARY KEY,
        user_id TEXT,
        сумма INTEGER,
        описание TEXT,
        дата TEXT
    );
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS аренда (
        id SERIAL PRIMARY KEY,
        user_id TEXT,
        машина TEXT,
        часы REAL,
        прибыль REAL,
        дата TEXT
    );
''')
conn.commit()

# Функции

def ensure_user_exists(user_id):
    cursor.execute("SELECT user_id FROM user_data WHERE user_id = %s", (str(user_id),))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO user_data (user_id) VALUES (%s)", (str(user_id),))
        conn.commit()

def get_начальный_баланс(user_id):
    ensure_user_exists(user_id)
    cursor.execute("SELECT начальный_баланс FROM user_data WHERE user_id = %s", (str(user_id),))
    row = cursor.fetchone()
    return row[0] if row else 0

def set_начальный_баланс(user_id, value):
    ensure_user_exists(user_id)
    cursor.execute("UPDATE user_data SET начальный_баланс = %s WHERE user_id = %s", (value, str(user_id)))
    conn.commit()

# Команды
@bot.command()
async def доход(ctx, сумма: int, *, описание: str):
    user_id = ctx.author.id
    дата = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO доходы (user_id, сумма, описание, дата)
        VALUES (%s, %s, %s, %s)
    ''', (str(user_id), сумма, описание, дата))
    conn.commit()
    await ctx.send(f"✅ Доход {сумма}₽ с описанием \"{описание}\" добавлен!")

@bot.command()
async def расход(ctx, сумма: int, *, описание: str):
    user_id = ctx.author.id
    дата = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO расходы (user_id, сумма, описание, дата)
        VALUES (%s, %s, %s, %s)
    ''', (str(user_id), сумма, описание, дата))
    conn.commit()
    await ctx.send(f"🧾 Расход {сумма}₽ с описанием \"{описание}\" добавлен!")

@bot.command()
async def аренда(ctx, машина: str, часы: float, прибыль: float):
    user_id = ctx.author.id
    дата = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO аренда (user_id, машина, часы, прибыль, дата)
        VALUES (%s, %s, %s, %s, %s)
    ''', (str(user_id), машина, часы, прибыль, дата))
    conn.commit()
    await ctx.send(f"🚗 Аренда {машина} на {часы}ч с прибылью {прибыль}₽ учтена!")

@bot.command()
async def баланс(ctx):
    user_id = str(ctx.author.id)
    доход = расход = аренда = 0

    cursor.execute("SELECT COALESCE(SUM(сумма), 0) FROM доходы WHERE user_id = %s", (user_id,))
    доход = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(сумма), 0) FROM расходы WHERE user_id = %s", (user_id,))
    расход = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(прибыль), 0) FROM аренда WHERE user_id = %s", (user_id,))
    аренда = cursor.fetchone()[0]

    начальный = get_начальный_баланс(user_id)
    итого = начальный + доход + аренда - расход

    await ctx.send(f"💰 Ваш баланс: {итого}₽\nНачальный: {начальный}₽\nДоходы: {доход}₽\nАренда: {аренда}₽\nРасходы: {расход}₽")

@bot.command()
async def старт(ctx, сумма: int):
    user_id = ctx.author.id
    set_начальный_баланс(user_id, сумма)
    await ctx.send(f"🎯 Установлен начальный баланс: {сумма}₽")

# Запуск
keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
