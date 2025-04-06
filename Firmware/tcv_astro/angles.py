import math

def deg_to_rad(degrees: float) -> float:
    return (degrees / 180.0) * math.pi

def rad_to_deg(radians: float) -> float:
    return (radians / math.pi) * 180.0

def sin_degrees(degrees: float) -> float:
    return math.sin(deg_to_rad(degrees))

def cos_degrees(degrees: float) -> float:
    return math.cos(deg_to_rad(degrees))

def tan_degrees(degrees: float) -> float:
    return math.tan(deg_to_rad(degrees))

def asin_degrees(sine: float) -> float:
    return rad_to_deg(math.asin(sine))

def acos_degrees(cosine: float) -> float:
    return rad_to_deg(math.acos(cosine))

def atan2_degrees(num: float, denum: float) -> float:
    return rad_to_deg(math.atan2(num, denum))

def signum(val: float) -> float:
    return -1.0 if val < 0.0 else 1.0

def dms_to_degrees(degrees: float=0.0, minutes: float=0.0, seconds: float=0.0) -> float:
    """Convert degrees/minutes/seconds to decimal degrees.

    Handles negatives properly.
    """
    assert (minutes >= 0.0 and seconds >= 0.0) or (degrees == 0.0 and minutes == 0.0)
    return signum(degrees) * (abs(degrees) + (minutes / 60.0) + (seconds / 3600.0))

class HoursMinutesSeconds:
    def __init__(self, hours: int, minutes: int, seconds: float):
        assert hours >= 0 and hours < 24
        assert minutes >= 0 and minutes < 60
        assert seconds >= 0.0 and seconds < 60.0
        self.hours: int = hours
        self.minutes: int = minutes
        self.seconds: int = seconds

    def __repr__(self):
        sec_frac, sec_int = math.modf(self.seconds)
        return "%dh%dm%ds.%0d" % (self.hours, self.minutes, sec_int, int(sec_frac * 1000.0))


def hours_to_hms(hours: float) -> HoursMinutesSeconds:
    hours_frac, hours_full = math.modf(hours)
    minutes = hours_frac * 60.0
    minutes_frac, minutes_full = math.modf(minutes)
    seconds = minutes_frac * 60.0
    return HoursMinutesSeconds(int(hours_full), int(minutes_full), seconds)


def degrees_to_hms(degrees: float) -> HoursMinutesSeconds:
    hours = ((degrees % 360.0) / 360.0) * 24.0
    return hours_to_hms(hours)


class DegreesMinutesSeconds:
    def __init__(self, degrees: int, minutes: int, seconds: float):
        assert degrees >= -180 and degrees < 360
        assert minutes >= 0 and minutes < 60
        assert seconds >= 0.0 and seconds < 60.0
        self.degrees: int = degrees
        self.minutes: int = minutes
        self.seconds: int = seconds

    def __repr__(self):
        sec_frac, sec_int = math.modf(self.seconds)
        return '%d°%d\'%d".%0d' % (self.degrees, self.minutes, sec_int, int(sec_frac * 1000.0))

def degrees_to_dms(degrees: float) -> DegreesMinutesSeconds:
    degrees_sign = signum(degrees)
    degrees_frac, degrees_full = math.modf(math.fabs(degrees))
    minutes = degrees_frac * 60.0
    minutes_frac, minutes_full = math.modf(minutes)
    seconds = minutes_frac * 60.0

    return DegreesMinutesSeconds(int(degrees_sign) * int(degrees_full), int(minutes_full), seconds)

def ecliptic_to_equatorial(in_lambda_degrees: float, beta_degrees: float, epsilon_degrees: float) -> tuple[float, float]:
    alpha = atan2_degrees(((sin_degrees(in_lambda_degrees) * cos_degrees(epsilon_degrees)) - (tan_degrees(beta_degrees) * sin_degrees(epsilon_degrees))), cos_degrees(in_lambda_degrees))
    delta = asin_degrees((sin_degrees(beta_degrees) * cos_degrees(epsilon_degrees)) + (cos_degrees(beta_degrees) * sin_degrees(epsilon_degrees) * sin_degrees(in_lambda_degrees)))

    return (alpha, delta)
