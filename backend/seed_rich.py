# -*- coding: utf-8 -*-
"""seed_rich.py - 第二阶段内容丰富种子脚本（幂等：标题去重，重复运行不产生重复数据）

基于 2026-10 热点素材生成：
- 9 个虎扑风热点帖子（C罗千球进度 / 乔丹球衣3.9亿 / 勇士不被看好 / 快艇伤病 / 中超蓉城冲冠 /
  愚者不灭发售 / 火炬之光SS14 / STEPX Neo 智能体手机 / AI眼镜新品潮），每帖 3-6 条热评
- 4 条视频（封面使用 static/uploads/ 下已下载图片），配视频评论与弹幕（正常内容）
- 为已有 user 角色用户随机分配头像（指向已下载图片，仅对空头像用户生效）

复用 seed_data.py 的连接方式与写入风格；只写库，不启动服务。
"""
import os
import random
import sqlite3

random.seed(20261020)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
DB_PATH = os.path.join(DATA_DIR, "hupu.db")

# 已下载封面图（static/uploads/），供帖子/视频封面与头像引用
UPLOAD_FILES = [
    "rule_basketball_1.jpg", "rule_basketball_2.jpg",
    "rule_football_1.jpg", "rule_football_2.jpg",
    "rule_game_1.jpg", "rule_game_2.jpg",
    "rule_tech_1.jpg", "rule_tech_2.jpg",
    "rule_nature_1.jpg", "rule_nature_2.jpg",
    "rule_scene_1.jpg", "rule_scene_2.jpg",
]
UPLOAD_URLS = [f"/uploads/{f}" for f in UPLOAD_FILES]

# ============ 帖子素材（标题 / 正文 / 分类 / 热评列表） ============
POSTS = [
    ("C罗千球进度98%！利雅得胜利大胜，总裁这是真要冲千球了",
     "刚看完比赛，利雅得胜利这场赢得太轻松了，C罗又进球了。查了下数据，职业生涯进球已经982个，距离千球就差18个，进度条已经98%。就这状态保持下去，感觉明年上半年就能看到千球里程碑了，兄弟们觉得千球之战会是哪一场？",
     "体育",
     [
         "总裁这状态踢到45岁真不是开玩笑，自律怪",
         "按他现在的效率，场均一球的话18场就搞定了，也就是两三个月的事",
         "隔壁梅西球迷已经开始沉默了哈哈哈",
         "千球俱乐部历史上估计就他一个人能进，含金量拉满",
         "别的不说，这个年龄还能稳定输出，真的respect",
         "到时候现场肯定人山人海，门票得抢破头",
     ]),
    ("乔丹「最后一舞」总冠军球衣3.9亿落槌，篮球纪念品新纪录",
     "刚看到新闻，乔丹1998年总决赛穿的那件球衣在Joopiter拍出1230万美元，折合人民币3.9亿，直接刷新乔丹个人纪念品拍卖纪录。想想当年公牛王朝，一件球衣承载的是一整个时代啊。有生之年系列，看看就好。",
     "体育",
     [
         "3.9亿，比我这辈子挣的都多，还是球衣",
         "球衣贵是因为穿上它的人叫乔丹，换我穿估计白送都没人要",
         "老流氓的商业价值真是一骑绝尘，退役多少年了还在破纪录",
         "当年总决赛录像我看了八百遍，这件球衣就是历史的注脚",
         "楼上说得对，这买的不是衣服是情怀和传奇",
         "羡慕有钱人，我连个复刻版都舍不得买",
     ]),
    ("勇士新赛季不被看好？库里：不在乎外界杂音，专注打球",
     "季前训练营库里接受采访回应了外界看衰勇士的言论：球队这几年确实错失过补强机会，但他不会把所有责任推给管理层，也不在乎外界怎么评价。新赛季西部这么卷，勇士真能顶住吗？大家怎么看。",
     "体育",
     [
         "库里这个态度就是勇士的定海神针，我永远相信他",
         "客观说，没补强还想争冠确实难，库里这话是给队友打气",
         "别急，等二轮秀打出来又是一波青春风暴（狗头）",
         "勇士球迷早就佛系了，看一场赚一场",
         "管理层是真抠，巅峰期就这么浪费，可惜了",
     ]),
    ("快艇还没开赛就5人躺进伤兵名单，这是要快沉船了？",
     "赛程还没正式开始，快艇已经有5名球员进了伤兵名单，加上之前雷纳德的签约违规重罚，整个队笼罩在阴影里。年年豪阵年年伤，这船还能开起来吗？船蜜今天破防了吗。",
     "体育",
     [
         "快艇：我们只是把伤病当成球队文化的一部分",
         "五年了，这套剧本我熟，开赛前豪言壮语，开赛后躺平",
         "卡子哥又双叒叕伤了，这合同签完直接开始养生模式",
         "船蜜表示已经麻木，心静自然凉",
         "说实话这套阵容健康的话真挺强的，可惜没有如果",
         "医疗组该换了，这伤病史太离谱",
     ]),
    ("中超冠军悬念终结？蓉城明天不败即提前夺冠",
     "中超倒数第二轮，蓉城只要不输就能提前捧杯。国安紧追不舍，但蓉城这赛季的表现确实是统治级的。作为看客都得承认，今年的蓉城配得上这个冠军。明天晚上的比赛准备蹲直播了。",
     "体育",
     [
         "蓉城今年太猛了，主场气氛也好，实至名归",
         "国安球迷路过，明年再来，恭喜蓉城",
         "这赛季中超最有悬念的不是谁夺冠，是蓉城赢几个球",
         "新鹏城都能2比2河南，中超剧本谁猜得到（狗头）",
         "提前恭喜，明天别浪就行",
         "十年蓉城球迷，今天终于等到这一天了",
     ]),
    ("《愚者不灭》10月22日发售！90秒新预告看着有点爽",
     "世雅这波宣传可以的，新动作RPG《愚者不灭》刚放出90秒游戏介绍影片，打击感和演出效果都在线，10月22日PS5/PC同步发售。这名字就很有梗，看了一眼Steam愿望单已经在涨了。发售那天有人一起冲吗。",
     "游戏",
     [
         "这游戏名字简直为我量身定制，不买说不过去",
         "动作系统看起来像那么回事，等实机评测再冲",
         "Steam钱包又要空了，10月大作扎堆真的扛不住",
         "试玩过的人说手感意外地好，期待正式版",
         "世雅这次是认真的，画面和打击感都不糊弄",
         "预约已点，别让我失望啊老哥",
     ]),
    ("火炬之光：无限SS14「塔罗斯的困兽」来了，追随者系统有点东西",
     "新赛季情报公开了，SS14加入追随者养成系统，还有新英雄特性「最终之人」，技能和体验也优化了一波，10月16日全球同步上线。刷子游戏出新赛季，懂的都懂，这个周末又有事干了。",
     "游戏",
     [
         "好耶，又可以刷爆我的肝了",
         "追随者系统要是做好玩，这赛季就有意思了",
         "火炬之光无限真是常青树，每个赛季都能整点新活",
         "新英雄特性看着挺强，开荒选它",
         "我的周末已经被SS14预定了",
         "策划终于听到玩家声音了，优化了不少痛点",
     ]),
    ("STEPX Neo 智能体手机发布：软硬模三位一体是噱头还是真变革？",
     "阶跃终端发布了首款大模型原生智能体手机STEPX Neo先行版，硬件+软件+模型三位一体，还搞了个独立MiniLED背屏给智能体当表情窗口。听着很酷，但说白了现在的AI手机不都是这个路数吗？真用起来到底是不是噱头，等实测吧。",
     "数码",
     [
         "AI手机年年有，今年特别多，先让子弹飞一会",
         "端云协同这个思路是对的，端侧快反应云侧深思考",
         "我的手机连语音助手都卡，先不凑热闹了",
         "那个背屏给智能体当表情窗口，有点中二但有点心动",
         "价格才是关键，配置吹上天不如定价实在",
         "要是真能跨应用自动办事，那确实算下一代",
     ]),
    ("AI眼镜新品潮：阿里千问N1、华为、XREAL全在冲，AI穿戴要起飞？",
     "阿里千问一口气发了N1系列AI眼镜加AI耳夹耳机，N1 Pro还有体征监测和眼动交互；华为、中兴、vivo、XREAL也在密集上新。机构都预测今年AI手机AI电脑销量要反超传统产品了。这波AI穿戴浪潮，你会入手吗。",
     "数码",
     [
         "5000万像素的眼镜，戴出去拍照会不会被人当偷拍",
         "近视党哭了，镜片一配又得多花几百",
         "眼镜+耳机+手表，出门一整套AI全家桶",
         "等第一波测评再决定，前车之鉴太多了",
         "AI眼镜如果真能全天候当翻译和助理，出差党狂喜",
         "钱包：我觉得你们数码区想让我破产",
     ]),
]

# ============ 视频素材（标题 / 简介 / 封面 / 视频评论 / 弹幕） ============
VIDEOS = [
    ("C罗千球倒计时：98%进度复盘，只差18球",
     "利雅得胜利大胜，C罗生涯进球来到982球。盘点他的进球分布与千球时间线，18球还要等多久？",
     "/uploads/rule_football_1.jpg",
     [
         "这进度条是真的，我每场都看着涨",
         "千球那天记得提醒我买球衣",
     ],
     [
         "来了来了，千球倒计时",
         "总裁加油",
         "18球而已，洒洒水",
         "刷起来",
         "这状态真稳",
         "respect",
     ]),
    ("乔丹3.9亿球衣落槌，篮球纪念品为什么这么贵",
     "「最后一舞」实穿球衣拍出1230万美元。一件衣服凭什么值3.9亿？从商业价值到历史意义一次讲清。",
     "/uploads/rule_basketball_1.jpg",
     [
         "老流氓的商业神话还在延续",
         "这球衣比我房子值钱系列",
     ],
     [
         "神穿过的衣服",
         "3.9亿 告辞",
         "篮球之神的含金量",
         "这辈子买不起系列",
         "太夸张了吧",
         "这就是传奇",
     ]),
    ("《愚者不灭》90秒实机预告解析，10月22日冲不冲",
     "世雅新动作RPG《愚者不灭》发售在即，逐帧看看这90秒预告里的打击感、演出和玩法亮点。",
     "/uploads/rule_game_1.jpg",
     [
         "预告看着确实爽，等发售",
         "名字取得好，不买不行",
     ],
     [
         "卧槽这个打击感",
         "必入",
         "10月22日见",
         "冲就完事了",
         "爽到",
         "画面可以",
     ]),
    ("STEPX Neo 智能体手机前瞻：独立背屏能给智能体开个脸？",
     "大模型原生智能体手机STEPX Neo先行版发布。软硬模三位一体怎么落地？MiniLED背屏又会怎么玩？先说结论再等实测。",
     "/uploads/rule_tech_1.jpg",
     [
         "背屏是灵魂，期待演示",
         "价格没出之前都是画饼",
     ],
     [
         "有点意思",
         "智能体手机真的来了",
         "背屏太会了",
         "等一手实测",
         "AI时代",
         "蹲一个价格",
     ]),
]

# ============ 头像分配（对空头像的 user 角色用户随机分配） ============
def assign_avatars(cur, user_ids):
    updated = 0
    for uid in user_ids:
        row = cur.execute("SELECT avatar FROM users WHERE id=?", (uid,)).fetchone()
        if row and row[0]:
            continue
        cur.execute("UPDATE users SET avatar=? WHERE id=?", (random.choice(UPLOAD_URLS), uid))
        updated += 1
    return updated


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def main():
    conn = get_conn()
    cur = conn.cursor()

    # 幂等：收集已有标题
    existing = set()
    for r in cur.execute("SELECT title FROM posts"):
        existing.add(r["title"])
    for r in cur.execute("SELECT title FROM videos"):
        existing.add(r["title"])

    # 真实用户池（排除 system/admin 与禁用用户）
    users = [r["id"] for r in cur.execute(
        "SELECT id FROM users WHERE role='user' AND status != 'banned' ORDER BY id")]
    if not users:
        print("警告: 无可用普通用户，跳过导入")
        conn.close()
        return

    n_post = n_video = n_comment = n_vc = n_dm = 0

    # 1. 帖子 + 热评
    for title, content, cat, comments in POSTS:
        if title in existing:
            continue
        author = random.choice(users)
        cur.execute(
            "INSERT INTO posts (user_id, title, content, category, status, like_count, comment_count) "
            "VALUES (?,?,?,?,?,?,0)",
            (author, title, content, cat, "visible", random.randint(20, 500)))
        pid = cur.lastrowid
        existing.add(title)
        n_post += 1
        for ctext in comments:
            cur.execute(
                "INSERT INTO comments (post_id, user_id, content, status) VALUES (?,?,?,?)",
                (pid, random.choice(users), ctext, "visible"))
            n_comment += 1
        cur.execute("UPDATE posts SET comment_count=? WHERE id=?", (len(comments), pid))

    # 2. 视频 + 视频评论 + 弹幕
    for title, desc, cover, vcomments, danmaku in VIDEOS:
        if title in existing:
            continue
        author = random.choice(users)
        cur.execute(
            "INSERT INTO videos (user_id, title, description, cover, status, view_count) "
            "VALUES (?,?,?,?,?,?)",
            (author, title, desc, cover, "approved", random.randint(5000, 120000)))
        vid = cur.lastrowid
        existing.add(title)
        n_video += 1
        for ctext in vcomments:
            cur.execute(
                "INSERT INTO video_comments (video_id, user_id, content, status) VALUES (?,?,?,?)",
                (vid, random.choice(users), ctext, "visible"))
            n_vc += 1
        for dtext in danmaku:
            cur.execute(
                "INSERT INTO danmaku (video_id, user_id, content, status) VALUES (?,?,?,?)",
                (vid, random.choice(users), dtext, "visible"))
            n_dm += 1

    # 3. 头像
    n_avatar = assign_avatars(cur, users)

    conn.commit()
    conn.close()

    print("seed_rich 导入完成")
    print(f"新增帖子: {n_post} / 热评: {n_comment}")
    print(f"新增视频: {n_video} / 视频评论: {n_vc} / 弹幕: {n_dm}")
    print(f"分配头像用户数: {n_avatar}")


if __name__ == "__main__":
    main()
