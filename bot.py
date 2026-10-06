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

# === ONDE VAI FICAR SALVO TUDO ===
PASTA_DADOS = "dados_sistema"
ARQUIVO_TICKETS = os.path.join(PASTA_DADOS, "tickets_salvos.json")
ARQUIVO_PRODUTOS = os.path.join(PASTA_DADOS, "produtos_salvos.json")
ARQUIVO_COMPRAS = os.path.join(PASTA_DADOS, "compras_salvas.json")

# === CRIAR PASTA SE NÃO EXISTIR ===
if not os.path.exists(PASTA_DADOS):
    os.makedirs(PASTA_DADOS)
    print(f"📁 Pasta criada: {PASTA_DADOS}")

# === CARREGAR DADOS SALVOS ===
def carregar(arquivo, padrao):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao

tickets = carregar(ARQUIVO_TICKETS, [])
produtos = carregar(ARQUIVO_PRODUTOS, {})
compras = carregar(ARQUIVO_COMPRAS, {})

# === SALVAR E MOSTRAR NO RENDER ===
def salvar_ticket(dados):
    tickets.append(dados)
    with open(ARQUIVO_TICKETS, "w", encoding="utf-8") as f:
        json.dump(tickets, f, ensure_ascii=False, indent=2)
    print(f"\n🎫 TICKET CRIADO E SALVO ✅")
    print(f"   Usuário: {dados['usuario_nome']}")
    print(f"   Canal: {dados['canal_nome']}")
    print(f"   ID Canal: {dados['canal_id']}")
    print(f"   Data: {dados['data']}")
    print(f"   Arquivo: {ARQUIVO_TICKETS}\n")

def salvar_produto(dados):
    produtos[dados["id"]] = dados
    with open(ARQUIVO_PRODUTOS, "w", encoding="utf-8") as f:
        json.dump(produtos, f, ensure_ascii=False, indent=2)
    print(f"\n📦 PRODUTO CRIADO E SALVO ✅")
    print(f"   ID: {dados['id']}")
    print(f"   Nome: {dados['nome']}")
    print(f"   Preço: R$ {dados['preco']:.2f}")
    print(f"   Estoque: {dados['estoque']}")
    print(f"   Arquivo: {ARQUIVO_PRODUTOS}\n")

def salvar_compra(dados):
    compras[dados["usuario_id"]] = compras.get(dados["usuario_id"], 0) + 1
    with open(ARQUIVO_COMPRAS, "w", encoding="utf-8") as f:
        json.dump(compras, f, ensure_ascii=False, indent=2)
    print(f"\n🛒 COMPRA REGISTRADA E SALVA ✅")
    print(f"   Usuário: {dados['usuario_nome']}")
    print(f"   Total: {compras[dados['usuario_id']]}")
    print(f"   Arquivo: {ARQUIVO_COMPRAS}\n")

# === CONFIGURAÇÕES ===
NOME_SUPORTE = "Suporte"
NOME_CLIENTE = "Cliente VIP"

@bot.event
async def on_ready():
    print(f"\n{'='*50}")
    print(f"✅ BOT ONLINE — {bot.user}")
    print(f"📦 Produtos salvos: {len(produtos)}")
    print(f"🎫 Tickets salvos: {len(tickets)}")
    print(f"👤 Compradores salvos: {len(compras)}")
    print(f"📂 Pasta de dados: {PASTA_DADOS}/")
    print(f"{'='*50}\n")
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos prontos!\n")
    except Exception as e:
        print(f"⚠️ Sincronização: {e}\n")

# === 1️⃣ ABRIR TICKET — SALVA TUDO ===
@bot.tree.command(name="abrir-ticket", description="Abrir atendimento")
async def abrir_ticket(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    # Verificar se já tem aberto
    for canal in interaction.guild.channels:
        if isinstance(canal, discord.TextChannel) and canal.topic == f"Ticket de {interaction.user.name}":
            await interaction.followup.send(f"⚠️ Já tem aberto: {canal.mention}", ephemeral=True)
            return
    
    cargo_sup = discord.utils.get(interaction.guild.roles, name=NOME_SUPORTE)
    perm = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        bot.user: discord.PermissionOverwrite(read_messages=True)
    }
    if cargo_sup:
        perm[cargo_sup] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    
    canal_ticket = await interaction.guild.create_text_channel(
        f"ticket-{interaction.user.name}",
        topic=f"Ticket de {interaction.user.name}",
        overwrites=perm
    )
    
    # SALVAR TICKET E MOSTRAR NO RENDER
    dados_ticket = {
        "usuario_nome": interaction.user.name,
        "usuario_id": interaction.user.id,
        "canal_nome": canal_ticket.name,
        "canal_id": canal_ticket.id,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "status": "aberto"
    }
    salvar_ticket(dados_ticket)
    
    await canal_ticket.send(f"✅ Bem-vindo, {interaction.user.mention}!\nExplique o que precisa.")
    if cargo_sup:
        await canal_ticket.send(f"{cargo_sup.mention} — Novo ticket!")
    
    await interaction.followup.send(f"✅ Criado: {canal_ticket.mention}", ephemeral=True)

# === 2️⃣ CADASTRAR PRODUTO — SALVA TUDO ===
@bot.tree.command(name="novo-produto", description="Cadastrar produto")
@app_commands.describe(nome="Nome", preco="Valor", estoque="Quantidade", pix="Chave PIX", imagem="Link da foto")
async def novo_produto(inter: discord.Interaction, nome: str, preco: float, estoque: int, pix: str, imagem: str=None):
    cargo_sup = discord.utils.get(inter.guild.roles, name=NOME_SUPORTE)
    if not ((cargo_sup and cargo_sup in inter.user.roles) or inter.user.guild_permissions.administrator):
        await inter.response.send_message("❌ Sem permissão!", ephemeral=True)
        return
    
    pid = f"prod_{len(produtos)+1}"
    dados_produto = {
        "id": pid,
        "nome": nome,
        "preco": preco,
        "estoque": estoque,
        "pix": pix,
        "imagem": imagem,
        "criado_por": inter.user.name,
        "data_criacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }
    
    salvar_produto(dados_produto)
    
    emb = discord.Embed(title=f"📦 {nome}", color=discord.Color.green())
    emb.add_field(name="Preço", value=f"R$ {preco:.2f}", inline=True)
    emb.add_field(name="Estoque", value=f"{estoque} unidades", inline=True)
    emb.add_field(name="PIX", value=f"`{pix}`", inline=False)
    emb.set_footer(text=f"ID: {pid} — Salvo em dados_sistema/")
    if imagem:
        emb.set_image(url=imagem)
    
    await inter.channel.send(embed=emb)
    await inter.response.send_message("✅ Produto salvo! 💾", ephemeral=True)

# === 3️⃣ DAR CLIENTE — SALVA COMPRA ===
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
    
    dados_compra = {
        "usuario_nome": usuario.name,
        "usuario_id": usuario.id
    }
    salvar_compra(dados_compra)
    
    await inter.response.send_message(
        f"✅ {usuario.mention}\n🛒 Total: {compras[usuario.id]}\n💾 Salvo!",
        ephemeral=False
    )

# === 4️⃣ RANKING ===
@bot.tree.command(name="ranking", description="Ver ranking de compras")
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

# === LIGAR ===
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Token não encontrado!")
