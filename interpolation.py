import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R, Slerp
import argparse


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def minimum_jerk(t):
    """Minimum-jerk easing curve (0..1)."""
    t = np.clip(t, 0.0, 1.0)
    return 10*t**3 - 15*t**4 + 6*t**5


def smoothstep(t):
    """Smoothstep easing curve."""
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def linear(t):
    """Linear interpolation."""
    return np.clip(t, 0.0, 1.0)


def get_easing(easing):
    if easing == "smoothstep":
        return smoothstep
    if easing == "linear":
        return linear
    # default
    return minimum_jerk


def slerp(q0, q1, t):
    # SciPy's Rotation supports Slerp via a separate helper.
    key_times = [0.0, 1.0]
    rotations = R.from_quat([q0, q1])
    slerp_fn = Slerp(key_times, rotations)
    return slerp_fn([t]).as_quat()[0]


def interpolate_root(root0, root1, t, easing="minimum_jerk"):
    """Smoothly interpolate a root pose (position + quaternion)."""
    s = get_easing(easing)(t)
    pos = (1 - s) * root0[:3] + s * root1[:3]
    rot = slerp(root0[3:], root1[3:], s)
    return np.concatenate([pos, rot])


def interpolate_joints(q0, q1, t, easing="minimum_jerk"):
    """Interpolate joint angles using easing and shortest-angle path."""
    s = get_easing(easing)(t)
    # Use shortest angle difference to avoid interpolation across the 2*pi boundary
    delta = (q1 - q0 + np.pi) % (2 * np.pi) - np.pi
    return q0 + s * delta


# ---------------------------------------------------
# CSV Motion
# ---------------------------------------------------

def load_motion(path):
    return pd.read_csv(path, header=None).values


def save_motion(path, motion):
    pd.DataFrame(motion).to_csv(path, header=False, index=False)


def frame_split(frame):
    root = frame[:7]
    joints = frame[7:]
    return root, joints


def frame_merge(root, joints):
    return np.concatenate([root, joints])


# ---------------------------------------------------
# Transition generation
# ---------------------------------------------------

def generate_transition(frame_a, frame_b, steps, easing="minimum_jerk", lower_limits=None, upper_limits=None):
    """Generate an interpolated transition between two frames.

    The output includes both endpoints (frame_a and frame_b).

    Args:
        frame_a: (N,) array for first frame.
        frame_b: (N,) array for last frame.
        steps: Number of frames to generate (includes endpoints).
        easing: Easing curve to use (minimum_jerk/smoothstep/linear).
        lower_limits: Optional (M,) lower joint limits for the joints (exclude root).
        upper_limits: Optional (M,) upper joint limits.
    """

    root_a, q_a = frame_split(frame_a)
    root_b, q_b = frame_split(frame_b)

    if steps <= 1:
        return np.array([frame_a, frame_b])

    frames = []
    for t in np.linspace(0.0, 1.0, steps):
        root = interpolate_root(root_a, root_b, t, easing=easing)
        q = interpolate_joints(q_a, q_b, t, easing=easing)

        # clamp to joint limits when available
        if lower_limits is not None and upper_limits is not None:
            q = np.clip(q, lower_limits, upper_limits)

        frames.append(frame_merge(root, q))

    return np.array(frames)


# ---------------------------------------------------
# World alignment
# ---------------------------------------------------

def align_motion(base_motion, target_motion):

    offset = base_motion[-1,:2] - target_motion[0,:2]

    target_motion[:,0] += offset[0]
    target_motion[:,1] += offset[1]

    return target_motion


# ---------------------------------------------------
# Build final motion
# ---------------------------------------------------

def build_motion(
    stand,
    motions,
    steps=60,
    hold=20,
    easing="minimum_jerk",
    lower_limits=None,
    upper_limits=None,
):
    """Stitch together a sequence of motions with stand transitions.

    Args:
        stand: (T, N) stand motion (typically a single frame repeated).
        motions: List of (T, N) motions to play in order.
        steps: Transition frames count.
        hold: Number of hold frames between segments.
        easing: Easing curve for transitions (minimum_jerk/smoothstep/linear).
        lower_limits/upper_limits: Optional joint limits (exclude root).
    """

    if not motions:
        return stand

    result = []
    stand_frame = stand[0]

    # ---- Stand before first clip ----
    first = motions[0]
    trans = generate_transition(
        stand_frame,
        first[0],
        steps,
        easing=easing,
        lower_limits=lower_limits,
        upper_limits=upper_limits,
    )
    result.append(trans)
    result.append(np.repeat(stand_frame[None, :], hold, axis=0))
    result.append(first)

    prev = first
    for next_motion in motions[1:]:
        trans = generate_transition(
            prev[-1],
            stand_frame,
            steps,
            easing=easing,
            lower_limits=lower_limits,
            upper_limits=upper_limits,
        )
        result.append(trans)
        result.append(np.repeat(stand_frame[None, :], hold, axis=0))

        next_motion = align_motion(prev, next_motion)
        trans = generate_transition(
            stand_frame,
            next_motion[0],
            steps,
            easing=easing,
            lower_limits=lower_limits,
            upper_limits=upper_limits,
        )
        result.append(trans)
        result.append(next_motion)
        prev = next_motion

    trans = generate_transition(
        prev[-1],
        stand_frame,
        steps,
        easing=easing,
        lower_limits=lower_limits,
        upper_limits=upper_limits,
    )
    result.append(trans)
    result.append(np.repeat(stand_frame[None, :], hold, axis=0))

    return np.vstack(result)


# ---------------------------------------------------
# Main
# ---------------------------------------------------

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--motionA", required=True)
    parser.add_argument("--motionB", default=None)
    parser.add_argument("--stand", required=True)
    parser.add_argument("--output", default="stitched_motion.csv")

    args = parser.parse_args()

    motionA = load_motion(args.motionA)
    stand = load_motion(args.stand)

    motionB = None
    if args.motionB:
        motionB = load_motion(args.motionB)

    # Backward compatible call: build a sequence from motionA and motionB
    motions = [motionA]
    if motionB is not None:
        motions.append(motionB)

    final_motion = build_motion(
        stand=stand,
        motions=motions,
    )

    save_motion(args.output, final_motion)


if __name__ == "__main__":
    main()