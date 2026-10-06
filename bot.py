import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

produtos = {}
chaves = {}

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    print("🔥 Sistema de Vendas Ativo!")

@bot.command(name="criar_produto")
async def criar_produto(ctx, nome, preco):
    produtos[nome] = {"preco": preco, "dono": ctx.author.id}
    await ctx.send(f"✅ Produto **{nome}** criado! Preço: R$ {preco}")

@bot.command(name="gerar_chave")
async def gerar_chave(ctx, nome_produto):
    if nome_produto in produtos:
        import random, string
        chave = f"ARTHUR-{nome_produto}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
        chaves[chave] = {"produto": nome_produto, "comprador": ctx.author.id}
        await ctx.author.send(f"🔑 Sua chave: `{chave}`\nProduto: {nome_produto}")
        await ctx.send(f"✅ Chave gerada e enviada por mensagem privada!")
    else:
        await ctx.send("❌ Produto não encontrado!")

@bot.command(name="validar")
async def validar(ctx, chave):
    if chave in chaves:
        await ctx.send(f"✅ Chave VÁLIDA!\nProduto: {chaves[chave]['produto']}")
    else:
        await ctx.send("❌ Chave INVÁLIDA ou não existe!")

@bot.command(name="lista_produtos")
async def lista_produtos(ctx):
    if produtos:
        msg = "📦 Produtos disponíveis:\n"
        for nome, dados in produtos.items():
            msg += f"• {nome} — R$ {dados['preco']}\n"
        await ctx.send(msg)
    else:
        await ctx.send("📭 Nenhum produto cadastrado!")

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("⚠️ Coloque seu token nas variáveis do Render!")
