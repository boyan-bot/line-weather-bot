import sqlite3

DB_NAME = 'users.db'

def init_db():
    #初回起動時にDBとテーブルを作成
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
                CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
    conn.commit()
    conn.close()

def add_user(user_id):
    #新しいuserIdをDBに追加（重複はスキップ）
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (user_id) VALUES (?)",(user_id,))
        conn.commit()
    except Exception as e:
        print(f'e:\n{e}')
        #UNIQUE制約に違反した場合
        pass
    finally:
        conn.close()
