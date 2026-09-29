# 3D Garment Template Generator (`Kloth`)

A parametric 3D garment template generator that translates garment imagery and size charts into a standardized, inspection-ready 3D garment template package covering all **nine required data categories**, accompanied by an automated validation suite, round-trip reader, and interactive 3D WebGL inspection viewer.

---

## Architecture Overview

```
                                      +-------------------------------+
                                      |   Garment Inputs              |
                                      | - Front Image (Studio Flat)   |
                                      | - Back Image (AI Inferred)    |
                                      | - H&M Size Chart JSON         |
                                      +---------------+---------------+
                                                      |
                                                      v
+-----------------------------+       +---------------+---------------+
|  Mannequin / Avatar Asset   |       |  Computer Vision Analysis     |
|  - SMPL-X GLB Mesh          | ----> |  - Silhouette Segmentation    |
|  - 52 Skeletal Joints       |       |  - Pixel-to-CM Scaling        |
|  - Real Torso Cross-Sections|       |  - Neck/Armhole/Shift Ratios  |
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
                                      | Multi-Size Mesh Grading       |
                                      | - XS (Base), XXS, S, M        |
                                      | - Alternate OBJ Meshes        |
                                      +---------------+---------------+
                                                      |
                                                      v
+-----------------------------------------------------+-----------------------------------------------+
|                                Standardized Output Package                                          |
| manifest.json | patterns_2d.json | meshes_panels.json | placement_3d.json | sewing_connections.json     |
| fabric_properties.json | fabric_direction.json | mannequin_skeleton.json | grading_sizes.json           |
| visibility_settings.json | mannequin.glb | garment_XXS.obj | garment_XS.obj | garment_S.obj | ...        |
+-----------------------------------------------------+-----------------------------------------------+
                                                      |
                        +-----------------------------+-------------------------------+
                        |                                                             |
                        v                                                             v
        +---------------+---------------+                             +---------------+---------------+
        |    Round-Trip Package Loader  |                             |  Interactive WebGL Viewer UI  |
        |  - Strict Schema Validation   |                             |  - Dual 2D Canvas & 3D WebGL  |
        |  - 25 Non-Circular Checks     |                             |  - Dynamic Size Switcher      |
        |  - 15 pytest Unit Tests (PASS)|                             |  - Seam & Fit Monitor         |
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
Executes CV silhouette extraction, sizing, pattern synthesis, triangulation, 3D placement, sewing pairing, grading, export, and round-trip verification:
```bash
python run_pipeline.py
# or on Windows: py -3.11 run_pipeline.py
```

### 3. Run Automated Tests
Executes the test suite covering the full pipeline, geometric tolerances, non-penetration, 1:1 seams, and invalid inputs:
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
| **3** | **Saved 3D garment positions** | `placement_3d.json` | **Implemented** | Conformal cylindrical wrapping around real avatar torso cross-sections ($Z > Z_{avatar}$ front, $Z < Z_{avatar}$ back) anchored to anatomical landmarks. Verified zero body penetration with $\ge 0.8\text{ cm}$ positive air clearance. |
| **4** | **Sewing connections** | `sewing_connections.json` | **Implemented** | 5 paired seams (left/right shoulders, left/right full-length sides, and center-back seam). Vertices resampled 1:1, edge lengths computed in cm, and gather ratios explicitly recorded. |
| **5** | **Fabric assignment and properties** | `fabric_properties.json` | **Estimated** | Single jersey cotton knit (95% cotton, 5% elastane): stretch warp (15%), stretch weft (28%), bending stiffness ($0.045\text{ N}\cdot\text{m}$), shear stiffness ($0.065\text{ N/m}$), weight ($180\text{ gsm}$). |
| **6** | **Fabric direction** | `fabric_direction.json` | **Defaulted** | Standard vertical grainline ($0^\circ$, unit vector `[0.0, 1.0]`) parallel to the spine/center front, distinguishing warp stretch along grain vs weft stretch across grain. |
| **7** | **Original mannequin mesh & skeleton** | `mannequin.glb`, `mannequin_skeleton.json` | **Implemented** | Kloth-provided SMPL-X female avatar mesh (10,251 vertices, 18,764 faces) with full 52-joint skeletal hierarchy and local $4\times 4$ transform matrices. |
| **8** | **Size labels, grading & alternate meshes** | `grading_sizes.json`, `garment_{XXS,XS,S,M}.obj` | **Implemented** | 4 complete sizes prepared: **XS** (primary base), **XXS**, **S**, and **M**. Includes exact delta metrics from base and individual Wavefront OBJ meshes. |
| **9** | **Visibility & material transparency** | `visibility_settings.json` | **Defaulted** | Per-panel visibility flags (`visible: true`), material opacity (`1.0`), and alpha blending mode (`OPAQUE`). |

---

## Garment Selection, Sizing & Assumptions

### 1. Garment Selection
Per the reviewer's instructions (*"Do not use the original reference garment. Choose any dress of your choice from the H&M dresses category"*), we selected the **H&M Sleeveless Jersey Shift Dress** (Reference: [H&M Product Page](https://www2.hm.com/en_in/productpage.1143896001.html)).
The dress is an above-knee, straight shift silhouette with sleeveless armholes, a scoop neckline, and a center-back seam.

### 2. Sizing Data Lineage
* **Sizes XXS, XS, and S**: Extracted directly from the reviewer-provided H&M size chart screenshot (`REGULAR XXS-S`, `samples/hm_size_chart.png`).
* **Size M**: Extrapolated from H&M standard women's regular size charts (Chest 90–98 cm, Waist 74–82 cm, Low Hip 95–102 cm).
* **Lower-Bound Rule**: Applied per the assignment specification (e.g. XS chest $78\text{--}82\text{ cm} \to 78.0\text{ cm}$).
* **Ease Allowances**: Because the H&M chart specifies body measurements, garment ease was added for relaxed single jersey wear:
  * Bust Ease: $+4.0\text{ cm}$ (Body $78\text{ cm} \to \text{Garment } 82\text{ cm}$)
  * Waist Ease: $+6.0\text{ cm}$ (Body $64\text{ cm} \to \text{Garment } 70\text{ cm}$)
  * Hip Ease: $+7.0\text{ cm}$ (Body $83\text{ cm} \to \text{Garment } 90\text{ cm}$)
  * Hem Flare: $\text{Hip} \times 1.22 \to 110.0\text{ cm}$
* **Length Assumptions**:
  * Front length: $88.0\text{ cm}$ for base size XS (an assumed length for an above-knee shift dress, as the H&M chart provides inside leg rather than garment length).
  * Back length: $90.0\text{ cm}$ ($+2.0\text{ cm}$ longer than front) to compensate for dorsal thoracic curvature.

### 3. Back Image Inference
Following the reviewer's guidelines, the back image (`samples/back.jpg`) was generated via Gemini vision matching the catalog lighting, sage-green jersey texture, and silhouette of `front.jpg`, incorporating a shallower crew neckline and a center-back seam.

---

## Computer Vision Silhouette Analysis

The `GarmentVisionAnalyzer` in [`src/garment_template/vision.py`](https://github.com/Areeb455/kloth_h-m/blob/main/src/garment_template/vision.py) processes `front.jpg`:
1. Segments the garment from the solid white studio background.
2. Extracts bounding dimensions in pixels ($1064\text{ px}$ height).
3. Establishes the pixel-to-cm ratio ($0.0827\text{ cm/px}$ for $88.0\text{ cm}$ target length).
4. Measures neckline dip ($2.9\text{ cm}$), armhole drop ($24.6\text{ cm}$), flat chest width ($37.6\text{ cm}$), and waist-to-chest ratio ($1.007$, confirming a straight shift silhouette).
These measurements directly parameterize the 2D pattern generation and are validated in the automated test suite.

---

## Mannequin Fit & Torso Non-Penetration

In [`src/garment_template/avatar.py`](https://github.com/Areeb455/kloth_h-m/blob/main/src/garment_template/avatar.py), the SMPL-X mannequin mesh is sliced at landmark heights to extract the true torso profile (excluding peripheral arm vertices):
* Chest ($Y=1.17\text{m}$): $Z \in [-0.185, 0.044\text{m}]$, Center $Z = -0.071\text{m}$
* Waist ($Y=1.00\text{m}$): $Z \in [-0.155, 0.087\text{m}]$, Center $Z = -0.034\text{m}$
* Hip ($Y=0.84\text{m}$): $Z \in [-0.183, 0.084\text{m}]$, Center $Z = -0.049\text{m}$

In [`src/garment_template/placement.py`](https://github.com/Areeb455/kloth_h-m/blob/main/src/garment_template/placement.py), panels are placed using an isometric cylindrical embedding ($s = R\theta$) centered on the avatar's real torso bounds. Front vertices are bounded at $Z \ge Z_{front} + 0.008\text{m}$ and back vertices at $Z \le Z_{back} - 0.008\text{m}$.
The validation suite inspects all 413 torso vertices and verifies zero mesh-body penetration with positive air clearance everywhere.

---

## Validation Suite & Test Results

The validation suite (`src/garment_template/validator.py`) runs 25 non-circular checks:

1. **Garment vs. Body Ease Checks**:
   * Bust ease: $+4.0\text{ cm}$ ($3.0 \le \Delta \le 6.0\text{ cm}$) -> **PASS**
   * Waist ease: $+6.0\text{ cm}$ ($4.0 \le \Delta \le 8.0\text{ cm}$) -> **PASS**
2. **Computer Vision Proportions**:
   * Image flat chest width ($37.6\text{ cm}$) vs. pattern flat chest ($41.0\text{ cm}$) delta $3.4\text{ cm} \le 4.0\text{ cm}$ -> **PASS**
   * Neckline scoop ratio: $2.9\text{ cm} \in [2.0, 12.0\text{ cm}]$ -> **PASS**
3. **Mannequin Fit**:
   * Zero body penetration verified across all 413 torso vertices (min clearance $+0.8\text{ cm}$) -> **PASS**
4. **3D vs. 2D Surface Area**:
   * Isometric strain ratio: $0.999 \in [0.90, 1.10]$ -> **PASS**
5. **Mesh Topology & Sewing**:
   * Face indices valid and in-range across all 3 panels -> **PASS**
   * 0 degenerate / zero-area triangles -> **PASS**
   * 1:1 vertex count matching on all 5 seams -> **PASS**
   * No duplicate seam edge usages -> **PASS**

### Pytest Execution Output
```
tests/test_invalid_inputs.py::test_unknown_size_raises_error PASSED      [  6%]
tests/test_invalid_inputs.py::test_missing_manifest_raises_error PASSED  [ 13%]
tests/test_invalid_inputs.py::test_nonexistent_package_path PASSED       [ 20%]
tests/test_invalid_inputs.py::test_malformed_size_chart_json PASSED      [ 26%]
tests/test_invalid_inputs.py::test_corrupt_or_truncated_image PASSED     [ 33%]
tests/test_invalid_inputs.py::test_corrupt_zip_package PASSED            [ 40%]
tests/test_invalid_inputs.py::test_negative_dimensions_rejected PASSED   [ 46%]
tests/test_invalid_inputs.py::test_range_lower_bound_parsing PASSED      [ 53%]
tests/test_pipeline.py::test_pipeline_runs_successfully PASSED           [ 60%]
tests/test_pipeline.py::test_roundtrip_load_from_directory PASSED        [ 66%]
tests/test_pipeline.py::test_roundtrip_load_from_zip PASSED              [ 73%]
tests/test_validation.py::test_2d_panel_polygons_valid PASSED            [ 80%]
tests/test_validation.py::test_mesh_has_no_degenerate_triangles PASSED   [ 86%]
tests/test_validation.py::test_sewing_connections_all_have_equal_vertices PASSED [ 93%]
tests/test_validation.py::test_no_duplicate_seams PASSED                 [100%]

============================= 15 passed in 5.38s ==============================
```

---

## Scope & Limitations

* **No Dynamic Physics Simulation**: No dynamic cloth simulation (mass-spring or finite-element physics with self-collision) is executed. The pipeline performs parametric CAD panel synthesis and isometric conformal placement around avatar landmarks in a pre-simulation starting arrangement with 1:1 paired seam vertices.
* **Garment Typology**: Optimized for continuous sleeveless/tank shift dresses, A-line skirts, and simple tunics without heavy gathering, ruffles, or structured interior corsetry.
* **Render Free-Tier Sleep**: On Render free tier, the web service spins down after inactivity. Accessing the URL takes ~50 seconds on cold start.

---

## AI Tools Usage Disclosure

* **Antigravity (Google DeepMind)**: Used as the primary pair-programming agent for designing the modular Python architecture, implementing the Shapely geometry math, writing test cases, and building the WebGL Three.js visualizer.
* **Gemini Vision**: Used to analyze the silhouette proportions of the H&M garment and generate the matching back studio flat-lay photograph.
* **Claude (Anthropic)**: Used during early reconnaissance to analyze the `.zprj` container schema and formulate the initial pipeline strategy.
* **Verification**: All mathematical models (isometric wrapping, cross-section clearance, Delaunay triangulation) were validated by running automated tests (`pytest`), cross-checking geometric invariants, and verifying 3D mesh rendering in Three.js. No API keys are committed to the repository.

---

## 5-Minute Video Recording Walkthrough Guide

| Timestamp | Screen Action | Talking Points |
|---|---|---|
| **0:00–0:30** | Show `README.md` and problem summary | "Hello team, this is the 3D Garment Template Generator built for Kloth. We translate 2D garment imagery and H&M size charts into an inspection-ready 3D template covering all nine categories." |
| **0:30–1:30** | Run `py -3.11 run_pipeline.py` in terminal | "Here we run the end-to-end pipeline. It uses computer vision to segment the garment silhouette, parses the H&M size chart using the lower-bound rule, extracts the 52-joint SMPL-X avatar skeleton and torso profiles, and conformally wraps the panels in 3D." |
| **1:30–3:00** | Open `http://localhost:8000` (Demo UI) | Show the 3D viewer: Orbit around the dress and avatar. Point out the zero-penetration air clearance. Click size buttons (**XXS**, **XS**, **S**, **M**) to demonstrate dynamic grading. Inspect the 2D pattern canvas, continuous shift construction, and center-back seam. |
| **3:00–4:00** | Inspect Output Package & Run Pytest | Open `output/template_package/manifest.json`. Show the 9 categories. Run `pytest tests/ -v` to prove all 15 tests and 25 non-circular validation checks pass. |
| **4:00–5:00** | Limitations & Sizing Explanation | "To be transparent about limitations: this is parametric template fitting guided by computer vision rather than a black-box physics simulation. Dimensions and ease allowances strictly follow the H&M size chart." |
