"""
数据库模块 — 使用 SQLite 存储团队日报、OKR 和成员信息。
所有数据保存在本地文件 bot_data.db 中，无需安装额外数据库软件。
"""

import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "bot_data.db"


def get_connection() -> sqlite3.Connection:
    """获取数据库连接。每次调用都返回新连接，记得用完关闭。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row          # 让查询结果可以像字典一样访问
    conn.execute("PRAGMA journal_mode=WAL") # 提高并发写入性能
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表（首次运行时自动创建）。"""
    conn = get_connection()
    cur = conn.cursor()

    # ---- 成员表：记录团队所有成员 ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER UNIQUE NOT NULL,   -- Telegram 用户 ID
            username      TEXT,                       -- Telegram 用户名（可选）
            display_name  TEXT NOT NULL,              -- 显示名称
            role          TEXT NOT NULL DEFAULT 'member', -- 'admin' 或 'member'
            joined_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---- 日报表：记录每个人的每日汇报 ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            username    TEXT,
            report_date DATE NOT NULL,                -- 汇报日期
            completed   TEXT NOT NULL DEFAULT '',     -- 今日完成
            planned     TEXT NOT NULL DEFAULT '',     -- 明日计划
            blockers    TEXT NOT NULL DEFAULT '',     -- 阻塞 / 需要帮助
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES members(user_id)
        )
    """)

    # ---- 索引：加速按日期和用户查询 ----
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_date
        ON reports(report_date)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_user_date
        ON reports(user_id, report_date)
    """)

    # ---- OKR 表：记录团队和个人的 OKR ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS okrs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            username     TEXT,
            quarter      TEXT NOT NULL,               -- 例如 "2026-Q2"
            objective    TEXT NOT NULL,               -- 目标（O）
            key_results  TEXT NOT NULL DEFAULT '',    -- 关键结果（KR），用换行分隔
            progress     INTEGER DEFAULT 0,           -- 进度百分比 0-100
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES members(user_id)
        )
    """)

    conn.commit()
    conn.close()


# ==================== 成员管理 ====================

def ensure_member(user_id: int, username: str = None, display_name: str = None):
    """
    确保成员存在于数据库中。如果不存在则自动创建。
    用于：任何团队成员第一次与 Bot 互动时自动注册。
    """
    conn = get_connection()
    cur = conn.cursor()

    name = display_name or username or str(user_id)

    cur.execute(
        "INSERT OR IGNORE INTO members (user_id, username, display_name, role) VALUES (?, ?, ?, 'member')",
        (user_id, username, name),
    )
    # 如果已存在但用户名变了，更新它
    cur.execute(
        "UPDATE members SET username = ?, display_name = COALESCE(?, display_name) WHERE user_id = ?",
        (username, display_name, user_id)
    )

    conn.commit()
    conn.close()


def set_admin(user_id: int):
    """将某个成员设置为管理员（就是你本人）。"""
    conn = get_connection()
    conn.execute("UPDATE members SET role = 'admin' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def is_admin(user_id: int) -> bool:
    """检查某个用户是否是管理员。"""
    conn = get_connection()
    row = conn.execute("SELECT role FROM members WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row is not None and row["role"] == "admin"


def get_all_members():
    """获取所有团队成员列表。"""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM members ORDER BY role DESC, joined_at ASC").fetchall()
    conn.close()
    return rows


# ==================== 日报管理 ====================

def save_report(user_id: int, username: str, completed: str, planned: str, blockers: str,
                report_date: str = None):
    """
    保存一份日报。如果当天已有日报，则更新；否则新增（一人一天一份）。
    """
    if report_date is None:
        report_date = datetime.date.today().isoformat()

    conn = get_connection()
    cur = conn.cursor()

    # 确保成员存在
    ensure_member(user_id, username)

    # 如果当天已有汇报 → 更新
    existing = cur.execute(
        "SELECT id FROM reports WHERE user_id = ? AND report_date = ?",
        (user_id, report_date),
    ).fetchone()

    if existing:
        cur.execute("""
            UPDATE reports
            SET completed = ?, planned = ?, blockers = ?, username = ?, created_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (completed, planned, blockers, username, existing["id"]))
    else:
        cur.execute("""
            INSERT INTO reports (user_id, username, report_date, completed, planned, blockers)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, username, report_date, completed, planned, blockers))

    conn.commit()
    conn.close()


def get_today_reports():
    """获取今天所有人的日报。"""
    today = datetime.date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM reports WHERE report_date = ? ORDER BY created_at DESC", (today,)
    ).fetchall()
    conn.close()
    return rows


def get_user_reports(user_id: int, days: int = 7):
    """获取某个成员最近 N 天的日报。"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM reports
        WHERE user_id = ?
        ORDER BY report_date DESC
        LIMIT ?
    """, (user_id, days)).fetchall()
    conn.close()
    return rows


def get_all_reports_since(days: int = 7):
    """获取最近 N 天所有人的日报（用于生成汇总）。"""
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM reports
        WHERE report_date >= ?
        ORDER BY report_date DESC, created_at DESC
    """, (cutoff,)).fetchall()
    conn.close()
    return rows


def get_members_without_report_today():
    """找出今天还没有提交日报的成员。"""
    today = datetime.date.today().isoformat()
    conn = get_connection()
    rows = conn.execute("""
        SELECT m.* FROM members m
        WHERE m.user_id NOT IN (
            SELECT user_id FROM reports WHERE report_date = ?
        )
        AND m.role = 'member'
    """, (today,)).fetchall()
    conn.close()
    return rows


def get_unresolved_blockers(days: int = 3):
    """
    查找连续 N 天都有阻塞事项的成员（用于预警）。
    返回：[(user_id, username, blocker_text, 连续天数), ...]
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT user_id, username, blockers, report_date
        FROM reports
        WHERE blockers != '' AND report_date >= date('now', ?)
        ORDER BY user_id, report_date DESC
    """, (f'-{days} days',)).fetchall()
    conn.close()

    # 按用户分组，检查连续性
    from collections import defaultdict
    user_blockers = defaultdict(list)
    for r in rows:
        if r["blockers"].strip():
            user_blockers[r["user_id"]].append({
                "date": r["report_date"],
                "blocker": r["blockers"],
                "username": r["username"],
            })

    # 找出连续有阻塞的用户
    alerts = []
    for uid, entries in user_blockers.items():
        if len(entries) >= 2:  # 至少连续2天
            alerts.append({
                "user_id": uid,
                "username": entries[0]["username"],
                "blockers": [e["blocker"] for e in entries],
                "consecutive_days": len(entries),
            })
    return alerts


# ==================== OKR 管理 ====================

def set_okr(user_id: int, username: str, quarter: str, objective: str, key_results: str):
    """为成员设定 OKR。同一个季度覆盖更新。"""
    conn = get_connection()
    cur = conn.cursor()

    existing = cur.execute(
        "SELECT id FROM okrs WHERE user_id = ? AND quarter = ?",
        (user_id, quarter),
    ).fetchone()

    if existing:
        cur.execute("""
            UPDATE okrs SET objective = ?, key_results = ?, username = ?
            WHERE id = ?
        """, (objective, key_results, username, existing["id"]))
    else:
        cur.execute("""
            INSERT INTO okrs (user_id, username, quarter, objective, key_results)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, quarter, objective, key_results))

    conn.commit()
    conn.close()


def get_user_okr(user_id: int, quarter: str = None):
    """获取某个成员的 OKR。"""
    conn = get_connection()
    if quarter:
        row = conn.execute(
            "SELECT * FROM okrs WHERE user_id = ? AND quarter = ? ORDER BY created_at DESC LIMIT 1",
            (user_id, quarter),
        ).fetchone()
    else:
        # 默认当前季度
        now = datetime.date.today()
        q = f"{now.year}-Q{(now.month - 1) // 3 + 1}"
        row = conn.execute(
            "SELECT * FROM okrs WHERE user_id = ? AND quarter = ? ORDER BY created_at DESC LIMIT 1",
            (user_id, q),
        ).fetchone()
    conn.close()
    return row


def get_all_okrs(quarter: str = None):
    """获取全队 OKR。"""
    if quarter is None:
        now = datetime.date.today()
        quarter = f"{now.year}-Q{(now.month - 1) // 3 + 1}"

    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM okrs WHERE quarter = ? ORDER BY user_id", (quarter,)
    ).fetchall()
    conn.close()
    return rows


# ==================== 适配器（供 bot_handlers 使用）====================

def get_user_role(user_id: int) -> str:
    """返回用户的角色字符串：'admin' 或 'member'"""
    if is_admin(user_id):
        return "admin"
    return "member"

def set_user_role(user_id: int, role: str):
    """设置用户角色"""
    conn = get_connection()
    conn.execute("UPDATE members SET role = ? WHERE user_id = ?", (role, user_id))
    conn.commit()
    conn.close()

def get_week_reports():
    """获取最近一周的所有日报"""
    return get_all_reports_since(days=7)

def get_all_users():
    """获取所有用户"""
    result = get_all_members()
    return [{"user_id": r["user_id"], "username": r["username"] or str(r["user_id"])}
            for r in result]

def save_okr(username: str, objective: str, key_results: list):
    """保存 OKR — 适配器，username 直接用作 user_id 映射"""
    conn = get_connection()
    row = conn.execute(
        "SELECT user_id FROM members WHERE username = ? OR display_name = ?",
        (username, username)
    ).fetchone()
    conn.close()
    if row:
        user_id = row["user_id"]
    else:
        # 如果用户不存在，用 username 的哈希作为临时 ID
        user_id = abs(hash(username)) % (10 ** 9)
        ensure_member(user_id, username)

    now = datetime.date.today()
    quarter = f"{now.year}-Q{(now.month - 1) // 3 + 1}"
    krs_text = "\n".join(key_results)
    set_okr(user_id, username, quarter, objective, krs_text)

def get_user_reports_by_username(username: str, days: int = 7):
    """通过用户名获取日报"""
    conn = get_connection()
    row = conn.execute(
        "SELECT user_id FROM members WHERE username = ? OR display_name = ?",
        (username, username)
    ).fetchone()
    conn.close()
    if row:
        return get_user_reports(row["user_id"], days)
    return []


# ==================== 启动时调用 ====================

if __name__ == "__main__":
    init_db()
    print("✅ 数据库初始化完成！")
