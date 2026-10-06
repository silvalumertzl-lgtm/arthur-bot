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

# === PASTAS E ARQUIVOS ===
PASTA = "dados_sistema"
if not os.path.exists(PASTA):
    os.makedirs(PASTA)

ARQ_PRODUTOS = os.path.join(PASTA, "produtos.json")
ARQ_TICKETS = os.path.join(PASTA, "tickets.json")
ARQ_CLIENTES = os.path.join(PASTA, "clientes.json")
ARQ_RANK = os.path.join(PASTA, "rank.json")

def carregar(arquivo, padrao):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao

produtos = carregar(ARQ_PRODUTOS, {})
tickets = carregar(ARQ_TICKETS, [])
clientes = carregar(ARQ_CLIENTES, {})
rank = carregar(ARQ_RANK, {})

NOME_SUPORTE = "Suporte"

# === SALVA AUTOMÁTICO SEMPRE ===
def salvar_tudo():
    with open(ARQ_PRODUTOS, "w", encoding="utf-8") as f:
        json.dump(produtos, f, ensure_ascii=False, indent=2)
    with open(ARQ_TICKETS, "w", encoding="utf-8") as f:
        json.dump(tickets, f, ensure_ascii=False, indent=2)
    with open(ARQ_CLIENTES, "w", encoding="utf-8") as f:
        json.dump(clientes, f, ensure_ascii=False, indent=2)
    with open(ARQ_RANK, "w", encoding="utf-8") as f:
        json.dump(rank, f, ensure_ascii=False, indent=2)
    print(f"💾 SALVO AUTOMÁTICO! Prod:{len(produtos)} | Tickets:{len(tickets)} | Clientes:{len(clientes)}\n")

@bot.event
async def on_ready():
    print(f"\n{'='*50}")
    print(f"✅ BOT ONLINE — {bot.user}")
    print(f"📦 Produtos: {len(produtos)} | 🎫 Tickets: {len(tickets)}")
    print(f"👤 Clientes: {len(clientes)} | 🏆 Rank: {len(rank)}")
    print(f"💾 Salvamento automático ATIVADO")
    print(f"{'='*50}\n")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos prontos!\n")
    except Exception as e:
        print(f"⚠️ Erro: {e}")

# ==================================================
# 🧹 LIMPAR CANAL
# ==================================================
@bot.tree.command(name="limpar", description="Apagar mensagens do canal")
@app_commands.describe(quantidade="Número de mensagens (padrão: 100)")
async def limpar(inter: discord.Interaction, quantidade: int = 100):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM!", ephemeral=True)
        return
    await inter.response.defer()
    await inter.channel.purge(limit=quantidade)
    await inter.followup.send(f"✅ Apagadas {quantidade} mensagens!", ephemeral=True)

# ==================================================
# 🎫 BOTÕES DO TICKET
# ==================================================
class BotoesTicket(discord.ui.View):
    def __init__(self, usuario_id):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.red, emoji="❌")
    async def cancelar(self, i: discord.Interaction, btn):
        if str(i.user.id) == self.usuario_id or i.user.guild_permissions.administrator:
            await i.channel.edit(name=f"fechado-{i.channel.name}")
            await i.response.send_message("❌ Ticket cancelado!", ephemeral=False)
            for t in tickets:
                if t.get("canal") == i.channel.id:
                    t["status"] = "cancelado"
                    t["fechado_por"] = i.user.name
            salvar_tudo()
            self.stop()
        else:
            await i.response.send_message("❌ Sem permissão!", ephemeral=True)

    @discord.ui.button(label="✅ Finalizar", style=discord.ButtonStyle.green, emoji="✅")
    async def finalizar(self, i: discord.Interaction, btn):
        if i.user.guild_permissions.administrator:
            await i.response.send_message("✅ Ticket finalizado! Obrigado! 💜", ephemeral=False)
            for t in tickets:
                if t.get("canal") == i.channel.id:
                    t["status"] = "finalizado"
                    t["fechado_por"] = i.user.name
            # Adiciona no rank do atendente
            uid = str(i.user.id)
            rank[uid] = rank.get(uid, {"nome": i.user.name, "atendimentos": 0})
            rank[uid]["atendimentos"] += 1
            rank[uid]["nome"] = i.user.name
            salvar_tudo()
            self.stop()
        else:
            await i.response.send_message("❌ Só ADM finaliza!", ephemeral=True)

# ==================================================
# 🎫 SETUP TICKET — BOTÃO PRA ABRIR
# ==================================================
@bot.tree.command(name="setup-ticket", description="Colocar mensagem de abrir ticket")
async def setup_ticket(inter: discord.Interaction):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM!", ephemeral=True)
        return

    emb = discord.Embed(
        title="🎫 ATENDIMENTO",
        description="Clique no botão abaixo para abrir seu ticket!\nNossa equipe vai te atender em breve! 💜",
        color=discord.Color.purple()
    )

    class BotaoAbrirTicket(discord.ui.View):
        @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, emoji="🎫")
        async def abrir(self, i: discord.Interaction, btn):
            await i.response.defer(ephemeral=True)
            for canal in i.guild.channels:
                if isinstance(canal, discord.TextChannel) and canal.topic == f"Ticket de {i.user.name}":
                    await i.followup.send(f"⚠️ Já aberto: {canal.mention}", ephemeral=True)
                    return

            perm = {
                i.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                bot.user: discord.PermissionOverwrite(read_messages=True)
            }
            cargo_sup = discord.utils.get(i.guild.roles, name=NOME_SUPORTE)
            if cargo_sup:
                perm[cargo_sup] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

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

            # Avisa a equipe
            mensagem_equipe = f"📢 **NOVO TICKET ABERTO!**\n👤 Cliente: {i.user.mention}"
            if cargo_sup:
                mensagem_equipe = f"{cargo_sup.mention} {mensagem_equipe}"

            await canal.send(
                mensagem_equipe + f"\n\n✅ Bem-vindo, {i.user.mention}!\nExplique o que precisa.",
                view=BotoesTicket(str(i.user.id))
            )
            await i.followup.send(f"✅ Criado: {canal.mention}", ephemeral=True)

    await inter.response.send_message(embed=emb, view=BotaoAbrirTicket())

# ==================================================
# 📦 NOVO PRODUTO — TUDO JUNTO AQUI
# ==================================================
@bot.tree.command(name="novo-produto", description="Criar novo produto com PIX")
@app_commands.describe(
    nome="Nome do produto",
    preco="Valor R$",
    descricao="O que é",
    imagem="Link da foto",
    chave_pix="Chave PIX pra pagamento",
    nome_conta_pix="Nome da conta PIX"
)
async def novo_produto(inter: discord.Interaction, nome: str, preco: float, descricao: str, imagem: str, chave_pix: str, nome_conta_pix: str):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM cadastra!", ephemeral=True)
        return

    pid = f"prod_{len(produtos)+1}"
    produtos[pid] = {
        "id": pid,
        "nome": nome,
        "preco": preco,
        "descricao": descricao,
        "imagem": imagem,
        "chave_pix": chave_pix,
        "nome_conta_pix": nome_conta_pix
    }
    salvar_tudo()

    emb = discord.Embed(title=f"📦 {nome}", description=descricao, color=discord.Color.green())
    emb.add_field(name="💰 Preço", value=f"R$ {preco:.2f}", inline=False)
    emb.set_image(url=imagem)

    class BotaoComprar(discord.ui.View):
        @discord.ui.button(label="💳 Comprar Agora", style=discord.ButtonStyle.green, emoji="🛒")
        async def comprar(self, i: discord.Interaction, btn):
            prod = produtos[pid]
            emb_pix = discord.Embed(title="💳 PAGAMENTO", description=f"Comprando: **{prod['nome']}**", color=discord.Color.gold())
            emb_pix.add_field(name="💰 Valor", value=f"R$ {prod['preco']:.2f}", inline=False)
            emb_pix.add_field(name="👤 Conta", value=prod["nome_conta_pix"], inline=False)
            emb_pix.add_field(name="🔑 Chave PIX", value=f"`{prod['chave_pix']}`", inline=False)

            class AcoesCompra(discord.ui.View):
                @discord.ui.button(label="📋 Copiar PIX", style=discord.ButtonStyle.primary)
                async def copiar(self, i2: discord.Interaction, btn2):
                    await i2.response.send_message(
                        f"📋 **Chave PIX:**\n`{prod['chave_pix']}`\n\n💰 Valor: R$ {prod['preco']:.2f}\n👤 {prod['nome_conta_pix']}",
                        ephemeral=True
                    )

                @discord.ui.button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.green)
                async def abrir_ticket_compra(self, i2: discord.Interaction, btn2):
                    await i2.response.defer(ephemeral=True)
                    for ch in i2.guild.channels:
                        if isinstance(ch, discord.TextChannel) and ch.topic == f"Compra: {prod['nome']} | {i2.user.name}":
                            await i2.followup.send(f"✅ Já aberto: {ch.mention}", ephemeral=True)
                            return

                    perm = {
                        i2.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        i2.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                        bot.user: discord.PermissionOverwrite(read_messages=True)
                    }
                    cargo_sup = discord.utils.get(i2.guild.roles, name=NOME_SUPORTE)
                    if cargo_sup:
                        perm[cargo_sup] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                    canal = await i2.guild.create_text_channel(
                        f"compra-{i2.user.name[:6]}",
                        topic=f"Compra: {prod['nome']} | Cliente: {i2.user.name}",
                        overwrites=perm
                    )
                    tickets.append({
                        "tipo": "compra",
                        "usuario": i2.user.name,
                        "produto": prod['nome'],
                        "valor": prod['preco'],
                        "canal": canal.id,
                        "status": "aberto",
                        "data": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                    # Conta cliente
                    clientes[str(i2.user.id)] = clientes.get(str(i2.user.id), 0) + 1
                    salvar_tudo()

                    mensagem = f"✅ Olá {i2.user.mention}!\n📦 **{prod['nome']}** — R$ {prod['preco']:.2f}\n\n📋 Envie o comprovante aqui!"
                    if cargo_sup:
                        mensagem = f"{cargo_sup.mention} 🔔 NOVA COMPRA!\n" + mensagem

                    await canal.send(mensagem, view=BotoesTicket(str(i2.user.id)))
                    await i2.followup.send(f"✅ Ticket: {canal.mention}", ephemeral=True)

            await i.response.send_message(embed=emb_pix, view=AcoesCompra(), ephemeral=True)

    await inter.channel.send(embed=emb, view=BotaoComprar())
    await inter.response.send_message(f"✅ Produto criado com PIX! ✨", ephemeral=True)

# ==================================================
# 👤 CLIENTES — Quem comprou
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
    total_compras = 0
    for uid, qtd in clientes.items():
        texto += f"• <@{uid}> — {qtd} compra(s)\n"
        total_compras += qtd

    emb = discord.Embed(title="👤 CLIENTES", description=texto, color=discord.Color.purple())
    emb.add_field(name="Total de compras", value=str(total_compras), inline=False)
    await inter.response.send_message(embed=emb, ephemeral=True)

# ==================================================
# 🏆 RANK — Atendentes
# ==================================================
@bot.tree.command(name="rank", description="Ver ranking dos atendentes")
async def ver_rank(inter: discord.Interaction):
    if not rank:
        await inter.response.send_message("⚠️ Ninguém no rank ainda!", ephemeral=True)
        return

    # Ordena do maior pro menor
    lista = sorted(rank.items(), key=lambda x: x[1]["atendimentos"], reverse=True)

    texto = ""
    posicao = 1
    medalhas = ["🥇", "🥈", "🥉"]
    for uid, dados in lista:
        medalha = medalhas[posicao-1] if posicao <= 3 else f"{posicao}."
        texto += f"{medalha} {dados['nome']} — {dados['atendimentos']} atendimentos\n"
        posicao += 1

    emb = discord.Embed(title="🏆 RANKING DE ATENDIMENTO", description=texto, color=discord.Color.gold())
    emb.set_footer(text="Quem mais finalizou tickets aparece aqui!")
    await inter.response.send_message(embed=emb, ephemeral=False)

# === LIGAR O BOT ===
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Token não encontrado!")
