from services.db import get_conn


def is_following(user_id, bin_id):
    with get_conn() as conn:
        return conn.execute("SELECT 1 FROM follows WHERE user_id = ? AND bin_id = ?",
                            (user_id, bin_id)).fetchone() is not None


def follow(user_id, bin_id):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO follows (user_id, bin_id) VALUES (?,?)",
                     (user_id, bin_id))


def unfollow(user_id, bin_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM follows WHERE user_id = ? AND bin_id = ?", (user_id, bin_id))