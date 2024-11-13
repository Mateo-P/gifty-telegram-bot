from fastapi import APIRouter, Depends
from schemas.payment import PaymentStatus
from utils.telegram import TelegramClient

router = APIRouter()


@router.post("/status")
async def payment_status_update(
    payment: PaymentStatus, telegram_client: TelegramClient = Depends()
):
    status = payment.status
    user_id = payment.id
    print(f"Received payment status update: status={status}, id={user_id}")

    chat_id = int(user_id)
    if status == "success":
        await telegram_client.bot.send_message(
            chat_id=chat_id,
            text="✅ Your payment was successful! Thank you for your purchase.",
        )
    else:
        await telegram_client.bot.send_message(
            chat_id=chat_id,
            text="❗ Your payment was not successful. Please try again.",
        )

    return {"message": "Notification sent to user."}
