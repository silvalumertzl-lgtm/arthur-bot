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
NOME_CARGO_SUPORTE = "Suporte"       # ← Nome EXATO do cargo
NOME_CARGO_CLIENTE = "Cliente VIP"   # ← Nome EXATO do cargo
palavras_proibidas = set()
compradores = {}

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} tá online!")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos registrados!")
    except Exception as e:
        print(f"❌ Erro: {e}")

# === SISTEMA DE TICKET — SUPORTE ENTRA SOZINHO ===
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

            # PEGA O CARGO DE SUPORTE
            cargo_suporte = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
            
            # PERMISSÕES — SUPORTE JÁ ENTRA VENDO E FALANDO
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),  # Todos os outros não veem
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),  # Quem abriu vê
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),  # O bot vê
            }
            
            # ✅ ADICIONA O CARGO DE SUPORTE AUTOMATICAMENTE
            if cargo_suporte:
                overwrites[cargo_suporte] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    embed_links=True,
                    attach_files=True
                )

            canal_ticket = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.name}",
                topic=f"Ticket de {interaction.user.name}",
                overwrites=overwrites
            )

            # Verifica se é Equipe ou Cliente
            e_equipe = (cargo_suporte and cargo_suporte in interaction.user.roles) or interaction.user.guild_permissions.administrator

            if e_equipe:
                embed_interno = discord.Embed(
                    title="🛡️ TICKET — EQUIPE",
                    description=f"Abrido por: {interaction.user.mention}\nFunção: **Equipe/Suporte**",
                    color=discord.Color.blue()
                )
            else:
                embed_interno = discord.Embed(
                    title="🎫 TICKET — CLIENTE",
                    description=f"Olá {interaction.user.mention}!\nExplique o que precisa que a equipe vai atender! 📩",
                    color=discord.Color.green()
                )

            class TicketFecharView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)

                @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.red, emoji="🔒", custom_id="fechar_ticket")
                async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                    cargo_sup = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
                    e_equipe_agora = (cargo_sup and cargo_sup in interaction.user.roles) or interaction.user.guild_permissions.administrator
                    e_dono = interaction.user.name in (canal_ticket.topic or "")

                    if not (e_dono or e_equipe_agora):
                        await interaction.response.send_message(
                            "❌ Apenas a equipe ou quem abriu pode fechar!",
                            ephemeral=True
                        )
                        return

                    await interaction.response.send_message("✅ Fechando...", ephemeral=True)
                    await canal_ticket.delete(reason=f"Fechado por {interaction.user}")

            await canal_ticket.send(embed=embed_interno, view=TicketFecharView())

            # AVISA A EQUIPE
            if cargo_suporte and not e_equipe:
                await canal_ticket.send(f"{cargo_suporte.mention} — Novo ticket aberto!")

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
    cargo_sup = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_sup and cargo_sup in interaction.user.roles) or interaction.user.guild_permissions.administrator

    if not tem_permissao:
        await interaction.response.send_message("❌ Apenas a Equipe pode cadastrar produtos!", ephemeral=True)
        return

    embed = discord.Embed(title=f"📦 {nome}", color=discord.Color.green())
    embed.add_field(name="💲 Preço", value=f"R$ {preco}", inline=True)
    embed.add_field(name="📦 Estoque", value=estoque, inline=True)
    embed.add_field(name="💳 PIX", value=f"`{pix}`", inline=False)
    embed.add_field(
        name="📩 Como receber",
        value="**Após pagar, abra um ticket para receber seu produto!**",
        inline=False
    )
    if imagem:
        embed.set_image(url=imagem)

    await interaction.response.send_message(embed=embed)

# === DAR CARGO DE CLIENTE ===
@bot.tree.command(name="dar-cliente", description="Dá cargo de cliente e registra compra")
@app_commands.describe(usuario="Pessoa que comprou")
async def dar_cliente(interaction: discord.Interaction, usuario: discord.Member):
    cargo_sup = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_sup and cargo_sup in interaction.user.roles) or interaction.user.guild_permissions.administrator

    if not tem_permissao:
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    cargo_cliente = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_CLIENTE)
    if not cargo_cliente:
        await interaction.response.send_message(
            f"⚠️ Cria o cargo **'{NOME_CARGO_CLIENTE}'** primeiro no Discord!",
            ephemeral=True
        )
        return

    if cargo_cliente not in usuario.roles:
        await usuario.add_roles(cargo_cliente)

    compradores[usuario.id] = compradores.get(usuario.id, 0) + 1

    await interaction.response.send_message(
        f"✅ {usuario.mention} recebeu o cargo de Cliente!\n🛒 Total de compras: **{compradores[usuario.id]}**",
        ephemeral=False
    )

# === RANKING ===
@bot.tree.command(name="ranking", description="Mostra quem mais comprou")
async def ranking(interaction: discord.Interaction):
    if not compradores:
        await interaction.response.send_message("📋 Nenhuma compra registrada ainda!", ephemeral=True)
        return

    top = sorted(compradores.items(), key=lambda x: x[1], reverse=True)[:10]

    embed = discord.Embed(title="🏆 RANKING — MAIS COMPRARAM", color=discord.Color.gold())
    for pos, (user_id, qtd) in enumerate(top, 1):
        user = await bot.fetch_user(user_id)
        medalha = {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, f"{pos}°")
        embed.add_field(
            name=f"{medalha} {user.name}",
            value=f"🛒 {qtd} compra{'s' if qtd>1 else ''}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# === LIMPAR CANAL ===
@bot.tree.command(name="limpar", description="Apaga TODAS as mensagens do canal")
async def limpar(interaction: discord.Interaction):
    cargo_sup = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_sup and cargo_sup in interaction.user.roles) or interaction.user.guild_permissions.administrator

    if not tem_permissao:
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    await interaction.response.send_message("⚠️ Apagando tudo em 5 segundos...", ephemeral=True)
    
    deleted = await interaction.channel.purge(limit=None)
    await interaction.channel.send(f"✅ Canal limpo! {len(deleted)} mensagens apagadas!", delete_after=5)

# === ANTI-PALAVRÃO ===
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    cargo_sup = discord.utils.get(message.guild.roles, name=NOME_CARGO_SUPORTE)
    if cargo_sup and cargo_sup in message.author.roles:
        return

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

# === BLOQUEAR PALAVRA ===
@bot.tree.command(name="bloquear-palavra", description="Bloqueia uma palavra")
@app_commands.describe(palavra="Palavra proibida")
async def bloquear_palavra(interaction: discord.Interaction, palavra: str):
    cargo_sup = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_sup and cargo_sup in interaction.user.roles) or interaction.user.guild_permissions.administrator

    if not tem_permissao:
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    palavras_proibidas.add(palavra.lower())
    await interaction.response.send_message(f"✅ Palavra **'{palavra}'** bloqueada!", ephemeral=True)

# === DESBLOQUEAR PALAVRA ===
@bot.tree.command(name="desbloquear-palavra", description="Libera uma palavra")
@app_commands.describe(palavra="Palavra para liberar")
async def desbloquear_palavra(interaction: discord.Interaction, palavra: str):
    cargo_sup = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_sup and cargo_sup in interaction.user.roles) or interaction.user.guild_permissions.administrator

    if not tem_permissao:
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    palavras_proibidas.discard(palavra.lower())
    await interaction.response.send_message(f"✅ Palavra **'{palavra}'** liberada!", ephemeral=True)

# === LISTAR PALAVRAS ===
@bot.tree.command(name="lista-bloqueadas", description="Mostra palavras bloqueadas")
async def lista_bloqueadas(interaction: discord.Interaction):
    cargo_sup = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_sup and cargo_sup in interaction.user.roles) or interaction.user.guild_permissions.administrator

    if not tem_permissao:
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    if not palavras_proibidas:
        await interaction.response.send_message("📋 Nenhuma palavra bloqueada!", ephemeral=True)
        return

    lista = "\n".join(f"• {p}" for p in palavras_proibidas)
    await interaction.response.send_message(f"📋 Palavras bloqueadas:\n{lista}", ephemeral=True)

# === LIGAR O BOT ===
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Token não encontrado!")
