import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
SRC_APP = WORKSPACE_ROOT / 'src' / 'app'

if str(SRC_APP) not in sys.path:
    sys.path.insert(0, str(SRC_APP))

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from filesystem import _save_markdown_to_path, load_file_by_path
from main import MyWidget


class DummyEvent:
    def accept(self):
        return None


class MarkdownRoundtripTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.source_path = WORKSPACE_ROOT / 'docs' / 'test-code.md'

    def setUp(self):
        self.widget = MyWidget()

    def tearDown(self):
        self.widget.close()

    def _open_in_visual_mode(self):
        load_file_by_path(str(self.source_path), self.widget)
        self.widget.switch_to_edit(DummyEvent())

    def test_save_unmodified_document_preserves_original_markdown(self):
        self._open_in_visual_mode()

        with TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / 'copy.md'
            _save_markdown_to_path(self.widget, str(target_path))

            self.assertEqual(
                self.source_path.read_text(encoding='utf-8'),
                target_path.read_text(encoding='utf-8'),
            )

    def test_save_visual_edit_preserves_existing_markdown_structure(self):
        self._open_in_visual_mode()

        cursor = self.widget.editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.EndOfBlock)
        cursor.insertBlock()
        cursor.insertText('Добавленный абзац после заголовка.')
        self.widget.editor.setTextCursor(cursor)
        self.widget.editor.document().setModified(True)

        with TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / 'visual-edit.md'
            _save_markdown_to_path(self.widget, str(target_path))
            saved_text = target_path.read_text(encoding='utf-8')

        self.assertIn('Добавленный абзац после заголовка.', saved_text)
        self.assertIn('\n\nДобавленный абзац после заголовка.\n\n## Заголовок второй', saved_text)
        self.assertIn('## Заголовок второй', saved_text)
        self.assertIn('**Пример кода**:', saved_text)
        self.assertGreaterEqual(saved_text.count('```'), 2)


if __name__ == '__main__':
    unittest.main()