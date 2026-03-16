#!/usr/bin/env python3
"""
Rerun-based visualization for SmartInterpolationTool
Visualizes G1 robot motions with interpolation and blending.

Usage:
    python rerun_visualize.py [--motion1 walk] [--motion2 wave] [--interpolation-steps 30]
"""

import sys
import argparse
import numpy as np
from pathlib import Path
import rerun as rr
import logging

# Add repo to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from interpolation import build_motion, load_motion, generate_transition

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_robot_config():
    """Load G1 robot configuration from URDF."""
    urdf_path = repo_root / "lafan1_retargeting_dataset/robot_description/g1/g1_29dof_rev_1_0.urdf"
    
    # Robot structure for visualization
    # Format: [x, y, z, qw, qx, qy, qz, 29 joint angles]
    return {
        "root_dof": 7,  # x, y, z, qw, qx, qy, qz
        "joint_count": 29,
        "total_dof": 36,
        "urdf_path": urdf_path,
    }


def log_body(position: np.ndarray, quaternion: np.ndarray, frame_idx: int) -> None:
    """Log robot body position and orientation."""
    # position: [x, y, z]
    # quaternion: [w, x, y, z] (Rerun uses wxyz format)
    rr.log(
        "robot/base",
        rr.Transform3D(translation=position, rotation_xyzw([0, 0, 0, 1])),
    )


def rotation_xyzw(quat):
    """Convert quaternion to Rerun's rotation format (xyzw)."""
    w, x, y, z = quat
    return rr.Quaternion(xyzw=np.array([x, y, z, w]))


def log_frame(frame: np.ndarray, frame_idx: int, time_s: float = None) -> None:
    """Log a single motion frame to Rerun."""
    if time_s is None:
        time_s = frame_idx * 0.033  # ~30fps
    
    # Set time for this frame
    rr.set_time_seconds("time", time_s)
    
    # Extract components
    position = frame[:3]  # x, y, z
    quaternion = frame[3:7]  # w, x, y, z
    joint_angles = frame[7:]  # 29 joints
    
    # Log base transform
    rr.log(
        "robot/base",
        rr.Transform3D(
            translation=position,
            rotation=rotation_xyzw(quaternion),
        ),
    )
    
    # Log joint angles as scalars (for inspection)
    for i, angle in enumerate(joint_angles):
        rr.log(f"robot/joint_{i:02d}", rr.Scalar(float(angle)))


def list_available_motions() -> dict:
    """List all available motion CSVs."""
    motion_dir = repo_root / "lafan1_retargeting_dataset/g1_29dof"
    motions = {}
    
    if motion_dir.exists():
        for csv_file in motion_dir.glob("*.csv"):
            motions[csv_file.stem] = csv_file
    
    return motions


def main():
    parser = argparse.ArgumentParser(
        description="Visualize G1 robot motions with real-time interpolation"
    )
    parser.add_argument(
        "--motion1",
        default="stand_pose",
        help="First motion CSV (default: stand_pose)",
    )
    parser.add_argument(
        "--motion2",
        default="motion_walk",
        help="Second motion CSV (default: motion_walk)",
    )
    parser.add_argument(
        "--interpolation-steps",
        type=int,
        default=30,
        help="Number of transition frames (default: 30)",
    )
    parser.add_argument(
        "--hold-frames",
        type=int,
        default=5,
        help="Number of frames to hold stand pose between motions (default: 5)",
    )
    parser.add_argument(
        "--list-motions",
        action="store_true",
        help="List available motions and exit",
    )
    parser.add_argument(
        "--easing",
        default="minimum-jerk",
        choices=["linear", "smoothstep", "minimum-jerk"],
        help="Interpolation easing function (default: minimum-jerk)",
    )
    
    args = parser.parse_args()
    
    # Initialize Rerun
    rr.init("SmartInterpolationTool", spawn=True)
    
    # List motions if requested
    available = list_available_motions()
    if args.list_motions:
        logger.info("Available motions:")
        for name, path in available.items():
            logger.info(f"  - {name}: {path}")
        return
    
    # Log available motions
    logger.info(f"Available motions: {list(available.keys())}")
    
    # Load motions
    logger.info(f"Loading motion1: {args.motion1}")
    logger.info(f"Loading motion2: {args.motion2}")
    
    if args.motion1 not in available:
        logger.error(f"Motion '{args.motion1}' not found. Available: {list(available.keys())}")
        return
    
    if args.motion2 not in available:
        logger.error(f"Motion '{args.motion2}' not found. Available: {list(available.keys())}")
        return
    
    try:
        motion1 = load_motion(str(available[args.motion1]))
        motion2 = load_motion(str(available[args.motion2]))
        
        logger.info(f"Loaded {args.motion1}: {motion1.shape}")
        logger.info(f"Loaded {args.motion2}: {motion2.shape}")
        
        # For stand_pose, use it as transition reference
        if args.motion1 == "stand_pose":
            stand = motion1
            # Use motion2 as the main animation
            motion_to_use = motion2
        else:
            stand = motion1[:1]  # Use first frame as stand
            motion_to_use = motion2
        
        # Build merged motion with smooth transition
        logger.info(f"Building interpolated motion with {args.interpolation_steps} transition frames...")
        merged = build_motion(
            stand=stand,
            motions=[motion_to_use],
            steps=args.interpolation_steps,
            hold=args.hold_frames,
        )
        
        logger.info(f"Total frames to visualize: {merged.shape[0]}")
        
        # Log all frames
        for frame_idx, frame in enumerate(merged):
            log_frame(frame, frame_idx)
            if (frame_idx + 1) % 10 == 0:
                logger.info(f"Logged {frame_idx + 1}/{merged.shape[0]} frames")
        
        logger.info("✓ Visualization complete! Use Rerun UI to play timeline.")
        logger.info("  - Play/pause with spacebar")
        logger.info("  - Scrub timeline with mouse")
        logger.info("  - Adjust playback speed in controls")
        
    except Exception as e:
        logger.error(f"Error during visualization: {e}", exc_info=True)
        return


if __name__ == "__main__":
    main()
