# SmartInterpolationTool

A small toolset for stitching and visualizing motion CSVs produced from Unitree G1 / LAFAN datasets.

## Web Visualizer

A lightweight web app is included to preview/animate CSV motions and to generate interpolated transitions between motions.

### Run the web app

1. Install dependencies (using the provided virtual environment):

```bash
python -m pip install -r requirements.txt
```

2. Start the server (run from the repo root):

```bash
python webapp/app.py
```

> If you run from inside the `webapp/` directory, it still works (the app auto-adjusts the import path).

3. Open the viewer in your browser:

```
http://localhost:5000
```

### Browserless GUI Check

If the machine cannot open a browser window, validate the real UI with headless Chromium instead:

```bash
python -m playwright install chromium
python smartinterp-setup/browserless_gui_check.py \
  --launch-local-server \
  --output smartinterp-setup/artifacts/local-gui-check.png
```

On Ubuntu, prefer:

```bash
python -m playwright install --with-deps chromium
```

The script loads the Flask app, builds a motion, enables playback, and saves a screenshot artifact you can inspect later.

### Non-Web Rerun Visualizer

If you want a non-web artifact instead of the Flask UI, use:

```bash
python rerun_visualize.py \
  --motion1 stand_pose \
  --motion2 motion_walk
```

By default this writes:

- `smartinterp-setup/artifacts/rerun/smartinterp_visualization.rrd`
- `smartinterp-setup/artifacts/rerun/smartinterp_visualization_summary.json`

On a remote instance, run the same command inside the prepared virtualenv:

```bash
source ~/smartinterp-venv/bin/activate
cd ~/smartinterp-remote/SmartInterpolationTool
python rerun_visualize.py --motion1 stand_pose --motion2 motion_walk
```

Use `--spawn-viewer` only on machines with a desktop session. On headless machines, keep the default behavior and copy the `.rrd` file elsewhere if you want to inspect it interactively.

### What it does

- Loads URDFs from `lafan1_retargeting_dataset/robot_description`
- Lets you pick a "stand" motion and one or two other motions
- Builds an interpolated/stiched motion using the same algorithm from `interpolation.py`
- Lets you choose interpolation easing (minimum-jerk, smoothstep, linear)
- Playback controls: speed slider, frame scrubber, and play/pause
- Record the canvas output to a WebM video file
- Multi-clip stitching (choose multiple clips to chain together with stand transitions)

### Notes

- The web app expects CSVs in the same format produced by `pkl_to_csv.py`: `root_pos (3), root_quat (4), 29 joint angles`.
- You can also upload your own CSVs through the UI and re-use them without re-uploading (cached on the server).
