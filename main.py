import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput, Button
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
    CREATE TABLE IF NOT EXISTS незавершённые_сделки (
        id SERIAL PRIMARY KEY,
        user_id TEXT,
        товар TEXT,
        цена_покупки REAL,
        дата TEXT
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
        self.часы = TextInput(label="Часы аренды", required=True, placeholder="Например: 2.5")
        self.ставка = TextInput(label="Цена за час аренды", required=True, placeholder="Например: 300")
        self.add_item(self.машина)
        self.add_item(self.часы)
        self.add_item(self.ставка)

    async def on_submit(self, interaction):
        дата = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        часы = float(self.часы.value)
        ставка = float(self.ставка.value)
        прибыль = часы * ставка

        cursor.execute("INSERT INTO аренда (user_id, машина, часы, прибыль, дата) VALUES (%s, %s, %s, %s, %s)",
                       (str(self.user_id), self.машина.value, часы, прибыль, дата))
        conn.commit()
        await interaction.response.send_message(f"🚗 Аренда учтена! Прибыль: {прибыль}₽", ephemeral=True)

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
        
class ПокупкаModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="Фиксация покупки")
        self.user_id = str(user_id)
        self.товар = TextInput(label="Что купили?", required=True)
        self.покупка = TextInput(label="Цена покупки", required=True, placeholder="Например: 1200")
        self.add_item(self.товар)
        self.add_item(self.покупка)

    async def on_submit(self, interaction):
        дата = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        товар = self.товар.value
        покупка = float(self.покупка.value)

        cursor.execute(
            "INSERT INTO незавершённые_сделки (user_id, товар, цена_покупки, дата) VALUES (%s, %s, %s, %s)",
            (self.user_id, товар, покупка, дата)
        )
        conn.commit()

        await interaction.response.send_message(f"📝 Зафиксировано: {товар} куплен за {покупка}₽", ephemeral=True)
        
class ЗавершитьСделкуModal(Modal):
    def __init__(self, user_id, сделка_id, товар, покупка):
        super().__init__(title="Продажа перекупа")
        self.user_id = str(user_id)
        self.сделка_id = сделка_id
        self.товар = товар
        self.покупка = покупка

        self.продажа = TextInput(label="Цена продажи", required=True, placeholder="Например: 1500")
        self.add_item(self.продажа)

    async def on_submit(self, interaction):
        продажа = float(self.продажа.value)
        прибыль = продажа - self.покупка
        дата = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if прибыль >= 0:
            cursor.execute(
                "INSERT INTO доходы (user_id, сумма, описание, дата) VALUES (%s, %s, %s, %s)",
                (self.user_id, прибыль, f"🔄 Перекуп (продажа): {self.товар}", дата)
            )
            msg = f"💰 Продано: {self.товар} → прибыль {прибыль}₽"
        else:
            cursor.execute(
                "INSERT INTO расходы (user_id, сумма, описание, дата) VALUES (%s, %s, %s, %s)",
                (self.user_id, abs(прибыль), f"🔄 Убыток при перекупе: {self.товар}", дата)
            )
            msg = f"📉 Продано: {self.товар} → убыток {abs(прибыль)}₽"

        # Удаляем завершённую сделку
        cursor.execute("DELETE FROM незавершённые_сделки WHERE id = %s", (self.сделка_id,))
        conn.commit()

        await interaction.response.send_message(msg, ephemeral=True)        
        
class ПерекупModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="Учёт перекупа")
        self.user_id = str(user_id)
        self.товар = TextInput(label="Что перекупили?", required=True)
        self.покупка = TextInput(label="Цена покупки", required=True, placeholder="Например: 1000")
        self.продажа = TextInput(label="Цена продажи", required=True, placeholder="Например: 1500")
        self.add_item(self.товар)
        self.add_item(self.покупка)
        self.add_item(self.продажа)

    async def on_submit(self, interaction):
        дата = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        покупка = float(self.покупка.value)
        продажа = float(self.продажа.value)
        прибыль = продажа - покупка

        if прибыль >= 0:
            cursor.execute("INSERT INTO доходы (user_id, сумма, описание, дата) VALUES (%s, %s, %s, %s)",
                           (self.user_id, прибыль, f"🔄 Перекуп: {self.товар.value}", дата))
            сообщение = f"💰 Сделка учтена! Прибыль: {прибыль}₽"
        else:
            cursor.execute("INSERT INTO расходы (user_id, сумма, описание, дата) VALUES (%s, %s, %s, %s)",
                           (self.user_id, abs(прибыль), f"🔄 Убыток при перекупе: {self.товар.value}", дата))
            сообщение = f"📉 Сделка в убыток! Потери: {abs(прибыль)}₽"

        conn.commit()
        await interaction.response.send_message(сообщение, ephemeral=True)
        
# Главное меню
class ПростоеМеню(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = str(user_id)
        self.add_item(Button(label="💵 Добавить доход", style=discord.ButtonStyle.success, custom_id="add_income"))
        self.add_item(Button(label="💸 Добавить расход", style=discord.ButtonStyle.danger, custom_id="add_expense"))
        self.add_item(Button(label="🚗 Учесть аренду", style=discord.ButtonStyle.primary, custom_id="add_rent"))
        self.add_item(Button(label="📊 Показать баланс", style=discord.ButtonStyle.secondary, custom_id="show_balance"))
        self.add_item(Button(label="💰 Установить начальный баланс", style=discord.ButtonStyle.secondary, custom_id="set_start"))
        self.add_item(Button(label="➕ Куплено", style=discord.ButtonStyle.primary, custom_id="resell_pending"))
        self.add_item(Button(label="✅ Продать", style=discord.ButtonStyle.success, custom_id="resell_complete"))
        self.add_item(Button(label="📋 Мои покупки", style=discord.ButtonStyle.secondary, custom_id="resell_list"))
        self.add_item(Button(label="📝 История операций", style=discord.ButtonStyle.secondary, custom_id="history"))
        self.add_item(Button(label="🔄 Перекуп", style=discord.ButtonStyle.primary, custom_id="resell"))
        self.add_item(Button(label="🗑️ Очистка данных", style=discord.ButtonStyle.danger, custom_id="clear_all"))

@bot.command(name="меню")
async def меню(ctx):
    embed = discord.Embed(
        title="Универсальный бот для учёта финансов",
        description="Теперь не придётся помнить о доходах и расходах — бот сделает это сам.",
        color=discord.Color.purple()
    )
    embed.set_image(url="https://i.imgur.com/jOmamcY.png")
    await ctx.send(embed=embed, view=ПростоеМеню(ctx.author.id))

@bot.event
async def on_interaction(interaction):
    user_id = str(interaction.user.id)

    if not interaction.data or "custom_id" not in interaction.data:
        return

    custom_id = interaction.data["custom_id"]

    if custom_id == "add_income":
        await interaction.response.send_modal(ДоходModal(user_id))

    elif custom_id == "add_expense":
        await interaction.response.send_modal(РасходModal(user_id))

    elif custom_id == "set_balance":
        await interaction.response.send_modal(БалансModal(user_id))

    elif custom_id == "add_rent":
        await interaction.response.send_modal(АрендаModal(user_id))

    elif custom_id == "show_balance":
        view = БалансView(user_id)
        await view.показать_баланс(interaction, None)

    elif custom_id == "show_history":
        await показать_историю(interaction, user_id)

    elif custom_id == "clear_income":
        await очистить_категорию(interaction, user_id, "доходы")

    elif custom_id == "clear_expense":
        await очистить_категорию(interaction, user_id, "расходы")

    elif custom_id == "clear_rental":
        await очистить_категорию(interaction, user_id, "аренда")

    elif custom_id == "clear_all":
        await очистить_все(interaction, user_id)

    elif custom_id == "resell":
        await interaction.response.send_modal(ПерекупModal(user_id))
        
    elif custom_id == "resell_pending":
        await interaction.response.send_modal(ПокупкаModal(user_id))
        
    elif custom_id == "clear_all":
        cursor.execute("DELETE FROM доходы WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM расходы WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM аренда WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM незавершённые_сделки WHERE user_id = %s", (user_id,))
        conn.commit()
        await interaction.response.send_message("🧹 Все данные очищены.", ephemeral=True)
    
    elif custom_id == "history":
        history_text = ""

        cursor.execute("SELECT сумма, описание, дата FROM доходы WHERE user_id = %s ORDER BY дата DESC LIMIT 5", (user_id,))
        доходы = cursor.fetchall()
        if доходы:
            history_text += "**📈 Доходы:**\n"
            for сумма, описание, дата in доходы:
                history_text += f"➕ {сумма}₽ — {описание} ({дата})\n"
        else:
            history_text += "📈 Доходы: ничего нет\n"

        cursor.execute("SELECT сумма, описание, дата FROM расходы WHERE user_id = %s ORDER BY дата DESC LIMIT 5", (user_id,))
        расходы = cursor.fetchall()
        if расходы:
            history_text += "\n**📉 Расходы:**\n"
            for сумма, описание, дата in расходы:
                history_text += f"➖ {сумма}₽ — {описание} ({дата})\n"
        else:
            history_text += "\n📉 Расходы: ничего нет\n"

        await interaction.response.send_message(history_text, ephemeral=True)
    
    elif custom_id == "resell_complete":
        cursor.execute("SELECT id, товар, цена_покупки FROM незавершённые_сделки WHERE user_id = %s", (user_id,))
        сделки = cursor.fetchall()

        if not сделки:
            await interaction.response.send_message("❌ У вас нет незавершённых покупок.", ephemeral=True)
            return

        if len(сделки) == 1:
            id_, товар, покупка = сделки[0]
            await interaction.response.send_modal(ЗавершитьСделкуModal(user_id, id_, товар, покупка))
        else:
            view = View()
            for id_, товар, покупка in сделки:
                button = Button(
                    label=f"{товар} ({покупка}₽)",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"sell_{id_}"
                )

                async def callback(inter, id_=id_, товар=товар, покупка=покупка):
                    await inter.response.send_modal(ЗавершитьСделкуModal(user_id, id_, товар, покупка))

                button.callback = callback
                view.add_item(button)

            await interaction.response.send_message("Выберите, что хотите продать:", view=view, ephemeral=True)

    elif custom_id == "resell_list":
        cursor.execute("SELECT товар, цена_покупки, дата FROM незавершённые_сделки WHERE user_id = %s", (user_id,))
        записи = cursor.fetchall()

        if not записи:
            await interaction.response.send_message("🔍 У вас нет незавершённых покупок.", ephemeral=True)
        else:
            lines = [f"🔹 {товар} — {цена}₽ (📅 {дата})" for товар, цена, дата in записи]
            текст = "\n".join(lines)
            await interaction.response.send_message(f"📋 **Ваши незавершённые покупки:**\n{текст}", ephemeral=True)

# Запуск
if __name__ == '__main__':
    keep_alive()  # Flask сервер для UptimeRobot
    bot.run(os.getenv("DISCORD_TOKEN"))
