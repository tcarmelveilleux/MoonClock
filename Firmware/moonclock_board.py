import board
import busio
import analogio
from digitalio import Pull, Direction, DigitalInOut
import microcontroller
import keypad
import neopixel
import adafruit_gps
import select
import winterbloom_smolmidi as smolmidi
import usb_midi
from adafruit_bus_device.spi_device import SPIDevice
from adafruit_max7219.matrices import CustomMatrix
from adafruit_ds3231 import DS3231
from adafruit_bitmap_font import bitmap_font
import time

# Give us a chance to run GC on circuitpython
try:
    import gc
    def run_gc():
        gc.collect()
except:
    def run_gc():
        pass

try:
  import ujson as json
except ImportError:
  import json


FONT_FILE = "fonts/moonclock.bdf"

# Using CircuitPython 9.x with https://circuitpython.org/board/waveshare_rp2040_zero/
# CircuitPython tips: https://github.com/todbot/circuitpython-tricks
# SPI/I2C tutorial: https://www.digikey.ca/en/maker/projects/circuitpython-basics-i2c-and-spi/9799e0554de14af3850975dfb0174ae3

class MCP49xxDriver:
  def __init__(self, spi_device: SPIDevice, ldac_pin: DigitalInOut, resolution_bits: int):
    self._spi_device: SPIDevice = spi_device
    self._resolution_mask = (1 << resolution_bits) - 1
    self._ldac_pin = ldac_pin

  def load_dac_value(self, channel_idx: int, value: int):
    MCP49XX_CHAN_SEL_BIT = 1 << 15
    MCP49XX_BUF_EN_BIT = 1 << 14
    MCP49XX_UNITY_GAIN_BIT = 1 << 13
    MCP49XX_SHDN_BIT = 1 << 12

    if channel_idx > 1:
      raise ValueError("Bad channel")

    code_val = value & self._resolution_mask

    # Always active, always buffer enabled, always unity gain. Make your own driver if you don't like it.
    cfg_reg = MCP49XX_SHDN_BIT | MCP49XX_BUF_EN_BIT | MCP49XX_UNITY_GAIN_BIT

    cfg_reg |= MCP49XX_CHAN_SEL_BIT if (channel_idx != 0) else 0
    cfg_reg |= code_val

    with self._spi_device as spi:
      spi.write(bytes([cfg_reg >> 8, cfg_reg & 0xff]))

  def latch_dacs(self):
    self._ldac_pin.value = False
    self._ldac_pin.value = False

    self._ldac_pin.value = True


class MoonClock:
  def __init__(self):
    # DAC pins and SPI device
    self.dac_cs_pin = DigitalInOut(board.GP26)
    self.dac_cs_pin.pull = None
    self.dac_cs_pin.switch_to_output(value=True)

    self.dac_ldac_pin = DigitalInOut(board.GP27)
    self.dac_ldac_pin.pull = None
    self.dac_ldac_pin.switch_to_output(value=True)

    self.dac_spi = busio.SPI(board.GP14, MOSI=board.GP15)
    self.dac_spi_device = SPIDevice(self.dac_spi, chip_select=self.dac_cs_pin, baudrate=1000000, polarity=0, phase=0)

    self.dac_driver = MCP49xxDriver(self.dac_spi_device, ldac_pin=self.dac_ldac_pin, resolution_bits=12)
    self.dac_driver.load_dac_value(0, 0)
    self.dac_driver.load_dac_value(1, 0)
    self.dac_driver.latch_dacs()

    # Display pins and SPI device
    self.display_cs_pin = DigitalInOut(board.GP5)
    self.display_cs_pin.pull = None
    self.display_cs_pin.switch_to_output(value=True)

    self.font = bitmap_font.load_font(FONT_FILE)
    run_gc()
    self.display_spi = busio.SPI(board.GP2, MOSI=board.GP3)
    #self.display_spi_device = SPIDevice(self.display_spi, chip_select=self.display_cs_pin, baudrate=1000000, polarity=0, phase=0)
    self.display = CustomMatrix(spi=self.display_spi, cs=self.display_cs_pin, width=32, height=8)
    self.display.init_display()
    self.display.brightness(0)
    self.display.clear_all()
    self.display.show()
    run_gc()

    # ADC Input 1 (for debug, not used yet)
    self.pot_adc_in = analogio.AnalogIn(board.A3)

    # Button0 (left), Button1 (right)
    self.button_pins = (board.GP8, board.GP4)
    self.buttons = keypad.Keys(self.button_pins, value_when_pressed=False, pull=True)
    self.left_button_num = 0
    self.right_button_num = 1

    # I2C port (for debug, not used yet)
    self.SCL1_PIN = board.GP11
    self.SDA1_PIN = board.GP10
    self.i2c1 = busio.I2C(self.SCL1_PIN, self.SDA1_PIN, frequency=100_000)
    self.rtc = DS3231(self.i2c1)

    # GPS UART0
    self.GPS_TX0_PIN = board.GP0
    self.GPS_RX0_PIN = board.GP1
    self.gps_uart = busio.UART(self.GPS_TX0_PIN, self.GPS_RX0_PIN, baudrate=9_600)

    self.gps = adafruit_gps.GPS(self.gps_uart, debug=False)

    # NeoPixel
    self.neopixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.1)
    self.neopixel.fill(0xFFFF00)

    self.midi_in = smolmidi.MidiIn(usb_midi.ports[0])

    self._poll = select.poll()
    self._poll.register(usb_midi.ports[0], select.POLLIN)


  def process_midi(self, handler: callable) -> bool:
    for _ in self._poll.ipoll(0):
      msg_in = self.midi_in.receive()
      if msg_in is None: continue

      if msg_in.type == smolmidi.SYSEX:
        sysex_payload, truncated = self.midi_in.receive_sysex(128)
        handler("".join([chr(b) for b in sysex_payload]))


  def load_json_settings(self) -> dict:
    json_str = []
    try:
      for byte_idx in range(len(microcontroller.nvm)):
        b = microcontroller.nvm[byte_idx]
        if b == 0 or b == 0xff:
          json_data = "".join(json_str)
          print("Loaded settings: ", json_data)
          return json.loads(json_data)
        else:
          json_str.append(chr(b))
    except Exception as e:
      print("Error loading settings: %s" % e)
      return {}


  def save_json_settings(self, val: dict):
    try:
      serialized_bytes = json.dumps(val).encode('utf-8')
      print("Saving: ", serialized_bytes)
      all_bytes = serialized_bytes + '\x00'
      microcontroller.nvm[0:len(all_bytes)] = all_bytes
    except Exception as e:
      print("ERROR SAVING SETTINGS: %s!" % e)


  def display_text(self, sx: int, sy: int, msg: str) -> None:
    font = self.font
    _, height, _, dy = font.get_bounding_box()
    font.load_glyphs(msg)

    if isinstance(self, MoonClock):
      disp = self.display
    else:
      disp = self

    for y in range(height):
        x = sx
        for c in msg:
            npix = 0

            glyph = font.get_glyph(ord(c))
            if not glyph:
                continue
            glyph_y = y + (glyph.height - (height + dy)) + glyph.dy
            if 0 <= glyph_y < glyph.height:
                for i in range(glyph.width):
                    value = glyph.bitmap[i, glyph_y]
                    disp.pixel(x, sy + y, value)
                    x += 1
                    npix += 1
            else:
                # empty section for this glyph
                for i in range(glyph.width):
                    disp.pixel(x, sy + y, 0)
                    x += 1
                    npix += 1
            for _ in range(glyph.shift_x - npix):
                disp.pixel(x, sy + y, 0)
                x += 1
