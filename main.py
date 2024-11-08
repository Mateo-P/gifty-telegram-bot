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

# Initialize FastAPI app
app = FastAPI()

# Pydantic model for the expected JSON payload
class PaymentStatus(BaseModel):
    status: str
    id: str

# Endpoint to receive payment status updates
@app.post("/payment-status")
async def payment_status_update(payment: PaymentStatus):
    """
    Receives payment status updates and notifies the user via Telegram.
    """
    # Extract status and id
    status = payment.status
    user_id = payment.id

    # Log the received data
    print(f"Received payment status update: status={status}, id={user_id}")

    # Send a message to the user via Telegram bot
    # Assuming status is 'success' when payment is successful
    if status == 'success':
        # Convert user_id to integer
        chat_id = int(user_id)
        # Send message to user
        await bot_application.bot.send_message(
            chat_id=chat_id,
            text="✅ Your payment was successful! Thank you for your purchase."
        )
    else:
        # Handle other statuses if necessary
        chat_id = int(user_id)
        await bot_application.bot.send_message(
            chat_id=chat_id,
            text="❗ Your payment was not successful. Please try again."
        )

    return {"message": "Notification sent to user."}

async def welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends a welcome message with 'Buy' and 'Redeem' buttons when any message is received.
    """
    # Extract user ID
    user_id = update.message.from_user.id

    # Print user ID to console
    print(f"User ID: {user_id}")

    # Define the initial buttons
    keyboard = [
        [InlineKeyboardButton("Buy", callback_data='buy')],
        [InlineKeyboardButton("Redeem", callback_data='redeem')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the welcome message with buttons
    await update.message.reply_text('Hi, welcome to Gifty!', reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the response when a button is pressed.
    """
    query = update.callback_query
    await query.answer()

    # Check if the user pressed "Buy"
    if query.data == 'buy':
        # Define buttons for amount selection
        amount_keyboard = [
            [InlineKeyboardButton("10,000", callback_data='10000')],
            [InlineKeyboardButton("30,000", callback_data='30000')],
            [InlineKeyboardButton("50,000", callback_data='50000')],
            [InlineKeyboardButton("100,000", callback_data='100000')]
        ]

        amount_reply_markup = InlineKeyboardMarkup(amount_keyboard)

        # Send a message to select the amount
        await query.edit_message_text(text="Select the amount:", reply_markup=amount_reply_markup)

    # Handle the amount selection
    elif query.data in ['10000', '30000', '50000', '100000']:
        # Confirm the selected amount to the user
        await query.edit_message_text(text=f"You selected {query.data}.")

        # Prepare data for POST request
        post_data = {
            "amount": int(query.data),
            "telegram_id": str(query.from_user.id)
        }

        # Make the async POST request using httpx to the backend
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{BACKEND_URL}/generate-payment-link", json=post_data)
                # Check if the request was successful
                if response.status_code == 200:
                    # Parse the response
                    data = response.json()
                    payment_link = data.get("payment_link_url")
                    if payment_link:
                        # Send the payment link to the user
                        await context.bot.send_message(
                            chat_id=query.from_user.id,
                            text=f"Please complete the payment using the following link:\n{payment_link}"
                        )
                    else:
                        # If the payment link is not in the response
                        await context.bot.send_message(
                            chat_id=query.from_user.id,
                            text="We could not retrieve the payment link."
                        )
                else:
                    # Handle unsuccessful response
                    await context.bot.send_message(
                        chat_id=query.from_user.id,
                        text="There was an error processing your purchase. Please try again."
                    )
            except Exception as e:
                # Handle exceptions
                print(f"An error occurred: {e}")
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="An error occurred while processing your request."
                )
    else:
        # For the "Redeem" button or any other option
        await query.edit_message_text(text="You chose to Redeem.")

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)

async def run_bot():
    global bot_application
    bot_application = Application.builder().token(TELEGRAM_TOKEN).build()
    bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, welcome_message))
    bot_application.add_handler(CallbackQueryHandler(button_handler))

    # Start the bot
    await bot_application.initialize()
    await bot_application.start()
    await bot_application.updater.start_polling()
    # Run the bot until it is stopped
    await bot_application.updater.idle()

def main():
    # Run FastAPI in a separate thread
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()

    # Run the Telegram bot
    asyncio.run(run_bot())

if __name__ == '__main__':
    main()
