import argparse
import datetime
import mido
import re

from dataclasses import dataclass, field

@dataclass
class ToolOptions:
    verbose_logs: bool = False
    midi_out_port_name: str = None


class MoonClockCommandSender:
    def __init__(self, midi_sender: callable):
        self.midi_sender = midi_sender

    def send_set_utc_time(self, hours: int, minutes: int, seconds: int):
        self.midi_sender(f'UTC,{hours},{minutes},{seconds}')

    def send_set_date(self, year: int, month: int, day: int, dow: int):
        self.midi_sender(f'DATE,{year},{month},{day},{dow}')

    def send_set_utc_offset(self, utc_offset_seconds: int):
        self.midi_sender(f'OFFSET,{utc_offset_seconds}')

    def send_set_dst(self, strategy_name: str):
        self.midi_sender(f'DST,{strategy_name}')

    def send_cal(self, channel_idx: int, value: int):
        self.midi_sender(f'CAL,{channel_idx},{value}')

    def send_stop_cal(self):
        self.midi_sender(f'STOPCAL')

class ToolContext:
    def __init__(self, options: ToolOptions):
        self.midi_out_port = None
        self.options = options
        self.command_sender = None

    def set_midi_port_from_name(self, midi_out_port_name: str) -> None:
        self.midi_out_port = mido.open_output(midi_out_port_name)
        self.command_sender = MoonClockCommandSender(self.send_midi_sysex_string)

    def send_midi_sysex_string(self, command: str) -> None:
        # All commands are just ASCII 0-127 commands sent as a block to the overall sysex with no manufacturer ID.
        # This is because the Moon Clock is alone by USB midi, so we cannot clash.
        self.midi_out_port.send(mido.Message('sysex', data=[ord(c) for c in command]))


class Action:
    def execute(self, context: ToolContext):
        pass


class SetUtcTimeAction:
    def __init__(self, hours:int, minutes:int, seconds: int):
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds

    def execute(self, context: ToolContext):
        print(f"ACTION: Setting time to {self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}")
        context.command_sender.send_set_utc_time(self.hours, self.minutes, self.seconds)

    @staticmethod
    def build(arg: str) -> Action:
        TEST_VALUES = """
            31:22:33
            1:22:34
            01:22:34
            01:22:60
            11:22
            11:22:33
            11:22:3
            11:22:03
            23:59:59
        """
        time_regex = re.compile(r'^((?P<hours>20|21|23|1[0-9]|0[0-9]|[0-9])(:(?P<minutes>[0-5][0-9])(:(?P<seconds>([0-5][0-9])?))?)|now)$')
        match = time_regex.match(arg)
        if not match:
            raise ValueError('Wrong UTC time format')

        if arg == 'now':
            now = datetime.datetime.now(tz=datetime.UTC)
            return SetUtcTimeAction(hours=now.hour, minutes=now.minute, seconds=now.second)

        hours_str = match.group('hours')
        minutes_str = match.group('minutes')
        seconds_str = match.group('seconds')

        hours = int(hours_str)
        minutes = 0 if not minutes_str else int(minutes_str)
        seconds = 0 if not seconds_str else int(seconds_str)
        return SetUtcTimeAction(hours, minutes, seconds)


class SetUtcOffsetAction:
    def __init__(self, seconds_offset: int):
        self.seconds_offset = seconds_offset

    def execute(self, context: ToolContext):
        print(f'ACTION: Setting UTC offset to {self.seconds_offset} seconds: ({self.seconds_offset / 3600.0:.3f} hours)')
        context.command_sender.send_set_utc_offset(self.seconds_offset)

    @staticmethod
    def build(arg: str) -> Action:
        TEST_VALUES = """
            -1
            -01
            -02:00
            -02:30
            +02:30
            +2:30
            +2
        """
        time_regex = re.compile(r'^(?P<hours>[-+](20|21|23|1[0-9]|0[0-9]|[0-9]))(:(?P<minutes>[0-5][0-9]))?$')

        match = time_regex.match(arg)
        if not match:
            raise ValueError('Wrong timezone offset')

        hours_str = match.group('hours')
        minutes_str = match.group('minutes')

        hours = int(hours_str)
        minutes = 0 if not minutes_str else int(minutes_str)
        seconds_offset = (hours * 3600) + (minutes * 60)

        return SetUtcOffsetAction(seconds_offset)

class SetDateAction:
    def __init__(self, year:int, month:int, day: int, dow: int):
        self.year = year
        self.month = month
        self.day = day
        self.dow = dow

    def execute(self, context: ToolContext):
        DAY_NAMES = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
        }
        print(f"ACTION: Setting date to {self.year:04d}/{self.month:02d}/{self.day:02d} ({DAY_NAMES[self.dow]})")
        context.command_sender.send_set_date(self.year, self.month, self.day, self.dow)

    @staticmethod
    def build(arg: str) -> Action:
        TEST_VALUES = """
            now
            2025/01/2
            2025/1/22
            2025/01/22
            2025/01/1
            2025/01/11
            2025/01/31
            2025/01/32
            2025/01/29
            2025/01/20
            2025/01/19
            2025/01/10
            2025/01/09
            2025/01/9
            2025/01/1
            2025/1/1
            2025/01/0
            2025/01/00
            2025/01/00
            2025/0/11
            2025/13/11
            2025/01/0
            2025/01/0
        """
        time_regex = re.compile(r'^((?P<year>20[0-9]{2})/(?P<month>10|11|12|0?[1-9])/(?P<day>30|31|([12][0-9])|(0?[1-9]))|now)$')
        match = time_regex.match(arg)
        if not match:
            raise ValueError('Wrong date format (expect YYYY/MM/DD or "now")')

        if arg == 'now':
            now = datetime.datetime.now(tz=datetime.UTC)
            return SetDateAction(now.year, now.month, now.day, now.weekday())

        year_str = match.group('year')
        month_str = match.group('month')
        day_str = match.group('day')

        year = int(year_str)
        month = 0 if not month_str else int(month_str)
        day = 0 if not day_str else int(day_str)
        dow = datetime.date(year, month, day).weekday()

        return SetDateAction(year, month, day, dow)


class SetDstAction:
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name

    def execute(self, context: ToolContext):
        print(f'ACTION: Setting DST strategy to "{self.strategy_name}"')
        context.command_sender.send_set_dst(self.strategy_name)

    @staticmethod
    def build(arg: str) -> Action:
        strategy = arg.lower()
        if strategy not in ['none', 'canada']:
            raise ValueError('Unknown DST strategy: "{arg}"')

        return SetDstAction(strategy)

class CalibrateAction:
    def __init__(self, channel_idx: int, value: int):
        self.channel_idx = channel_idx
        self.value = value

    def execute(self, context: ToolContext):
        print(f'ACTION: Calibrate channel {self.channel_idx} to {self.value}')
        context.command_sender.send_cal(self.channel_idx, self.value)

    @staticmethod
    def build(arg: str) -> Action:
        try:
            cal_regex = re.compile(r'^(?P<channel>\d+):(?P<value>\d+)$')
            match = cal_regex.match(arg)
            if not match:
                raise ValueError('Wrong calibration argument format')

            channel = int(match.group('channel'))
            value = int(match.group('value'))

            if not (0 <= channel <= 1):
                raise ValueError("Channel must be in [0, 1]")
            if not (0 <= value <= 4095):
                raise ValueError("Value must be in [0, 4095]")
        except Exception as e:
            print(e)
            raise

        return CalibrateAction(channel, value)

class StopCalibrateAction:
    def __init__(self):
        pass

    def execute(self, context: ToolContext):
        print(f'ACTION: Stop calibration')
        context.command_sender.send_stop_cal()

@dataclass
class CommandLine:
    options: ToolOptions
    actions: list[Action] = field(default_factory=list)


def is_likely_usable_port(name: str) -> bool:
    if "CircuitPython" in name:
        return True
    elif "MoonClock" in name:
        return True

    return False


def get_usable_midi_outs() -> list[str]:
    return [name for name in mido.get_output_names() if is_likely_usable_port(name)]


def parse_command_line() -> CommandLine:
    options = ToolOptions()
    actions: list[Action] = []

    usable_midi_outs = get_usable_midi_outs()
    if len(usable_midi_outs) == 0:
        usable_midi_outs = [None]

    default_midi_out = usable_midi_outs[0]

    parser = argparse.ArgumentParser()
    parser.add_argument("--midi-out", action="store", default=default_midi_out, type=str, help=f'Select name of MIDI port to send commands (default: "{default_midi_out}")')
    parser.add_argument("--verbose", help="increase output verbosity",
                        action="store_true")

    parser.add_argument("--set-utc-time", action="store", metavar="HH:MM:SS.sss", type=SetUtcTimeAction.build, help='Set UTC time from HH:MM:SS.sss or "now"')
    parser.add_argument("--set-utc-offset", action="store", metavar="OFFSET_HOURS", type=SetUtcOffsetAction.build, help='Set timezone offset from UTC to OFFSET_HOURS')
    parser.add_argument("--set-date", action="store", metavar="YYYY/MM/DD", type=SetDateAction.build, help='Set date from YYYY/MM/DD or "now"')
    parser.add_argument("--set-dst", action="store", type=SetDstAction.build, help='Set DST computations to given strategy ("none", "canada").')
    parser.add_argument("--cal", action="append", type=CalibrateAction.build, metavar="N:X", help='Set channel N to value X')
    parser.add_argument("--stop-cal", action="store_true", help='Stop calibration mode, return to normal')

    args = parser.parse_args()

    if args.verbose:
        options.verbose_logs = True

    if args.set_utc_time:
        actions.append(args.set_utc_time)
    if args.set_utc_offset:
        actions.append(args.set_utc_offset)
    if args.set_date:
        actions.append(args.set_date)
    if args.set_dst:
        actions.append(args.set_dst)
    if args.cal:
        for cal_action in args.cal:
            actions.append(cal_action)
    if args.stop_cal:
        actions.append(StopCalibrateAction())

    options.midi_out_port_name = args.midi_out

    return CommandLine(options, actions)


def main():
    cmd_line = parse_command_line()

    if not cmd_line.actions:
        print("Nothing do do!")
        return


    # TODO: Build context
    context = ToolContext(cmd_line.options)
    context.set_midi_port_from_name(cmd_line.options.midi_out_port_name)

    print("Executing actions:")
    for action in cmd_line.actions:
        action.execute(context)


if __name__ == "__main__":
    main()
