from fastapi import APIRouter, Depends
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from schemas.payment import PaymentStatus
from utils import telegram
from utils.telegram import TelegramClient

router = APIRouter()


@router.post("/status")
async def payment_status_update(
    payment: PaymentStatus, telegram_client: TelegramClient = Depends()
):
    status = payment.status
    user_id = payment.telegram_id
    message_id = payment.message_id
    giftcard = payment.gift_card
    gift_card_details = (
        "🎁 <b>Gift Card Details:</b>\n\n"
        f"• <b>Code:</b> <code>{giftcard['code']}</code>\n"
        f"• <b>Status:</b> {giftcard['status']}\n"
        f"• <b>Balance:</b> {giftcard['balance']} COP\n"
        f"• <b>Expires At:</b> {giftcard['expires_at']}\n"
        "\nThank you for your purchase! 🎉"
    )
    print(f"[Status]: {status}, [Id]: {user_id}")

    chat_id = int(user_id)
    if status == "success":
        # Build the keyboard
        try:
            await telegram_client.bot_application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=gift_card_details,
                parse_mode="HTML",
                reply_markup=telegram_client.get_menu()
            )
        except telegram.error.BadRequest as e:
            if "Message to edit not found" in str(e):
                # Send a new message if the original message cannot be edited
                await telegram_client.bot_application.bot.send_message(
                    chat_id=chat_id,
                    text=gift_card_details,
                    parse_mode="HTML",
                    reply_markup=telegram_client.get_menu()
                )
    else:
        await telegram_client.bot.send_message(
            chat_id=chat_id,
            text="❗ Your payment was not successful. Please try again.",
        )

    return {"message": "Notification sent to user."}
