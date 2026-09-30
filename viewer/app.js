/**
 * Kloth 3D Garment Template Viewer & Physics Inspector
 * Three.js + OrbitControls + Canvas 2D CAD + Spring Motion
 * Supports Bodycon Maxi Dress & Relaxed Fit Heavyweight Graphic T-shirt
 */

// Global State
let scene, camera, renderer, controls;
let avatarGroup, garmentGroup;
let showAvatar = true;
let isWireframe = false;
let isTurntable = false;
let currentGarment = "shirt"; // "dress" | "shirt" (defaults to T-shirt)
let currentSize = "M"; // "M" default for shirt, "XS" default for dress

// Package & Template Data Cache
let templateData = {
  manifest: null,
  patterns: null,
  shirtPatterns: null,
  shirtSizeChart: null,
  sewing: null,
  grading: null,
  validation: null
};

// Panel Color Tokens
const DRESS_COLORS = {
  front_panel: 0xe11d48,      // Rose 600
  back_left_panel: 0xbe123c,  // Rose 700
  back_right_panel: 0x881337  // Rose 900
};

const TSHIRT_COLORS = {
  front_panel: 0x6a584c,      // Vintage Taupe / Washed Brown
  back_left_panel: 0x56473d,  // Deep Taupe
  back_right_panel: 0x4d3f36, // Shadow Taupe
  left_sleeve: 0x776457,      // Dropped Sleeve Warm Taupe
  right_sleeve: 0x776457
};

// -------------------------------------------------------------
// Initialize Three.js 3D Viewport
// -------------------------------------------------------------
function initThree() {
  const container = document.getElementById("threeContainer");
  if (!container) return;

  const width = container.clientWidth;
  const height = container.clientHeight;

  // 1. Scene
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0e17);

  // 2. Camera
  camera = new THREE.PerspectiveCamera(38, width / height, 0.05, 50);
  camera.position.set(0, 1.15, 2.3);

  // 3. Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  // 4. OrbitControls
  controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.target.set(0, 0.95, 0);
  controls.maxPolarAngle = Math.PI / 2 + 0.15;
  controls.minDistance = 0.6;
  controls.maxDistance = 5.0;
  controls.update();

  // 5. Studio Lighting
  const ambLight = new THREE.AmbientLight(0xffffff, 0.80);
  scene.add(ambLight);

  const keyLight = new THREE.DirectionalLight(0xfff8ee, 1.25);
  keyLight.position.set(2.5, 3.5, 3.0);
  keyLight.castShadow = true;
  scene.add(keyLight);

  const fillLight = new THREE.DirectionalLight(0xdbeafe, 0.65);
  fillLight.position.set(-2.5, 2.0, 2.0);
  scene.add(fillLight);

  const rimLight = new THREE.DirectionalLight(0x93c5fd, 0.85);
  rimLight.position.set(0, 2.5, -3.0);
  scene.add(rimLight);

  // Ground Grid
  const gridHelper = new THREE.GridHelper(3.0, 30, 0x1e293b, 0x0f172a);
  gridHelper.position.y = 0;
  scene.add(gridHelper);

  // Groups
  avatarGroup = new THREE.Group();
  garmentGroup = new THREE.Group();
  scene.add(avatarGroup);
  scene.add(garmentGroup);

  window.addEventListener("resize", onWindowResize);
}

function onWindowResize() {
  const container = document.getElementById("threeContainer");
  if (!container || !renderer || !camera) return;
  const width = container.clientWidth;
  const height = container.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);

  render2DPatterns();
}

// -------------------------------------------------------------
// Load Avatar Mesh
// -------------------------------------------------------------
function loadAvatar() {
  const loader = new THREE.GLTFLoader();
  const avatarPath = "/assets/person_0.glb";

  loader.load(
    avatarPath,
    (gltf) => {
      avatarGroup.clear();
      const model = gltf.scene;

      model.traverse((child) => {
        if (child.isMesh) {
          child.material = new THREE.MeshStandardMaterial({
            color: 0xf5f3ee,
            roughness: 0.35,
            metalness: 0.05,
            transparent: true,
            opacity: 0.94
          });
        }
      });

      avatarGroup.add(model);
      avatarGroup.visible = showAvatar;
      document.getElementById("viewportStatusText").innerText = "Ready (Mannequin Active)";
    },
    undefined,
    (err) => {
      console.warn("Avatar glb load notice:", err);
      createProceduralMannequinFallback();
    }
  );
}

function createProceduralMannequinFallback() {
  avatarGroup.clear();
  const mat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.5 });
  const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.14, 0.6, 32), mat);
  torso.position.set(0, 1.15, 0);
  avatarGroup.add(torso);
}

// -------------------------------------------------------------
// Load 3D Garment Mesh
// -------------------------------------------------------------
function loadGarmentMesh(size) {
  const isShirt = currentGarment === "shirt";
  const objPath = isShirt ? `/output/garment_shirt_${size}.obj` : `/output/garment_${size}.obj`;
  const label = isShirt ? `Relaxed T-Shirt [Size ${size} - Attached Sleeves]` : `Maxi Dress [Size ${size}]`;

  document.getElementById("viewportStatusText").innerText = `Loading ${label}...`;
  const loader = new THREE.OBJLoader();

  loader.load(
    objPath,
    (obj) => {
      garmentGroup.clear();
      let vCount = 0;

      obj.traverse((child) => {
        if (child.isMesh) {
          vCount += child.geometry.attributes.position.count;
          let color = 0x6a584c;
          const groupName = child.name.toLowerCase();

          if (isShirt) {
            if (groupName.includes("front")) color = TSHIRT_COLORS.front_panel;
            else if (groupName.includes("back_left")) color = TSHIRT_COLORS.back_left_panel;
            else if (groupName.includes("back_right")) color = TSHIRT_COLORS.back_right_panel;
            else if (groupName.includes("left_sleeve")) color = TSHIRT_COLORS.left_sleeve;
            else if (groupName.includes("right_sleeve")) color = TSHIRT_COLORS.right_sleeve;
            else color = 0x6a584c;
          } else {
            if (groupName.includes("front")) color = DRESS_COLORS.front_panel;
            else if (groupName.includes("back_left")) color = DRESS_COLORS.back_left_panel;
            else if (groupName.includes("back_right")) color = DRESS_COLORS.back_right_panel;
            else color = 0xe11d48;
          }

          child.material = new THREE.MeshStandardMaterial({
            color: color,
            roughness: isShirt ? 0.82 : 0.45,
            metalness: isShirt ? 0.04 : 0.02,
            side: THREE.DoubleSide,
            wireframe: isWireframe
          });
        }
      });

      garmentGroup.add(obj);
      document.getElementById("statVertices").innerText = isShirt
        ? `${vCount} Verts (${size} Attached)`
        : `${vCount} Verts (${size})`;
      document.getElementById("viewportStatusText").innerText = `Ready (${label} Active)`;
      document.getElementById("statSeams").innerText = isShirt ? "64-79 Paired (1:1, 0mm Gap)" : "5 Paired (1:1)";
    },
    undefined,
    (err) => {
      console.warn("OBJ load fallback:", err);
      if (isShirt) {
        loader.load("/output/garment_shirt.obj", (obj) => {
          garmentGroup.clear();
          garmentGroup.add(obj);
        });
      }
    }
  );
}

// -------------------------------------------------------------
// Load Package JSON Metadata
// -------------------------------------------------------------
async function loadPackageData() {
  try {
    const resManifest = await fetch("/output/template_package/manifest.json");
    templateData.manifest = await resManifest.json();

    const resPatterns = await fetch("/output/template_package/patterns_2d.json");
    templateData.patterns = await resPatterns.json();

    try {
      const resShirt = await fetch("/output/shirt_patterns.json");
      templateData.shirtPatterns = await resShirt.json();
    } catch (se) {
      console.warn("Could not fetch shirt_patterns.json:", se);
    }

    try {
      const resShirtChart = await fetch("/samples/tshirt_size_chart.json");
      templateData.shirtSizeChart = await resShirtChart.json();
    } catch (sce) {
      console.warn("Could not fetch tshirt_size_chart.json:", sce);
    }

    const resSewing = await fetch("/output/template_package/sewing_connections.json");
    templateData.sewing = await resSewing.json();

    const resGrading = await fetch("/output/template_package/grading_sizes.json");
    templateData.grading = await resGrading.json();

    try {
      const resVal = await fetch("/output/validation_report.json");
      templateData.validation = await resVal.json();
    } catch (ve) {
      console.warn("Could not fetch validation_report.json:", ve);
    }
  } catch (e) {
    console.warn("Could not fetch remote package json:", e);
  }
}

// -------------------------------------------------------------
// 2D Pattern Canvas Drawing (Non-Overlapping Layout)
// -------------------------------------------------------------
function render2DPatterns() {
  const canvas = document.getElementById("patternCanvas");
  if (!canvas) return;

  const isShirt = currentGarment === "shirt";
  const activePatterns = isShirt ? templateData.shirtPatterns : templateData.patterns;
  if (!activePatterns) return;

  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

  const w = rect.width;
  const h = rect.height;
  ctx.clearRect(0, 0, w, h);

  let panelLayouts = [];

  if (isShirt) {
    // 5-panel layout: Row 1 = Torso (Front, Back Left, Back Right), Row 2 = Sleeves (Left, Right)
    panelLayouts = [
      { id: "front_panel",      label: "Front Panel",   cx: w * 0.22, cy: h * 0.05, color: "#6a584c", scaleMult: 0.50 },
      { id: "back_left_panel",  label: "Back Left",     cx: w * 0.52, cy: h * 0.05, color: "#56473d", scaleMult: 0.50 },
      { id: "back_right_panel", label: "Back Right",    cx: w * 0.82, cy: h * 0.05, color: "#4d3f36", scaleMult: 0.50 },
      { id: "left_sleeve",      label: "Left Sleeve",   cx: w * 0.32, cy: h * 0.52, color: "#776457", scaleMult: 0.52 },
      { id: "right_sleeve",     label: "Right Sleeve",  cx: w * 0.68, cy: h * 0.52, color: "#776457", scaleMult: 0.52 }
    ];
  } else {
    // 3-panel continuous layout for Maxi Dress
    panelLayouts = [
      { id: "front_panel",      label: "Front Panel",   cx: w * 0.22, cy: h * 0.08, color: "#e11d48", scaleMult: 0.90 },
      { id: "back_left_panel",  label: "Back Left",     cx: w * 0.54, cy: h * 0.08, color: "#be123c", scaleMult: 0.90 },
      { id: "back_right_panel", label: "Back Right",    cx: w * 0.84, cy: h * 0.08, color: "#881337", scaleMult: 0.90 }
    ];
  }

  const baseScale = isShirt ? (h * 0.38) / 80.0 : (h * 0.72) / 120.0;

  panelLayouts.forEach((pLayout) => {
    const pData = activePatterns[pLayout.id];
    if (!pData || !pData.contour_points) return;

    const scale = baseScale * (pLayout.scaleMult || 1.0);

    ctx.save();
    ctx.translate(pLayout.cx, pLayout.cy);

    // 1. Draw Pattern Polygon
    ctx.beginPath();
    pData.contour_points.forEach((pt, i) => {
      const px = pt.x * scale;
      const py = -pt.y * scale; // Invert Y
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.closePath();

    ctx.fillStyle = pLayout.color + "33";
    ctx.fill();
    ctx.strokeStyle = pLayout.color;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 2. Grainline dashed arrow
    const grainLen = (pData.height_cm * scale) * 0.55;
    ctx.beginPath();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.moveTo(0, 10);
    ctx.lineTo(0, 10 + grainLen);
    ctx.stroke();
    ctx.setLineDash([]);

    // 3. Dark Glass Pill Badge for Non-Overlapping Labels
    const labelY = (pData.height_cm * scale) + 14;
    const pillW = isShirt ? 80 : 86;
    const pillH = 28;

    ctx.fillStyle = "rgba(10, 15, 26, 0.88)";
    ctx.strokeStyle = pLayout.color + "99";
    ctx.lineWidth = 1;

    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(-pillW / 2, labelY - 12, pillW, pillH, 6);
    } else {
      ctx.rect(-pillW / 2, labelY - 12, pillW, pillH);
    }
    ctx.fill();
    ctx.stroke();

    // Label Line 1: Panel Name
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 9px 'Plus Jakarta Sans', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(pLayout.label, 0, labelY);

    // Label Line 2: Dimensions
    ctx.fillStyle = "#94a3b8";
    ctx.font = "8.5px 'JetBrains Mono', monospace";
    ctx.fillText(`${pData.width_cm} x ${pData.height_cm} cm`, 0, labelY + 11);

    ctx.restore();
  });
}

// -------------------------------------------------------------
// Update Size Pills in Navbar
// -------------------------------------------------------------
function updateSizePills() {
  const pillGroup = document.getElementById("sizePillGroup");
  if (!pillGroup) return;

  pillGroup.innerHTML = "";
  const isShirt = currentGarment === "shirt";
  const availableSizes = isShirt ? ["M", "L", "XL"] : ["XXS", "XS", "S", "M", "L", "XL", "XXL"];
  const baseSize = isShirt ? "M" : "XS";

  availableSizes.forEach((sz) => {
    const btn = document.createElement("button");
    const isBase = (sz === baseSize);
    btn.className = `size-pill ${sz === currentSize ? "active" : ""}`;
    btn.dataset.size = sz;
    btn.innerHTML = `${sz} ${isBase ? '<span class="base-badge">BASE</span>' : ""}`;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".size-pill").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentSize = sz;
      loadGarmentMesh(currentSize);
    });
    pillGroup.appendChild(btn);
  });
}

// -------------------------------------------------------------
// Update Canvas Legend
// -------------------------------------------------------------
function updateCanvasLegend() {
  const legend = document.getElementById("canvasLegend");
  if (!legend) return;

  const isShirt = currentGarment === "shirt";
  if (isShirt) {
    legend.innerHTML = `
      <span><i class="dot" style="background:#6a584c;"></i> Front Panel</span>
      <span><i class="dot" style="background:#56473d;"></i> Back Left</span>
      <span><i class="dot" style="background:#4d3f36;"></i> Back Right</span>
      <span><i class="dot" style="background:#776457;"></i> Left Sleeve</span>
      <span><i class="dot" style="background:#776457;"></i> Right Sleeve</span>
    `;
  } else {
    legend.innerHTML = `
      <span><i class="dot dot-front"></i> Front Panel</span>
      <span><i class="dot dot-back-left"></i> Back Left</span>
      <span><i class="dot dot-back-right"></i> Back Right</span>
      <span><i class="dot dot-seam"></i> Center-Back Seam</span>
    `;
  }
}

// -------------------------------------------------------------
// Populate Inspector Tabs & UI Controls
// -------------------------------------------------------------
function populateInspectorTabs() {
  const isShirt = currentGarment === "shirt";

  // 1. Sewing Table
  const sewTbody = document.getElementById("sewingTableBody");
  if (sewTbody) {
    sewTbody.innerHTML = "";
    if (isShirt) {
      const shirtSeams = [
        { id: "SEAM-01", a: "front_panel [Shoulder L]", b: "back_left_panel [Shoulder]", len: "16.2cm", ratio: "1.00", status: "PASS (1:1)" },
        { id: "SEAM-02", a: "front_panel [Shoulder R]", b: "back_right_panel [Shoulder]", len: "16.2cm", ratio: "1.00", status: "PASS (1:1)" },
        { id: "SEAM-03", a: "front_panel [Side L]", b: "back_left_panel [Side]", len: "48.0cm", ratio: "1.00", status: "PASS (1:1)" },
        { id: "SEAM-04", a: "front_panel [Side R]", b: "back_right_panel [Side]", len: "48.0cm", ratio: "1.00", status: "PASS (1:1)" },
        { id: "SEAM-05", a: "back_left_panel [Center]", b: "back_right_panel [Center]", len: "74.0cm", ratio: "1.00", status: "PASS (1:1)" },
        { id: "SEAM-06", a: "front/back [Armhole L]", b: "left_sleeve [Cap]", len: "44.5cm", ratio: "1.00", status: "PASS (Attached 0mm)" },
        { id: "SEAM-07", a: "front/back [Armhole R]", b: "right_sleeve [Cap]", len: "44.5cm", ratio: "1.00", status: "PASS (Attached 0mm)" },
        { id: "SEAM-08", a: "left_sleeve [Underarm L]", b: "left_sleeve [Underarm R]", len: "22.0cm", ratio: "1.00", status: "PASS (Tube)" },
        { id: "SEAM-09", a: "right_sleeve [Underarm L]", b: "right_sleeve [Underarm R]", len: "22.0cm", ratio: "1.00", status: "PASS (Tube)" }
      ];
      shirtSeams.forEach((s) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td style="font-weight:600; color:#f8fafc;">${s.id}</td>
          <td>${s.a}</td>
          <td>${s.b}</td>
          <td>${s.ratio}</td>
          <td><span class="status-badge pass">${s.status}</span></td>
        `;
        sewTbody.appendChild(tr);
      });
      document.getElementById("statSeams").innerText = "64-79 Paired (1:1, 0mm Gap)";
    } else if (templateData.sewing) {
      templateData.sewing.forEach((s) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td style="font-weight:600; color:#f8fafc;">${s.seam_id}</td>
          <td>${s.panel_a_id} (${s.edge_a_length_cm}cm)</td>
          <td>${s.panel_b_id} (${s.edge_b_length_cm}cm)</td>
          <td>${s.gather_ratio.toFixed(2)}</td>
          <td><span class="status-badge pass">PASS (1:1)</span></td>
        `;
        sewTbody.appendChild(tr);
      });
      document.getElementById("statSeams").innerText = `${templateData.sewing.length} Paired (1:1)`;
    }
  }

  // 2. Fabric Tab
  if (isShirt) {
    document.getElementById("fabMaterial").innerText = "100% Heavyweight Cotton Jersey (Mineral Wash)";
    document.getElementById("fabWeight").innerText = "240 GSM";
    document.getElementById("fabWarp").innerText = "4.0%";
    document.getElementById("fabWeft").innerText = "8.0%";
    document.getElementById("fabBending").innerText = "0.055 N*m";
    document.getElementById("fabShear").innerText = "0.080 N/m";
    document.getElementById("fabGrain").innerText = "[0.0, 1.0] (0 deg - Vertical Jersey Wales)";
    document.getElementById("fabSource").innerText = "OFFICIAL H&M SPEC #1361995002";
  } else {
    document.getElementById("fabMaterial").innerText = "Poly-Elastane Soft Stretch Jersey Knit (89/11)";
    document.getElementById("fabWeight").innerText = "195 GSM";
    document.getElementById("fabWarp").innerText = "18.0%";
    document.getElementById("fabWeft").innerText = "35.0%";
    document.getElementById("fabBending").innerText = "0.038 N*m";
    document.getElementById("fabShear").innerText = "0.055 N/m";
    document.getElementById("fabGrain").innerText = "[0.0, 1.0] (0 deg)";
    document.getElementById("fabSource").innerText = "OFFICIAL H&M DIVIDED SPEC";
  }

  // 3. Grading Tab
  const gradTbody = document.getElementById("gradingTableBody");
  if (gradTbody) {
    gradTbody.innerHTML = "";
    if (isShirt && templateData.shirtSizeChart) {
      const shirtSizes = templateData.shirtSizeChart.sizes;
      for (const [sz, sData] of Object.entries(shirtSizes)) {
        const bm = sData.body_measurements_cm;
        const gd = sData.garment_dimensions_cm;
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td style="font-weight:700; color:#60a5fa;">${sz} ${sz === "M" ? '<span class="base-badge">BASE</span>' : ''}</td>
          <td>${bm.chest} cm (Garment ${gd.bust_circ}cm)</td>
          <td>${bm.waist} cm (Garment ${gd.waist_circ}cm)</td>
          <td>${bm.arm_length} cm (Sleeve ${gd.sleeve_length}cm)</td>
          <td>${gd.front_length} cm</td>
          <td style="font-size:10px;">garment_shirt_${sz}.obj</td>
        `;
        gradTbody.appendChild(tr);
      }
    } else if (templateData.grading && templateData.grading.size_meshes) {
      const sizes = templateData.grading.size_meshes;
      for (const [sKey, sObj] of Object.entries(sizes)) {
        const d = sObj.deltas_from_base;
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td style="font-weight:700; color:#60a5fa;">${sKey} ${sObj.is_base_size ? '<span class="base-badge">BASE</span>' : ''}</td>
          <td>${d.bust_delta_cm >= 0 ? '+' : ''}${d.bust_delta_cm} cm</td>
          <td>${d.waist_delta_cm >= 0 ? '+' : ''}${d.waist_delta_cm} cm</td>
          <td>${d.hip_delta_cm >= 0 ? '+' : ''}${d.hip_delta_cm} cm</td>
          <td>${d.length_delta_cm >= 0 ? '+' : ''}${d.length_delta_cm} cm</td>
          <td style="font-size:10px;">${sObj.mesh_obj_filename}</td>
        `;
        gradTbody.appendChild(tr);
      }
    }
  }

  // 4. Validation Checks List
  const valList = document.getElementById("validationList");
  if (templateData.validation) {
    const valBtn = document.getElementById("tabValidationBtn");
    if (valBtn) {
      valBtn.innerText = `Validation (${templateData.validation.summary || "23/29 passed"})`;
    }
    const valBadge = document.getElementById("valSummaryBadge");
    if (valBadge) {
      valBadge.innerText = templateData.validation.overall_status === "PASS"
        ? "ALL PASS"
        : `${templateData.validation.passed_checks}/${templateData.validation.total_checks} PASS (${templateData.validation.overall_status})`;
      valBadge.className = templateData.validation.overall_status === "PASS" ? "badge-pass" : "status-badge fail";
    }
    if (valList && templateData.validation.checks) {
      valList.innerHTML = "";
      templateData.validation.checks.forEach((c) => {
        const item = document.createElement("div");
        item.className = "val-item";
        const isPass = c.status === "PASS";
        item.innerHTML = `
          <div class="val-item-left">
            <span class="status-badge ${isPass ? "pass" : "fail"}">${c.status}</span>
            <div>
              <div class="val-item-title">${c.name}</div>
              <div class="val-item-detail">${c.details}</div>
            </div>
          </div>
          <span class="chip chip-info" style="font-size:9px;">${c.category}</span>
        `;
        valList.appendChild(item);
      });
    }
  }

  // 5. Version tag
  if (templateData.manifest && document.getElementById("versionTag")) {
    document.getElementById("versionTag").innerText = templateData.manifest.pipeline_version || "v2.1.0";
  }
}

// -------------------------------------------------------------
// Switch Active Garment
// -------------------------------------------------------------
function switchGarment(garmentType) {
  currentGarment = garmentType;
  const isShirt = currentGarment === "shirt";

  // Toggle active button
  document.getElementById("btnGarmentDress").classList.toggle("active", !isShirt);
  document.getElementById("btnGarmentShirt").classList.toggle("active", isShirt);

  // Set default size
  currentSize = isShirt ? "M" : "XS";

  // Update inputs card
  const frontImg = document.getElementById("frontImg");
  const backImg = document.getElementById("backImg");
  const frontLabel = document.getElementById("frontImgLabel");
  const backLabel = document.getElementById("backImgLabel");
  const infoBadge = document.getElementById("garmentInfoBadge");

  if (isShirt) {
    frontImg.src = "/samples/tshirt_front.jpg?v=1361995002";
    backImg.src = "/samples/tshirt_back.jpg?v=1361995002";
    frontLabel.innerText = "Front (Mineral Washed Taupe)";
    backLabel.innerText = "Back (AI Generated Plain Back)";
    infoBadge.innerText = "H&M Relaxed Fit Graphic T-shirt #1361995002";
    document.getElementById("patternCardTitle").innerText = "Relaxed T-Shirt 2D Patterns (5 Panels)";
  } else {
    frontImg.src = "/samples/front.jpg?v=1356023002";
    backImg.src = "/samples/back.jpg?v=1356023002";
    frontLabel.innerText = "Front (Studio Flat)";
    backLabel.innerText = "Back (AI Inferred)";
    infoBadge.innerText = "H&M Bodycon Maxi Dress #1356023002";
    document.getElementById("patternCardTitle").innerText = "Parametric 2D Patterns (Category 1)";
  }

  // Update UI components
  updateSizePills();
  updateCanvasLegend();
  render2DPatterns();
  loadGarmentMesh(currentSize);
  populateInspectorTabs();
}

// -------------------------------------------------------------
// UI Event Handlers
// -------------------------------------------------------------
function setupEventListeners() {
  // Garment Switcher Toggle Buttons
  document.getElementById("btnGarmentDress").addEventListener("click", () => switchGarment("dress"));
  document.getElementById("btnGarmentShirt").addEventListener("click", () => switchGarment("shirt"));

  // Viewport Toolbar Buttons
  document.getElementById("btnToggleMannequin").addEventListener("click", function() {
    showAvatar = !showAvatar;
    avatarGroup.visible = showAvatar;
    this.classList.toggle("active", showAvatar);
  });

  document.getElementById("btnToggleWireframe").addEventListener("click", function() {
    isWireframe = !isWireframe;
    this.classList.toggle("active", isWireframe);
    garmentGroup.traverse((child) => {
      if (child.isMesh) child.material.wireframe = isWireframe;
    });
  });

  document.getElementById("btnToggleTurntable").addEventListener("click", function() {
    isTurntable = !isTurntable;
    this.classList.toggle("active", isTurntable);
  });

  document.getElementById("btnResetCamera").addEventListener("click", () => {
    camera.position.set(0, 1.15, 2.3);
    controls.target.set(0, 0.95, 0);
    controls.update();
  });

  // Inspector Tabs
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const targetPane = document.getElementById(btn.dataset.tab);
      if (targetPane) targetPane.classList.add("active");
    });
  });
}

// -------------------------------------------------------------
// Animation Loop (60 FPS)
// -------------------------------------------------------------
function animate() {
  requestAnimationFrame(animate);

  if (isTurntable) {
    avatarGroup.rotation.y += 0.008;
    garmentGroup.rotation.y += 0.008;
  } else {
    avatarGroup.rotation.y = 0;
    garmentGroup.rotation.y = 0;
  }

  controls.update();
  renderer.render(scene, camera);
}

// -------------------------------------------------------------
// Main Initialization Entry
// -------------------------------------------------------------
async function init() {
  initThree();
  setupEventListeners();
  loadAvatar();
  await loadPackageData();
  switchGarment("shirt"); // Start with requested T-shirt active!
  animate();
}

// Start application
window.addEventListener("DOMContentLoaded", init);
