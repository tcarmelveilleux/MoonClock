import board
import digitalio
import storage
import time
import usb_midi

usb_midi.set_names(in_jack_name="MoonClockMidiIn", out_jack_name="MoonClockMidiOut")
usb_midi.enable()
# button_pins = (board.GP15, board.GP14)

# switch_pressed = None
# for button_pin in button_pins:
#   switch = digitalio.DigitalInOut(button_pin)
#   switch.direction = digitalio.Direction.INPUT
#   switch.pull = digitalio.Pull.UP
#   time.sleep(0.01)

#   if switch.value == False:
#     switch_pressed = switch

# # Read-only for firmware on buttons pressed, so that program can written.
# read_only_for_program = switch_pressed is not None
# storage.remount("/", read_only_for_program)

# # Wait for switch to be up
# time.sleep(0.1)
# while switch_pressed.value == False :
#   time.sleep(0.01)
# time.sleep(0.1)

print("Booting...")

