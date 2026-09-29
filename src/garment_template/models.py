"""
Data models for the 3D Garment Template Generator.
Covers all 9 required data categories from the Kloth assignment specification.
"""

from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Category 1: Original 2D pattern geometry
# -------------------------------------------------------------
class BoundaryPoint2D(BaseModel):
    x: float = Field(..., description="X coordinate in cm")
    y: float = Field(..., description="Y coordinate in cm")


class Panel2DGeometry(BaseModel):
    panel_id: str
    panel_name: str
    side: str = Field(..., description="'front' or 'back'")
    category: str = Field(..., description="'bodice', 'skirt', etc.")
    width_cm: float
    height_cm: float
    area_sq_cm: float
    perimeter_cm: float
    contour_points: List[BoundaryPoint2D]
    edges: Dict[str, List[int]] = Field(
        default_factory=dict,
        description="Named edge segments mapped to contour point index slices"
    )


# -------------------------------------------------------------
# Category 2: Triangle mesh
# -------------------------------------------------------------
class VertexCorrespondence(BaseModel):
    vertex_id: int
    point_2d: Tuple[float, float] = Field(..., description="(x, y) in cm")
    uv: Tuple[float, float] = Field(..., description="(u, v) normalized [0, 1]")
    point_3d: Tuple[float, float, float] = Field(..., description="(x, y, z) in meters or cm")


class PanelMesh(BaseModel):
    panel_id: str
    vertex_count: int
    face_count: int
    vertices_2d: List[Tuple[float, float]]
    vertices_3d: List[Tuple[float, float, float]]
    faces: List[Tuple[int, int, int]]
    uvs: List[Tuple[float, float]]


# -------------------------------------------------------------
# Category 3: Saved 3D garment positions
# -------------------------------------------------------------
class PlacedPanel3D(BaseModel):
    panel_id: str
    center_3d: Tuple[float, float, float]
    bounding_box_min: Tuple[float, float, float]
    bounding_box_max: Tuple[float, float, float]
    initial_arrangement: str = Field(
        ...,
        description="Preserved arrangement description (e.g. 'front_torso_wrap', 'back_torso_wrap')"
    )


# -------------------------------------------------------------
# Category 4: Sewing connections
# -------------------------------------------------------------
class SewingConnection(BaseModel):
    seam_id: str
    panel_a_id: str
    edge_a_name: str
    edge_a_vertex_indices: List[int]
    edge_a_length_cm: float

    panel_b_id: str
    edge_b_name: str
    edge_b_vertex_indices: List[int]
    edge_b_length_cm: float

    seam_order: int
    gather_ratio: float = Field(
        1.0,
        description="Ratio of edge_a_length / edge_b_length (1.0 for flat seams, >1.0 for gathered)"
    )
    is_valid: bool = True
    tolerance_cm: float = 0.5


# -------------------------------------------------------------
# Category 5: Fabric assignment and properties
# -------------------------------------------------------------
class FabricAssignment(BaseModel):
    panel_id: str
    material_name: str
    stretch_warp_percent: float
    stretch_weft_percent: float
    bending_stiffness_Nm: float
    shear_stiffness_N_m: float
    weight_gsm: float
    density_kg_m3: float
    source: str = Field(..., description="'default' or 'estimated'")


# -------------------------------------------------------------
# Category 6: Fabric direction
# -------------------------------------------------------------
class FabricDirection(BaseModel):
    panel_id: str
    grainline_angle_deg: float = Field(0.0, description="Angle in degrees relative to vertical (Y axis)")
    grainline_vector: Tuple[float, float] = Field((0.0, 1.0), description="2D unit vector for grainline")
    warp_stretch_along_grain: float
    weft_stretch_across_grain: float
    source: str = Field(..., description="'default' or 'estimated'")


# -------------------------------------------------------------
# Category 7: Original mannequin mesh and skeleton
# -------------------------------------------------------------
class SkeletonJoint(BaseModel):
    joint_index: int
    name: str
    parent_index: Optional[int]
    local_matrix: List[float] = Field(..., description="16-element 4x4 matrix")


class MannequinRef(BaseModel):
    mesh_filename: str
    format: str = "glb"
    vertex_count: int
    face_count: int
    height_cm: float
    joint_count: int
    joints: List[SkeletonJoint]
    reference_source: str = "Kloth provided SMPL-X female avatar (person_0.glb)"


# -------------------------------------------------------------
# Category 8: Size labels, grading information and alternate meshes
# -------------------------------------------------------------
class SizeDeltas(BaseModel):
    bust_delta_cm: float
    waist_delta_cm: float
    hip_delta_cm: float
    hem_delta_cm: float
    length_delta_cm: float


class SizeMeshRef(BaseModel):
    size_label: str
    is_base_size: bool
    dimensions_cm: Dict[str, float]
    deltas_from_base: SizeDeltas
    mesh_obj_filename: str
    vertex_count: int
    face_count: int


class GradingInfo(BaseModel):
    base_size: str
    supported_sizes: List[str]
    size_meshes: Dict[str, SizeMeshRef]


# -------------------------------------------------------------
# Category 9: Visibility and material transparency
# -------------------------------------------------------------
class PanelMaterialSettings(BaseModel):
    panel_id: str
    visible: bool = True
    opacity: float = Field(1.0, ge=0.0, le=1.0)
    alpha_mode: str = "OPAQUE"


# -------------------------------------------------------------
# Master Package Manifest
# -------------------------------------------------------------
class TemplateManifest(BaseModel):
    schema_version: str = "1.0.0"
    garment_name: str
    brand: str
    category: str
    base_size: str
    supported_sizes: List[str]
    created_at: str

    category_1_patterns_file: str = "patterns_2d.json"
    category_2_meshes_file: str = "meshes_panels.json"
    category_3_placement_file: str = "placement_3d.json"
    category_4_sewing_file: str = "sewing_connections.json"
    category_5_fabric_file: str = "fabric_properties.json"
    category_6_direction_file: str = "fabric_direction.json"
    category_7_mannequin_file: str = "mannequin_skeleton.json"
    category_8_grading_file: str = "grading_sizes.json"
    category_9_visibility_file: str = "visibility_settings.json"

    mannequin_mesh_file: str = "mannequin.glb"
    base_garment_obj_file: str = "garment_base_XS.obj"
