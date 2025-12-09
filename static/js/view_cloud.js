function polarToCartesianWithRotation(phi, r, theta) {
    const alpha = (120 - theta) * Math.PI / 180;
    const phiRad = phi * Math.PI / 180;

    const x = r * Math.cos(phiRad) * Math.cos(alpha) - 100 * Math.sin(alpha);
    const y = r * Math.sin(phiRad);
    const z = -r * Math.cos(phiRad) * Math.sin(alpha) - 100 * Math.cos(alpha);

    return { x: x / 1000, y: y / 1000, z: z / 1000 };
}


// Функция для создания текстовой подписи (Sprite)
function makeTextSprite(message, color = "#222", fontSize = 120) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    context.font = `bold ${fontSize}px Arial`;
    context.fillStyle = color;
    context.textBaseline = "top";
    context.fillText(message, 0, 0);
    const texture = new THREE.CanvasTexture(canvas);
    const spriteMaterial = new THREE.SpriteMaterial({ map: texture, depthTest: false });
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.scale.set(fontSize * 0.012, fontSize * 0.006, 1); // Пропорционально fontSize
    return sprite;
}

function addAxisLabels(scene, axis, min, max, step, fixed = 0) {
    for (let v = Math.ceil(min / step) * step; v <= max; v += step) {
        let pos = { x: 0, y: 0, z: 0 };
        pos[axis] = v;
        // подпись
        const label = makeTextSprite(v.toFixed(fixed), "#444", 120);
        // немного смещаем подписи от оси
        if (axis === "x") {
            label.position.set(v, min, min);
        } else if (axis === "y") {
            label.position.set(min, v, min);
        } else if (axis === "z") {
            label.position.set(min, min, v);
        }
        scene.add(label);
    }
}

function createPointCloudVisualization(coordinates, containerId) {
    if (typeof THREE === 'undefined') {
        console.error('Three.js не загружен');
        return;
    }
    const container = document.getElementById(containerId);
    if (!container) {
        console.error('Контейнер не найден');
        return;
    }
    container.innerHTML = '';
    const width = container.clientWidth;
    const height = container.clientHeight;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8f9fa);
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 10000);
    camera.position.set(0, 0, 10);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    container.appendChild(renderer.domElement);

    // Преобразуем координаты
    const positions = [];
    coordinates.forEach(coord => {
        const { x, y, z } = polarToCartesianWithRotation(coord.phi, coord.r, coord.theta);
        positions.push(x, y, z);
    });
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    const material = new THREE.PointsMaterial({
        size: 0.03,
        color: 0x3366ff,
        opacity: 0.5,
        transparent: true
    });
    const points = new THREE.Points(geometry, material);
    scene.add(points);

    geometry.computeBoundingBox();
    const bbox = geometry.boundingBox;
    const min = bbox.min, max = bbox.max;

    // Оси
    const axesHelper = new THREE.AxesHelper(Math.max(max.x - min.x, max.y - min.y, max.z - min.z) * 0.6);
    scene.add(axesHelper);

    // Сетка по каждой оси (в метрах)
    const gridSizeX = Math.ceil(max.x - min.x);
    const gridSizeY = Math.ceil(max.y - min.y);
    const gridSizeZ = Math.ceil(max.z - min.z);
    const gridXY = new THREE.GridHelper(gridSizeX, Math.max(2, Math.round(gridSizeX)), 0x888888, 0xcccccc);
    gridXY.rotation.x = Math.PI / 2;
    gridXY.position.set(0, 0, min.z);
    scene.add(gridXY);
    const gridYZ = new THREE.GridHelper(gridSizeY, Math.max(2, Math.round(gridSizeY)), 0x888888, 0xcccccc);
    gridYZ.rotation.z = Math.PI / 2;
    gridYZ.position.set(min.x, 0, 0);
    scene.add(gridYZ);
    const gridXZ = new THREE.GridHelper(gridSizeZ, Math.max(2, Math.round(gridSizeZ)), 0x888888, 0xcccccc);
    gridXZ.position.set(0, min.y, 0);
    scene.add(gridXZ);

    // Подписи осей (X, Y, Z)
    const xLabel = makeTextSprite("X, м", "#222", 130);
    xLabel.position.set(max.x, min.y, min.z);
    scene.add(xLabel);
    const yLabel = makeTextSprite("Y, м", "#222", 130);
    yLabel.position.set(min.x, max.y, min.z);
    scene.add(yLabel);
    const zLabel = makeTextSprite("Z, м", "#222", 130);
    zLabel.position.set(min.x, min.y, max.z);
    scene.add(zLabel);

    // Деления с числами (метки) на осях
    const stepX = Math.max(1, Math.round((max.x - min.x) / 6));
    const stepY = Math.max(1, Math.round((max.y - min.y) / 6));
    const stepZ = Math.max(1, Math.round((max.z - min.z) / 6));
    addAxisLabels(scene, "x", min.x, max.x, stepX, 1);
    addAxisLabels(scene, "y", min.y, max.y, stepY, 1);
    addAxisLabels(scene, "z", min.z, max.z, stepZ, 1);

    // Tooltip (в метрах)
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const tooltip = document.createElement('div');
    tooltip.style.position = 'absolute';
    tooltip.style.background = 'rgba(255,255,255,0.95)';
    tooltip.style.border = '1px solid #888';
    tooltip.style.padding = '4px 8px';
    tooltip.style.fontSize = '13px';
    tooltip.style.pointerEvents = 'none';
    tooltip.style.display = 'none';
    tooltip.style.zIndex = 10;
    container.appendChild(tooltip);

    function onPointerMove(event) {
        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObject(points);
        if (intersects.length > 0) {
            const idx = intersects[0].index * 3;
            const x = positions[idx].toFixed(2);
            const y = positions[idx + 1].toFixed(2);
            const z = positions[idx + 2].toFixed(2);
            tooltip.innerHTML = `X=${x} м<br>Y=${y} м<br>Z=${z} м`;
            // Позиционирование tooltip: не выходить за пределы окна
            let left = event.clientX + 10;
            let top = event.clientY - 10;
            const pad = 10;
            setTimeout(() => {
                const ttRect = tooltip.getBoundingClientRect();
                if (left + ttRect.width > window.innerWidth - pad) {
                    left = window.innerWidth - ttRect.width - pad;
                }
                if (top + ttRect.height > window.innerHeight - pad) {
                    top = window.innerHeight - ttRect.height - pad;
                }
                if (top < pad) top = pad;
                if (left < pad) left = pad;
                tooltip.style.left = left + 'px';
                tooltip.style.top = top + 'px';
            }, 0);
            tooltip.style.display = 'block';
        } else {
            tooltip.style.display = 'none';
        }
    }
    renderer.domElement.addEventListener('pointermove', onPointerMove);

    // Управление камерой
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.screenSpacePanning = false;
    controls.minDistance = 0.1;
    controls.maxDistance = Math.max(gridSizeX, gridSizeY, gridSizeZ) * 5;
    controls.target.set(
        (min.x + max.x) / 2,
        (min.y + max.y) / 2,
        (min.z + max.z) / 2
    );
    controls.update();

    function setAspectRatio() {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }
    window.addEventListener('resize', setAspectRatio);

    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }
    animate();

    return {
        cleanup: () => {
            window.removeEventListener('resize', setAspectRatio);
            renderer.domElement.removeEventListener('pointermove', onPointerMove);
            renderer.dispose();
            geometry.dispose();
            material.dispose();
        }
    };
}

function loadVisualization(userId, experimentId) {
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const visualization = document.getElementById('visualization');
    loading.style.display = 'flex';
    error.style.display = 'none';
    visualization.innerHTML = '';
    fetch(`/${userId}/api/experiments/${experimentId}/measurements`)
        .then(response => {
            if (!response.ok) throw new Error('Ошибка загрузки данных');
            return response.json();
        })
        .then(data => {
            loading.style.display = 'none';
            const header = document.createElement('div');
            header.style.cssText = 'text-align: center; margin-bottom: 20px; font-size: 18px; color: #006D75; font-weight: bold;';
            header.textContent = `3D Облако точек (${data.measurements_count.toLocaleString()} точек)`;
            visualization.appendChild(header);
            const threeContainer = document.createElement('div');
            threeContainer.id = 'three-container';
            threeContainer.style.cssText = 'width: 100%; height: 500px; border: 1px solid #dee2e6; border-radius: 4px;';
            visualization.appendChild(threeContainer);
            createPointCloudVisualization(data.coordinates, 'three-container');
            const pointCount = document.createElement('div');
            pointCount.style.cssText = 'text-align: center; margin-top: 20px; font-size: 16px; color: #6c757d;';
            pointCount.textContent = `Количество точек: ${data.measurements_count.toLocaleString()}`;
            visualization.appendChild(pointCount);
            const instructions = document.createElement('div');
            instructions.style.cssText = 'text-align: center; margin-top: 10px; font-size: 14px; color: #6c757d;';
            instructions.innerHTML = 'Используйте мышь для вращения, колесо мыши для масштабирования. Наведите на точку для просмотра координат.';
            visualization.appendChild(instructions);
        })
        .catch(err => {
            loading.style.display = 'none';
            error.style.display = 'block';
            error.textContent = 'Ошибка загрузки визуализации: ' + err.message;
        });
}