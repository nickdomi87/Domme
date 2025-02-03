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

# Tarefas, compras e missões fictícias
TAREFAS = {
    DOMI_ID: ["Lavar a louça", "Organizar o armário", "Escrever um poema", "Fazer um chá", "Ler um capítulo de livro"],
    TATI_ID: ["Planejar a próxima semana", "Praticar meditação", "Fazer uma lista de desejos", "Criar uma playlist", "Escrever no diário"]
}

COMPRAS = {
    DOMI_ID: ["Comprar flores", "Adquirir um livro novo", "Comprar um bolo", "Adquirir chá exótico", "Comprar velas aromáticas"],
    TATI_ID: ["Comprar um novo diário", "Adquirir um hidratante", "Comprar chocolate", "Comprar café especial", "Adquirir um acessório de moda"]
}

MISSOES = {
    DOMI_ID: ["Massagear Tati por 10 minutos", "Escrever uma carta de amor", "Criar uma lista de 5 coisas para surpreender Tati", "Fazer um jantar especial", "Cantar uma música"],
    TATI_ID: ["Escolher uma punição para Domi", "Planejar um momento especial", "Escolher um filme para assistir juntas", "Escrever uma história curta", "Praticar algo novo"]
}

# Mensagens personalizadas para o Modo 1
NYXIA_RESPONSES = {
    "domi": [
        "Domi... sua única função hoje é garantir a satisfação de Tati. Nada mais importa.",
        "Suas vontades não fazem parte do jogo hoje. Apenas as dela.",
        "Espero que esteja pronta para servi-la sem hesitar.",
    ],
    "tati": [
        "Tati, você tem o controle absoluto hoje. Faça valer a pena.",
        "Domi existe para te satisfazer. Não precisa ser generosa.",
        "Hoje, só a sua **recompensa** importa.",
    ]
}

# Sistema de desafios a cada 3 horas
async def send_challenge():
    """Envia desafios a cada 3 horas"""
    domi_missao = random.choice(MISSOES[DOMI_ID])
    tati_missao = random.choice(MISSOES[TATI_ID])
    
    await bot.send_message(chat_id=DOMI_ID, text=f"Sua missão: {domi_missao}")
    await bot.send_message(chat_id=TATI_ID, text=f"Sua missão: {tati_missao}")

async def obey(update, context):
    """Usuário aceita o desafio e ganha pontos"""
    user_id = update.message.from_user.id
    if user_id not in AUTHORIZED_USERS:
        return await update.message.reply_text("Você não tem permissão para isso.")

    pontos[user_id] += 10
    await update.message.reply_text(f"Você aceitou o desafio e ganhou 10 pontos. Sua pontuação atual: {pontos[user_id]}.")

async def show_points(update, context):
    """Exibe a pontuação atual"""
    await update.message.reply_text(f"Pontos de Domi: {pontos[DOMI_ID]}\nPontos de Tati: {pontos[TATI_ID]}")

async def handle_tasks(update, context):
    user_id = update.message.from_user.id
    if user_id not in AUTHORIZED_USERS:
        return await update.message.reply_text("Você não tem permissão para isso.")
    tasks = TAREFAS.get(user_id, [])
    await update.message.reply_text(f"Suas tarefas: {', '.join(tasks)}")

async def handle_shopping(update, context):
    user_id = update.message.from_user.id
    if user_id not in AUTHORIZED_USERS:
        return await update.message.reply_text("Você não tem permissão para isso.")
    shopping = COMPRAS.get(user_id, [])
    await update.message.reply_text(f"Suas compras: {', '.join(shopping)}")

async def set_mode(update, context):
    """Permite mudar o modo da Domme usando o comando /modo"""
    global MODO_ATIVO

    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return await update.message.reply_text("Você não tem permissão para mudar os modos.")

    try:
        novo_modo = int(context.args[0])
        if novo_modo not in MODOS:
            raise ValueError
        MODO_ATIVO = novo_modo
        await update.message.reply_text(f"🔹 Modo alterado para: {MODOS[MODO_ATIVO]}")
    except (IndexError, ValueError):
        await update.message.reply_text("Uso correto: /modo <1, 2 ou 3>")

async def handle_message(update, context):
    """Função para responder mensagens usando OpenAI"""
    user_message = update.message.text
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é Domme N.Y.X.I.A., misteriosa e sofisticada, que controla este jogo."},
                {"role": "user", "content": user_message},
            ]
        )
        reply = response["choices"][0]["message"]["content"]
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"Erro ao processar sua mensagem: {e}")

# Configuração dos manipuladores
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CommandHandler("obey", obey))
app.add_handler(CommandHandler("points", show_points))
app.add_handler(CommandHandler("tarefas", handle_tasks))
app.add_handler(CommandHandler("compras", handle_shopping))
app.add_handler(CommandHandler("modo", set_mode))

# Configuração do agendador
scheduler = AsyncIOScheduler(timezone=pytz.UTC)
scheduler.add_job(send_challenge, "interval", hours=3)

# Início do bot
async def main():
    scheduler.start()
    print("Bot iniciado!")
    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())