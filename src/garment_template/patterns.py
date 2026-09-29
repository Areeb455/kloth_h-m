"""
Parametric 2D Pattern Generation Module.
Constructs unstretched 2D pattern panels in centimeters using Shapely polygons.
Implements Category 1: Original 2D pattern geometry.
"""

from typing import Dict, List, Tuple
import numpy as np
from shapely.geometry import Polygon

from .models import Panel2DGeometry, BoundaryPoint2D


class PatternGenerator:
    def __init__(self, dimensions: Dict[str, float]):
        """
        dimensions expects:
        bust_circ, waist_circ, hip_circ, hem_circ, front_length, back_length, shoulder_width
        """
        self.dims = dimensions

        # Half-widths for front & back panels (since body is symmetric left/right)
        self.w_bust = dimensions["bust_circ"] / 2.0
        self.w_waist = dimensions["waist_circ"] / 2.0
        self.w_hip = dimensions["hip_circ"] / 2.0
        self.w_hem = dimensions["hem_circ"] / 2.0

        # Vertical proportions based on anatomical landmarks
        self.bodice_len_front = 38.0
        self.bodice_len_back = 40.0

        self.skirt_len_front = max(20.0, dimensions["front_length"] - self.bodice_len_front)
        self.skirt_len_back = max(20.0, dimensions["back_length"] - self.bodice_len_back)

        self.shoulder_w = dimensions.get("shoulder_width", 32.0)
        self.strap_w = 4.5  # Width of shoulder strap at top

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

    def build_front_bodice(self) -> Panel2DGeometry:
        """
        Builds front upper bodice panel.
        Origin (0,0) is at the center waist seam.
        """
        h = self.bodice_len_front
        half_waist = self.w_waist / 2.0
        half_bust = self.w_bust / 2.0
        half_shoulder = self.shoulder_w / 2.0

        neck_drop = 12.0
        neck_half_w = 9.0
        armhole_drop = 18.0

        # Construct boundary clockwise starting from center waist (0, 0)
        points: List[Tuple[float, float]] = []
        edges: Dict[str, List[int]] = {}

        # 1. Waist seam (center waist to right waist)
        idx_waist_start = len(points)
        points.append((0.0, 0.0))
        points.append((half_waist, 0.0))
        idx_waist_end = len(points) - 1
        edges["waist_right"] = [idx_waist_start, idx_waist_end]

        # 2. Right side seam (right waist to right underarm)
        idx_side_start = len(points) - 1
        underarm_r = (half_bust, h - armhole_drop)
        points.append(underarm_r)
        idx_side_end = len(points) - 1
        edges["side_seam_right"] = [idx_side_start, idx_side_end]

        # 3. Right armhole (underarm to right shoulder outer)
        idx_armhole_r_start = len(points) - 1
        shoulder_outer_r = (half_shoulder, h - 2.5)
        arm_ctrl_r = (half_bust * 0.85, h - armhole_drop * 0.5)
        arm_pts_r = self._sample_bezier_curve(underarm_r, arm_ctrl_r, shoulder_outer_r, num_pts=8)[1:]
        for p in arm_pts_r:
            points.append(p)
        idx_armhole_r_end = len(points) - 1
        edges["armhole_right"] = [idx_armhole_r_start, idx_armhole_r_end]

        # 4. Right shoulder seam (shoulder outer to shoulder inner / neck)
        idx_shoulder_r_start = len(points) - 1
        shoulder_inner_r = (neck_half_w, h)
        points.append(shoulder_inner_r)
        idx_shoulder_r_end = len(points) - 1
        edges["shoulder_right"] = [idx_shoulder_r_start, idx_shoulder_r_end]

        # 5. Front neckline (right neck to left neck through center front scoop)
        idx_neck_start = len(points) - 1
        neck_ctrl_r = (neck_half_w * 0.5, h - neck_drop)
        neck_center = (0.0, h - neck_drop)
        neck_ctrl_l = (-neck_half_w * 0.5, h - neck_drop)
        shoulder_inner_l = (-neck_half_w, h)

        pts_neck1 = self._sample_bezier_curve(shoulder_inner_r, neck_ctrl_r, neck_center, num_pts=7)[1:]
        pts_neck2 = self._sample_bezier_curve(neck_center, neck_ctrl_l, shoulder_inner_l, num_pts=7)[1:]
        for p in pts_neck1 + pts_neck2:
            points.append(p)
        idx_neck_end = len(points) - 1
        edges["neckline"] = [idx_neck_start, idx_neck_end]

        # 6. Left shoulder seam (left shoulder inner to outer)
        idx_shoulder_l_start = len(points) - 1
        shoulder_outer_l = (-half_shoulder, h - 2.5)
        points.append(shoulder_outer_l)
        idx_shoulder_l_end = len(points) - 1
        edges["shoulder_left"] = [idx_shoulder_l_start, idx_shoulder_l_end]

        # 7. Left armhole (shoulder outer to left underarm)
        idx_armhole_l_start = len(points) - 1
        underarm_l = (-half_bust, h - armhole_drop)
        arm_ctrl_l = (-half_bust * 0.85, h - armhole_drop * 0.5)
        arm_pts_l = self._sample_bezier_curve(shoulder_outer_l, arm_ctrl_l, underarm_l, num_pts=8)[1:]
        for p in arm_pts_l:
            points.append(p)
        idx_armhole_l_end = len(points) - 1
        edges["armhole_left"] = [idx_armhole_l_start, idx_armhole_l_end]

        # 8. Left side seam (left underarm to left waist)
        idx_side_l_start = len(points) - 1
        points.append((-half_waist, 0.0))
        idx_side_l_end = len(points) - 1
        edges["side_seam_left"] = [idx_side_l_start, idx_side_l_end]

        # 9. Left waist (left waist back to center waist)
        idx_waist_l_start = len(points) - 1
        edges["waist_left"] = [idx_waist_l_start, 0]

        # Compute polygon metrics
        poly = Polygon(points)
        bounds = poly.bounds  # minx, miny, maxx, maxy
        w = round(bounds[2] - bounds[0], 2)
        ht = round(bounds[3] - bounds[1], 2)

        return Panel2DGeometry(
            panel_id="front_bodice",
            panel_name="Front Upper Panel",
            side="front",
            category="bodice",
            width_cm=w,
            height_cm=ht,
            area_sq_cm=round(poly.area, 2),
            perimeter_cm=round(poly.length, 2),
            contour_points=[BoundaryPoint2D(x=p[0], y=p[1]) for p in points],
            edges=edges
        )

    def build_back_bodice(self) -> Panel2DGeometry:
        """
        Builds back upper bodice panel.
        Origin (0,0) is at the center back waist.
        Neck drop is shallower (4.0 cm vs 12.0 cm) as typical for crew necks.
        """
        h = self.bodice_len_back
        half_waist = self.w_waist / 2.0
        half_bust = self.w_bust / 2.0
        half_shoulder = self.shoulder_w / 2.0

        neck_drop = 4.0  # Shallower back neckline
        neck_half_w = 9.0
        armhole_drop = 18.0

        points: List[Tuple[float, float]] = []
        edges: Dict[str, List[int]] = {}

        # 1. Waist seam
        idx_waist_start = len(points)
        points.append((0.0, 0.0))
        points.append((half_waist, 0.0))
        idx_waist_end = len(points) - 1
        edges["waist_right"] = [idx_waist_start, idx_waist_end]

        # 2. Right side seam
        idx_side_start = len(points) - 1
        underarm_r = (half_bust, h - armhole_drop)
        points.append(underarm_r)
        idx_side_end = len(points) - 1
        edges["side_seam_right"] = [idx_side_start, idx_side_end]

        # 3. Right armhole
        idx_armhole_r_start = len(points) - 1
        shoulder_outer_r = (half_shoulder, h - 2.0)
        arm_ctrl_r = (half_bust * 0.88, h - armhole_drop * 0.5)
        arm_pts_r = self._sample_bezier_curve(underarm_r, arm_ctrl_r, shoulder_outer_r, num_pts=8)[1:]
        for p in arm_pts_r:
            points.append(p)
        idx_armhole_r_end = len(points) - 1
        edges["armhole_right"] = [idx_armhole_r_start, idx_armhole_r_end]

        # 4. Right shoulder seam
        idx_shoulder_r_start = len(points) - 1
        shoulder_inner_r = (neck_half_w, h)
        points.append(shoulder_inner_r)
        idx_shoulder_r_end = len(points) - 1
        edges["shoulder_right"] = [idx_shoulder_r_start, idx_shoulder_r_end]

        # 5. Back neckline (shallower curve)
        idx_neck_start = len(points) - 1
        neck_center = (0.0, h - neck_drop)
        shoulder_inner_l = (-neck_half_w, h)
        pts_neck1 = self._sample_bezier_curve(shoulder_inner_r, (neck_half_w * 0.5, h - neck_drop * 0.8), neck_center, num_pts=7)[1:]
        pts_neck2 = self._sample_bezier_curve(neck_center, (-neck_half_w * 0.5, h - neck_drop * 0.8), shoulder_inner_l, num_pts=7)[1:]
        for p in pts_neck1 + pts_neck2:
            points.append(p)
        idx_neck_end = len(points) - 1
        edges["neckline"] = [idx_neck_start, idx_neck_end]

        # 6. Left shoulder seam
        idx_shoulder_l_start = len(points) - 1
        shoulder_outer_l = (-half_shoulder, h - 2.0)
        points.append(shoulder_outer_l)
        idx_shoulder_l_end = len(points) - 1
        edges["shoulder_left"] = [idx_shoulder_l_start, idx_shoulder_l_end]

        # 7. Left armhole
        idx_armhole_l_start = len(points) - 1
        underarm_l = (-half_bust, h - armhole_drop)
        arm_ctrl_l = (-half_bust * 0.88, h - armhole_drop * 0.5)
        arm_pts_l = self._sample_bezier_curve(shoulder_outer_l, arm_ctrl_l, underarm_l, num_pts=8)[1:]
        for p in arm_pts_l:
            points.append(p)
        idx_armhole_l_end = len(points) - 1
        edges["armhole_left"] = [idx_armhole_l_start, idx_armhole_l_end]

        # 8. Left side seam
        idx_side_l_start = len(points) - 1
        points.append((-half_waist, 0.0))
        idx_side_l_end = len(points) - 1
        edges["side_seam_left"] = [idx_side_l_start, idx_side_l_end]

        # 9. Left waist
        idx_waist_l_start = len(points) - 1
        edges["waist_left"] = [idx_waist_l_start, 0]

        poly = Polygon(points)
        bounds = poly.bounds
        w = round(bounds[2] - bounds[0], 2)
        ht = round(bounds[3] - bounds[1], 2)

        return Panel2DGeometry(
            panel_id="back_bodice",
            panel_name="Back Upper Panel",
            side="back",
            category="bodice",
            width_cm=w,
            height_cm=ht,
            area_sq_cm=round(poly.area, 2),
            perimeter_cm=round(poly.length, 2),
            contour_points=[BoundaryPoint2D(x=p[0], y=p[1]) for p in points],
            edges=edges
        )

    def build_front_skirt(self) -> Panel2DGeometry:
        """
        Builds front lower skirt panel.
        Origin (0,0) is at center top waist.
        Y extends downward (negative Y) to hem: y = -skirt_len_front.
        """
        h = self.skirt_len_front
        half_waist = self.w_waist / 2.0
        half_hip = self.w_hip / 2.0
        half_hem = self.w_hem / 2.0

        points: List[Tuple[float, float]] = []
        edges: Dict[str, List[int]] = {}

        # 1. Top waist seam (center waist to right waist)
        points.append((0.0, 0.0))
        points.append((half_waist, 0.0))
        edges["waist_top_right"] = [0, 1]

        # 2. Right side skirt seam (waist -> hip curve -> hem)
        hip_y = -round(h * 0.35, 2)
        points.append((half_hip, hip_y))
        points.append((half_hem, -h))
        edges["skirt_side_right"] = [1, 3]

        # 3. Bottom hem seam (right hem to center hem to left hem)
        points.append((0.0, -h - 1.0))  # subtle bottom hem curve
        points.append((-half_hem, -h))
        edges["hem"] = [3, 5]

        # 4. Left side skirt seam (left hem -> hip curve -> left waist)
        points.append((-half_hip, hip_y))
        points.append((-half_waist, 0.0))
        edges["skirt_side_left"] = [5, 7]

        # 5. Top left waist seam back to center
        edges["waist_top_left"] = [7, 0]

        poly = Polygon(points)
        bounds = poly.bounds
        w = round(bounds[2] - bounds[0], 2)
        ht = round(bounds[3] - bounds[1], 2)

        return Panel2DGeometry(
            panel_id="front_skirt",
            panel_name="Front Lower Panel",
            side="front",
            category="skirt",
            width_cm=w,
            height_cm=ht,
            area_sq_cm=round(poly.area, 2),
            perimeter_cm=round(poly.length, 2),
            contour_points=[BoundaryPoint2D(x=p[0], y=p[1]) for p in points],
            edges=edges
        )

    def build_back_skirt(self) -> Panel2DGeometry:
        """
        Builds back lower skirt panel.
        Matches front skirt width with back-specific length.
        """
        h = self.skirt_len_back
        half_waist = self.w_waist / 2.0
        half_hip = self.w_hip / 2.0
        half_hem = self.w_hem / 2.0

        points: List[Tuple[float, float]] = []
        edges: Dict[str, List[int]] = {}

        # 1. Top waist seam
        points.append((0.0, 0.0))
        points.append((half_waist, 0.0))
        edges["waist_top_right"] = [0, 1]

        # 2. Right side skirt seam
        hip_y = -round(h * 0.35, 2)
        points.append((half_hip, hip_y))
        points.append((half_hem, -h))
        edges["skirt_side_right"] = [1, 3]

        # 3. Bottom hem seam
        points.append((0.0, -h - 1.0))
        points.append((-half_hem, -h))
        edges["hem"] = [3, 5]

        # 4. Left side skirt seam
        points.append((-half_hip, hip_y))
        points.append((-half_waist, 0.0))
        edges["skirt_side_left"] = [5, 7]

        # 5. Top left waist seam
        edges["waist_top_left"] = [7, 0]

        poly = Polygon(points)
        bounds = poly.bounds
        w = round(bounds[2] - bounds[0], 2)
        ht = round(bounds[3] - bounds[1], 2)

        return Panel2DGeometry(
            panel_id="back_skirt",
            panel_name="Back Lower Panel",
            side="back",
            category="skirt",
            width_cm=w,
            height_cm=ht,
            area_sq_cm=round(poly.area, 2),
            perimeter_cm=round(poly.length, 2),
            contour_points=[BoundaryPoint2D(x=p[0], y=p[1]) for p in points],
            edges=edges
        )

    def generate_all_panels(self) -> Dict[str, Panel2DGeometry]:
        """Generates all 4 parametric garment panels."""
        return {
            "front_bodice": self.build_front_bodice(),
            "back_bodice": self.build_back_bodice(),
            "front_skirt": self.build_front_skirt(),
            "back_skirt": self.build_back_skirt()
        }
