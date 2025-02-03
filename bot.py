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
DESAFIOS = {
    "domi": [
        "Domi, massageie Tati por exatamente **7 minutos**.",
        "Domi, use apenas palavras para atiçá-la. Mas sem toque direto.",
    ],
    "tati": [
        "Tati, escolha algo que Domi **não pode fazer hoje**.",
        "Tati, determine algo que Domi **deverá executar sem questionar**.",
    ]
}

async def send_challenge():
    """Envia desafios a cada 3 horas"""
    domi_desafio = random.choice(DESAFIOS["domi"])
    tati_desafio = random.choice(DESAFIOS["tati"])
    
    desafios_pendentes[DOMI_ID] = {"desafio": domi_desafio, "status": "pendente"}
    desafios_pendentes[TATI_ID] = {"desafio": tati_desafio, "status": "pendente"}
    
    await bot.send_message(chat_id=DOMI_ID, text=f"Seu desafio: {domi_desafio}\nEnvie 'OBEDECER' em até 3 horas para aceitar.")
    await bot.send_message(chat_id=TATI_ID, text=f"Seu desafio: {tati_desafio}\nEnvie 'OBEDECER' em até 3 horas para aceitar.")

    # Penalização após 3 horas
    await asyncio.sleep(10800)  # 3 horas em segundos
    for user_id in [DOMI_ID, TATI_ID]:
        if desafios_pendentes.get(user_id, {}).get("status") == "pendente":
            pontos[user_id] -= 10
            await bot.send_message(chat_id=user_id, text="Você não aceitou o desafio dentro do tempo. Perdeu 10 pontos.")

async def obey(update, context):
    """Usuário aceita o desafio e ganha pontos"""
    user_id = update.message.from_user.id
    if user_id not in desafios_pendentes or desafios_pendentes[user_id]["status"] != "pendente":
        return await update.message.reply_text("Você não tem desafios pendentes ou já aceitou.")

    desafios_pendentes[user_id]["status"] = "aceito"
    pontos[user_id] += 10
    other_id = DOMI_ID if user_id == TATI_ID else TATI_ID
    
    await bot.send_message(chat_id=other_id, text="A domme exige sua presença para a execução do desafio. Você tem 2 horas para estar disponível.")
    
    # Penalização se a outra pessoa não estiver disponível
    await asyncio.sleep(7200)  # 2 horas em segundos
    if desafios_pendentes[user_id]["status"] == "aceito":
        pontos[other_id] -= 10
        await bot.send_message(chat_id=other_id, text="Você não se apresentou a tempo. Perdeu 10 pontos.")

    await update.message.reply_text(f"Desafio aceito. Você ganhou 10 pontos.")

async def show_points(update, context):
    """Exibe a pontuação atual"""
    await update.message.reply_text(f"Pontos de Domi: {pontos[DOMI_ID]}\nPontos de Tati: {pontos[TATI_ID]}")

async def set_mode(update: Update, context):
    """Permite mudar o modo da domme usando o comando /modo"""
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

# Configurando o agendador com timezone
scheduler = AsyncIOScheduler(timezone=pytz.UTC)
scheduler.add_job(send_challenge, "interval", hours=3)

async def start_scheduler():
    scheduler.start()

# Função de interação com a OpenAI
async def handle_message(update, context):
    """Função para responder as mensagens recebidas utilizando o modelo GPT"""
    user_message = update.message.text  # Obtém a mensagem enviada pelo usuário

    try:
        # Faz a chamada para o modelo GPT da OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Utiliza o modelo gpt-4
            messages=[
                {"role": "system", "content": "Você é Domme N.Y.X.I.A., uma domme misteriosa, envolvente e sofisticada, sempre pronta para desafiar seus submissos."},
                {"role": "user", "content": user_message},
            ]
        )
        
        # Obtém a resposta do modelo
        bot_reply = response["choices"][0]["message"]["content"]

        # Envia a resposta para o usuário
        await update.message.reply_text(bot_reply)

    except Exception as e:
        # Caso ocorra algum erro, envia uma mensagem de erro
        await update.message.reply_text(f"Ocorreu um erro ao processar sua mensagem: {e}")

# Configuração do manipulador de mensagens
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CommandHandler("obey", obey))
app.add_handler(CommandHandler("points", show_points))
app.add_handler(CommandHandler("modo", set_mode))

# Iniciando o bot corretamente sem conflitos de loop
async def main():
    scheduler.start()
    print("Bot iniciado!")
    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())