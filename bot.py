import discord
from discord import app_commands
from discord.ext import commands
import os
import re

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === CONFIGURAÇÕES ===
NOME_CARGO_SUPORTE = "Suporte"  # ← Nome EXATO do cargo que criou
palavras_proibidas = set()

# === QUANDO LIGAR ===
@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} tá online!")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos registrados!")
    except Exception as e:
        print(f"❌ Erro: {e}")

# === SISTEMA DE TICKET ===
@bot.tree.command(name="setup-ticket", description="Coloca o sistema de ticket neste canal")
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Atendimento",
        description="Clique no botão abaixo para abrir seu ticket!",
        color=discord.Color.purple()
    )
    embed.set_footer(text="ARTHURMODS — Atendimento")

    class TicketAbrirView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, emoji="🎫", custom_id="abrir_ticket_novo")
        async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Verifica se já tem aberto
            for canal in interaction.guild.channels:
                if isinstance(canal, discord.TextChannel) and canal.topic == f"Ticket de {interaction.user.name}":
                    await interaction.response.send_message(
                        f"⚠️ Você já tem um ticket aberto: {canal.mention}",
                        ephemeral=True
                    )
                    return

            # Permissões do canal
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

            # Mensagem interna + botão de fechar
            embed_interno = discord.Embed(
                title="🎫 Ticket Aberto",
                description=f"Olá {interaction.user.mention}!\nExplique o que precisa que a equipe vai atender! 📩",
                color=discord.Color.green()
            )

            class TicketFecharView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)

                @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.red, emoji="🔒", custom_id="fechar_ticket")
                async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                    cargo_suporte = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
                    e_equipe = cargo_suporte and cargo_suporte in interaction.user.roles
                    e_dono = interaction.user.name in (canal_ticket.topic or "")

                    if not (e_dono or e_equipe):
                        await interaction.response.send_message(
                            "❌ Apenas a equipe ou quem abriu pode fechar!",
                            ephemeral=True
                        )
                        return

                    await interaction.response.send_message("✅ Fechando...", ephemeral=True)
                    await canal_ticket.delete(reason=f"Fechado por {interaction.user}")

            await canal_ticket.send(embed=embed_interno, view=TicketFecharView())

            # ✅ NOTIFICA O CARGO DE SUPORTE
            cargo = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
            if cargo:
                await canal_ticket.send(f"{cargo.mention} — Novo ticket aberto!")

            await interaction.response.send_message(
                f"✅ Ticket criado! → {canal_ticket.mention}",
                ephemeral=True
            )

    await interaction.response.send_message(embed=embed, view=TicketAbrirView())

# === SISTEMA DE PRODUTO ===
@bot.tree.command(name="novo-produto", description="Cadastra um produto novo")
@app_commands.describe(
    nome="Nome do produto",
    preco="Preço",
    estoque="Quantidade",
    pix="Chave PIX",
    imagem="Link da foto (opcional)"
)
async def novo_produto(
    interaction: discord.Interaction,
    nome: str,
    preco: str,
    estoque: str,
    pix: str,
    imagem: str = None
):
    # Verifica se tem cargo de Suporte OU é Administrador
    cargo_suporte = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_suporte and cargo_suporte in interaction.user.roles) or interaction.user.guild_permissions.administrator

    if not tem_permissao:
        await interaction.response.send_message(
            "❌ Apenas a Equipe/Suporte pode cadastrar produtos!",
            ephemeral=True
        )
        return

    embed = discord.Embed(title=f"📦 {nome}", color=discord.Color.green())
    embed.add_field(name="💲 Preço", value=f"R$ {preco}", inline=True)
    embed.add_field(name="📦 Estoque", value=estoque, inline=True)
    embed.add_field(name="💳 PIX", value=f"`{pix}`", inline=False)
    
    # ⚠️ MENSAGEM IMPORTANTE QUE TU PEDIU
    embed.add_field(
        name="📩 Como receber",
        value="**Após efetuar o pagamento, abra um ticket para receber seu produto!**",
        inline=False
    )

    if imagem:
        embed.set_image(url=imagem)

    await interaction.response.send_message(embed=embed)

# === SISTEMA ANTI-PALAVRÃO ===
@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Ignora mensagens do bot

    cargo_suporte = discord.utils.get(message.guild.roles, name=NOME_CARGO_SUPORTE) if message.guild else None
    if cargo_suporte and cargo_suporte in message.author.roles:
        return  # Equipe não é punida

    # Verifica se tem palavra proibida
    texto = message.content.lower()
    for palavra in palavras_proibidas:
        if re.search(re.escape(palavra.lower()), texto):
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} ⚠️ Palavra proibida detectada!",
                delete_after=3
            )
            break

    await bot.process_commands(message)

# === ADICIONAR PALAVRA PROIBIDA ===
@bot.tree.command(name="bloquear-palavra", description="Adiciona uma palavra proibida")
@app_commands.describe(palavra="Palavra que quer bloquear")
async def bloquear_palavra(interaction: discord.Interaction, palavra: str):
    cargo_suporte = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_suporte and cargo_suporte in interaction.user.roles) or interaction.user.guild_permissions.administrator

    if not tem_permissao:
        await interaction.response.send_message("❌ Apenas a Equipe pode usar isso!", ephemeral=True)
        return

    palavras_proibidas.add(palavra.lower())
    await interaction.response.send_message(f"✅ Palavra **'{palavra}'** foi bloqueada!", ephemeral=True)

# === REMOVER PALAVRA PROIBIDA ===
@bot.tree.command(name="desbloquear-palavra", description="Remove uma palavra da lista")
@app_commands.describe(palavra="Palavra que quer liberar")
async def desbloquear_palavra(interaction: discord.Interaction, palavra: str):
    cargo_suporte = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_suporte and cargo_suporte in interaction.user.roles) or interaction.user.guild_permissions.administrator

    if not tem_permissao:
        await interaction.response.send_message("❌ Apenas a Equipe pode usar isso!", ephemeral=True)
        return

    palavras_proibidas.discard(palavra.lower())
    await interaction.response.send_message(f"✅ Palavra **'{palavra}'** foi liberada!", ephemeral=True)

# === LISTAR PALAVRAS BLOQUEADAS ===
@bot.tree.command(name="lista-bloqueadas", description="Mostra todas as palavras bloqueadas")
async def lista_bloqueadas(interaction: discord.Interaction):
    cargo_suporte = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_suporte and cargo_suporte in interaction.user.roles) or interaction.user.guild_permissions.administrator

    if not tem_permissao:
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    if not palavras_proibidas:
        await interaction.response.send_message("📋 Nenhuma palavra bloqueada ainda!", ephemeral=True)
        return

    lista = "\n".join(f"• {p}" for p in palavras_proibidas)
    await interaction.response.send_message(f"📋 Palavras bloqueadas:\n{lista}", ephemeral=True)

# === LIGAR O BOT ===
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Token não encontrado!")
