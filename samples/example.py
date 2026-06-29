def get_user(user_id):
    import sqlite3
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = " + str(user_id))
    return cur.fetchone()
