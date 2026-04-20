import os
import shutil
import sys
from pathlib import Path


class AppPaths:
    app_name = 'Simple Markdown GUI'
    config_dir_name = 'assets'
    styles_file_name = 'styles.css'
    config_file_name = 'config.ini'
    config_sample_file_name = 'config_sample.ini'

    windows_appdata_var_name = 'APPDATA'
    unix_config_dir_name = '.config'

    frozen_attr_name = 'frozen'
    meipass_attr_name = '_MEIPASS'

    write_test_file_name = '.write_test'
    write_test_content = 'ok'
    missing_config_dir_message = 'Unable to locate the config directory.'

    @classmethod
    def _is_frozen(cls) -> bool:
        return bool(
            getattr(sys, cls.frozen_attr_name, False)
            and hasattr(sys, cls.meipass_attr_name)
        )

    @classmethod
    def _get_runtime_dir(cls) -> Path:
        if cls._is_frozen():
            return Path(getattr(sys, cls.meipass_attr_name))
        return Path(__file__).resolve().parent

    @classmethod
    def _find_assets_dir(cls) -> Path:
        current_dir = cls._get_runtime_dir()

        for candidate in (current_dir, *current_dir.parents):
            assets_dir = candidate / cls.config_dir_name
            if assets_dir.is_dir():
                return assets_dir

        raise FileNotFoundError(cls.missing_config_dir_message)

    @classmethod
    def _get_user_config_dir(cls) -> Path:
        windows_config_dir_name = os.environ.get(cls.windows_appdata_var_name)
        if windows_config_dir_name:
            return Path(windows_config_dir_name) / cls.app_name / cls.config_dir_name
        return Path.home() / cls.unix_config_dir_name / cls.app_name / cls.config_dir_name

    @classmethod
    def _get_portable_runtime_dir(cls) -> Path:
        if cls._is_frozen():
            return Path(sys.executable).resolve().parent / cls.config_dir_name
        return cls._find_assets_dir()

    @classmethod
    def _is_writable_directory(cls, directory: Path) -> bool:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe_path = directory / cls.write_test_file_name
            probe_path.write_text(cls.write_test_content, encoding='utf-8')
            probe_path.unlink()
            return True
        except OSError:
            return False

    @classmethod
    def _get_runtime_assets_dir(cls) -> Path:
        portable_dir = cls._get_portable_runtime_dir()
        if cls._is_writable_directory(portable_dir):
            return portable_dir
        return cls._get_user_config_dir()

    @classmethod
    def get_assets_dir(cls) -> str:
        return str(cls._get_runtime_assets_dir())

    @classmethod
    def get_config_dir(cls) -> str:
        return str(cls._get_runtime_assets_dir())

    @classmethod
    def get_config_path(cls) -> str:
        return str(cls._get_runtime_assets_dir() / cls.config_file_name)

    @classmethod
    def get_config_sample_path(cls) -> str:
        return str(cls._find_assets_dir() / cls.config_sample_file_name)

    @classmethod
    def get_styles_path(cls) -> str:
        return str(cls._get_runtime_assets_dir() / cls.styles_file_name)

    @classmethod
    def get_styles_template_path(cls) -> str:
        return str(cls._find_assets_dir() / cls.styles_file_name)

    @classmethod
    def ensure_runtime_assets_exist(cls) -> str:
        runtime_assets_dir = cls._get_runtime_assets_dir()
        runtime_assets_dir.mkdir(parents=True, exist_ok=True)

        config_path = runtime_assets_dir / cls.config_file_name
        if not config_path.exists():
            config_sample_path = Path(cls.get_config_sample_path())
            if config_sample_path.exists():
                shutil.copyfile(config_sample_path, config_path)
            else:
                config_path.touch()

        styles_path = runtime_assets_dir / cls.styles_file_name
        if not styles_path.exists():
            styles_template_path = Path(cls.get_styles_template_path())
            if styles_template_path.exists():
                shutil.copyfile(styles_template_path, styles_path)
            else:
                styles_path.touch()

        return str(runtime_assets_dir)

    @classmethod
    def ensure_config_exists(cls) -> str:
        runtime_assets_dir = Path(cls.ensure_runtime_assets_exist())
        return str(runtime_assets_dir / cls.config_file_name)