"""
Parametric 2D Pattern Generation Module.
Constructs continuous full-length 2D pattern panels in centimeters using Shapely polygons,
guided directly by computer-vision silhouette proportions and size-chart dimensions.
Implements Category 1: Original 2D pattern geometry.
"""

from typing import Dict, List, Tuple, Optional
import numpy as np
from shapely.geometry import Polygon

from .models import Panel2DGeometry, BoundaryPoint2D


class PatternGenerator:
    def __init__(self, dimensions: Dict[str, float], vision_proportions: Optional[Dict[str, float]] = None):
        """
        dimensions: bust_circ, waist_circ, hip_circ, hem_circ, front_length, back_length, shoulder_width
        vision_proportions: Optional measurements extracted directly from product photos by vision.py
        """
        for k, v in dimensions.items():
            if v is None or np.isnan(v) or v <= 0:
                raise ValueError(f"Invalid dimension '{k}': {v}. Must be positive non-NaN number.")
        self.dims = dimensions

        # Proportions: Use image-measured proportions if provided, else sizing defaults
        vp = vision_proportions or {}

        # Front / back lengths
        self.total_len_front = dimensions["front_length"]
        self.total_len_back = dimensions["back_length"]

        # Half widths (since body is symmetric left/right)
        self.w_bust = dimensions["bust_circ"] / 2.0
        self.w_waist = dimensions["waist_circ"] / 2.0
        self.w_hip = dimensions["hip_circ"] / 2.0
        self.w_hem = dimensions["hem_circ"] / 2.0

        # Incorporate image-measured neckline and armhole drops
        self.neck_drop_front = vp.get("neck_depth", 13.9)
        self.neck_drop_back = vp.get("back_neck_depth", 13.7)
        self.armhole_drop = vp.get("armhole_depth", 18.1)

        self.shoulder_w = dimensions.get("shoulder_width", 23.5)
        self.neck_half_w = 8.0  # Narrow tank strap width: (23.5/2 - 8.0) = 3.75 cm (~3 cm)

    def _sample_bezier_curve(self, p0: Tuple[float, float], p1: Tuple[float, float],
                             p2: Tuple[float, float], num_pts: int = 8) -> List[Tuple[float, float]]:
        """Samples quadratic Bezier curve for neckline and armholes."""
        t = np.linspace(0, 1, num_pts)
        pts = []
        for ti in t:
            bx = (1 - ti)**2 * p0[0] + 2 * (1 - ti) * ti * p1[0] + ti**2 * p2[0]
            by = (1 - ti)**2 * p0[1] + 2 * (1 - ti) * ti * p1[1] + ti**2 * p2[1]
            pts.append((round(float(bx), 3), round(float(by), 3)))
        return pts

    def build_front_panel(self) -> Panel2DGeometry:
        """
        Builds the continuous, full-length Front Shift Dress Panel (no waist seam).
        Origin (0,0) is at center top neck level; Y extends downward to -total_len_front.
        """
        h = self.total_len_front
        half_shoulder = self.shoulder_w / 2.0
        half_bust = self.w_bust / 2.0
        half_waist = self.w_waist / 2.0
        half_hip = self.w_hip / 2.0
        half_hem = self.w_hem / 2.0

        armhole_y = -self.armhole_drop
        waist_y = -min(40.0, round(h * 0.35, 2))
        hip_y = -min(60.0, round(h * 0.52, 2))
        hem_y = -h

        points: List[Tuple[float, float]] = []
        edges: Dict[str, List[int]] = {}

        # 1. Right shoulder (from neck inner to shoulder outer)
        p_neck_inner_r = (self.neck_half_w, 0.0)
        p_shoulder_outer_r = (half_shoulder, -2.5)
        idx_sh_r_start = len(points)
        points.append(p_neck_inner_r)
        points.append(p_shoulder_outer_r)
        edges["shoulder_right"] = [idx_sh_r_start, len(points) - 1]

        # 2. Right armhole (shoulder outer to right underarm)
        p_underarm_r = (half_bust, armhole_y)
        ctrl_arm_r = (half_bust * 0.85, armhole_y * 0.5)
        arm_pts_r = self._sample_bezier_curve(p_shoulder_outer_r, ctrl_arm_r, p_underarm_r, num_pts=8)[1:]
        for p in arm_pts_r:
            points.append(p)
        edges["armhole_right"] = [len(points) - 1 - len(arm_pts_r), len(points) - 1]

        # 3. Continuous Right Side Seam (underarm -> straight shift waist -> hip -> hem)
        idx_side_r_start = len(points) - 1
        points.append((half_waist, waist_y))
        points.append((half_hip, hip_y))
        points.append((half_hem, hem_y))
        idx_side_r_end = len(points) - 1
        edges["side_seam_right"] = [idx_side_r_start, idx_side_r_end]

        # 4. Bottom Hem (right hem to left hem)
        idx_hem_start = len(points) - 1
        points.append((0.0, hem_y - 1.0))  # gentle bottom hem curve
        points.append((-half_hem, hem_y))
        idx_hem_end = len(points) - 1
        edges["hem"] = [idx_hem_start, idx_hem_end]

        # 5. Continuous Left Side Seam (hem -> hip -> waist -> left underarm)
        idx_side_l_start = len(points) - 1
        points.append((-half_hip, hip_y))
        points.append((-half_waist, waist_y))
        p_underarm_l = (-half_bust, armhole_y)
        points.append(p_underarm_l)
        idx_side_l_end = len(points) - 1
        edges["side_seam_left"] = [idx_side_l_start, idx_side_l_end]

        # 6. Left armhole (underarm to left shoulder outer)
        p_shoulder_outer_l = (-half_shoulder, -2.5)
        ctrl_arm_l = (-half_bust * 0.85, armhole_y * 0.5)
        arm_pts_l = self._sample_bezier_curve(p_underarm_l, ctrl_arm_l, p_shoulder_outer_l, num_pts=8)[1:]
        for p in arm_pts_l:
            points.append(p)
        edges["armhole_left"] = [idx_side_l_end, len(points) - 1]

        # 7. Left shoulder (shoulder outer to neck inner)
        p_neck_inner_l = (-self.neck_half_w, 0.0)
        idx_sh_l_start = len(points) - 1
        points.append(p_neck_inner_l)
        edges["shoulder_left"] = [idx_sh_l_start, len(points) - 1]

        # 8. Front scoop neckline (left neck inner to right neck inner)
        idx_neck_start = len(points) - 1
        neck_center = (0.0, -self.neck_drop_front)
        pts_neck1 = self._sample_bezier_curve(p_neck_inner_l, (-self.neck_half_w * 0.5, -self.neck_drop_front), neck_center, num_pts=7)[1:]
        pts_neck2 = self._sample_bezier_curve(neck_center, (self.neck_half_w * 0.5, -self.neck_drop_front), p_neck_inner_r, num_pts=7)[1:]
        for p in pts_neck1 + pts_neck2[:-1]:  # omit last point as it closes to p_neck_inner_r
            points.append(p)
        edges["neckline"] = [idx_neck_start, 0]

        poly = Polygon(points)
        bounds = poly.bounds
        w = round(bounds[2] - bounds[0], 2)
        ht = round(bounds[3] - bounds[1], 2)

        return Panel2DGeometry(
            panel_id="front_panel",
            panel_name="Front Shift Dress Panel",
            side="front",
            category="shift_dress",
            width_cm=w,
            height_cm=ht,
            area_sq_cm=round(poly.area, 2),
            perimeter_cm=round(poly.length, 2),
            contour_points=[BoundaryPoint2D(x=p[0], y=p[1]) for p in points],
            edges=edges
        )

    def build_back_panel(self, side_half: str) -> Panel2DGeometry:
        """
        Builds a full-length Back Panel half ('left' or 'right') joined along the center-back seam.
        """
        is_right = (side_half == "right")
        h = self.total_len_back
        half_shoulder = self.shoulder_w / 2.0
        half_bust = self.w_bust / 2.0
        half_waist = self.w_waist / 2.0
        half_hip = self.w_hip / 2.0
        half_hem = self.w_hem / 2.0

        armhole_y = -self.armhole_drop
        waist_y = -min(40.0, round(h * 0.35, 2))
        hip_y = -min(60.0, round(h * 0.52, 2))
        hem_y = -h

        sign = 1.0 if is_right else -1.0
        points: List[Tuple[float, float]] = []
        edges: Dict[str, List[int]] = {}

        if is_right:
            # Center back seam top (0, -neck_drop_back)
            p_cb_top = (0.0, -self.neck_drop_back)
            p_cb_bottom = (0.0, hem_y)
            p_hem_outer = (half_hem, hem_y)
            p_hip = (half_hip, hip_y)
            p_waist = (half_waist, waist_y)
            p_underarm = (half_bust, armhole_y)
            p_sh_outer = (half_shoulder, -2.0)
            p_neck_inner = (self.neck_half_w, 0.0)

            # 1. Center Back Seam (top to bottom)
            idx_cb_start = len(points)
            points.append(p_cb_top)
            points.append(p_cb_bottom)
            edges["center_back_seam"] = [idx_cb_start, len(points) - 1]

            # 2. Hem
            idx_hem_start = len(points) - 1
            points.append(p_hem_outer)
            edges["hem"] = [idx_hem_start, len(points) - 1]

            # 3. Continuous Side Seam
            idx_side_start = len(points) - 1
            points.append(p_hip)
            points.append(p_waist)
            points.append(p_underarm)
            edges["side_seam_right"] = [idx_side_start, len(points) - 1]

            # 4. Armhole
            arm_pts = self._sample_bezier_curve(p_underarm, (half_bust * 0.88, armhole_y * 0.5), p_sh_outer, num_pts=8)[1:]
            for p in arm_pts:
                points.append(p)
            edges["armhole_right"] = [len(points) - 1 - len(arm_pts), len(points) - 1]

            # 5. Shoulder Seam
            idx_sh_start = len(points) - 1
            points.append(p_neck_inner)
            edges["shoulder_right"] = [idx_sh_start, len(points) - 1]

            # 6. Back neckline to center top
            pts_neck = self._sample_bezier_curve(p_neck_inner, (self.neck_half_w * 0.5, -self.neck_drop_back), p_cb_top, num_pts=6)[1:-1]
            for p in pts_neck:
                points.append(p)
            edges["neckline"] = [len(points) - 1, 0]

            panel_id = "back_right_panel"
            panel_name = "Back Right Shift Panel"
        else:
            # Left half of back
            p_cb_top = (0.0, -self.neck_drop_back)
            p_cb_bottom = (0.0, hem_y)
            p_hem_outer = (-half_hem, hem_y)
            p_hip = (-half_hip, hip_y)
            p_waist = (-half_waist, waist_y)
            p_underarm = (-half_bust, armhole_y)
            p_sh_outer = (-half_shoulder, -2.0)
            p_neck_inner = (-self.neck_half_w, 0.0)

            # 1. Back Neckline from center top to left neck inner
            idx_neck_start = len(points)
            points.append(p_cb_top)
            pts_neck = self._sample_bezier_curve(p_cb_top, (-self.neck_half_w * 0.5, -self.neck_drop_back), p_neck_inner, num_pts=6)[1:]
            for p in pts_neck:
                points.append(p)
            edges["neckline"] = [idx_neck_start, len(points) - 1]

            # 2. Shoulder Seam
            idx_sh_start = len(points) - 1
            points.append(p_sh_outer)
            edges["shoulder_left"] = [idx_sh_start, len(points) - 1]

            # 3. Armhole
            arm_pts = self._sample_bezier_curve(p_sh_outer, (-half_bust * 0.88, armhole_y * 0.5), p_underarm, num_pts=8)[1:]
            for p in arm_pts:
                points.append(p)
            edges["armhole_left"] = [len(points) - 1 - len(arm_pts), len(points) - 1]

            # 4. Continuous Side Seam
            idx_side_start = len(points) - 1
            points.append(p_waist)
            points.append(p_hip)
            points.append(p_hem_outer)
            edges["side_seam_left"] = [idx_side_start, len(points) - 1]

            # 5. Hem to center back bottom
            idx_hem_start = len(points) - 1
            points.append(p_cb_bottom)
            edges["hem"] = [idx_hem_start, len(points) - 1]

            # 6. Center Back Seam (bottom back to top)
            edges["center_back_seam"] = [len(points) - 1, 0]

            panel_id = "back_left_panel"
            panel_name = "Back Left Shift Panel"

        poly = Polygon(points)
        bounds = poly.bounds
        w = round(bounds[2] - bounds[0], 2)
        ht = round(bounds[3] - bounds[1], 2)

        return Panel2DGeometry(
            panel_id=panel_id,
            panel_name=panel_name,
            side="back",
            category="shift_dress",
            width_cm=w,
            height_cm=ht,
            area_sq_cm=round(poly.area, 2),
            perimeter_cm=round(poly.length, 2),
            contour_points=[BoundaryPoint2D(x=p[0], y=p[1]) for p in points],
            edges=edges
        )

    def generate_all_panels(self) -> Dict[str, Panel2DGeometry]:
        """Generates continuous full-length panels matching the real garment."""
        return {
            "front_panel": self.build_front_panel(),
            "back_left_panel": self.build_back_panel(side_half="left"),
            "back_right_panel": self.build_back_panel(side_half="right")
        }
