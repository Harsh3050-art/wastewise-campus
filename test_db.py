
from services.db import init_db, DB_PATH

init_db()

print("Database initialized successfully!")
print("Database location:", DB_PATH)
