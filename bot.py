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
if not os.path.exists(PASTA):
    os.makedirs(PASTA)

ARQ_PRODUTOS = os.path.join(PASTA, "produtos.json")
ARQ_TICKETS = os.path.join(PASTA, "tickets.json")
ARQ_CLIENTES = os.path.join(PASTA, "clientes.json")
ARQ_CONFIG = os.path.join(PASTA, "config.json")

def carregar(arquivo, padrao):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao

produtos = carregar(ARQ_PRODUTOS, {})
tickets = carregar(ARQ_TICKETS, [])
clientes = carregar(ARQ_CLIENTES, {})
config = carregar(ARQ_CONFIG, {
    "cargo_suporte": "Suporte",
    "chave_pix": "",
    "nome_conta_pix": ""
})

NOME_SUPORTE = config["cargo_suporte"]

def salvar_tudo():
    with open(ARQ_PRODUTOS, "w", encoding="utf-8") as f:
        json.dump(produtos, f, ensure_ascii=False, indent=2)
    with open(ARQ_TICKETS, "w", encoding="utf-8") as f:
        json.dump(tickets, f, ensure_ascii=False, indent=2)
    with open(ARQ_CLIENTES, "w", encoding="utf-8") as f:
        json.dump(clientes, f, ensure_ascii=False, indent=2)
    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"💾 SALVO! Prod:{len(produtos)} | Tickets:{len(tickets)} | Clientes:{len(clientes)}\n")

@bot.event
async def on_ready():
    print(f"\n{'='*50}")
    print(f"✅ BOT ONLINE — {bot.user}")
    print(f"📦 Produtos: {len(produtos)} | 🎫 Tickets: {len(tickets)} | 👤 Clientes: {len(clientes)}")
    print(f"{'='*50}\n")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos prontos!\n")
    except Exception as e:
        print(f"⚠️ Erro: {e}")

# ==================================================
# 🔧 CONFIGURAR PIX
# ==================================================
@bot.tree.command(name="config-pix", description="Configurar chave PIX")
@app_commands.describe(chave="Chave PIX", nome_conta="Nome da conta")
async def config_pix(inter: discord.Interaction, chave: str, nome_conta: str):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM!", ephemeral=True)
        return
    config["chave_pix"] = chave
    config["nome_conta_pix"] = nome_conta
    salvar_tudo()
    await inter.response.send_message(
        f"✅ PIX CONFIGURADO!\n🔑 `{chave}`\n👤 {nome_conta}",
        ephemeral=True
    )

# ==================================================
# 🎫 BOTÕES DO TICKET
# ==================================================
class BotoesTicket(discord.ui.View):
    def __init__(self, usuario_id, produto_nome=None):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id
        self.produto_nome = produto_nome

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.red, emoji="❌")
    async def cancelar(self, i: discord.Interaction, btn):
        if str(i.user.id) == self.usuario_id or i.user.guild_permissions.administrator:
            await i.channel.edit(name=f"cancelado-{i.channel.name}")
            await i.response.send_message("❌ Ticket cancelado!", ephemeral=False)
            for t in tickets:
                if t.get("canal") == i.channel.id:
                    t["status"] = "cancelado"
                    t["fechado_por"] = i.user.name
            salvar_tudo()
            self.stop()
        else:
            await i.response.send_message("❌ Só o dono ou ADM pode cancelar!", ephemeral=True)

    @discord.ui.button(label="✅ Finalizar", style=discord.ButtonStyle.green, emoji="✅")
    async def finalizar(self, i: discord.Interaction, btn):
        if i.user.guild_permissions.administrator:
            await i.response.send_message("✅ Ticket finalizado! Obrigado! 💜", ephemeral=False)
            for t in tickets:
                if t.get("canal") == i.channel.id:
                    t["status"] = "finalizado"
                    t["fechado_por"] = i.user.name
            salvar_tudo()
            self.stop()
        else:
            await i.response.send_message("❌ Só ADM pode finalizar!", ephemeral=True)

# ==================================================
# 🎫 SETUP TICKET — Coloca a mensagem pra abrir
# ==================================================
@bot.tree.command(name="setup-ticket", description="Colocar mensagem de abrir ticket")
async def setup_ticket(inter: discord.Interaction):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM!", ephemeral=True)
        return

    emb = discord.Embed(
        title="🎫 ATENDIMENTO",
        description="Clique no botão abaixo para abrir seu ticket!",
        color=discord.Color.purple()
    )

    class BotaoAbrirTicket(discord.ui.View):
        @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, emoji="🎫")
        async def abrir(self, i: discord.Interaction, btn):
            await i.response.defer(ephemeral=True)
            for canal in i.guild.channels:
                if isinstance(canal, discord.TextChannel) and canal.topic == f"Ticket de {i.user.name}":
                    await i.followup.send(f"⚠️ Já tem aberto: {canal.mention}", ephemeral=True)
                    return

            perm = {
                i.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                bot.user: discord.PermissionOverwrite(read_messages=True)
            }
            if (sup := discord.utils.get(i.guild.roles, name=NOME_SUPORTE)):
                perm[sup] = discord.PermissionOverwrite(read_messages=True)

            canal = await i.guild.create_text_channel(
                f"ticket-{i.user.name[:6]}",
                topic=f"Ticket de {i.user.name}",
                overwrites=perm
            )
            tickets.append({
                "tipo": "suporte",
                "usuario": i.user.name,
                "canal": canal.id,
                "status": "aberto",
                "data": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            salvar_tudo()

            await canal.send(
                f"✅ Bem-vindo, {i.user.mention}!\nExplique o que precisa.",
                view=BotoesTicket(str(i.user.id))
            )
            await i.followup.send(f"✅ Criado: {canal.mention}", ephemeral=True)

    await inter.response.send_message(embed=emb, view=BotaoAbrirTicket())

# ==================================================
# 📦 NOVO PRODUTO — Tu cadastra e aparece pra comprar
# ==================================================
@bot.tree.command(name="novo-produto", description="Criar novo produto")
@app_commands.describe(nome="Nome do produto", preco="Valor R$", descricao="O que é", imagem="Link da foto")
async def novo_produto(inter: discord.Interaction, nome: str, preco: float, descricao: str, imagem: str=None):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM cadastra!", ephemeral=True)
        return
    if not config.get("chave_pix"):
        await inter.response.send_message("❌ Configure /config-pix primeiro!", ephemeral=True)
        return

    pid = f"prod_{len(produtos)+1}"
    produtos[pid] = {
        "id": pid,
        "nome": nome,
        "preco": preco,
        "descricao": descricao,
        "imagem": imagem
    }
    salvar_tudo()

    emb = discord.Embed(title=f"📦 {nome}", description=descricao, color=discord.Color.green())
    emb.add_field(name="💰 Preço", value=f"R$ {preco:.2f}", inline=False)
    if imagem:
        emb.set_image(url=imagem)

    class BotaoComprar(discord.ui.View):
        @discord.ui.button(label="💳 Comprar Agora", style=discord.ButtonStyle.green, emoji="🛒")
        async def comprar(self, i: discord.Interaction, btn):
            emb_pix = discord.Embed(title="💳 PAGAMENTO", description=f"Comprando: **{nome}**", color=discord.Color.gold())
            emb_pix.add_field(name="💰 Valor", value=f"R$ {preco:.2f}", inline=False)
            emb_pix.add_field(name="👤 Conta", value=config["nome_conta_pix"], inline=False)
            emb_pix.add_field(name="🔑 PIX", value=f"`{config['chave_pix']}`", inline=False)

            class Acoes(discord.ui.View):
                @discord.ui.button(label="📋 Copiar PIX", style=discord.ButtonStyle.primary)
                async def copiar(self, i2: discord.Interaction, btn2):
                    await i2.response.send_message(
                        f"📋 **Chave PIX:**\n`{config['chave_pix']}`\n\n💰 R$ {preco:.2f}",
                        ephemeral=True
                    )

                @discord.ui.button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.green)
                async def abrir_ticket_compra(self, i2: discord.Interaction, btn2):
                    await i2.response.defer(ephemeral=True)
                    for ch in i2.guild.channels:
                        if isinstance(ch, discord.TextChannel) and ch.topic == f"Compra: {nome} | {i2.user.name}":
                            await i2.followup.send(f"✅ Já aberto: {ch.mention}", ephemeral=True)
                            return

                    perm = {
                        i2.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        i2.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                        bot.user: discord.PermissionOverwrite(read_messages=True)
                    }
                    if (sup := discord.utils.get(i2.guild.roles, name=NOME_SUPORTE)):
                        perm[sup] = discord.PermissionOverwrite(read_messages=True)

                    canal = await i2.guild.create_text_channel(
                        f"compra-{i2.user.name[:6]}",
                        topic=f"Compra: {nome} | Cliente: {i2.user.name}",
                        overwrites=perm
                    )
                    tickets.append({
                        "tipo": "compra",
                        "usuario": i2.user.name,
                        "produto": nome,
                        "valor": preco,
                        "canal": canal.id,
                        "status": "aberto",
                        "data": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                    # Conta cliente
                    clientes[str(i2.user.id)] = clientes.get(str(i2.user.id), 0) + 1
                    salvar_tudo()

                    await canal.send(
                        f"✅ Olá {i2.user.mention}!\n"
                        f"📦 **Produto:** {nome}\n"
                        f"💰 **Valor:** R$ {preco:.2f}\n\n"
                        f"📋 **Envie o comprovante aqui!**",
                        view=BotoesTicket(str(i2.user.id), nome)
                    )
                    await i2.followup.send(f"✅ Ticket criado: {canal.mention}", ephemeral=True)

            await i.response.send_message(embed=emb_pix, view=Acoes(), ephemeral=True)

    await inter.channel.send(embed=emb, view=BotaoComprar())
    await inter.response.send_message(f"✅ Produto criado! ✨", ephemeral=True)

# ==================================================
# 👤 VER CLIENTES — Quem comprou
# ==================================================
@bot.tree.command(name="clientes", description="Ver lista de clientes")
async def ver_clientes(inter: discord.Interaction):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM!", ephemeral=True)
        return
    if not clientes:
        await inter.response.send_message("⚠️ Nenhum cliente ainda!", ephemeral=True)
        return

    texto = ""
    total = 0
    for uid, qtd in clientes.items():
        texto += f"• <@{uid}> — {qtd} compra(s)\n"
        total += qtd

    emb = discord.Embed(title="👤 CLIENTES", description=texto, color=discord.Color.purple())
    emb.add_field(name="Total de compras", value=str(total), inline=False)
    await inter.response.send_message(embed=emb, ephemeral=True)

# ==================================================
# 💾 SALVAR TUDO
# ==================================================
@bot.tree.command(name="salvar-tudo", description="Salvar tudo manualmente")
async def salvar(inter: discord.Interaction):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM!", ephemeral=True)
        return
    salvar_tudo()
    await inter.response.send_message(
        f"✅ SALVO! 💾\n"
        f"📦 Produtos: {len(produtos)}\n"
        f"🎫 Tickets: {len(tickets)}\n"
        f"👤 Clientes: {len(clientes)}",
        ephemeral=True
    )

# === LIGAR ===
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Token não encontrado!")
