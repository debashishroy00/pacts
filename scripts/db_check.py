"""
Database connectivity smoke test for containerized PACTS runner.
Validates that Postgres connection works from inside Docker network.
"""
import asyncio
import os
import sys
import asyncpg


async def main():
    """Test database connectivity with minimal dependencies."""
    # Read connection params from environment (set by docker-compose)
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    database = os.getenv("POSTGRES_DB", "pacts")
    user = os.getenv("POSTGRES_USER", "pacts")
    password = os.getenv("POSTGRES_PASSWORD", "pacts")

    print(f"🔍 Testing connection to {user}@{host}:{port}/{database}")

    try:
        # Connect
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            timeout=10
        )
        print("✅ Connected to database!")

        # Test query
        version = await conn.fetchval("SELECT version()")
        print(f"✅ Postgres version: {version}")

        # Check schema
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        table_names = [t['tablename'] for t in tables]
        print(f"✅ Found {len(tables)} tables: {', '.join(table_names)}")

        # Verify v3.0 tables exist
        expected_tables = {'runs', 'run_steps', 'artifacts', 'selector_cache', 'heal_history', 'metrics'}
        missing = expected_tables - set(table_names)
        if missing:
            print(f"⚠️  Warning: Missing tables: {missing}")
        else:
            print("✅ All v3.0 tables present!")

        # Close connection
        await conn.close()
        print("\n✅ Database smoke test PASSED!")
        return 0

    except Exception as e:
        print(f"\n❌ Database smoke test FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
