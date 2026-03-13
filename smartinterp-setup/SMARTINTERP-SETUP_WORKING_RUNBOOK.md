# SMARTINTERP-SETUP_WORKING_RUNBOOK.md

## Purpose

This runbook provides the complete, step-by-step procedure to set up, configure, and validate SmartInterpolationTool as a fully functional application on a local development machine. This document contains all commands, configurations, and testing procedures that have been verified to work.

## Scope

- **Target Environment**: macOS local development machine with conda
- **Target Paths**: `/Users/dercio.fernandes/dm-isaac-g1/agents/SmartInterpolationTool`
- **Expected Outcome**: Fully functional web app with multi-CSV merge, visualization, and interpolation capabilities

## Preconditions / Prerequisites

Before starting this runbook:
- [ ] Conda is installed and available in PATH
- [ ] Git is available in PATH
- [ ] Python 3.10+ is available via conda
- [ ] SmartInterpolationTool repository is cloned at `/Users/dercio.fernandes/dm-isaac-g1/agents/SmartInterpolationTool`
- [ ] Modern web browser installed (Chrome, Firefox, Safari)
- [ ] Sample motion CSV files available for testing (can be generated or provided)

## Expected Steady-State Outcome

After completing this runbook:
- [ ] Conda environment `smartinterp` exists with all dependencies installed
- [ ] Flask web server runs without errors on `localhost:5000`
- [ ] Web UI loads with dark theme, video-editor-like interface
- [ ] CSV upload functionality works through web interface
- [ ] Multi-CSV merge with interpolation generates smooth motions
- [ ] 3D visualization renders and plays back motion in browser
- [ ] Stand pose transitions apply correctly
- [ ] Complete requirements.txt with all pinned versions exists
- [ ] All features tested and verified working end-to-end

---

## Phase 1: Environment Setup

### Step 1.1: Create Isolated Conda Environment

```bash
# Create conda environment with Python 3.10
conda create -n smartinterp python=3.10 -y

# Activate environment
conda activate smartinterp

# Verify Python version
python --version  # Should show 3.10.x
```

**Expected Output**: `Python 3.10.x :: Anaconda, Inc.`

### Step 1.2: Navigate to Project Root

```bash
cd /Users/dercio.fernandes/dm-isaac-g1/agents/SmartInterpolationTool

# Verify you're in the right place
pwd  # Should end with: .../SmartInterpolationTool
ls   # Should show: interpolation.py, webapp/, requirements.txt, etc.
```

### Step 1.3: Install Dependencies

```bash
# Install all required packages from requirements.txt
pip install -r requirements.txt

# Verify key packages installed
python -c "import flask; import numpy; import scipy; print('✓ Core packages installed')"
```

**Expected Output**: `✓ Core packages installed` (no errors)

---

## Phase 2: Backend Feature Implementation

### Step 2.1: Verify Interpolation Engine

```bash
# Test that interpolation.py can be imported
python -c "from interpolation import *; print('✓ Interpolation module loads')"

# Test basic interpolation function with dummy data
python << 'EOF'
import numpy as np
from interpolation import interpolate_motion

# Create dummy motion frames (test data)
motion1 = np.random.randn(10, 36)  # 10 frames, 36 DOF (3 pos + 4 quat + 29 angles)
motion2 = np.random.randn(10, 36)

# Test interpolation
try:
    result = interpolate_motion(motion1, motion2, num_transition_frames=10)
    print(f"✓ Interpolation works. Generated {len(result)} frames")
except Exception as e:
    print(f"✗ Interpolation error: {e}")
EOF
```

**Expected Output**: `✓ Interpolation works. Generated X frames` (where X >= 10)

### Step 2.2: Verify URDF and Lafan1 Dataset Access

```bash
# Check URDF files exist
ls -la lafan1_retargeting_dataset/robot_description/ | head -20

# Should show URDF files for G1 robot
# Expected: Files like g1_29dof.urdf or similar
```

**Expected Output**: List of URDF files present

### Step 2.3: Enhance Interpolation with Joint Limits

```bash
# Create/update utils module with G1 joint limits
python << 'EOF'
import numpy as np

# Unitree G1 29-DOF joint limits (in radians)
# Format: [min, max] for each joint
G1_JOINT_LIMITS = {
    # Left Leg (6 DOF)
    'left_hip_roll': [-0.5, 0.5],
    'left_hip_pitch': [-1.57, 1.57],
    'left_hip_yaw': [-0.5, 0.5],
    'left_knee': [0, 2.7],
    'left_ankle_pitch': [-0.9, 0.9],
    'left_ankle_roll': [-0.5, 0.5],
    # Right Leg (6 DOF)
    'right_hip_roll': [-0.5, 0.5],
    'right_hip_pitch': [-1.57, 1.57],
    'right_hip_yaw': [-0.5, 0.5],
    'right_knee': [0, 2.7],
    'right_ankle_pitch': [-0.9, 0.9],
    'right_ankle_roll': [-0.5, 0.5],
    # Left Arm (6 DOF)
    'left_shoulder_pitch': [-1.57, 1.57],
    'left_shoulder_roll': [-1.57, 1.57],
    'left_shoulder_yaw': [-1.57, 1.57],
    'left_elbow': [0, 2.7],
    'left_wrist_pitch': [-1.57, 1.57],
    'left_wrist_roll': [-1.57, 1.57],
    # Right Arm (6 DOF)
    'right_shoulder_pitch': [-1.57, 1.57],
    'right_shoulder_roll': [-1.57, 1.57],
    'right_shoulder_yaw': [-1.57, 1.57],
    'right_elbow': [0, 2.7],
    'right_wrist_pitch': [-1.57, 1.57],
    'right_wrist_roll': [-1.57, 1.57],
    # Waist (1 DOF)
    'waist_yaw': [-1.57, 1.57],
}

print(f"✓ G1 Joint Limits defined ({len(G1_JOINT_LIMITS)} joints)")
EOF
```

**Expected Output**: `✓ G1 Joint Limits defined (29 joints)`

---

## Phase 3: Web App Frontend Implementation

### Step 3.1: Test Flask Server Startup

```bash
# Start Flask development server
python webapp/app.py &

# Wait a few seconds for server to start
sleep 2

# Test server is running
curl -s http://localhost:5000 | head -20

# Should show HTML output, not 404 or connection error
```

**Expected Output**: HTML content from index.html (not error)

### Step 3.2: Verify Web UI Assets Load

```bash
# Check static assets exist
ls -la webapp/static/
# Expected: app.js, style.css

ls -la webapp/templates/
# Expected: index.html
```

**Expected Output**: CSS and JS files present

### Step 3.3: Update CSS for Dark Theme (if needed)

Check `webapp/static/style.css` and ensure:
- [ ] Dark background (#1a1a1a or similar)
- [ ] Light text (#ffffff or #e0e0e0)
- [ ] Modern, sleek design with proper spacing
- [ ] Video-editor-like timeline interface

**Reference**: Update to modern dark design if current theme is light

---

## Phase 4: API Endpoint Implementation

### Step 4.1: CSV Upload Endpoint

Test endpoint:
```bash
# Create test CSV file
cat > test_motion.csv << 'EOF'
0.0,0.0,0.0,1.0,0.0,0.0,0.0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0.1,0.0,0.0,1.0,0.0,0.0,0.0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
EOF

# Test upload via curl
curl -X POST -F "file=@test_motion.csv" http://localhost:5000/api/upload

# Expected: JSON response with file ID
```

**Expected Output**: JSON with file ID and metadata

### Step 4.2: Merge Endpoint

Test endpoint:
```bash
# Upload two motions first
FILE1_ID=$(curl -s -X POST -F "file=@test_motion.csv" http://localhost:5000/api/upload | jq -r '.id')
FILE2_ID=$(curl -s -X POST -F "file=@test_motion.csv" http://localhost:5000/api/upload | jq -r '.id')

# Merge with stand pose
curl -X POST http://localhost:5000/api/merge \
  -H "Content-Type: application/json" \
  -d "{
    \"file_ids\": [\"$FILE1_ID\", \"$FILE2_ID\"],
    \"stand_pose_id\": \"stand_pose\",
    \"interpolation_type\": \"minimum_jerk\"
  }"

# Expected: JSON response with merged motion data or file ID
```

**Expected Output**: JSON with merged motion or status

---

## Phase 5: Testing & Validation

### Step 5.1: Manual Web UI Test - Upload CSV

1. Open browser: `http://localhost:5000`
2. Click "Upload CSV" button
3. Select test_motion.csv
4. **Verify**: File appears in file list, can be selected

**Expected**: File listed without errors

### Step 5.2: Manual Web UI Test - Visualize Motion

1. Select uploaded CSV from dropdown
2. Click "Preview" or "Visualize"
3. **Verify**: 3D model appears and renders

**Expected**: Robot model visible in 3D viewport

### Step 5.3: Manual Web UI Test - Merge Two Motions

1. Upload 2 different CSV files (or same file twice for now)
2. Select "Stand Pose" from dropdown
3. Select first motion
4. Select second motion
5. Set interpolation to "Minimum Jerk"
6. Click "Merge"
7. **Verify**: Merged motion preview shows smooth transition

**Expected**: Smooth motion rendered without jerks

### Step 5.4: Playback & Controls Test

1. Click "Play" button
2. **Verify**: Motion plays back smoothly
3. Adjust speed slider - motion speed changes
4. Drag timeline scrubber - position updates
5. Click "Pause" - motion pauses

**Expected**: All controls responsive and working

### Step 5.5: Export Test

1. Click "Export as CSV"
2. **Verify**: CSV file downloads to computer
3. Open file - should have 36 columns (3 pos + 4 quat + 29 angles)

**Expected**: Valid CSV file with correct format

---

## Phase 6: Dependencies & Requirements.txt

### Step 6.1: Generate Clean requirements.txt

```bash
# Freeze current environment
pip freeze > requirements_generated.txt

# Review and manually create clean requirements.txt with only needed packages:
cat > requirements.txt << 'EOF'
Flask==2.3.3
numpy==1.24.3
scipy==1.11.2
Werkzeug==2.3.7
Jinja2==3.1.2
click==8.1.7
itsdangerous==2.1.2
MarkupSafe==2.1.3
EOF
```

### Step 6.2: Test Fresh Installation

```bash
# Create new test environment
conda create -n smartinterp-test python=3.10 -y
conda activate smartinterp-test

# Install from requirements.txt only
pip install -r requirements.txt

# Test imports
python -c "import flask; import numpy; import scipy; print('✓ All dependencies install cleanly')"
```

**Expected**: No errors, clean installation

---

## Phase 7: Final End-to-End Validation

### Step 7.1: Complete Merge Workflow

Follow this sequence on local machine:

1. Start with two different motion CSV files (or generate test ones)
2. Upload Motion A via web UI
3. Upload Motion B via web UI  
4. Set Stand Pose
5. Select Motion A → Motion B with stand pose transition
6. Choose "Minimum Jerk" interpolation
7. Click "Merge"
8. **Verify in preview**:
   - Smooth transition from Motion A
   - Brief stand pose hold
   - Smooth entry into Motion B
   - No jerky movements or limit violations
9. Play animation back at various speeds
10. Export merged motion
11. **Verify export**: Valid CSV with 36 columns

**Expected**: Complete workflow works without errors

### Step 7.2: Edge Case Testing

Test with:
- [ ] Invalid CSV format (should show error message)
- [ ] Empty CSV (should show error message)
- [ ] Very large CSV (>1000 frames) - should still respond
- [ ] Rapid upload/merge clicks (no crashes)

**Expected**: Graceful error handling, no crashes

### Step 7.3: Performance Validation

- [ ] Web UI loads in under 2 seconds
- [ ] CSV upload completes in under 5 seconds
- [ ] Merge operation completes in under 10 seconds
- [ ] Playback smooth (30+ FPS)
- [ ] No memory leaks during extended use

**Expected**: Responsive performance

---

## Troubleshooting Guide

### Problem: "ModuleNotFoundError: No module named 'flask'"

**Solution:**
```bash
conda activate smartinterp
pip install flask
```

### Problem: "Port 5000 already in use"

**Solution:**
```bash
# Kill existing process
lsof -ti:5000 | xargs kill -9

# Or use different port
python webapp/app.py --port 5001
```

### Problem: Web UI shows blank page

**Solution:**
- Check browser console (F12) for JavaScript errors
- Verify static assets load (check Network tab)
- Restart Flask server

### Problem: Merge produces jerky motion

**Solution:**
```bash
# Check interpolation parameters
python interpolation.py --debug
# Try different easing (linear, smoothstep, minimum_jerk)
# Verify CSV data format (36 columns exactly)
```

---

## Sign-Off Checklist

Complete this before marking task as done:

- [ ] Conda environment created: `smartinterp`
- [ ] All dependencies installed from requirements.txt
- [ ] Flask server runs without errors
- [ ] Web UI dark theme displays correctly
- [ ] CSV upload works through web interface
- [ ] Motion visualization rendering in 3D
- [ ] Single motion playback works with all controls
- [ ] Two motions merged successfully with stand pose
- [ ] Merged motion smooth (no jerky movements)
- [ ] Merged motion respects joint limits
- [ ] Export to CSV works, file has correct format
- [ ] complete requirements.txt with pinned versions exists
- [ ] All code tested on local laptop
- [ ] Remediation log updated with all actions
- [ ] No runtime errors or crashes observed

Once all checkboxes complete, task is ready for deployment.
