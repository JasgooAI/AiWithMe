"""配置加载模块"""
import os
import yaml
from pathlib import Path
from typing import Any


class Config:
    """配置管理器"""

    _instance = None
    _config: dict = {}
    _sources: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._config:
            self._load_config()

    @property
    def base_path(self) -> Path:
        """项目根目录（Obsidian vault）"""
        # src 在 .archive 文件夹中，所以需要向上4级
        return Path(__file__).parent.parent.parent.parent

    @property
    def archive_path(self) -> Path:
        """归档目录（代码和配置）"""
        return self.base_path / '.archive'

    @property
    def config_path(self) -> Path:
        """配置文件目录"""
        return self.archive_path / '.system' / 'config'

    @property
    def data_path(self) -> Path:
        """数据目录"""
        return self.archive_path / '.system' / 'data'

    @property
    def logs_path(self) -> Path:
        """日志目录"""
        return self.archive_path / '.system' / 'logs'

    def _load_config(self) -> None:
        """加载配置文件"""
        config_file = self.config_path / 'config.yaml'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}

        sources_file = self.config_path / 'sources.yaml'
        if sources_file.exists():
            with open(sources_file, 'r', encoding='utf-8') as f:
                self._sources = yaml.safe_load(f) or {}

    def reload(self) -> None:
        """重新加载配置"""
        self._config = {}
        self._sources = {}
        self._load_config()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项，支持点分隔的键"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    @property
    def api_key(self) -> str:
        """获取 API Key（优先使用环境变量）"""
        return os.environ.get('INTEL_API_KEY') or self.get('api.api_key', '')

    @property
    def api_base_url(self) -> str:
        """获取 API Base URL（优先使用环境变量）"""
        return os.environ.get('INTEL_API_BASE_URL') or self.get('api.base_url', '')

    @property
    def api_model(self) -> str:
        """获取模型名称"""
        return self.get('api.model', 'gemini-2.5-flash')

    @property
    def sources(self) -> list:
        """获取启用的信息源列表"""
        all_sources = self._sources.get('sources', [])
        # 过滤掉 enabled: false 的源
        return [s for s in all_sources if s.get('enabled', True)]

    @property
    def output_paths(self) -> dict:
        """获取输出路径配置"""
        return {
            'daily_summary': self.base_path / '每日汇总',
            'articles': self.base_path / '文章',
            'favorites': self.base_path,  # 精华汇总在根目录
            'sources_index': self.base_path / '来源',
        }

    @property
    def db_path(self) -> Path:
        """数据库路径"""
        return self.data_path / 'articles.db'


# 全局配置实例
config = Config()
