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
