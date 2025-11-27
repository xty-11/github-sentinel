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

    def send_console_notification(self, processed_updates_list: list[Dict]) -> None:
        """终端输出通知"""
        text_report = self.report_generator.generate_text_report(processed_updates_list)
        print("\n" + "="*80)
        print("📢 GitHub Sentinel 终端通知")
        print("="*80)
        print(text_report)

    def send_email_notification(self, processed_updates_list: list[Dict]) -> None:
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

    def send_webhook_notification(self, processed_updates_list: list[Dict]) -> None:
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

    def send_notification(self, processed_updates_list: list[Dict]) -> None:
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
