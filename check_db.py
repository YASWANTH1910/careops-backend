import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2, re

url = os.getenv("DATABASE_URL")
m = re.match(r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", url)
user, pw, host, port, db = m.groups()
conn = psycopg2.connect(host=host, port=int(port), dbname=db, user=user, password=pw)
cur = conn.cursor()

cur.execute("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'userrole'")
print("Enum values:", [r[0] for r in cur.fetchall()])

cur.execute("SELECT id, email, role FROM users")
print("Users:", cur.fetchall())

conn.close()
