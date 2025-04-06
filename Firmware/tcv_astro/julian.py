import math
try:
    from ucollections import namedtuple
except ImportError:
    from collections import namedtuple

# Difference between Dynamical Time and UTC From RASC Observer's Handbook, 2025
TT_UT_DIFFERENCE_SECONDS_2017 = 69.184

EPOCH_J2000 = 2451545.0

FractionalDate = namedtuple("FractionalDate", ("year", "month", "day"))

def time_to_fraction(hours: int, minutes: int, seconds: float) -> float:
    """Converts HH:MM:SS.ssss to fractional days. Only supports returning values [0.0, 1.0["""
    total_day_hours = (seconds / 3600.0) + (minutes / 60.0) + hours
    fractional_days = total_day_hours / 24.0
    if (fractional_days < 0.0) or (fractional_days >= 1.0):
        raise ValueError("Output is out of range [0.0, 1.0[]")
    return fractional_days


def is_gregorian_calendar(year: int, month: int, day: float) -> bool:
    """Returns True if the date is at or after the transition to Gregorian.

    CAVEAT: This method assumes the entire history before the transition was using the Julian
    calendar. For our purposes (this package), this is OK.

    Raises ValueError on invalid (non-existent day).
    """
    # The transition was the day after 1582 October 4.
    if year < 1582:
        return False
    if year > 1582:
        return True

    # Year 1582, transition after Oct 4
    if month < 10:
        return False

    if month == 10:
        if day < 5.0:
            return False
        # First Gregorian day is 1582 October 15. Days between October 5 and 14 inclusive do not exist.
        if not (day >= 15.0):
            raise ValueError("October of 1582 does not include day %d due to Gregorian transition" % day)

    return True


def date_to_julian_day(year: int, month: int, day: float) -> float:
    """Convert a civil date with fractional day to julian day number.

    This takes into account the transition from Julian to Gregorian after 1582 October 4.

    Algorithm is from:
     - Meeus, J. (1991). Astronomical algorithms (1st ed.). Willmann-Bell. Chap 7.
    """

    # January/February are treated as the 13th and 14th month for the algorithm below.
    if month in [1, 2]:
        year = year - 1
        month = month + 12

    a: int = int(year / 100)

    if is_gregorian_calendar(year, month, day):
        b: int = 2 - a + int(a / 4)
    else:
        b: int = 0

    jd: float = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5

    return jd


def julian_day_to_date(jd: float) -> FractionalDate:
    """Convert a julian day number to civil date with fractional day.

    This takes into account the transition from Julian to Gregorian after 1582 October 4.

    Algorithm is from:
     - Meeus, J. (1991). Astronomical algorithms (1st ed.). Willmann-Bell. Chap 7.
    """
    if jd < 0.0:
        raise ValueError("Only positive Julian days supported")

    jd += 0.5
    fractional_part, integer_part = math.modf(jd)
    z: int = int(integer_part)
    f: float = fractional_part

    if z < 2299161:
        a: int = z
    else:
        alpha: int = int((z - 1867216.25) / 36524.25)
        a: int = z + 1 + alpha - int(alpha / 4)

    b: int = a + 1524
    c: int = int((b - 122.1) / 365.25)
    d: int = int(365.25 * c)
    e: int = int((b - d) / 30.6001)

    fractional_day: float = b - d - int(30.6001 * e) + f
    if e < 14:
        month: int = e - 1
    else:
        assert e in [14, 15]
        month: int = e - 13

    if month > 2:
        year: int = c - 4716
    else:
        assert month in [1, 2]
        year: int = c - 4715

    return FractionalDate(year, month, fractional_day)


def julian_day_to_julian_centuries(jd: float, epoch: float=EPOCH_J2000) -> float:
    return (jd - epoch) / 36525.0

