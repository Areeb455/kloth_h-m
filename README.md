# 3D Garment Template Generator (`Kloth`)

A parametric 3D garment template generator that translates garment imagery and size charts into a standardized, inspection-ready 3D garment template package covering all **nine required data categories**, accompanied by a Position-Based Dynamics (PBD) 3D cloth simulation engine, an automated validation suite, round-trip reader, and interactive 3D WebGL inspection viewer.

---

## Architecture Overview

```
                                      +-------------------------------+
                                      |   Garment Inputs              |
                                      | - Front Image (Studio Flat)   |
                                      | - Back Image (AI Inferred)    |
                                      | - H&M Size Chart JSON (XXS-S) |
                                      +---------------+---------------+
                                                      |
                                                      v
+-----------------------------+       +---------------+---------------+
|  Mannequin / Avatar Asset   |       |  Computer Vision Analysis     |
|  - SMPL-X GLB Mesh          | ----> |  - Color-Edge Neckline Dip    |
|  - 52 Skeletal Joints       |       |  - Pixel-to-CM Scaling        |
|  - Real Torso Cross-Sections|       |  - Inflection Armhole/Chest   |
+-----------------------------+       +---------------+---------------+
               |                                      |
               v                                      v
+-----------------------------+       +---------------+---------------+
| Sizing & Ease Engine        | ----> | 2D Parametric Patterns        |
| - Lower-Bound Range Rule    |       | - 3 Continuous Shift Panels   |
| - Body Ease (+4cm / +6cm)   |       | - Unstretched cm Boundaries   |
+-----------------------------+       +---------------+---------------+
                                                      |
                                                      v
                                      +---------------+---------------+
                                      | Tessellation & Meshing        |
                                      | - Delaunay Triangulation      |
                                      | - Non-degenerate Triangles    |
                                      | - UV Texture Coordinates      |
                                      +---------------+---------------+
                                                      |
                                                      v
                                      +---------------+---------------+
                                      | 3D Torso-Aware Placement      |
                                      | - Conformal Cylindrical Wrap  |
                                      | - Positive Air Clearance      |
                                      | - Zero Avatar Penetration     |
                                      +---------------+---------------+
                                                      |
                                                      v
                                      +---------------+---------------+
                                      | Assembly & Sewing Engine      |
                                      | - 5 Paired Seams (Center Back)|
                                      | - 1:1 Vertex Resampling       |
                                      | - Explicit Gather Ratios      |
                                      +---------------+---------------+
                                                      |
                                                      v
                                      +---------------+---------------+
                                      | 3D PBD Cloth Simulation       |
                                      | - Distance & Bending Consts   |
                                      | - Seam Closure (< 5mm gap)    |
                                      | - Torso Collision Projection  |
                                      | - Mass from 180 GSM Fabric    |
                                      +---------------+---------------+
                                                      |
                                                      v
                                      +---------------+---------------+
                                      | Multi-Size Mesh Grading       |
                                      | - XS (Base), XXS, S           |
                                      | - Alternate OBJ Meshes        |
                                      +---------------+---------------+
                                                      |
                                                      v
+-----------------------------------------------------+-----------------------------------------------+
|                                Standardized Output Package                                          |
| manifest.json | patterns_2d.json | meshes_panels.json | placement_3d.json | sewing_connections.json     |
| fabric_properties.json | fabric_direction.json | mannequin_skeleton.json | grading_sizes.json           |
| visibility_settings.json | mannequin.glb | garment_XXS.obj | garment_XS.obj | garment_S.obj                |
+-----------------------------------------------------+-----------------------------------------------+
                                                      |
                        +-----------------------------+-------------------------------+
                        |                                                             |
                        v                                                             v
        +---------------+---------------+                             +---------------+---------------+
        |    Round-Trip Package Loader  |                             |  Interactive WebGL Viewer UI  |
        |  - Strict Schema Validation   |                             |  - Dual 2D Canvas & 3D WebGL  |
        |  - 27 Non-Circular Checks     |                             |  - Dynamic Size Switcher      |
        |  - 20 pytest Unit Tests (PASS)|                             |  - Seam & Fit Monitor         |
        +-------------------------------+                             +-------------------------------+
```

---

## Quickstart

### 1. Requirements & Setup
The pipeline runs on Python 3.10+ (tested on Python 3.11 64-bit Windows & Linux).

```bash
git clone https://github.com/Areeb455/kloth_h-m.git
cd kloth_h-m
pip install -r requirements.txt
```

### 2. Run the Full End-to-End Pipeline
Executes CV silhouette extraction, sizing, pattern synthesis, triangulation, 3D placement, sewing pairing, 3D PBD cloth simulation, grading, export, and round-trip verification:
```bash
python run_pipeline.py
# or on Windows: py -3.11 run_pipeline.py
```

### 3. Run Automated Tests
Executes the test suite covering the full pipeline, simulation stability, seam gap < 5 mm, non-penetration, 1:1 seams, and invalid inputs:
```bash
pytest tests/ -v
# or on Windows: py -3.11 -m pytest tests/ -v
```

### 4. Launch Interactive WebGL Demo UI
Launches the dual 2D/3D inspection viewer with live size switching and seam tracking:
```bash
python run_demo.py
# or on Windows: py -3.11 run_demo.py
```
Open **[http://localhost:8000](http://localhost:8000)** in any modern web browser.

---

## 9-Category Status Matrix

| # | Required Data Category | Package Output File | Status | Implementation Details |
|---|---|---|---|---|
| **1** | **Original 2D pattern geometry** | `patterns_2d.json` | **Implemented** | Continuous full-length shift dress panels in cm (front panel, back left panel, back right panel) with boundary coordinate lists, width, height, surface area, and perimeter using Shapely. Guided by CV proportions. |
| **2** | **Triangle mesh** | `meshes_panels.json` | **Implemented** | Delaunay triangulation with 1:1 vertex correspondence between 2D flat coordinates `(x, y)` in cm, normalized UV coordinates `[0, 1]`, and initial 3D positions with counter-clockwise winding. |
| **3** | **Saved 3D garment positions** | `placement_3d.json` | **Implemented** | Conformal cylindrical wrapping around real avatar torso cross-sections ($Z > Z_{avatar}$ front, $Z < Z_{avatar}$ back) anchored to anatomical landmarks. Verified zero body penetration with positive air clearance. |
| **4** | **Sewing connections** | `sewing_connections.json` | **Implemented** | 5 paired seams (left/right shoulders, left/right full-length sides, and center-back seam). Vertices resampled 1:1, edge lengths computed in cm, and gather ratios explicitly recorded. |
| **5** | **Fabric assignment and properties** | `fabric_properties.json` | **Estimated** | Single jersey cotton knit (95% cotton, 5% elastane): stretch warp (15%), stretch weft (28%), bending stiffness ($0.045\text{ N}\cdot\text{m}$), shear stiffness ($0.065\text{ N/m}$), weight ($180\text{ gsm}$). |
| **6** | **Fabric direction** | `fabric_direction.json` | **Defaulted** | Standard vertical grainline ($0^\circ$, unit vector `[0.0, 1.0]`) parallel to the spine/center front, distinguishing warp stretch along grain vs weft stretch across grain. |
| **7** | **Original mannequin mesh & skeleton** | `mannequin.glb`, `mannequin_skeleton.json` | **Implemented** | Kloth-provided SMPL-X female avatar mesh (10,251 vertices, 18,764 faces) with full 52-joint skeletal hierarchy and local $4\times 4$ transform matrices. |
| **8** | **Size labels, grading & alternate meshes** | `grading_sizes.json`, `garment_{XXS,XS,S}.obj` | **Implemented** | 3 complete sizes from reviewer size chart: **XS** (primary base), **XXS**, and **S**. Includes exact delta metrics from base and individual Wavefront OBJ meshes. |
| **9** | **Visibility & material transparency** | `visibility_settings.json` | **Defaulted** | Per-panel visibility flags (`visible: true`), material opacity (`1.0`), and alpha blending mode (`OPAQUE`). |

---

## Data Provenance: Measured vs. Assumed Properties

| Property | Source / Category | Value (XS Base) | Methodology / Notes |
|---|---|---|---|
| **Front Neckline Depth** | **Measured (CV)** | **7.4 cm** | Extracted via inner collar color-edge gradient scan ($\text{Sobel } dy$) in `vision.py`. Distinguishes front scoop from back collar rim. |
| **Shoulder Span** | **Measured (CV)** | **30.8 cm** | Silhouette upper contour peak-to-peak horizontal span scaled by target garment height ($88.0\text{ cm}$). |
| **Armhole Depth** | **Measured (CV)** | **22.3 cm** | Detected at the inflection plateau where silhouette width transitions from armhole contour to vertical side seam. |
| **Flat Chest Width** | **Measured (CV)** | **36.8 cm** | Silhouette underarm horizontal width ($445\text{ px} \times 0.0827\text{ cm/px}$). |
| **Body Chest, Waist, Hip** | **Measured (Chart)** | **78.0 / 64.0 / 83.0 cm** | Lower bound of H&M size chart range (`78-82`, `64-66`, `83-87`) per assignment instructions. |
| **Bust Ease** | **Assumed (Ease)** | **+4.0 cm** | Standard ease allowance for jersey knit shift dress ($78.0 \to 82.0\text{ cm}$). |
| **Waist Ease** | **Assumed (Ease)** | **+6.0 cm** | Shift silhouette ease allowance ($64.0 \to 70.0\text{ cm}$). |
| **Hip Ease** | **Assumed (Ease)** | **+7.0 cm** | Shift silhouette ease allowance ($83.0 \to 90.0\text{ cm}$). |
| **Garment Front Length** | **Assumed** | **88.0 cm** | Standard above-knee length for regular women's shift dress (H&M chart omits garment length). |
| **Back Garment Length** | **Assumed** | **90.0 cm** | $+2.0\text{ cm}$ over front to accommodate dorsal thoracic curvature and buttocks volume. |
| **Back Image & Center Seam** | **AI-Inferred** | **N/A** | AI-generated back image (`back.jpg`) and center-back seam reflecting realistic 2-piece back construction. |

---

## Position-Based Dynamics (PBD) Cloth Simulation

Implemented in [`src/garment_template/simulation.py`](https://github.com/Areeb455/kloth_h-m/blob/main/src/garment_template/simulation.py):
1. **Unified Global Mesh**: Consolidates front and back panels into a shared PBD particle system.
2. **Structural Distance Constraints**: Rest lengths initialized from exact 2D pattern metric coordinates ($L_{rest} = \|p_{2d,a} - p_{2d,b}\| \times 0.01\text{ m}$).
3. **Bending Constraints**: Isometric bending constraints over adjacent triangle pairs.
4. **Rigid Seam Stitching**: Corresponding seam boundary vertices pulled to midpoint ($x_A \leftarrow x_{mid}, x_B \leftarrow x_{mid}$), achieving exact **$0.00\text{ mm}$** seam assembly gap (< 5 mm requirement).
5. **Vectorized Torso Collision**: Fast radial projection preventing avatar penetration across the 52-joint avatar body profile.
6. **Mass from GSM**: Nodal masses computed per triangle based on fabric areal density ($180\text{ g/m}^2$).
7. **Equilibrium Settling**: Kinetic energy decreases from initial drape to settled state ($KE < 0.0001\text{ J}$).
8. **Export**: Both initial wrapped arrangement (`garment_{SIZE}_initial.obj`) and simulated drape (`garment_{SIZE}.obj`) exported per size.

---

## Multi-Size Grading (XXS, XS, S)

In accordance with reviewer instructions, active sizes are strictly limited to **XXS, XS, and S** directly from the reviewer-provided H&M size chart screenshot:
* **XXS**: Chest 74 cm, Waist 62 cm, Low Hip 79 cm.
* **XS (Primary Base)**: Chest 78 cm, Waist 64 cm, Low Hip 83 cm.
* **S**: Chest 82 cm, Waist 68 cm, Low Hip 87 cm.

Individual 3D OBJ meshes for both initial placement and simulated drapes are generated for each size.

---

## Validation Suite & Automated Checks

The automated validation suite (`src/garment_template/validator.py`) runs 27 non-circular checks:

1. **3D Avatar Fit**:
   * 3D Simulated Chest Perimeter Ease: $+26.0\text{ cm}$ over 78 cm body -> **PASS**
2. **Computer Vision Proportions**:
   * Front Neckline Depth Match: Pattern $7.4\text{ cm}$ vs Vision $7.4\text{ cm}$ ($\Delta = 0.0\text{ cm} \le 1.5\text{ cm}$) -> **PASS**
   * Chest Width Consistency: Image-derived $36.8\text{ cm}$ vs Pattern $41.0\text{ cm}$ ($\Delta = 4.2\text{ cm} \le 5.0\text{ cm}$) -> **PASS**
3. **Cloth Simulation Quality**:
   * Seam Assembly Gap: Max $0.00\text{ mm}$ (< 5.0 mm threshold) -> **PASS**
   * Simulation Numerical Stability: Zero NaNs or Infs -> **PASS**
   * Equilibrium Settling: Kinetic energy settled, displacement < 1 mm -> **PASS**
4. **Mannequin Fit**:
   * Avatar Torso Non-Penetration: Zero body penetration verified across 402 torso vertices -> **PASS**
5. **Area Strain Preservation**:
   * front_panel: within elastic knit limit -> **PASS**
   * back_left_panel: within elastic knit limit -> **PASS**
   * back_right_panel: within elastic knit limit -> **PASS**
6. **Mesh Topology**:
   * Non-degenerate triangles across all panels -> **PASS**
   * Face indices valid and in-range -> **PASS**
7. **Sewing Integrity**:
   * 1:1 vertex count matching on all 5 seams -> **PASS**
   * Gather ratios within $[0.90, 1.10]$ -> **PASS**
   * No duplicate seam edges -> **PASS**

### Test Suite Execution Output
```
======================= 20 passed, 3 warnings in 12.24s =======================
```

---

## AI Tools Usage & Security Disclosure

* **Antigravity (Google DeepMind)**: Primary coding agent for designing pipeline architecture, PBD physics simulation, Shapely geometry math, and WebGL viewer.
* **Gemini Vision**: Used to analyze garment proportions and generate the matching back view flat-lay image.
* **Claude (Anthropic)**: Used for code review, critique, and verification of mathematical constraints.
* **Zero API Keys Committed**: All code and configurations run entirely locally. No API keys, credentials, or secrets are committed to git (`.gitignore` enforces exclusion of `.env`).
