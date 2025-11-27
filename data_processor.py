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
