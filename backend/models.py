"""数据模型定义：表结构常量与状态枚举"""

# ---- 用户信用分规则 ----
CREDIT_PENALTY = {
    "high": 5,   # 高危违规扣 5 分
    "mid": 3,    # 中危违规扣 3 分
    "low": 1,    # 低危违规扣 1 分
}

CREDIT_RECOVER = 1          # 每发布 1 条通过审核的内容恢复 1 分（上限 100）
CREDIT_DAILY_RECOVER_LIMIT = 3  # 每日最多恢复 3 分（T12）

# ---- 存疑审核队列状态 ----
REVIEW_PENDING = "pending"
REVIEW_RESOLVED = "resolved"
REVIEW_AUTO_FOLDED = "auto_folded"

# ---- 申诉状态 ----
APPEAL_PENDING = "pending"
APPEAL_APPROVED = "approved"
APPEAL_REJECTED = "rejected"

# ---- 直播间封禁类型 ----
BAN_KICK = "kick"
BAN_MUTE = "mute"

# ---- 审核动作 ----
ACTION_BLOCKED = "blocked"
ACTION_FOLDED = "folded"
ACTION_WARNED = "warned"
ACTION_BANNED = "banned"
ACTION_REVERTED = "reverted"

# ---- 内容状态 ----
# visible: 正常展示
# folded:  折叠显示（中危违规）
# blocked: 拦截（高危违规，不展示）
# warned:  低危提示（展示但标注提示）
# banned:  管理员确认封禁（不展示）
STATUS_VISIBLE = "visible"
STATUS_FOLDED = "folded"
STATUS_BLOCKED = "blocked"
STATUS_WARNED = "warned"
STATUS_BANNED = "banned"

# ---- 视频状态 ----
STATUS_VIDEO_PENDING = "pending"
STATUS_VIDEO_APPROVED = "approved"
STATUS_VIDEO_REJECTED = "rejected"

# ---- 用户状态 ----
USER_STATUS_ACTIVE = "active"
USER_STATUS_BANNED = "banned"

# ---- 违规来源类型 ----
SOURCE_POST = "posts"
SOURCE_COMMENT = "comments"
SOURCE_VIDEO_COMMENT = "video_comment"
SOURCE_DANMAKU = "danmaku"
SOURCE_VIDEO = "videos"
SOURCE_LIVE = "live"

# ---- 风险等级 ----
RISK_HIGH = "high"
RISK_MID = "mid"
RISK_LOW = "low"

# ---- 六分类标签 ----
LABEL_MAP = {
    0: "正常",
    1: "色情低俗",
    2: "辱骂暴力",
    3: "广告引流",
    4: "敏感言论",
    5: "歧视煽动",
}

# 标签 -> 风险等级
LABEL_RISK = {
    "色情低俗": RISK_HIGH,
    "敏感言论": RISK_HIGH,
    "辱骂暴力": RISK_MID,
    "歧视煽动": RISK_MID,
    "广告引流": RISK_LOW,
}

# 板块分类
CATEGORIES = ["推荐", "科技", "游戏", "影视", "数码", "体育", "生活", "求助", "闲聊"]
