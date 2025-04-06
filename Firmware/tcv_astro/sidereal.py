from tcv_astro.polynomial import poly_eval
from tcv_astro.ecliptic import nutations_and_obliquity
from tcv_astro.julian import julian_day_to_julian_centuries
from tcv_astro.angles import cos_degrees


def sidereal_time_at_greenwhich(jd: float) -> float:
    """Get sidereal time at Greenwhich. Assumes 0h UT.

     Reference:
        Meeus, J. (1991). Astronomical algorithms (1st ed.). Willmann-Bell". Chapter 11.

    """
    T = julian_day_to_julian_centuries(jd)

    # Mean sidereal time
    theta_o = poly_eval(T, [100.46061837, 36000.770053608, 0.000387933, -1.0 / 38710000.0]) % 360.0

    nutations = nutations_and_obliquity(jd)
    # TODO: use more accurate nutations algorithm
    eq_equinox = nutations.nutation_longitude / 15.0 * cos_degrees(nutations.true_obliquity)

    # Apparent sidereal time
    theta_o_app = theta_o + eq_equinox

    # print(locals())

    return theta_o_app