"""种子数据脚本：为交流平台录入帖子/视频/弹幕/评论基础数据（数据基于近期网络热点素材）"""
import json
import os
import random
import sqlite3

random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
DB_PATH = os.path.join(DATA_DIR, "hupu.db")
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")
COVER_DIR = os.path.join(STATIC_DIR, "covers")

# 弹幕语料（真实网络弹幕，来自毕设训练集 processed_v2）
DANMAKU_SRC = r"C:\Users\swerey.SWEREY\PycharmProjects\PythonProject2\data\processed_v2\train.jsonl"

LABEL_MAP = {0: "正常", 1: "色情低俗", 2: "辱骂暴力", 3: "广告引流", 4: "敏感言论", 5: "歧视煽动"}

# ============ 帖子素材（基于2026年10月网络热点） ============
POSTS = [
    # (title, content, category, is_bad, label_id)
    ("2026旗舰横评：OPPO Find X10、小米18 Pro、iPhone 18 Pro 怎么选",
     "最近把三台旗舰都摸了一遍。Find X10双2亿影像+8000mAh大电池，性价比是真的高；小米18 Pro小屏手感好还有防窥屏；iPhone 18 Pro生态和视频能力强但价格也最顶。预算够就按需选，看重续航影像选OPPO，小屏党选小米，苹果生态用户闭眼iPhone。",
     "数码", False, 0),
    ("GTA6 定档 11 月 19 日，但可能错过 TGA 年度提名？",
     "GTA6 终于定档了，但 TGA 提名投票截止一般在 11 月中旬，留给评委通关的时间不足一周。年度最佳之争还没开始就要结束了吗？大家怎么看。",
     "游戏", False, 0),
    ("《影之刃零》10月29日发售，国产武侠黑马预定",
     "定档 10 月 29 日 PS5/PC 双端。实机演示的打击感和武侠味都很足，外媒已经把国产武侠当成年度黑马候选了。预约走起。",
     "游戏", False, 0),
    ("《生化危机9：安魂曲》口碑炸裂，年度最佳有力竞争者",
     "M 站 89 分，用户评分 9.5 创历史纪录。恐怖氛围、流程设计都在线，Capcom 今年是真高产。",
     "游戏", False, 0),
    ("TGA 年度游戏大预测：今年真是最难选的一年",
     "皇牌空战30周年、控制:共振、火焰纹章、生化9、影之刃零……各有拥趸，没有绝对统治力作品。评论区聊聊你心中的年度最佳。",
     "游戏", False, 0),
    ("国庆档破10亿，《神探之痕迹》凭什么称霸",
     "3.7亿稳坐冠军。剧本扎实悬疑节奏好，张译稳，陈飞宇演反派是最大惊喜。今年票房真的是口碑驱动了。",
     "影视", False, 0),
    ("《牧神记》百集里程碑，国漫顶流名副其实",
     "B站年番两年播放22亿+，追番700万+。原著还原度高，打戏在线，国风质感拉满，路人也能圈粉。",
     "影视", False, 0),
    ("《伟大的长征》今晚央视开播，能否复刻《觉醒年代》神话",
     "觉醒年代原班主创，张永新执导，于和伟王劲松领衔。筹备五年、三次重走长征路。60集体量对节奏是考验，期待一下。",
     "影视", False, 0),
    ("高速服务区充电桩假期变慢充，新能源车主太难了",
     "假期高速充电排队久、充电慢，闪充直接变慢充。多家车企已经回应要优化节假日充电服务。这个痛点什么时候能解决。",
     "科技", False, 0),
    ("华为 Mate 80 系列到底值不值得冲",
     "麒麟芯片+鸿蒙，信号续航影像综合很强，商务人群关注度很高。用过的朋友说说实际体验。",
     "数码", False, 0),
    ("国庆拼假出游，全世界都知道中国人放假了",
     "中秋国庆双节叠加拼出超长假期，出境游热度爆炸，国外景区全是同胞。这波你出门了吗。",
     "生活", False, 0),
    ("218元全资进组横店演戏，年轻人图什么",
     "自费小额进组体验拍戏，有人觉得是圆梦有人觉得是韭菜。横店追梦文化你怎么看。",
     "生活", False, 0),
    ("老年旅客火车票将享折上折，你支持吗",
     "年满60周岁购指定车次车票可享折上折，不限定周中时段。惠民举措越来越细了。",
     "生活", False, 0),
    # 违规示例帖子（触发审核折叠）
    ("这游戏策划就是个脑残，改得什么玩意",
     "新版本平衡性改得稀烂，剑人策划脑子进水，退坑了。", "游戏", True, 2),
    ("某些主播为了流量真的什么都干得出来",
     "深夜直播间卖擦边内容，真当大家不看吗，恶心。", "闲聊", True, 1),
]

# ============ 视频素材 ============
VIDEOS = [
    ("《影之刃零》15分钟实机演示", "国产武侠动作新作，打击感拉满，10月29日正式发售。"),
    ("GTA6 最新预告深度解析", "定档11月19日，逐帧解析预告细节与发售悬念。"),
    ("iPhone 18 Pro 上手体验", "A20 Pro 芯片、四档可变光圈，视频能力全面提升。"),
    ("OPPO Find X10 影像实测", "双2亿影像+8000mAh大电池，性价比旗舰实拍对比。"),
    ("小米18 Pro 深度评测", "小屏旗舰手感+硬件级防窥屏，2nm骁龙8至尊版体验。"),
    ("国庆档《神探之痕迹》观后感", "聊聊这部3.7亿票房冠军为什么好看。"),
    ("《牧神记》百集名场面混剪", "两年22亿播放的国漫顶流，高光时刻一次看爽。"),
    ("高速充电桩实测：假期真的变慢充吗", "国庆假期服务区充电桩实测，闪充变慢充实锤了吗。"),
]

# ============ 评论素材 ============
COMMENTS = [
    (1, 0, "OPPO这次确实良心，影像不缩水还有大电池"),
    (1, 1, "小米18 Pro 防窥屏上班摸鱼神器"),
    (1, 2, "iPhone 18 Pro 价格劝退，但生态真的值"),
    (4, 0, "生化9流程和氛围都顶级，恐怖爱好者必玩"),
    (5, 1, "我投影之刃零一票，国产武侠终于站起来了"),
    (6, 0, "陈飞宇演反派真的颠覆，演技进步很大"),
    (6, 2, "国庆档终于不是烂片扎堆了，口碑驱动好评"),
    (11, 0, "出去玩人太多了，但真的快乐"),
    (11, 2, "国内景区挤，国外景区更挤哈哈哈"),
    (12, 1, "圆梦可以，别被割韭菜就行"),
    (1, 1, "楼主就是个傻逼，三家都买不起在这指点江山"),  # 违规折叠
    (2, 2, "GTA6 要是错过 TGA 就太冤了，主办方该破例"), 
]

# ============ 演示用户 ============
USERS = [
    ("shuishui", "水水", "user"),
    ("awei", "阿伟", "user"),
    ("yingmi", "影迷小张", "user"),
    ("dianmao", "数码老王", "user"),
    ("wanjia", "打游戏不菜", "user"),
]


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def make_cover(idx, title):
    """PIL 生成渐变封面图"""
    os.makedirs(COVER_DIR, exist_ok=True)
    path = os.path.join(COVER_DIR, f"video{idx}.png")
    try:
        from PIL import Image, ImageDraw, ImageFont
        import random as r
        w, h = 640, 360
        img = Image.new("RGB", (w, h))
        d = ImageDraw.Draw(img)
        c1 = (r.randint(30, 90), r.randint(30, 90), r.randint(60, 120))
        c2 = (r.randint(100, 160), r.randint(80, 140), r.randint(140, 200))
        for y in range(h):
            t = y / h
            d.line([(0, y), (w, y)], fill=(
                int(c1[0] + (c2[0] - c1[0]) * t),
                int(c1[1] + (c2[1] - c1[1]) * t),
                int(c1[2] + (c2[2] - c1[2]) * t),
            ))
        font = None
        for fp in [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
            try:
                font = ImageFont.truetype(fp, 28)
                break
            except Exception:
                continue
        d.text((30, 150), title[:14], fill=(255, 255, 255), font=font)
        img.save(path, "PNG")
        return f"/covers/video{idx}.png"
    except Exception as e:
        print("cover fail:", e)
        return ""


def load_danmaku_pool():
    """从弹幕语料抽样本：正常60条 + 各违规类12条"""
    if not os.path.exists(DANMAKU_SRC):
        print("警告: 弹幕语料不存在，跳过弹幕导入", DANMAKU_SRC)
        return []
    pools = {i: [] for i in range(6)}
    with open(DANMAKU_SRC, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            label = obj["label"]
            if len(pools[label]) < 300:
                pools[label].append(obj["text"])
    result = []
    for i in [0]:
        for t in random.sample(pools[0], 60):
            result.append((t, 0))
    for i in [1, 2, 3, 4, 5]:
        for t in random.sample(pools[i], 12):
            result.append((t, i))
    return result


def main():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM posts")
    if cur.fetchone()[0] > 0:
        print("已存在种子数据，跳过导入。如需重置请先清空数据库。")
        conn.close()
        return

    from auth import hash_password

    # 1. 用户
    user_ids = {}
    for username, nick, role in USERS:
        cur.execute("INSERT INTO users (username, password_hash, nickname, role, credit_score) VALUES (?,?,?,?,?)",
                    (username, hash_password("123456"), nick, role, random.randint(80, 100)))
        user_ids[username] = cur.lastrowid
    cur.execute("SELECT id FROM users WHERE username='admin'")
    admin_id = cur.fetchone()[0]

    # 2. 帖子（含违规示例）
    for i, (title, content, cat, is_bad, label_id) in enumerate(POSTS):
        author = random.choice(list(user_ids.values()))
        status = "visible"
        if is_bad:
            status = "folded"
            risk = "high" if label_id in (1, 4) else "medium"
            action = "blocked" if label_id in (1, 4) else "folded"
            cur.execute("INSERT INTO violations (user_id, content, source_type, source_id, label, risk_level, action) VALUES (?,?,?,?,?,?,?)",
                        (author, content[:100], "post", 0, LABEL_MAP[label_id], risk, action))
        cur.execute("INSERT INTO posts (user_id, title, content, category, status, like_count, comment_count) VALUES (?,?,?,?,?,?,0)",
                    (author, title, content, cat, status, random.randint(0, 300)))
        pid = cur.lastrowid
        if is_bad:
            cur.execute("UPDATE violations SET source_id=? WHERE source_type='post' AND source_id=0", (pid,))
        post_ids[i] = pid

    # 3. 视频 + 封面
    video_ids = []
    for i, (title, desc) in enumerate(VIDEOS, start=1):
        author = random.choice(list(user_ids.values()))
        cover = make_cover(i, title)
        cur.execute("INSERT INTO videos (user_id, title, description, cover, status, view_count) VALUES (?,?,?,?,?,?)",
                    (author, title, desc, cover, "approved", random.randint(500, 50000)))
        video_ids.append(cur.lastrowid)

    # 4. 评论
    for post_idx, user_idx, content in COMMENTS:
        pid = post_ids[post_idx - 1]
        uid = list(user_ids.values())[user_idx % len(user_ids)]
        status = "visible"
        if "傻逼" in content:
            status = "folded"
            cur.execute("INSERT INTO violations (user_id, content, source_type, source_id, label, risk_level, action) VALUES (?,?,?,?,?,?,?)",
                        (uid, content, "comment", pid, "辱骂暴力", "medium", "folded"))
        cur.execute("INSERT INTO comments (post_id, user_id, content, status) VALUES (?,?,?,?)",
                    (pid, uid, content, status))
        cur.execute("UPDATE posts SET comment_count=comment_count+1 WHERE id=?", (pid,))

    # 5. 弹幕（正常+违规，违规弹幕走拦截）
    pool = load_danmaku_pool()
    vid_normal = video_ids[0]
    vid_hot = video_ids[3]
    for text, label in pool:
        vid = vid_normal if label == 0 else vid_hot
        uid = random.choice(list(user_ids.values()))
        if label == 0:
            cur.execute("INSERT INTO danmaku (video_id, user_id, content, status) VALUES (?,?,?,?)",
                        (vid, uid, text, "visible"))
        else:
            cur.execute("INSERT INTO danmaku (video_id, user_id, content, status) VALUES (?,?,?,?)",
                        (vid, uid, text, "blocked"))
            risk = "high" if label in (1, 4) else "medium"
            action = "blocked"
            cur.execute("INSERT INTO violations (user_id, content, source_type, source_id, label, risk_level, action) VALUES (?,?,?,?,?,?,?)",
                        (uid, text, "danmaku", vid, LABEL_MAP[label], risk, action))

    conn.commit()
    conn.close()

    counts = {}
    cur = conn = None
    conn = get_conn()
    for tbl in ["users", "posts", "videos", "comments", "danmaku", "violations"]:
        conn.row_factory = sqlite3.Row
        counts[tbl] = conn.execute(f"SELECT COUNT(*) c FROM {tbl}").fetchone()["c"]
    conn.close()
    print("导入完成:", counts)


if __name__ == "__main__":
    post_ids = {}
    main()
