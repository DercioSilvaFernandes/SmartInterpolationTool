# Automated Remote Imitation Learning Policy Runbook

## Purpose

Use this file as the instruction source for an agent that must connect to a remote instance over SSH, upload a user-provided video, run the full video-to-mimic pipeline, create a new mimic task, train and export the policy, validate the policy-generation flow, and finally upload outputs to AWS S3.

The agent must adapt to different remote folder layouts. Do not hardcode paths unless they are first verified on the target instance.

## Mandatory Interaction Contract

Before doing any remote action, the agent must stop and ask for the SSH target.

Minimum questions the agent must ask before starting:

1. `Send me the SSH command or the host/user/port for the target instance.`
2. `Send me the local path to the source video.`
3. `Send me the task name to create for this mimic policy.`

Only ask for the S3 bucket and prefix near the end if they were not already provided.

If any required value is missing, do not guess. Ask first.

## SSH Key Discovery Rules

Before asking for a PEM path, the agent should try to discover one locally.

Search order:

1. Check whether the user-provided SSH command already includes `-i /path/to/key.pem`.
2. Search the current workspace.
3. Search `~/.ssh`.
4. Search `~/Downloads`.
5. Search `~/Documents`.
6. Search `~/Desktop`.

Suggested local discovery commands:

```bash
find . -type f -name "*.pem" 2>/dev/null
find ~/.ssh ~/Downloads ~/Documents ~/Desktop -type f -name "*.pem" 2>/dev/null
```

Rules:

- If exactly one PEM candidate is found and it matches the SSH target naming, use it.
- If multiple PEM files are found, show the candidate paths and ask the user which one to use.
- If no PEM is found and the SSH command does not include `-i`, ask the user for the PEM path.
- Do not attempt remote work until SSH authentication is confirmed.

## Remote Discovery Rules

The remote instance may not match the expected layout exactly. The agent must verify paths before running the pipeline.

Expected components:

- `video2robot/run_pipeline.py`
- `pkl_to_csv.py`
- `csv_to_npz.py`
- `unitree_rl_lab.sh`
- mimic task folder for `g1_29dof`

Start with likely paths:

- `/workspace/video2robot`
- `/workspace/dm-isaac-g1`
- `/workspace/unitree_rl_lab`

If any expected path is missing, discover by script name first:

```bash
find /workspace -type f \( -name "run_pipeline.py" -o -name "pkl_to_csv.py" -o -name "csv_to_npz.py" -o -name "unitree_rl_lab.sh" \) 2>/dev/null
find /workspace -type d -path "*tasks/mimic/robots/g1_29dof" 2>/dev/null
find /workspace -type f \( -name "tracking_env_cfg.py" -o -name "tracking_env.cfg" -o -path "*deploy/robots/g1_29dof/config/config.yaml" \) 2>/dev/null
```

Use the discovered script locations, not assumptions.

## Real Local References From This Workspace

These are the current local script names and argument patterns. Use them as the preferred command shape when the remote repo matches this layout:

- `pkl_to_csv.py`: `/src/dm_isaac_g1/mimic/scripts/pkl_to_csv.py`
- `csv_to_npz.py`: `/unitree_rl_lab/scripts/mimic/csv_to_npz.py`
- `unitree_rl_lab.sh`: `/unitree_rl_lab/unitree_rl_lab.sh`
- mimic task root:
  `/unitree_rl_lab/source/unitree_rl_lab/unitree_rl_lab/tasks/mimic/robots/g1_29dof`

Observed script interface:

```bash
python pkl_to_csv.py --input INPUT_PKL --output OUTPUT_CSV
python csv_to_npz.py -f INPUT_CSV --input_fps 60 --output_name OUTPUT_NPZ
./unitree_rl_lab.sh -l
./unitree_rl_lab.sh -t --task TASK_NAME
./unitree_rl_lab.sh -p --task TASK_NAME
```

Note: in this codebase the task config file is named `tracking_env_cfg.py`, not `tracking_env.cfg`. The agent should support either filename depending on what exists remotely.

## Required Outputs

The pipeline is complete only when all of these exist:

- Uploaded video on the remote instance
- `robot_motion.pkl`
- converted `.csv`
- converted `.npz`
- new mimic task folder
- training run output
- exported policy artifacts
- final S3 upload destination recorded

## End-to-End Procedure

### 1. Collect Inputs

Collect and confirm:

- SSH command or host, user, and optional port
- PEM path if not auto-discovered
- local video path
- task name
- optional input FPS override if the source video or CSV requires something other than `60`
- optional S3 bucket and prefix

Validate the video path locally before upload:

```bash
test -f "LOCAL_VIDEO_PATH"
```

### 2. Establish SSH Access

If the user gave a full SSH command, prefer using it as-is after validating or inserting the PEM path.

Example shapes:

```bash
ssh -i KEY.pem ubuntu@HOST
ssh -i KEY.pem -p PORT ubuntu@HOST
```

Confirm remote access with a lightweight probe:

```bash
ssh -i KEY.pem ubuntu@HOST 'hostname && pwd && ls /workspace'
```

### 3. Upload the Video

Pick or create a stable upload location such as `/workspace/uploads/videos`.

```bash
ssh -i KEY.pem ubuntu@HOST 'mkdir -p /workspace/uploads/videos'
scp -i KEY.pem "LOCAL_VIDEO_PATH" ubuntu@HOST:/workspace/uploads/videos/
```

Record the final remote video path.

### 4. Run `video2robot`

Find the repo root that contains `run_pipeline.py`, then run:

```bash
ssh -i KEY.pem ubuntu@HOST "cd VIDEO2ROBOT_ROOT && python run_pipeline.py --video REMOTE_VIDEO_PATH"
```

After it finishes, find the newest generated `robot_motion.pkl`:

```bash
ssh -i KEY.pem ubuntu@HOST 'find VIDEO2ROBOT_ROOT/data -type f -name "robot_motion.pkl" 2>/dev/null | sort'
```

Prefer the newest match if multiple files exist.

### 5. Convert `robot_motion.pkl` to CSV

Find `pkl_to_csv.py`, then generate a CSV next to the pickle or inside a task-specific output folder.

Example:

```bash
ssh -i KEY.pem ubuntu@HOST "mkdir -p /workspace/mimic_outputs/TASK_NAME"
ssh -i KEY.pem ubuntu@HOST "python PKL_TO_CSV_SCRIPT --input ROBOT_MOTION_PKL --output /workspace/mimic_outputs/TASK_NAME/TASK_NAME.csv"
```

Validate that the CSV exists and is non-empty.

### 6. Convert CSV to NPZ

Find `csv_to_npz.py`, then run:

```bash
ssh -i KEY.pem ubuntu@HOST "cd UNITREE_RL_LAB_ROOT && python scripts/mimic/csv_to_npz.py -f /workspace/mimic_outputs/TASK_NAME/TASK_NAME.csv --input_fps 60 --output_name /workspace/mimic_outputs/TASK_NAME/TASK_NAME.npz"
```

If the script path differs, use the discovered absolute path instead.

Validate that both files now exist:

- `/workspace/mimic_outputs/TASK_NAME/TASK_NAME.csv`
- `/workspace/mimic_outputs/TASK_NAME/TASK_NAME.npz`

### 7. Create a New Mimic Task

Find:

- the mimic task root
- an existing task folder to clone, for example `dance_102`
- the correct config filename: `tracking_env_cfg.py` or `tracking_env.cfg`

Procedure:

1. Copy an existing task folder under `.../tasks/mimic/robots/g1_29dof/`.
2. Rename the copied folder to `TASK_NAME`.
3. Copy the generated `.npz` into that new folder.
4. Edit the new task folder `__init__.py` and register the new gym task name.
5. Edit the tracking config file and point `motion_file` to the new `.npz`.

Expected task folder shape:

```text
.../g1_29dof/TASK_NAME/
  __init__.py
  tracking_env_cfg.py   # or tracking_env.cfg
  TASK_NAME.npz
```

Registration rule:

- Mirror the closest existing task entry.
- Replace the task id string with the new task name.
- Keep the existing `entry_point`, env config entry point, and PPO config structure unless the repo differs.

Tracking config rule:

- Update only the `motion_file` reference and task-local identifiers unless more changes are required by the target repo.
- Preserve existing reward, observation, and robot config unless the task fails to load.

### 8. Verify Task Registration

List available tasks:

```bash
ssh -i KEY.pem ubuntu@HOST "cd UNITREE_RL_LAB_ROOT && ./unitree_rl_lab.sh -l"
```

The new task must appear before training starts.

If it does not appear:

- inspect the new task folder `__init__.py`
- inspect sibling task registrations
- inspect import side effects in parent packages
- fix registration before continuing

### 9. Train the Policy

Run:

```bash
ssh -i KEY.pem ubuntu@HOST "cd UNITREE_RL_LAB_ROOT && ./unitree_rl_lab.sh -t --task TASK_NAME"
```

Training stop condition:

- training exits successfully, or
- mean reward reaches about `100`

If training must be stopped manually, send `Ctrl + C` only after confirming logs and checkpoints are already being written.

Record:

- training log directory
- latest checkpoint
- best checkpoint if clearly identified

### 10. Export the Policy

After training:

```bash
ssh -i KEY.pem ubuntu@HOST "cd UNITREE_RL_LAB_ROOT && ./unitree_rl_lab.sh -p --task TASK_NAME"
```

Expected outputs include:

- ONNX
- JIT
- policy checkpoints
- export metadata

The agent must locate and record the real export directory instead of assuming it.

### 11. End-to-End Validation

The agent must verify the pipeline, not just run commands.

Minimum checks:

- SSH connection succeeded
- uploaded video exists remotely
- `robot_motion.pkl` exists
- CSV exists and has content
- NPZ exists and has content
- new mimic task appears in `./unitree_rl_lab.sh -l`
- training created checkpoints
- export created deployable artifacts
- final outputs were uploaded to S3

If any stage fails, the agent should:

1. inspect the failing command output
2. locate the real path or interface
3. retry with the corrected path
4. stop and ask only if a required input or missing repo component blocks progress

## Path Adaptation Rules

When the remote layout differs:

- prefer `find` by script filename over guessing directory names
- prefer cloning an existing mimic task that already works on that instance
- compare against sibling task folders to determine required edits
Do not treat a path mismatch as a blocker until discovery has been attempted.

## Recommended Remote Output Layout

Use a task-specific artifact folder when possible:

```text
/workspace/mimic_outputs/TASK_NAME/
  original_video.ext
  TASK_NAME.csv
  TASK_NAME.npz
  logs/
  exports/
```

## S3 Upload Placeholder

At the end, upload the relevant artifacts to AWS S3. Fill these placeholders later:

- bucket: `s3://REPLACE_ME_BUCKET`
- prefix: `REPLACE_ME_PREFIX/TASK_NAME/`

Suggested upload commands:

```bash
aws s3 cp /workspace/mimic_outputs/TASK_NAME/TASK_NAME.csv s3://REPLACE_ME_BUCKET/REPLACE_ME_PREFIX/TASK_NAME/
aws s3 cp /workspace/mimic_outputs/TASK_NAME/TASK_NAME.npz s3://REPLACE_ME_BUCKET/REPLACE_ME_PREFIX/TASK_NAME/
aws s3 cp EXPORT_DIR s3://REPLACE_ME_BUCKET/REPLACE_ME_PREFIX/TASK_NAME/exported/ --recursive
aws s3 cp CHECKPOINT_DIR s3://REPLACE_ME_BUCKET/REPLACE_ME_PREFIX/TASK_NAME/checkpoints/ --recursive
```

Record the final uploaded S3 paths in the run summary.

## Completion Definition

This automation is complete only when the agent can report:

- SSH target used
- PEM path used
- local video path and remote uploaded path
- final `robot_motion.pkl` path
- final CSV path
- final NPZ path
- mimic task folder path
- training log and checkpoint path
- export path
- S3 upload path

## Operator Notes

- Ask before remote work.
- Auto-discover PEM before asking for it.
- Adapt to path differences in real time.
- Use the real script interfaces that exist on the target instance.
- Verify each stage before moving to the next one.
- Do not run sim2sim as part of this workflow. Stop after export and S3 upload.
