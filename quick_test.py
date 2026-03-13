#!/usr/bin/env python3
"""Quick validation tests for SmartInterpolationTool"""

import sys
sys.path.insert(0, "/Users/dercio.fernandes/dm-isaac-g1/agents/SmartInterpolationTool")

import numpy as np
from interpolation import build_motion, generate_transition

print("Running core functionality tests...")

# Test 1: Basic transition
frame_a = np.zeros(36)
frame_a[3] = 1  # Identity quaternion
frame_b = np.zeros(36)
frame_b[3] = 1
frame_b[20] = 0.5

trans = generate_transition(frame_a, frame_b, steps=10)
assert trans.shape == (10, 36), f"Transition shape error: {trans.shape}"
print(f"✓ Test 1: Generated {len(trans)} transition frames")

# Test 2: Multi-motion merge
stand = np.zeros((5, 36))
stand[:, 3] = 1
m1 = np.zeros((10, 36))
m1[:, 3] = 1
m2 = np.zeros((10, 36))
m2[:, 3] = 1

merged = build_motion(stand=stand, motions=[m1, m2], steps=8, hold=2)
assert merged.shape[1] == 36, f"Merged shape error: {merged.shape}"
assert merged.shape[0] > 20, f"Merged too short: {merged.shape[0]}"
print(f"✓ Test 2: Merged 2 motions into {merged.shape[0]} frames total")

# Test 3: With joint limits
lower = np.full(29, -1.57)
upper = np.full(29, 1.57)
merged_lim = build_motion(stand=stand, motions=[m1], steps=5, hold=2,
                          lower_limits=lower, upper_limits=upper)
assert merged_lim.shape == (36, 36), f"Merged with limits shape: {merged_lim.shape}"
print(f"✓ Test 3: Built motion with joint limits: {merged_lim.shape}")

print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
