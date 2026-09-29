"""
Fabric, Direction and Material Properties Module.
Implements:
- Category 5: Fabric assignment and properties (stretch, bending, weight gsm)
- Category 6: Fabric direction (grainline vector, warp/weft stretch)
- Category 9: Visibility and material transparency
"""

from typing import Dict, List
from .models import FabricAssignment, FabricDirection, PanelMaterialSettings


class FabricManager:
    def __init__(self, fabric_specs: Dict = None):
        # Default or estimated single jersey knit specs (95% cotton / 5% elastane)
        self.specs = fabric_specs or {
            "material_name": "Cotton Single Jersey 95/5",
            "weight_gsm": 180.0,
            "density_kg_m3": 450.0,
            "stretch_warp_percent": 15.0,  # stretch along vertical grain
            "stretch_weft_percent": 28.0,  # cross-grain stretch across body
            "bending_stiffness_Nm": 0.045,
            "shear_stiffness_N_m": 0.065,
            "source": "estimated"
        }

    def get_fabric_assignments(self, panel_ids: List[str]) -> Dict[str, FabricAssignment]:
        """Category 5: Fabric assignment per panel."""
        mat_name = self.specs.get("material_name") or self.specs.get("fabric_type", "Cotton Single Jersey 95/5")
        assignments = {}
        for pid in panel_ids:
            assignments[pid] = FabricAssignment(
                panel_id=pid,
                material_name=mat_name,
                stretch_warp_percent=self.specs["stretch_warp_percent"],
                stretch_weft_percent=self.specs["stretch_weft_percent"],
                bending_stiffness_Nm=self.specs["bending_stiffness_Nm"],
                shear_stiffness_N_m=self.specs["shear_stiffness_N_m"],
                weight_gsm=self.specs["weight_gsm"],
                density_kg_m3=self.specs["density_kg_m3"],
                source=self.specs.get("source", self.specs.get("status", "estimated"))
            )
        return assignments

    def get_fabric_directions(self, panel_ids: List[str]) -> Dict[str, FabricDirection]:
        """
        Category 6: Fabric grainline direction per panel.
        Standard vertical grainline (0 deg, vector [0, 1]) parallel to spine / center front.
        """
        directions = {}
        for pid in panel_ids:
            directions[pid] = FabricDirection(
                panel_id=pid,
                grainline_angle_deg=0.0,
                grainline_vector=(0.0, 1.0),
                warp_stretch_along_grain=self.specs["stretch_warp_percent"],
                weft_stretch_across_grain=self.specs["stretch_weft_percent"],
                source="default"
            )
        return directions

    def get_visibility_settings(self, panel_ids: List[str]) -> Dict[str, PanelMaterialSettings]:
        """Category 9: Visibility and material transparency."""
        settings = {}
        for pid in panel_ids:
            settings[pid] = PanelMaterialSettings(
                panel_id=pid,
                visible=True,
                opacity=1.0,
                alpha_mode="OPAQUE"
            )
        return settings
