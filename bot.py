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

ARQ_PRODUTOS = os.path.join(PASTA, "loja_produtos.json")
ARQ_TICKETS = os.path.join(PASTA, "tickets.json")
ARQ_FILAS = os.path.join(PASTA, "apostas_filas.json")
ARQ_CONFIG = os.path.join(PASTA, "config.json")

def carregar(arquivo, padrao):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao

produtos = carregar(ARQ_PRODUTOS, {})
tickets = carregar(ARQ_TICKETS, [])
filas = carregar(ARQ_FILAS, {"normal": {}, "infinito": {}})
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
    with open(ARQ_FILAS, "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=2)
    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"💾 SALVO! Prod:{len(produtos)} | Tickets:{len(tickets)} | Filas:OK\n")

@bot.event
async def on_ready():
    print(f"\n{'='*60}")
    print(f"✅ BOT ONLINE — {bot.user}")
    print(f"🛒 Loja: {len(produtos)} produtos | 🎫 Tickets: {len(tickets)}")
    print(f"⚔️ Apostas — Normal:{len(filas['normal'])} | Infinito:{len(filas['infinito'])}")
    print(f"{'='*60}\n")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos prontos!\n")
    except Exception as e:
        print(f"⚠️ Erro: {e}")

# ==================================================
# 🔧 CONFIG PIX
# ==================================================
@bot.tree.command(name="config-pix", description="Configurar chave PIX da loja")
@app_commands.describe(chave="Chave PIX", nome_conta="Nome da conta")
async def config_pix(inter: discord.Interaction, chave: str, nome_conta: str):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM!", ephemeral=True)
        return
    config["chave_pix"] = chave
    config["nome_conta_pix"] = nome_conta
    salvar_tudo()
    await inter.response.send_message(f"✅ PIX configurado!\n🔑 `{chave}`\n👤 {nome_conta}", ephemeral=True)

# ==================================================
# 🎫 BOTÕES DO TICKET — CANCELAR / FINALIZAR
# ==================================================
class BotoesTicketLoja(discord.ui.View):
    def __init__(self, usuario_id):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.red, emoji="❌")
    async def cancelar(self, i: discord.Interaction, btn):
        # Cliente pode cancelar
        if str(i.user.id) == self.usuario_id or i.user.guild_permissions.administrator:
            await i.channel.edit(name=f"fechado-{i.channel.name}", overwrites=None)
            await i.response.send_message("❌ Ticket cancelado! Canal fechado.", ephemeral=False)
            for t in tickets:
                if t.get("canal") == i.channel.id:
                    t["status"] = "cancelado"
                    t["fechado_por"] = i.user.name
                    t["data_fechamento"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            salvar_tudo()
            self.stop()
        else:
            await i.response.send_message("❌ Só o dono ou ADM pode cancelar!", ephemeral=True)

    @discord.ui.button(label="✅ Finalizar", style=discord.ButtonStyle.green, emoji="✅")
    async def finalizar(self, i: discord.Interaction, btn):
        # SÓ ADM finaliza
        if i.user.guild_permissions.administrator:
            await i.response.send_message("✅ Ticket finalizado! Obrigado pela preferência! 💜", ephemeral=False)
            for t in tickets:
                if t.get("canal") == i.channel.id:
                    t["status"] = "finalizado"
                    t["fechado_por"] = i.user.name
                    t["data_fechamento"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            salvar_tudo()
            self.stop()
        else:
            await i.response.send_message("❌ Apenas ADM pode finalizar!", ephemeral=True)

class BotoesTicketAposta(discord.ui.View):
    def __init__(self, usuario_id):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id

    @discord.ui.button(label="❌ Cancelar Fila", style=discord.ButtonStyle.red, emoji="❌")
    async def cancelar_fila(self, i: discord.Interaction, btn):
        if str(i.user.id) == self.usuario_id or i.user.guild_permissions.administrator:
            await i.channel.edit(name=f"cancelado-{i.channel.name}")
            await i.response.send_message("❌ Fila/Ticket cancelado!", ephemeral=False)
            for t in tickets:
                if t.get("canal") == i.channel.id:
                    t["status"] = "cancelado"
                    t["fechado_por"] = i.user.name
            salvar_tudo()
            self.stop()
        else:
            await i.response.send_message("❌ Sem permissão!", ephemeral=True)

    @discord.ui.button(label="🏆 Partida Concluída", style=discord.ButtonStyle.green, emoji="🏆")
    async def concluir(self, i: discord.Interaction, btn):
        if i.user.guild_permissions.administrator:
            await i.response.send_message("🏆 Partida registrada! Obrigado a todos! ⚔️", ephemeral=False)
            for t in tickets:
                if t.get("canal") == i.channel.id:
                    t["status"] = "concluido"
                    t["fechado_por"] = i.user.name
            salvar_tudo()
            self.stop()
        else:
            await i.response.send_message("❌ Só ADM confirma resultado!", ephemeral=True)

# ==================================================
# 🛒 LOJA
# ==================================================
@bot.tree.command(name="cadastrar-produto", description="Adicionar produto")
@app_commands.describe(nome="Nome", preco="Valor", descricao="Info", imagem="Link da foto")
async def cad_prod(inter: discord.Interaction, nome: str, preco: float, descricao: str, imagem: str=None):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM!", ephemeral=True)
        return
    if not config.get("chave_pix"):
        await inter.response.send_message("❌ Configure /config-pix primeiro!", ephemeral=True)
        return
    pid = f"prod_{len(produtos)+1}"
    produtos[pid] = {"id":pid,"nome":nome,"preco":preco,"descricao":descricao,"imagem":imagem}
    salvar_tudo()
    await inter.response.send_message(f"✅ Produto: {nome} | R${preco:.2f}", ephemeral=True)

@bot.tree.command(name="loja", description="Ver produtos")
async def ver_loja(inter: discord.Interaction):
    if not produtos:
        await inter.response.send_message("⚠️ Nenhum produto!", ephemeral=True)
        return
    await inter.response.defer()
    for pid, p in produtos.items():
        emb = discord.Embed(title=f"📦 {p['nome']}", description=p["descricao"], color=discord.Color.green())
        emb.add_field(name="💰 Preço", value=f"R$ {p['preco']:.2f}", inline=False)
        if p["imagem"]: emb.set_image(url=p["imagem"])

        class BotaoComprar(discord.ui.View):
            @discord.ui.button(label="💳 Comprar Agora", style=discord.ButtonStyle.green)
            async def comprar(self, i: discord.Interaction, btn):
                emb_pix = discord.Embed(title="💳 PAGAMENTO", description=f"Produto: {p['nome']}", color=discord.Color.gold())
                emb_pix.add_field(name="Valor", value=f"R$ {p['preco']:.2f}", inline=False)
                emb_pix.add_field(name="PIX", value=f"`{config['chave_pix']}`", inline=False)
                emb_pix.add_field(name="Conta", value=config["nome_conta_pix"], inline=False)

                class AcoesCompra(discord.ui.View):
                    @discord.ui.button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.green)
                    async def abrir_ticket_compra(self, i2: discord.Interaction, btn2):
                        await i2.response.defer(ephemeral=True)
                        for ch in i2.guild.channels:
                            if isinstance(ch, discord.TextChannel) and ch.topic == f"Compra: {p['nome']} | {i2.user.name}":
                                await i2.followup.send(f"✅ Já aberto: {ch.mention}", ephemeral=True)
                                return

                        perm = {i2.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                i2.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                                bot.user: discord.PermissionOverwrite(read_messages=True)}
                        if (sup := discord.utils.get(i2.guild.roles, name=NOME_SUPORTE)):
                            perm[sup] = discord.PermissionOverwrite(read_messages=True)

                        canal = await i2.guild.create_text_channel(
                            f"compra-{i2.user.name[:6]}",
                            topic=f"Compra: {p['nome']} | Cliente: {i2.user.name}",
                            overwrites=perm
                        )
                        tickets.append({
                            "tipo": "compra", "usuario": i2.user.name, "produto": p['nome'],
                            "valor": p['preco'], "canal": canal.id, "status": "aberto",
                            "data": datetime.now().strftime("%d/%m/%Y %H:%M")
                        })
                        salvar_tudo()

                        await canal.send(
                            f"✅ Olá {i2.user.mention}!\n📦 **{p['nome']}** — R$ {p['preco']:.2f}\n\n"
                            f"📋 Envie o comprovante aqui!",
                            view=BotoesTicketLoja(str(i2.user.id))
                        )
                        await i2.followup.send(f"✅ Ticket: {canal.mention}", ephemeral=True)

                await i.response.send_message(embed=emb_pix, view=AcoesCompra(), ephemeral=True)

        await inter.channel.send(embed=emb, view=BotaoComprar())
    await inter.followup.send("✅ Loja carregada!", ephemeral=True)

# ==================================================
# ⚔️ APOSTAS — FILAS COM TICKET
# ==================================================
@bot.tree.command(name="menu-filas", description="Botões de fila de apostas")
async def menu_filas(inter: discord.Interaction):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM!", ephemeral=True)
        return

    emb = discord.Embed(title="⚔️ ESCOLHA SEU MODO", color=discord.Color.blue())
    emb.add_field(name="❄️ Gelo Normal", value="Regras padrão", inline=True)
    emb.add_field(name="🔥 Gelo Infinito", value="Gelo nunca acaba", inline=True)
    emb.set_footer(text="Só forma par com o mesmo modo!")

    class BotoesFila(discord.ui.View):
        async def criar_canal_partida(self, i: discord.Interaction, modo_nome, modo_chave):
            uid = str(i.user.id)
            if uid in filas[modo_chave]:
                await i.response.send_message("⚠️ Já está na fila!", ephemeral=True)
                return
            # Sair da outra fila
            outra = "infinito" if modo_chave == "normal" else "normal"
            if uid in filas[outra]: del filas[outra][uid]

            if filas[modo_chave]:
                outro_id = list(filas[modo_chave].keys())[0]
                del filas[modo_chave][outro_id]

                # Categoria
                cat = next((c for c in i.guild.categories if c.name == "📋 COMBINAR REGRAS"), None)
                if not cat: cat = await i.guild.create_category("📋 COMBINAR REGRAS")

                canal = await i.guild.create_text_channel(f"partida-{modo_nome[:5]}-{i.user.name[:4]}", category=cat)
                await canal.set_permissions(i.guild.default_role, read_messages=False)
                await canal.set_permissions(i.user, read_messages=True)
                om = i.guild.get_member(int(outro_id))
                if om: await canal.set_permissions(om, read_messages=True)
                if (sup := discord.utils.get(i.guild.roles, name=NOME_SUPORTE)):
                    await canal.set_permissions(sup, read_messages=True)

                tickets.append({
                    "tipo": "aposta", "modo": modo_nome, "jogador1": outro_id, "jogador2": uid,
                    "canal": canal.id, "status": "aberto", "data": datetime.now().strftime("%d/%m/%Y %H:%M")
                })
                salvar_tudo()

                emb_ch = discord.Embed(title=f"⚔️ PARTIDA — {modo_nome}", color=discord.Color.orange())
                emb_ch.add_field(name="Jogador 1", value=f"<@{outro_id}>", inline=True)
                emb_ch.add_field(name="Jogador 2", value=i.user.mention, inline=True)
                emb_ch.add_field(name="📋 Combinem as regras!", value="Depois avisem o resultado!", inline=False)
                await canal.send(embed=emb_ch, view=BotoesTicketAposta(str(uid)))
                await i.response.send_message(f"✅ Partida formada! {canal.mention}", ephemeral=True)
            else:
                filas[modo_chave][uid] = i.user.name
                salvar_tudo()
                await i.response.send_message(f"✅ Entrou na fila! Aguarde adversário...", ephemeral=True)

        @discord.ui.button(label="❄️ Gelo Normal", style=discord.ButtonStyle.primary)
        async def normal(self, i: discord.Interaction, btn):
            await self.criar_canal_partida(i, "Gelo Normal", "normal")

        @discord.ui.button(label="🔥 Gelo Infinito", style=discord.ButtonStyle.danger)
        async def infinito(self, i: discord.Interaction, btn):
            await self.criar_canal_partida(i, "Gelo Infinito", "infinito")

    await inter.response.send_message(embed=emb, view=BotoesFila())

@bot.tree.command(name="sair-fila", description="Sair da fila")
async def sair_fila(inter: discord.Interaction):
    uid = str(inter.user.id)
    saida = []
    for m in ["normal", "infinito"]:
        if uid in filas[m]:
            del filas[m][uid]
            saida.append("❄️Normal" if m=="normal" else "🔥Infinito")
    if saida:
        salvar_tudo()
        await inter.response.send_message(f"✅ Saiu: {', '.join(saida)}", ephemeral=True)
    else:
        await inter.response.send_message("⚠️ Não está em fila!", ephemeral=True)

# ==================================================
# 💾 SALVAR TUDO
# ==================================================
@bot.tree.command(name="salvar-tudo", description="Salvar tudo")
async def salvar(inter: discord.Interaction):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Só ADM!", ephemeral=True)
        return
    salvar_tudo()
    await inter.response.send_message(f"✅ SALVO! Prod:{len(produtos)} | Tickets:{len(tickets)}", ephemeral=True)

token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Token não encontrado!")
