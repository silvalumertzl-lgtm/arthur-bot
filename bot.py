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
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos registrados!")
    except Exception as e:
        print(f"❌ Erro: {e}")

# === SEUS COMANDOS AQUI ===
@bot.tree.command(name="setup-ticket", description="Cria o sistema de ticket")
async def setup_ticket(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Sistema de ticket criado!", ephemeral=True)

@bot.tree.command(name="produto", description="Ver produtos")
async def produto(interaction: discord.Interaction):
    await interaction.response.send_message("📦 Produtos disponíveis...", ephemeral=False)
# === FIM DOS COMANDOS ===

# === INICIO CORRETO ===
token = os.getenv("DISCORD_TOKEN")

if token:
    @bot.event
    async def setup_hook():
        pass  # os comandos já foram registrados acima
    
    bot.run(token)  # ✅ AQUI É O CERTO! NÃO USA await bot.start()
else:
    print("❌ Token não encontrado nas variáveis de ambiente!")
