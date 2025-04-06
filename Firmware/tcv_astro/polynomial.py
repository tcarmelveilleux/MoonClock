def poly_eval(x: float, coefficients: list[float]) -> float:
    """Horner method evaluation of polynomial at x, where coefficients are from a[0] to a[degree-1]."""
    result = coefficients[-1]
    for coefficient in coefficients[-2::-1]:
        result = coefficient + (result * x)

    return result

def poly_eval_naive(x: float, coefficients: list[float]) -> float:
    """Naive evaluation of polynomial at x, where coefficients are from a[0] to a[degree-1]."""
    result = coefficients[0]
    current_power = 1.0
    for coefficient in coefficients[1:]:
        current_power *= x
        result += (current_power * coefficient)

    return result

def linear_interp_in_parts(x: float, known_points: list[tuple[float, float]], extrapolate_edges: bool=True) -> float:
    """Linearly interpolate over multiple linear segments between the known points (in tuple (x,y) form).

    - Known-points must be in sorted ascending order of x position
    - If `x` is outside the bounds of the known points, the y value of the closest
      defined edge is returned if `extrapolate_edges` is True, otherwise a ValueError is raised.
    """

    if len(known_points) < 2:
        raise ValueError("Insufficient known points for interpolation")

    min_x, min_y = known_points[0]
    max_x, max_y = known_points[-1]
    if extrapolate_edges:
        if x < min_x:
            return min_y
        elif x > max_x:
            return max_y

    for segment_idx in range(len(known_points) - 1):
        x1, y1 = known_points[segment_idx]
        x2, y2 = known_points[segment_idx + 1]
        if x < x1 or x > x2: continue

        slope = (y2 - y1) / (x2 - x1)
        return y1 + (slope * (x - x1))

    raise ValueError("Input value out of bounds")
