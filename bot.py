from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import openai

# Tokens e configurações
TELEGRAM_TOKEN = "7773946789:AAFue4w2jkf_Bqzjlxd9LgtEMc2H6eEixb8"
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# Função para lidar com mensagens
async def handle_message(update: Update, context):
    user_message = update.message.text
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": user_message}]
    )
    gpt_response = response['choices'][0]['message']['content']
    await update.message.reply_text(gpt_response)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot está rodando...")
app.run_polling()