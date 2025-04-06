from moonclock_board import MoonClock
from tcv_astro import moon, sun
from tcv_astro import julian, polynomial
from adafruit_datetime import datetime, timedelta
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

  def get_local_time(self) -> time.struct_time:
    now = self.moon_clock.rtc.datetime
    now_datetime = datetime(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)
    local_datetime_before_dst = now_datetime + timedelta(seconds=self.settings_dict["utc_offset_seconds"])
    dst_offset = self.get_dst_hours_delta(local_datetime_before_dst)
    local_datetime = local_datetime_before_dst + dst_offset

    return local_datetime.timetuple()

  def get_jd(self) -> float:
    now = self.moon_clock.rtc.datetime
    jd = julian.date_to_julian_day(now.tm_year, now.tm_mon, now.tm_mday) + julian.time_to_fraction(now.tm_hour, now.tm_min, now.tm_sec)
    return jd

class MoonClockFirmware:
  def __init__(self):
    self.moon_clock = MoonClock()
    self.settings = MoonClockSettings(self.moon_clock)
    self.settings.load_settings()

    self.dac_value = 0

    self._last_print = time.monotonic()
    self._last_dial = time.monotonic()
    self._last_moon_age = time.monotonic()

    self._num_seconds_refresh = 0
    self.NUM_SECONDS_TO_RESET_DISPLAY = 127

  def set_phase_dial_to_days(self, days:float):
    # curve = [(0.0, 480.0), (1.0, 620.0), (2.0, 737.0), (3.0,  863.0), (4.0, 953.0), (5.0, 1080.0), (6, 1205.0), (7, 1315.0),
    #          (11.0, 1725.0), (14.0, 2020.0), (16.0, 2210.0), (18.0, 2400.0), (21, 2680.0), (23.0, 2852.0), (25.0, 3030.0), (27.0, 3200.0), (28.0, 3300.0), (29.0, 3380.0)]
    # value = int(polynomial.linear_interp_in_parts(days, curve))

    value = int(polynomial.poly_eval(days, [5.046e+02, 1.174e+02, -6.444e-01]))
    self.moon_clock.dac_driver.load_dac_value(CHANNEL_MOON_PHASE, value)
    self.moon_clock.dac_driver.latch_dacs()
    print("value: %d" % value)


  def loop(self):
    moon_clock: MoonClock = self.moon_clock

    moon_clock.process_midi(handler=self.settings.process_sysex_setting)

    button = moon_clock.buttons.events.get()
    if button and button.pressed :
      if button.key_number == moon_clock.left_button_num:
        print("Left button pressed")
      elif button.key_number == moon_clock.right_button_num:
        print("Right button pressed")

    # Every second print out current time from GPS, RTC and time.localtime()
    now = time.monotonic()

    if now - self._last_print >= 1.0:
        self._last_print = now
        t = self.settings.get_local_time()
        time_str = "{:02}:{:02}:{:02}".format(t.tm_hour, t.tm_min, t.tm_sec)
        moon_clock.display.clear_all()

        # HACK: Display with fake MAX7219 dies at random
        self._num_seconds_refresh += 1
        if self._num_seconds_refresh == self.NUM_SECONDS_TO_RESET_DISPLAY:
            moon_clock.display.init_display()
            moon_clock.display.clear_all()

        moon_clock.display_text(3, 0, time_str)
        moon_clock.display.show()

    if now - self._last_moon_age >= 10.0:
        self._last_moon_age = now

        # TODO: Move this computation to the moon module
        jd = self.settings.get_jd()
        solar_pos = sun.solar_coordinates_low_accuracy_meeus(jd)
        lunar_pos = moon.lunar_coordinates_high_accuracy_meeus(jd)

        moon_age_days: float = ((lunar_pos.true_lon - solar_pos.true_lon) % 360.0) / 12.1907
        debug_print("Moon age: %.3f" % (moon_age_days))
        if not self.settings.is_test_mode:
          normalized_to_28_days = (moon_age_days / 29.530575) * 28.0
          self.set_phase_dial_to_days(normalized_to_28_days)


    if False:
        if now - self._last_dial >= 0.01:
            self._last_dial = now
            moon_clock.dac_driver.load_dac_value(0, self.dac_value)
            moon_clock.dac_driver.load_dac_value(1, self.dac_value)
            moon_clock.dac_driver.latch_dacs()
            self.dac_value += 1
            if self.dac_value > 3500:
              self.dac_value = 0

t1 = time.monotonic()
position = moon.lunar_coordinates_high_accuracy_meeus(jd=2448724.5)
t2 = time.monotonic()

debug_print("%.3f" % (t2 - t1))
debug_print("ra %.6f" % position.ra_apparent)
debug_print("dec %.6f" % position.dec_apparent)

firmware = MoonClockFirmware()
while True:
  firmware.loop()
