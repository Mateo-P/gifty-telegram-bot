from fastapi import APIRouter, Depends
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from schemas.giftcard import RedeemingTransaction
from utils import telegram
from utils.telegram import TelegramClient

router = APIRouter()


@router.post("/redeem_request")
async def redeem_request(
    redeeming_transaction: RedeemingTransaction, telegram_client: TelegramClient = Depends()
):
    transaction_status = redeeming_transaction.status
    message = redeeming_transaction.message
    if transaction_status == "CREATED":
        await telegram_client.bot_application.bot.send_message(
            chat_id=int(redeeming_transaction.telegram_id),
            text=message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Confirm", callback_data=f"redeem_confirm__{redeeming_transaction.id}")],
                [InlineKeyboardButton("Reject", callback_data=f"redeem_reject__{redeeming_transaction.id}")],
            ])
        )
    else:
        #notifies the customer
        await telegram_client.bot_application.bot.send_message(
            chat_id=int(redeeming_transaction.customer_telegram_id),
            text=message,
            reply_markup=telegram_client.get_menu()
        )
        #notifies the shop
        await telegram_client.bot_application.bot.send_message(
            chat_id=int(redeeming_transaction.shop_telegram_id),
            text=message,
            reply_markup=telegram_client.get_shop_menu()
        )
    return {"message": f"[{transaction_status}] Redeem request sent to user."}
