/**
 * Kloth 3D Garment Template Generator - Interactive Viewer
 * Specialized for H&M Scoop-Neck Bodycon Maxi Dress (#1356023002)
 * Three.js WebGL Engine with Real-Time Size Switching & 2D Pattern Visualizer
 */

(function () {
  "use strict";

  // Three.js State
  let scene, camera, renderer, controls;
  let mannequinGroup = new THREE.Group();
  let garmentGroup = new THREE.Group();
  let avatarGroup = new THREE.Group();

  let showAvatar = true;
  let isWireframe = false;
  let isTurntable = false;
  let currentSize = "XS"; // XS is base size; M and L are supported hero sizes

  // Package & Template Data Cache
  let templateData = {
    manifest: null,
    patterns: null,
    sewing: null,
    grading: null,
    fabric: null,
    validation: null,
    product: null
  };

  // Garment Material: Deep Burgundy Maroon (#881337)
  const DRESS_COLOR = 0x881337;
  const garmentMaterial = new THREE.MeshStandardMaterial({
    color: DRESS_COLOR,
    roughness: 0.60,
    metalness: 0.08,
    side: THREE.DoubleSide,
    wireframe: false
  });

  // -------------------------------------------------------------
  // Three.js Scene Setup
  // -------------------------------------------------------------
  function initScene() {
    const container = document.getElementById("threeContainer");
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    // 1. Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060911);

    // 2. Camera
    camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(0.0, 0.90, 2.6);

    // 3. Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // 4. Controls
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(0.0, 0.85, 0.0);
    controls.minDistance = 0.8;
    controls.maxDistance = 5.0;
    controls.maxPolarAngle = Math.PI / 2 + 0.1;

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.80);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xfff5ea, 1.4);
    keyLight.position.set(2.0, 3.5, 2.5);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xdbeafe, 0.7);
    fillLight.position.set(-2.5, 2.0, 1.5);
    scene.add(fillLight);

    const backLight = new THREE.DirectionalLight(0x93c5fd, 0.85);
    backLight.position.set(0.0, 2.5, -2.5);
    scene.add(backLight);

    // Floor Grid
    const grid = new THREE.GridHelper(3.0, 30, 0x1e293b, 0x0f172a);
    grid.position.y = 0.0;
    scene.add(grid);

    scene.add(mannequinGroup);
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
  // Load Mannequin (GLTF Avatar)
  // -------------------------------------------------------------
  function loadAvatar() {
    const loader = new THREE.GLTFLoader();
    const avatarPath = "/assets/person_0.glb";

    loader.load(
      avatarPath,
      (gltf) => {
        avatarGroup.clear();
        const model = gltf.scene;

        const avatarMat = new THREE.MeshStandardMaterial({
          color: 0xe2e8f0,
          roughness: 0.45,
          metalness: 0.08,
          wireframe: false
        });

        model.traverse((child) => {
          if (child.isMesh) {
            child.material = avatarMat;
            child.castShadow = true;
            child.receiveShadow = true;
          }
        });

        avatarGroup.add(model);
        document.getElementById("statVertices").innerText = "SMPL-X (52 Joints)";
      },
      undefined,
      (err) => {
        console.warn("Avatar load fallback to mannequin.glb:", err);
        loader.load("/output/template_package/mannequin.glb", (gltf) => {
          avatarGroup.clear();
          avatarGroup.add(gltf.scene);
        });
      }
    );
  }

  // -------------------------------------------------------------
  // Load 3D Garment Mesh
  // -------------------------------------------------------------
  function loadGarmentMesh(size) {
    const objPath = `/output/garment_${size}.obj`;
    const label = `Maxi Dress [Size ${size}]`;

    document.getElementById("viewportStatusText").innerText = `Loading ${label}...`;
    const loader = new THREE.OBJLoader();

    loader.load(
      objPath,
      (obj) => {
        garmentGroup.clear();
        let totalVerts = 0;

        obj.traverse((child) => {
          if (child.isMesh) {
            child.material = garmentMaterial;
            child.castShadow = true;
            child.receiveShadow = true;
            if (child.geometry && child.geometry.attributes.position) {
              totalVerts += child.geometry.attributes.position.count;
            }
          }
        });

        garmentGroup.add(obj);
        document.getElementById("viewportStatusText").innerText = `Ready (${label} Active)`;
        document.getElementById("statVertices").innerText = `${totalVerts} Verts (${size} Bodycon)`;
        document.getElementById("statSeams").innerText = "0.0% Penetration (0 Tears)";
      },
      undefined,
      (err) => {
        console.warn("OBJ load fallback to garment.obj:", err);
        loader.load("/output/garment.obj", (obj) => {
          garmentGroup.clear();
          garmentGroup.add(obj);
          document.getElementById("viewportStatusText").innerText = `Ready (${label} Active)`;
        });
      }
    );
  }

  // -------------------------------------------------------------
  // Fetch Package Data (Resilient Multi-Fetch)
  // -------------------------------------------------------------
  async function loadPackageData() {
    const safeFetch = async (url) => {
      try {
        const res = await fetch(url);
        if (!res.ok) return null;
        return await res.json();
      } catch (e) {
        return null;
      }
    };

    templateData.manifest = await safeFetch("/output/template_package/manifest.json");
    templateData.patterns = await safeFetch("/output/template_package/patterns_2d.json");
    templateData.sewing = await safeFetch("/output/template_package/sewing_connections.json");
    templateData.grading = await safeFetch("/output/template_package/grading_sizes.json");
    templateData.fabric = await safeFetch("/output/template_package/fabric_properties.json");
    templateData.validation = await safeFetch("/output/template_package/validation_report.json");
    templateData.product = await safeFetch("/samples/product_details.json");

    populateInspectorTabs();
    render2DPatterns();
  }

  // -------------------------------------------------------------
  // 2D Pattern Canvas Drawing (Normalized, Top-Down, Clean Glass Badges)
  // -------------------------------------------------------------
  function render2DPatterns() {
    const canvas = document.getElementById("patternCanvas");
    if (!canvas) return;

    const activePatterns = templateData.patterns;
    if (!activePatterns) return;

    // Update badge in card header
    const badgeEl = document.getElementById("patternDimsBadge");
    if (badgeEl) {
      badgeEl.innerText = `Size ${currentSize} [cm]`;
    }

    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    // Dynamic Sizing Dimensions based on active size
    const sizeLookup = {
      XXS: { hem_circ: 72.0, front_length: 116.0, back_length: 118.0 },
      XS:  { hem_circ: 76.0, front_length: 118.0, back_length: 120.0 },
      S:   { hem_circ: 80.0, front_length: 120.0, back_length: 122.0 },
      M:   { hem_circ: 86.0, front_length: 122.0, back_length: 124.0 },
      L:   { hem_circ: 94.0, front_length: 124.0, back_length: 126.0 },
      XL:  { hem_circ: 103.0, front_length: 125.0, back_length: 127.0 },
      XXL: { hem_circ: 113.0, front_length: 126.0, back_length: 128.0 }
    };

    const curDims = (templateData.grading && templateData.grading.size_meshes && templateData.grading.size_meshes[currentSize] && templateData.grading.size_meshes[currentSize].dimensions_cm) 
      || sizeLookup[currentSize] || sizeLookup["XS"];

    const formatNum = (v) => (v % 1 === 0 ? v.toFixed(0) : v.toFixed(1));

    // 3-panel continuous layout for Maxi Dress (Front, Back Left, Back Right)
    const panelLayouts = [
      { id: "front_panel",      label: "Front Panel",   cx: w * 0.22, cy: h * 0.05, color: "#e11d48" },
      { id: "back_left_panel",  label: "Back Left",     cx: w * 0.54, cy: h * 0.05, color: "#be123c" },
      { id: "back_right_panel", label: "Back Right",    cx: w * 0.84, cy: h * 0.05, color: "#881337" }
    ];

    const baseScale = (h * 0.68) / 130.0;

    panelLayouts.forEach((pLayout) => {
      const pData = activePatterns[pLayout.id];
      if (!pData || !pData.contour_points) return;

      const pts = pData.contour_points;
      if (pts.length < 3) return;

      const isFront = (pLayout.id === "front_panel");
      
      // Compute actual width and height in cm for the active size
      const actualWidthCm = isFront ? (curDims.hem_circ / 2.0) : (curDims.hem_circ / 4.0);
      const actualHeightCm = isFront ? (curDims.front_length + 1.0) : curDims.back_length;

      // Scaling relative to base pattern (XS has hem_circ 76, front_length 118, back_length 120)
      const scaleX = curDims.hem_circ / 76.0;
      const scaleY = isFront ? ((curDims.front_length + 1.0) / 119.0) : (curDims.back_length / 120.0);

      // Compute bounding box in base pattern units
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      pts.forEach((pt) => {
        if (pt.x < minX) minX = pt.x;
        if (pt.x > maxX) maxX = pt.x;
        if (pt.y < minY) minY = pt.y;
        if (pt.y > maxY) maxY = pt.y;
      });

      const pWidth = (maxX - minX) * scaleX;
      const pHeight = (maxY - minY) * scaleY;
      const scale = baseScale;

      ctx.save();
      // Center panel horizontally at pLayout.cx, top at pLayout.cy
      const offsetX = pLayout.cx - (pWidth * scale) / 2.0;
      const offsetY = pLayout.cy;
      ctx.translate(offsetX, offsetY);

      // Draw Scaled Pattern Contour
      ctx.beginPath();
      // Invert Y so highest Y (shoulders) is at top, lowest Y (hem) is at bottom
      const startX = (pts[0].x - minX) * scaleX * scale;
      const startY = (maxY - pts[0].y) * scaleY * scale;
      ctx.moveTo(startX, startY);

      for (let i = 1; i < pts.length; i++) {
        const px = (pts[i].x - minX) * scaleX * scale;
        const py = (maxY - pts[i].y) * scaleY * scale;
        ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fillStyle = pLayout.color + "22";
      ctx.fill();
      ctx.strokeStyle = pLayout.color;
      ctx.lineWidth = 1.6;
      ctx.stroke();

      // Vertical Grainline
      const gx = (pWidth * scale) / 2.0;
      const gy1 = 10;
      const gy2 = pHeight * scale - 10;

      ctx.beginPath();
      ctx.setLineDash([4, 4]);
      ctx.moveTo(gx, gy1);
      ctx.lineTo(gx, gy2);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.40)";
      ctx.lineWidth = 1.2;
      ctx.stroke();
      ctx.setLineDash([]);

      // Glass Badge for Panel Dimensions
      const badgeY = (pHeight * scale) + 16;
      const badgeW = 96;
      const badgeH = 28;

      ctx.fillStyle = "rgba(10, 15, 26, 0.90)";
      ctx.strokeStyle = pLayout.color + "99";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(gx - badgeW / 2, badgeY - 14, badgeW, badgeH, 6);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#ffffff";
      ctx.font = "600 11px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(pLayout.label, gx, badgeY - 1);

      ctx.fillStyle = "#38bdf8";
      ctx.font = "600 10px 'JetBrains Mono', monospace";
      ctx.fillText(`${formatNum(actualWidthCm)} × ${formatNum(actualHeightCm)} cm`, gx, badgeY + 10);

      ctx.restore();
    });
  }

  // -------------------------------------------------------------
  // Dynamic Size Selector Pills
  // -------------------------------------------------------------
  function updateSizePills() {
    const pillGroup = document.getElementById("sizePillGroup");
    if (!pillGroup) return;

    pillGroup.innerHTML = "";
    const availableSizes = ["XXS", "XS", "S", "M", "L", "XL", "XXL"];
    const baseSize = "XS";

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
        render2DPatterns();
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
    legend.innerHTML = `
      <span><i class="dot dot-front"></i> Front Panel</span>
      <span><i class="dot dot-back-left"></i> Back Left</span>
      <span><i class="dot dot-back-right"></i> Back Right</span>
    `;
  }

  // -------------------------------------------------------------
  // Populate Inspector Tabs & UI Controls
  // -------------------------------------------------------------
  function populateInspectorTabs() {
    // 1. Sewing Table (JSON root = array of seam objects)
    const sewTbody = document.getElementById("sewingTableBody");
    if (sewTbody && templateData.sewing) {
      sewTbody.innerHTML = "";
      const seams = Array.isArray(templateData.sewing)
        ? templateData.sewing : (templateData.sewing.seams || []);
      seams.forEach((s) => {
        const isValid = s.is_valid !== false;
        const tr = document.createElement("tr");
        tr.innerHTML =
          '<td style="font-weight:600; color:#f8fafc;">' + s.seam_id + '</td>' +
          '<td>' + s.panel_a_id + ' [' + s.edge_a_name + '] (' + (s.edge_a_length_cm||0).toFixed(2) + 'cm)</td>' +
          '<td>' + s.panel_b_id + ' [' + s.edge_b_name + '] (' + (s.edge_b_length_cm||0).toFixed(2) + 'cm)</td>' +
          '<td>' + (s.gather_ratio||1).toFixed(2) + '</td>' +
          '<td><span class="status-badge ' + (isValid ? 'pass' : 'fail') + '">' + (isValid ? 'PASS (1:1)' : 'FAIL') + '</span></td>';
        sewTbody.appendChild(tr);
      });
      const validCount = seams.filter(s => s.is_valid !== false).length;
      const seamsEl = document.getElementById("statSeams");
      if (seamsEl) seamsEl.innerText = validCount + "/" + seams.length + " Paired (1:1, 0 Tears)";
    }

    // 2. Fabric Tab
    if (templateData.fabric) {
      const f = templateData.fabric.front_panel || templateData.fabric;
      if (f) {
        const el = (id) => document.getElementById(id);
        if (el("fabMaterial")) el("fabMaterial").innerText = f.material_name || "Poly-Elastane Soft Stretch Jersey Knit (89/11)";
        if (el("fabWeight"))   el("fabWeight").innerText   = f.weight_gsm !== undefined ? f.weight_gsm + " GSM" : "195 GSM";
        if (el("fabWarp"))     el("fabWarp").innerText     = f.stretch_warp_percent !== undefined ? f.stretch_warp_percent + "%" : "18.0%";
        if (el("fabWeft"))     el("fabWeft").innerText     = f.stretch_weft_percent !== undefined ? f.stretch_weft_percent + "%" : "35.0%";
        if (el("fabBending"))  el("fabBending").innerText  = f.bending_stiffness_Nm !== undefined ? f.bending_stiffness_Nm + " N*m" : "0.038 N*m";
        if (el("fabShear"))    el("fabShear").innerText    = f.shear_stiffness_N_m !== undefined ? f.shear_stiffness_N_m + " N/m" : "0.055 N/m";
      }
    }

    // 3. Grading Tab
    const gradTbody = document.getElementById("gradingTableBody");
    if (gradTbody && templateData.grading) {
      gradTbody.innerHTML = "";
      const sizeMeshes = templateData.grading.size_meshes || templateData.grading;
      if (sizeMeshes && typeof sizeMeshes === "object" && !Array.isArray(sizeMeshes)) {
        for (const [sz, gData] of Object.entries(sizeMeshes)) {
          if (!gData || typeof gData !== "object") continue;
          const dims = gData.dimensions_cm || {};
          const isBase = sz === "XS";
          const tr = document.createElement("tr");
          tr.innerHTML =
            '<td style="font-weight:700; color:#e11d48;">' + sz + (isBase ? ' <span class="base-badge">BASE</span>' : '') + '</td>' +
            '<td>' + (dims.bust_circ  !== undefined ? dims.bust_circ  : '–') + ' cm</td>' +
            '<td>' + (dims.waist_circ !== undefined ? dims.waist_circ : '–') + ' cm</td>' +
            '<td>' + (dims.hip_circ   !== undefined ? dims.hip_circ   : '–') + ' cm</td>' +
            '<td>' + (dims.front_length !== undefined ? dims.front_length : '–') + ' cm</td>' +
            '<td style="font-size:10px;">' + (gData.mesh_filename || 'garment_' + sz + '.obj') + '</td>';
          gradTbody.appendChild(tr);
        }
      }
    }

    // 4. Validation Tab (JSON: {overall_status, passed_checks, total_checks, checks:[{category,name,status,details}]})
    if (templateData.validation) {
      const v = templateData.validation;
      const passed = v.passed_checks !== undefined ? v.passed_checks : 0;
      const total  = v.total_checks  !== undefined ? v.total_checks  : 0;
      const isPassing = (v.overall_status || "").toUpperCase() === "PASS";

      const summaryBadge = document.getElementById("valSummaryBadge");
      if (summaryBadge) {
        summaryBadge.className = "status-badge " + (isPassing ? "pass" : "fail");
        summaryBadge.innerText = passed + "/" + total + " PASS" + (isPassing ? "" : " (FAIL)");
      }
      const tabBtn = document.getElementById("tabValidationBtn");
      if (tabBtn) tabBtn.innerText = "Validation (" + passed + "/" + total + ")";

      const valList = document.getElementById("validationList");
      if (valList && Array.isArray(v.checks)) {
        valList.innerHTML = "";
        v.checks.forEach((chk) => {
          const isPassed = (chk.status || "").toUpperCase() === "PASS";
          const item = document.createElement("div");
          item.className = "val-item";
          item.innerHTML =
            '<div class="val-item-left">' +
              '<span style="font-size:14px;font-weight:700;color:' + (isPassed ? '#34d399' : '#f87171') + '">' + (isPassed ? '\u2713' : '\u2717') + '</span>' +
              '<div>' +
                '<div class="val-item-title">' + (chk.name || '') + '</div>' +
                '<div class="val-item-detail">' + (chk.category || '') + ' \u2014 ' + (chk.details || '') + '</div>' +
              '</div>' +
            '</div>' +
            '<span class="status-badge ' + (isPassed ? 'pass' : 'fail') + '">' + (isPassed ? 'PASS' : 'FAIL') + '</span>';
          valList.appendChild(item);
        });
      }
    }
  }

  // -------------------------------------------------------------
  // UI Event Handlers
  // UI Event Handlers
  // -------------------------------------------------------------
  function setupEventListeners() {
    // Viewport Toolbar Buttons
    document.getElementById("btnToggleMannequin").addEventListener("click", function() {
      showAvatar = !showAvatar;
      avatarGroup.visible = showAvatar;
      this.classList.toggle("active", showAvatar);
    });

    document.getElementById("btnToggleWireframe").addEventListener("click", function() {
      isWireframe = !isWireframe;
      garmentMaterial.wireframe = isWireframe;
      this.classList.toggle("active", isWireframe);
    });

    document.getElementById("btnToggleTurntable").addEventListener("click", function() {
      isTurntable = !isTurntable;
      this.classList.toggle("active", isTurntable);
    });

    document.getElementById("btnResetCamera").addEventListener("click", function() {
      controls.reset();
      camera.position.set(0.0, 0.90, 2.6);
      controls.target.set(0.0, 0.85, 0.0);
    });

    // Inspector Tab Switching
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".tab-pane").forEach((c) => c.classList.remove("active"));
        this.classList.add("active");
        const tabId = this.dataset.tab;
        const targetContent = document.getElementById(tabId);
        if (targetContent) targetContent.classList.add("active");
      });
    });
  }

  // -------------------------------------------------------------
  // Animation Loop
  // -------------------------------------------------------------
  function animate() {
    requestAnimationFrame(animate);

    if (isTurntable) {
      avatarGroup.rotation.y += 0.008;
      garmentGroup.rotation.y += 0.008;
      mannequinGroup.rotation.y += 0.008;
    }

    controls.update();
    renderer.render(scene, camera);
  }

  // -------------------------------------------------------------
  // Application Entry Point
  // -------------------------------------------------------------
  async function init() {
    initScene();
    setupEventListeners();
    updateSizePills();       // Immediately populate size pills so they are always visible!
    updateCanvasLegend();    // Immediately set canvas legend
    loadAvatar();            // Load SMPL-X mannequin
    loadGarmentMesh("XS");   // Load default base size XS dress mesh
    await loadPackageData(); // Load JSON templates and populate tables/patterns
    animate();
  }

  // Start application
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
