"""
DeepSeek API 客户端 —— 调用 DeepSeek 大模型进行智能汇总和分析。

你需要一个 DeepSeek API Key，在 https://platform.deepseek.com/api_keys 申请。
首次注册赠送额度，足够个人使用很长时间。
"""

import os
import requests

# =============================================================================
# 配置 —— 从环境变量读取（在 .env 文件中设置）
# =============================================================================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 可选的模型：deepseek-chat（便宜快速）或 deepseek-reasoner（深度推理）
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def _call_api(messages, temperature=0.7, max_tokens=2000):
    """
    底层 API 调用函数，不对外暴露。
    
    参数：
        messages: 消息列表，格式 [{"role": "system|user|assistant", "content": "..."}]
        temperature: 随机程度，0 最稳定，1 最随机。汇总建议用 0.3-0.5
        max_tokens: 最大输出长度
    
    返回：
        API 返回的完整 JSON，或出错时返回 None
    """
    url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {"error": "请求超时，DeepSeek API 响应太慢，请稍后重试"}
    except requests.exceptions.RequestException as e:
        return {"error": f"API 请求失败：{e}"}


def _get_reply_text(api_result):
    """
    从 API 返回结果中提取文本回复。
    
    参数：
        api_result: _call_api 返回的 JSON
    
    返回：
        AI 的回复文本，或错误信息
    """
    if api_result is None:
        return "❌ 未收到 API 响应，请检查网络连接"
    
    if "error" in api_result:
        return f"❌ {api_result['error']}"
    
    try:
        choices = api_result.get("choices", [])
        if choices:
            return choices[0]["message"]["content"]
        else:
            return "❌ API 返回了空结果"
    except (KeyError, IndexError, TypeError):
        return "❌ 解析 API 返回数据失败"


# =============================================================================
# 对外接口 —— 供 bot.py 调用
# =============================================================================

def summarize_daily_reports(reports_text):
    """
    日报汇总：把一堆日报内容发给 AI，让它生成结构化的团队总结。
    
    参数：
        reports_text: 所有日报拼接成的字符串，格式如：
            【张三】完成：xxx / 计划：xxx / 阻塞：无
            【李四】完成：xxx / 计划：xxx / 阻塞：有，xxx
    
    返回：
        AI 生成的汇总文本，包括：
        - 团队整体进展
        - 每个人的关键产出
        - 阻塞项预警
        - 明日关注建议
    """
    if not DEEPSEEK_API_KEY:
        return "⚠️ 未设置 DEEPSEEK_API_KEY，请在 .env 文件中填入你的 API Key"
    
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个专业的团队管理助手。你的任务是根据团队成员的日报，生成一份结构化的汇总报告。"
                "报告需要包含：\n"
                "1. 📊 团队整体进展概述（2-3句话）\n"
                "2. 👤 每位成员的关键产出（列出名字+要点）\n"
                "3. ⚠️ 阻塞项预警（明确指出需要关注的问题）\n"
                "4. 💡 明日关注建议\n"
                "请使用 emoji 和清晰的分段格式，让管理者一目了然。"
            ),
        },
        {
            "role": "user",
            "content": f"以下是团队今天的日报，请汇总：\n\n{reports_text}",
        },
    ]
    
    result = _call_api(messages, temperature=0.4, max_tokens=2000)
    return _get_reply_text(result)


def analyze_member(member_name, reports_text):
    """
    成员工作分析：分析某个成员近期的工作表现。
    
    参数：
        member_name: 成员名字
        reports_text: 该成员近期的日报内容
    
    返回：
        AI 生成的分析报告，包括工作节奏、优势、改进建议
    """
    if not DEEPSEEK_API_KEY:
        return "⚠️ 未设置 DEEPSEEK_API_KEY"
    
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个善解人意的团队教练。你的任务是根据某位团队成员近期的日报记录，"
                "给出建设性的工作分析。分析要真诚、具体、有帮助性。"
                "格式：\n"
                "1. 📈 工作节奏观察\n"
                "2. ✅ 做得好的地方\n"
                "3. 🔧 可以改进的地方\n"
                "4. 💪 具体建议（可操作的建议）\n"
                "语气要积极正面，目的是帮助成长，而非批评。"
            ),
        },
        {
            "role": "user",
            "content": f"请分析 {member_name} 近期的工作情况：\n\n{reports_text}",
        },
    ]
    
    result = _call_api(messages, temperature=0.5, max_tokens=1500)
    return _get_reply_text(result)


def suggest_action_from_blockers(blockers_text):
    """
    阻塞建议：当有成员报告阻塞时，让 AI 给出解除阻塞的建议。
    
    参数：
        blockers_text: 阻塞项描述
    
    返回：
        AI 给出的处理建议
    """
    if not DEEPSEEK_API_KEY:
        return "⚠️ 未设置 DEEPSEEK_API_KEY"
    
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个经验丰富的技术管理者。团队成员遇到了工作阻塞，"
                "请给出具体可行的解决建议。可以包括："
                "1. 问题的可能原因\n"
                "2. 建议的解决步骤\n"
                "3. 需要协调的资源\n"
                "4. 给管理者的提醒\n"
                "简洁实用，2-3 条核心建议即可。"
            ),
        },
        {
            "role": "user",
            "content": f"以下是我团队成员报告的阻塞项，请给出处理建议：\n\n{blockers_text}",
        },
    ]
    
    result = _call_api(messages, temperature=0.5, max_tokens=1000)
    return _get_reply_text(result)


def generate_reminder_message(missing_members_str):
    """
    生成催日报消息：当有人还没交日报时，生成一条得体的提醒消息。
    
    参数：
        missing_members_str: 还没交日报的成员名字列表，如 "张三, 李四"
    
    返回：
        一条语气友好的提醒消息，可以直接发到群里
    """
    if not DEEPSEEK_API_KEY:
        return f"⚠️ 以下成员还未提交今日日报：{missing_members_str}\n请尽快提交！（使用 /report 命令）"
    
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个亲和力强的团队负责人。你需要提醒某些成员提交日报。"
                "请生成一条简短友好的提醒消息，语气轻松但不失正式。"
                "包含emoji，保持在 3 句话以内。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"请帮我提醒以下成员提交今天的日报：{missing_members_str}"
                "他们可以使用 /report 命令提交。"
            ),
        },
    ]
    
    result = _call_api(messages, temperature=0.7, max_tokens=300)
    return _get_reply_text(result)


def generate_weekly_summary(reports_text):
    """
    周报汇总：汇总一周的团队工作。
    
    参数：
        reports_text: 本周所有日报内容
    
    返回：
        AI 生成的周报
    """
    if not DEEPSEEK_API_KEY:
        return "⚠️ 未设置 DEEPSEEK_API_KEY"
    
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个专业的团队管理助手。请根据本周团队成员的日报记录，"
                "生成一份周报。内容包括：\n"
                "1. 📊 本周团队整体成果\n"
                "2. 👤 每位成员的关键贡献\n"
                "3. 🎯 目标达成情况\n"
                "4. ⚠️ 风险和阻塞\n"
                "5. 📅 下周重点\n"
                "专业简洁，用 emoji 组织。"
            ),
        },
        {
            "role": "user",
            "content": f"以下是团队本周的日报记录，请生成周报：\n\n{reports_text}",
        },
    ]
    
    result = _call_api(messages, temperature=0.4, max_tokens=2500)
    return _get_reply_text(result)
