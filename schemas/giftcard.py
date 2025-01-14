from typing import Any
from pydantic import BaseModel


class RedeemingTransaction(BaseModel):
    customer_telegram_id: str
    id: str
    message: str
    status: str

class RedeemingTransactionUpdate(RedeemingTransaction):
    shop_telegram_id : str 


class TransactionError(BaseModel):
    error: str | None

