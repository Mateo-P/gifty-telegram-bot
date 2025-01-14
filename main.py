from fastapi import FastAPI
from routers import giftcard, payment
import threading
import uvicorn
from utils.telegram import TelegramClient

telegram_client = TelegramClient()
app = FastAPI()


# Función para correr FastAPI
def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)


# health check endpoint
@app.get("/health")
def healthcheck():
    return 200


# routes
app.include_router(
    giftcard.router,
    prefix="/giftcards",
)
app.include_router(
    payment.router,
    prefix="/payments",
)


def main():
    # order matters here. first start fastapi
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()

    telegram_client = TelegramClient()
    telegram_client.start()


if __name__ == "__main__":
    main()
