import pandas as pd

from services.db import get_conn


def _rank(df):
    df = df.sort_values(["points", "name"], ascending=[False, True]).reset_index(drop=True)
    df["rank"] = df["points"].rank(method="min", ascending=False).astype(int) if len(df) else []
    return df


def all_time():
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT id, name, COALESCE(hostel_or_dept, '') AS group_name, "
            "total_points AS points FROM users WHERE role = 'student'", conn)
    return _rank(df)


def weekly():
    with get_conn() as conn:
        df = pd.read_sql_query(
            """SELECT u.id, u.name, COALESCE(u.hostel_or_dept, '') AS group_name,
                      COALESCE(SUM(p.points), 0) AS points
               FROM users u LEFT JOIN points_log p
                 ON p.user_id = u.id AND p.created_at >= datetime('now', '-7 days')
               WHERE u.role = 'student' GROUP BY u.id""", conn)
    df["points"] = df["points"].clip(lower=0)
    return _rank(df)


def by_group():
    df = all_time()
    df = df[df["group_name"] != ""]
    if df.empty:
        return pd.DataFrame(columns=["group_name", "members", "total", "average"])
    g = df.groupby("group_name")["points"].agg(members="count", total="sum", average="mean").reset_index()
    g["average"] = g["average"].round(1)
    return g.sort_values(["total", "group_name"], ascending=[False, True]).reset_index(drop=True)