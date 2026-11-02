"""数据库连接与建表（sqlite3 标准库实现，无额外依赖）"""

import os
import sqlite3
import threading
from contextlib import contextmanager

from config import DATABASE_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
# M6：数据库路径集中到 config（默认 data/hupu.db，测试可用环境变量 HUPU_DB_PATH 指向临时库）
DB_PATH = DATABASE_PATH

_lock = threading.RLock()


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def db_cursor():
    """获取游标上下文，自动提交/回滚/关闭"""
    conn = get_conn()
    try:
        with _lock:
            cur = conn.cursor()
            yield cur
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """创建所有数据表"""
    with db_cursor() as cur:
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nickname TEXT NOT NULL DEFAULT '',
            avatar TEXT DEFAULT '',
            credit_score INTEGER NOT NULL DEFAULT 100,
            role TEXT NOT NULL DEFAULT 'user',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            file_path TEXT DEFAULT '',
            cover TEXT DEFAULT '',
            cover_url TEXT DEFAULT '',
            url TEXT DEFAULT '',
            audit_json TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            view_count INTEGER NOT NULL DEFAULT 0,
            duration INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT DEFAULT '',
            category TEXT NOT NULL DEFAULT '闲聊',
            status TEXT NOT NULL DEFAULT 'visible',
            like_count INTEGER NOT NULL DEFAULT 0,
            comment_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'visible',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS danmaku (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'visible',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (video_id) REFERENCES videos(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS video_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'visible',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (video_id) REFERENCES videos(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL DEFAULT 0,
            label TEXT NOT NULL DEFAULT '',
            risk_level TEXT NOT NULL DEFAULT 'low',
            action TEXT NOT NULL DEFAULT 'warned',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS post_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            UNIQUE(post_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            follow_user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            UNIQUE(user_id, follow_user_id)
        );

        CREATE TABLE IF NOT EXISTS review_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            label TEXT NOT NULL DEFAULT '',
            risk_level TEXT NOT NULL DEFAULT 'mid',
            status TEXT NOT NULL DEFAULT 'pending',
            action TEXT DEFAULT '',
            handled_by INTEGER DEFAULT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            handled_at TEXT
        );

        CREATE TABLE IF NOT EXISTS live_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            cover TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'off',
            viewer_count INTEGER NOT NULL DEFAULT 0,
            started_at TEXT,
            stream_type TEXT NOT NULL DEFAULT '',   -- 直播来源类型：camera=摄像头 / game=游戏画面（屏幕/窗口捕获）
            ended_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS live_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'visible',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (room_id) REFERENCES live_rooms(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 主页推荐轮播：仅存手动置顶项，自动聚合动态计算
        CREATE TABLE IF NOT EXISTS carousel_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL CHECK (item_type IN ('post', 'video')),
            item_id INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            start_at TEXT,
            end_at TEXT,
            created_by INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_carousel_type_id ON carousel_items(item_type, item_id);
        CREATE INDEX IF NOT EXISTS idx_carousel_order ON carousel_items(sort_order, created_at);

        CREATE TABLE IF NOT EXISTS appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL DEFAULT 0,
            reason TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            reply TEXT DEFAULT '',
            handled_by INTEGER DEFAULT NULL,
            handled_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS credit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            delta INTEGER NOT NULL DEFAULT 0,
            reason TEXT NOT NULL DEFAULT '',
            ref_id INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operator_id INTEGER NOT NULL DEFAULT 0,
            action TEXT NOT NULL DEFAULT '',
            target_type TEXT DEFAULT '',
            target_id INTEGER DEFAULT 0,
            detail TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (operator_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS live_bans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            ban_type TEXT NOT NULL DEFAULT 'kick',
            reason TEXT DEFAULT '',
            operator_id INTEGER DEFAULT NULL,
            expires_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (room_id) REFERENCES live_rooms(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS banned_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT '辱骂暴力',
            risk_level TEXT NOT NULL DEFAULT 'mid',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_violations_created ON violations(created_at);
        CREATE INDEX IF NOT EXISTS idx_violations_label ON violations(label);
        CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category);
        CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
        CREATE INDEX IF NOT EXISTS idx_posts_like ON posts(like_count, created_at);
        CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);
        CREATE INDEX IF NOT EXISTS idx_comments_user ON comments(user_id);
        CREATE INDEX IF NOT EXISTS idx_danmaku_user ON danmaku(user_id);
        CREATE INDEX IF NOT EXISTS idx_danmaku_video ON danmaku(video_id);
        CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);
        CREATE INDEX IF NOT EXISTS idx_video_comments_video ON video_comments(video_id);
        CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status);
        CREATE INDEX IF NOT EXISTS idx_live_rooms_status ON live_rooms(status);
        CREATE INDEX IF NOT EXISTS idx_live_messages_room ON live_messages(room_id);
        CREATE INDEX IF NOT EXISTS idx_appeals_user ON appeals(user_id);
        CREATE INDEX IF NOT EXISTS idx_appeals_status ON appeals(status);
        CREATE INDEX IF NOT EXISTS idx_credit_log_user ON credit_log(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_log_op ON audit_log(operator_id);
        CREATE INDEX IF NOT EXISTS idx_live_bans_room ON live_bans(room_id);
        -- S5：数据量大时防慢查询 —— 弹幕/评论按 视频/帖子 + 状态 + 时间 复合索引
        CREATE INDEX IF NOT EXISTS idx_danmaku_video_status ON danmaku(video_id, status, id);
        CREATE INDEX IF NOT EXISTS idx_comments_post_status ON comments(post_id, status, id);
        CREATE INDEX IF NOT EXISTS idx_video_comments_video_status ON video_comments(video_id, status, id);
        CREATE INDEX IF NOT EXISTS idx_violations_user_created ON violations(user_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_review_queue_status_risk ON review_queue(status, risk_level, created_at);
        CREATE INDEX IF NOT EXISTS idx_live_messages_room_status ON live_messages(room_id, status, id);
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,          -- 举报人
            target_type TEXT NOT NULL,          -- posts/videos/danmaku/comments/video_comments/live_messages
            target_id INTEGER NOT NULL,
            reason TEXT NOT NULL DEFAULT '',    -- 举报理由（可空）
            status TEXT NOT NULL DEFAULT 'pending',   -- pending/resolved
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            handled_by INTEGER,
            handled_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
        CREATE INDEX IF NOT EXISTS idx_reports_target ON reports(target_type, target_id);
        CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id);
        """)

        # 兼容已有库：users 表补充 status 字段（封禁状态 active/banned）
        user_cols = cur.execute("PRAGMA table_info(users)").fetchall()
        if not any(c["name"] == "status" for c in user_cols):
            cur.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        # users 补 banned_reason / banned_until（封禁原因与到期时间，T11）
        if not any(c["name"] == "banned_reason" for c in user_cols):
            cur.execute("ALTER TABLE users ADD COLUMN banned_reason TEXT DEFAULT ''")
        if not any(c["name"] == "banned_until" for c in user_cols):
            cur.execute("ALTER TABLE users ADD COLUMN banned_until TEXT")
        # users 表 phone（手机号搜索，批次三B新增）
        if not any(c["name"] == "phone" for c in user_cols):
            cur.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''")

        # videos 补 audit_json / url / cover_url（审核结果明细持久化与上传资源地址）
        video_cols = cur.execute("PRAGMA table_info(videos)").fetchall()
        if not any(c["name"] == "audit_json" for c in video_cols):
            cur.execute("ALTER TABLE videos ADD COLUMN audit_json TEXT DEFAULT ''")
        if not any(c["name"] == "url" for c in video_cols):
            cur.execute("ALTER TABLE videos ADD COLUMN url TEXT DEFAULT ''")
        if not any(c["name"] == "cover_url" for c in video_cols):
            cur.execute("ALTER TABLE videos ADD COLUMN cover_url TEXT DEFAULT ''")
        if not any(c["name"] == "duration" for c in video_cols):
            cur.execute("ALTER TABLE videos ADD COLUMN duration INTEGER NOT NULL DEFAULT 0")

        # violations 补 reverted（误判回退标记：1=已回退信用，0=未回退）
        viol_cols = cur.execute("PRAGMA table_info(violations)").fetchall()
        if not any(c["name"] == "reverted" for c in viol_cols):
            cur.execute("ALTER TABLE violations ADD COLUMN reverted INTEGER NOT NULL DEFAULT 0")

        # posts 补 summary（帖子简介字段，用户互访主页/帖子卡片展示）
        post_cols = cur.execute("PRAGMA table_info(posts)").fetchall()
        if not any(c["name"] == "summary" for c in post_cols):
            cur.execute("ALTER TABLE posts ADD COLUMN summary TEXT DEFAULT ''")

        # live_rooms 补 stream_type / ended_at（摄像头/游戏直播来源类型、结束时间，兼容已有库）
        live_cols = cur.execute("PRAGMA table_info(live_rooms)").fetchall()
        if not any(c["name"] == "stream_type" for c in live_cols):
            cur.execute("ALTER TABLE live_rooms ADD COLUMN stream_type TEXT NOT NULL DEFAULT ''")
        if not any(c["name"] == "ended_at" for c in live_cols):
            cur.execute("ALTER TABLE live_rooms ADD COLUMN ended_at TEXT")

        # 默认管理员账号 admin/admin123
        cur.execute("SELECT id FROM users WHERE username=?", ("admin",))
        if cur.fetchone() is None:
            from auth import hash_password
            cur.execute(
                "INSERT INTO users (username, password_hash, nickname, role, credit_score) VALUES (?,?,?,?,?)",
                ("admin", hash_password("admin123"), "管理员", "admin", 100),
            )

        # M6：确保系统操作者用户 id=0 存在（audit_log 外键约束），供自动处置（模型/词典拦截等）写审计日志
        cur.execute(
            "INSERT OR IGNORE INTO users (id, username, password_hash, nickname, role, credit_score) "
            "VALUES (0, 'system', '*', '系统', 'admin', 100)"
        )
