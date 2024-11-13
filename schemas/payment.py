from pydantic import BaseModel


class PaymentStatus(BaseModel):
    status: str
    id: str
