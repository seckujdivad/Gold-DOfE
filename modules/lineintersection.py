# Code is taken from https://stackoverflow.com/questions/563198/how-do-you-detect-where-two-line-segments-intersect

import numpy as np

def np_perp( a ) :
    b = np.empty_like(a)
    b[0] = a[1]
    b[1] = -a[0]
    return b

def np_cross_product(a, b):
    return np.dot(a, np_perp(b))

def wrap_np_seg_intersect(a, b, considerCollinearOverlapAsIntersect = False):
    return np_seg_intersect(np.array([np.array([a[0][0], a[0][1]]), np.array([a[1][0], a[1][1]])]), np.array([np.array([b[0][0], b[0][1]]), np.array([b[1][0], b[1][1]])]), considerCollinearOverlapAsIntersect)

def np_seg_intersect(a, b, considerCollinearOverlapAsIntersect = False):
    # https://stackoverflow.com/questions/563198/how-do-you-detect-where-two-line-segments-intersect/565282#565282
    # http://www.codeproject.com/Tips/862988/Find-the-intersection-point-of-two-line-segments
    r = a[1] - a[0]
    s = b[1] - b[0]
    v = b[0] - a[0]
    num = np_cross_product(v, r)
    denom = np_cross_product(r, s)
    # If r x s = 0 and (q - p) x r = 0, then the two lines are collinear.
    if np.isclose(denom, 0) and np.isclose(num, 0):
        # 1. If either  0 <= (q - p) * r <= r * r or 0 <= (p - q) * s <= * s
        # then the two lines are overlapping,
        if(considerCollinearOverlapAsIntersect):
            vDotR = np.dot(v, r)
            aDotS = np.dot(-v, s)
            if (0 <= vDotR  and vDotR <= np.dot(r,r)) or (0 <= aDotS  and aDotS <= np.dot(s,s)):
                return True
        # 2. If neither 0 <= (q - p) * r = r * r nor 0 <= (p - q) * s <= s * s
        # then the two lines are collinear but disjoint.
        # No need to implement this expression, as it follows from the expression above.
        return None
    if np.isclose(denom, 0) and not np.isclose(num, 0):
        # Parallel and non intersecting
        return None
    u = num / denom
    t = np_cross_product(v, s) / denom
    if u >= 0 and u <= 1 and t >= 0 and t <= 1:
        res = b[0] + (s*u)
        return res
    # Otherwise, the two line segments are not parallel but do not intersect.
    return None