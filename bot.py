import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === PASTAS ===
PASTA = "dados_sistema"
PASTA_BACKUPS = os.path.join(PASTA, "backups_automáticos")

if not os.path.exists(PASTA):
    os.makedirs(PASTA)
    print(f"📁 Pasta criada: {PASTA}")
if not os.path.exists(PASTA_BACKUPS):
    os.makedirs(PASTA_BACKUPS)
    print(f"📁 Pasta de backups: {PASTA_BACKUPS}")

ARQ_TICKETS = os.path.join(PASTA, "tickets.json")
ARQ_PRODUTOS = os.path.join(PASTA, "produtos.json")
ARQ_COMPRAS = os.path.join(PASTA, "compras.json")

# === CARREGAR ===
def carregar(arquivo, padrao):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao

tickets = carregar(ARQ_TICKETS, [])
produtos = carregar(ARQ_PRODUTOS, {})
compras = carregar(ARQ_COMPRAS, {})

# === SALVAR ===
def salvar_ticket(dados):
    tickets.append(dados)
    with open(ARQ_TICKETS, "w", encoding="utf-8") as f:
        json.dump(tickets, f, ensure_ascii=False, indent=2)
    print(f"🎫 Ticket salvo: {dados['usuario']}")

def salvar_produto(dados):
    produtos[dados["id"]] = dados
    with open(ARQ_PRODUTOS, "w", encoding="utf-8") as f:
        json.dump(produtos, f, ensure_ascii=False, indent=2)
    print(f"📦 Produto salvo: {dados['nome']}")

def salvar_compras():
    with open(ARQ_COMPRAS, "w", encoding="utf-8") as f:
        json.dump(compras, f, ensure_ascii=False, indent=2)

# === BACKUP AUTOMÁTICO ===
def fazer_backup_automático():
    data = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    tudo = {
        "data_backup": data,
        "tickets": tickets,
        "produtos": produtos,
        "compras": compras
    }
    caminho = os.path.join(PASTA_BACKUPS, f"backup_{data}.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(tudo, f, ensure_ascii=False, indent=2)
    print(f"\n💾 BACKUP AUTOMÁTICO FEITO! ✅")
    print(f"📂 Arquivo: backups_automáticos/backup_{data}.json\n")

# === CONFIGS ===
NOME_SUPORTE = "Suporte"
NOME_CLIENTE = "Cliente VIP"

@bot.event
async def on_ready():
    print(f"\n{'='*45}")
    print(f"✅ BOT ONLINE — {bot.user}")
    
    # 🔹 FAZ BACKUP AUTOMÁTICO AO LIGAR!
    fazer_backup_automático()
    
    print(f"🎫 Tickets: {len(tickets)} | 📦 Produtos: {len(produtos)} | 👤 Compras: {len(compras)}")
    print(f"{'='*45}\n")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos prontos!\n")
    except Exception as e:
        print(f"⚠️ Sinc: {e}")

# === 1️⃣ ATENDIMENTO COM BOTÃO ===
@bot.tree.command(name="atendimento", description="Coloca a mensagem de atendimento")
async def atendimento(interaction: discord.Interaction):
    cargo_sup = discord.utils.get(interaction.guild.roles, name=NOME_SUPORTE)
    if not ((cargo_sup and cargo_sup in interaction.user.roles) or interaction.user.guild_permissions.administrator):
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎫 ARTHUR MODS — ATENDIMENTO",
        description="Clique no botão abaixo para abrir seu ticket!",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Estamos prontos para te atender! 💜")

    class BotaoAtendimento(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, emoji="🎫")
        async def abrir(self, inter: discord.Interaction, button):
            await inter.response.defer(ephemeral=True)
            
            for canal in inter.guild.channels:
                if isinstance(canal, discord.TextChannel) and canal.topic == f"Ticket de {inter.user.name}":
                    await inter.followup.send(f"⚠️ Já tem aberto: {canal.mention}", ephemeral=True)
                    return

            perm = {
                inter.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                inter.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                bot.user: discord.PermissionOverwrite(read_messages=True)
            }
            if cargo_sup:
                perm[cargo_sup] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            canal = await inter.guild.create_text_channel(
                f"ticket-{inter.user.name}",
                topic=f"Ticket de {inter.user.name}",
                overwrites=perm
            )

            dados = {
                "usuario": inter.user.name,
                "usuario_id": inter.user.id,
                "canal": canal.name,
                "canal_id": canal.id,
                "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
            salvar_ticket(dados)

            await canal.send(f"✅ Bem-vindo, {inter.user.mention}!\nExplique o que precisa! 💜")
            if cargo_sup:
                await canal.send(f"{cargo_sup.mention} — Novo ticket!")

            await inter.followup.send(f"✅ Criado: {canal.mention}", ephemeral=True)

    await interaction.response.send_message(embed=embed, view=BotaoAtendimento())

# === 2️⃣ NOVO PRODUTO ===
@bot.tree.command(name="novo-produto", description="Cadastrar produto")
@app_commands.describe(nome="Nome", preco="Valor", estoque="Quantidade", pix="Chave PIX", imagem="Link da foto")
async def novo_produto(inter: discord.Interaction, nome: str, preco: float, estoque: int, pix: str, imagem: str=None):
    cargo_sup = discord.utils.get(inter.guild.roles, name=NOME_SUPORTE)
    if not ((cargo_sup and cargo_sup in inter.user.roles) or inter.user.guild_permissions.administrator):
        await inter.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    pid = f"prod_{len(produtos)+1}"
    dados = {
        "id": pid, "nome": nome, "preco": preco, "estoque": estoque,
        "pix": pix, "imagem": imagem,
        "criado_por": inter.user.name,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }
    salvar_produto(dados)

    emb = discord.Embed(title=f"📦 {nome}", color=discord.Color.green())
    emb.add_field(name="Preço", value=f"R$ {preco:.2f}", inline=True)
    emb.add_field(name="Estoque", value=f"{estoque} unidades", inline=True)
    emb.add_field(name="PIX", value=f"`{pix}`", inline=False)
    emb.set_footer(text=f"ID: {pid} — Salvo ✅")
    if imagem: emb.set_image(url=imagem)

    await inter.channel.send(embed=emb)
    await inter.response.send_message("✅ Produto salvo! 💾", ephemeral=True)

# === 3️⃣ DAR CLIENTE ===
@bot.tree.command(name="dar-cliente", description="Registrar compra")
@app_commands.describe(usuario="Quem comprou")
async def dar_cliente(inter: discord.Interaction, usuario: discord.Member):
    cargo_sup = discord.utils.get(inter.guild.roles, name=NOME_SUPORTE)
    if not ((cargo_sup and cargo_sup in inter.user.roles) or inter.user.guild_permissions.administrator):
        await inter.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    cargo_cli = discord.utils.get(inter.guild.roles, name=NOME_CLIENTE)
    if not cargo_cli:
        await inter.response.send_message(f"⚠️ Cria o cargo '{NOME_CLIENTE}'!", ephemeral=True)
        return

    if cargo_cli not in usuario.roles:
        await usuario.add_roles(cargo_cli)

    compras[usuario.id] = compras.get(usuario.id, 0) + 1
    salvar_compras()

    await inter.response.send_message(
        f"✅ {usuario.mention}\n🛒 Total: {compras[usuario.id]}\n💾 Salvo!",
        ephemeral=False
    )

# === 4️⃣ RANKING ===
@bot.tree.command(name="ranking", description="Ver ranking")
async def ranking(inter: discord.Interaction):
    if not compras:
        await inter.response.send_message("📋 Nenhuma compra ainda!", ephemeral=True)
        return
    top = sorted(compras.items(), key=lambda x: x[1], reverse=True)[:10]
    emb = discord.Embed(title="🏆 RANKING", color=discord.Color.gold())
    for pos, (uid, qtd) in enumerate(top, 1):
        user = await bot.fetch_user(uid)
        med = {1:"🥇",2:"🥈",3:"🥉"}.get(pos, f"{pos}°")
        emb.add_field(name=f"{med} {user.name}", value=f"🛒 {qtd} compra{'s' if qtd>1 else ''}", inline=False)
    await inter.response.send_message(embed=emb)

# === 5️⃣ BACKUP MANUAL — BAIXAR NO CELULAR 📱===
@bot.tree.command(name="backup", description="Baixar backup completo")
async def backup(inter: discord.Interaction):
    cargo_sup = discord.utils.get(inter.guild.roles, name=NOME_SUPORTE)
    if not ((cargo_sup and cargo_sup in inter.user.roles) or inter.user.guild_permissions.administrator):
        await inter.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    data = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    nome_arq = f"backup_completo_{data}.json"

    tudo = {
        "data_backup": data,
        "tickets": tickets,
        "produtos": produtos,
        "compras": compras
    }

    caminho = os.path.join(PASTA, nome_arq)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(tudo, f, ensure_ascii=False, indent=2)

    arquivo = discord.File(caminho, filename=nome_arq)

    emb = discord.Embed(title="💾 BACKUP COMPLETO", color=discord.Color.gold())
    emb.add_field(name="🎫 Tickets", value=str(len(tickets)), inline=True)
    emb.add_field(name="📦 Produtos", value=str(len(produtos)), inline=True)
    emb.add_field(name="👤 Compradores", value=str(len(compras)), inline=True)

    await inter.response.send_message(embed=emb, file=arquivo, ephemeral=True)
    print(f"💾 Backup baixado por: {inter.user.name}")

# === LIGAR ===
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Token não encontrado!")
