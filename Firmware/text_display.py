import gc

class TextDisplay:
  def __init__(self, ssd3306_display) -> None:
    self._display = ssd3306_display

    self.font_width = 5
    self.font_height = 8

    self.char_width:int = self._display.width // self.font_width
    self.char_height:int = self._display.height // self.font_height
    self.cursor_x:int = 0
    self.cursor_y:int = 0

    self._display.fill(0)
    self._display.show()

  def set_cursor_x(self, x:int):
    self.cursor_x = min(x, self.char_width - 1)

  def set_cursor_y(self, y:int):
    self.cursor_y = min(y, self.char_height - 1)

  def set_cursor(self, x: int, y: int):
    self.set_cursor_x(x)
    self.set_cursor_y(y)

  def show(self):
    self._display.show()

    # Force-garbage-collect after SHOW due to enormous heap usage.
    gc.collect()

  def write(self, text:str):
    for char in text:
      if char == '\n':
        self.set_cursor(0, self.cursor_y + 1)
      elif char == '\r':
        self.set_cursor_x(0)
      else:
        self._display.text(char, self.cursor_x * self.font_width, self.cursor_y * self.font_height, 1)
        self.advance_cursor()

  def advance_cursor(self):
    new_x = self.cursor_x + 1
    new_y = self.cursor_y
    if new_x >= self.char_width:
      new_x = 0
      new_y = self.cursor_y + 1
    self.set_cursor(new_x, new_y)

  def clear(self, force_show=False):
    self.set_cursor(0, 0)
    self._display.fill(0)
    if force_show:
      self.show()
