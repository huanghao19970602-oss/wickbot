# 🤖 团队管理 Telegram Bot —— 零基础部署指南

> 即使你完全不会编程，跟着这份指南，也能在 30 分钟内把你的专属团队管理机器人跑起来！

---

## 📖 目录

1. [这个 Bot 能做什么？](#1-这个-bot-能做什么？)
2. [你需要准备什么？](#2-你需要准备什么？)
3. [第一步：获取 Telegram Bot Token](#3-第一步获取-telegram-bot-token)
4. [第二步：获取 DeepSeek API Key](#4-第二步获取-deepseek-api-key)
5. [第三步：获取你的 Telegram 用户 ID](#5-第三步获取你的-telegram-用户-id)
6. [第四步：部署到 Railway（最推荐，免费）](#6-第四步部署到-railway最推荐免费)
7. [第五步：配置并启动](#7-第五步配置并启动)
8. [第六步：把团队成员加入 Bot](#8-第六步把团队成员加入-bot)
9. [命令速查表](#9-命令速查表)
10. [常见问题](#10-常见问题)

---

## 1. 这个 Bot 能做什么？

| 功能 | 怎么用 | 谁可以用 |
|------|--------|----------|
| 📝 日报提交 | 发送 `/report`，Bot 引导你分三步填写 | 所有成员 |
| 📊 AI 智能汇总 | 发送 `/summary`，AI 自动总结团队本周工作 | 仅管理员 |
| 👤 成员进度查询 | 发送 `/member @用户名` 查看某人最近日报 | 仅管理员 |
| 🔍 表现分析 | 发送 `/analyze @用户名`，AI 分析工作表现 | 仅管理员 |
| 🎯 OKR 管理 | 发送 `/setokr` 设定目标，`/okr` 查看 | 管理员/全员 |
| 📢 提交提醒 | 发送 `/remind`，列出还没交日报的人 | 仅管理员 |
| 📋 今日一览 | 发送 `/all`，快速查看今天谁交了日报 | 仅管理员 |

## 2. 你需要准备什么？

| 物品 | 说明 | 费用 |
|------|------|------|
| Telegram 账号 | 你已经在用了 ✅ | 免费 |
| DeepSeek API Key | 在 platform.deepseek.com 注册即送额度 | 首次免费，后续按量付费（很便宜） |
| GitHub 账号 | 用来连接 Railway 部署 | 免费 |
| Railway 账号 | 用来运行 Bot（24小时在线） | 免费额度够用 |
| 一台电脑 | 用来做配置，不需要一直开着 | 你的电脑就行 |

> 💡 **整个流程大约 30 分钟**，之后 Bot 会 7×24 小时运行，不需要你管它。

## 3. 第一步：获取 Telegram Bot Token

> 这是 Bot 的"身份证"，让程序知道你在控制哪个 Bot。

1. 在 Telegram 中搜索 **@BotFather**（注意拼写，是官方账号，有蓝勾）
2. 点击「开始」或发送 `/start`
3. 发送 `/newbot`
4. 按提示给 Bot 起个名字，例如「张总团队助手」
5. 再给 Bot 起个用户名（必须以 `bot` 结尾），例如 `zhang_team_bot`
6. 成功后你会收到一条消息，里面包含 **Token**，格式像这样：
   ```
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
7. 🔐 **把这段 Token 复制保存好**，后面会用到。

> ⚠️ Token 相当于 Bot 的密码，**不要发给任何人**！

## 4. 第二步：获取 DeepSeek API Key

> 这是调用 DeepSeek 大模型的"钥匙"，用来做智能汇总和分析。

1. 打开浏览器，访问 **https://platform.deepseek.com**
2. 点击右上角「登录/注册」（用手机号或邮箱注册）
3. 登录后，点击左侧菜单「API Keys」
4. 点击「创建 API Key」
5. 给 Key 起个名字，例如「team-bot」
6. 🔐 **复制保存这个 Key**（只显示一次！）
7. 新用户赠送 100 万 tokens 免费额度，够你用几个月。

## 5. 第三步：获取你的 Telegram 用户 ID

> 这是你的"数字身份证"，Bot 用这个判断谁是管理员。

1. 在 Telegram 中搜索 **@userinfobot**
2. 点击「开始」或发送任意消息
3. 它会回复你的信息，其中包含 `Id: 123456789`
4. 🔐 **复制这个数字 ID**，后面会用到。

## 6. 第四步：部署到 Railway（最推荐，免费）

> Railway 是一个云服务平台，可以免费运行 Python 程序。你的 Bot 会 24 小时运行在上面。

### 6.1 注册 Railway

1. 打开 **https://railway.app**
2. 点击「Start a New Project」
3. 选择「Deploy from GitHub repo」
4. 用你的 GitHub 账号登录授权

### 6.2 上传代码到 GitHub

> 如果你不会用 Git，没关系，用网页操作就行。

1. 打开 **https://github.com**，登录你的账号
2. 点击右上角「+」→「New repository」
3. Repository name 填 `tg-team-bot`
4. 选择「Public」或「Private」都行
5. 点击「Create repository」
6. 在新页面点击「uploading an existing file」
7. 把 `tg-team-bot` 文件夹里的所有文件拖进去：
   - `bot.py`
   - `bot_handlers.py`
   - `database.py`
   - `deepseek_client.py`
   - `requirements.txt`
   - `.env.example`
8. 点击「Commit changes」

### 6.3 在 Railway 部署

1. 回到 **Railway** 页面
2. 点击「Deploy from GitHub repo」
3. 搜索并选择你刚创建的 `tg-team-bot` 仓库
4. Railway 会自动检测到这是 Python 项目并开始部署
5. 等待 2-3 分钟，直到显示「Deployed ✅」

## 7. 第五步：配置并启动

### 7.1 设置环境变量

在 Railway 项目页面：

1. 点击你的项目
2. 点击顶部的「Variables」标签
3. 添加以下三个变量：

| 变量名 | 值（填入你自己的） |
|--------|-------------------|
| `BOT_TOKEN` | 你在第 3 步拿到的 Token |
| `DEEPSEEK_API_KEY` | 你在第 4 步拿到的 API Key |
| `ADMIN_USER_ID` | 你在第 5 步拿到的数字 ID |

4. 添加完后，Railway 会自动重新部署（约 1 分钟）

### 7.2 验证 Bot 是否成功启动

1. 在 Telegram 中搜索你的 Bot 用户名（第 3 步起的那个）
2. 发送 `/start`
3. 如果收到欢迎消息，说明部署成功！🎉

## 8. 第六步：把团队成员加入 Bot

### 8.1 设置自己为管理员

> 第一次使用时，你需要把自己设为管理员才能用管理命令。

在 Bot 聊天框中发送：
```
/start
```
Bot 会自动在数据库中记录你。但由于你设置了 `ADMIN_USER_ID`，可以手动确认。

以后如果你换了设备或 Bot 重装，发 `/start` 就行。

### 8.2 让团队成员加入

把 Bot 用户名发给团队成员，让他们：

1. 在 Telegram 搜索你的 Bot 用户名
2. 发送 `/start`
3. 就可以开始使用 `/report` 提交日报了

> 💡 你也可以创建一个 Telegram 群，把 Bot 拉进去，大家在群里发命令即可。

## 9. 命令速查表

### 所有成员都可以用

| 命令 | 功能 |
|------|------|
| `/start` | 开始使用 |
| `/help` | 查看帮助 |
| `/report` | 提交今日日报（分三步引导） |
| `/cancel` | 取消当前日报提交 |
| `/okr` | 查看团队 OKR |

### 仅管理员可用

| 命令 | 功能 | 示例 |
|------|------|------|
| `/summary` | AI 生成本周团队工作汇总 | `/summary` |
| `/all` | 查看今天所有人的日报 | `/all` |
| `/member @用户名` | 查看某人最近 7 天日报 | `/member @zhangsan` |
| `/analyze @用户名` | AI 分析某人工作表现 | `/analyze @zhangsan` |
| `/setokr @用户名 目标 \| KR1, KR2` | 设定 OKR | `/setokr @zhangsan 提升留存 \| 留存85%, 流失<5%` |
| `/remind` | 提醒未交日报的成员 | `/remind` |

## 10. 常见问题

### Q: 部署要钱吗？
**A:** Railway 免费额度每月 $5，跑这个 Bot 够用。DeepSeek API 首次注册送 100 万 tokens，一个 7 人团队每天使用估计月消耗不到 50 万 tokens，免费额度够用 2 个月。后续充值几十块钱够用好几个月。

### Q: 我的 Bot 不理我？
**A:** 检查 Railway 上是否显示「Deployed」，环境变量是否正确设置（特别是 `BOT_TOKEN`）。

### Q: 怎么让 Bot 每天自动提醒大家交日报？
**A:** 第一期版本需要你手动发 `/remind`。下一期可以加定时任务。但你可以配合 DeepSeek GUI 的排程功能，每天下午 5 点提醒你自己去发 `/remind`。

### Q: 数据存在哪里？安全吗？
**A:** 数据存 Railway 的临时磁盘上。建议每月导出备份（后续可加 `/export` 命令）。Railway 免费版磁盘不永久保存，重启可能丢失。升级到 Hobby 计划（$5/月）可获得永久存储。

### Q: 我能修改日报的问题吗？
**A:** 当前版本日报分三步：完成了什么 → 计划做什么 → 有什么阻塞。如果需要修改，告诉我，我可以帮你改代码。

---

## 🎉 最后

部署完成后，你的工作流会变成这样：

1. **每天早上** — 团队成员到公司，打开 TG，给 Bot 发 `/report`，花 1 分钟填写日报
2. **随时** — 你想了解某个人的进展，发 `/member @姓名`
3. **每周五** — 发 `/summary`，AI 自动生成周报
4. **每月初** — 发 `/setokr` 设定当月目标
5. **需要辅导时** — 发 `/analyze @姓名`，AI 分析工作模式

再也不用一个个去问了！📱✨

有问题随时回来问我，我可以帮你改代码、加功能、或者排查问题。
