from tcv_astro import julian
from tcv_astro.polynomial import poly_eval
from tcv_astro.angles import sin_degrees, cos_degrees, asin_degrees, atan2_degrees, degrees_to_hms, degrees_to_dms
from tcv_astro.ecliptic import nutation_simplified_meeus


class SolarCoordinates:
    def __init__(self, true_lon: float, apparent_lon: float, apparent_lat: float, radius_vector: float, ra: float, dec: float, ra_apparent: float, dec_apparent: float):
        """Initialize solar coordinates from arguments

        This is a cheesy dataclass, since MicroPython doesn't have them.

        - True (geometric) longitude in degrees, AKA capital theta
        - Apparent longitude in degrees
        - Apparent latitude in degrees
        - Radius vector (distance from Earth to the Sun) in AU, AKA R
        - Right ascension in decimal degrees, AKA alpha
        - Declination in decimal degrees, AKA delta
        - Apparent right ascension in decimal degrees
        - Apparent declination in decimnal degrees
        """

        # TODO: Validate all values for legitimate range

        self.true_lon = true_lon
        self.apparent_lon = apparent_lon
        self.apparent_lat = apparent_lat
        self.radius_vector = radius_vector
        self.ra = ra
        self.dec = dec
        self.ra_apparent = ra_apparent
        self.dec_apparent = dec_apparent


def solar_coordinates_low_accuracy_meeus(jd: float) -> SolarCoordinates:
    """Obtain solar coordinates, including geometric lat/lon and ra/dec and apparent ra/dec for a Julian day.

    Uses the simpler and lower accuracy method described in
        Meeus, J. (1991). Astronomical algorithms (1st ed.). Willmann-Bell". Chapter 24.
    """
    # Current date in julian centuries from epoch J2000.0
    T = julian.julian_day_to_julian_centuries(jd, epoch=julian.EPOCH_J2000)

    # Geometric mean longitude of the Sun
    Lo = poly_eval(T, [280.46645, 36000.76983, 0.0003032]) % 360.0

    # Mean anomaly of the Sun
    M = poly_eval(T, [357.52910, 35999.05030, -0.0001559, -0.00000048]) % 360.0

    # Eccentricity of the Earth/Sun orbit

    # Value 1: "Meeus, J. (1991). Astronomical algorithms (1st ed.). Willmann-Bell". Equation 24.4.
    e = poly_eval(T, [0.016708617, -0.000042037, -0.0000001236])

    # Equation of the center, estimatd in parts
    CsinM = poly_eval(T, [1.914600, -0.004817, -0.000014]) * sin_degrees(M)
    Csin2M = poly_eval(T, [0.019993, -0.000101]) * sin_degrees((2.0 * M) % 360.0)
    Csin3M = 0.000290 * sin_degrees((3.0 * M) % 360.0)
    C = CsinM + Csin2M + Csin3M

    # Sun's true longitude
    Theta = (Lo + C) % 360.0

    # Sun's true anomaly
    v = M + C

    # Sun's radius vector
    R = (1.000001018 * (1.0 - (e * e))) / (1.0 + (e * cos_degrees(v % 360.0)))

    # Apparent longitude
    Omega = poly_eval(T, [125.04, -1934.136]) % 360.0
    sun_lambda = (Theta - 0.00569 - (0.00478 * sin_degrees(Omega))) % 360.0

    # Compute true obliquity
    epsilon = nutation_simplified_meeus(jd).true_obliquity

    # Compute right ascension and declination
    ra = atan2_degrees((cos_degrees(epsilon) * sin_degrees(Theta)), cos_degrees(Theta)) % 360.0
    dec = asin_degrees(sin_degrees(epsilon) * sin_degrees(Theta))

    # Compute apparent right ascension and declination
    epsilon_for_apparent = epsilon + (0.00256 * cos_degrees(Omega))
    ra_apparent = atan2_degrees((cos_degrees(epsilon_for_apparent) * sin_degrees(sun_lambda)), cos_degrees(sun_lambda)) % 360.0
    dec_apparent = asin_degrees(sin_degrees(epsilon_for_apparent) * sin_degrees(sun_lambda))

    return SolarCoordinates(true_lon=Theta, apparent_lon=sun_lambda, apparent_lat=0.0, radius_vector=R, ra=ra, dec=dec, ra_apparent=ra_apparent, dec_apparent=dec_apparent)

def solar_coordinates(jd: float) -> SolarCoordinates:
    return solar_coordinates_low_accuracy_meeus(jd)
