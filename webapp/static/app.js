import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.162.0/build/three.module.js';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.162.0/examples/jsm/controls/OrbitControls.js';
import { URDFLoader } from 'https://cdn.jsdelivr.net/npm/urdf-loader@1.1.0/dist/urdf-loader.module.js';

const robotTypeEl = document.getElementById('robotType');
const standSelect = document.getElementById('standSelect');
const motionASelect = document.getElementById('motionASelect');
const motionBSelect = document.getElementById('motionBSelect');
const standUpload = document.getElementById('standUpload');
const motionAUpload = document.getElementById('motionAUpload');
const motionBUpload = document.getElementById('motionBUpload');
const buildButton = document.getElementById('buildButton');
const downloadButton = document.getElementById('downloadButton');
const playPauseButton = document.getElementById('playPauseButton');
const frameLabel = document.getElementById('frameLabel');
const frameScrub = document.getElementById('frameScrub');
const stepsInput = document.getElementById('steps');
const holdInput = document.getElementById('hold');
const easingSelect = document.getElementById('easing');
const playbackSpeedInput = document.getElementById('playbackSpeed');
const playbackSpeedLabel = document.getElementById('playbackSpeedLabel');
const recordButton = document.getElementById('recordButton');

const canvasContainer = document.getElementById('canvasContainer');

let renderer, scene, camera, controls;
let robot = null;
let jointNames = [];
let frames = [];
let frameIndex = 0;
let playing = false;
let playbackSpeed = 1.0;
let accumulatedTime = 0;
let lastTime = 0;
let frameRate = 30;
let mediaRecorder = null;
let recordedChunks = [];

const uploadCache = {
  stand: null,
  motionA: null,
  motionB: null,
};

async function fetchJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

async function uploadMotion(file) {
  const form = new FormData();
  form.set('file', file);

  const res = await fetch('/api/upload_motion', {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.error || res.statusText);
  }
  return res.json();
}

async function init() {
  window.addEventListener('error', (ev) => {
    alert(`JavaScript error: ${ev.message}`);
    console.error('Captured error', ev.error);
  });

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0b0b);

  const width = canvasContainer.clientWidth;
  const height = canvasContainer.clientHeight;

  camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
  camera.position.set(1.5, 1.8, 2.5);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  canvasContainer.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.8, 0);
  controls.update();

  const hemi = new THREE.HemisphereLight(0xffffff, 0x222222, 1);
  scene.add(hemi);
  const dir = new THREE.DirectionalLight(0xffffff, 0.9);
  dir.position.set(5, 10, 5);
  scene.add(dir);

  const grid = new THREE.GridHelper(4, 12, 0x444444, 0x222222);
  scene.add(grid);

  window.addEventListener('resize', onResize);

  await populateRobotTypes();

  buildButton.addEventListener('click', onBuild);
  playPauseButton.addEventListener('click', togglePlay);
  downloadButton.addEventListener('click', onDownload);
  recordButton.addEventListener('click', toggleRecording);
  playbackSpeedInput.addEventListener('input', onPlaybackSpeedChanged);
  frameScrub.addEventListener('input', onFrameScrub);

  document.getElementById('addClipButton').addEventListener('click', addClipRow);

  updatePlaybackSpeedLabel();
  frameScrub.min = 1;
  frameScrub.max = 1;
  frameScrub.value = 1;
  animate();
}

function onResize() {
  const width = canvasContainer.clientWidth;
  const height = canvasContainer.clientHeight;
  renderer.setSize(width, height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

async function populateRobotTypes() {
  const types = await fetchJson('/api/robot_types');
  robotTypeEl.innerHTML = types.map(t => `<option value="${t}">${t}</option>`).join('');
  robotTypeEl.addEventListener('change', () => loadRobotConfig(robotTypeEl.value));
  await loadRobotConfig(types[0]);
}

function addClipRow(initialValue = "") {
  const clipList = document.getElementById('clipList');
  const row = document.createElement('div');
  row.className = 'row clip-row';

  const select = document.createElement('select');
  select.innerHTML = standSelect.innerHTML; // copy options
  select.value = initialValue;

  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = '.csv';

  const removeButton = document.createElement('button');
  removeButton.type = 'button';
  removeButton.textContent = '✕';
  removeButton.title = 'Remove this clip';
  removeButton.addEventListener('click', () => row.remove());

  row.appendChild(select);
  row.appendChild(fileInput);
  row.appendChild(removeButton);
  clipList.appendChild(row);
}

async function loadRobotConfig(robotType) {
  const config = await fetchJson(`/api/robot_config?robot_type=${encodeURIComponent(robotType)}`);
  jointNames = config.joint_names;

  await loadRobotModel(config.urdf_url);
  await populateMotionLists(robotType);

  // clear any extra clip rows when switching robot types
  document.getElementById('clipList').innerHTML = '';
}

async function populateMotionLists(robotType) {
  const motions = await fetchJson(`/api/list_motions?robot_type=${encodeURIComponent(robotType)}`);

  const buildOptions = (items) => ["", ...items].map((name) => {
    const label = name || "(none)";
    return `<option value="${name}">${label}</option>`;
  }).join('');

  standSelect.innerHTML = buildOptions(motions);
  motionASelect.innerHTML = buildOptions(motions);
  motionBSelect.innerHTML = buildOptions(motions);

  // update any dynamic clip rows too
  document.querySelectorAll('.clip-row select').forEach((select) => {
    const current = select.value;
    select.innerHTML = buildOptions(motions);
    if (motions.includes(current)) {
      select.value = current;
    }
  });
}

async function loadRobotModel(urdfUrl) {
  if (robot) {
    scene.remove(robot);
    robot.traverse((c) => {
      if (c.geometry) c.geometry.dispose();
      if (c.material) c.material.dispose();
    });
    robot = null;
  }

  const loader = new URDFLoader();
  return new Promise((resolve, reject) => {
    loader.load(
      urdfUrl,
      (loaded) => {
        robot = loaded;
        robot.traverse((obj) => {
          if (obj.material) obj.material.side = THREE.DoubleSide;
        });
        robot.position.set(0, 0, 0);
        robot.quaternion.set(0, 0, 0, 1);
        scene.add(robot);
        resolve();
      },
      undefined,
      (err) => {
        console.error('Failed to load URDF', err);
        alert('Failed to load robot URDF. Check console for details.');
        reject(err);
      }
    );
  });
}

async function onBuild() {
  if (!robot) return;

  buildButton.disabled = true;
  downloadButton.disabled = true;
  playPauseButton.disabled = true;
  recordButton.disabled = true;
  frames = [];
  frameIndex = 0;
  playing = false;
  accumulatedTime = 0;
  playing = false;
  updateFrameLabel();

  const form = new FormData();
  form.set('robot_type', robotTypeEl.value);
  form.set('steps', stepsInput.value);
  form.set('hold', holdInput.value);
  form.set('easing', easingSelect.value);

  const setFieldOrUpload = async (fieldName, selectEl, fileInput) => {
    // Prefer upload cache (file previously uploaded)
    if (uploadCache[fieldName]?.id) {
      form.append(`${fieldName}_id`, uploadCache[fieldName].id);
      return;
    }

    if (fileInput.files.length > 0) {
      const file = fileInput.files[0];
      const cached = uploadCache[fieldName];
      if (!cached || cached.name !== file.name || cached.lastModified !== file.lastModified) {
        const uploaded = await uploadMotion(file);
        uploadCache[fieldName] = {
          id: uploaded.id,
          name: file.name,
          lastModified: file.lastModified,
        };
      }
      form.append(`${fieldName}_id`, uploadCache[fieldName].id);
      return;
    }

    if (selectEl.value) {
      form.append(fieldName, selectEl.value);
    }
  };

  await setFieldOrUpload('stand', standSelect, standUpload);
  await setFieldOrUpload('motionA', motionASelect, motionAUpload);
  await setFieldOrUpload('motionB', motionBSelect, motionBUpload);
  // Additional clip rows
  for (const row of document.querySelectorAll('.clip-row')) {
    const select = row.querySelector('select');
    const fileInput = row.querySelector('input[type=file]');
    if (!select || !fileInput) continue;
    await setFieldOrUpload(`motion`, select, fileInput);
  }
  try {
    const res = await fetch('/api/generate_motion', {
      method: 'POST',
      body: form,
    });
    const data = await res.json();
    if (!res.ok) {
      alert(`Error: ${data.error || res.statusText}`);
      return;
    }
    frames = data.frames;
    frameIndex = 0;
    updateFrameLabel();
    applyFrame(0);
    accumulatedTime = 0;
    lastTime = performance.now();
    downloadButton.disabled = false;
    playPauseButton.disabled = false;
    playPauseButton.textContent = 'Play';
  } catch (err) {
    console.error(err);
    alert('Failed to build motion. See console for details.');
  } finally {
    buildButton.disabled = false;
  }
}

function applyFrame(index) {
  if (!robot || !frames?.length) return;
  index = Math.max(0, Math.min(index, frames.length - 1));
  frameIndex = index;

  const data = frames[index];
  if (!Array.isArray(data) || data.length < 7) return;

  const base = data.slice(0, 7);
  const joints = data.slice(7);

  robot.position.set(base[0], base[1], base[2]);
  robot.quaternion.set(base[3], base[4], base[5], base[6]);

  for (let i = 0; i < jointNames.length && i < joints.length; i += 1) {
    const name = jointNames[i];
    const val = joints[i];
    const joint = robot.joints?.[name];
    if (!joint) continue;
    if (typeof joint.setJointValue === 'function') {
      joint.setJointValue(val);
    } else if (joint.joint && typeof joint.joint.setJointValue === 'function') {
      joint.joint.setJointValue(val);
    } else {
      // fallback: set around object value property
      joint.value = val;
    }
  }

  robot.updateMatrixWorld(true);
  updateFrameLabel();

  if (frameScrub) {
    frameScrub.max = frames.length || 1;
    frameScrub.value = frameIndex + 1;
  }
}

function updateFrameLabel() {
  if (!frames.length) {
    frameLabel.textContent = '—';
    frameScrub.max = 1;
    frameScrub.value = 1;
  } else {
    frameLabel.textContent = `${frameIndex + 1} / ${frames.length}`;
    frameScrub.max = frames.length;
    frameScrub.value = frameIndex + 1;
  }
}

function togglePlay() {
  if (!frames.length) return;
  playing = !playing;
  playPauseButton.textContent = playing ? 'Pause' : 'Play';
}

function onPlaybackSpeedChanged() {
  playbackSpeed = parseFloat(playbackSpeedInput.value) || 1.0;
  updatePlaybackSpeedLabel();
}

function updatePlaybackSpeedLabel() {
  playbackSpeedLabel.textContent = `${playbackSpeed.toFixed(2)}×`;
}

function onFrameScrub() {
  if (!frames.length) return;
  playing = false;
  playPauseButton.textContent = 'Play';
  const idx = Math.max(0, Math.min(frames.length - 1, parseInt(frameScrub.value, 10) - 1));
  applyFrame(idx);
}

function toggleRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    stopRecording();
  } else {
    startRecording();
  }
}

function startRecording() {
  if (!renderer) return;
  recordedChunks = [];
  const stream = renderer.domElement.captureStream(30);
  mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp9' });
  mediaRecorder.ondataavailable = (evt) => {
    if (evt.data && evt.data.size > 0) {
      recordedChunks.push(evt.data);
    }
  };
  mediaRecorder.onstop = () => {
    const blob = new Blob(recordedChunks, { type: 'video/webm' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'recorded_motion.webm';
    a.click();
    URL.revokeObjectURL(url);
    recordButton.textContent = 'Record Video';
  };
  mediaRecorder.start();
  recordButton.textContent = 'Stop Recording';
}

function stopRecording() {
  if (mediaRecorder) {
    mediaRecorder.stop();
  }
}

function animate(time) {
  requestAnimationFrame(animate);
  if (playing && frames.length) {
    const delta = (time - lastTime) / 1000;
    accumulatedTime += delta * playbackSpeed;
    const frameDuration = 1 / frameRate;
    if (accumulatedTime >= frameDuration) {
      const step = Math.max(1, Math.floor(accumulatedTime / frameDuration));
      frameIndex = (frameIndex + step) % frames.length;
      applyFrame(frameIndex);
      accumulatedTime -= step * frameDuration;
    }
  }
  lastTime = time;
  controls.update();
  renderer.render(scene, camera);
}

init().catch((err) => {
  console.error('Failed to initialize viewer', err);
  alert('Failed to initialize viewer. See console for details.');
});
