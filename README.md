# SMB-MSL: Motor Sequence Learning Task (WiP — untested, do not use for research purpose)

PsychoPy implementation of the **SMB Scene Sequence Learning (SSL) task** — a naturalistic motor sequence learning paradigm built on Super Mario Bros. scenes from the CNeuroMod `mario.scenes` dataset. The task ships in two modes:

- **MSP mode** (Motor Sequence Production) — canonical button sequences extracted from BK2 replay files are presented as abstract NES button-chord sequences with per-element duration bars. The player reproduces them by pressing the correct button combinations for the correct duration.
- **Gameplay mode** — loads SMB savestates via `stable-retro`. The player actually plays the scenes in real time. Death detection (enemy hits, falls) immediately interrupts the current execution.

## Installation

### 1. Python environment with `uv`

Dependencies and the virtualenv are managed by [`uv`](https://docs.astral.sh/uv/). Install it once:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The recommended path on Linux is to run `./setup.sh` (see [step 3](#3-datasets-mariostimuli-and-marioscenes)): it auto-detects your distro, points `uv sync` at the matching prebuilt wxPython wheel index, and then installs the datalad datasets. If you only want the Python env without the data, the same `uv sync` call works on its own — but you'll need `--find-links` set to the right wxPython wheel index for your distro, e.g. Linux Mint 22 / Ubuntu 24.04:

```bash
uv sync --find-links https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-24.04/
```

This creates `.venv/` and installs everything declared in `pyproject.toml` (PsychoPy, stable-retro, NumPy, SciPy, wxPython, datalad, tqdm). Python 3.9+ is required; `uv` will fetch a matching interpreter if needed.

Run anything in the project env with `uv run`:

```bash
uv run smb-ssl-task            # entry point
uv run python -m smb_ssl_task  # equivalent
```

#### Why the wxPython find-links URL?

PsychoPy needs wxPython, which has no Linux wheels on PyPI (it only ships there as an sdist that needs system GTK dev headers to build). The CNeuroMod-friendly path is the [wxPython extras index](https://extras.wxpython.org/wxPython4/extras/linux/gtk3/) — a per-distro directory of prebuilt wheels. `setup.sh` picks the right directory automatically; supported flavours are:

| Distro family | URL fragment | Notes |
|---|---|---|
| Ubuntu (24.04 / 22.04 / 20.04) | `ubuntu-XX.XX` | Direct match |
| Linux Mint, Pop!_OS, elementary, Zorin, KDE Neon, Tuxedo | `ubuntu-XX.XX` | Mapped via `UBUNTU_CODENAME` (noble → 24.04, jammy → 22.04, focal → 20.04) |
| Debian (11 / 12) | `debian-XX` | Direct match |
| Fedora (37 / 38) | `fedora-XX` | Direct match |

If your distro isn't covered, browse the [extras index](https://extras.wxpython.org/wxPython4/extras/linux/gtk3/) for a compatible variant and pass it explicitly with `uv sync --find-links <URL>`. The current pin is `wxpython==4.2.2` (latest version available across all supported distro directories at time of writing).

`uv.lock` is **not** committed because the wheel URL it pins is distro-specific; `setup.sh` regenerates it for each machine.

If you manage PsychoPy separately (e.g., the standalone installer) and just want this repo importable on top of it, install without dependencies:

```bash
uv pip install -e . --no-deps
```

### 2. Linux: realtime scheduling permissions

PsychoPy's keyboard backend (PsychToolbox) requires realtime thread scheduling. Without it the task will crash with a segfault. Run the following once, then **log out and back in**:

```bash
sudo groupadd --force psychopy
sudo usermod -a -G psychopy $USER
sudo tee /etc/security/limits.d/99-psychopy.conf > /dev/null << 'EOF'
@psychopy - nice -20
@psychopy - rtprio 50
@psychopy - memlock unlimited
EOF
```

### 3. Datasets (`mario.stimuli` and `mario.scenes`)

The task depends on two CNeuroMod datalad datasets:

| Dataset | Purpose |
|---|---|
| [`courtois-neuromod/mario.stimuli`](https://github.com/courtois-neuromod/mario.stimuli) | NES ROM + `stable-retro` integration metadata (the **Retro integration dir** in the GUI) |
| [`courtois-neuromod/mario.scenes`](https://github.com/courtois-neuromod/mario.scenes) | Per-session gameplay archives (the **Scenes dataset dir** in the GUI) |

A helper script `setup.sh` provisions everything in one go:

1. detects your Linux distro and picks the matching wxPython wheel index (see the table above),
2. runs `uv sync --find-links <that-index>` to create `.venv/` and install all Python deps (incl. `datalad` and `tqdm`),
3. `datalad install` for both datasets, then `datalad get` (via `uv run`) — the `mario.scenes` fetch is scoped to `sourcedata/scenes_info/` and `sub-*/ses-*/gamelogs.tar` so we skip the BIDS `func/` files (events/bold) the task doesn't use,
4. unpacks the per-session `gamelogs.tar` archives in `mario.scenes` using the dataset's own decompress script (via `uv run`).

```bash
./setup.sh                  # interactive: prompts for a data root (default: repo root)
./setup.sh /path/to/root    # non-interactive
```

Requirements: `uv` and `git` on PATH, plus SSH access to `github.com:courtois-neuromod` (these datasets are released under CNeuroMod's data-sharing terms; request access if needed).

After the script finishes you'll have:

```
<DATA_ROOT>/
├── mario.stimuli/                 # ROM + integration files
│   └── SuperMarioBros-Nes/        # used as the "Retro integration dir"
└── mario.scenes/                  # scene gamelogs (unpacked)
    └── sub-XX/ses-YYY/gamelogs/
```

Both paths are then entered once in the GUI (see below) and persisted in `.smb_ssl_settings.json`.

---

## Running the task

```bash
# Via the installed entry point
uv run smb-ssl-task

# Or as a module
uv run python -m smb_ssl_task
```

(`uv run` activates the project `.venv` for you; you can also `source .venv/bin/activate` and drop the `uv run` prefix.)

A GUI dialog will prompt you for:

| Field | Description |
|---|---|
| **Participant ID** | String identifier (e.g., `01`) |
| **Group** | `1` or `2` — determines which 6 scenes are trained vs. untrained |
| **Mode** | `msp` (chord sequences with duration) or `gameplay` (actual Mario play) |
| **Session type** | `training`, `test`, `scan_paced`, `scan_fullspeed`, or `pretrain` |
| **Session number** | Integer session index |
| **Blocks / Reps** | Number of blocks (training) or reps per scene (test) |
| **Screen resolution** | Display resolution in WxH pixels (auto-detected) |
| **Scenes dataset dir** | Path to the `mario.scenes` dataset root (saved across runs) |
| **Retro integration dir** | Directory containing `SuperMarioBros-Nes/` (gameplay mode only, saved across runs) |
| **Advanced mode** | Opens an extended configuration panel (see below) |

MSP mode does not require **Retro integration dir** — you can leave the field empty.

## Session types

**Pre-training** (`pretrain`) — Familiarization using 6 scenes not in the experimental set. Self-paced, two executions per trial (both guided). No points.

**Training** (`training`) — 6 trained scenes, blocks of 24 trials (4 reps per scene, shuffled). Each trial has two executions:
- *MSP mode*: Execution 1 with symbols visible, Execution 2 from memory (symbols hidden)
- *Gameplay mode*: Execution 1 normal play, Execution 2 immediate replay

Adaptive reward system: 0 points (error/slow), 1 point (correct), 3 points (correct and fast). Speed threshold updates per block when error rate < 15%.

**Behavioral test** (`test`) — All 12 scenes (6 trained + 6 untrained) intermixed. Self-paced, no points.

**Scan session — paced** (`scan_paced`) — 8 functional runs for fMRI. 12 scenes x 6 reps = 72 trials per run, arranged as consecutive pairs. Each trial: 1s prep + 5s execution + 0.5s ITI. Expanding pacing line in MSP mode. 5 rest periods (10s fixation) per run. Waits for scanner trigger (`=` key) before each run.

**Scan session — full speed** (`scan_fullspeed`) — Same structure but with a short static go-cue instead of the expanding pacing line.

## Advanced mode

When **Advanced mode** is checked, a comprehensive configuration panel opens before the session starts. All parameters are pre-populated with their current defaults; the user only changes what they need.

**Dialog 1 — Configuration overrides:**

| Section | Fields |
|---------|--------|
| **Scene / Clip** | Scene ID filter, Subject filter, Outcome filter, Clip min duration, Clip min/max elements |
| **Timing** | Execution timeout, Inter-execution/trial intervals, Feedback duration, Gameplay max duration, Fixation duration, Countdown step duration, Speed factor |
| **Training** | Reps per sequence, Pretrain reps per scene, Error rate threshold, Fast bonus fraction |
| **Scanner** | Prep duration, Execution duration, ITI, Reps per sequence, Number of runs, Rest periods/duration |
| **Behavior** | Repeat until passed |

Any changed values override the corresponding `config.py` constant for that session (propagated to all loaded modules at startup via `config.apply_overrides()`).

**Speed factor** — Controls emulator playback speed for both the BK2 preview replay and the player's gameplay execution (1.0 = real-time, 0.5 = half speed, 2.0 = double speed). Useful for piloting or debugging. Must not be 0.

**Repeat until passed** — When enabled, each trial loops until the participant completes it successfully (accuracy_trial = 1). The `repeat_attempt` column in the TSV tracks the attempt number.

**Dialog 2 — Clip selection (optional):** Only shown when a Scene ID filter is set and the scenes dataset is valid. Allows selecting a specific BK2 clip from the dataset, which overrides the default canonical sequence for that scene.

## Action vocabulary

NES inputs are compressed into distinct actions, each representing a set of simultaneously held buttons:

| Symbol | Buttons | Description |
|--------|---------|-------------|
| `_` | (none) | Wait / stand |
| `R` | RIGHT | Walk right |
| `rR` | RIGHT+B | Run right |
| `J` | A | Standing jump |
| `RJ` | RIGHT+A | Walk-jump right |
| `rRJ` | RIGHT+A+B | Run-jump right |
| `L` | LEFT | Walk left |
| `LJ` | LEFT+A | Walk-jump left |
| `rLJ` | LEFT+A+B | Run-jump left |
| `D` | DOWN | Crouch / enter pipe |

In MSP mode, each element in the sequence is a chord with a target duration. The player must press the correct button combination and hold it for the indicated duration (shown by a horizontal bar below each symbol). A configurable timing tolerance (default 50ms) allows for small timing errors.

## Input mapping

**Keyboard:**

| Key | NES Button |
|-----|------------|
| Arrow Right | RIGHT |
| Arrow Left | LEFT |
| Arrow Up | UP |
| Arrow Down | DOWN |
| X | A (jump) |
| Z | B (run) |

**Gamepad** (optional): D-pad or left stick for directions, face buttons for A/B. Configurable in `smb_ssl_task/config.py`.

Press `Escape` at any time to abort the session (data collected so far is saved).

## Scene selection

12 scenes are hardcoded (2 groups of 6), drawn from worlds 1–2 of the CNeuroMod `mario.scenes` dataset:

- **Set 1**: w1l1s3, w1l1s5, w1l1s8, w1l2s2, w1l3s3, w2l1s3
- **Set 2**: w1l1s4, w1l1s10, w1l2s4, w1l3s7, w2l1s5, w2l3s3

Group 1 trains on Set 1 (Set 2 untrained); Group 2 trains on Set 2 (Set 1 untrained). 6 additional pretrain scenes are selected from non-overlapping positions.

## Output

Data is saved to `output/` in the working directory:

```
output/
└── sub-01/
    ├── pretrain/
    │   └── sub-01_pretrain_ses-01.tsv
    ├── training/
    │   └── sub-01_training_ses-01.tsv
    ├── test/
    │   └── sub-01_test_ses-01.tsv
    ├── scan_paced/
    │   └── sub-01_scan_paced_ses-01.tsv
    └── scan_fullspeed/
        └── sub-01_scan_fullspeed_ses-01.tsv
```

Each TSV file has one row per execution with columns covering both modes:

| Column | Description |
|---|---|
| `participant_id` | Participant identifier |
| `group` | Group assignment (1 or 2) |
| `session_type` | Session type string |
| `session_number` | Session index |
| `block_number` | Block number (1 for test/scan) |
| `run_number` | Functional run (scan) or 0 |
| `trial_number` | Global trial counter |
| `scene_id` | Scene identifier (e.g., `w1l1s3`) |
| `mode` | `msp` or `gameplay` |
| `execution_number` | 1 or 2 |
| `condition` | `trained`, `untrained`, or `pretrain` |
| `target_sequence` | Target action symbols, semicolon-separated (MSP) |
| `response_sequence` | Pressed action symbols, semicolon-separated (MSP) |
| `target_durations` | Target hold durations in seconds, semicolon-separated (MSP) |
| `response_durations` | Actual hold durations in seconds, semicolon-separated (MSP) |
| `accuracy_per_element` | 1/0 per position, semicolon-separated (MSP) |
| `accuracy_trial` | 1 if all elements correct (chord + timing), else 0 (MSP) |
| `movement_time` | First to last element time in seconds (MSP) |
| `inter_element_intervals` | Intervals between elements, semicolon-separated (MSP) |
| `outcome` | `completed`, `death`, or `timeout` (gameplay) |
| `traversal_time` | Scene traversal time in seconds (gameplay) |
| `distance_reached` | Fraction of scene traversed, 0.0–1.0 (gameplay) |
| `points_awarded` | Points for this execution |
| `advanced_mode` | Whether advanced mode was active (`True`/`False`) |
| `source_bk2` | Path to the selected BK2 clip (advanced mode) or `NA` |
| `repeat_attempt` | Attempt number within a trial (1 normally, >1 with repeat-until-passed) |

Columns not applicable to the current mode are filled with `NA`.

## Configuration

Edit `smb_ssl_task/config.py` to adjust:

- Display settings (screen size, game render size, colors, font sizes)
- Action display parameters (symbol spacing, feedback colors)
- Timing parameters (timeouts, intervals, gameplay max duration, speed factor)
- Training parameters (trials per block, error threshold, point values)
- Scanner settings (trigger key, trial timing, runs, rest periods)
- Input mappings (keyboard and gamepad)
- Duration bar appearance and timing tolerance
- BK2 clip filtering (min/max elements, min duration, allowed symbols)
- Output directory (default: `output/`)

Alternatively, use **Advanced mode** in the GUI to override any config parameter for a single session without editing the file. Overrides are applied at startup via `config.apply_overrides()` and propagated to all loaded modules.

## BK2 parser

`smb_ssl_task/scenes.py` includes a standalone BK2 parser for extracting action sequences from replay files:

```python
from smb_ssl_task.scenes import parse_bk2, extract_action_sequence

# Raw per-frame button states
frames = parse_bk2("path/to/clip.bk2")
# [{"RIGHT"}, {"RIGHT", "A"}, {"RIGHT", "A", "B"}, ...]

# Compressed action sequence (collapsed, noise-filtered)
actions = extract_action_sequence("path/to/clip.bk2", min_frames=3)
# ["R", "RJ", "rRJ", "rR", ...]
```

The 12 experimental scenes currently use pre-extracted placeholder sequences. These will be replaced with actual BK2 data once scene selection is finalized.

---

## Project structure

```
SMB-MSL/
├── pyproject.toml
├── README.md
├── setup.sh                       # datalad install + unpack helper
└── smb_ssl_task/
    ├── __init__.py
    ├── __main__.py                # Entry point, GUI dialog, mode dispatch
    ├── config.py                  # All parameters (display, timing, input, paths)
    ├── advanced_gui.py            # Advanced mode: config overrides + clip selection dialogs
    ├── scenes.py                  # Scene definitions, BK2 parser, action vocabulary
    ├── input_handler.py           # Unified keyboard/gamepad -> NES button mapping
    ├── data_logging.py            # TSV writer (MSP + gameplay columns)
    ├── display.py                 # Shared instruction/feedback/rest screens
    ├── msp.py                     # MSP mode: ActionSequenceDisplay + chord/duration collection
    ├── game.py                    # Gameplay mode: stable-retro wrapper + rendering
    ├── task_training.py           # Training session
    ├── task_test.py               # Behavioral test
    ├── task_pretrain.py           # Pre-training
    └── task_scan.py               # Scan session
```
