from fastapi import APIRouter, Depends
from schemas.payment import PaymentStatus
from utils.telegram import TelegramClient

router = APIRouter()


@router.post("/status")
async def payment_status_update(
    payment: PaymentStatus, telegram_client: TelegramClient = Depends()
):
    status = payment.status
    user_id = payment.telegram_id
    giftcard = payment.gift_card
    gift_card_details = (
        f"🎁 Gift Card Details:\n\n"
        f"• Code: `{giftcard['code']}`\n"
        f"• Balance: {giftcard['balance']} COP\n"
        f"• Expires At: {giftcard['expires_at']}\n"
        f"\nThank you for your purchase! 🎉"
    )
    print(f"[Status]: {status}, [Id]: {user_id}")

    chat_id = int(user_id)
    if status == "success":
        await telegram_client.send_message(
            chat_id=chat_id,
            text=gift_card_details,
        )
    else:
        await telegram_client.bot.send_message(
            chat_id=chat_id,
            text="❗ Your payment was not successful. Please try again.",
        )

    return {"message": "Notification sent to user."}
