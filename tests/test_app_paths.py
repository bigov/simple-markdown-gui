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
    def test_ensure_config_exists_copies_sample_to_user_config_dir(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            assets_dir = temp_path / 'assets'
            assets_dir.mkdir()
            sample_path = assets_dir / 'config_sample.ini'
            sample_path.write_text('[Default]\nbase_dir = ./\n', encoding='utf-8')

            user_config_dir = temp_path / 'user-config'

            with patch.object(AppPaths, '_find_assets_dir', return_value=assets_dir):
                with patch.object(AppPaths, '_get_user_config_dir', return_value=user_config_dir):
                    config_path = Path(AppPaths.ensure_config_exists())

            self.assertEqual(user_config_dir / 'config.ini', config_path)
            self.assertTrue(config_path.exists())
            self.assertEqual(sample_path.read_text(encoding='utf-8'), config_path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()