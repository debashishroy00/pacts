import asyncpg
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

async def test():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', '5432')),
            database=os.getenv('POSTGRES_DB', 'pacts'),
            user=os.getenv('POSTGRES_USER', 'pacts_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'pacts_dev_password')
        )
        print(f"✅ Connected to database!")
        result = await conn.fetchval('SELECT 1')
        print(f"✅ Query test: {result}")
        await conn.close()
        print("✅ Connection closed")
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test())
