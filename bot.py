import asyncio
import random
import os
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import nest_asyncio
import openai
from dotenv import load_dotenv
from apscheduler.util import timezone
import pytz

# Carrega variáveis de ambiente
load_dotenv()

# Configuração do bot
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TOKEN)
app = Application.builder().token(TOKEN).build()

# Chave da API da OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# IDs das pessoas autorizadas
DOMI_ID = 1007537544  # ID de Domi
TATI_ID = 7784216834  # ID de Tati
ADMIN_ID = DOMI_ID  # Apenas Domi pode mudar os modos

AUTHORIZED_USERS = [DOMI_ID, TATI_ID]

# Modos disponíveis
MODOS = {
    1: "Modo 1 - Apenas Tati pode ter **recompensas**, Domi é sub.",
    2: "Modo 2 - Ninguém pode ter **recompensas**, apenas provocações.",
    3: "Modo 3 - Apenas Domi pode ter **recompensas**, Tati não."
}
MODO_ATIVO = 1  # Começa no Modo 1 por padrão

# Pontuação
pontos = {DOMI_ID: 0, TATI_ID: 0}

# Dicionário para armazenar desafios pendentes
desafios_pendentes = {}

# Tarefas e compras para cada pessoa
tarefas_domi = ["Organizar os livros", "Preparar o jantar", "Escrever um poema", "Limpar a mesa", "Fazer meditação"]
tarefas_tati = ["Criar uma playlist", "Escolher um filme", "Planejar um final de semana", "Alongar", "Escrever uma história"]

compras_domi = ["Comprar flores", "Caderno novo", "Chá de camomila", "Marcador de livros", "Vela aromática"]
compras_tati = ["Comprar sobremesa", "Hidratante facial", "Livro de receitas", "Fone de ouvido", "Almofada confortável"]

DESAFIOS = {
    "domi": [
        "Domi, massageie Tati por 7 minutos.",
        "Domi, recite um poema para Tati.",
        "Domi, escreva uma carta para Tati.",
        "Domi, organize algo em casa.",
        "Domi, prepare um jantar especial."
    ],
    "tati": [
        "Tati, escolha algo para vocês fazerem juntos.",
        "Tati, planeje uma surpresa para Domi.",
        "Tati, escreva uma lista de metas.",
        "Tati, crie uma nova música.",
        "Tati, organize um dia relaxante para ambos."
    ]
}

async def send_challenge():
    """Envia desafios a cada 3 horas"""
    domi_desafio = random.choice(DESAFIOS["domi"])
    tati_desafio = random.choice(DESAFIOS["tati"])
    
    desafios_pendentes[DOMI_ID] = {"desafio": domi_desafio, "status": "pendente"}
    desafios_pendentes[TATI_ID] = {"desafio": tati_desafio, "status": "pendente"}
    
    await bot.send_message(chat_id=DOMI_ID, text=f"Seu desafio: {domi_desafio}\nEnvie 'OBEDECER' para aceitar.")
    await bot.send_message(chat_id=TATI_ID, text=f"Seu desafio: {tati_desafio}\nEnvie 'OBEDECER' para aceitar.")

    await asyncio.sleep(10800)  # 3 horas
    for user_id in [DOMI_ID, TATI_ID]:
        if desafios_pendentes.get(user_id, {}).get("status") == "pendente":
            pontos[user_id] -= 10
            await bot.send_message(chat_id=user_id, text="Você não aceitou o desafio. Perdeu 10 pontos.")

async def obey(update, context):
    """Usuário aceita o desafio"""
    user_id = update.message.from_user.id
    if user_id not in desafios_pendentes or desafios_pendentes[user_id]["status"] != "pendente":
        return await update.message.reply_text("Sem desafios pendentes ou já aceitos.")
    
    desafios_pendentes[user_id]["status"] = "aceito"
    pontos[user_id] += 10
    other_id = DOMI_ID if user_id == TATI_ID else TATI_ID
    await bot.send_message(chat_id=other_id, text="A domme exige sua presença para o desafio.")
    await update.message.reply_text("Desafio aceito. Você ganhou 10 pontos.")

async def show_points(update, context):
    """Exibe a pontuação"""
    await update.message.reply_text(f"Pontos de Domi: {pontos[DOMI_ID]}\nPontos de Tati: {pontos[TATI_ID]}")

async def set_mode(update: Update, context):
    """Muda o modo"""
    global MODO_ATIVO
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return await update.message.reply_text("Sem permissão para mudar os modos.")
    try:
        novo_modo = int(context.args[0])
        if novo_modo not in MODOS:
            raise ValueError
        MODO_ATIVO = novo_modo
        await update.message.reply_text(f"Modo alterado para: {MODOS[MODO_ATIVO]}")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso: /modo <1, 2 ou 3>")

async def show_lists(update, context):
    """Mostra listas de tarefas e compras"""
    user_id = update.message.from_user.id
    if user_id == DOMI_ID:
        tarefas = tarefas_domi
        compras = compras_domi
    elif user_id == TATI_ID:
        tarefas = tarefas_tati
        compras = compras_tati
    else:
        return await update.message.reply_text("Acesso negado.")
    
    tarefas_str = "\n".join(f"- {t}" for t in tarefas)
    compras_str = "\n".join(f"- {c}" for c in compras)
    await update.message.reply_text(f"Tarefas:\n{tarefas_str}\n\nCompras:\n{compras_str}")

async def handle_message(update, context):
    """Interação com a OpenAI"""
    user_message = update.message.text
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é Domme N.Y.X.I.A., misteriosa e envolvente."},
                {"role": "user", "content": user_message}
            ]
        )
        bot_reply = response["choices"][0]["message"]["content"]
        await update.message.reply_text(bot_reply)
    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")

# Configuração do bot
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CommandHandler("obey", obey))
app.add_handler(CommandHandler("points", show_points))
app.add_handler(CommandHandler("modo", set_mode))
app.add_handler(CommandHandler("showlists", show_lists))

async def main():
    scheduler = AsyncIOScheduler(timezone=pytz.UTC)
    scheduler.add_job(send_challenge, "interval", hours=3)
    scheduler.start()
    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())