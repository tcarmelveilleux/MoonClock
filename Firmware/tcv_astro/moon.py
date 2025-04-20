
from tcv_astro import julian
from tcv_astro.polynomial import poly_eval
from tcv_astro.angles import sin_degrees, cos_degrees, asin_degrees, atan2_degrees, degrees_to_hms, degrees_to_dms, ecliptic_to_equatorial
from tcv_astro.ecliptic import nutation_simplified_meeus
from tcv_astro.utils import package_relpath
from tcv_astro.sun import solar_coordinates_low_accuracy_meeus
import struct
from io import BytesIO

# Give us a chance to run GC on circuitpython
try:
    import gc
    def run_gc():
        gc.collect()
except:
    def run_gc():
        pass

class LunarCoordinates:
    def __init__(self, true_lon: float, ra_apparent: float, dec_apparent: float, horizontal_parallax_degrees: float, distance_km: float):
        """Initialize lunar coordinates from arguments

        This is a cheesy dataclass, since MicroPython doesn't have them.

        - True ecliptic longitude
        - Apparent right ascension in decimal degrees
        - Apparent declination in decimnal degrees
        - Moon horizontal parallax in degrees
        - Distance from the center of the earth in kilometers

        """
        self.true_lon = true_lon
        self.ra_apparent = ra_apparent
        self.dec_apparent = dec_apparent
        self.horizontal_parallax_degrees = horizontal_parallax_degrees
        self.distance_km = distance_km


TBL_IDX_SIGMA1 = 0
TBL_IDX_SIGMAR = 1
TBL_IDX_SIGMAB = 2


def sum_table45(table45_bytes: bytes, table_idx: int, m_corrector: callable, D: float, M: float, Mprime: float, F: float) -> float:
    """Computes the sum from one of the columns of Table 45 A/B from Meeus.

    - table45_bytes --> content of specially encoded packed binary file (see scripts/convert_table45.py
    - table_idx --> which of the table/columns to add
    - m_corrector --> callable with (M) that applies a correction factor when M !=0 in a row
    - D, M, Mprime, F --> base values to apply to the factors of the table

    Reference:
        Meeus, J. (1991). Astronomical algorithms (1st ed.). Willmann-Bell". Chapter 45.

    Tables re-entered by hand by the author, from the book.
    """
    TABLE45_MAGIC = 0x7ab45000
    header_format = "<IB"
    entry_format = "<bbbbi"

    assert table_idx <= TBL_IDX_SIGMAB
    with BytesIO(table45_bytes) as infile:
        magic, num_tables = struct.unpack(header_format, infile.read(struct.calcsize(header_format)))
        if magic != TABLE45_MAGIC or table_idx >= num_tables:
            raise ValueError("Wrong table45 format")

        to_skip = table_idx

        entry_size = struct.calcsize(entry_format)

        for load_idx in range(table_idx + 1):
            num_items = struct.unpack("<H", infile.read(2))[0]
            if load_idx < to_skip:
                infile.read(num_items * entry_size)
                continue

            final_sum = 0.0
            for _ in range(num_items):
                row = struct.unpack(entry_format, infile.read(entry_size))
                M_D: int = row[0]
                M_M: int = row[1]
                M_Mprime: int = row[2]
                M_F: int = row[3]
                coeff: float = float(row[4])

                m_factor = m_corrector(M_M)
                trig_arg = (M_D * D) + (M_M * M) + (M_Mprime * Mprime) + (M_F * F)

                if (table_idx == TBL_IDX_SIGMAR):
                    trig_val = cos_degrees(trig_arg % 360.0)
                else:
                    trig_val = sin_degrees(trig_arg % 360.0)

                final_sum += (m_factor * coeff * trig_val)

            return final_sum


def lunar_coordinates_high_accuracy_meeus(jd: float) -> LunarCoordinates:
    """Obtain geocentric apparent lunar coordinates.

    Uses high-accuracy algorithm from:
        Meeus, J. (1991). Astronomical algorithms (1st ed.). Willmann-Bell". Chapter 45.
    """
    # Current date in julian centuries from epoch J2000.0
    T = julian.julian_day_to_julian_centuries(jd, epoch=julian.EPOCH_J2000)

    # Mean longitude of the moon
    Lprime = poly_eval(T, [218.3164591, 481267.88134236, -0.0013268, 1.0 / 538851.0, -1.0 / 65194000.0]) % 360.0

    # Mean elongation of the moon
    D = poly_eval(T, [297.8502042, 445267.1115168, -0.0016300, 1.0 / 545868.0, -1.0 / 113065000.0]) % 360.0

    # Mean anomaly of the sun
    M = poly_eval(T, [357.5291092, 35999.0502909, -0.0001536, 1.0 / 24490000.0]) % 360.0

    # Mean anomaly of the moon
    Mprime = poly_eval(T, [134.9634114, 477198.8676313, 0.0089970, 1.0 / 69699.0, -1.0 / 14712000.0]) % 360.0

    # Moon's argument of latitude (mean distance of the moon from its ascending node)
    F = poly_eval(T, [93.2720993, 483202.0175273, -0.0034029, -1.0 / 3526000, 1.0 / 863310000.0]) % 360.0

    # Other needed arguments for the corrections
    A1 = (119.75 + (131.849 * T)) % 360.0
    A2 = (53.09 + (479264.290 * T)) % 360.0
    A3 = (313.45 + (481266.484 * T)) % 360.0
    E = poly_eval(T, [1.0, -0.002516, -0.0000074])

    def m_corrector(M: int) -> float:
        if abs(M) == 1:
            return E
        elif abs(M) == 2:
            return E * E
        else:
            return 1.0

    with open(package_relpath(__file__, "table45.bin"), "rb") as infile:
        table45_bytes = infile.read()

    # The sums Sigma1, SigmaR, SigmaB are the core values used by the algorithm.
    sigma1 = sum_table45(table45_bytes, TBL_IDX_SIGMA1, m_corrector, D, M, Mprime, F)
    sigma1 += (3958.0 * sin_degrees(A1)) + (1962.0 * sin_degrees(Lprime - F)) + (318.0 * sin_degrees(A2))
    run_gc()

    sigmar = sum_table45(table45_bytes, TBL_IDX_SIGMAR, m_corrector, D, M, Mprime, F)

    sigmab = sum_table45(table45_bytes, TBL_IDX_SIGMAB, m_corrector, D, M, Mprime, F)
    sigmab += (-2235.0 * sin_degrees(Lprime)) + (382.0 * sin_degrees(A3)) + (175.0 * sin_degrees(A1 - F))
    sigmab += (175.0 * sin_degrees(A1 + F)) + (127.0 * sin_degrees(Lprime - Mprime)) - (115.0 * sin_degrees(Lprime + Mprime))

    # Make the big blob garbage-collectable once done.
    table45_bytes = None
    run_gc()

    # Geocentric latitude of the center of the moon
    moon_lambda = (Lprime + (sigma1 / 1e6)) % 360.0

    # Geocentric longitude of the center of the moon
    beta = sigmab / 1e6

    # Distance of the moon in kilometers
    delta = 385000.56 + (sigmar / 1e3)

    # Equatorial horizontal parallax
    moon_pi = asin_degrees(6378.14 / delta) % 360.0
    if moon_pi > 180.0:
        moon_pi = moon_pi - 360.0

    # TODO: Re-check accuracy to the book after moving to using accurate nutations from chap 21, not simplified
    nutation = nutation_simplified_meeus(jd)
    apparent_lambda = moon_lambda + nutation.nutation_longitude

    ra_apparent, dec_apparent = ecliptic_to_equatorial(apparent_lambda, beta, epsilon_degrees=nutation.true_obliquity)

    return LunarCoordinates(true_lon=moon_lambda, ra_apparent=ra_apparent, dec_apparent=dec_apparent, horizontal_parallax_degrees=moon_pi, distance_km=delta)


def lunar_coordinates(jd: float) -> LunarCoordinates:
    return lunar_coordinates_high_accuracy_meeus(jd)


def lunar_age_normalized_28_days(jd: float) -> float:
    """Return the lunar age normalized over 28 days instead of 29.53 days, which helps to show/understand quarter/half better."""
    solar_pos = solar_coordinates_low_accuracy_meeus(jd)
    lunar_pos = lunar_coordinates_high_accuracy_meeus(jd)

    moon_age_days: float = ((lunar_pos.true_lon - solar_pos.true_lon) % 360.0) / 12.1907
    normalized_to_28_days = (moon_age_days / 29.530575) * 28.0

    return normalized_to_28_days
