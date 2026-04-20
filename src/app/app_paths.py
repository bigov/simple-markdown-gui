from pathlib import Path


class AppPaths:
    @staticmethod
    def _find_assets_dir() -> str:
        current_dir = Path(__file__).resolve().parent

        for candidate in (current_dir, *current_dir.parents):
            assets_dir = candidate / 'assets'
            if assets_dir.is_dir():
                return str(assets_dir)

        raise FileNotFoundError("Unable to locate the 'assets' directory.")

    config_dir = _find_assets_dir.__func__()

    @classmethod
    def get_config_path(cls) -> str:
        return str(Path(cls.config_dir) / 'config.ini')

    @classmethod
    def get_styles_path(cls) -> str:
        return str(Path(cls.config_dir) / 'styles.css')