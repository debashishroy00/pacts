import os
from dotenv import load_dotenv

ok = load_dotenv()
print("dotenv_loaded=", ok)
for k in ["POSTGRES_HOST","POSTGRES_PORT","POSTGRES_DB","POSTGRES_USER","POSTGRES_PASSWORD"]:
    print(k, "=", os.getenv(k))
