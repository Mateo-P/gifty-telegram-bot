from contextlib import suppress
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

    async def send_message(self, chat_id: int, text: str, parse_mode: str = None):
        await self.bot_application.bot.send_message(
            chat_id=chat_id, text=text, parse_mode=parse_mode
        )

    async def welcome_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        user_id = update.message.from_user.id
        print(f"User ID: {user_id}")

        consumer_name = update.message.from_user.first_name
        # Make a GET request to fetch user's gift cards
        async with httpx.AsyncClient() as client:
            with suppress(Exception):
                response = await client.get(
                    f"{BACKEND_URL}/giftcards/", params={"telegram_id": user_id}
                )
                gift_cards = response.json().get("gift_cards", [])
                if gift_cards:
                    context.user_data["gift_cards"] = gift_cards

        # Build the keyboard
        keyboard = [
            [InlineKeyboardButton("Buy", callback_data="buy")],
            [InlineKeyboardButton("Redeem", callback_data="redeem")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send the welcome message along with gift card info
        await update.message.reply_text(
            f"Hi {consumer_name}, welcome to Gifty! 🎁", reply_markup=reply_markup
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
        elif query.data == "redeem":
            gift_cards = context.user_data.get("gift_cards")
            if gift_cards:
                gift_cards_message = "Here are your active gift cards:\n" + "\n".join(
                    [
                        f"Code: {gc['code']}, Balance: {gc['balance']}"
                        for gc in gift_cards
                    ]
                )
                await query.edit_message_text(text=gift_cards_message)
        else:
            await query.edit_message_text(
                text="You have no active gift cards to redeem."
            )
