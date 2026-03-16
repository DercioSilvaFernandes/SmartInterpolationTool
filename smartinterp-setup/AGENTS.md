# AGENTS.md - SmartInterpolationTool Setup

## Repo Purpose

This workspace is dedicated to setting up SmartInterpolationTool as a production-ready application for merging and visualizing Unitree G1 robot motion CSV files with intelligent interpolation.

When a task-specific markdown file exists under `current_task/`, follow it as the mission-specific source of truth.
When a remediation log is required, keep it updated throughout execution, not only at the end.

## Local Development Environment

This task requires:
- **Python**: 3.8+ (verified with conda env)
- **conda environment**: Isolated Python environment for safety and reproducibility
- **Headless GUI validation**: Use Playwright + Chromium to verify the web UI without an interactive browser
- **Remote target support**: Browserless Ubuntu instances are valid test targets when the operator provides SSH access

Pre-requisites:
- Conda installed and available in PATH
- Git access to clone lafan1 repository if needed
- Chromium installed through Playwright (`python -m playwright install chromium` locally, `python -m playwright install --with-deps chromium` on Ubuntu)
- Interactive browser access is optional; a browserless GUI screenshot is the required evidence artifact

Creation of conda environment:
```bash
conda create -n smartinterp python=3.10
conda activate smartinterp
cd /Users/dercio.fernandes/dm-isaac-g1/agents/SmartInterpolationTool
pip install -r requirements.txt
python -m playwright install chromium
```

## Core Operating Principles

- **Act like a developer, not a note-taker**: Build, test, and validate continuously.
- **Do not stop at identifying missing features**: Implement required functionality.
- **Prefer working solutions over perfect architecture**: Get E2E workflow working first.
- **Test as you build**: Each feature should be tested before moving to the next.
- **Keep changes scoped to the task**: Focus on CSV merge, interpolation, and web visualization.
- **Ensure reproducibility**: Complete requirements.txt with pinned versions.
- **Documentation updates**: Keep inline code comments and remediation logs updated.
- **Default to browserless GUI checks**: Validate the Flask UI with `smartinterp-setup/browserless_gui_check.py` and keep the generated screenshot path in the log.
- **Use remote instances when supplied**: If the operator provides an instance, run the same validation flow there over SSH. Never write plaintext passwords into repo files.

## Acceptance Criteria Checklist

Task is complete when ALL of the following are verified working:

- [ ] Multiple CSV merge with intelligent interpolation
- [ ] Web app dark theme UI (modern, sleek, video-editor-like)
- [ ] Live interpolation visualization with easing controls
- [ ] Browserless GUI validation screenshot captured from the target machine
- [ ] CSV upload and caching
- [ ] Stand pose support
- [ ] 2 CSVs successfully merged with stand pose in between
- [ ] Physical robot joint limit validation
- [ ] Complete requirements.txt with pinned versions
- [ ] Local and/or remote target tested with conda env and headless GUI validation

## Task File Rules

For any active task in `current_task/`:
- Read the task file before making changes
- Treat it as the mission definition and acceptance criteria
- Create and maintain the required remediation log immediately
- Update the remediation log after every meaningful action:
  - Feature implemented
  - Test performed
  - File changed/created
  - Any issues discovered and fixes applied

## When to Update Logs

Update `current_task/SMARTINTERP-SETUP_REMEDIATION_LOG.md` after:
- Creating/modifying any Python code
- Running successful tests
- Modifying web app frontend/backend
- Installing dependencies
- Running browserless GUI validation or remote-instance checks
- Encountering and fixing any issues
