import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import httpx
import os
from dotenv import load_dotenv
import threading
import uvicorn

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
BACKEND_URL = os.getenv('BACKEND_URL') 

# Variable global para acceder al bot
bot_application = None

# Inicializar la aplicación FastAPI
app = FastAPI()

# Modelo Pydantic para el payload JSON esperado
class PaymentStatus(BaseModel):
    status: str
    id: str

# Endpoint para recibir actualizaciones de estado de pago
@app.post("/payment-status")
async def payment_status_update(payment: PaymentStatus):
    status = payment.status
    user_id = payment.id
    print(f"Received payment status update: status={status}, id={user_id}")

    chat_id = int(user_id)
    if status == 'success':
        await bot_application.bot.send_message(
            chat_id=chat_id,
            text="✅ Your payment was successful! Thank you for your purchase."
        )
    else:
        await bot_application.bot.send_message(
            chat_id=chat_id,
            text="❗ Your payment was not successful. Please try again."
        )

    return {"message": "Notification sent to user."}

# Función para manejar mensajes de bienvenida
async def welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    print(f"User ID: {user_id}")

    keyboard = [
        [InlineKeyboardButton("Buy", callback_data='buy')],
        [InlineKeyboardButton("Redeem", callback_data='redeem')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text('Hi, welcome to Gifty!', reply_markup=reply_markup)

# Función para manejar botones
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'buy':
        amount_keyboard = [
            [InlineKeyboardButton("10,000", callback_data='10000')],
            [InlineKeyboardButton("30,000", callback_data='30000')],
            [InlineKeyboardButton("50,000", callback_data='50000')],
            [InlineKeyboardButton("100,000", callback_data='100000')]
        ]
        amount_reply_markup = InlineKeyboardMarkup(amount_keyboard)
        await query.edit_message_text(text="Select the amount:", reply_markup=amount_reply_markup)

    elif query.data in ['10000', '30000', '50000', '100000']:
        await query.edit_message_text(text=f"You selected {query.data}.")
        post_data = {
            "amount": int(query.data),
            "telegram_id": str(query.from_user.id)
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{BACKEND_URL}", json=post_data)
                if response.status_code == 200:
                    data = response.json()
                    payment_link = data.get("payment_link_url")
                    if payment_link:
                        await context.bot.send_message(
                            chat_id=query.from_user.id,
                            text=f"Please complete the payment using the following link:\n{payment_link}"
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=query.from_user.id,
                            text="We could not retrieve the payment link."
                        )
                else:
                    await context.bot.send_message(
                        chat_id=query.from_user.id,
                        text="There was an error processing your purchase. Please try again."
                    )
            except Exception as e:
                print(f"An error occurred: {e}")
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="An error occurred while processing your request."
                )
    else:
        await query.edit_message_text(text="You chose to Redeem.")

# Función para correr FastAPI
def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Función para correr el bot de Telegram
def run_bot():
    global bot_application
    bot_application = Application.builder().token(TELEGRAM_TOKEN).build()
    bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, welcome_message))
    bot_application.add_handler(CallbackQueryHandler(button_handler))

    bot_application.run_polling()

def main():
    # Ejecutar FastAPI en un hilo separado
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()

    # Ejecutar el bot de Telegram
    run_bot()

if __name__ == '__main__':
    main()
