"""
Sizing and Measurement Engine.
Parses the H&M size chart according to official assignment rules:
- Applies lower-bound range resolution (e.g. 78-82 -> 78).
- Distinguishes body measurements from garment dimensions.
- Applies garment ease allowances for jersey knitwear.
- Computes front/back length differentiation and grading deltas.
"""

import json
from typing import Dict, Any, List
from .models import SizeDeltas


class SizingEngine:
    def __init__(self, size_chart_path: str):
        with open(size_chart_path, "r") as f:
            self.raw_data = json.load(f)

        self.primary_base_size = self.raw_data.get("primary_base_size", "XS")
        self.supported_sizes = self.raw_data.get("supported_sizes", ["XXS", "XS", "S", "M"])
        self.sizes_data = self.raw_data["sizes"]
        self.ease_allowances = self.raw_data.get("ease_allowances_cm", {
            "bust_ease": 4.0,
            "waist_ease": 6.0,
            "hip_ease": 7.0
        })
        self.length_assumptions = self.raw_data.get("length_assumptions", {
            "back_vs_front_delta_cm": 2.0
        })

    @staticmethod
    def resolve_range_lower(value_str: str) -> float:
        """
        Assignment Rule: Use lower number wherever size chart gives a range.
        E.g. '78-82' -> 78.0, '32-34' -> 32.0, '71' -> 71.0
        """
        if isinstance(value_str, (int, float)):
            return float(value_str)
        cleaned = str(value_str).strip()
        if "-" in cleaned:
            parts = cleaned.split("-")
            return float(parts[0].strip())
        return float(cleaned)

    def get_garment_dimensions(self, size: str) -> Dict[str, float]:
        """
        Returns complete garment dimensions in cm for a specific size.
        """
        if size not in self.sizes_data:
            raise ValueError(f"Unknown size '{size}'. Available: {list(self.sizes_data.keys())}")

        size_entry = self.sizes_data[size]
        if "garment_dimensions_cm" in size_entry:
            dims = dict(size_entry["garment_dimensions_cm"])
        else:
            # Derive dynamically from body measurements + ease
            body = size_entry["body_measurements_cm"]
            chest = self.resolve_range_lower(body["chest"])
            waist = self.resolve_range_lower(body["waist"])
            hip = self.resolve_range_lower(body["low_hip"])

            bust_circ = chest + self.ease_allowances["bust_ease"]
            waist_circ = waist + self.ease_allowances["waist_ease"]
            hip_circ = hip + self.ease_allowances["hip_ease"]
            hem_circ = hip_circ * 1.22
            front_len = 88.0 + (size_entry.get("eur_size", 34) - 34) * 1.0
            back_len = front_len + self.length_assumptions["back_vs_front_delta_cm"]
            shoulder_w = 32.0 + (chest - 78.0) * 0.15

            dims = {
                "bust_circ": round(bust_circ, 1),
                "waist_circ": round(waist_circ, 1),
                "hip_circ": round(hip_circ, 1),
                "hem_circ": round(hem_circ, 1),
                "front_length": round(front_len, 1),
                "back_length": round(back_len, 1),
                "shoulder_width": round(shoulder_w, 1)
            }

        return dims

    def get_grading_deltas(self, target_size: str, base_size: str = None) -> SizeDeltas:
        """
        Computes the incremental deltas in cm from base_size to target_size.
        """
        base = base_size or self.primary_base_size
        base_dims = self.get_garment_dimensions(base)
        target_dims = self.get_garment_dimensions(target_size)

        return SizeDeltas(
            bust_delta_cm=round(target_dims["bust_circ"] - base_dims["bust_circ"], 2),
            waist_delta_cm=round(target_dims["waist_circ"] - base_dims["waist_circ"], 2),
            hip_delta_cm=round(target_dims["hip_circ"] - base_dims["hip_circ"], 2),
            hem_delta_cm=round(target_dims["hem_circ"] - base_dims["hem_circ"], 2),
            length_delta_cm=round(target_dims["front_length"] - base_dims["front_length"], 2)
        )
