import discord
from discord import app_commands
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} tá online!")
    # Registra os comandos
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos registrados!")
    except Exception as e:
        print(f"❌ Erro ao registrar: {e}")

# Coloca SEUS comandos aqui
@bot.tree.command(name="setup-ticket", description="Cria o sistema de ticket")
async def setup_ticket(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Sistema de ticket configurado!", ephemeral=True)

@bot.tree.command(name="produto", description="Ver produto")
async def produto(interaction: discord.Interaction):
    await interaction.response.send_message("📦 Produtos disponíveis...", ephemeral=False)

# Token
token = os.getenv("DISCORD_TOKEN")
if token:
    await bot.start(token)
else:
    print("❌ Token não encontrado!")
