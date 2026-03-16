# SMARTINTERP-SETUP_INTEGRATION_ENABLEMENT.md

## Executive Summary

This document defines the complete setup and validation of SmartInterpolationTool as a functional, tested, production-ready application for Unitree G1 robot motion manipulation.

## Objective

Create a complete, tested, and deployable SmartInterpolationTool that allows users to:
1. Merge multiple CSV robot motion files intelligently
2. Visualize CSV motion data and interpolations in real-time via a modern web interface
3. Validate and review that interface on browserless machines using a headless screenshot workflow
3. Apply smooth interpolation that respects physical robot constraints
4. Edit CSVs directly in the web app with live feedback
5. Leverage LAFAN1 dataset visualization techniques
6. Support Unitree G1 29-DOF URDF constraints

## Primary Target Systems

- **Backend**: Python interpolation engine (`interpolation.py`)
- **Frontend**: Modern web app with dark theme (Flask + HTML5 + Three.js/Babylon.js)
- **Browserless validation**: `smartinterp-setup/browserless_gui_check.py` using Playwright + Chromium
- **Data**: CSV motion files (root position, root quaternion, 29 joint angles)
- **Robot Model**: Unitree G1 29-DOF URDF from lafan1_retargeting_dataset

## Specific Capabilities Required

### 1. Multi-CSV Intelligent Merging
- Accept 2 or more CSV motion files
- Automatically generate interpolated transitions between files
- Respect physical joint limits and avoid hard/jerky movements
- Support smooth easing functions (minimum-jerk, smoothstep, linear)
- Generate stand pose transitions between motions

### 2. Modern Web Visualization Interface
- **Design**: Video-editor-like UX (timeline, tracks, clips)
- **Theme**: Dark mode, sleek, professional appearance
- **Real-time preview**: Show interpolation as parameters change
- **Browserless review**: Produce a GUI screenshot artifact without opening a browser window
- **Live editing**: Edit CSV values and see immediate updates
- **Playback controls**: Play/pause, speed slider, frame scrubber
- **Recording**: Export visualization to WebM video

### 3. LAFAN1 Integration
- Use lafan1 visualization techniques for motion rendering
- Access LAFAN1 URDF files for robot model
- Leverage LAFAN1 dataset format understanding

### 4. Physical Constraints
- Enforce Unitree G1 29-DOF joint limits
- Generate smooth trajectories that avoid hard movements
- Apply realistic acceleration/deceleration profiles

### 5. CSV Workflow
- Upload CSV files through web interface
- Cache uploaded files server-side (avoid re-uploading)
- Parse CSV format: `[root_pos (3), root_quat (4), 29 joint angles]`
- Save/export merged motions as new CSV files

### 6. Complete Dependencies
- Comprehensive `requirements.txt` with pinned versions
- All dependencies verified and tested locally

## What Constitutes "Complete"

This task is complete ONLY when:

1. **Web App Running**: Flask server starts without errors
2. **CSV Upload Works**: Can upload 2 or more CSV files through UI
3. **Merge Operation**: Successfully merge 2 CSVs with stand pose in between
4. **Live Visualization**: See rendered motion in browser or validate it via a browserless Chromium screenshot on the target machine
5. **Real-time Feedback**: Change interpolation parameters → see immediate changes
6. **Full Test Suite**: All workflows tested end-to-end on local laptop:
   - Upload 2 motion CSVs
   - Set stand pose
   - Apply interpolation between them
   - Visualize result or capture browserless GUI proof
   - Verify smooth, physically realistic motion
   - Export result
7. **Requirements Reproducibility**: Fresh conda env can install all deps from requirements.txt
8. **Code Quality**: No runtime errors, proper error handling in web app

## Key Dependencies & Preconditions

### Environment
- Python 3.10+ (conda environment)
- macOS development machine or Ubuntu remote instance
- Headless Chromium available through Playwright
- WebGL-capable graphics stack sufficient for Chromium headless rendering

### Code Repositories
- Existing SmartInterpolationTool codebase
- LAFAN1 retargeting dataset (already cloned) for URDF files
- Unitree G1 documentation for joint limits

### Data Files
- Sample CSV motion files for testing
- G1 URDF model (from lafan1_retargeting_dataset)

## Success Metrics

1. **Functional**: All features work as specified without errors
2. **Tested**: Multi-CSV merge tested with real data on local machine
3. **Browserless-ready**: GUI validation passes and a screenshot artifact is produced on machines without browser access
3. **Reproducible**: Fresh conda env + requirements.txt = working system
4. **Performant**: Web app responsive, visualization smooth (30+ fps)
5. **Robust**: Proper error handling, user feedback for invalid inputs
6. **Documented**: Code comments, README updated, remediation log complete

## Upstream Context

- **SmartInterpolationTool**: Existing Python interpolation engine
- **LAFAN1 Dataset**: Already available in repo, provides URDF and visualization patterns
- **Unitree G1**: 29-DOF robot with specific joint limits
- **Web Framework**: Flask for backend server
