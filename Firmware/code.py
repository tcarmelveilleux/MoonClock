from moonclock_board import MoonClock
from tcv_astro import moon, sun
from tcv_astro import julian, polynomial
from adafruit_datetime import datetime, timedelta
from adafruit_max7219.matrices import CustomMatrix
import array
import gc
import json
import re
import os
import storage
import supervisor
import time
import rtc
import adafruit_gps

CHANNEL_MOON_PHASE = 0
CHANNEL_MOONLESS_HOURS = 1

NUM_SECONDS_TO_RESET_DISPLAY = 127

def debug_print(*args):
  print(*args)


def get_date_of_nth_weekday_of_month(year: int, month: int, weekday: int, num: int) -> int:
  date_iter = datetime(year, month, 1, 0, 0, 0)
  cur_num = 0

  while date_iter.month == month:
    if date_iter.weekday() == weekday:
      cur_num += 1

    if cur_num == num:
      return date_iter.day

    date_iter += timedelta(days=1)

  raise ValueError("Never found the correct day")


class MoonClockSettings:
  def __init__(self, moon_clock: MoonClock):
    self.moon_clock = moon_clock
    self.settings_dict = {
        "utc_offset_seconds": 0,
        "latitude_millionths": 43451600,
        "longitude_millionths": 80492500,
        "dst_strategy": "canada"
    }
    self.is_test_mode = False

  def process_sysex_setting(self, setting: str):
    debug_print("Got SysEx setting command: ", setting)
    tokens = setting.split(',')
    need_save: bool = False

    try:
      if tokens[0] == "UTC":
        hours = int(tokens[1])
        minutes = int(tokens[2])
        seconds = int(tokens[3])

        current_time = self.moon_clock.rtc.datetime
        new_time = time.struct_time((current_time.tm_year, current_time.tm_mon, current_time.tm_mday, hours, minutes, seconds, current_time.tm_wday, -1, -1))
        self.moon_clock.rtc.datetime = new_time
      elif tokens[0] == "DATE":
        year = int(tokens[1])
        month = int(tokens[2])
        day = int(tokens[3])
        dow = int(tokens[4])

        current_time = self.moon_clock.rtc.datetime
        new_time = time.struct_time((year, month, day, current_time.tm_hour, current_time.tm_min, current_time.tm_sec, dow, -1, -1))
        self.moon_clock.rtc.datetime = new_time
      elif tokens[0] == "OFFSET":
        self.settings_dict["utc_offset_seconds"] = int(tokens[1])
        need_save = True
      elif tokens[0] == "DST":
        self.settings_dict["dst_strategy"] = tokens[1]
        need_save = True
      elif tokens[0] == "POS":
        self.settings_dict["latitude_millionths"] = int(tokens[1])
        self.settings_dict["longitude_millionths"] = int(tokens[2])
        need_save = True
      elif tokens[0] == "STOPCAL":
        self.is_test_mode = False
      elif tokens[0] == "CAL":
        self.is_test_mode = True
        channel = int(tokens[1]) % 2
        value = int(tokens[2]) % 4096
        self.moon_clock.dac_driver.load_dac_value(channel, value)
        self.moon_clock.dac_driver.latch_dacs()

    except Exception as e:
      debug_print('Error processing sysex "%s": %s' % (setting, e))
      return

    if need_save:
      self.save_settings()

  def load_settings(self):
    settings_dict = self.moon_clock.load_json_settings()
    if not settings_dict:
      debug_print(settings_dict)
      self.save_settings()
      return

    self.settings_dict.update(settings_dict)

  def save_settings(self):
    self.moon_clock.save_json_settings(self.settings_dict)


  def get_dst_hours_delta(self, local_datetime_before_dst: datetime) -> timedelta:
    strategy = self.settings_dict["dst_strategy"]
    if strategy == "none":
      return timedelta(0)

    if strategy == "canada":
      # On the second Sunday in March, at 2:00 a.m. EST, clocks are advanced to 3:00 a.m. EDT,
      # creating a 23-hour day. On the first Sunday in November, at 2:00 a.m. EDT,
      # clocks are moved back to 1:00 a.m. EST, which results in a 25-hour day
      SUNDAY = 6
      MARCH = 3
      NOVEMBER = 11

      month = local_datetime_before_dst.month
      day = local_datetime_before_dst.day
      hour = local_datetime_before_dst.hour

      second_sunday_of_march = get_date_of_nth_weekday_of_month(local_datetime_before_dst.year, MARCH, SUNDAY, num=2)
      first_sunday_of_october = get_date_of_nth_weekday_of_month(local_datetime_before_dst.year, NOVEMBER, SUNDAY, num=1)
      if month >= MARCH and month <= NOVEMBER:
        if month == MARCH:
          if day >= second_sunday_of_march and hour >= 2:
            return timedelta(hours=1)
          else:
            return timedelta(hours=0)
        elif month == NOVEMBER:
          if day <= first_sunday_of_october and hour < 1:
            return timedelta(hours=1)
          else:
            return timedelta(hours=0)
        else:
          return timedelta(hours=1)

    return timedelta(hours=0)

  def to_local_time(self, now_datetime: datetime) -> datetime:
    local_datetime_before_dst = now_datetime + timedelta(seconds=self.settings_dict["utc_offset_seconds"])
    dst_offset = self.get_dst_hours_delta(local_datetime_before_dst)
    local_datetime = local_datetime_before_dst + dst_offset

    return local_datetime

  def get_local_time(self) -> datetime:
    now = self.moon_clock.rtc.datetime
    now_datetime = datetime(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)

    return self.to_local_time(now_datetime)

  def get_local_struct_time(self, now_datetime: datetime) -> time.struct_time:
    return self.to_local_time(now_datetime).timetuple()

  def get_jd(self) -> float:
    now = self.moon_clock.rtc.datetime
    jd = julian.date_to_julian_day(now.tm_year, now.tm_mon, now.tm_mday) + julian.time_to_fraction(now.tm_hour, now.tm_min, now.tm_sec)
    return jd


class AstroDataComputer:
  def __init__(self, moon_clock: MoonClock, settings: MoonClockSettings):
    OLD_DATE = datetime(1970, 1, 1)

    self._moon_clock = moon_clock

    self._last_full_day_process_time: datetime = OLD_DATE

    self._moon_local_rise_time: datetime = OLD_DATE
    self._moon_local_set_time: datetime = OLD_DATE
    self._sun_local_rise_time: datetime = OLD_DATE
    self._sun_local_set_time: datetime = OLD_DATE

    self._settings = settings

    self._last_moon_age: float = 0.0

    self.LUNAR_PHASE_UPDATE_PERIOD_SECONDS = 10.0

  def set_phase_dial_to_days(self, days:float):
    # curve = [(0.0, 480.0), (1.0, 620.0), (2.0, 737.0), (3.0,  863.0), (4.0, 953.0), (5.0, 1080.0), (6, 1205.0), (7, 1315.0),
    #          (11.0, 1725.0), (14.0, 2020.0), (16.0, 2210.0), (18.0, 2400.0), (21, 2680.0), (23.0, 2852.0), (25.0, 3030.0), (27.0, 3200.0), (28.0, 3300.0), (29.0, 3380.0)]
    # value = int(polynomial.linear_interp_in_parts(days, curve))

    value = int(polynomial.poly_eval(days, [5.046e+02, 1.174e+02, -6.444e-01]))
    self._moon_clock.dac_driver.load_dac_value(CHANNEL_MOON_PHASE, value)
    self._moon_clock.dac_driver.latch_dacs()

  def update_lunar_phase(self, now: float):
    if (now - self._last_moon_age) < self.LUNAR_PHASE_UPDATE_PERIOD_SECONDS:
      return

    self._last_moon_age = now
    normalized_to_28_days = moon.lunar_age_normalized_28_days(jd=self._settings.get_jd())
    self.set_phase_dial_to_days(normalized_to_28_days)

  def process_rise_set(self, local_time: datetime):
    pass

  def process_moonless_hours(self, local_time: datetime):
    pass

  def process(self, now: float, local_time: datetime):
    if local_time.date() != self._last_full_day_process_time.date():
      self._last_full_day_process_time = local_time

      self.process_rise_set(local_time)
      self.process_moonless_hours(local_time)

    self.update_lunar_phase(now)

class Screen:
  def __init__(self, display: CustomMatrix):
    self._display: CustomMatrix = display
    self._screen_change_action = None

  def render(self):
    """Render the screen to display"""
    pass

  def on_left_button_press(self):
    """Handle the "Left" button being pressed"""
    pass

  def on_right_button_press(self):
    """Handle the "Right" button being pressed"""
    pass

  def on_screen_enter(self):
    """Action taken when the screen is just entered, prior to render."""
    pass

  def on_screen_exit(self):
    """Action taken when the screen is just exited, before next screen is entered."""
    pass

  def get_screen_change_action(self):
    """Return a screen-specific value to indicate a screen change"""
    retval = self._screen_change_action
    self._screen_change_action = None
    return retval

  def loop(self, now: float):
    """Executed continously by the main loop."""
    pass

  def back(self):
    """Set the screen change action to "Back" """
    self._screen_change_action = {"is_back": True}
    debug_print("Backing from screen: %s" % self.__class__.__name__)


class TextDisplayScreen(Screen):
  def __init__(self, display: CustomMatrix, settings: MoonClockSettings, num_elements: int):
    super().__init__(display)
    self._last_print = 0.0
    self._settings = settings
    self._num_elements = num_elements
    self._strings: list[str] = [""] * num_elements
    self._current_idx = 0
    self._marquee_time_seconds = 4.0

    # Number of seconds before we force-refresh our garbage dispaly
    self._num_seconds_refresh: int = 0
    self._num_seconds_current_screen: int = 0.0

  def on_left_button_press(self):
    self._screen_change_action = {"action": "previous"}

  def on_right_button_press(self):
    self._screen_change_action = {"action": "next"}

  def render(self):
    self._display.clear_all()

    # HACK: Display with fake MAX7219 dies at random
    self._num_seconds_refresh += 1
    if self._num_seconds_refresh == NUM_SECONDS_TO_RESET_DISPLAY:
      self._display.init_display()
      self._display.clear_all()

    self._display.display_text(3, 0, self._strings[self._current_idx])
    self._display.show()

  def compute_strings(self, local_time: datetime):
    pass

  def loop(self, now: float, local_time: datetime):
    if now - self._last_print < 1.0:
      return

    self._last_print = now

    self.compute_strings(local_time)
    self.render()

    # Process marquee
    self._num_seconds_current_screen += 1
    if self._num_seconds_current_screen >= self._marquee_time_seconds:
      self._num_seconds_current_screen = 0
      self._current_idx += 1
      self._current_idx %= self._num_elements

class LocalTimeScreen(TextDisplayScreen):
  def __init__(self, display: CustomMatrix, settings: MoonClockSettings):
    super().__init__(display, settings, num_elements=1)

  def compute_strings(self, local_time: datetime):
    t = self._settings.get_local_struct_time(local_time)
    self._strings[0] = "{:02}:{:02}:{:02}".format(t.tm_hour, t.tm_min, t.tm_sec)

class DateScreen(TextDisplayScreen):
  def __init__(self, display: CustomMatrix, settings: MoonClockSettings):
    super().__init__(display, settings, num_elements=1)

  def compute_strings(self, local_time: datetime):
    self._strings[0] = "date"

class MoonRiseSetScreen(TextDisplayScreen):
  def __init__(self, display: CustomMatrix, settings: MoonClockSettings, astro_computer: AstroDataComputer):
    super().__init__(display, settings, num_elements=2)
    self._astro_computer = astro_computer

  def compute_strings(self, local_time: datetime):
    self._strings[0] = "moonrise"
    self._strings[1] = "moonset"

class SunRiseSetScreen(TextDisplayScreen):
  def __init__(self, display: CustomMatrix, settings: MoonClockSettings, astro_computer: AstroDataComputer):
    super().__init__(display, settings, num_elements=2)
    self._astro_computer = astro_computer

  def compute_strings(self, local_time: datetime):
    self._strings[0] = "sunrise"
    self._strings[1] = "sunset"

class ScreenStateMachine:
  STATE_UI = 0
  STATE_TEST = 1

  SCREEN_LOCAL_TIME = 0
  SCREEN_DATE = 1
  SCREEN_MOON_RISE_SET = 2
  SCREEN_SUN_RISE_SET = 3

  NUM_SCREENS = 4

  def __init__(self, moon_clock: MoonClock, settings: MoonClockSettings, astro_computer: AstroDataComputer) -> None:
    self.moon_clock = moon_clock
    self.settings = settings
    self.state = self.STATE_UI
    self.astro_computer = astro_computer

    display = self.moon_clock.display

    # Monkey-patch "display_text" method onto every display
    display.display_text = self.moon_clock.display_text

    self.all_screens = [
      LocalTimeScreen(display, self.settings),
      DateScreen(display, self.settings),
      MoonRiseSetScreen(display, self.settings, self.astro_computer),
      SunRiseSetScreen(display, self.settings, self.astro_computer)
    ]

    self.current_screen_id = -1
    self.current_screen: Screen = None

    self.change_screen(0)

  def on_left_button_press(self):
    if self.state == self.STATE_UI:
      self.current_screen.on_left_button_press()

  def on_right_button_press(self):
    if self.state == self.STATE_UI:
      self.current_screen.on_right_button_press()

  def process_screen_change_action(self):
    screen_change_action = self.current_screen.get_screen_change_action()
    if screen_change_action is None:
      return

    if screen_change_action.get("action") == "next":
      self.change_screen((self.current_screen_id + 1) % len(self.all_screens))
    elif screen_change_action.get("action") == "previous":
      self.change_screen((self.current_screen_id - 1) % len(self.all_screens))

  def change_screen(self, screen_id):
    new_screen_id = screen_id % len(self.all_screens)
    new_screen = self.all_screens[new_screen_id]

    if new_screen_id != self.current_screen_id:
      old_screen_name = self.current_screen.__class__.__name__ if self.current_screen is not None else "None"
      new_screen_name = new_screen.__class__.__name__
      debug_print("Going from %s to %s" % (old_screen_name, new_screen_name))

      if self.current_screen is not None:
        self.current_screen.on_screen_exit()

      self.current_screen_id = new_screen_id
      self.current_screen = new_screen

      self.current_screen.on_screen_enter()
      self.current_screen.render()

  def loop(self, now: float, local_time: datetime):
    self.current_screen.loop(now, local_time)
    self.process_screen_change_action()


class MoonClockFirmware:
  def __init__(self):
    self.moon_clock = MoonClock()
    self.settings = MoonClockSettings(self.moon_clock)
    self.settings.load_settings()

    self.astro_data_computer = AstroDataComputer(self.moon_clock, self.settings)

    self.state_machine = ScreenStateMachine(self.moon_clock, self.settings, self.astro_data_computer)

  def loop(self):
    moon_clock: MoonClock = self.moon_clock

    moon_clock.process_midi(handler=self.settings.process_sysex_setting)

    button = moon_clock.buttons.events.get()
    if button and button.pressed:
      if button.key_number == moon_clock.left_button_num:
        self.state_machine.on_left_button_press()
      elif button.key_number == moon_clock.right_button_num:
        self.state_machine.on_right_button_press()

    local_time = self.settings.get_local_time()
    now = time.monotonic()

    self.astro_data_computer.process(now, local_time)

    self.state_machine.loop(now, local_time)

######################################################################

firmware = MoonClockFirmware()
while True:
  firmware.loop()
