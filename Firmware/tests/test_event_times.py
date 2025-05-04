import unittest
from datetime import datetime, timedelta
from dataclasses import dataclass

from tcv_astro.event_times import get_event_time, RiseTransitSetTimes, ObjectPositions, get_moon_positions_for_event, get_sun_positions_for_event
from tcv_astro.julian import date_to_julian_day
from tcv_astro.angles import hours_to_hms


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


def get_dst_hours_delta(local_datetime_before_dst: datetime, strategy: str="none") -> timedelta:
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


@dataclass
class RiseSetEvent:
    moment: datetime
    is_rise: bool

class TestEventTimes(unittest.TestCase):
    def assertMomentWithinDelta(self, expected_moment: datetime, actual_moment, accuracy_delta: timedelta):
        self.assertGreaterEqual(actual_moment, expected_moment - accuracy_delta)
        self.assertLessEqual(actual_moment, expected_moment + accuracy_delta)

    def test_event_times_venus_in_boston(self):
        # Meeus example 14.a: event times for Venus on 1988 March 20 in boston

        object_positions = ObjectPositions(
            prev_day_ra_apparent=40.68021,
            cur_day_ra_apparent=41.73129,
            next_day_ra_apparent=42.78204,
            prev_day_dec_apparent=18.04761,
            cur_day_dec_apparent=18.44092,
            next_day_dec_apparent=18.82742
        )

        obs_lat = 42.3333
        obs_lon = 71.0833
        event_times: RiseTransitSetTimes = get_event_time(jd=date_to_julian_day(1988, 3, 20), object_positions=object_positions, obs_lat_degrees=obs_lat, obs_lon_degrees=obs_lon, delta_t=56.0)
        self.assertAlmostEqual(event_times.rise_time_hours / 24.0, 0.51766, places=5)
        self.assertAlmostEqual(event_times.transit_time_hours / 24.0, 0.81980, places=5)
        self.assertAlmostEqual(event_times.set_time_hours / 24.0, 0.12130, places=5)

        # print("RISE_TODAY:", hours_to_hms(event_times.rise_time_hours))
        # print("TRANSIT_TODAY:", hours_to_hms(event_times.transit_time_hours))
        # print("SET_TODAY:", hours_to_hms(event_times.set_time_hours))
        # print("SET_TOMORROW:", hours_to_hms(event_times.next_set_time_hours))

    def test_event_times_sun_moon_in_kitchener(self):
        # Based on US Naval Observatory data, obtained on April 6, 2025
        # https://aa.usno.navy.mil/calculated/rstt/oneday?date=2025-03-26&lat=43.4516&lon=-80.4925&label=Kitchener&tz=5&tz_sign=-1&tz_label=false&dst=true&submit=Get+Data
        #
        # NOTE: Only testing for a date where local moon rise/set both fall in same civil day in UTC as the handling
        #       of roll-over needs to be done by application logic to match with USNO tables (which show rise/set same
        #       Julian Day number only).

        # Sunday, 2025-March-26
        # Zone: 4.0 hours West of Greenwich
        #
        # Sun
        #   Begin Civil Twilight 06:45
        #   Rise 07:14
        #   Upper Transit 13:27
        #   Set 19:42
        #   End Civil Twilight 20:11
        # Moon
        #   Rise 06:01
        #   Upper Transit 11:07
        #   Set 16:24

        obs_lat = 43.4516
        obs_lon = 80.4925

        ONE_MINUTE = timedelta(minutes=1)

        timezone_delta = timedelta(hours=-5)

        YEAR = 2025
        MONTH = 3
        DAY = 26

        jd = date_to_julian_day(YEAR, MONTH, DAY)

        # ====== SUN ======
        sun_positions = get_sun_positions_for_event(jd)
        sun_event_times: RiseTransitSetTimes = get_event_time(jd, object_positions=sun_positions, obs_lat_degrees=obs_lat, obs_lon_degrees=obs_lon)

        sun_rise_hms = hours_to_hms(sun_event_times.rise_time_hours)
        sun_set_hms = hours_to_hms(sun_event_times.set_time_hours)

        sun_local_rise_hms = datetime(YEAR, MONTH, DAY, sun_rise_hms.hours, sun_rise_hms.minutes, int(sun_rise_hms.seconds)) + timezone_delta
        sun_local_rise_hms += get_dst_hours_delta(sun_local_rise_hms, strategy="canada")
        sun_local_set_hms = datetime(YEAR, MONTH, DAY, sun_set_hms.hours, sun_set_hms.minutes, int(sun_set_hms.seconds)) + timezone_delta
        sun_local_set_hms += get_dst_hours_delta(sun_local_set_hms, strategy="canada")

        SUN_ACTUAL_RISE = datetime(YEAR, MONTH, DAY, hour=7, minute=14, second=0)
        SUN_ACTUAL_SET = datetime(YEAR, MONTH, DAY, hour=19, minute=42, second=0)

        self.assertMomentWithinDelta(expected_moment=SUN_ACTUAL_RISE, actual_moment=sun_local_rise_hms, accuracy_delta=ONE_MINUTE)
        self.assertMomentWithinDelta(expected_moment=SUN_ACTUAL_SET, actual_moment=sun_local_set_hms, accuracy_delta=ONE_MINUTE)

        # ====== MOON ======
        moon_positions = get_moon_positions_for_event(jd)
        moon_event_times: RiseTransitSetTimes = get_event_time(jd, object_positions=moon_positions, obs_lat_degrees=obs_lat, obs_lon_degrees=obs_lon)

        moon_rise_hms = hours_to_hms(moon_event_times.rise_time_hours)
        moon_set_hms = hours_to_hms(moon_event_times.set_time_hours)

        moon_local_rise_hms = datetime(YEAR, MONTH, DAY, moon_rise_hms.hours, moon_rise_hms.minutes, int(moon_rise_hms.seconds)) + timezone_delta
        moon_local_rise_hms += get_dst_hours_delta(moon_local_rise_hms, strategy="canada")
        moon_local_set_hms = datetime(YEAR, MONTH, DAY, moon_set_hms.hours, moon_set_hms.minutes, int(moon_set_hms.seconds)) + timezone_delta
        moon_local_set_hms += get_dst_hours_delta(moon_local_set_hms, strategy="canada")

        MOON_ACTUAL_RISE = datetime(YEAR, MONTH, DAY, hour=6, minute=1, second=0)
        MOON_ACTUAL_SET = datetime(YEAR, MONTH, DAY, hour=16, minute=24, second=0)

        self.assertMomentWithinDelta(expected_moment=MOON_ACTUAL_RISE, actual_moment=moon_local_rise_hms, accuracy_delta=ONE_MINUTE)
        self.assertMomentWithinDelta(expected_moment=MOON_ACTUAL_SET, actual_moment=moon_local_set_hms, accuracy_delta=ONE_MINUTE)

    def test_event_times_moon_in_kitchener(self):
        # Moon rise/transit/set in Kitchener on 2025, Mar 31

        obs_lat = 43.4516
        obs_lon = 80.4925

        events = []
        YEAR = 2025
        MONTH = 4
        for day in range(1,30):
            jd = date_to_julian_day(YEAR, MONTH, day)

            object_positions = get_moon_positions_for_event(jd)
            event_times: RiseTransitSetTimes = get_event_time(jd, object_positions=object_positions, obs_lat_degrees=obs_lat, obs_lon_degrees=obs_lon)

            def almanac_time_str(hours: float) -> str:
                hms = hours_to_hms(hours)
                return f"{hms.hours:02d}:{hms.minutes:02d}"

            rise_hms = hours_to_hms(event_times.rise_time_hours)
            set_hms = hours_to_hms(event_times.set_time_hours)

            timezone_delta = timedelta(hours=-5)

            local_rise_hms = datetime(YEAR, MONTH, day, rise_hms.hours, rise_hms.minutes, int(rise_hms.seconds)) + timezone_delta
            local_rise_hms += get_dst_hours_delta(local_rise_hms, strategy="canada")
            local_set_hms = datetime(YEAR, MONTH, day, set_hms.hours, set_hms.minutes, int(set_hms.seconds)) + timezone_delta
            local_set_hms += get_dst_hours_delta(local_set_hms, strategy="canada")

            before_str = "diff" if local_set_hms.day != local_rise_hms.day else "same"

            print(f"2025 Mar {day:02d}    {almanac_time_str(event_times.rise_time_hours)}    {almanac_time_str(event_times.transit_time_hours)}    {almanac_time_str(event_times.set_time_hours)} -> {local_rise_hms} | {local_set_hms} {before_str}")

            events.append(RiseSetEvent(local_rise_hms, is_rise=True))
            events.append(RiseSetEvent(local_set_hms, is_rise=False))

        events.sort(key=lambda x: x.moment)
        for idx, event in enumerate(events):
            if idx >= 1:
                diff = events[idx].moment - events[idx-1].moment
            else:
                diff = timedelta(seconds=0.0)

            print(f'{"RISE:" if event.is_rise else "SET: "} {event.moment} {diff.seconds / 3600.0:.3f}')


        # print("RISE_TODAY:", hours_to_hms(event_times_today.rise_time_hours))
        # print("TRANSIT_TODAY:", hours_to_hms(event_times_today.transit_time_hours))
        # print("SET_TODAY:", hours_to_hms(event_times_today.set_time_hours))
        # print(event_times_today.next_set_time_hours)

        # jd = jd + 1.0
        # object_positions = get_moon_positions_for_event(jd)
        # event_times_tomorrow: RiseTransitSetTimes = get_event_time(jd, object_positions=object_positions, obs_lat_degrees=obs_lat, obs_lon_degrees=obs_lon)

        # print("RISE_TOMORROW:", hours_to_hms(event_times_tomorrow.rise_time_hours))
        # print("TRANSIT_TOMORROW:", hours_to_hms(event_times_tomorrow.transit_time_hours))
        # print("SET_TOMORROW:", hours_to_hms(event_times_tomorrow.set_time_hours))
        # print("NEXT_SET_TODAY:", hours_to_hms(event_times_tomorrow.next_set_time_hours))
        # """
        # 2025 Feb 06 (Thu)        16:36  53                         07:48 305
        # 2025 Feb 07 (Fri)        17:23  50        00:44 73S        09:02 310
        # 2025 Feb 08 (Sat)        18:21  49        01:44 75S        10:08 311
        # 2025 Feb 09 (Sun)        19:28  51        02:44 75S        11:02 310
        # 2025 Feb 10 (Mon)        20:40  56        03:42 72S        11:44 306
        # """

if __name__ == '__main__':
    unittest.main()