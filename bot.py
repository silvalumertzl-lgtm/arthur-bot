import discord
from discord import app_commands
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} tá online!")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos registrados!")
    except Exception as e:
        print(f"❌ Erro: {e}")

# === SETUP-TICKET — PRONTO, SÓ USAR ===
@bot.tree.command(name="setup-ticket", description="Coloca o sistema de ticket neste canal")
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Atendimento",
        description="Clique no botão abaixo para abrir seu ticket!",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Sistema de Atendimento")

    class TicketView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, emoji="🎫", custom_id="abrir_ticket")
        async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Verifica se já tem aberto
            for canal in interaction.guild.channels:
                if isinstance(canal, discord.TextChannel) and canal.topic == f"Ticket de {interaction.user.name}":
                    await interaction.response.send_message(
                        f"⚠️ Você já tem um ticket aberto: {canal.mention}",
                        ephemeral=True
                    )
                    return

            # Cria o canal do ticket
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            canal_ticket = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.name}",
                topic=f"Ticket de {interaction.user.name}",
                overwrites=overwrites
            )

            await canal_ticket.send(
                f"Olá {interaction.user.mention}! 📩\n"
                "Explique o que você precisa que a equipe vai te responder em breve!"
            )
            await interaction.response.send_message(
                f"✅ Ticket criado! → {canal_ticket.mention}",
                ephemeral=True
            )

    await interaction.response.send_message(embed=embed, view=TicketView())

# === NOVO PRODUTO — PREENCHE TUDO DIRETO NO DISCORD ===
@bot.tree.command(name="novo-produto", description="Cadastra um produto novo")
@app_commands.describe(
    nome="Nome do produto",
    preco="Preço do produto",
    estoque="Quantidade disponível",
    pix="Chave PIX para pagamento",
    imagem="Link da imagem do produto"
)
async def novo_produto(
    interaction: discord.Interaction,
    nome: str,
    preco: str,
    estoque: str,
    pix: str,
    imagem: str = None
):
    embed = discord.Embed(
        title=f"📦 {nome}",
        color=discord.Color.green()
    )
    embed.add_field(name="💲 Preço", value=f"R$ {preco}", inline=True)
    embed.add_field(name="📦 Estoque", value=estoque, inline=True)
    embed.add_field(name="💳 PIX", value=f"`{pix}`", inline=False)
    
    if imagem:
        embed.set_image(url=imagem)

    await interaction.response.send_message(embed=embed)
    print(f"✅ Produto '{nome}' cadastrado no canal {interaction.channel.name}")

# === LIGAR O BOT ===
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Token não encontrado!")
