from contextlib import suppress
from schemas.giftcard import RedeemingTransaction, RedeemingTransactionUpdate, TransactionError
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL")
NIT, NAME, EMAIL, PHONE = range(4)

class TelegramClient:
    def __init__(self):
        self.bot_application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Conversation handler for shop creation
        shop_conversation_handler = ConversationHandler( 
            entry_points=[CommandHandler("shop", self.start_shop_creation)], 
            states={ 
                NIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_nit)], 
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_name)], 
                EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_email)], 
                PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_phone)], 
            },
            fallbacks=[CommandHandler("cancel", self.cancel)], 
        )

        # Add handlers
        self.bot_application.add_handler(shop_conversation_handler)
        self.bot_application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, self.welcome_message
            )
        )
        self.bot_application.add_handler(CallbackQueryHandler(self.button_handler))

    def start(self):
        print("INFO:     Started gifty telegram bot 🚀🤖📱")
        self.bot_application.run_polling()

    async def stop(self):
        await self.bot_application.stop()
        await self.bot_application.shutdown()
        print("Stopped gifty telegram bot")

    #TODO change the name of this function
    async def welcome_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        user_id = update.message.from_user.id

        if context.user_data.get("awaiting_gift_card_code"):
            gc_code = update.message.text
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{BACKEND_URL}/giftcards/redeem/",
                        json={"telegram_id": user_id, "gc_code": gc_code}
                    )

                    
                    
                    if response.status_code == 201:
                        redeeming_transaction = RedeemingTransaction(**response.json())
                        await self.bot_application.bot.send_message(
                            chat_id=int(redeeming_transaction.customer_telegram_id),
                            text=redeeming_transaction.message,
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("Confirm", callback_data=f"redeem_confirm__{redeeming_transaction.id}")],
                                [InlineKeyboardButton("Reject", callback_data=f"redeem_reject__{redeeming_transaction.id}")],
                            ])
                        )
                        return await update.message.reply_text("⏳ Awaiting for customer to validate redemption...")
                       
                    else:
                        transaction_error = TransactionError(**response.json()).error
                        await update.message.reply_text(
                            transaction_error
                        )
            except Exception as e:
                print(f"Error during gift card redemption: {e}")
                await update.message.reply_text("An error occurred during redemption. Please try again.")

        
        else:
            consumer_name = update.message.from_user.first_name

            # Send the welcome message along with gift card info
            await update.message.reply_text(
                f"🎁 Hi {consumer_name}, welcome to Gifty! ", reply_markup=self.get_menu()
            )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        message_id = query.message.message_id

        try:
            if query.data == "buy":
                await self.handle_buy_selection(query)

            elif query.data in ["10000", "30000", "50000", "100000"]:
                await self.handle_payment_process(query, user_id, message_id)

            elif query.data == "redeem":
                await self.handle_redeem_gift_cards(query, user_id, context)

            elif query.data.startswith("gc"):
                await self.handle_gift_card_details(query, context)
            
            elif query.data == "shop_redeem":
                await self.handle_redeem_shop(query, user_id, context)
            
            elif query.data.startswith("redeem_confirm") or query.data.startswith("redeem_reject"):
                await self.handle_customer_redeem_confirm(query,context)
            else:
                await query.edit_message_text(
                    text="You have no active gift cards to redeem."
                )
        except Exception as e:
            print(f"An error occurred: {e}")
            await query.edit_message_text(
                text="❗ An unexpected error occurred. Please try again later."
            )

    # ---- Helper Functions ----

    async def handle_buy_selection(self, query) -> None:
        """Handles the 'buy' selection to show amount options."""
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


    async def handle_payment_process(self, query, user_id: int, message_id: int) -> None:
        """Handles the payment process for a selected amount."""
        post_data = {
            "amount": int(query.data),
            "channel": "telegram",
            "user_channel_id": str(user_id),
            "user_message_id": message_id
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{BACKEND_URL}/giftcards/buy/", json=post_data)
                if response.status_code == 200:
                    data = response.json()
                    payment_link = data.get("payment_link_url")
                    if payment_link:
                        pay_button = [[InlineKeyboardButton("Pay", url=payment_link)]]
                        await query.edit_message_text(
                            text="Please complete the payment by clicking 👇:",
                            reply_markup=InlineKeyboardMarkup(pay_button),
                        )
                    else:
                        await query.edit_message_text(
                            text="We could not retrieve the payment link. Please try again."
                        )
                else:
                    await query.edit_message_text(
                        text="There was an error processing your purchase. Please try again."
                    )
            except Exception as e:
                print(f"Error during payment process: {e}")
                await query.edit_message_text(
                    text="An error occurred while processing your request."
                )


    async def handle_redeem_gift_cards(self, query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles fetching and displaying redeemable gift cards."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{BACKEND_URL}/giftcards/", params={"telegram_id": user_id})
                gift_cards = response.json().get("gift_cards", [])
                if gift_cards:
                    gcs_list = [
                        [InlineKeyboardButton(f"Code: {gc['code']} - Balance: ${gc['balance']}", callback_data=f"gc_{gc['code']}")]
                        for gc in gift_cards
                    ]
                    await query.edit_message_text(
                        text="Your 🎁**Gift Cards**👇",
                        reply_markup=InlineKeyboardMarkup(gcs_list),
                        parse_mode="Markdown",
                    )
                    context.user_data["gift_cards"] = gift_cards
                else:
                    await query.edit_message_text(text="You don't have any gift cards to redeem.")
            except Exception as e:
                print(f"Error fetching gift cards: {e}")
                await query.edit_message_text(
                    text="❗ An error occurred while fetching gift cards. Please try again later."
                )


    async def handle_gift_card_details(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles displaying the details of a selected gift card."""
        gift_cards = context.user_data.get("gift_cards", [])
        gift_card_code = query.data.split("_")[1]
        matching_card = next((gc for gc in gift_cards if gc["code"] == gift_card_code), None)

        if matching_card:
            gift_card_message = (
                f"🎁**Gift Card Details**👇\n\n"
                f"• **Code**: `{matching_card['code']}`\n"
                f"• **Status**: {matching_card['status']}\n"
                f"• **Balance**: {matching_card['balance']} COP\n"
                f"• **Expires At**: {matching_card['expires_at']}\n\n"
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
    
    async def handle_customer_redeem_confirm(self, query,context: ContextTypes.DEFAULT_TYPE) -> None:
        """"""
        query_parts = query.data.split("__")
        user_action = query_parts[0]
        id = query_parts[1]
        async with httpx.AsyncClient() as client:
            try:
                redeem_trasaction = {
                    "id": id,
                    "user_action": user_action,
                }

                response = await client.patch(
                    f"{BACKEND_URL}/giftcards/redeem/", json=redeem_trasaction
                )
                if response.status_code == 200:
                    redeeming_transaction = RedeemingTransactionUpdate(**response.json())
                    message = redeeming_transaction.message

                    #notifies the customer
                    await query.edit_message_text(
                        text=message,
                        parse_mode="Markdown",
                        reply_markup=self.get_menu(),
                    )
                    #notifies the shop
                    await self.bot_application.bot.send_message(
                        chat_id=int(redeeming_transaction.shop_telegram_id),
                        text=message,
                        parse_mode="Markdown",
                        reply_markup=self.get_shop_menu()
                    )
                else:
                    transaction_error = TransactionError(**response.json()).error
                    await query.edit_message_text(
                        transaction_error
                    )
            except Exception as e:
                await query.edit_message_text(text=f"Error in shop data:\n{e}\nPlease restart.")
                return ConversationHandler.END

    def get_menu(self):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Buy", callback_data="buy")],
            [InlineKeyboardButton("Redeem", callback_data="redeem")],
        ])

    #Shops--------------------------------------------

    async def handle_redeem_shop(self, query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        await query.edit_message_text(
            text="🎁 Insert the gift card code:"
        )
        context.user_data["awaiting_gift_card_code"] = True


    async def start_shop_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["conversation_active"] = True
        telegram_id = update.message.from_user.id
        async with httpx.AsyncClient() as client:
            try:  
                response = await client.get(
                    f"{BACKEND_URL}/shops/?telegram_id={telegram_id}")
                
                shop = response.json()
                if response.status_code == 200:
                    greeting_message = (
                    f"Hi {shop['name']}, welcome to Gifty! 🎁"
                    )
                    await update.message.reply_text(
                        greeting_message,
                        parse_mode="Markdown",
                        reply_markup=self.get_shop_menu()
                        )
                    #context.user_data["conversation_active"] = False
                else:
                    raise Exception("Not found")

            except Exception as e:
                context.user_data["conversation_active"] = True
                await update.message.reply_text(
                    "Welcome to the Shop Creator!\n Please provide the shop's NIT:"
                )
                return NIT

    async def collect_nit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["nit"] = update.message.text
        await update.message.reply_text("Got it!\n Now, please provide the shop's name:")
        return NAME

    async def collect_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["name"] = update.message.text
        await update.message.reply_text("Great!\n Now, please provide the shop's email:")
        return EMAIL

    async def collect_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        email = update.message.text
        try:
            context.user_data["email"] = email
            await update.message.reply_text("Thanks!\n Now, provide the shop's phone number:")
            return PHONE
        except Exception:
            await update.message.reply_text("Invalid email format. Please try again.")
            return EMAIL

    async def collect_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        telegram_id = update.message.from_user.id
        context.user_data["phone"] = update.message.text
        async with httpx.AsyncClient() as client:
            try:
                shop_data = {
                    "nit": context.user_data["nit"],
                    "name": context.user_data["name"],
                    "email": context.user_data["email"],
                    "phone": context.user_data["phone"],
                    "telegram_id": telegram_id
                }

                response = await client.post(
                    f"{BACKEND_URL}/shops/", json=shop_data
                )
                if response.status_code == 201:
                    shop = response.json().get('shop')
                    shop_info = (
                    f"🏪      Shop created successfully             ✅\n\n"
                    f"• **Name**: {shop['name']}\n"
                    f"• **Nit**: `{shop['nit']}`\n"
                    f"• **Email**: {shop['email']}\n"
                    f"• **Phone**: {shop['phone']}\n\n\n"
                    )
                    await update.message.reply_text(
                        text=shop_info,
                        parse_mode="Markdown",
                        reply_markup=self.get_shop_menu(),
                    )
            except Exception as e:
                context.user_data["conversation_active"] = False
                await update.message.reply_text(f"Error in shop data:\n{e}\nPlease restart.")
                return ConversationHandler.END

    # Cancel the conversation

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["conversation_active"] = False
        await update.message.reply_text(
            "Shop creation canceled.", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


    def get_shop_menu(self):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Redeem", callback_data="shop_redeem")],
        ])
