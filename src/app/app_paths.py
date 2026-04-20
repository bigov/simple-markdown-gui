import os
import shutil
import sys
from pathlib import Path


class AppPaths:
    app_name = 'Simple Markdown GUI'

    @classmethod
    def _get_runtime_dir(cls) -> Path:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS)
        return Path(__file__).resolve().parent

    @classmethod
    def _find_assets_dir(cls) -> Path:
        current_dir = cls._get_runtime_dir()

        for candidate in (current_dir, *current_dir.parents):
            assets_dir = candidate / 'assets'
            if assets_dir.is_dir():
                return assets_dir

        raise FileNotFoundError("Unable to locate the 'assets' directory.")

    @classmethod
    def _get_user_config_dir(cls) -> Path:
        appdata_dir = os.environ.get('APPDATA')
        if appdata_dir:
            return Path(appdata_dir) / cls.app_name
        return Path.home() / '.config' / cls.app_name

    @classmethod
    def get_assets_dir(cls) -> str:
        return str(cls._find_assets_dir())

    @classmethod
    def get_config_dir(cls) -> str:
        return str(cls._get_user_config_dir())

    @classmethod
    def get_config_path(cls) -> str:
        return str(cls._get_user_config_dir() / 'config.ini')

    @classmethod
    def get_config_sample_path(cls) -> str:
        return str(cls._find_assets_dir() / 'config_sample.ini')

    @classmethod
    def get_legacy_config_path(cls) -> str:
        return str(cls._find_assets_dir() / 'config.ini')

    @classmethod
    def get_styles_path(cls) -> str:
        return str(cls._find_assets_dir() / 'styles.css')

    @classmethod
    def ensure_config_exists(cls) -> str:
        config_dir = cls._get_user_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / 'config.ini'

        if config_path.exists():
            return str(config_path)

        legacy_config_path = Path(cls.get_legacy_config_path())
        if legacy_config_path.exists() and not getattr(sys, 'frozen', False):
            shutil.copyfile(legacy_config_path, config_path)
            return str(config_path)

        config_sample_path = Path(cls.get_config_sample_path())
        if config_sample_path.exists():
            shutil.copyfile(config_sample_path, config_path)
        else:
            config_path.touch()

        return str(config_path)