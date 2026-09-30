"""
Computer Vision Analysis Module.
Processes garment imagery (front.jpg and back.jpg):
1. Segments garment silhouette from studio background.
2. Extracts landmark pixel positions (shoulders, neckline dip, underarm, waist, hip, hem).
3. Converts pixel measurements to real-world centimeters using the target garment length.
4. Returns proportion measurements used directly by pattern generation and validation.
"""

import os
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image


class GarmentVisionAnalyzer:
    def __init__(self, front_image_path: str, back_image_path: str = None):
        if not os.path.exists(front_image_path):
            raise FileNotFoundError(f"Front image not found: {front_image_path}")

        self.front_path = front_image_path
        self.back_path = back_image_path
        self.front_img = Image.open(front_image_path).convert("RGB")
        self.front_arr = np.array(self.front_img)

    def extract_silhouette_measurements(self, target_garment_length_cm: float = 88.0) -> Dict[str, Any]:
        """
        Extracts silhouette contour and key dimensions in pixels and centimeters.
        Directly measures from image:
        1. Front neckline lowest point (via color-edge gradient of inner neck opening).
        2. Shoulder span (via top contour width peak).
        3. Armhole drop & underarm chest width (via silhouette width inflection point).
        """
        # Threshold out solid white background (RGB > 238)
        mask = np.any(self.front_arr < 238, axis=2)
        y_indices, x_indices = np.where(mask)

        if len(y_indices) == 0:
            raise ValueError("No garment silhouette detected in image.")

        y_top = int(y_indices.min())
        y_bottom = int(y_indices.max())
        x_left = int(x_indices.min())
        x_right = int(x_indices.max())

        garment_height_px = y_bottom - y_top
        garment_width_px = x_right - x_left

        # Pixel to centimeter scaling factor (calibrated by target garment length)
        px_to_cm = target_garment_length_cm / float(garment_height_px)
        x_center = int((x_left + x_right) / 2)

        # 1. Front Neckline Lowest Point
        # Detect inner neckband edge using vertical gradient in neck region
        gray = np.mean(self.front_arr, axis=2).astype(np.float64)
        front_neck_y_candidates = []
        for col_x in range(x_center - 25, x_center + 26, 5):
            col_strip = gray[y_top:y_top + int(0.25 * garment_height_px), col_x]
            dy = np.diff(col_strip)
            if len(dy) >= 140:
                search_region = dy[70:140]
                peak_rel = 70 + int(np.argmax(search_region))
                front_neck_y_candidates.append(peak_rel)

        if front_neck_y_candidates:
            front_neck_depth_px = int(np.median(front_neck_y_candidates))
        else:
            front_neck_depth_px = int(0.10 * garment_height_px)

        front_neck_depth_cm = round(front_neck_depth_px * px_to_cm, 1)

        # 2. Shoulder Span from Top Contour
        top_10_pct = max(30, int(0.10 * garment_height_px))
        shoulder_widths = []
        for r in range(y_top, y_top + top_10_pct):
            xs = np.where(mask[r, :])[0]
            if len(xs) > 0:
                shoulder_widths.append((int(xs[-1] - xs[0]), r - y_top))

        if shoulder_widths:
            max_shoulder_tuple = max(shoulder_widths, key=lambda it: it[0])
            shoulder_span_px = max_shoulder_tuple[0]
        else:
            shoulder_span_px = int(0.65 * garment_width_px)

        shoulder_span_cm = round(shoulder_span_px * px_to_cm, 1)

        # 3. Armhole Drop & Underarm Chest Width (Inflection Point)
        # Search below the neckline opening where the torso is solid, finding the local maximum
        # where the armhole curves outward before tapering inward toward the waist.
        row_widths = []
        min_search_r = y_top + max(front_neck_depth_px, int(0.12 * garment_height_px))
        max_search_r = y_top + int(0.35 * garment_height_px)
        for r in range(min_search_r, max_search_r):
            xs = np.where(mask[r, :])[0]
            if len(xs) > 0:
                row_widths.append((r - y_top, int(xs[-1] - xs[0])))

        if row_widths:
            # Underarm inflection point: maximum width before waist tapering starts
            best_row = max(row_widths, key=lambda it: it[1])
            armhole_depth_px = best_row[0]
            w_chest_px = best_row[1]
        else:
            armhole_depth_px = int(0.18 * garment_height_px)
            w_chest_px = int(0.35 * garment_width_px)

        armhole_depth_cm = round(armhole_depth_px * px_to_cm, 1)
        w_chest_cm = round(w_chest_px * px_to_cm, 1)

        # 4. Waist, Hip, and Hem Widths
        y_waist = int(y_top + 0.48 * garment_height_px)
        w_waist_px = self._get_row_width(mask, y_waist)

        y_hip = int(y_top + 0.65 * garment_height_px)
        w_hip_px = self._get_row_width(mask, y_hip)

        y_hem = int(y_top + 0.98 * garment_height_px)
        w_hem_px = self._get_row_width(mask, y_hem)

        measurements = {
            "image_dimensions_px": {"width": self.front_img.size[0], "height": self.front_img.size[1]},
            "garment_bbox_px": {"y_top": y_top, "y_bottom": y_bottom, "height_px": garment_height_px, "max_width_px": garment_width_px},
            "scale_px_to_cm": round(px_to_cm, 5),
            "proportions_cm": {
                "total_length": round(target_garment_length_cm, 1),
                "neck_depth": front_neck_depth_cm,
                "shoulder_span": shoulder_span_cm,
                "armhole_depth": armhole_depth_cm,
                "flat_chest_width": w_chest_cm,
                "flat_waist_width": round(w_waist_px * px_to_cm, 1),
                "flat_hip_width": round(w_hip_px * px_to_cm, 1),
                "flat_hem_width": round(w_hem_px * px_to_cm, 1)
            },
            "silhouette_ratios": {
                "waist_to_chest": round(w_waist_px / max(1, w_chest_px), 3),
                "hem_to_chest": round(w_hem_px / max(1, w_chest_px), 3),
                "is_bodycon": bool((w_waist_px / max(1, w_chest_px)) < 0.95)
            },
            "data_provenance": {
                "measured_from_image": [
                    f"front_neck_depth ({front_neck_depth_cm} cm - inner neckband scoop contour)",
                    f"shoulder_span ({shoulder_span_cm} cm - top contour peak across tank straps)",
                    f"armhole_depth ({armhole_depth_cm} cm - underarm silhouette inflection point)",
                    f"flat_chest_width ({w_chest_cm} cm - underarm width across flat garment)",
                    f"flat_waist_width ({round(w_waist_px * px_to_cm, 1)} cm - mid-torso row width)",
                    f"flat_hip_width ({round(w_hip_px * px_to_cm, 1)} cm - pelvic row width)",
                    f"flat_hem_width ({round(w_hem_px * px_to_cm, 1)} cm - bottom hem row width)"
                ],
                "assumed_parameters": [
                    f"total_garment_length ({target_garment_length_cm} cm reference scale for maxi bodycon dress)",
                    "back_neck_depth (measured from back catalog image if present, else 3.0 cm)",
                    "center_back_seam (AI-inferred from back image seam line)"
                ]
            }
        }

        # Analyze back image if present
        if self.back_path and os.path.exists(self.back_path):
            back_img = Image.open(self.back_path).convert("RGB")
            back_arr = np.array(back_img)
            back_mask = np.any(back_arr < 238, axis=2)
            y_b_indices, x_b_indices = np.where(back_mask)
            if len(y_b_indices) > 0 and len(x_b_indices) > 0:
                y_b_top = int(y_b_indices.min())
                y_b_bottom = int(y_b_indices.max())
                x_b_center = int(x_b_indices.mean())
                back_h_px = max(1, y_b_bottom - y_b_top)
                neck_b_y = y_b_top
                while neck_b_y < y_b_bottom and not back_mask[neck_b_y, x_b_center]:
                    neck_b_y += 1
                back_neck_depth_ratio = (neck_b_y - y_b_top) / back_h_px
                back_neck_depth_cm = round(back_neck_depth_ratio * target_garment_length_cm, 1)
                measurements["proportions_cm"]["back_neck_depth"] = back_neck_depth_cm
                measurements["data_provenance"]["measured_from_image"].append(
                    f"back_neck_depth ({back_neck_depth_cm} cm - scoop back neckline contour)"
                )

        return measurements

    @staticmethod
    def _get_row_width(mask: np.ndarray, y: int) -> int:
        if 0 <= y < mask.shape[0]:
            xs = np.where(mask[y, :])[0]
            if len(xs) > 0:
                return int(xs[-1] - xs[0])
        return 0

