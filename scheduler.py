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
