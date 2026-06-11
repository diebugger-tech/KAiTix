<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as THREE from 'three';
  import { MapControls } from 'three/examples/jsm/controls/MapControls.js';
  import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
  import { nodeColor, nodeStroke, baseEdgeColor } from '$lib/topologyColors';
  import { appState } from '$lib/state.svelte';

  let {
    data,
    visibleNodeIds = new Set<number>(),
    selectedNode = $bindable(null),
    showCables = false,
    showPower = false,
    showCrossRack = false,
    showIntraRack = false,
    showDeviceTypes = new Set<string>(),
    selectedStandort = '__ALL__',
    selectedRackreihe = '__ALL__',
    selectedRack = '__ALL__',
    showHeatmap = false,
    anomalyScores = []
  } = $props();

  let containerEl: HTMLElement;
  let renderer: THREE.WebGLRenderer;
  let labelRenderer: CSS2DRenderer;
  let scene: THREE.Scene;
  let camera: THREE.PerspectiveCamera;
  let controls: MapControls;
  let sceneReady = $state(false);
  let animationFrameId: number;

  const RACK_WIDTH = 18;
  const RACK_GAP = 5;
  const RACK_DEPTH = 18;
  const U_HEIGHT = 1.2;
  const ROW_GAP = 30;
  const STANDORT_GAP = 80;
  const PDU_W = 2;

  // Stores for interactivity
  let deviceMeshes: THREE.Mesh[] = [];
  let rackWireframes: { mesh: THREE.LineSegments, rack: any, aura: THREE.Mesh }[] = [];
  let cableMeshes: { mesh: THREE.Mesh, edge: any }[] = [];
  let rackLabels: { label: CSS2DObject, rackId: number }[] = [];
  let standortLabels: { label: CSS2DObject, standort: string }[] = [];
  let deviceBoxes = new Map<number, { x: number, y: number, z: number, w: number }>();
  let raycaster = new THREE.Raycaster();
  let mouse = new THREE.Vector2();
  let hoveredNodeId = $state<number | null>(null);

  function initScene() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(appState.theme === 'light' ? '#F4F7F5' : '#080c14');

    // Lighting (Catch #1)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(100, 200, 100);
    scene.add(dirLight);

    // Camera
    camera = new THREE.PerspectiveCamera(45, containerEl.clientWidth / containerEl.clientHeight, 1, 2000);
    
    // WebGL Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(containerEl.clientWidth, containerEl.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    containerEl.appendChild(renderer.domElement);

    // CSS2D Renderer (Catch #3)
    labelRenderer = new CSS2DRenderer();
    labelRenderer.setSize(containerEl.clientWidth, containerEl.clientHeight);
    labelRenderer.domElement.style.position = 'absolute';
    labelRenderer.domElement.style.top = '0px';
    labelRenderer.domElement.style.pointerEvents = 'none'; // Critical for OrbitControls
    containerEl.appendChild(labelRenderer.domElement);

    // Controls (Catch #4)
    controls = new MapControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    buildTopology();

    // Event listeners
    window.addEventListener('resize', onWindowResize);
    renderer.domElement.addEventListener('pointerdown', onPointerDown);
    renderer.domElement.addEventListener('pointermove', onPointerMove);

    animate();
    sceneReady = true;
  }

  $effect(() => {
    if (sceneReady && scene) {
      scene.background = new THREE.Color(appState.theme === 'light' ? '#F4F7F5' : '#080c14');
    }
  });

  function buildTopology() {
    if (!data) return;

    // Sort racks by standort, then rackreihe
    let sortedRacks = [...data.racks].sort((a, b) => {
      const sA = a.standort || '';
      const sB = b.standort || '';
      if (sA !== sB) return sA.localeCompare(sB);
      const rA = a.rackreihe || '';
      const rB = b.rackreihe || '';
      return rA.localeCompare(rB);
    });

    let currentStandort = null;
    let currentReihe = null;
    let xOffset = 0;
    let zOffset = 0;

    let maxX = 0;
    let maxZ = 0;

    for (const rack of sortedRacks) {
      if (currentStandort !== rack.standort) {
        if (currentStandort !== null) {
          xOffset += STANDORT_GAP;
          zOffset = 0;
        }
        currentStandort = rack.standort;
        currentReihe = rack.rackreihe;

        // Standort Label
        const div = document.createElement('div');
        div.className = 'text-xs font-bold text-[var(--color-text)] bg-[var(--color-bg3)] px-2 py-1 rounded border border-[var(--color-border2)] backdrop-blur-sm';
        div.textContent = rack.standort || 'Unbekannt';
        const label = new CSS2DObject(div);
        label.position.set(xOffset, 40, zOffset - 10);
        scene.add(label);
        standortLabels.push({ label, standort: rack.standort || '' });
      } else if (currentReihe !== rack.rackreihe) {
        zOffset += ROW_GAP;
        xOffset = Math.max(0, xOffset - (xOffset % STANDORT_GAP)); // Reset X relative to standort
        currentReihe = rack.rackreihe;
      }

      const rackH = rack.hoehe_u * U_HEIGHT;

      // Rack Rahmen (Catch #2: EdgesGeometry instead of MeshPhysicalMaterial)
      const boxGeo = new THREE.BoxGeometry(RACK_WIDTH, rackH, RACK_DEPTH);
      const edges = new THREE.EdgesGeometry(boxGeo);
      const lineMat = new THREE.LineBasicMaterial({ color: 0x1e293b, transparent: true, opacity: 0.5 });
      const wireframe = new THREE.LineSegments(edges, lineMat);
      // Box position is center
      const rackCx = xOffset + RACK_WIDTH / 2;
      const rackCy = rackH / 2;
      const rackCz = zOffset + RACK_DEPTH / 2;
      wireframe.position.set(rackCx, rackCy, rackCz);
      scene.add(wireframe);

      // Heatmap Aura
      const auraGeo = new THREE.BoxGeometry(RACK_WIDTH + 2, rackH + 2, RACK_DEPTH + 2);
      const auraMat = new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.0, side: THREE.DoubleSide, depthWrite: false });
      const auraMesh = new THREE.Mesh(auraGeo, auraMat);
      auraMesh.position.set(rackCx, rackCy, rackCz);
      scene.add(auraMesh);

      rackWireframes.push({ mesh: wireframe, rack, aura: auraMesh });

      // Rack Label
      const rDiv = document.createElement('div');
      rDiv.className = 'text-[9px] text-[var(--color-text2)] font-bold whitespace-nowrap';
      rDiv.textContent = rack.name;
      const rLabel = new CSS2DObject(rDiv);
      rLabel.position.set(rackCx, rackH + 2, rackCz);
      scene.add(rLabel);
      rackLabels.push({ label: rLabel, rackId: rack.id });

      // Devices in Rack
      const rackDevices = data.nodes.filter(n => n.rack_id === rack.id);
      let pduLeftCount = 0;
      let pduRightCount = 0;

      for (const dev of rackDevices) {
        let h = Math.max(dev.u_hoehe || 1, 1) * U_HEIGHT;
        let cx = rackCx, cy = 0, cz = rackCz;
        let w = RACK_WIDTH - 1, d = RACK_DEPTH - 1;

        if (dev.u_hoehe === 0) {
          // PDU - zero U (full height of rack)
          w = PDU_W;
          h = rackH;
          d = PDU_W;
          cy = rackH / 2; // Center vertically
          // Alternate left and right back corners, offset by depth if multiple
          if (pduLeftCount <= pduRightCount) {
            cx = xOffset + PDU_W / 2;
            cz = zOffset + PDU_W / 2 + pduLeftCount * (PDU_W + 1);
            pduLeftCount++;
          } else {
            cx = xOffset + RACK_WIDTH - PDU_W / 2;
            cz = zOffset + PDU_W / 2 + pduRightCount * (PDU_W + 1);
            pduRightCount++;
          }
        } else if (dev.u_position) {
          // Slotted
          cy = (dev.u_position - 1) * U_HEIGHT + h / 2;
        } else {
          // Floating
          cy = rackH + h / 2 + 5; 
        }

        const devGeo = new THREE.BoxGeometry(w, h, d);
        const col = nodeColor(dev.typ);
        // StandardMaterial for lighting (Catch #1)
        const devMat = new THREE.MeshStandardMaterial({ 
          color: col,
          roughness: 0.7,
          metalness: 0.1
        });
        
        const devMesh = new THREE.Mesh(devGeo, devMat);
        devMesh.position.set(cx, cy, cz);
        devMesh.userData = { id: dev.id, node: dev };
        scene.add(devMesh);
        deviceMeshes.push(devMesh);

        deviceBoxes.set(dev.id, { x: cx, y: cy, z: cz, w });
      }

      xOffset += RACK_WIDTH + RACK_GAP;
      if (xOffset > maxX) maxX = xOffset;
      if (zOffset > maxZ) maxZ = zOffset;
    }

    // Edges (Cables)
    const portUsage = new Map<number, number>();

    if (showCables || showPower) {
      for (const edge of data.edges) {
        const isPower = (edge as any).edge_type === 'power';
        if (!showPower && isPower) continue;
        if (!showCables && !isPower) continue;
        if (!showCrossRack && edge.cross_rack) continue;
        if (!showIntraRack && !edge.cross_rack) continue;

        const a = deviceBoxes.get(edge.von_device_id);
        const b = deviceBoxes.get(edge.nach_device_id);
        if (!a || !b) continue;

        // Port Spreading: Offset cable positions along the width of the device
        const usageA = portUsage.get(edge.von_device_id) || 0;
        const usageB = portUsage.get(edge.nach_device_id) || 0;
        portUsage.set(edge.von_device_id, usageA + 1);
        portUsage.set(edge.nach_device_id, usageB + 1);

        // Distribute from front-left to front-right
        const dxA = (a.w * 0.8) * ((usageA % 10) / 9) - (a.w * 0.4);
        const dxB = (b.w * 0.8) * ((usageB % 10) / 9) - (b.w * 0.4);

        // Z offset: attach to front of device
        const dz = RACK_DEPTH / 2;

        const p0 = new THREE.Vector3(a.x + dxA, a.y, a.z + dz);
        const p2 = new THREE.Vector3(b.x + dxB, b.y, b.z + dz);
        
        // Control point: Gravity droop (lower Y) and further forward (higher Z)
        const midX = (p0.x + p2.x) / 2;
        const droop = edge.cross_rack ? 30 : 5;
        const midY = Math.min(p0.y, p2.y) - droop - (Math.abs(p0.x - p2.x) * 0.1);
        const midZ = Math.max(p0.z, p2.z) + (edge.cross_rack ? 15 : 5);
        const p1 = new THREE.Vector3(midX, midY, midZ);

        const curve = new THREE.QuadraticBezierCurve3(p0, p1, p2);
        
        // Tube Geometry for thick cables
        const radius = isPower ? 0.6 : 0.3;
        const tubeGeo = new THREE.TubeGeometry(curve, 16, radius, 6, false);
        
        const colHex = baseEdgeColor(edge.typ, (edge as any).phase, isPower);
        const tubeMat = new THREE.MeshStandardMaterial({ 
          color: colHex, 
          roughness: 0.5, 
          metalness: 0.2,
          transparent: true,
          opacity: 1.0
        });

        const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat);
        scene.add(tubeMesh);
        cableMeshes.push({ mesh: tubeMesh, edge });
      }
    }

    // Set camera
    camera.position.set(maxX / 2, 80, maxZ + 150);
    controls.target.set(maxX / 2, 20, maxZ / 2);
    controls.update();
  }

  function onPointerMove(event: PointerEvent) {
    if (!renderer) return;
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(deviceMeshes);
    if (intersects.length > 0) {
      const node = intersects[0].object.userData.node;
      hoveredNodeId = node.id;
      renderer.domElement.style.cursor = 'pointer';
    } else {
      hoveredNodeId = null;
      renderer.domElement.style.cursor = 'default';
    }
  }

  function onPointerDown(event: PointerEvent) {
    if (!renderer) return;
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    // Intersection against device meshes only
    const intersects = raycaster.intersectObjects(deviceMeshes);
    if (intersects.length > 0) {
      const node = intersects[0].object.userData.node;
      selectedNode = selectedNode?.id === node.id ? null : node;
    } else {
      selectedNode = null;
    }
  }

  function onWindowResize() {
    if (!camera || !renderer || !containerEl || !labelRenderer) return;
    camera.aspect = containerEl.clientWidth / containerEl.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(containerEl.clientWidth, containerEl.clientHeight);
    labelRenderer.setSize(containerEl.clientWidth, containerEl.clientHeight); // Catch #3
  }

  function animate() {
    animationFrameId = requestAnimationFrame(animate);
    if (controls) controls.update(); // Catch #4
    if (renderer && scene && camera) renderer.render(scene, camera);
    if (labelRenderer && scene && camera) labelRenderer.render(scene, camera); // Catch #3
  }

  export function resetCamera() {
    if (camera && controls) {
      // Re-target to center. We can estimate center.
      controls.reset();
    }
  }

  export function zoomIn() {
    if (camera && controls) {
      const target = controls.target;
      const position = camera.position;
      const dir = new THREE.Vector3().subVectors(target, position);
      camera.position.add(dir.multiplyScalar(0.2));
      controls.update();
    }
  }

  export function zoomOut() {
    if (camera && controls) {
      const target = controls.target;
      const position = camera.position;
      const dir = new THREE.Vector3().subVectors(position, target);
      camera.position.add(dir.multiplyScalar(0.25));
      controls.update();
    }
  }

  // Reactive updates for filtering
  $effect(() => {
    if (!sceneReady) return;

    // Svelte 5 reactivity: explicitly read dependencies outside the loop to ensure tracking
    const currentStandort = selectedStandort;
    const currentReihe = selectedRackreihe;
    const currentRack = selectedRack;

    // 1. Hide/show Racks (Wireframes & Labels)
    const visibleRackIds = new Set<number>();
    for (const rw of rackWireframes) {
      const r = rw.rack;
      let visible = true;
      if (currentStandort !== '__ALL__' && r.standort !== currentStandort) visible = false;
      if (currentReihe !== '__ALL__' && r.rackreihe !== currentReihe && `${r.standort} || ${r.rackreihe}` !== currentReihe) visible = false;
      if (currentRack !== '__ALL__' && String(r.id) !== String(currentRack)) visible = false;
      
      rw.mesh.visible = visible;
      if (visible) visibleRackIds.add(r.id);
      
      const lbl = rackLabels.find(l => l.rackId === r.id);
      if (lbl) lbl.label.visible = visible;

      // Heatmap
      if (showHeatmap && visible) {
        const scoreObj = anomalyScores.find(s => s.rack_id === r.id);
        if (scoreObj) {
          rw.aura.visible = true;
          if (scoreObj.level === 'critical') { rw.aura.material.color.setHex(0xef4444); rw.aura.material.opacity = 0.3; }
          else if (scoreObj.level === 'warning') { rw.aura.material.color.setHex(0xf59e0b); rw.aura.material.opacity = 0.2; }
          else { rw.aura.material.color.setHex(0x10b981); rw.aura.material.opacity = 0.1; }
        } else {
          rw.aura.visible = false;
        }
      } else {
        rw.aura.visible = false;
      }
    }

    // 2. Hide/show meshes based on visibleRackIds, visibleNodeIds and showDeviceTypes
    for (const mesh of deviceMeshes) {
      const node = mesh.userData.node;
      const inVisibleRack = node.rack_id ? visibleRackIds.has(node.rack_id) : true;
      const isVisible = inVisibleRack && visibleNodeIds.has(node.id) && showDeviceTypes.has(node.typ);
      mesh.visible = isVisible;
      
      // Focus highlight
      if (mesh.material instanceof THREE.MeshStandardMaterial) {
        if (selectedNode?.id || hoveredNodeId) {
          const isFocused = node.id === selectedNode?.id || node.id === hoveredNodeId;
          mesh.material.emissive.setHex(isFocused ? 0x333333 : 0x000000);
          mesh.material.opacity = isFocused ? 1.0 : 0.3;
          mesh.material.transparent = true;
        } else {
          mesh.material.emissive.setHex(0x000000);
          mesh.material.opacity = 1.0;
          mesh.material.transparent = false;
        }
      }
    }

    // 3. Highlight Cables (Hover / Selected focus mode)
    const activeFocusId = hoveredNodeId || selectedNode?.id;
    for (const cm of cableMeshes) {
      const isVisibleEdge = visibleNodeIds.has(cm.edge.von_device_id) && visibleNodeIds.has(cm.edge.nach_device_id);
      
      if (!isVisibleEdge) {
        cm.mesh.visible = false;
        continue;
      }

      cm.mesh.visible = true;

      if (activeFocusId) {
        const isConnected = cm.edge.von_device_id === activeFocusId || cm.edge.nach_device_id === activeFocusId;
        if (isConnected) {
          cm.mesh.material.opacity = 1.0;
          cm.mesh.material.emissive.copy(cm.mesh.material.color).multiplyScalar(0.5); // Glow effect
        } else {
          cm.mesh.material.opacity = 0.05;
          cm.mesh.material.emissive.setHex(0x000000);
        }
      } else {
        cm.mesh.material.opacity = 0.8;
        cm.mesh.material.emissive.setHex(0x000000);
      }
    }

    // 4. Hide/show Standort labels
    for (const sl of standortLabels) {
      sl.label.visible = (currentStandort === '__ALL__' || sl.standort === currentStandort);
    }
    
    // Optional center camera on filtered
    if (visibleNodeIds.size > 0 && visibleNodeIds.size < data?.nodes.length) {
      let sumX = 0, sumY = 0, sumZ = 0;
      let count = 0;
      // Calculate center based on visible racks instead of just devices to be more stable
      for (const rw of rackWireframes) {
        if (rw.mesh.visible) {
          sumX += rw.mesh.position.x;
          sumY += rw.mesh.position.y;
          sumZ += rw.mesh.position.z;
          count++;
        }
      }
      if (count > 0 && controls) {
        controls.target.set(sumX / count, sumY / count, sumZ / count);
      }
    }
  });

  onMount(() => {
    initScene();
  });

  onDestroy(() => {
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    if (renderer) {
      renderer.dispose();
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      renderer.domElement.removeEventListener('pointermove', onPointerMove);
    }
    window.removeEventListener('resize', onWindowResize);
    
    // Cleanup geometries and materials
    if (scene) {
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          if (Array.isArray(object.material)) {
            object.material.forEach(m => m.dispose());
          } else {
            object.material.dispose();
          }
        } else if (object instanceof THREE.LineSegments) {
          object.geometry.dispose();
          if (Array.isArray(object.material)) {
            object.material.forEach(m => m.dispose());
          } else {
            object.material.dispose();
          }
        }
      });
    }
  });
</script>

<div bind:this={containerEl} class="w-full h-full relative outline-none"></div>
