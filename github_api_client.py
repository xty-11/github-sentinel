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
