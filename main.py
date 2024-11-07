from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import httpx

#TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_TOKEN="7919446321:AAHeDmhwp7Bx9ERfJHgwQovKkyeylN-jOgE"
print(TELEGRAM_TOKEN)




async def welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message with 'Buy' and 'Redeem' buttons when any message is received."""
    
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
    """Handles the response when a button is pressed."""
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
            "user_id": query.from_user.id,
            "amount": int(query.data)
        }

        #https://gifty.api.servimarketco.store/giftcards/buy/

    else:
        # For the "Redeem" button or any other option
        await query.edit_message_text(text="You chose to Redeem.")



def main():
    """Main function to set up and run the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, welcome_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()


# Run the bot without asyncio.run() to avoid event loop issues
if __name__ == '__main__':
    main()