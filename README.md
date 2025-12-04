# FemSub · Telegram 投稿机器人

一个多媒体投稿与审核工作流的 Telegram 机器人，支持匿名、标签管理、管理员编辑以及频道自动分发。最新版本已经模块化拆分，便于维护和扩展。

---

## ✨ 主要特性
- **多格式投稿**：文本、单图、视频、文件、相册组图全覆盖。
- **匿名开关**：用户在预览面板即可切换匿名状态。
- **双层审核界面**：管理员群收到“内容预览 + 操作面板”两条消息，避免误操作。
- **Tag 与文案编辑**：管理员可追加标签、重写文案，并实时同步到预览消息。
- **频道自动发布**：通过审核后自动推送到主频道，支持署名和自定义导航链接。
- **统计与个人中心**：`/stats` 提供全局数据，`/my` 命令展示个人投稿概况。
- **管理员私聊回复**：深链 `reply_{user_id}` 可进入与投稿人单独对话的模式。

---

## 🧱 项目结构
```
FemSub/
├── main.py                 # 程序入口，只负责装配和启动
├── app/
│   ├── __init__.py
│   ├── config.py           # Settings / 环境变量解析
│   ├── database.py         # SQLite Repository
│   ├── models.py           # 数据类与枚举
│   ├── handlers/           # Telegram handler 层
│   │   ├── callbacks.py
│   │   ├── commands.py
│   │   └── messages.py
│   └── services/           # 业务逻辑
│       ├── __init__.py
│       ├── admin_service.py
│       ├── feedback_service.py
│       ├── submission_service.py
│       └── container.py    # ServiceContainer 统一注入
├── requirements.txt
├── run_dev.py              # watchgod 热重载启动器
└── femsub.db               # SQLite 数据库（运行后生成）
```

---

## ⚙️ 环境配置
支持直接在环境变量（或 `.env`）中覆盖以下设置，均在 `app/config.py` 中读取：

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `BOT_TOKEN` | - | Telegram Bot Token（必须设置） |
| `ADMIN_GROUP_ID` | - | 管理员群组 ID（必须设置） |
| `CHANNEL_ID` | - | 发布频道 ID（必须设置） |
| `NAV_CHANNEL_LINK` | `https://t.me/FemSub_bot` | 频道底部导航链接 |
| `PRESET_TAGS` | `#日常,#福利,...` | 预设标签，逗号分隔 |
| `REJECTION_REASONS` | `内容违规,...` | 预设拒绝原因 |
| `MEDIA_GROUP_TIMEOUT` | `3` | 相册收集防抖时间（秒） |

可以在项目根目录创建 `.env` 文件，示例：
```
BOT_TOKEN=123456:ABC
ADMIN_GROUP_ID=-100xxxxxxxx
CHANNEL_ID=-100yyyyyyyy
```

---

## 📦 安装与运行
1. **安装依赖**
```bash
   pip install -r requirements.txt
```
2. **启动机器人**
```bash
python main.py
```
3. **开发模式（自动重载）**
   ```bash
   python run_dev.py
   ```

> **注意**：项目默认使用 SQLite，本地运行会在根目录生成 `femsub.db`。

---

## 🗺️ 工作流概览

### 用户侧
1. 发送内容（文字/媒体/相册）。
2. Bot 回传预览 + 控制按钮（匿名切换、确认、取消）。
3. 确认后进入待审核状态，并等待管理员结果通知。

### 管理员侧
1. 管理员群收到两条消息：`预览层`（用户原稿）和 `控制层`（操作面板）。
2. 控制面板支持：通过/拒绝、编辑文案、添加 Tag、拉黑用户。
3. 通过后自动发布到频道，并按匿名设置追加署名/导航链接。
4. 审核结果会同步通知投稿人。

---

## 📜 命令速查

| 命令 | 用户 | 管理员 | 功能 |
| --- | --- | --- | --- |
| `/start` `/help` | ✅ | ✅ | 使用指南、深链回复入口 |
| `/my` | ✅ | - | 个人投稿总览 |
| `/stats` | - | ✅（限管理员群） | 投稿统计面板 |
| `/stop` | - | ✅ | 退出管理员回复模式 |

管理员通过深链 `t.me/<bot>?start=reply_{user_id}` 进入私聊回复模式，回复完成后发送 `/stop` 退出。

---

## 🧪 数据库说明
表结构位于 `app/database.py`，包括：
- `media_files`：JSON 字符串，存储 media_group 中的所有文件 ID。
- `caption` / `caption_only`：分别表示“标签拼接后的展示文案”和“管理员可编辑的原始文案”。
- `tags`：空格分隔字符串，便于直接拼接展示。

默认提供自动建表逻辑，无需手动创建。

---

## 🧭 开发提示
- Handler 层（`app/handlers`）只负责解析 Telegram 事件，所有复杂逻辑都在 `services`。
- `ServiceContainer` 负责注入 `settings` 与 `Database`，避免到处 import 单例。
- 新增功能时建议以 Service 为边界，保持 Handler 薄且可测试。

---

## 📞 支持
如需定制或遇到问题，欢迎提交 Issue 或联系维护者。  
**FemSub** —— 让投稿管理更简单！