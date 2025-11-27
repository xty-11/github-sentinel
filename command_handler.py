from typing import Dict, List, Optional, Callable
from queue import Queue
from dataclasses import dataclass
from enum import Enum

# 命令类型枚举
class CommandType(Enum):
    ADD = "add"
    REMOVE = "remove"
    LIST = "list"
    FETCH = "fetch"
    EXIT = "exit"
    HELP = "help"

# 命令数据结构
@dataclass
class Command:
    type: CommandType
    owner: Optional[str] = None
    repo: Optional[str] = None
    events: Optional[List[str]] = None
    callback: Optional[Callable[[str], None]] = None  # 命令执行结果回调

class CommandHandler:
    """线程安全的命令处理器：接收命令、执行命令、返回结果"""
    def __init__(self, subscription_manager, github_client, data_processor, report_generator, notifier):
        self.subscription_manager = subscription_manager
        self.github_client = github_client
        self.data_processor = data_processor
        self.report_generator = report_generator
        self.notifier = notifier
        self.valid_events = ["commits", "pull_requests", "issues", "releases"]

    def execute(self, command: Command) -> str:
        """执行命令并返回结果"""
        try:
            if command.type == CommandType.ADD:
                if not (command.owner and command.repo and command.events):
                    return "错误：添加订阅需指定 仓库所有者、仓库名称 和 监听事件（--events）"
                # 验证事件有效性
                invalid_events = [e for e in command.events if e not in self.valid_events]
                if invalid_events:
                    return f"错误：无效事件类型 {invalid_events}，支持的事件：{self.valid_events}"
                success = self.subscription_manager.add_subscription(
                    owner=command.owner,
                    repo=command.repo,
                    watch_events=command.events
                )
                return "添加成功" if success else "添加失败（可能已订阅或参数错误）"

            elif command.type == CommandType.REMOVE:
                if not (command.owner and command.repo):
                    return "错误：删除订阅需指定 仓库所有者 和 仓库名称"
                success = self.subscription_manager.remove_subscription(
                    owner=command.owner,
                    repo=command.repo
                )
                return "删除成功" if success else "删除失败（未找到订阅）"

            elif command.type == CommandType.LIST:
                subs = self.subscription_manager.get_all_subscriptions()
                if not subs:
                    return "暂无订阅仓库"
                result = "已订阅仓库列表：\n"
                for i, sub in enumerate(subs, 1):
                    result += f"{i}. {sub['owner']}/{sub['repo']}\n"
                    result += f"   监听事件：{', '.join(sub['watch_events'])}\n"
                return result

            elif command.type == CommandType.FETCH:
                return self._fetch_immediate_updates()

            elif command.type == CommandType.HELP:
                return self._get_help_text()

            elif command.type == CommandType.EXIT:
                return "正在退出程序..."

            else:
                return f"未知命令：{command.type.value}"
        except Exception as e:
            return f"命令执行失败：{str(e)}"

    def _fetch_immediate_updates(self) -> str:
        """立即获取所有订阅仓库的更新并发送通知"""
        subs = self.subscription_manager.get_all_subscriptions()
        if not subs:
            return "暂无订阅仓库，无法获取更新"
        
        result = f"正在获取 {len(subs)} 个仓库的更新...\n"
        # 批量获取并处理更新
        raw_updates_list = [self.github_client.fetch_repo_updates(sub) for sub in subs]
        processed_updates = self.data_processor.batch_process_updates(raw_updates_list)
        filtered_updates = self.data_processor.filter_empty_updates(processed_updates)
        
        # 生成报告并发送通知（终端即时输出）
        if filtered_updates:
            self.notifier.send_console_notification(filtered_updates)
            return result + f"更新检查完成：{len(filtered_updates)} 个仓库有更新（已在终端显示）"
        else:
            return result + "更新检查完成：未检测到任何仓库的更新"

    @staticmethod
    def _get_help_text() -> str:
        """获取帮助信息"""
        return """
GitHub Sentinel 交互式命令帮助：
================================
1. 添加订阅：add <仓库所有者> <仓库名称> --events <事件1> <事件2>...
   示例：add octocat hello-world --events commits issues
   支持事件：commits（提交）、pull_requests（PR）、issues（问题）、releases（发布）

2. 删除订阅：remove <仓库所有者> <仓库名称>
   示例：remove octocat hello-world

3. 列出订阅：list
   功能：查看所有已订阅的仓库及监听事件

4. 立即更新：fetch
   功能：手动触发一次全量更新检查，即时显示结果

5. 帮助信息：help
   功能：查看所有支持的命令

6. 退出程序：exit
   功能：安全退出，保存当前订阅配置
================================
"""