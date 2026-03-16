#!/usr/bin/env python3
"""Headless-friendly Rerun visualization for SmartInterpolationTool.

This script builds an interpolated motion and records it to a Rerun `.rrd`
artifact by default so it can run on remote instances without a browser or GUI.
Optionally, it can also spawn the Rerun viewer when a desktop session exists.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import rerun as rr

repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from interpolation import build_motion, load_motion  # noqa: E402


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_ARTIFACT_DIR = repo_root / "smartinterp-setup" / "artifacts" / "rerun"
DEFAULT_RRD_PATH = DEFAULT_ARTIFACT_DIR / "smartinterp_visualization.rrd"
DEFAULT_SUMMARY_PATH = DEFAULT_ARTIFACT_DIR / "smartinterp_visualization_summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a non-web Rerun visualization artifact for SmartInterpolationTool.")
    parser.add_argument("--motion1", default="stand_pose", help="First motion CSV stem (default: stand_pose).")
    parser.add_argument("--motion2", default="motion_walk", help="Second motion CSV stem (default: motion_walk).")
    parser.add_argument("--interpolation-steps", type=int, default=30, help="Transition frame count.")
    parser.add_argument("--hold-frames", type=int, default=5, help="Stand-pose hold frames between clips.")
    parser.add_argument("--easing", default="minimum_jerk", choices=["linear", "smoothstep", "minimum_jerk"], help="Interpolation easing.")
    parser.add_argument("--frame-rate", type=float, default=30.0, help="Playback frame rate used in the recording.")
    parser.add_argument("--list-motions", action="store_true", help="List available motion CSV stems and exit.")
    parser.add_argument("--spawn-viewer", action="store_true", help="Also launch the Rerun desktop viewer.")
    parser.add_argument("--output-rrd", default=str(DEFAULT_RRD_PATH), help="Where to save the `.rrd` recording.")
    parser.add_argument("--summary-json", default=str(DEFAULT_SUMMARY_PATH), help="Where to save a JSON summary.")
    return parser.parse_args()


def list_available_motions() -> dict[str, Path]:
    motion_dir = repo_root / "lafan1_retargeting_dataset" / "g1_29dof"
    motions: dict[str, Path] = {}
    if motion_dir.exists():
        for csv_file in sorted(motion_dir.glob("*.csv")):
            motions[csv_file.stem] = csv_file
    return motions


def resolve_motion(name: str, available: dict[str, Path]) -> Path:
    if name not in available:
        raise KeyError(f"Motion '{name}' not found. Available motions: {sorted(available)}")
    return available[name]


def build_recording(motion1_name: str, motion2_name: str, steps: int, hold: int, easing: str) -> tuple[np.ndarray, dict]:
    available = list_available_motions()
    motion1 = load_motion(str(resolve_motion(motion1_name, available)))
    motion2 = load_motion(str(resolve_motion(motion2_name, available)))

    if motion1_name == "stand_pose":
        stand = motion1
        motions = [motion2]
    else:
        stand = motion1[:1]
        motions = [motion2]

    merged = build_motion(
        stand=stand,
        motions=motions,
        steps=steps,
        hold=hold,
        easing=easing,
    )

    root_positions = merged[:, :3]
    joint_angles = merged[:, 7:]

    summary = {
        "motion1": motion1_name,
        "motion2": motion2_name,
        "interpolation_steps": steps,
        "hold_frames": hold,
        "easing": easing,
        "frame_count": int(merged.shape[0]),
        "dof": int(merged.shape[1]),
        "joint_count": int(max(0, merged.shape[1] - 7)),
        "root_position_min": root_positions.min(axis=0).round(6).tolist(),
        "root_position_max": root_positions.max(axis=0).round(6).tolist(),
        "joint_angle_min": float(np.min(joint_angles)) if joint_angles.size else 0.0,
        "joint_angle_max": float(np.max(joint_angles)) if joint_angles.size else 0.0,
    }
    return merged, summary


def configure_rerun(output_rrd: Path, spawn_viewer: bool) -> None:
    output_rrd.parent.mkdir(parents=True, exist_ok=True)
    rr.init("SmartInterpolationTool", spawn=spawn_viewer)
    rr.save(str(output_rrd))


def log_static_overview(merged: np.ndarray) -> None:
    root_positions = merged[:, :3]
    rr.log(
        "world/root_trajectory",
        rr.LineStrips3D([root_positions], colors=[[80, 170, 255]], radii=[0.01]),
        static=True,
    )
    rr.log(
        "world/root_endpoints",
        rr.Points3D(
            [root_positions[0], root_positions[-1]],
            colors=[[0, 255, 140], [255, 90, 90]],
            radii=[0.04, 0.04],
        ),
        static=True,
    )


def log_frames(merged: np.ndarray, frame_rate: float) -> None:
    dt = 1.0 / frame_rate
    for frame_idx, frame in enumerate(merged):
        rr.set_time("frame", sequence=frame_idx)
        rr.set_time("time", duration=frame_idx * dt)

        position = frame[:3]
        quaternion = frame[3:7]
        joints = frame[7:]

        rr.log("robot/base_position", rr.Points3D([position], colors=[[255, 220, 90]], radii=[0.03]))

        rr.log("plots/root_x", rr.Scalars([float(position[0])]))
        rr.log("plots/root_y", rr.Scalars([float(position[1])]))
        rr.log("plots/root_z", rr.Scalars([float(position[2])]))
        rr.log("plots/root_qw", rr.Scalars([float(quaternion[0])]))
        rr.log("plots/root_qx", rr.Scalars([float(quaternion[1])]))
        rr.log("plots/root_qy", rr.Scalars([float(quaternion[2])]))
        rr.log("plots/root_qz", rr.Scalars([float(quaternion[3])]))

        for joint_idx, angle in enumerate(joints):
            rr.log(f"plots/joint_{joint_idx:02d}", rr.Scalars([float(angle)]))


def save_summary(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    available = list_available_motions()

    if args.list_motions:
        for name in sorted(available):
            print(name)
        return 0

    output_rrd = Path(args.output_rrd).expanduser().resolve()
    summary_json = Path(args.summary_json).expanduser().resolve()

    try:
        merged, summary = build_recording(
            motion1_name=args.motion1,
            motion2_name=args.motion2,
            steps=args.interpolation_steps,
            hold=args.hold_frames,
            easing=args.easing,
        )
    except Exception as exc:
        logger.error("Failed to build recording: %s", exc)
        return 1

    summary["frame_rate"] = args.frame_rate
    summary["duration_seconds"] = round(summary["frame_count"] / args.frame_rate, 3)
    summary["output_rrd"] = str(output_rrd)
    summary["summary_json"] = str(summary_json)

    configure_rerun(output_rrd=output_rrd, spawn_viewer=args.spawn_viewer)
    log_static_overview(merged)
    log_frames(merged, frame_rate=args.frame_rate)
    save_summary(summary_json, summary)

    logger.info("Saved Rerun recording: %s", output_rrd)
    logger.info("Saved summary JSON: %s", summary_json)
    logger.info(
        "Built %s frames from %s -> %s using %s easing",
        summary["frame_count"],
        args.motion1,
        args.motion2,
        args.easing,
    )
    if args.spawn_viewer:
        logger.info("Viewer spawned. Open the Rerun desktop app window to inspect the recording.")
    else:
        logger.info("Headless mode complete. Copy the `.rrd` file to another machine if you want to inspect it interactively.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
