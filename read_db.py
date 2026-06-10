import sqlite3

db_path = 'backend/kaitix.db'
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, name, depends_on_vm_id FROM virtual_machines")
    print(cur.fetchall())
except Exception as e:
    print(e)
