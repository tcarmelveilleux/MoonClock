import unittest

from tcv_astro import moon

class TestMoon(unittest.TestCase):
    def test_lunar_coordinates(self):
        position = moon.lunar_coordinates_high_accuracy_meeus(jd=2448724.5)

        # self.assertAlmostEqual(position.radius_vector, 0.99766, places=5)
        # self.assertAlmostEqual(position.true_lon, 199.90987, places=5)
        # self.assertAlmostEqual(position.apparent_lon, 199.90894, places=4)
        # # Deemed zero for all intents and purposes of the low-accuracy version
        # self.assertEqual(position.apparent_lat, 0.0)
        # self.assertAlmostEqual(position.ra_apparent, 198.38082, places=3)
        # self.assertAlmostEqual(position.dec_apparent, -7.78507, places=3)

if __name__ == '__main__':
    unittest.main()