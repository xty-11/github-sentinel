import json
import os
from typing import Dict, Optional

#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
class ConfigManager:
    """配置管理器：加载、验证、提供配置信息"""
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.expanduser("~/Study/AI/github-sentinel-secret/config.json")
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
            "github_token": "",
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
