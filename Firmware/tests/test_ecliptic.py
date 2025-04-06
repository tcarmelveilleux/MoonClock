import unittest

from tcv_astro import ecliptic
from tcv_astro import angles

class TestEcliptic(unittest.TestCase):
    def test_nutations_and_obliquity(self):
        nut_and_ob = ecliptic.nutations_and_obliquity(jd=2446895.5)
        self.assertAlmostEqual(nut_and_ob.nutation_longitude, angles.dms_to_degrees(seconds=-3.788), 2)
        self.assertAlmostEqual(nut_and_ob.nutation_obliquity, angles.dms_to_degrees(seconds=9.443), 3)
        self.assertAlmostEqual(nut_and_ob.true_obliquity, angles.dms_to_degrees(23, 26, 36.850), 3)

if __name__ == '__main__':
    unittest.main()