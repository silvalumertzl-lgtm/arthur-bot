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
NOME_CARGO_SUPORTE = "Suporte"
NOME_CARGO_CLIENTE = "Cliente VIP"
palavras_proibidas = set()
compradores = {}
produtos = {}

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} tá online!")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos prontos!")
    except Exception as e:
        print(f"❌ Erro: {e}")

# === 1️⃣ SISTEMA DE TICKET ===
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
            for canal in interaction.guild.channels:
                if isinstance(canal, discord.TextChannel) and canal.topic == f"Ticket de {interaction.user.name}":
                    await interaction.response.send_message(
                        f"⚠️ Você já tem um ticket aberto: {canal.mention}",
                        ephemeral=True
                    )
                    return

            cargo_suporte = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            if cargo_suporte:
                overwrites[cargo_suporte] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_messages=True
                )

            canal_ticket = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.name}",
                topic=f"Ticket de {interaction.user.name}",
                overwrites=overwrites
            )

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
                        await interaction.response.send_message("❌ Apenas a equipe ou quem abriu pode fechar!", ephemeral=True)
                        return
                    await interaction.response.send_message("✅ Fechando...", ephemeral=True)
                    await canal_ticket.delete(reason=f"Fechado por {interaction.user}")

            await canal_ticket.send(embed=embed_interno, view=TicketFecharView())
            if cargo_suporte and not e_equipe:
                await canal_ticket.send(f"{cargo_suporte.mention} — Novo ticket aberto!")
            await interaction.response.send_message(f"✅ Ticket criado! → {canal_ticket.mention}", ephemeral=True)

    await interaction.response.send_message(embed=embed, view=TicketAbrirView())

# === 2️⃣ SISTEMA DE PRODUTO ===
@bot.tree.command(name="novo-produto", description="Cadastra um produto novo")
@app_commands.describe(
    nome="Nome do produto",
    preco="Preço unitário (ex: 50 ou 2.50)",
    estoque="Quantidade disponível",
    pix="Chave PIX para pagamento",
    imagem="Link da foto (opcional)"
)
async def novo_produto(
    interaction: discord.Interaction,
    nome: str,
    preco: float,
    estoque: int,
    pix: str,
    imagem: str = None
):
    cargo_sup = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_sup and cargo_sup in interaction.user.roles) or interaction.user.guild_permissions.administrator
    if not tem_permissao:
        await interaction.response.send_message("❌ Apenas a Equipe pode cadastrar produtos!", ephemeral=True)
        return

    produto_id = f"prod_{len(produtos) + 1}"
    produtos[produto_id] = {
        "nome": nome,
        "preco": preco,
        "estoque": estoque,
        "pix": pix,
        "imagem": imagem
    }

    embed = discord.Embed(title=f"📦 {nome}", color=discord.Color.green())
    embed.add_field(name="💲 Preço Unitário", value=f"R$ {preco:.2f}", inline=True)
    embed.add_field(name="📦 Estoque Disponível", value=f"{estoque} unidades", inline=True)
    embed.add_field(name="💳 PIX", value=f"`{pix}`", inline=False)
    embed.add_field(
        name="📩 Como receber",
        value="**Após pagar, abra um ticket para receber seu produto!**",
        inline=False
    )
    embed.set_footer(text=f"ID: {produto_id} — Clique abaixo para comprar")
    if imagem:
        embed.set_image(url=imagem)

    class ComprarView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="🛒 Comprar Agora", style=discord.ButtonStyle.green, custom_id=f"comprar_{produto_id}")
        async def comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
            prod = produtos.get(produto_id)
            if not prod or prod["estoque"] <= 0:
                await interaction.response.send_message("❌ Produto esgotado!", ephemeral=True)
                return

            class QuantidadeModal(discord.ui.Modal, title="Quantidade"):
                quantidade = discord.ui.TextInput(
                    label="Quantas unidades você quer?",
                    placeholder=f"Disponível: {prod['estoque']}",
                    min_length=1,
                    max_length=2,
                    required=True
                )

                async def on_submit(self, modal_interaction: discord.Interaction):
                    try:
                        qtd = int(self.quantidade.value)
                    except ValueError:
                        await modal_interaction.response.send_message("❌ Digite apenas números!", ephemeral=True)
                        return
                    if qtd <= 0:
                        await modal_interaction.response.send_message("❌ Quantidade inválida!", ephemeral=True)
                        return
                    if qtd > prod["estoque"]:
                        await modal_interaction.response.send_message(
                            f"❌ Só temos {prod['estoque']} unidades disponíveis!",
                            ephemeral=True
                        )
                        return

                    total = prod["preco"] * qtd
                    prod["estoque"] -= qtd

                    embed_pagamento = discord.Embed(title="✅ PEDIDO REALIZADO", color=discord.Color.gold())
                    embed_pagamento.add_field(name="📦 Produto", value=prod["nome"], inline=False)
                    embed_pagamento.add_field(name="🔢 Quantidade", value=f"{qtd} unidade{'s' if qtd>1 else ''}", inline=True)
                    embed_pagamento.add_field(name="💲 Valor Unitário", value=f"R$ {prod['preco']:.2f}", inline=True)
                    embed_pagamento.add_field(name="💰 TOTAL A PAGAR", value=f"**R$ {total:.2f}**", inline=False)
                    embed_pagamento.add_field(name="💳 Chave PIX", value=f"`{prod['pix']}`", inline=False)
                    embed_pagamento.add_field(
                        name="📩 Instruções",
                        value="Após pagar, abra um ticket e envie o comprovante!",
                        inline=False
                    )
                    await modal_interaction.response.send_message(embed=embed_pagamento, ephemeral=True)

            await interaction.response.send_modal(QuantidadeModal())

    await interaction.channel.send(embed=embed, view=ComprarView())
    await interaction.response.send_message("✅ Produto publicado!", ephemeral=True)

# === 3️⃣ DAR CARGO DE CLIENTE ===
@bot.tree.command(name="dar-cliente", description="Dá cargo de cliente e conta compra")
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

# === 4️⃣ RANKING ===
@bot.tree.command(name="ranking", description="Mostra quem mais comprou")
async def ranking(interaction: discord.Interaction):
    if not compradores:
        await interaction.response.send_message("📋 Nenhuma compra registrada ainda!", ephemeral=True)
        return

    top = sorted(compradores.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 RANKING — MAIS COMPRARAM", color=discord.Color.gold())
    embed.set_footer(text="ARTHURMODS — Top 10 Compradores")
    for pos, (user_id, qtd) in enumerate(top, 1):
        user = await bot.fetch_user(user_id)
        medalha = {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, f"{pos}°")
        embed.add_field(
            name=f"{medalha} {user.name}",
            value=f"🛒 {qtd} compra{'s' if qtd>1 else ''}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

# === 5️⃣ LIMPAR CANAL ===
@bot.tree.command(name="limpar", description="Apaga TUDO somente neste canal")
async def limpar(interaction: discord.Interaction):
    cargo_sup = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_SUPORTE)
    tem_permissao = (cargo_sup and cargo_sup in interaction.user.roles) or interaction.user.guild_permissions.administrator
    if not tem_permissao:
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    await interaction.response.send_message("⚠️ Apagando TUDO deste canal...", ephemeral=True)
    deleted = await interaction.channel.purge(limit=None)
    await interaction.channel.send(
        f"✅ **Canal limpo!**\n📍 Canal: **{interaction.channel.name}**\n📝 {len(deleted)} mensagens apagadas!",
        delete_after=5
    )

# === 6️⃣ ANTI-PALAVRÃO ===
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

# === LISTAR PALAVRAS BLOQUEADAS ===
@bot.tree.command(name="lista-bloqueadas", description="Mostra todas as palavras bloqueadas")
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
