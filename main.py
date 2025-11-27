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
