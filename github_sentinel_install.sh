#!/bin/bash
set -euo pipefail

# 项目配置
PROJECT_NAME="github-sentinel"
PROJECT_DIR="/Users/xty/Study/AI/.${PROJECT_NAME}"

CONFIG_DIR="/Users/xty/Study/AI/.${PROJECT_NAME}_config"
CONFIG_PATH="$CONFIG_DIR/config.json"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"

# 颜色输出
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m" # 无颜色

# 步骤1：创建项目目录
echo -e "${GREEN}[1/6] 创建项目目录...${NC}"
mkdir -p "$PROJECT_DIR"
mkdir -p "$CONFIG_DIR"

# 步骤3：生成所有 Python 核心文件
echo -e "${GREEN}[3/6] 创建核心代码文件...${NC}"

# 3.1 config.py
cat > "$PROJECT_DIR/config.py" << 'EOF'
import json
import os
from typing import Dict, Optional

class ConfigManager:
    """配置管理器：加载、验证、提供配置信息"""
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.expanduser("~/.github_sentinel_config/config.json")
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict:
        """加载配置文件，若不存在则创建默认配置"""
        if not os.path.exists(self.config_path):
            self._create_default_config()
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _create_default_config(self) -> None:
        """创建默认配置文件"""
        default_config = {
            "github_token": "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN",
            "subscriptions": [
                # 示例：{"owner": "octocat", "repo": "hello-world", "watch_events": ["commits", "pull_requests", "issues"]}
            ],
            "check_frequency": "daily",  # 支持 "daily" / "weekly"
            "notification": {
                "type": "console",  # 支持 "console" / "email" / "webhook"
                "email": {
                    "sender": "your-email@example.com",
                    "recipient": "target-email@example.com",
                    "smtp_server": "smtp.example.com",
                    "smtp_port": 587,
                    "smtp_user": "your-email@example.com",
                    "smtp_password": "your-email-password"
                },
                "webhook": {
                    "url": "https://your-webhook-url.com"
                }
            }
        }
        # 创建目录（若不存在）
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)
        print(f"默认配置文件已创建：{self.config_path}")
        print("请修改配置文件中的 GitHub Token 和订阅信息后重新运行")

    def _validate_config(self) -> None:
        """验证配置文件必填字段"""
        REQUIRED_FIELDS = ["github_token", "subscriptions", "check_frequency", "notification"]
        for field in REQUIRED_FIELDS:
            if field not in self.config:
                raise ValueError(f"配置文件缺少必填字段：{field}")
        # 验证 GitHub Token 不为默认值
        if self.config["github_token"] == "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN":
            raise ValueError("请在配置文件中设置有效的 GitHub Personal Access Token")
        # 验证订阅格式
        for sub in self.config["subscriptions"]:
            required_sub_fields = ["owner", "repo", "watch_events"]
            for field in required_sub_fields:
                if field not in sub:
                    raise ValueError(f"订阅项缺少字段：{field}，订阅内容：{sub}")
        # 验证频率格式
        if self.config["check_frequency"] not in ["daily", "weekly"]:
            raise ValueError("check_frequency 只能是 'daily' 或 'weekly'")

    def get_config(self) -> Dict:
        """获取完整配置"""
        return self.config

    def update_config(self, new_config: Dict) -> None:
        """更新配置并保存到文件"""
        self.config.update(new_config)
        self._validate_config()
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)
EOF

# 3.2 subscription_manager.py
cat > "$PROJECT_DIR/subscription_manager.py" << 'EOF'
from typing import List, Dict, Optional
from config import ConfigManager

class SubscriptionManager:
    """订阅管理器：管理 GitHub 仓库订阅"""
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = self.config_manager.get_config()
        self.subscriptions: List[Dict] = self.config["subscriptions"]

    def get_all_subscriptions(self) -> List[Dict]:
        """获取所有订阅"""
        return self.subscriptions.copy()

    def get_subscription(self, owner: str, repo: str) -> Optional[Dict]:
        """根据 owner 和 repo 获取单个订阅"""
        for sub in self.subscriptions:
            if sub["owner"] == owner and sub["repo"] == repo:
                return sub.copy()
        return None

    def add_subscription(self, owner: str, repo: str, watch_events: List[str]) -> bool:
        """添加订阅（去重）"""
        # 验证事件类型
        valid_events = ["commits", "pull_requests", "issues", "releases"]
        for event in watch_events:
            if event not in valid_events:
                print(f"无效的事件类型：{event}，支持的类型：{valid_events}")
                return False
        # 去重检查
        if self.get_subscription(owner, repo):
            print(f"已订阅仓库：{owner}/{repo}，无需重复添加")
            return False
        # 添加订阅
        new_sub = {
            "owner": owner,
            "repo": repo,
            "watch_events": watch_events
        }
        self.subscriptions.append(new_sub)
        self.config_manager.update_config({"subscriptions": self.subscriptions})
        print(f"成功添加订阅：{owner}/{repo}，监听事件：{watch_events}")
        return True

    def remove_subscription(self, owner: str, repo: str) -> bool:
        """删除订阅"""
        sub = self.get_subscription(owner, repo)
        if not sub:
            print(f"未找到订阅：{owner}/{repo}")
            return False
        self.subscriptions.remove(sub)
        self.config_manager.update_config({"subscriptions": self.subscriptions})
        print(f"成功删除订阅：{owner}/{repo}")
        return True

    def update_subscription_events(self, owner: str, repo: str, new_watch_events: List[str]) -> bool:
        """更新订阅的监听事件"""
        sub = self.get_subscription(owner, repo)
        if not sub:
            print(f"未找到订阅：{owner}/{repo}")
            return False
        # 验证事件类型
        valid_events = ["commits", "pull_requests", "issues", "releases"]
        for event in new_watch_events:
            if event not in valid_events:
                print(f"无效的事件类型：{event}，支持的类型：{valid_events}")
                return False
        # 更新事件
        sub["watch_events"] = new_watch_events
        self.config_manager.update_config({"subscriptions": self.subscriptions})
        print(f"成功更新订阅事件：{owner}/{repo}，新事件：{new_watch_events}")
        return True
EOF

# 3.3 github_api_client.py
cat > "$PROJECT_DIR/github_api_client.py" << 'EOF'
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from config import ConfigManager

class GitHubAPIClient:
    """GitHub API 客户端：获取仓库动态"""
    GITHUB_API_BASE_URL = "https://api.github.com"

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.get_config()
        self.headers = {
            "Authorization": f"token {self.config['github_token']}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _get_time_range(self) -> Tuple[str, str]:
        """根据检查频率获取时间范围（UTC 时间）"""
        now = datetime.utcnow()
        if self.config["check_frequency"] == "daily":
            start_time = now - timedelta(days=1)
        else:  # weekly
            start_time = now - timedelta(weeks=1)
        # 格式化为 ISO 8601 字符串（GitHub API 要求）
        return start_time.isoformat() + "Z", now.isoformat() + "Z"

    def get_commits(self, owner: str, repo: str) -> List[Dict]:
        """获取仓库指定时间范围内的提交记录"""
        start_time, end_time = self._get_time_range()
        url = f"{self.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/commits"
        params = {
            "since": start_time,
            "until": end_time,
            "per_page": 100  # 最多获取 100 条
        }
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()  # 抛出 HTTP 错误
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"获取 {owner}/{repo} 提交记录失败：{str(e)}")
            return []

    def get_pull_requests(self, owner: str, repo: str) -> List[Dict]:
        """获取仓库指定时间范围内的 PR（状态：open/closed/merged）"""
        start_time, end_time = self._get_time_range()
        url = f"{self.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/pulls"
        params = {
            "state": "all",
            "since": start_time,
            "until": end_time,
            "per_page": 100
        }
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"获取 {owner}/{repo} PR 失败：{str(e)}")
            return []

    def get_issues(self, owner: str, repo: str) -> List[Dict]:
        """获取仓库指定时间范围内的 Issue（排除 PR，状态：open/closed）"""
        start_time, end_time = self._get_time_range()
        url = f"{self.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/issues"
        params = {
            "state": "all",
            "since": start_time,
            "until": end_time,
            "per_page": 100,
            "filter": "all"
        }
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            # 过滤掉 PR（Issue 和 PR 共用接口，PR 有 pull_request 字段）
            issues = [item for item in response.json() if "pull_request" not in item]
            return issues
        except requests.exceptions.RequestException as e:
            print(f"获取 {owner}/{repo} Issue 失败：{str(e)}")
            return []

    def get_releases(self, owner: str, repo: str) -> List[Dict]:
        """获取仓库指定时间范围内的 Release"""
        start_time, end_time = self._get_time_range()
        url = f"{self.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/releases"
        params = {"per_page": 100}
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            # 过滤时间范围内的 Release
            releases = [
                release for release in response.json()
                if start_time <= release["created_at"] <= end_time
            ]
            return releases
        except requests.exceptions.RequestException as e:
            print(f"获取 {owner}/{repo} Release 失败：{str(e)}")
            return []

    def fetch_repo_updates(self, subscription: Dict) -> Dict:
        """根据订阅获取仓库所有指定类型的更新"""
        owner = subscription["owner"]
        repo = subscription["repo"]
        watch_events = subscription["watch_events"]
        
        updates = {
            "owner": owner,
            "repo": repo,
            "events": {},
            "update_time": datetime.utcnow().isoformat() + "Z"
        }

        # 根据监听事件获取对应更新
        if "commits" in watch_events:
            updates["events"]["commits"] = self.get_commits(owner, repo)
        if "pull_requests" in watch_events:
            updates["events"]["pull_requests"] = self.get_pull_requests(owner, repo)
        if "issues" in watch_events:
            updates["events"]["issues"] = self.get_issues(owner, repo)
        if "releases" in watch_events:
            updates["events"]["releases"] = self.get_releases(owner, repo)

        return updates
EOF

# 3.4 data_processor.py
cat > "$PROJECT_DIR/data_processor.py" << 'EOF'
from typing import List, Dict, Any
from datetime import datetime

class DataProcessor:
    """数据处理器：过滤、提取、汇总 GitHub 仓库更新"""

    @staticmethod
    def _process_commit(commit: Dict) -> Dict:
        """提取提交记录的关键信息"""
        return {
            "sha": commit["sha"][:7],  # 简化 SHA
            "message": commit["commit"]["message"].split("\n")[0],  # 只保留第一行（标题）
            "author": commit["commit"]["author"]["name"],
            "author_email": commit["commit"]["author"]["email"],
            "created_at": commit["commit"]["author"]["date"],
            "url": commit["html_url"]
        }

    @staticmethod
    def _process_pull_request(pr: Dict) -> Dict:
        """提取 PR 的关键信息"""
        return {
            "number": pr["number"],
            "title": pr["title"],
            "state": pr["state"],
            "author": pr["user"]["login"] if pr["user"] else "unknown",
            "created_at": pr["created_at"],
            "updated_at": pr["updated_at"],
            "merged": pr.get("merged", False),
            "merged_at": pr.get("merged_at"),
            "url": pr["html_url"]
        }

    @staticmethod
    def _process_issue(issue: Dict) -> Dict:
        """提取 Issue 的关键信息"""
        return {
            "number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "author": issue["user"]["login"] if issue["user"] else "unknown",
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
            "closed_at": issue.get("closed_at"),
            "url": issue["html_url"]
        }

    @staticmethod
    def _process_release(release: Dict) -> Dict:
        """提取 Release 的关键信息"""
        return {
            "tag_name": release["tag_name"],
            "name": release["name"],
            "draft": release["draft"],
            "prerelease": release["prerelease"],
            "author": release["author"]["login"] if release["author"] else "unknown",
            "created_at": release["created_at"],
            "published_at": release["published_at"],
            "url": release["html_url"],
            "body": release["body"][:200] + "..." if len(release["body"]) > 200 else release["body"]  # 截断长描述
        }

    def process_updates(self, raw_updates: Dict) -> Dict:
        """处理单个仓库的原始更新数据，提取关键信息"""
        processed = {
            "owner": raw_updates["owner"],
            "repo": raw_updates["repo"],
            "update_time": raw_updates["update_time"],
            "events": {}
        }

        # 处理每种事件类型
        if "commits" in raw_updates["events"] and raw_updates["events"]["commits"]:
            processed["events"]["commits"] = [
                self._process_commit(commit) for commit in raw_updates["events"]["commits"]
            ]
        if "pull_requests" in raw_updates["events"] and raw_updates["events"]["pull_requests"]:
            processed["events"]["pull_requests"] = [
                self._process_pull_request(pr) for pr in raw_updates["events"]["pull_requests"]
            ]
        if "issues" in raw_updates["events"] and raw_updates["events"]["issues"]:
            processed["events"]["issues"] = [
                self._process_issue(issue) for issue in raw_updates["events"]["issues"]
            ]
        if "releases" in raw_updates["events"] and raw_updates["events"]["releases"]:
            processed["events"]["releases"] = [
                self._process_release(release) for release in raw_updates["events"]["releases"]
            ]

        return processed

    def batch_process_updates(self, raw_updates_list: List[Dict]) -> List[Dict]:
        """批量处理多个仓库的更新数据"""
        return [self.process_updates(raw) for raw in raw_updates_list]

    def filter_empty_updates(self, processed_updates_list: List[Dict]) -> List[Dict]:
        """过滤无更新的仓库数据"""
        return [
            updates for updates in processed_updates_list
            if any(events for events in updates["events"].values())
        ]
EOF

# 3.5 report_generator.py
cat > "$PROJECT_DIR/report_generator.py" << 'EOF'
from typing import List, Dict
from datetime import datetime

class ReportGenerator:
    """报告生成器：将更新数据生成为文本/Markdown 报告"""

    def __init__(self, check_frequency: str):
        self.frequency = check_frequency
        self.report_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    def _get_report_header(self) -> str:
        """生成报告头部"""
        period = "24小时内" if self.frequency == "daily" else "7天内"
        return f"📊 GitHub Sentinel 仓库更新报告\n" \
               f"=============================\n" \
               f"报告生成时间：{self.report_time}\n" \
               f"监控周期：{period}\n" \
               f"=============================\n\n"

    def _generate_repo_section(self, repo_updates: Dict) -> str:
        """生成单个仓库的更新章节"""
        owner = repo_updates["owner"]
        repo = repo_updates["repo"]
        repo_url = f"https://github.com/{owner}/{repo}"
        section = f"🔹 仓库：[{owner}/{repo}]({repo_url})\n"
        section += f"更新时间：{repo_updates['update_time']}\n\n"

        # 添加各事件类型的更新
        events = repo_updates["events"]
        
        if "commits" in events and events["commits"]:
            section += f"  📝 提交记录（共 {len(events['commits'])} 条）：\n"
            for commit in events["commits"]:
                section += f"    - [{commit['sha']}] {commit['message']}\n"
                section += f"      作者：{commit['author']} | 时间：{commit['created_at'][:10]} | {commit['url']}\n"
            section += "\n"

        if "pull_requests" in events and events["pull_requests"]:
            section += f"  🔀 拉取请求（共 {len(events['pull_requests'])} 条）：\n"
            for pr in events["pull_requests"]:
                state = "✅ 已合并" if pr["merged"] else "🔴 已关闭" if pr["state"] == "closed" else "🟡 开放中"
                section += f"    - #{pr['number']} {pr['title']} {state}\n"
                section += f"      作者：{pr['author']} | 创建时间：{pr['created_at'][:10]} | {pr['url']}\n"
            section += "\n"

        if "issues" in events and events["issues"]:
            section += f"  ❗ Issue（共 {len(events['issues'])} 条）：\n"
            for issue in events["issues"]:
                state = "🔴 已关闭" if issue["state"] == "closed" else "🟡 开放中"
                closed_time = f" | 关闭时间：{issue['closed_at'][:10]}" if issue["closed_at"] else ""
                section += f"    - #{issue['number']} {issue['title']} {state}\n"
                section += f"      作者：{issue['author']} | 创建时间：{issue['created_at'][:10]}{closed_time} | {issue['url']}\n"
            section += "\n"

        if "releases" in events and events["releases"]:
            section += f"  🚀 Release（共 {len(events['releases'])} 条）：\n"
            for release in events["releases"]:
                status = "📦 正式版" if not release["prerelease"] and not release["draft"] else "🔧 草稿" if release["draft"] else "⚠️ 预发布"
                section += f"    - {release['tag_name']}：{release['name']} {status}\n"
                section += f"      作者：{release['author']} | 发布时间：{release['published_at'][:10]} | {release['url']}\n"
                section += f"      描述：{release['body']}\n"
            section += "\n"

        return section + "---\n\n"

    def generate_markdown_report(self, processed_updates_list: List[Dict]) -> str:
        """生成 Markdown 格式报告"""
        if not processed_updates_list:
            return f"{self._get_report_header()}\n📭 没有检测到任何仓库的更新～\n"

        report = self._get_report_header()
        for repo_updates in processed_updates_list:
            report += self._generate_repo_section(repo_updates)
        return report

    def generate_text_report(self, processed_updates_list: List[Dict]) -> str:
        """生成纯文本格式报告（兼容终端输出）"""
        markdown_report = self.generate_markdown_report(processed_updates_list)
        # 移除 Markdown 链接格式（[文本](链接) → 文本 (链接)）
        import re
        text_report = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1 (\2)", markdown_report)
        # 替换 emoji 和格式符
        text_report = text_report.replace("📊", "").replace("🔹", "-").replace("📝", "").replace("🔀", "").replace("❗", "").replace("🚀", "")
        text_report = text_report.replace("✅", "").replace("🔴", "").replace("🟡", "").replace("📦", "").replace("🔧", "").replace("⚠️", "")
        return text_report
EOF

# 3.6 notifier.py
cat > "$PROJECT_DIR/notifier.py" << 'EOF'
from typing import Dict
import smtplib
from email.mime.text import MIMEText
import requests
from report_generator import ReportGenerator

class Notifier:
    """通知器：多渠道推送报告"""
    def __init__(self, config: Dict, report_generator: ReportGenerator):
        self.config = config
        self.notification_config = self.config["notification"]
        self.report_generator = report_generator

    def send_console_notification(self, processed_updates_list: List[Dict]) -> None:
        """终端输出通知"""
        text_report = self.report_generator.generate_text_report(processed_updates_list)
        print("\n" + "="*80)
        print("📢 GitHub Sentinel 终端通知")
        print("="*80)
        print(text_report)

    def send_email_notification(self, processed_updates_list: List[Dict]) -> None:
        """邮件推送通知"""
        email_config = self.notification_config.get("email", {})
        # 验证邮件配置
        required_email_fields = ["sender", "recipient", "smtp_server", "smtp_port", "smtp_user", "smtp_password"]
        for field in required_email_fields:
            if not email_config.get(field):
                print(f"邮件配置缺少字段：{field}，跳过邮件通知")
                return

        # 生成 Markdown 报告（邮件支持 HTML，可转换 Markdown 为 HTML）
        markdown_report = self.report_generator.generate_markdown_report(processed_updates_list)
        # 简单转换 Markdown 为 HTML（实际可用 markdown 库优化）
        html_report = markdown_report.replace("\n", "<br>").replace("### ", "<h3>").replace("###", "</h3>")
        html_report = html_report.replace("🔹 ", "<strong>").replace("\n- ", "<br>- ").replace("[", "<a href=").replace("]", ">").replace("(", "</a> (")

        # 构造邮件
        msg = MIMEText(html_report, "html", "utf-8")
        msg["From"] = email_config["sender"]
        msg["To"] = email_config["recipient"]
        msg["Subject"] = f"GitHub Sentinel 仓库更新报告（{self.report_generator.report_time[:10]}）"

        try:
            # 连接 SMTP 服务器并发送
            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
            server.starttls()  # 启用 TLS
            server.login(email_config["smtp_user"], email_config["smtp_password"])
            server.send_message(msg)
            server.quit()
            print(f"邮件通知已发送至：{email_config['recipient']}")
        except Exception as e:
            print(f"邮件发送失败：{str(e)}")

    def send_webhook_notification(self, processed_updates_list: List[Dict]) -> None:
        """Webhook 推送通知（JSON 格式）"""
        webhook_config = self.notification_config.get("webhook", {})
        webhook_url = webhook_config.get("url")
        if not webhook_url:
            print("Webhook URL 未配置，跳过 Webhook 通知")
            return

        # 构造 JSON 数据
        payload = {
            "report_time": self.report_generator.report_time,
            "frequency": self.config["check_frequency"],
            "updates": processed_updates_list
        }

        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            print(f"Webhook 通知已发送：{webhook_url}，状态码：{response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Webhook 推送失败：{str(e)}")

    def send_notification(self, processed_updates_list: List[Dict]) -> None:
        """根据配置发送多渠道通知"""
        notification_type = self.notification_config["type"]
        if notification_type == "console":
            self.send_console_notification(processed_updates_list)
        elif notification_type == "email":
            self.send_email_notification(processed_updates_list)
            self.send_console_notification(processed_updates_list)  # 同时终端输出
        elif notification_type == "webhook":
            self.send_webhook_notification(processed_updates_list)
            self.send_console_notification(processed_updates_list)  # 同时终端输出
        else:
            print(f"不支持的通知类型：{notification_type}，仅终端输出")
            self.send_console_notification(processed_updates_list)
EOF

# 3.7 scheduler.py
cat > "$PROJECT_DIR/scheduler.py" << 'EOF'
from apscheduler.schedulers.blocking import BlockingScheduler
from typing import Callable
import logging

# 配置日志（避免 APScheduler 无日志输出）
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class TaskScheduler:
    """任务调度器：定时执行 GitHub 仓库更新检查"""
    def __init__(self, check_frequency: str, task_func: Callable):
        self.frequency = check_frequency
        self.task_func = task_func  # 要执行的任务函数
        self.scheduler = BlockingScheduler()

    def _add_daily_task(self) -> None:
        """添加每日任务（默认每天 9:00 执行）"""
        self.scheduler.add_job(
            self.task_func,
            trigger="cron",
            hour=9,
            minute=0,
            id="daily_update_check",
            name="每日 GitHub 仓库更新检查",
            replace_existing=True
        )
        print("已添加每日任务：每天 9:00 执行更新检查")

    def _add_weekly_task(self) -> None:
        """添加每周任务（默认每周一 9:00 执行）"""
        self.scheduler.add_job(
            self.task_func,
            trigger="cron",
            day_of_week=0,  # 0=周一（APScheduler 中周一为 0，周日为 6）
            hour=9,
            minute=0,
            id="weekly_update_check",
            name="每周 GitHub 仓库更新检查",
            replace_existing=True
        )
        print("已添加每周任务：每周一 9:00 执行更新检查")

    def start_scheduling(self) -> None:
        """启动调度器"""
        # 根据频率添加任务
        if self.frequency == "daily":
            self._add_daily_task()
        else:
            self._add_weekly_task()
        # 立即执行一次任务
        print("立即执行一次更新检查...")
        self.task_func()
        # 启动调度器（阻塞当前线程）
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("调度器已停止")
        finally:
            self.scheduler.shutdown()
EOF

# 3.8 main.py
cat > "$PROJECT_DIR/main.py" << 'EOF'
import argparse
from config import ConfigManager
from subscription_manager import SubscriptionManager
from github_api_client import GitHubAPIClient
from data_processor import DataProcessor
from report_generator import ReportGenerator
from notifier import Notifier
from scheduler import TaskScheduler

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="GitHub Sentinel - 自动跟踪 GitHub 仓库更新的 AI Agent")
    subparsers = parser.add_subparsers(dest="command", required=True, help="子命令：start / add / remove / list")

    # 1. 启动调度器（核心功能）
    parser_start = subparsers.add_parser("start", help="启动更新检查和定时调度")

    # 2. 添加订阅
    parser_add = subparsers.add_parser("add", help="添加 GitHub 仓库订阅")
    parser_add.add_argument("owner", help="仓库所有者（如 octocat）")
    parser_add.add_argument("repo", help="仓库名称（如 hello-world）")
    parser_add.add_argument("--events", nargs="+", required=True, 
                           choices=["commits", "pull_requests", "issues", "releases"],
                           help="要监听的事件类型（可多选）")

    # 3. 删除订阅
    parser_remove = subparsers.add_parser("remove", help="删除 GitHub 仓库订阅")
    parser_remove.add_argument("owner", help="仓库所有者")
    parser_remove.add_argument("repo", help="仓库名称")

    # 4. 列出所有订阅
    parser_list = subparsers.add_parser("list", help="列出所有已订阅的仓库")

    args = parser.parse_args()

    # 初始化核心模块
    try:
        config_manager = ConfigManager()
        subscription_manager = SubscriptionManager(config_manager)
    except ValueError as e:
        print(f"配置错误：{e}")
        return

    # 处理命令
    if args.command == "add":
        # 添加订阅
        subscription_manager.add_subscription(
            owner=args.owner,
            repo=args.repo,
            watch_events=args.events
        )
    elif args.command == "remove":
        # 删除订阅
        subscription_manager.remove_subscription(
            owner=args.owner,
            repo=args.repo
        )
    elif args.command == "list":
        # 列出订阅
        subs = subscription_manager.get_all_subscriptions()
        if not subs:
            print("暂无订阅仓库")
            return
        print("已订阅仓库列表：")
        for i, sub in enumerate(subs, 1):
            print(f"{i}. {sub['owner']}/{sub['repo']}")
            print(f"   监听事件：{', '.join(sub['watch_events'])}")
    elif args.command == "start":
        # 启动核心流程（获取更新 → 处理数据 → 生成报告 → 发送通知）
        def update_check_task():
            print("\n" + "="*80)
            print("开始执行 GitHub 仓库更新检查...")
            print("="*80)

            # 1. 获取所有订阅
            subs = subscription_manager.get_all_subscriptions()
            if not subs:
                print("暂无订阅仓库，跳过更新检查")
                return

            # 2. 初始化其他模块
            github_client = GitHubAPIClient(config_manager)
            data_processor = DataProcessor()
            report_generator = ReportGenerator(config_manager.get_config()["check_frequency"])
            notifier = Notifier(config_manager.get_config(), report_generator)

            # 3. 批量获取原始更新数据
            print(f"正在获取 {len(subs)} 个仓库的更新...")
            raw_updates_list = [github_client.fetch_repo_updates(sub) for sub in subs]

            # 4. 处理数据（提取关键信息 + 过滤无更新仓库）
            processed_updates = data_processor.batch_process_updates(raw_updates_list)
            filtered_updates = data_processor.filter_empty_updates(processed_updates)
            print(f"检查完成：{len(filtered_updates)} 个仓库有更新")

            # 5. 生成报告并发送通知
            notifier.send_notification(filtered_updates)

        # 启动调度器
        scheduler = TaskScheduler(
            check_frequency=config_manager.get_config()["check_frequency"],
            task_func=update_check_task
        )
        scheduler.start_scheduling()

if __name__ == "__main__":
    main()
EOF
