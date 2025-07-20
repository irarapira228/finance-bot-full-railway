import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput
import psycopg2
import os
from datetime import datetime
from keep_alive import keep_alive  # для UptimeRobot

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

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

def ensure_user_exists(user_id):
    cursor.execute("SELECT user_id FROM user_data WHERE user_id = %s", (str(user_id),))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO user_data (user_id) VALUES (%s)", (str(user_id),))
        conn.commit()

def set_начальный_баланс(user_id, value):
    ensure_user_exists(user_id)
    cursor.execute("UPDATE user_data SET начальный_баланс = %s WHERE user_id = %s", (value, str(user_id)))
    conn.commit()

# Модальные окна
class ДоходModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="Добавить доход")
        self.user_id = user_id
        self.amount = TextInput(label="Сумма", required=True)
        self.description = TextInput(label="Описание", required=True)
        self.add_item(self.amount)
        self.add_item(self.description)

    async def on_submit(self, interaction):
        дата = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO доходы (user_id, сумма, описание, дата) VALUES (%s, %s, %s, %s)",
                       (str(self.user_id), int(self.amount.value), self.description.value, дата))
        conn.commit()
        await interaction.response.send_message("✅ Доход добавлен!", ephemeral=True)

class РасходModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="Добавить расход")
        self.user_id = user_id
        self.amount = TextInput(label="Сумма", required=True)
        self.description = TextInput(label="Описание", required=True)
        self.add_item(self.amount)
        self.add_item(self.description)

    async def on_submit(self, interaction):
        дата = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO расходы (user_id, сумма, описание, дата) VALUES (%s, %s, %s, %s)",
                       (str(self.user_id), int(self.amount.value), self.description.value, дата))
        conn.commit()
        await interaction.response.send_message("🧾 Расход добавлен!", ephemeral=True)

class АрендаModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="Учесть аренду")
        self.user_id = user_id
        self.машина = TextInput(label="Машина", required=True)
        self.часы = TextInput(label="Часы", required=True)
        self.прибыль = TextInput(label="Прибыль", required=True)
        self.add_item(self.машина)
        self.add_item(self.часы)
        self.add_item(self.прибыль)

    async def on_submit(self, interaction):
        дата = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO аренда (user_id, машина, часы, прибыль, дата) VALUES (%s, %s, %s, %s, %s)",
                       (str(self.user_id), self.машина.value, float(self.часы.value), float(self.прибыль.value), дата))
        conn.commit()
        await interaction.response.send_message("🚗 Аренда учтена!", ephemeral=True)

# Очистка
class ОчисткаView(View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = str(user_id)

    @discord.ui.button(label="Доходы", style=discord.ButtonStyle.danger)
    async def доходы(self, interaction, _):
        cursor.execute("DELETE FROM доходы WHERE user_id = %s", (self.user_id,))
        conn.commit()
        await interaction.response.send_message("✅ Доходы удалены", ephemeral=True)

    @discord.ui.button(label="Расходы", style=discord.ButtonStyle.danger)
    async def расходы(self, interaction, _):
        cursor.execute("DELETE FROM расходы WHERE user_id = %s", (self.user_id,))
        conn.commit()
        await interaction.response.send_message("✅ Расходы удалены", ephemeral=True)

    @discord.ui.button(label="Аренда", style=discord.ButtonStyle.danger)
    async def аренда(self, interaction, _):
        cursor.execute("DELETE FROM аренда WHERE user_id = %s", (self.user_id,))
        conn.commit()
        await interaction.response.send_message("✅ Аренда удалена", ephemeral=True)

    @discord.ui.button(label="Всё", style=discord.ButtonStyle.danger)
    async def всё(self, interaction, _):
        cursor.execute("DELETE FROM доходы WHERE user_id = %s", (self.user_id,))
        cursor.execute("DELETE FROM расходы WHERE user_id = %s", (self.user_id,))
        cursor.execute("DELETE FROM аренда WHERE user_id = %s", (self.user_id,))
        cursor.execute("UPDATE user_data SET начальный_баланс = 0 WHERE user_id = %s", (self.user_id,))
        conn.commit()
        await interaction.response.send_message("🧹 Всё очищено!", ephemeral=True)

# Просмотр
class БалансView(View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = str(user_id)

    async def показать_баланс(self, interaction, _):
        cursor.execute("SELECT начальный_баланс FROM user_data WHERE user_id = %s", (self.user_id,))
        начальный = cursor.fetchone()
        начальный = начальный[0] if начальный else 0
        cursor.execute("SELECT COALESCE(SUM(сумма),0) FROM доходы WHERE user_id = %s", (self.user_id,))
        доход = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(сумма),0) FROM расходы WHERE user_id = %s", (self.user_id,))
        расход = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(прибыль),0) FROM аренда WHERE user_id = %s", (self.user_id,))
        аренда = cursor.fetchone()[0]
        итог = начальный + доход + аренда - расход
        await interaction.response.send_message(f"💰 Баланс: {итог}₽\nНачальный: {начальный}₽\nДоходы: {доход}₽\nАренда: {аренда}₽\nРасходы: {расход}₽", ephemeral=True)

    async def установить_баланс(self, interaction, _):
        class StartModal(Modal):
            def __init__(inner):
                super().__init__(title="Начальный баланс")
                inner.amount = TextInput(label="Введите сумму", required=True)
                inner.add_item(inner.amount)

            async def on_submit(inner, interaction):
                set_начальный_баланс(self.user_id, int(inner.amount.value))
                await interaction.response.send_message("🎯 Баланс установлен!", ephemeral=True)

        await interaction.response.send_modal(StartModal())

    async def история_операций(self, interaction, _):
        msg = "📒 История:\n"
        cursor.execute("SELECT сумма, описание, дата FROM доходы WHERE user_id = %s ORDER BY дата DESC LIMIT 5", (self.user_id,))
        доходы = cursor.fetchall()
        msg += "\n🟢 Доходы:\n" + "\n".join([f"+{с}₽ | {о} ({д})" for с, о, д in доходы]) if доходы else "\nНет доходов"
        cursor.execute("SELECT сумма, описание, дата FROM расходы WHERE user_id = %s ORDER BY дата DESC LIMIT 5", (self.user_id,))
        расходы = cursor.fetchall()
        msg += "\n\n🔴 Расходы:\n" + "\n".join([f"-{с}₽ | {о} ({д})" for с, о, д in расходы]) if расходы else "\nНет расходов"
        cursor.execute("SELECT машина, часы, прибыль, дата FROM аренда WHERE user_id = %s ORDER BY дата DESC LIMIT 5", (self.user_id,))
        аренды = cursor.fetchall()
        msg += "\n\n🚗 Аренда:\n" + "\n".join([f"{м}: {ч}ч → {п}₽ ({д})" for м, ч, п, д in аренды]) if аренды else "\nНет аренды"
        await interaction.response.send_message(msg, ephemeral=True)

# Главное меню
class ГлавноеМеню(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Выберите действие",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="📥 Добавить доход", value="доход"),
            discord.SelectOption(label="📤 Добавить расход", value="расход"),
            discord.SelectOption(label="🚗 Учесть аренду", value="аренда"),
            discord.SelectOption(label="💰 Показать баланс", value="баланс"),
            discord.SelectOption(label="🎯 Установить начальный баланс", value="начальный"),
            discord.SelectOption(label="📒 История операций", value="история"),
            discord.SelectOption(label="🧹 Очистка данных", value="очистка")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = select.values[0]
        view = БалансView(self.user_id)
        if value == "доход":
            await interaction.response.send_modal(ДоходModal(self.user_id))
        elif value == "расход":
            await interaction.response.send_modal(РасходModal(self.user_id))
        elif value == "аренда":
            await interaction.response.send_modal(АрендаModal(self.user_id))
        elif value == "баланс":
            await view.показать_баланс(interaction, None)
        elif value == "начальный":
            await view.установить_баланс(interaction, None)
        elif value == "история":
            await view.история_операций(interaction, None)
        elif value == "очистка":
            await interaction.response.send_message("🧼 Очистка данных:", view=ОчисткаView(self.user_id), ephemeral=True)

@bot.command(name="меню")
async def меню(ctx):
    embed = discord.Embed(
        title="Универсальный бот для учёта финансов",
        description="Теперь не придётся помнить о доходах и расходах — бот сделает это сам.",
        color=discord.Color.purple()
    )
    embed.set_image(url="https://i.imgur.com/jOmamcY.png")  # можешь заменить на свою ссылку
    await ctx.send(embed=embed, view=ГлавноеМеню(ctx.author.id))

# Запуск
if __name__ == '__main__':
    keep_alive()  # Flask сервер для UptimeRobot
    bot.run(os.getenv("DISCORD_TOKEN"))
