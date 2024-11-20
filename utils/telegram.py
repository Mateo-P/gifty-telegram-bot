# telegram_client.py
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

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL")
print("BACKEND_URL: ", BACKEND_URL)


class TelegramClient:
    def __init__(self):
        self.bot_application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.bot_application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.welcome_message)
        )
        self.bot_application.add_handler(CallbackQueryHandler(self.button_handler))

    def start(self):
        print("INFO:     Started gifty telegram bot 🚀🤖📱")
        self.bot_application.run_polling()

    async def stop(self):
        await self.bot_application.stop()
        await self.bot_application.shutdown()
        print("Stopped gifty telegram bot")

    async def send_message(self, chat_id: int, text: str):
        await self.bot_application.bot.send_message(chat_id=chat_id, text=text)

    async def welcome_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        user_id = update.message.from_user.id
        print(f"User ID: {user_id}")
        # TODO fetch user name in case it exist

        keyboard = [
            [InlineKeyboardButton("Buy", callback_data="buy")],
            [InlineKeyboardButton("Redeem", callback_data="redeem")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Hi, welcome to Gifty!", reply_markup=reply_markup
        )

    async def button_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        await query.answer()

        if query.data == "buy":
            amount_keyboard = [
                [InlineKeyboardButton("10,000", callback_data="10000")],
                [InlineKeyboardButton("30,000", callback_data="30000")],
                [InlineKeyboardButton("50,000", callback_data="50000")],
                [InlineKeyboardButton("100,000", callback_data="100000")],
            ]
            amount_reply_markup = InlineKeyboardMarkup(amount_keyboard)
            await query.edit_message_text(
                text="Select the amount:", reply_markup=amount_reply_markup
            )

        elif query.data in ["10000", "30000", "50000", "100000"]:
            await query.edit_message_text(text=f"You selected {query.data}.")
            post_data = {
                "amount": int(query.data),
                "channel": "telegram",
                "user_channel_id": str(query.from_user.id),
            }

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{BACKEND_URL}/giftcards/buy/", json=post_data
                    )
                    if response.status_code == 200:
                        data = response.json()
                        payment_link = data.get("payment_link_url")
                        if payment_link:
                            await self.send_message(
                                chat_id=query.from_user.id,
                                text=f"Please complete the payment using the following link:\n{payment_link}",
                            )
                        else:
                            await self.send_message(
                                chat_id=query.from_user.id,
                                text="We could not retrieve the payment link.",
                            )
                    else:
                        await self.send_message(
                            chat_id=query.from_user.id,
                            text="There was an error processing your purchase. Please try again.",
                        )
                except Exception as e:
                    print(f"An error occurred: {e}")
                    await self.send_message(
                        chat_id=query.from_user.id,
                        text="An error occurred while processing your request.",
                    )
        else:
            await query.edit_message_text(text="You chose to Redeem.")