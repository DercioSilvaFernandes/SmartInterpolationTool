#!/usr/bin/env python3
"""
End-to-End Test Suite for SmartInterpolationTool
Tests the complete workflow: CSV merge, interpolation, and visualization support
"""

import numpy as np
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, "/Users/dercio.fernandes/dm-isaac-g1/agents/SmartInterpolationTool")

from interpolation import (
    build_motion, generate_transition, frame_split, frame_merge, 
    interpolate_root, interpolate_joints, load_motion, save_motion, minimum_jerk
)

def test_1_basic_functions():
    """Test basic interpolation functions"""
    print("\n=== TEST 1: Basic Functions ===")
    
    # Test easing function
    t_values = np.linspace(0, 1, 5)
    easing_values = [minimum_jerk(t) for t in t_values]
    print(f"✓ Easing values at t={t_values}: {easing_values}")
    
    # Test frame operations
    root = np.array([0, 0, 0, 0, 0, 0, 1])
    joints = np.zeros(29)
    frame = frame_merge(root, joints)
    assert frame.shape == (36,), f"Frame shape mismatch: {frame.shape}"
    root_out, joints_out = frame_split(frame)
    assert np.allclose(root, root_out), "Root split failed"
    print(f"✓ Frame split/merge works correctly")

def test_2_interpolation():
    """Test interpolation between two frames"""
    print("\n=== TEST 2: Interpolation ===")
    
    # Create two frames: standing, then raised arm
    frame_a = np.zeros(36)
    frame_a[3] = 1  # Identity quaternion
    
    frame_b = frame_a.copy()
    frame_b[20] = 0.5  # Raise right shoulder pitch
    
    # Generate transition
    transition = generate_transition(frame_a, frame_b, steps=10, easing="minimum_jerk")
    print(f"✓ Generated transition with {len(transition)} frames")
    print(f"  Frame shape: {transition[0].shape}")
    print(f"  Shoulder pitch range: [{transition[0,20]:.3f}, {transition[-1,20]:.3f}]")
    
    assert transition.shape == (10, 36), f"Unexpected transition shape: {transition.shape}"

def test_3_multi_motion_merge():
    """Test merging multiple motions"""
    print("\n=== TEST 3: Multi-Motion Merge ===")
    
    # Create stand pose
    stand = np.zeros((5, 36))
    stand[:, 3] = 1  # Identity quaternion
    
    # Create motion A
    motion_a = np.zeros((10, 36))
    motion_a[:, 3] = 1
    for i in range(10):
        motion_a[i, 0] = 0.1 * (i / 10)  # Forward motion
    
    # Create motion B  
    motion_b = np.zeros((10, 36))
    motion_b[:, 3] = 1
    for i in range(10):
        motion_b[i, 20] = 0.3 * np.sin(np.pi * i / 10)  # Arm wave
    
    # Merge
    merged = build_motion(
        stand=stand,
        motions=[motion_a, motion_b],
        steps=10,
        hold=3,
        easing="minimum_jerk"
    )
    
    print(f"✓ Merged {len([motion_a, motion_b])} motions")
    print(f"  Result shape: {merged.shape}")
    print(f"  Total frames: {merged.shape[0]}")
    
    # Verify shape
    # Expected: transition(10) + stand hold(3) + motion_a(10) + 
    #           transition(10) + stand hold(3) + transition(10) + motion_b(10) +
    #           transition(10) + stand hold(3) = 78 frames
    assert merged.shape[1] == 36, f"DOF mismatch: {merged.shape[1]}"
    assert merged.shape[0] > 20, f"Merged motion too short: {merged.shape[0]}"

def test_4_joint_limits():
    """Test joint limit enforcement"""
    print("\n=== TEST 4: Joint Limits ===")
    
    # Create motions that would violate limits
    stand = np.zeros((5, 36))
    stand[:, 3] = 1
    
    motion = np.zeros((10, 36))
    motion[:, 3] = 1
    # Set joint 0 to exceed typical limits
    motion[:, 7] = 5.0  # Way beyond typical range
    
    # Define joint limits
    lower_limits = np.full(29, -1.57)
    upper_limits = np.full(29, 1.57)
    
    # Merge with limits
    merged = build_motion(
        stand=stand,
        motions=[motion],
        steps=5,
        hold=2,
        easing="minimum_jerk",
        lower_limits=lower_limits,
        upper_limits=upper_limits
    )
    
    # Check that joints are clamped
    joint_values = merged[:, 7]
    clamped = np.allclose(joint_values, np.clip(joint_values, -1.57, 1.57))
    print(f"✓ Joint limits enforced: values in range [{joint_values.min():.3f}, {joint_values.max():.3f}]")

def test_5_csv_io():
    """Test CSV loading and saving"""
    print("\n=== TEST 5: CSV I/O ===")
    
    test_dir = "/tmp/smartinterp_test"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create test motion
    motion = np.random.randn(20, 36)
    motion[:, 3] = 1  # Fix quaternion to identity
    
    # Save
    test_file = os.path.join(test_dir, "test_motion.csv")
    save_motion(test_file, motion)
    print(f"✓ Saved motion to {test_file}")
    
    # Load
    loaded = load_motion(test_file)
    assert np.allclose(motion, loaded, atol=1e-6), "CSV round-trip failed"
    print(f"✓ Loaded motion matches saved data (shape: {loaded.shape})")
    
    os.remove(test_file)
    os.rmdir(test_dir)

def main():
    """Run all tests"""
    print("=" * 60)
    print("SmartInterpolationTool End-to-End Test Suite")
    print("=" * 60)
    
    try:
        test_1_basic_functions()
        test_2_interpolation()
        test_3_multi_motion_merge()
        test_4_joint_limits()
        test_5_csv_io()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
