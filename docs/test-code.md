# Заголовок первый

## Заголовок второй

### Заголовок третий

#### Заголовок четвертый

##### Заголовок пятый

###### Заголовок шестой

  


**Пример кода**:

```
@Slot()
def toggle_bold(self):
    cursor = self.editor.textCursor()
    if not cursor.hasSelection():
        return

    selected_format = cursor.charFormat()
    new_format = QTextCharFormat(selected_format)
    if selected_format.fontWeight() == QFont.Bold:
        new_format.setFontWeight(QFont.Normal)
    else:
        new_format.setFontWeight(QFont.Bold)
    cursor.mergeCharFormat(new_format)
    self.editor.mergeCurrentCharFormat(new_format)
```