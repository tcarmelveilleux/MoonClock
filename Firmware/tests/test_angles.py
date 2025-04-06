import unittest

from tcv_astro import angles

class TestAngles(unittest.TestCase):
    def test_signum(self):
        self.assertEqual(angles.signum(0.0001), 1.0)
        self.assertEqual(angles.signum(1000.0), 1.0)
        self.assertEqual(angles.signum(0.0), 1.0)
        self.assertEqual(angles.signum(-0.0001), -1.0)
        self.assertEqual(angles.signum(-1000.0), -1.0)

    def test_dms_conversion(self):
        self.assertAlmostEqual(angles.dms_to_degrees(150.0, 0.0, 0.0), 150.0)
        self.assertAlmostEqual(angles.dms_to_degrees(150.0, 30.0, 0.0), 150.5)
        self.assertAlmostEqual(angles.dms_to_degrees(150.0, 30.0, 3600.0), 151.5)

        self.assertAlmostEqual(angles.dms_to_degrees(-150.0, 0.0, 0.0), -150.0)
        self.assertAlmostEqual(angles.dms_to_degrees(-150.0, 30.0, 0.0), -150.5)
        self.assertAlmostEqual(angles.dms_to_degrees(-150.0, 30.0, 3600.0), -151.5)
        self.assertAlmostEqual(angles.dms_to_degrees(0, 0.0, 1.0), 1.0/3600.0)

if __name__ == '__main__':
    unittest.main()
