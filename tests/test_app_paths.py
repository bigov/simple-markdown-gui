import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
SRC_APP = WORKSPACE_ROOT / 'src' / 'app'

if str(SRC_APP) not in sys.path:
    sys.path.insert(0, str(SRC_APP))

from app_paths import AppPaths


class AppPathsTest(unittest.TestCase):
    def test_ensure_runtime_assets_exist_copies_config_and_styles(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            assets_dir = temp_path / 'assets'
            assets_dir.mkdir()
            config_sample_path = assets_dir / 'config_sample.ini'
            config_sample_path.write_text('[Default]\nbase_dir = ./\n', encoding='utf-8')
            styles_template_path = assets_dir / 'styles.css'
            styles_template_path.write_text('body { color: #333; }\n', encoding='utf-8')

            runtime_assets_dir = temp_path / 'runtime-assets'

            with patch.object(AppPaths, '_find_assets_dir', return_value=assets_dir):
                with patch.object(AppPaths, '_get_runtime_assets_dir', return_value=runtime_assets_dir):
                    config_path = Path(AppPaths.ensure_config_exists())
                    styles_path = Path(AppPaths.get_styles_path())

            self.assertEqual(runtime_assets_dir / 'config.ini', config_path)
            self.assertTrue(config_path.exists())
            self.assertTrue(styles_path.exists())
            self.assertEqual(config_sample_path.read_text(encoding='utf-8'), config_path.read_text(encoding='utf-8'))
            self.assertEqual(styles_template_path.read_text(encoding='utf-8'), styles_path.read_text(encoding='utf-8'))

    def test_get_runtime_assets_dir_prefers_portable_directory_when_writable(self):
        with TemporaryDirectory() as temp_dir:
            portable_assets_dir = Path(temp_dir) / 'portable-assets'

            with patch.object(AppPaths, '_get_portable_runtime_dir', return_value=portable_assets_dir):
                with patch.object(AppPaths, '_get_user_config_dir', return_value=Path(temp_dir) / 'user-assets'):
                    runtime_assets_dir = AppPaths._get_runtime_assets_dir()

            self.assertEqual(portable_assets_dir, runtime_assets_dir)


if __name__ == '__main__':
    unittest.main()