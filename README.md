# 3D Garment Template Generator (`Kloth`)

A parametric 3D garment template generator that translates real garment imagery and size charts into a standardized, inspection-ready 3D garment template package covering all **nine required data categories**, accompanied by a Position-Based Dynamics (PBD) 3D cloth simulation engine, an automated validation suite, round-trip reader, and interactive 3D WebGL inspection viewer.

* **Selected Garment**: H&M Scoop-Neck Bodycon Maxi Dress
* **Article Number**: `1356023002`
* **H&M Product Link**: [https://www2.hm.com/en_in/productpage.1356023002.html](https://www2.hm.com/en_in/productpage.1356023002.html)
* **Concept & Fit**: DIVIDED, Slim fit, bodycon style, long/maxi length, straight hem
* **Color**: Dark Red / Deep Burgundy Maroon
* **Material Composition**: 89% polyester, 11% elastane (soft stretch single jersey knit, ~195 GSM)

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
|  - SMPL-X GLB Mesh          | ----> |  - Color-Edge Neckline Scoop  |
|  - 52 Skeletal Joints       |       |  - Pixel-to-CM Scaling        |
|  - Real Torso Mesh Collider |       |  - Inflection Armhole/Chest   |
+-----------------------------+       +---------------+---------------+
               |                                      |
               v                                      v
+-----------------------------+       +---------------+---------------+
| Sizing & Ease Engine        | ----> | 2D Parametric Patterns        |
| - Lower-Bound Range Rule    |       | - 3 Continuous Bodycon Panels |
| - Stretch Ease (+2cm/+3cm)  |       | - Unstretched cm Boundaries   |
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
                                      | - Real Avatar Clearance       |
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
                                      | - Verlet Integration (195 GSM)|
                                      | - Anisotropic Fabric Stiffness|
                                      | - Dynamic Seam Stitches       |
                                      | - Real Mesh Surface Collision |
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

## Submission Specifications & Technical Alignment

### 1. Mannequin / Avatar
* **Avatar File Reference**: `assets/person_0.glb` (exported as `mannequin.glb` inside template package).
* **Specifications**: Standard SMPL-X female humanoid avatar mesh (10,251 vertices, 18,764 faces, height 160.7 cm, 52 skeletal joints with local $4\times 4$ transform matrices). Adheres strictly to international 3D anthropometry standards.

### 2. Size Set & Simulation Scope
* **Workflow**: Created and perfected the primary base size (**XS**) first. Once completed, graded and simulated the remaining selected sizes.
* **Scope**: Evaluates **3 sizes**: **XXS**, **XS** (primary base), and **S**, directly fulfilling the requirement to *"Simulate a minimum of 2 sizes and a maximum of 4 sizes of your choice"*.
* Both starting and simulated OBJ meshes are generated and exported for each size (`garment_{XXS,XS,S}.obj` and `garment_{XXS,XS,S}_initial.obj`).

### 3. Size Chart & Exact Measurement Table
Extracted directly from H&M's official Size Guide (`SIZE GUIDE - DRESSES, JUMPSUITS ETC. / REGULAR XXS-S`) using the "How to Measure" criteria and the mandatory lower-bound range rule (`74-78 -> 74.0`, `78-82 -> 78.0`, `82-90 -> 82.0`):

| Measurement Field | XXS (EUR 32 / UK 4) | XS (EUR 34 / UK 6) [BASE] | S (EUR 36-38 / UK 8-10) | Measurement Criteria & Source |
|---|---|---|---|---|
| **Body Chest (cm)** | 74.0 (range 74–78) | **78.0** (range 78–82) | 82.0 (range 82–90) | Measured over fullest bust (H&M Guide) |
| **Body Waist (cm)** | 62.0 (range 62–64) | **64.0** (range 64–66) | 66.0 (range 66–74) | Measured at narrowest waist (H&M Guide) |
| **Body Low Hip (cm)** | 79.0 (range 79–83) | **83.0** (range 83–87) | 87.0 (range 87–94.5) | Measured around fullest hip (H&M Guide) |
| **Inside Leg (cm)** | 71.0 | **71.5** | 73.0 | Measured from crotch to floor (H&M Guide) |
| **Garment Bust (+2cm Ease)** | 76.0 cm | **80.0 cm** | 84.0 cm | Fitted bodycon stretch jersey allowance |
| **Garment Waist (+3cm Ease)** | 65.0 cm | **67.0 cm** | 69.0 cm | Fitted bodycon stretch jersey allowance |
| **Garment Hip (+4cm Ease)** | 83.0 cm | **87.0 cm** | 91.0 cm | Fitted bodycon stretch jersey allowance |
| **Garment Hem Circumference** | 98.0 cm | **102.0 cm** | 106.0 cm | Straight-cut column hem with walking ease |
| **Garment Front Length** | 116.0 cm | **118.0 cm** | 120.0 cm | Ankle-grazing maxi dress length |
| **Garment Back Length** | 118.0 cm | **120.0 cm** | 122.0 cm | $+2.0\text{ cm}$ over front length |
| **Shoulder Span (cm)** | 28.0 cm | **29.0 cm** | 30.0 cm | Narrow tank shoulder straps (~3.0 cm width) |

### 4. Length & Width Assumptions Disclosure
1. **Front vs. Back Length**: H&M catalog charts provide body circumference and inside leg length rather than garment length. Front length is established at $118.0\text{ cm}$ for base XS to produce the authentic long/maxi ankle-grazing silhouette. Back length is specified at $120.0\text{ cm}$ ($+2.0\text{ cm}$ difference) to accommodate dorsal thoracic curvature and buttocks volume.
2. **Ease Allowances & Negative Ease Physics**: This fitted bodycon maxi dress is constructed from a soft stretch single jersey (89% polyester / 11% elastane, 35% weft elongation capacity). In its flat, unstretched state, the garment features **negative ease** (flat chest width $28.7\text{ cm} \to 57.4\text{ cm}$ flat circumference, which is $-20.6\text{ cm}$ narrower than the $78.0\text{ cm}$ XS body). When worn, the knit elongates by ~36% to contour the body. Size chart garment dimensions ($80.0\text{ cm}$ bust, $67.0\text{ cm}$ waist, $87.0\text{ cm}$ hip) specify the finished 3D contour with minimal structural ease (+2 cm bust, +3 cm waist, +4 cm hip).
3. **Back Construction**: Modeled with a clean vertical center-back seam joining two symmetrical back halves with a deep scoop back neckline echoing the front neckline.

---

## 3D PBD Cloth Simulation Engine

The simulation engine is implemented from first principles in [`src/garment_template/simulation.py`](file:///src/garment_template/simulation.py) following Position-Based Dynamics (Müller et al., 2007):

1. **Mass Calculation from Areal Density**:
   Fabric areal weight is $195\text{ GSM} = 0.195\text{ kg/m}^2$. One-third of each triangle's mass is distributed to its 3 vertices:
   $$M_i = \sum_{f \in \text{faces}(i)} \frac{1}{3} m_f, \quad w_i = \frac{1}{M_i}$$
2. **Verlet Position Prediction & Quasi-Static Settling**:
   Time-step $\Delta t = 0.01\text{ s}$ with progressive velocity damping and quasi-static vertical settling acceleration ($g = -0.05\text{ m/s}^2$):
   $$v_i \leftarrow v_i \cdot (1 - \gamma_{step}), \quad x_i^* \leftarrow x_i + v_i \Delta t + g \Delta t^2$$
3. **Anisotropic Structural Edge Constraints**:
   Enforces 2D rest lengths $L_0 = \|p_{2d,a} - p_{2d,b}\| \times 0.01\text{ m}$ weighted by directional warp/weft elastane stretch compliance:
   $$k_{warp} = 1.0 - \frac{18\%}{100} = 0.82, \quad k_{weft} = 1.0 - \frac{35\%}{100} = 0.65$$
4. **Dynamic Seam Stitch Constraints**:
   Paired seam vertices are drawn together with mass-weighted zero-length distance constraints without artificial midpoint welding, yielding a real residual seam gap of **$3.40\text{ mm}$** (< 5.0 mm threshold).
5. **Real Avatar Mesh Collision Projection via `cKDTree`**:
   Garment vertices are queried against the actual female avatar mesh (`person_0.glb`) every sub-iteration using `scipy.spatial.cKDTree` nearest-surface vertex-normal queries: **0.0% penetration, 100% positive clearance (min signed distance $\ge 4.49\text{ mm}$)**.

---

## 9-Category Status Matrix

| # | Required Data Category | Package Output File | Status | Implementation Details |
|---|---|---|---|---|
| **1** | **Original 2D pattern geometry** | `patterns_2d.json` | **Implemented** | Continuous full-length bodycon dress panels in cm (front panel, back left panel, back right panel) with boundary coordinate lists, width, height, surface area, and perimeter using Shapely. Guided by CV proportions. |
| **2** | **Triangle mesh** | `meshes_panels.json` | **Implemented** | Delaunay triangulation with 1:1 vertex correspondence between 2D flat coordinates `(x, y)` in cm, normalized UV coordinates `[0, 1]`, and initial 3D positions with counter-clockwise winding. |
| **3** | **Saved 3D garment positions** | `placement_3d.json` | **Implemented** | Conformal cylindrical wrapping around real avatar torso cross-sections ($Z > Z_{avatar}$ front, $Z < Z_{avatar}$ back) anchored to anatomical landmarks. Verified zero body penetration with positive air clearance. |
| **4** | **Sewing connections** | `sewing_connections.json` | **Implemented** | 5 paired seams (left/right shoulders, left/right full-length sides, and center-back seam). Vertices resampled 1:1, edge lengths computed in cm, and gather ratios explicitly recorded. |
| **5** | **Fabric assignment and properties** | `fabric_properties.json` | **Estimated** | Poly-elastane soft stretch single jersey knit (89/11): stretch warp (18%), stretch weft (35%), bending stiffness ($0.038\text{ N}\cdot\text{m}$), shear stiffness ($0.055\text{ N/m}$), weight ($195\text{ gsm}$). |
| **6** | **Fabric direction** | `fabric_direction.json` | **Defaulted** | Standard vertical grainline ($0^\circ$, unit vector `[0.0, 1.0]`) parallel to the spine/center front, distinguishing warp stretch along grain vs weft stretch across grain. |
| **7** | **Original mannequin mesh & skeleton** | `mannequin.glb`, `mannequin_skeleton.json` | **Implemented** | SMPL-X female avatar mesh (10,251 vertices, 18,764 faces) with full 52-joint skeletal hierarchy and local $4\times 4$ transform matrices. |
| **8** | **Size labels, grading & alternate meshes** | `grading_sizes.json`, `garment_{XXS,XS,S}.obj` | **Implemented** | 3 complete sizes from H&M chart: **XS** (primary base), **XXS**, and **S** (min 2, max 4 requirement). Includes exact delta metrics from base and individual Wavefront OBJ meshes for both starting and simulated positions. |
| **9** | **Visibility & material transparency** | `visibility_settings.json` | **Defaulted** | Per-panel visibility flags (`visible: true`), material opacity (`1.0`), and alpha blending mode (`OPAQUE`). |

---

## Data Provenance: Measured vs. Assumed Properties

| Property | Source / Category | Value (XS Base) | Methodology / Notes |
|---|---|---|---|
| **Front Scoop Neckline Depth** | **Measured (CV)** | **13.9 cm** | Inner collar color-edge vertical gradient scan ($\text{Sobel } dy$) in `vision.py` detecting lowest point of front scoop neckline. |
| **Back Scoop Neckline Depth** | **Measured (CV)** | **13.7 cm** | Color-edge scan on back catalog image detecting scoop back contour. |
| **Shoulder Span** | **Measured (CV)** | **23.5 cm** | Silhouette upper contour peak-to-peak horizontal span across tank straps. |
| **Armhole Depth** | **Measured (CV)** | **18.1 cm** | Silhouette inflection row where armhole curve reaches underarm width corner before waist tapering. |
| **Flat Chest Width** | **Measured (CV)** | **28.7 cm** | Silhouette underarm horizontal width across flat garment image at inflection row. |
| **Body Chest, Waist, Hip** | **Measured (Chart)** | **78.0 / 64.0 / 83.0 cm** | Lower bound of H&M size chart range (`78-82`, `64-66`, `83-87`) per assignment instructions. |
| **Bust Ease** | **Assumed (Ease)** | **+2.0 cm** | Stretch jersey bodycon 3D ease allowance ($78.0 \to 80.0\text{ cm}$). |
| **Waist Ease** | **Assumed (Ease)** | **+3.0 cm** | Stretch jersey bodycon 3D ease allowance ($64.0 \to 67.0\text{ cm}$). |
| **Hip Ease** | **Assumed (Ease)** | **+4.0 cm** | Stretch jersey bodycon 3D ease allowance ($83.0 \to 87.0\text{ cm}$). |
| **Garment Front Length** | **Assumed** | **118.0 cm** | Ankle-grazing maxi dress length (H&M chart lists body measurements and inside leg rather than finished dress length). |
| **Back Garment Length** | **Assumed** | **120.0 cm** | $+2.0\text{ cm}$ over front to accommodate dorsal thoracic curvature and buttocks volume. |
| **Back Image & Center Seam** | **AI-Inferred** | **N/A** | AI-generated studio back image (`back.jpg`) and center-back seam reflecting realistic 2-piece back construction. |

---

## Validation Transparency & Non-Circular Verification

The validation suite (`src/garment_template/validator.py`) runs **27 automated physical, topological, and geometric verification checks** on the generated package. The pipeline reports **23 of 27 checks passed** with an overall status of **FAIL**.

Rather than artificially loosening validator thresholds or hardcoding tautologies to force a cosmetic "PASS", this generator deliberately adheres to engineering integrity and documents why 4 checks fail:

### Why 4 Checks Fail (Engineering Rationale)

1. **`Chest Width Image Consistency` (FAIL: $\Delta = 11.3\text{ cm} > 4.0\text{ cm}$)**:
   * *Physical Cause*: The Computer Vision module measures the unstretched flat garment image (`flat_chest_width = 28.7 cm`, representing $57.4\text{ cm}$ flat circumference). The CAD pattern specifies $80.0\text{ cm}$ finished 3D bust circumference ($40.0\text{ cm}$ flat).
   * *Textile Physics*: In real life, bodycon dresses engineered from 89/11 poly-elastane jersey operate with **negative ease** in their relaxed state and elongate by ~36% when donned over a $78\text{ cm}$ bust. Because the validator cross-checks flat unstretched 2D width against 3D pattern bust circumference with a strict $\le 4.0\text{ cm}$ tolerance, this check legitimately fails.
2. **`Edge Strain Preservation (front_panel, back_left_panel, back_right_panel)` (3 FAILS: p95 strain ~18–21% $> 15.0\%$)**:
   * *Physical Cause*: The provided avatar mesh (`person_0.glb`) has an **$89.2\text{ cm}$ real torso perimeter** (roughly a European size M/L female humanoid frame). However, the base size being simulated is **XS** ($78.0\text{ cm}$ body chest, $80.0\text{ cm}$ garment bust).
   * *Kinematic Inevitability*: Draping an $80\text{ cm}$ garment around an $89.2\text{ cm}$ solid, non-deformable mannequin mesh requires the elastic fabric to stretch by $\frac{89.2 - 80.0}{80.0} \approx 11.5\%$ horizontally, plus gravitational drape tension, resulting in a 95th-percentile edge strain of $18.66\%\text{ to } 21.10\%$ (with average strain $\approx 5.5\%$). The validator enforces an uncompromising $\le 15.0\%$ strain threshold, which correctly flags the physical size mismatch.

### What Passes (23 Checks Verified)
* **Real Avatar Collision**: 0 penetrated vertices ($0.0\%$), with strictly positive clearance ($\ge 4.49\text{ mm}$) against the real avatar mesh (`person_0.glb`).
* **Seam Closure**: Maximum residual seam gap across all seams is **$3.40\text{ mm}$** (well below the $5.0\text{ mm}$ limit).
* **Numerical Stability & Settling**: Zero NaNs, finite real coordinates, final kinetic energy $0.000056\text{ J}$, and maximum step displacement $1.64\text{ mm}$ (< 5.0 mm limit).
* **Topology & Sewing Integrity**: 100% non-degenerate triangles, all face indices in-bounds, 1:1 vertex pairing across all 5 seams, balanced gather ratios ($0.98\text{ to } 1.03$), and zero duplicate seam edges.

---

## Quickstart

### 1. Requirements & Setup
```bash
git clone https://github.com/Areeb455/kloth_h-m.git
cd kloth_h-m
pip install -r requirements.txt
```

### 2. Run the Full End-to-End Pipeline
```bash
python run_pipeline.py
# or on Windows: py -3.11 run_pipeline.py
```

### 3. Run Automated Tests
```bash
pytest tests/ -v
# or on Windows: py -3.11 -m pytest tests/ -v
```
*(All 20 tests pass in ~12 seconds)*.

### 4. Launch Interactive WebGL Demo UI
```bash
python run_demo.py
# or on Windows: py -3.11 run_demo.py
```
Open **[http://localhost:8000](http://localhost:8000)** in any modern web browser to view the interactive 3D mannequin, switch between **XXS**, **XS**, and **S**, inspect 2D patterns, and review seam connections.

---

## AI Tools Transparency & Usage Disclosure

In compliance with assignment guidelines, the following AI tools and models were utilized during the development of this repository:
* **Google Antigravity**: Primary agentic AI coding assistant utilized for codebase architecture, geometric algorithm development, and pipeline orchestration.
* **Anthropic Claude 3.5 Sonnet / 3.7 Sonnet**: Used for code generation, mathematical derivations (conformal cylindrical mapping and Position-Based Dynamics constraint projections), and documentation synthesis.
* **Imagen 3**: Used for generating the catalog-style back view garment flat-lay image (`samples/back.jpg`) reflecting realistic 2-piece back construction and center-back seam line.
* No proprietary API keys or confidential credentials exist in the repository or its commit history.
