from tcv_astro.sidereal import sidereal_time_at_greenwhich
from tcv_astro.angles import acos_degrees, asin_degrees, sin_degrees, cos_degrees, dms_to_degrees
from tcv_astro.sun import solar_coordinates, SolarCoordinates
from tcv_astro.moon import lunar_coordinates, LunarCoordinates
from tcv_astro.julian import TT_UT_DIFFERENCE_SECONDS_2017

try:
    from enum import IntEnum
except ImportError:
    IntEnum = object

try:
    from typing import Optional
except ImportError:
    Optional = 'Optional'

class ObjectPositions:
    def __init__(self, prev_day_ra_apparent: float, prev_day_dec_apparent: float, cur_day_ra_apparent: float, cur_day_dec_apparent: float, next_day_ra_apparent: float, next_day_dec_apparent: float, ho_degrees: float=-0.5667):
        self.prev_day_ra_apparent: float = prev_day_ra_apparent
        self.prev_day_dec_apparent: float = prev_day_dec_apparent
        self.cur_day_ra_apparent: float = cur_day_ra_apparent
        self.cur_day_dec_apparent: float = cur_day_dec_apparent
        self.next_day_ra_apparent: float = next_day_ra_apparent
        self.next_day_dec_apparent: float = next_day_dec_apparent
        self.ho_degrees: float = ho_degrees


class RiseTransitSetTimes:
    def __init__(self, rise_time_hours: float, transit_time_hours: float, set_time_hours: float, next_set_time_hours: Optional[float]):
        self.rise_time_hours: float = rise_time_hours
        self.transit_time_hours: float = transit_time_hours
        self.set_time_hours: float = set_time_hours
        self.next_set_time_hours: float = next_set_time_hours


def get_moon_positions_for_event(jd: float) -> ObjectPositions:
    prev_day: LunarCoordinates = lunar_coordinates(jd - 1.0)
    cur_day: LunarCoordinates = lunar_coordinates(jd)
    next_day: LunarCoordinates = lunar_coordinates(jd + 1.0)

    return ObjectPositions(
        prev_day_ra_apparent = prev_day.ra_apparent,
        prev_day_dec_apparent = prev_day.dec_apparent,
        cur_day_ra_apparent = cur_day.ra_apparent,
        cur_day_dec_apparent = cur_day.dec_apparent,
        next_day_ra_apparent = next_day.ra_apparent,
        next_day_dec_apparent = next_day.dec_apparent,
        ho_degrees = (0.7275 * cur_day.horizontal_parallax_degrees) - dms_to_degrees(minutes=34)
    )


def get_sun_positions_for_event(jd: float) -> ObjectPositions:
    prev_day: SolarCoordinates = solar_coordinates(jd - 1.0)
    cur_day:  SolarCoordinates = solar_coordinates(jd)
    next_day: SolarCoordinates = solar_coordinates(jd + 1.0)

    return ObjectPositions(
        prev_day_ra_apparent = prev_day.ra_apparent,
        prev_day_dec_apparent = prev_day.dec_apparent,
        cur_day_ra_apparent = cur_day.ra_apparent,
        cur_day_dec_apparent = cur_day.dec_apparent,
        next_day_ra_apparent = next_day.ra_apparent,
        next_day_dec_apparent = next_day.dec_apparent,
        ho_degrees = -0.8333
    )


def interpolate(y1: float, y2: float, y3: float, n: float) -> float:
    """Interpolate a normalized interval `n` around y2, with y1 and y3 being same tabular distance.

    Reference:
        Meeus, J. (1991). Astronomical algorithms (1st ed.). Willmann-Bell". Equation 3.3.
    """
    a = y2 - y1
    b = y3 - y2
    c = b - a
    #assert n >= -1.0 and n <= 1.0

    return y2 + ((n / 2.0) * (a + b + (n * c)))


def get_event_time(jd: float, object_positions: ObjectPositions, obs_lat_degrees: float, obs_lon_degrees: float, delta_t: float=TT_UT_DIFFERENCE_SECONDS_2017) -> Optional[RiseTransitSetTimes]:
    alpha1, delta1 = object_positions.prev_day_ra_apparent, object_positions.prev_day_dec_apparent
    alpha2, delta2 = object_positions.cur_day_ra_apparent, object_positions.cur_day_dec_apparent
    alpha3, delta3 = object_positions.next_day_ra_apparent, object_positions.next_day_dec_apparent
    ho_degrees = object_positions.ho_degrees

    theta0 = sidereal_time_at_greenwhich(jd)
    Ho_arg = ((sin_degrees(ho_degrees) - (sin_degrees(obs_lat_degrees) * sin_degrees(delta2))) / (cos_degrees(obs_lat_degrees) * cos_degrees(delta2)))

    # No rise/set times (always or never visible)
    if abs(Ho_arg) > 1.0:
        return None

    Ho = acos_degrees(Ho_arg)
    assert Ho >= 0.0 and Ho <= 180.0

    # Transit
    mo = ((alpha2 + obs_lon_degrees - theta0) / 360.0)

    # Rising
    m1 = (mo - (Ho / 360.0))

    # Setting
    m2 = (mo + (Ho / 360.0))

    # print(f'{m1:.3f} {mo:.3f} {m2:.13f}')

    mo = mo % 1.0
    m1 = m1 % 1.0
    m2 = m2 % 1.0

    # compute_next_set = False
    # if m2 >= 1.0:
    #     compute_next_set = True
    #     m2 -= 1.0

    def get_interpolated_time(initial_m: float, is_transit: bool) -> float:
        theta = (theta0 + (360.985647 * initial_m)) % 360.0

        n = initial_m + (delta_t / 86400.0)
        # Interpolated apparent right ascension
        alpha = interpolate(alpha1, alpha2, alpha3, n)
        # Interpolated apparent declination
        delta = interpolate(delta1, delta2, delta3, n)

        # Local hour angle
        H = (theta - obs_lon_degrees - alpha)

        # Body's local altitude per Meeus eq. 12.6
        h = asin_degrees(((sin_degrees(obs_lat_degrees) * sin_degrees(delta)) + (cos_degrees(obs_lat_degrees) * cos_degrees(delta) * cos_degrees(H))))

        if is_transit:
            delta_m = -H / 360.0
        else:
            delta_m = (h - ho_degrees) / (360.0 * cos_degrees(delta) * cos_degrees(obs_lat_degrees) * sin_degrees(H))

        m_corrected = initial_m + delta_m
        hours = (m_corrected * 24.0) % 24.0
        return hours

    rising_time = get_interpolated_time(m1, is_transit=False)
    transit_time = get_interpolated_time(mo, is_transit=True)
    setting_time = get_interpolated_time(m2, is_transit=False)

    compute_next_set = False
    next_setting_time = None
    if compute_next_set:
        next_setting_time = get_interpolated_time(m2 + 1.0, is_transit=False)

    return RiseTransitSetTimes(rise_time_hours=rising_time, transit_time_hours=transit_time, set_time_hours=setting_time, next_set_time_hours=next_setting_time)
