from fastapi import FastAPI
from contextlib import asynccontextmanager
from utils.telegram import TelegramClient
from routers import payment


telegram_client = TelegramClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_client.start()

    # yield to FastAPI
    yield

    await telegram_client.stop()


app = FastAPI(title="gifty bot api", version="1.0.0", lifespan=lifespan)


# health check endpoint
@app.get("/health")
def healthcheck():
    return 200


# routes
app.include_router(
    payment.router,
    prefix="/payments",
)
