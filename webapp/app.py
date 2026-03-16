import os
import io
import json
import sys
import uuid
import xml.etree.ElementTree as ET

# Ensure the repository root is on sys.path so we can import interpolation when running
# `python webapp/app.py` from inside the webapp folder.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import numpy as np
import pandas as pd
from flask import Flask, send_from_directory, jsonify, request, render_template, abort
from flask_cors import CORS

import interpolation

# Base paths
DATA_DIR = os.path.join(ROOT_DIR, "lafan1_retargeting_dataset")
ROBOT_DESC_DIR = os.path.join(DATA_DIR, "robot_description")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Uploaded motion cache: id -> filename
uploaded_motions = {}

# Map robot types to their URDF relative path and data folder
ROBOT_CONFIGS = {
    "g1_23dof": {
        "urdf": "g1/g1_23dof.urdf",
        "data_dir": "g1_23dof",
    },
    "g1_29dof": {
        "urdf": "g1/g1_29dof_rev_1_0.urdf",
        "data_dir": "g1_29dof",
    },
    "h1": {
        "urdf": "h1/h1.urdf",
        "data_dir": "h1",
    },
    "h1_2": {
        "urdf": "h1_2/h1_2_wo_hand.urdf",
        "data_dir": "h1_2",
    },
}

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)


def _get_robot_config(robot_type: str):
    if robot_type not in ROBOT_CONFIGS:
        raise KeyError(f"Unknown robot_type '{robot_type}'. Known: {list(ROBOT_CONFIGS.keys())}")
    cfg = ROBOT_CONFIGS[robot_type]
    urdf_path = os.path.join(ROBOT_DESC_DIR, cfg["urdf"])
    data_dir = os.path.join(DATA_DIR, cfg["data_dir"])
    return urdf_path, data_dir


def _available_robot_types():
    available = []
    for robot_type in ROBOT_CONFIGS:
        urdf_path, data_dir = _get_robot_config(robot_type)
        if os.path.isfile(urdf_path) and os.path.isdir(data_dir):
            available.append(robot_type)
    return sorted(available)


def _list_csv_files(data_dir):
    if not os.path.isdir(data_dir):
        return []
    return sorted([f for f in os.listdir(data_dir) if f.lower().endswith(".csv")])


def _load_csv_bytes(stream):
    # pandas can read from file-like object
    df = pd.read_csv(io.BytesIO(stream.read()), header=None)
    return df.values.astype(np.float32)


def _load_csv_path(path):
    return pd.read_csv(path, header=None).values.astype(np.float32)


def _save_uploaded_file(uploaded_file):
    """Save an uploaded file and return an id that can be referenced later."""
    file_id = str(uuid.uuid4())
    filename = f"{file_id}.csv"
    path = os.path.join(UPLOAD_DIR, filename)
    uploaded_file.save(path)
    uploaded_motions[file_id] = path
    return file_id


def _get_uploaded_path(file_id):
    return uploaded_motions.get(file_id)


def _get_joint_order(robot_type: str):
    """Return a list of joint names in the same order as the CSV dof vector.

    This is derived by reading the URDF joint order.
    """
    urdf_path, _ = _get_robot_config(robot_type)

    tree = ET.parse(urdf_path)
    root = tree.getroot()
    joint_names = []

    for joint in root.findall('joint'):
        joint_type = joint.get('type', '')
        # Keep only actuated joints (skip fixed / mimic joints)
        if joint_type in ('revolute', 'continuous', 'prismatic'):
            joint_names.append(joint.get('name'))

    return joint_names


def _get_joint_limits(robot_type: str):
    """Return lower/upper limits for each joint in CSV order."""
    urdf_path, _ = _get_robot_config(robot_type)

    tree = ET.parse(urdf_path)
    root = tree.getroot()

    lower = []
    upper = []
    for joint in root.findall('joint'):
        joint_type = joint.get('type', '')
        if joint_type not in ('revolute', 'continuous', 'prismatic'):
            continue

        if joint_type == 'continuous':
            lower.append(-np.pi)
            upper.append(np.pi)
            continue

        limit = joint.find('limit')
        if limit is None:
            lower.append(-np.inf)
            upper.append(np.inf)
            continue

        lower.append(float(limit.get('lower', '-inf')))
        upper.append(float(limit.get('upper', 'inf')))

    return np.array(lower, dtype=np.float32), np.array(upper, dtype=np.float32)


def _infer_csv_dof_size(robot_type: str):
    try:
        _, data_dir = _get_robot_config(robot_type)
    except KeyError:
        return None

    for filename in _list_csv_files(data_dir):
        path = os.path.join(data_dir, filename)
        try:
            return int(pd.read_csv(path, header=None, nrows=1).shape[1])
        except Exception:
            continue
    return None


def _align_joint_limits(lower_limits, upper_limits, joint_count: int):
    if len(lower_limits) == joint_count and len(upper_limits) == joint_count:
        return lower_limits, upper_limits

    lower = np.full(joint_count, -np.inf, dtype=np.float32)
    upper = np.full(joint_count, np.inf, dtype=np.float32)
    usable = min(joint_count, len(lower_limits), len(upper_limits))
    lower[:usable] = lower_limits[:usable]
    upper[:usable] = upper_limits[:usable]
    return lower, upper


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/robot_description/<path:filename>")
def robot_description(filename):
    return send_from_directory(ROBOT_DESC_DIR, filename)


@app.route("/motion_files/<robot_type>/<path:filename>")
def motion_file(robot_type, filename):
    try:
        _, data_dir = _get_robot_config(robot_type)
    except KeyError:
        abort(404)
    return send_from_directory(data_dir, filename)


@app.route("/api/robot_types")
def api_robot_types():
    return jsonify(_available_robot_types())


@app.route("/api/list_motions")
def api_list_motions():
    robot_type = request.args.get("robot_type", "g1_29dof")
    try:
        _, data_dir = _get_robot_config(robot_type)
    except KeyError:
        return jsonify({"error": "invalid robot_type"}), 400
    motions = _list_csv_files(data_dir)
    return jsonify(motions)


@app.route("/api/upload_motion", methods=["POST"])
def api_upload_motion():
    """Upload a CSV motion file once and refer to it by id."""
    if "file" not in request.files:
        return jsonify({"error": "missing file"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "empty filename"}), 400
    file_id = _save_uploaded_file(f)
    return jsonify({"id": file_id, "filename": f.filename})


@app.route("/api/uploaded_motion/<file_id>")
def api_uploaded_motion(file_id):
    path = _get_uploaded_path(file_id)
    if not path or not os.path.isfile(path):
        abort(404)
    return send_from_directory(UPLOAD_DIR, os.path.basename(path), as_attachment=True)


@app.route("/api/robot_config")
def api_robot_config():
    robot_type = request.args.get("robot_type", "g1_29dof")
    try:
        urdf_path, _ = _get_robot_config(robot_type)
    except KeyError:
        return jsonify({"error": "invalid robot_type"}), 400
    if not os.path.isfile(urdf_path):
        return jsonify({"error": f"missing URDF for robot_type '{robot_type}'"}), 404

    joint_names = _get_joint_order(robot_type)
    lower_limits, upper_limits = _get_joint_limits(robot_type)
    csv_dof_size = _infer_csv_dof_size(robot_type) or (7 + len(joint_names))
    urdf_url = f"/robot_description/{ROBOT_CONFIGS[robot_type]['urdf']}"
    return jsonify({
        "robot_type": robot_type,
        "urdf_url": urdf_url,
        "joint_names": joint_names,
        "csv_dof_size": csv_dof_size,
        "joint_limits": {
            "lower": lower_limits.tolist(),
            "upper": upper_limits.tolist(),
        },
    })


@app.route("/api/generate_motion", methods=["POST"])
def api_generate_motion():
    """Generate a combined motion (stand + motionA [+ motionB]) and return frames."""
    robot_type = request.form.get("robot_type", "g1_29dof")
    steps = int(request.form.get("steps", 60))
    hold = int(request.form.get("hold", 20))
    easing = request.form.get("easing", "minimum_jerk")

    # Load motions: can be provided as a previously uploaded ID, a direct upload, or a filename from dataset
    def load_motion_field(field_name):
        # prefer uploaded file id
        id_field = f"{field_name}_id"
        if id_field in request.form and request.form[id_field]:
            file_id = request.form[id_field]
            path = _get_uploaded_path(file_id)
            if not path or not os.path.isfile(path):
                raise FileNotFoundError(f"Uploaded motion not found: {file_id}")
            return _load_csv_path(path)

        # then direct upload
        if field_name in request.files:
            f = request.files[field_name]
            if f.filename == "":
                return None
            return _load_csv_bytes(f.stream)

        # then dataset filename
        fn = request.form.get(field_name)
        if not fn:
            return None
        try:
            _, data_dir = _get_robot_config(robot_type)
        except KeyError:
            raise
        path = os.path.join(data_dir, fn)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Motion file not found: {path}")
        return _load_csv_path(path)

    try:
        stand = load_motion_field("stand")

        # support multiple clips (preferred)
        motions = []
        for file_id in request.form.getlist("motion_ids") + request.form.getlist("motion_id"):
            path = _get_uploaded_path(file_id)
            if not path or not os.path.isfile(path):
                raise FileNotFoundError(f"Uploaded motion not found: {file_id}")
            motions.append(_load_csv_path(path))

        for fn in request.form.getlist("motions") + request.form.getlist("motion"):
            if not fn:
                continue
            _, data_dir = _get_robot_config(robot_type)
            path = os.path.join(data_dir, fn)
            if not os.path.isfile(path):
                raise FileNotFoundError(f"Motion file not found: {path}")
            motions.append(_load_csv_path(path))

        # fallback to old motionA/motionB behavior
        if not motions:
            motionA = load_motion_field("motionA")
            motionB = load_motion_field("motionB")
            if motionA is not None:
                motions.append(motionA)
            if motionB is not None:
                motions.append(motionB)

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400

    if stand is None or not motions:
        return jsonify({"error": "stand and at least one motion are required"}), 400

    joint_count = max(0, stand.shape[1] - 7)
    lower_limits, upper_limits = _align_joint_limits(*_get_joint_limits(robot_type), joint_count)

    final = interpolation.build_motion(
        stand=stand,
        motions=motions,
        steps=steps,
        hold=hold,
        easing=easing,
        lower_limits=lower_limits,
        upper_limits=upper_limits,
    )

    return jsonify({
        "frames": final.tolist(),
        "shape": final.shape,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
