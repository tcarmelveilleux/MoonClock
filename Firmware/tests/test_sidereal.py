import unittest

from tcv_astro import sidereal
from tcv_astro import angles

class TestSidereal(unittest.TestCase):
    def test_sidereal_time(self):
        app_sidereal = sidereal.sidereal_time_at_greenwhich(jd=2446895.5)
        print("sidereal", angles.degrees_to_hms(app_sidereal))

if __name__ == '__main__':
    unittest.main()