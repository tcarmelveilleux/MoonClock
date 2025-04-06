import unittest

from tcv_astro import polynomial

class TestPolynomial(unittest.TestCase):
    def test_evaluation(self):
        self.assertEqual(polynomial.poly_eval_naive(0.0, [1.0]), 1.0)
        self.assertEqual(polynomial.poly_eval_naive(0.0, [0.0, 1.0]), 0.0)
        self.assertEqual(polynomial.poly_eval_naive(0.0, [1.0, 1.0]), 1.0)
        self.assertEqual(polynomial.poly_eval_naive(3.0, [2.0]), 2.0)
        self.assertEqual(polynomial.poly_eval_naive(2.0, [1.0, 2.0]), 5.0)
        self.assertEqual(polynomial.poly_eval_naive(-1.0, [1.0, 2.0, -4.0]), -5.0)
        self.assertEqual(polynomial.poly_eval_naive(2.0, [1.0, -2.0, 4.0, 6.0]), 61.0)

        self.assertEqual(polynomial.poly_eval(0.0, [1.0]), 1.0)
        self.assertEqual(polynomial.poly_eval(0.0, [0.0, 1.0]), 0.0)
        self.assertEqual(polynomial.poly_eval(0.0, [1.0, 1.0]), 1.0)
        self.assertEqual(polynomial.poly_eval(3.0, [2.0]), 2.0)
        self.assertEqual(polynomial.poly_eval(2.0, [1.0, 2.0]), 5.0)
        self.assertEqual(polynomial.poly_eval(-1.0, [1.0, 2.0, -4.0]), -5.0)
        self.assertEqual(polynomial.poly_eval(2.0, [1.0, -2.0, 4.0, 6.0]), 61.0)

    def test_linear_interpolate(self):
        coeffs = [(1.0, 2.0), (2.0, 3.0), (3.0, 5.0)]

        with self.assertRaises(ValueError):
            polynomial.linear_interp_in_parts(x=0.0, known_points=[])
        with self.assertRaises(ValueError):
            polynomial.linear_interp_in_parts(x=0.0, known_points=[(1.0, 2.0)])
        
        # Edge conditions without extrapolation
        with self.assertRaises(ValueError):
            polynomial.linear_interp_in_parts(x=0.0, known_points=coeffs, extrapolate_edges=False)
        with self.assertRaises(ValueError):
            polynomial.linear_interp_in_parts(x=4.0, known_points=coeffs, extrapolate_edges=False)

        # Edge conditions with extrapolation
        self.assertEqual(polynomial.linear_interp_in_parts(x=1.0, known_points=coeffs), 2.0)
        self.assertEqual(polynomial.linear_interp_in_parts(x=0.99999999, known_points=coeffs), 2.0)
        self.assertEqual(polynomial.linear_interp_in_parts(x=-1000.0, known_points=coeffs), 2.0)

        self.assertEqual(polynomial.linear_interp_in_parts(x=3.0, known_points=coeffs), 5.0)
        self.assertEqual(polynomial.linear_interp_in_parts(x=3.00000001, known_points=coeffs), 5.0)
        self.assertEqual(polynomial.linear_interp_in_parts(x=1000.0, known_points=coeffs), 5.0)

        # Intermediate values
        self.assertEqual(polynomial.linear_interp_in_parts(x=1.5, known_points=coeffs), 2.5)
        self.assertEqual(polynomial.linear_interp_in_parts(x=2.0, known_points=coeffs), 3.0)
        self.assertEqual(polynomial.linear_interp_in_parts(x=2.5, known_points=coeffs), 4.0)

    
if __name__ == '__main__':
    unittest.main()