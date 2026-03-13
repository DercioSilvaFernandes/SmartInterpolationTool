import numpy as np
import os

# Directory where we'll save CSV files
data_dir = "/Users/dercio.fernandes/dm-isaac-g1/agents/SmartInterpolationTool/lafan1_retargeting_dataset/g1_29dof"

# Use consistent frame count for all motions
NUM_FRAMES = 30

# Create stand pose (neutral stance - all joints at 0, identity quaternion)
stand_pose = np.zeros((NUM_FRAMES, 36))
stand_pose[:, 3] = 1.0  # Set quaternion to identity [0, 0, 0, 1] (w=1 is at index 3)
np.savetxt(os.path.join(data_dir, "stand_pose.csv"), stand_pose, delimiter=',', fmt='%.6f')

# Create walking motion (simplified - hip pitch oscillation, identity quat)
walk_motion = np.zeros((NUM_FRAMES, 36))
walk_motion[:, 3] = 1.0  # Identity quaternion
for i in range(NUM_FRAMES):
    t = i / NUM_FRAMES
    # Add position variation
    walk_motion[i, 0] = 0.1 * t  # Forward motion in x
    # Left hip pitch: oscillate (index 9)
    walk_motion[i, 9] = 0.3 * np.sin(2 * np.pi * t)
    # Right hip pitch: phase-shifted (index 23)
    walk_motion[i, 23] = 0.3 * np.sin(2 * np.pi * t + np.pi)
np.savetxt(os.path.join(data_dir, "motion_walk.csv"), walk_motion, delimiter=',', fmt='%.6f')

# Create waving motion (arm waving, identity quat)
wave_motion = np.zeros((NUM_FRAMES, 36))
wave_motion[:, 3] = 1.0  # Identity quaternion
for i in range(NUM_FRAMES):
    t = i / NUM_FRAMES
    # Add position variation
    wave_motion[i, 0] = 0.1 + 0.05 * np.sin(4 * np.pi * t)  # X position
    # Right shoulder pitch: move arm up and down
    wave_motion[i, 20] = 0.5 * np.sin(4 * np.pi * t)
    # Right elbow: slightly bent
    wave_motion[i, 24] = 0.3 + 0.2 * np.sin(4 * np.pi * t)
np.savetxt(os.path.join(data_dir, "motion_wave.csv"), wave_motion, delimiter=',', fmt='%.6f')

print(f"✓ Created stand_pose.csv ({stand_pose.shape})")
print(f"✓ Created motion_walk.csv ({walk_motion.shape})")
print(f"✓ Created motion_wave.csv ({wave_motion.shape})")
print(f"\nAll files saved to: {data_dir}")
print(f"Format: [x, y, z, qw, qx, qy, qz, 29 joint angles] = 36 values per row")


