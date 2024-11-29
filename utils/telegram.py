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

        # Send the welcome message along with gift card info
        await update.message.reply_text(
            f"Hi {consumer_name}, welcome to Gifty! 🎁", reply_markup=self.get_menu()
        )

    async def button_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        message_id = query.message.message_id
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
            post_data = {
                "amount": int(query.data),
                "channel": "telegram",
                "user_channel_id": str(user_id),
                "user_message_id": message_id
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
                            pay_button = [
                                [InlineKeyboardButton("Pay", url=payment_link)],
                            ]
                            pay_button_reply_markup = InlineKeyboardMarkup(pay_button)
                            await query.edit_message_text(
                                text=f"Please complete the payment clicking 👇:",
                                reply_markup=pay_button_reply_markup,
                            )
                        else:
                            await self.send_message(
                                chat_id=user_id,
                                text="We could not retrieve the payment link.",
                            )
                    else:
                        await self.send_message(
                            chat_id=user_id,
                            text="There was an error processing your purchase. Please try again.",
                        )
                except Exception as e:
                    print(f"An error occurred: {e}")
                    await self.send_message(
                        chat_id=query.from_user.id,
                        text="An error occurred while processing your request.",
                    )
        elif query.data == "redeem":
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        f"{BACKEND_URL}/giftcards/", params={"telegram_id": user_id}
                    )
                    gift_cards = response.json().get("gift_cards", [])
                    if gift_cards:
                        gcs_list = [
                            [
                                InlineKeyboardButton(
                                    f"Code: {gc['code']} - Balance: ${gc['balance']}".ljust(50),
                                    callback_data=f"gc_{gc['code']}",
                                )
                            ]
                            for gc in gift_cards
                        ]

                        gcs_list_markup = InlineKeyboardMarkup(gcs_list)
                        await query.edit_message_text(
                            text="Your             🎁**Gift Cards**          👇",
                            reply_markup=gcs_list_markup,
                            parse_mode="Markdown",
                        )
                        context.user_data["gift_cards"]= gift_cards
                    else:
                        await query.edit_message_text(
                            text="You don't have any gift cards to redeem."
                        )
                except Exception as e:
                    print(f"An error occurred while fetching gift cards: {e}")
                    await query.edit_message_text(
                        text="❗ An error occurred while fetching gift cards."
                    )
        
        elif query.data.startswith("gc"):
            # Extract the code from query.data
            gift_card_code = query.data.split("_")[1]  # Extracts "R21AC2" from "gc_R21AC2"

            # Retrieve the gift cards from user data
            gift_cards = context.user_data.get("gift_cards", [])

            # Find the gift card that matches the code
            matching_card = next((gc for gc in gift_cards if gc["code"] == gift_card_code), None)

            if matching_card:
                gift_card_message = (
                    f"Your              🎁**Gift Card**            👇\n\n"
                    f"• **Code**: `{matching_card['code']}`\n"
                    f"• **Status**: {matching_card['status']}\n"
                    f"• **Balance**: {matching_card['balance']} COP\n"
                    f"• **Expires At**: {matching_card['expires_at']}\n\n\n"
                    "**How to redeem?**\n"
                    "Provide the shop the code above to redeem your balance."
                )
                await query.edit_message_text(
                    text=gift_card_message,
                    parse_mode="Markdown",
                    reply_markup=self.get_menu(),
                )
            else:
                await query.edit_message_text(
                    text="You have no active gift card matching the code to redeem."
                )
        else:
            await query.edit_message_text(
                text="You have no active gift cards to redeem."
            )

    def get_menu(self):  # Fixed: Added self as a parameter
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Buy", callback_data="buy")],
            [InlineKeyboardButton("Redeem", callback_data="redeem")],
        ])
