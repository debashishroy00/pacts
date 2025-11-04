import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "pacts"),
            user=os.getenv("POSTGRES_USER", "pacts"),
            password=os.getenv("POSTGRES_PASSWORD", "pacts"),
        )
        result = await conn.fetchval("SELECT current_user")
        print(f"✅ Connected as: {result}")
        await conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test_connection())
