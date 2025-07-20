import discord
from discord.ext import commands
import datetime
import json
import os
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "user_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

user_data = load_data()

def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in user_data:
        user_data[user_id] = {
            "доходы": [],
            "расходы": [],
            "аренда": [],
            "начальный_баланс": 0
        }
        save_data()
    return user_data[user_id]

# ---------------- Кнопки ----------------

class ДоходButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="💰 Доход", style=discord.ButtonStyle.success, custom_id="btn_income")

    async def callback(self, interaction: discord.Interaction):
        modal = IncomeModal(user_id=interaction.user.id)
        await interaction.response.send_modal(modal)

class РасходButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🔴 Расход", style=discord.ButtonStyle.danger, custom_id="btn_expense")

    async def callback(self, interaction: discord.Interaction):
        modal = ExpenseModal(user_id=interaction.user.id)
        await interaction.response.send_modal(modal)

class АрендаButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🚗 Аренда авто", style=discord.ButtonStyle.success, custom_id="btn_rental")

    async def callback(self, interaction: discord.Interaction):
        modal = RentalModal(user_id=interaction.user.id)
        await interaction.response.send_modal(modal)

class БалансButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="📊 Баланс", style=discord.ButtonStyle.primary, custom_id="btn_balance")

    async def callback(self, interaction: discord.Interaction):
        data = get_user_data(interaction.user.id)
        доход = sum(entry['сумма'] for entry in data["доходы"])
        расход = sum(entry['сумма'] for entry in data["расходы"])
        аренда = sum(entry['прибыль'] for entry in data["аренда"])
        итог = data["начальный_баланс"] + доход + аренда - расход
        text = (
            f"🏁 Начальный баланс: {data['начальный_баланс']} руб.\n"
            f"💰 Доходы: {доход} руб.\n🔴 Расходы: {расход} руб.\n🚗 Аренда: {аренда} руб.\n\n"
            f"📌 Итог: **{итог} руб.**"
        )
        await interaction.response.send_message(text, ephemeral=True)

class ИсторияButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="📖 История", style=discord.ButtonStyle.secondary, custom_id="btn_history")

    async def callback(self, interaction: discord.Interaction):
        data = get_user_data(interaction.user.id)
        history = ""
        for entry in data["доходы"]:
            history += f"💰 Доход: {entry['сумма']} руб. - {entry['описание']} ({entry['дата']})\n"
        for entry in data["расходы"]:
            history += f"🔴 Расход: {entry['сумма']} руб. - {entry['описание']} ({entry['дата']})\n"
        for entry in data["аренда"]:
            history += f"🚗 Аренда: {entry['прибыль']} руб. ({entry['машина']}, {entry['часы']} ч., {entry['дата']})\n"
        if not history:
            history = "Нет данных."
        await interaction.response.send_message(history, ephemeral=True)

class ОчиститьButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🗑️ Очистить", style=discord.ButtonStyle.danger, custom_id="btn_clear")

    async def callback(self, interaction: discord.Interaction):
        view = ОчисткаВыборView(user_id=interaction.user.id)
        await interaction.response.send_message("Что вы хотите очистить?", view=view, ephemeral=True)

class НачальныйБалансButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🏁 Нач. баланс", style=discord.ButtonStyle.success, custom_id="btn_start_balance")

    async def callback(self, interaction: discord.Interaction):
        modal = НачальныйБалансModal(user_id=interaction.user.id)
        await interaction.response.send_modal(modal)

# ---------------- Модальные окна ----------------

class IncomeModal(discord.ui.Modal, title="Добавить доход"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    сумма = discord.ui.TextInput(label="Сумма", placeholder="Введите сумму", required=True)
    описание = discord.ui.TextInput(label="Описание", placeholder="Продажа, премия и т.д.", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        data = get_user_data(self.user_id)
        data["доходы"].append({
            "сумма": int(self.сумма.value),
            "описание": self.описание.value,
            "дата": datetime.datetime.now().strftime("%d.%m.%Y")
        })
        save_data()
        await interaction.response.send_message("✅ Доход добавлен!", ephemeral=True)

class ExpenseModal(discord.ui.Modal, title="Добавить расход"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    сумма = discord.ui.TextInput(label="Сумма", placeholder="Введите сумму", required=True)
    описание = discord.ui.TextInput(label="Описание", placeholder="Покупка, штраф и т.д.", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        data = get_user_data(self.user_id)
        data["расходы"].append({
            "сумма": int(self.сумма.value),
            "описание": self.описание.value,
            "дата": datetime.datetime.now().strftime("%d.%m.%Y")
        })
        save_data()
        await interaction.response.send_message("✅ Расход добавлен!", ephemeral=True)

class RentalModal(discord.ui.Modal, title="Добавить аренду авто"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    машина = discord.ui.TextInput(label="Автомобиль", placeholder="Модель машины", required=True)
    часы = discord.ui.TextInput(label="Часы аренды", placeholder="Например: 3", required=True)
    стоимость_часа = discord.ui.TextInput(label="Цена за час", placeholder="Например: 500", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            часы = float(self.часы.value)
            цена = float(self.стоимость_часа.value)
            прибыль = часы * цена
            data = get_user_data(self.user_id)
            data["аренда"].append({
                "машина": self.машина.value,
                "часы": часы,
                "прибыль": прибыль,
                "дата": datetime.datetime.now().strftime("%d.%m.%Y")
            })
            save_data()
            await interaction.response.send_message(f"✅ Аренда добавлена: {прибыль} руб.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Убедитесь, что вы ввели числа.", ephemeral=True)

class НачальныйБалансModal(discord.ui.Modal, title="Установить начальный баланс"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    сумма = discord.ui.TextInput(label="Сумма", placeholder="Введите сумму", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            сумма = int(self.сумма.value)
            data = get_user_data(self.user_id)
            data["начальный_баланс"] = сумма
            save_data()
            await interaction.response.send_message(f"✅ Начальный баланс установлен: {сумма} руб.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Введите корректную сумму (число).", ephemeral=True)

# ---------------- Очистка ----------------

class ОчисткаВыборView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

        self.add_item(ОчиститьКонкретноButton("доходы", "💰 Доходы"))
        self.add_item(ОчиститьКонкретноButton("расходы", "🔴 Расходы"))
        self.add_item(ОчиститьКонкретноButton("аренда", "🚗 Аренда"))
        self.add_item(ОчиститьБалансButton())

class ОчиститьКонкретноButton(discord.ui.Button):
    def __init__(self, field, label):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, custom_id=f"clear_{field}")
        self.field = field

    async def callback(self, interaction: discord.Interaction):
        data = get_user_data(interaction.user.id)
        data[self.field] = []
        save_data()
        await interaction.response.send_message(f"✅ {self.label} очищены.", ephemeral=True)

class ОчиститьБалансButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="📉 Баланс (всё)", style=discord.ButtonStyle.danger, custom_id="clear_all")

    async def callback(self, interaction: discord.Interaction):
        data = get_user_data(interaction.user.id)
        data["доходы"] = []
        data["расходы"] = []
        data["аренда"] = []
        data["начальный_баланс"] = 0
        save_data()
        await interaction.response.send_message("✅ Баланс полностью очищен.", ephemeral=True)

# ---------------- Главное меню ----------------

class FinanceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ДоходButton())
        self.add_item(РасходButton())
        self.add_item(АрендаButton())
        self.add_item(БалансButton())
        self.add_item(ИсторияButton())
        self.add_item(НачальныйБалансButton())
        self.add_item(ОчиститьButton())

@bot.command(name="финансы")
async def финансы(ctx):
    embed = discord.Embed(
        title="Универсальный бот для учёта финансов",
        description="Теперь не придётся помнить о доходах и расходах — бот сделает это сам.",
        color=discord.Color.purple()
    )
    embed.set_image(url="https://i.imgur.com/jOmamcY.png")
    await ctx.send(embed=embed, view=FinanceView())

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} готов")
    bot.add_view(FinanceView())

keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])