from contextlib import asynccontextmanager
from tortoise import Tortoise
import os

DB_URL = os.getenv("DATABASE_URL")
@asynccontextmanager
async def lifespan(app):
    await Tortoise.init(
        db_url=DB_URL,
        modules={"models": ["model.key","model.user"]},
    )
    await Tortoise.generate_schemas()  
    print("✅ Connected to Neon DB")
    yield  
    await Tortoise.close_connections()
    print("❌ Disconnected from DB")
