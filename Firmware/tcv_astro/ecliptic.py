from tcv_astro.angles import sin_degrees, cos_degrees, dms_to_degrees, degrees_to_dms
from tcv_astro.polynomial import poly_eval
from tcv_astro.julian import julian_day_to_julian_centuries, EPOCH_J2000

class EclipticNutationsAndObliquity:
    """Dataclass for Ecliptic nutations and the obliquity of the ecliptic.

    - nutation_longitude, nutation_obliquity, true_obliquity are in decimal degrees.

    This doesn't use @dataclass since MicroPython doesn't have it.
    """
    def __init__(self, nutation_longitude: float, nutation_obliquity: float, true_obliquity: float):
        self.nutation_longitude: float = nutation_longitude
        self.nutation_obliquity: float = nutation_obliquity
        self.true_obliquity: float = true_obliquity


def nutation_simplified_meeus(jd: float) -> EclipticNutationsAndObliquity:
    """Get the nutations in longitude and obliquity for a given Julian day number `jd`.

    Simplified method from "Meeus, J. (1991). Astronomical algorithms (1st ed.). Willmann-Bell". Chapter 21, page 132.

    Accuracy to 0.5" in longitude (delta psi) and 0.1" in obliquity (delta epsilon).
    """
    T: float = julian_day_to_julian_centuries(jd, epoch=EPOCH_J2000)

    # The below are present for if we ever move to the more accurate multi-term method.
    # I left them here because I bothered to type them before I realized I didn't need them :D
    if False:
        # Mean elongation of the Moon from the Sun
        D = poly_eval(T, [297.85036, 445267.111480, -0.0019142, 1.0 / 189474.0])

        # Mean anomaly of the Sun (Earth)
        M = poly_eval(T, [357.52772, 35999.050340, -0.0001603, -1.0 / 300000.0])

        # Mean anomaly of the Moon
        Mprime = poly_eval(T, [134.96298, 477198.867398, 0.0086972, 1.0 / 56250.0])

        # Moon's argument of latitude
        F = poly_eval(T, [93.27191, 483202.017538, -0.0036825, 1.0 / 327270.0])

        Omega = poly_eval(T, [125.04452, -1934.136261, 0.0020708, 1.0 / 450000.0]) % 360.0

    # Longitude of the ascending node of the Moon's mean orbit on the
    # ecliptic, measured from the mean equinox of the date.
    Omega = poly_eval(T, [125.04452, -1934.136261]) % 360.0

    # Mean longitude of the Sun
    L = (280.4465 + (36000.7698 * T)) % 360.0

    # Mean longitude of the Moon
    Lprime = (218.3165 + (481267.8813 * T)) % 360.0

    # Nutation in longitude
    delta_psi = dms_to_degrees(seconds=-17.20) * sin_degrees(Omega)
    delta_psi += dms_to_degrees(seconds=-1.32) * sin_degrees(2 * L)
    delta_psi += dms_to_degrees(seconds=-0.23) * sin_degrees(2 * Lprime)
    delta_psi += dms_to_degrees(seconds=0.21) * sin_degrees(2 * Omega)
    delta_psi %= 360.0
    delta_psi = (360.0 - delta_psi) if delta_psi > 180.0 else delta_psi

    # Nutation in obliquity
    delta_epsilon = dms_to_degrees(seconds=9.20) * cos_degrees(Omega)
    delta_epsilon += dms_to_degrees(seconds=0.57) * cos_degrees(2 * L)
    delta_epsilon += dms_to_degrees(seconds=0.10) * cos_degrees(2 * Lprime)
    delta_epsilon += dms_to_degrees(seconds=-0.09) * cos_degrees(2 * Omega)
    delta_epsilon %= 360.0
    delta_epsilon = (360.0 - delta_epsilon) if delta_epsilon > 180.0 else delta_epsilon

    # Simplified mean obliquity (equation 21.2), valid for < 2000 years from J2000.0,
    # which is OK for our purposes.
    epsilon_coeffs = [
        dms_to_degrees(degrees=23.0, minutes=26.0, seconds=21.448), # Constant (T^0)
        dms_to_degrees(seconds=-46.8150), # T^1
        dms_to_degrees(seconds=-0.00059), # T^2
        dms_to_degrees(seconds=0.001813), # T^3
    ]
    epsilon0 = poly_eval(T, epsilon_coeffs) % 360.0

    # True obliquity
    epsilon = (epsilon0 + delta_epsilon) % 360.

    # print("nutation", locals())
    # print("delta_psi", degrees_to_dms(delta_psi))
    # print("delta_epsilon", degrees_to_dms(delta_epsilon))
    # print("epsilon0", degrees_to_dms(epsilon0))
    # print("epsilon", degrees_to_dms(epsilon))

    return EclipticNutationsAndObliquity(nutation_longitude=delta_psi, nutation_obliquity=delta_epsilon, true_obliquity=epsilon)

def nutations_and_obliquity(jd: float) -> EclipticNutationsAndObliquity:
    return nutation_simplified_meeus(jd)
