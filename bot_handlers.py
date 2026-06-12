"""
Bot 命令处理器 —— 所有 / 命令的具体实现
包括：日报提交流程、智能汇总、进度查询、OKR 管理、成员分析
"""
import datetime
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from database import (
    save_report, get_user_reports_by_username, get_today_reports,
    get_week_reports, get_all_users, set_user_role,
    get_user_role, save_okr, get_all_okrs, get_user_okr
)
from deepseek_client import summarize_daily_reports, analyze_member

logger = logging.getLogger(__name__)

# 日报多步对话的状态常量
WAITING_COMPLETED = 1   # 等待输入「今天完成了什么」
WAITING_PLANNED = 2      # 等待输入「明天计划做什么」
WAITING_BLOCKERS = 3     # 等待输入「有什么阻塞」
REPORTING = 0            # 占位，ConversationHandler 不使用但保持兼容

# ==================== 管理员权限检查 ====================

def _is_admin(update: Update) -> bool:
    """检查发送命令的用户是否是管理员"""
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    return role == "admin"

def _require_admin(update: Update):
    """如果不是管理员则返回提示文本"""
    if not _is_admin(update):
        return "⛔ 此命令仅限团队管理员使用。\n如需权限，请联系管理员在数据库中设置。"
    return None

# ==================== /start 和 /help 命令 ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """新成员加入或首次使用时的欢迎消息"""
    user = update.effective_user
    welcome_msg = (
        f"👋 你好 {user.first_name}！欢迎使用团队管理 Bot！\n\n"
        "📋 你可以使用以下命令：\n\n"
        "📝 /report — 提交今日日报\n"
        "📊 /okr — 查看团队 OKR\n"
        "❓ /help — 查看所有命令\n\n"
        "💡 你的日报会被安全保存，管理员会定期查看团队进展。"
    )
    await update.message.reply_text(welcome_msg)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示所有可用命令"""
    is_admin = _is_admin(update)
    help_text = (
        "📋 团队管理 Bot 命令列表\n\n"
        "📝 日报相关：\n"
        "/report — 提交今日日报\n"
        "/cancel — 取消当前日报提交\n\n"
        "📊 查看相关：\n"
        "/okr — 查看团队 OKR\n"
    )
    if is_admin:
        help_text += (
            "\n🔧 管理员命令：\n"
            "/summary — AI 生成月度工作总结（默认周汇总）\n"
            "/all — 查看今日所有人日报提交情况\n"
            "/member @用户名 — 查看某位成员最近的日报\n"
            "/analyze @用户名 — AI 分析某位成员的工作表现\n"
            "/setokr @用户名 目标 — 为成员设定 OKR\n"
            "/remind — 提醒未提交日报的成员\n"
        )
    await update.message.reply_text(help_text)


# ==================== 日报提交 — 多步对话流程 ====================

async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始日报提交流程 — 第一步：询问今天完成了什么"""
    await update.message.reply_text(
        "📝 来，说一下你今天的工作吧！\n\n"
        "✏️ 第一步：今天完成了什么？（可以分条写，比如：\n"
        "1. 完成登录模块开发\n"
        "2. 修复了 3 个线上 Bug\n\n"
        "写好直接发给我就行～\n"
        "🚫 输入 /cancel 可以取消"
    )
    return WAITING_COMPLETED


async def handle_completed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """接收「今日完成」→ 询问明天计划"""
    context.user_data["report_completed"] = update.message.text
    await update.message.reply_text(
        "👍 收到！\n\n"
        "✏️ 第二步：明天计划做什么？\n\n"
        "（输入 /cancel 取消）"
    )
    return WAITING_PLANNED


async def handle_planned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """接收「明日计划」→ 询问阻塞"""
    context.user_data["report_planned"] = update.message.text
    await update.message.reply_text(
        "📋 好的！\n\n"
        "✏️ 最后一步：有什么阻塞或需要帮助的？\n"
        "没有的话回复「无」或「没有」即可～\n\n"
        "（输入 /cancel 取消）"
    )
    return WAITING_BLOCKERS


async def handle_blockers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """接收「阻塞」→ 保存日报 → 完成"""
    completed = context.user_data.get("report_completed", "")
    planned = context.user_data.get("report_planned", "")
    blockers = update.message.text

    user = update.effective_user
    save_report(
        user_id=user.id,
        username=user.username or user.full_name,
        completed=completed,
        planned=planned,
        blockers=blockers
    )

    await update.message.reply_text(
        "✅ 日报提交成功！辛苦了！\n\n"
        f"📋 今日完成：{completed[:100]}{'...' if len(completed) > 100 else ''}\n"
        f"📌 明日计划：{planned[:100]}{'...' if len(planned) > 100 else ''}\n"
        f"⚠️ 阻塞项：{blockers[:100]}{'...' if len(blockers) > 100 else ''}\n\n"
        "💪 明天继续加油！输入 /report 可再次提交。"
    )

    context.user_data.clear()
    return ConversationHandler.END


async def report_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消日报提交"""
    context.user_data.clear()
    await update.message.reply_text("🚫 日报提交已取消。需要时输入 /report 重新开始。")
    return ConversationHandler.END


# ==================== 管理员命令 ====================

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI 智能汇总 — 管理员查看团队周/月汇总"""
    err = _require_admin(update)
    if err:
        await update.message.reply_text(err)
        return

    await update.message.reply_text("🤖 正在让 AI 分析最近的团队数据，请稍等...")

    reports = get_week_reports()

    if not reports:
        await update.message.reply_text("📭 最近一周还没有任何日报记录。")
        return

    # 把日报列表转成 AI 能读的文本格式
    reports_text = "\n".join(
        f"【{r['username']}】完成：{r['completed']} | 计划：{r['planned']} | 阻塞：{r['blockers']}"
        for r in reports
    )
    summary = summarize_daily_reports(reports_text)

    await update.message.reply_text(
        f"📊 AI 团队工作汇总（最近一周）\n\n{summary}\n\n"
        f"📝 共分析了 {len(reports)} 条日报记录。"
    )


async def all_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员查看今日所有人日报提交情况"""
    err = _require_admin(update)
    if err:
        await update.message.reply_text(err)
        return

    reports = get_today_reports()

    if not reports:
        await update.message.reply_text("📭 今天还没有人提交日报。输入 /remind 提醒大家～")
        return

    msg_parts = ["📋 今日日报提交情况：\n"]
    for r in reports:
        msg_parts.append(
            f"👤 {r['username']}\n"
            f"  ✅ 完成：{r['completed'][:80]}{'...' if len(r['completed']) > 80 else ''}\n"
        )

    await update.message.reply_text("\n".join(msg_parts))


async def member_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员查询某位成员的近期日报"""
    err = _require_admin(update)
    if err:
        await update.message.reply_text(err)
        return

    if not context.args:
        await update.message.reply_text(
            "❓ 用法：/member @用户名 或 /member 用户名\n"
            "例如：/member @zhangsan"
        )
        return

    username = context.args[0].lstrip("@")
    reports = get_user_reports_by_username(username, days=7)

    if not reports:
        await update.message.reply_text(f"📭 {username} 最近 7 天没有提交日报。")
        return

    msg_parts = [f"📋 {username} 最近 7 天日报：\n"]
    for r in reports:
        msg_parts.append(
            f"\n📅 {r['date']}\n"
            f"  ✅ {r['completed'][:100]}{'...' if len(r['completed']) > 100 else ''}\n"
            f"  📌 {r['planned'][:80]}{'...' if len(r['planned']) > 80 else ''}\n"
            f"  ⚠️ {r['blockers'][:60]}{'...' if len(r['blockers']) > 60 else ''}"
        )

    await update.message.reply_text("\n".join(msg_parts))


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI 分析某位成员的工作表现"""
    err = _require_admin(update)
    if err:
        await update.message.reply_text(err)
        return

    if not context.args:
        await update.message.reply_text(
            "❓ 用法：/analyze @用户名\n"
            "例如：/analyze @zhangsan"
        )
        return

    username = context.args[0].lstrip("@")
    await update.message.reply_text(f"🤖 正在让 AI 分析 {username} 的工作表现，请稍等...")

    reports = get_user_reports_by_username(username, days=14)

    if not reports:
        await update.message.reply_text(f"📭 {username} 最近没有足够的日报数据可供分析（需至少 3 条）。")
        return

    # 把日报列表转成 AI 能读的文本格式
    reports_text = "\n".join(
        f"日期：{r['report_date']} | 完成：{r['completed']} | 计划：{r['planned']} | 阻塞：{r['blockers']}"
        for r in reports
    )
    analysis = analyze_member(username, reports_text)

    await update.message.reply_text(
        f"🔍 AI 工作表现分析：{username}\n\n{analysis}\n\n"
        f"⚠️ 此分析基于最近 {len(reports)} 条日报记录，仅供参考。"
    )


async def set_okr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员为成员设定 OKR"""
    err = _require_admin(update)
    if err:
        await update.message.reply_text(err)
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "❓ 用法：/setokr @用户名 目标描述 | 关键结果1, 关键结果2, 关键结果3\n"
            "例如：/setokr @zhangsan 提升用户留存率 | 留存提高到85%, 流失率降至5%以下, 完成AB实验"
        )
        return

    username = context.args[0].lstrip("@")
    rest = " ".join(context.args[1:])

    if "|" in rest:
        objective, krs_str = rest.split("|", 1)
        key_results = [kr.strip() for kr in krs_str.split(",")]
    else:
        objective = rest
        key_results = []

    save_okr(username, objective, key_results)

    await update.message.reply_text(
        f"✅ 已为 {username} 设定 OKR！\n\n"
        f"🎯 目标：{objective}\n"
        f"📏 关键结果：\n  " + "\n  ".join(f"• {kr}" for kr in key_results)
    )


async def view_okr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看 OKR"""
    okrs = get_all_okrs()
    if not okrs:
        await update.message.reply_text("📭 尚未设定任何 OKR。管理员可使用 /setokr 设定。")
        return

    msg_parts = ["🎯 团队 OKR 总览：\n"]
    for okr in okrs:
        msg_parts.append(
            f"\n👤 {okr['username']}\n"
            f"  🎯 {okr['objective']}\n"
            f"  📏 {okr['key_results']}"
        )
    await update.message.reply_text("\n".join(msg_parts))


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员提醒未提交日报的成员"""
    err = _require_admin(update)
    if err:
        await update.message.reply_text(err)
        return

    all_users = get_all_users()
    today_reports = get_today_reports()
    today_users = {r["user_id"] for r in today_reports}

    not_reported = [u for u in all_users if u["user_id"] not in today_users]

    if not not_reported:
        await update.message.reply_text("✅ 大家都已提交今日日报！太棒了！")
        return

    msg_parts = ["📢 今日尚未提交日报的成员：\n"]
    for u in not_reported:
        msg_parts.append(f"  • {u['username']} — 请尽快提交日报！")

    await update.message.reply_text("\n".join(msg_parts))
