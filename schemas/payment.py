from typing import Any
from pydantic import BaseModel


class PaymentStatus(BaseModel):
    status: str
    telegram_id: str
    gift_card: Any
    message_id: str
