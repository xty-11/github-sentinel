import argparse
import selectors
import sys
import threading
import time
from queue import Queue, Empty  # 导入 Empty 异常类
from typing import Optional

from config import ConfigManager
from subscription_manager import SubscriptionManager
from github_api_client import GitHubAPIClient
from data_processor import DataProcessor
from report_generator import ReportGenerator
from notifier import Notifier
from scheduler import TaskScheduler
from command_handler import CommandHandler, Command, CommandType

# 全局配置
COMMAND_QUEUE = Queue(maxsize=10)  # 命令队列（主线程→子线程）
RESULT_QUEUE = Queue(maxsize=10)   # 结果队列（子线程→主线程）

def parse_input_line(line: str) -> Optional[Command]:
    """解析终端输入，转换为 Command 对象"""
    line = line.strip()
    if not line:
        return None

    parts = line.split()
    cmd_name = parts[0].lower()

    # 解析 help/exit/fetch 命令
    if cmd_name == "help":
        return Command(type=CommandType.HELP)
    elif cmd_name == "exit":
        return Command(type=CommandType.EXIT)
    elif cmd_name == "fetch":
        return Command(type=CommandType.FETCH)

    # 解析 list 命令
    elif cmd_name == "list":
        return Command(type=CommandType.LIST)

    # 解析 add 命令（格式：add owner repo --events e1 e2...）
    elif cmd_name == "add":
        if len(parts) < 5 or "--events" not in parts:
            RESULT_QUEUE.put("错误：add 命令格式错误！正确格式：add <所有者> <仓库> --events <事件1> <事件2>...")
            return None
        events_idx = parts.index("--events")
        if events_idx < 3:  # 至少需要 add owner repo --events
            RESULT_QUEUE.put("错误：add 命令缺少必要参数！")
            return None
        owner = parts[1]
        repo = parts[2]
        events = parts[events_idx+1:]
        return Command(
            type=CommandType.ADD,
            owner=owner,
            repo=repo,
            events=events
        )

    # 解析 remove 命令（格式：remove owner repo）
    elif cmd_name == "remove":
        if len(parts) != 3:
            RESULT_QUEUE.put("错误：remove 命令格式错误！正确格式：remove <所有者> <仓库>")
            return None
        owner = parts[1]
        repo = parts[2]
        return Command(
            type=CommandType.REMOVE,
            owner=owner,
            repo=repo
        )

    # 未知命令
    else:
        RESULT_QUEUE.put(f"错误：未知命令 '{cmd_name}'，输入 help 查看支持的命令")
        return None

def input_listener():
    """非阻塞输入监听器（主线程）：监听终端输入，放入命令队列"""
    # 配置非阻塞 IO
    selector = selectors.DefaultSelector()
    selector.register(sys.stdin, selectors.EVENT_READ)

    print("=== GitHub Sentinel 交互式模式（v0.0.1）===")
    print("输入 help 查看支持的命令，输入 exit 退出程序")
    print("========================================\n")

    while True:
        # 非阻塞等待输入（超时 0.5 秒，避免 CPU 占用过高）
        events = selector.select(timeout=0.5)
        for key, mask in events:
            if key.fileobj == sys.stdin:
                line = sys.stdin.readline()
                if line:  # 读取到输入
                    # 处理换行符和特殊字符
                    line = line.rstrip('\n\r')
                    cmd = parse_input_line(line)
                    if cmd:
                        try:
                            COMMAND_QUEUE.put_nowait(cmd)
                            # 特殊处理 exit 命令：放入队列后直接退出主线程
                            if cmd.type == CommandType.EXIT:
                                return
                        except Queue.Full:
                            print("错误：命令队列已满，请稍后再试")
                else:  # 输入流关闭（如 Ctrl+D）
                    COMMAND_QUEUE.put_nowait(Command(type=CommandType.EXIT))
                    return

        # 检查结果队列，输出命令执行结果
        while not RESULT_QUEUE.empty():
            result = RESULT_QUEUE.get_nowait()
            print(f"\n{result}\n")
            print("请输入命令（help 查看帮助）：", end="", flush=True)

def task_worker(config_manager: ConfigManager):
    """任务工作线程（子线程）：执行定时任务 + 处理命令队列"""
    # 初始化核心模块
    try:
        subscription_manager = SubscriptionManager(config_manager)
        github_client = GitHubAPIClient(config_manager)
        data_processor = DataProcessor()
        check_frequency = config_manager.get_config()["check_frequency"]
        report_generator = ReportGenerator(check_frequency)
        notifier = Notifier(config_manager.get_config(), report_generator)
        command_handler = CommandHandler(
            subscription_manager=subscription_manager,
            github_client=github_client,
            data_processor=data_processor,
            report_generator=report_generator,
            notifier=notifier
        )
    except Exception as e:
        RESULT_QUEUE.put(f"初始化失败：{str(e)}")
        return

    # 定义定时任务（与原逻辑一致）
    def scheduled_update_task():
        try:
            print("\n" + "="*80)
            print("定时更新检查启动...")
            print("="*80)
            subs = subscription_manager.get_all_subscriptions()
            if not subs:
                print("定时更新检查完成：未检测到任何仓库的更新\n")
                return
            raw_updates_list = [github_client.fetch_repo_updates(sub) for sub in subs]
            processed_updates = data_processor.batch_process_updates(raw_updates_list)
            filtered_updates = data_processor.filter_empty_updates(processed_updates)
            if filtered_updates:
                notifier.send_notification(filtered_updates)
            else:
                print("定时更新检查完成：未检测到任何仓库的更新\n")
        except Exception as e:
            print(f"定时任务执行失败：{str(e)}\n")

    # 启动定时调度器（非阻塞模式，用线程包装）
    try:
        scheduler_thread = threading.Thread(
            target=TaskScheduler(check_frequency, scheduled_update_task).start_scheduling,
            daemon=True  # 主线程退出时自动终止
        )
        scheduler_thread.start()
        print("定时任务已启动，按配置频率自动执行更新检查\n")
        print("请输入命令（help 查看帮助）：", end="", flush=True)
    except Exception as e:
        RESULT_QUEUE.put(f"定时任务启动失败：{str(e)}")
        return

    # 循环处理命令队列（核心修复：捕获 Empty 异常）
    while True:
        try:
            # 非阻塞获取命令（超时 1 秒，避免 CPU 空转）
            cmd = COMMAND_QUEUE.get(timeout=1)
            # 执行命令并获取结果
            result = command_handler.execute(cmd)
            # 将结果放入结果队列，供主线程输出
            RESULT_QUEUE.put_nowait(result)
            # 处理退出命令
            if cmd.type == CommandType.EXIT:
                time.sleep(0.5)  # 等待结果输出
                return
        except Empty:  # 修复：捕获正确的 Empty 异常（从 queue 导入）
            continue  # 无命令时继续循环，不阻塞
        except Exception as e:
            RESULT_QUEUE.put_nowait(f"命令处理异常：{str(e)}")

def main():
    # 解析命令行参数（仅保留 start 命令，兼容原有启动方式）
    parser = argparse.ArgumentParser(description="GitHub Sentinel - 交互式 GitHub 仓库动态跟踪工具")
    subparsers = parser.add_subparsers(dest="command", required=True, help="子命令")
    parser_start = subparsers.add_parser("start", help="启动交互式模式")
    args = parser.parse_args()

    # 初始化配置（优先处理配置错误）
    try:
        config_manager = ConfigManager()
    except ValueError as e:
        print(f"配置错误：{e}")
        return

    # 启动子线程（任务工作线程）
    worker_thread = threading.Thread(
        target=task_worker,
        args=(config_manager,),
        daemon=False  # 等待子线程处理完退出命令
    )
    worker_thread.start()

    # 启动主线程（非阻塞输入监听器）
    input_listener()

    # 等待子线程退出
    worker_thread.join(timeout=5)
    print("\n程序已安全退出，订阅配置已保存")

if __name__ == "__main__":
    main()