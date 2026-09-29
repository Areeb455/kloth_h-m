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
        """
        # Threshold out solid white background (RGB > 240)
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

        # Pixel to centimeter scaling factor
        px_to_cm = target_garment_length_cm / float(garment_height_px)

        # 1. Measure top shoulder height & neckline dip
        # Shoulder outer tops are at y_top
        # Find neckline center dip: scan central vertical line from y_top down
        x_center = int((x_left + x_right) / 2)
        neck_y = y_top
        while neck_y < y_bottom and not mask[neck_y, x_center]:
            neck_y += 1
        neck_depth_px = max(20, neck_y - y_top)

        # 2. Measure widths at key landmark proportions along garment height
        # Underarm / Chest (~28% down)
        y_chest = int(y_top + 0.28 * garment_height_px)
        w_chest_px = self._get_row_width(mask, y_chest)

        # Waist (~48% down)
        y_waist = int(y_top + 0.48 * garment_height_px)
        w_waist_px = self._get_row_width(mask, y_waist)

        # Hip (~65% down)
        y_hip = int(y_top + 0.65 * garment_height_px)
        w_hip_px = self._get_row_width(mask, y_hip)

        # Hem (~98% down)
        y_hem = int(y_top + 0.98 * garment_height_px)
        w_hem_px = self._get_row_width(mask, y_hem)

        # Armhole depth in pixels = y_chest - y_top
        armhole_depth_px = y_chest - y_top

        # Convert to centimeters
        measurements = {
            "image_dimensions_px": {"width": self.front_img.size[0], "height": self.front_img.size[1]},
            "garment_bbox_px": {"y_top": y_top, "y_bottom": y_bottom, "height_px": garment_height_px, "max_width_px": garment_width_px},
            "scale_px_to_cm": round(px_to_cm, 5),
            "proportions_cm": {
                "total_length": round(target_garment_length_cm, 1),
                "neck_depth": round(neck_depth_px * px_to_cm, 1),
                "armhole_depth": round(armhole_depth_px * px_to_cm, 1),
                "flat_chest_width": round(w_chest_px * px_to_cm, 1),
                "flat_waist_width": round(w_waist_px * px_to_cm, 1),
                "flat_hip_width": round(w_hip_px * px_to_cm, 1),
                "flat_hem_width": round(w_hem_px * px_to_cm, 1),
                "shoulder_span": round(w_chest_px * 0.78 * px_to_cm, 1)
            },
            "silhouette_ratios": {
                "waist_to_chest": round(w_waist_px / max(1, w_chest_px), 3),
                "hem_to_chest": round(w_hem_px / max(1, w_chest_px), 3),
                "is_straight_shift": bool(0.95 <= (w_waist_px / max(1, w_chest_px)) <= 1.05)
            }
        }

        # Analyze back image if present
        if self.back_path and os.path.exists(self.back_path):
            back_img = Image.open(self.back_path).convert("RGB")
            back_arr = np.array(back_img)
            back_mask = np.any(back_arr < 238, axis=2)
            y_b_indices, _ = np.where(back_mask)
            if len(y_b_indices) > 0:
                y_b_top = int(y_b_indices.min())
                neck_b_y = y_b_top
                while neck_b_y < y_b_top + 200 and not back_mask[neck_b_y, x_center]:
                    neck_b_y += 1
                back_neck_depth_px = max(10, neck_b_y - y_b_top)
                measurements["proportions_cm"]["back_neck_depth"] = round(back_neck_depth_px * px_to_cm, 1)

        return measurements

    @staticmethod
    def _get_row_width(mask: np.ndarray, y: int) -> int:
        if 0 <= y < mask.shape[0]:
            xs = np.where(mask[y, :])[0]
            if len(xs) > 0:
                return int(xs[-1] - xs[0])
        return 0
