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
