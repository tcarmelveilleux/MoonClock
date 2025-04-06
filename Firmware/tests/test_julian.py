import unittest

from tcv_astro import julian

class TestJulian(unittest.TestCase):
    def test_known_dates(self):
        self.assertEqual(julian.date_to_julian_day(1957, 10, 4.81),  2436116.31)
        self.assertEqual(julian.date_to_julian_day(333, 1, 27.5),  1842713.0)

        self.assertEqual(julian.date_to_julian_day(2000, 1, 1.5),  2451545.0)
        self.assertEqual(julian.date_to_julian_day(1987, 1, 27.0), 2446822.5)
        self.assertEqual(julian.date_to_julian_day(1987, 6, 19.5), 2446966.0)
        self.assertEqual(julian.date_to_julian_day(1988, 1, 27.0), 2447187.5)
        self.assertEqual(julian.date_to_julian_day(1988, 6, 19.5), 2447332.0)
        self.assertEqual(julian.date_to_julian_day(1900, 1, 1.0), 2415020.5)
        self.assertEqual(julian.date_to_julian_day(1600, 1, 1.0), 2305447.5)
        self.assertEqual(julian.date_to_julian_day(1600, 12, 31.0), 2305812.5)
        self.assertEqual(julian.date_to_julian_day(837, 4, 10.3), 2026871.8)
        self.assertEqual(julian.date_to_julian_day(-1000, 7, 12.5), 1356001.0)
        self.assertEqual(julian.date_to_julian_day(-1000, 2, 29.0), 1355866.5)
        self.assertEqual(julian.date_to_julian_day(-1001, 8, 17.9), 1355671.4)
        self.assertEqual(julian.date_to_julian_day(-4712, 1, 1.5), 0.0)
        self.assertEqual(julian.date_to_julian_day(2010, 1, 1.0), 2455197.5)
        self.assertEqual(julian.date_to_julian_day(2015, 3, 21.5), 2457103.0)

    def test_is_gregorian_works(self):
        # Gregorian cases
        self.assertTrue(julian.is_gregorian_calendar(2025, 1, 25.0))
        self.assertTrue(julian.is_gregorian_calendar(1583, 10, 15.0))

        # Transition period
        self.assertTrue(julian.is_gregorian_calendar(1582, 10, 15.0))
        self.assertFalse(julian.is_gregorian_calendar(1582, 10, 4.0))
        self.assertFalse(julian.is_gregorian_calendar(1582, 10, 4.999999))
        self.assertFalse(julian.is_gregorian_calendar(1582, 10, 3.0))
        
        # Invalid dates
        with self.assertRaises(ValueError):
            julian.is_gregorian_calendar(1582, 10, 5.0)
        with self.assertRaises(ValueError):            
            julian.is_gregorian_calendar(1582, 10, 9.0)
        with self.assertRaises(ValueError):    
            julian.is_gregorian_calendar(1582, 10, 14.0)
        with self.assertRaises(ValueError):
            julian.is_gregorian_calendar(1582, 10, 14.999999)
        
        # Prior to transition, all dates julian
        self.assertFalse(julian.is_gregorian_calendar(837, 4, 10.3))
        self.assertFalse(julian.is_gregorian_calendar(-100, 1, 1.0))
        self.assertFalse(julian.is_gregorian_calendar(-4712, 1, 1.5))
        self.assertFalse(julian.is_gregorian_calendar(-10000, 4, 7.9))

    def test_fractional_days(self):
        self.assertEqual(julian.time_to_fraction(hours=0, minutes=0, seconds=0.0), 0.0)
        self.assertEqual(julian.time_to_fraction(hours=12, minutes=0, seconds=0.0), 0.5)
        self.assertEqual(julian.time_to_fraction(hours=6, minutes=0, seconds=0.0), 0.25)
        self.assertAlmostEqual(julian.time_to_fraction(hours=18, minutes=32, seconds=14.0), 0.7723842592592592)
        self.assertAlmostEqual(julian.time_to_fraction(hours=23, minutes=59, seconds=1.0), 0.9993171296296296)
        self.assertAlmostEqual(julian.time_to_fraction(hours=23, minutes=59, seconds=59.999999), 0.999999999)
        with self.assertRaises(ValueError):
            julian.time_to_fraction(hours=24, minutes=0, seconds=0.0)
        with self.assertRaises(ValueError):
            julian.time_to_fraction(hours=-1, minutes=0, seconds=0.0)
        with self.assertRaises(ValueError):
            julian.time_to_fraction(hours=23, minutes=60, seconds=0.0)

    def test_julian_to_date(self):
        year, month, day = julian.julian_day_to_date(2436116.31)
        self.assertEqual(year, 1957)
        self.assertEqual(month, 10)
        self.assertAlmostEqual(day, 4.81)

        year, month, day = julian.julian_day_to_date(1842713.0)
        self.assertEqual(year, 333)
        self.assertEqual(month, 1)
        self.assertAlmostEqual(day, 27.5)

        year, month, day = julian.julian_day_to_date(1507900.13)
        self.assertEqual(year, -584)
        self.assertEqual(month, 5)
        self.assertAlmostEqual(day, 28.63)

        year, month, day = julian.julian_day_to_date(2457103.0)
        self.assertEqual(year, 2015)
        self.assertEqual(month, 3)
        self.assertAlmostEqual(day, 21.5)

        year, month, day = julian.julian_day_to_date(0.0)
        self.assertEqual(year, -4712)
        self.assertEqual(month, 1)
        self.assertAlmostEqual(day, 1.5)

        with self.assertRaises(ValueError):
            julian.julian_day_to_date(-0.0001)

    def test_julian_centuries(self):
        self.assertEqual(julian.julian_day_to_julian_centuries(julian.EPOCH_J2000, julian.EPOCH_J2000), 0.0)
        self.assertAlmostEqual(julian.julian_day_to_julian_centuries(2448908.5, julian.EPOCH_J2000), -0.072183436)

if __name__ == '__main__':
    unittest.main()