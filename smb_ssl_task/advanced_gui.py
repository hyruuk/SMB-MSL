"""
Advanced mode GUI for the SMB SSL task.

When "Advanced mode" is checked in the main dialog, a comprehensive
configuration panel lets the user override any timing / training /
scanner / clip-filtering parameter.  Optionally a second dialog allows
picking a specific BK2 clip from the mario.scenes dataset.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from psychopy import gui

from smb_ssl_task import config
from smb_ssl_task.scenes import (
    get_scene_info_any,
    _scene_id_from_filename,
)


# ---------------------------------------------------------------------------
# Mapping from dialog field names to config constant names
# ---------------------------------------------------------------------------

_FIELD_TO_CONFIG = {
    # Clip filtering
    "Clip min duration (s)":        "CLIP_MIN_DURATION_SEC",
    "Clip min elements":            "CLIP_MIN_ELEMENTS",
    "Clip max elements":            "CLIP_MAX_ELEMENTS",
    # Timing
    "Execution timeout (s)":        "EXECUTION_TIMEOUT",
    "Inter-execution interval (s)": "INTER_EXECUTION_INTERVAL",
    "Inter-trial interval (s)":     "INTER_TRIAL_INTERVAL",
    "Feedback duration (s)":        "FEEDBACK_DURATION",
    "Gameplay max duration (s)":    "GAMEPLAY_MAX_DURATION",
    "Fixation duration (s)":        "FIXATION_DURATION",
    "Countdown step duration (s)":  "COUNTDOWN_STEP_DURATION",
    "Speed factor":                 "SPEED_FACTOR",
    # Training
    "Training reps per sequence":   "TRAINING_REPS_PER_SEQ",
    "Pretrain reps per scene":      "PRETRAIN_REPS_PER_SCENE",
    "Error rate threshold":         "ERROR_RATE_THRESHOLD",
    "Fast bonus fraction":          "FAST_BONUS_FRACTION",
    # Scanner
    "Scan prep duration (s)":       "SCAN_PREP_DURATION",
    "Scan execution duration (s)":  "SCAN_EXECUTION_DURATION",
    "Scan ITI (s)":                 "SCAN_ITI",
    "Scan reps per sequence":       "SCAN_REPS_PER_SEQ",
    "Scan number of runs":          "SCAN_N_RUNS",
    "Scan rest periods":            "SCAN_REST_PERIODS",
    "Scan rest duration (s)":       "SCAN_REST_DURATION",
}


@dataclass
class AdvancedConfig:
    """Carries advanced mode selections to session runners."""
    enabled: bool = False
    selected_bk2: Optional[str] = None
    selected_scene_id: Optional[str] = None
    selected_scene_info: Optional[dict] = None
    repeat_until_passed: bool = False
    # Raw overrides: {CONFIG_CONSTANT_NAME: value}  (populated by dialog)
    _overrides: dict = field(default_factory=dict)

    def get_config_overrides(self):
        """Return a dict of ``{CONFIG_CONSTANT_NAME: value}`` for all
        parameters the user changed from the defaults."""
        return dict(self._overrides)


# ---------------------------------------------------------------------------
# Dataset scanning helpers (unchanged)
# ---------------------------------------------------------------------------

def _parse_bk2_filename(filename):
    """Extract metadata from a BK2 filename.

    Expected pattern::

        sub-01_ses-001_task-mario_level-w1l1_scene-3_clip-01500000000619.bk2

    Returns
    -------
    dict or None
        Keys: subject, session, level_str, scene_num, scene_id, clip_id.
    """
    m = re.match(
        r"(sub-\d+)_(ses-\d+)_task-mario_level-(w\d+l\d+)_scene-(\d+)_clip-(.+)\.bk2$",
        filename,
    )
    if not m:
        return None
    return {
        "subject": m.group(1),
        "session": m.group(2),
        "level_str": m.group(3),
        "scene_num": int(m.group(4)),
        "scene_id": f"{m.group(3)}s{m.group(4)}",
        "clip_id": m.group(5),
    }


def _get_outcome(bk2_path):
    """Read outcome from the companion _summary.json (or 'unknown')."""
    summary_path = bk2_path.replace(".bk2", "_summary.json")
    try:
        with open(summary_path) as f:
            meta = json.load(f)
        return meta.get("Outcome", "unknown")
    except (OSError, json.JSONDecodeError):
        return "unknown"


def scan_dataset(scenes_path):
    """Walk the mario.scenes dataset and build a structured index.

    Returns
    -------
    dict with keys:
        clips : list[dict]
            Each dict: path, filename, subject, session, level_str,
            scene_num, scene_id, clip_id, outcome.
        subjects : sorted list of unique subject strings
        levels : sorted list of unique level strings (e.g. "w1l1")
        scene_ids : sorted list of unique scene_id strings
    """
    clips = []
    subjects = set()
    levels = set()
    scene_ids = set()

    for sub_dir in sorted(os.listdir(scenes_path)):
        if not sub_dir.startswith("sub-"):
            continue
        sub_path = os.path.join(scenes_path, sub_dir)
        if not os.path.isdir(sub_path):
            continue
        for ses_dir in sorted(os.listdir(sub_path)):
            if not ses_dir.startswith("ses-"):
                continue
            gamelogs_dir = os.path.join(sub_path, ses_dir, "gamelogs")
            if not os.path.isdir(gamelogs_dir):
                continue
            for fname in sorted(os.listdir(gamelogs_dir)):
                if not fname.endswith(".bk2"):
                    continue
                info = _parse_bk2_filename(fname)
                if info is None:
                    continue
                full_path = os.path.join(gamelogs_dir, fname)
                outcome = _get_outcome(full_path)
                clip = {
                    "path": full_path,
                    "filename": fname,
                    "outcome": outcome,
                    **info,
                }
                clips.append(clip)
                subjects.add(info["subject"])
                levels.add(info["level_str"])
                scene_ids.add(info["scene_id"])

    return {
        "clips": clips,
        "subjects": sorted(subjects),
        "levels": sorted(levels),
        "scene_ids": sorted(scene_ids),
    }


# ---------------------------------------------------------------------------
# Dialog builders
# ---------------------------------------------------------------------------

def _tab_specs(dataset_index):
    """Return tab definitions for the tabbed advanced-config dialog.

    Each entry is ``(tab_title, [field_spec, ...])`` where ``field_spec`` is
    ``(label, kind, default, choices_or_None, tip)`` with ``kind`` one of
    ``"choice" | "bool" | "float" | "int"``.
    """
    if dataset_index is not None:
        scene_choices = ["(All)"] + dataset_index["scene_ids"]
        subject_choices = ["(All)"] + dataset_index["subjects"]
        outcome_choices = ["(All)", "completed", "death"]
    else:
        scene_choices = ["(All)"]
        subject_choices = ["(All)"]
        outcome_choices = ["(All)"]

    c = config

    return [
        ("Scene / Clip", [
            ("Scene ID", "choice", scene_choices[0], scene_choices,
                "Filter clips by scene (e.g. w1l1s3)"),
            ("Subject filter", "choice", subject_choices[0], subject_choices,
                "Filter clips by subject (e.g. sub-01)"),
            ("Outcome filter", "choice", outcome_choices[0], outcome_choices,
                "Filter by clip outcome (completed/death)"),
            ("Clip min duration (s)", "float", c.CLIP_MIN_DURATION_SEC, None,
                f"Default: {c.CLIP_MIN_DURATION_SEC}"),
            ("Clip min elements", "int", c.CLIP_MIN_ELEMENTS, None,
                f"Default: {c.CLIP_MIN_ELEMENTS}"),
            ("Clip max elements", "int", c.CLIP_MAX_ELEMENTS, None,
                f"Default: {c.CLIP_MAX_ELEMENTS}"),
        ]),
        ("Timing", [
            ("Execution timeout (s)", "float", c.EXECUTION_TIMEOUT, None,
                f"Default: {c.EXECUTION_TIMEOUT}"),
            ("Inter-execution interval (s)", "float", c.INTER_EXECUTION_INTERVAL,
                None, f"Default: {c.INTER_EXECUTION_INTERVAL}"),
            ("Inter-trial interval (s)", "float", c.INTER_TRIAL_INTERVAL, None,
                f"Default: {c.INTER_TRIAL_INTERVAL}"),
            ("Feedback duration (s)", "float", c.FEEDBACK_DURATION, None,
                f"Default: {c.FEEDBACK_DURATION}"),
            ("Gameplay max duration (s)", "float", c.GAMEPLAY_MAX_DURATION, None,
                f"Default: {c.GAMEPLAY_MAX_DURATION}"),
            ("Fixation duration (s)", "float", c.FIXATION_DURATION, None,
                f"Default: {c.FIXATION_DURATION}"),
            ("Countdown step duration (s)", "float", c.COUNTDOWN_STEP_DURATION,
                None, f"Default: {c.COUNTDOWN_STEP_DURATION}"),
            ("Speed factor", "float", c.SPEED_FACTOR, None,
                "Playback speed (1.0 = real-time, 0.5 = half speed). Must not be 0."),
        ]),
        ("Training", [
            ("Training reps per sequence", "int", c.TRAINING_REPS_PER_SEQ, None,
                f"Default: {c.TRAINING_REPS_PER_SEQ}"),
            ("Pretrain reps per scene", "int", c.PRETRAIN_REPS_PER_SCENE, None,
                f"Default: {c.PRETRAIN_REPS_PER_SCENE}"),
            ("Error rate threshold", "float", c.ERROR_RATE_THRESHOLD, None,
                f"Default: {c.ERROR_RATE_THRESHOLD}"),
            ("Fast bonus fraction", "float", c.FAST_BONUS_FRACTION, None,
                f"Default: {c.FAST_BONUS_FRACTION}"),
        ]),
        ("Scanner", [
            ("Scan prep duration (s)", "float", c.SCAN_PREP_DURATION, None,
                f"Default: {c.SCAN_PREP_DURATION}"),
            ("Scan execution duration (s)", "float", c.SCAN_EXECUTION_DURATION,
                None, f"Default: {c.SCAN_EXECUTION_DURATION}"),
            ("Scan ITI (s)", "float", c.SCAN_ITI, None,
                f"Default: {c.SCAN_ITI}"),
            ("Scan reps per sequence", "int", c.SCAN_REPS_PER_SEQ, None,
                f"Default: {c.SCAN_REPS_PER_SEQ}"),
            ("Scan number of runs", "int", c.SCAN_N_RUNS, None,
                f"Default: {c.SCAN_N_RUNS}"),
            ("Scan rest periods", "int", c.SCAN_REST_PERIODS, None,
                f"Default: {c.SCAN_REST_PERIODS}"),
            ("Scan rest duration (s)", "float", c.SCAN_REST_DURATION, None,
                f"Default: {c.SCAN_REST_DURATION}"),
        ]),
        ("Behavior", [
            ("Repeat until passed", "bool", False, None,
                "Loop the trial until the participant passes"),
        ]),
    ]


_wx_app = None  # module-level reference to keep wx.App alive


def _show_tabbed_config_dialog(dataset_index):
    """Show the advanced-config dialog with a wx.Notebook of tabs.

    Returns ``(values, ok)`` where ``values`` is ``{label: raw_value}`` for
    every field (numbers come back as strings from TextCtrl; ``_collect_overrides``
    coerces them) and ``ok`` is True iff the user clicked OK.
    """
    import wx
    # Ensure a wx.App exists and stays alive. PsychoPy may have already
    # created one; otherwise we create a minimal one and hold a module-level
    # reference so it survives this function's stack frame.
    global _wx_app
    if not wx.GetApp():
        _wx_app = wx.App(False)

    tabs = _tab_specs(dataset_index)

    dlg = wx.Dialog(
        None,
        title="Advanced Mode — Configuration",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    notebook = wx.Notebook(dlg)
    controls = {}  # field label -> wx control

    for tab_title, fields in tabs:
        panel = wx.Panel(notebook)
        grid = wx.FlexGridSizer(rows=len(fields), cols=2, vgap=8, hgap=12)
        grid.AddGrowableCol(1, 1)
        for label, kind, default, choices, tip in fields:
            lbl = wx.StaticText(panel, label=label)
            if kind == "choice":
                ctrl = wx.Choice(panel, choices=choices)
                if default in choices:
                    ctrl.SetStringSelection(default)
                else:
                    ctrl.SetSelection(0)
            elif kind == "bool":
                ctrl = wx.CheckBox(panel)
                ctrl.SetValue(bool(default))
            else:  # float / int — single-line TextCtrl
                ctrl = wx.TextCtrl(panel, value=str(default))
            if tip:
                lbl.SetToolTip(tip)
                ctrl.SetToolTip(tip)
            grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(ctrl, 1, wx.EXPAND)
            controls[label] = ctrl
        wrapper = wx.BoxSizer(wx.VERTICAL)
        wrapper.Add(grid, 1, wx.EXPAND | wx.ALL, 14)
        panel.SetSizer(wrapper)
        notebook.AddPage(panel, tab_title)

    btn_sizer = dlg.CreateButtonSizer(wx.OK | wx.CANCEL)

    main = wx.BoxSizer(wx.VERTICAL)
    main.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)
    main.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)
    dlg.SetSizer(main)
    dlg.Fit()
    # Force the dialog wide enough for all tab labels in one row so wx
    # doesn't fall back to scroll arrows on a narrow auto-fitted dialog.
    w, h = dlg.GetSize()
    # Estimate: ~100 px per tab label + 60 px margin (covers the 5 labels
    # "Scene / Clip / Timing / Training / Scanner / Behavior").
    min_w = max(w, 100 * notebook.GetPageCount() + 60)
    dlg.SetSize((min_w, h))
    dlg.SetMinSize((min_w, h))
    dlg.Center()

    ok = (dlg.ShowModal() == wx.ID_OK)

    values = {}
    for label, ctrl in controls.items():
        if isinstance(ctrl, wx.Choice):
            values[label] = ctrl.GetStringSelection()
        elif isinstance(ctrl, wx.CheckBox):
            values[label] = ctrl.GetValue()
        else:
            values[label] = ctrl.GetValue()
    dlg.Destroy()
    return values, ok


def _collect_overrides(dlg_dict):
    """Compare dialog values to current config defaults; return overrides.

    Returns
    -------
    dict
        ``{CONFIG_CONSTANT_NAME: new_value}`` for every field the user
        changed from the default.
    """
    overrides = {}
    for field_name, const_name in _FIELD_TO_CONFIG.items():
        default = getattr(config, const_name)
        raw = dlg_dict[field_name]
        # Coerce to the same type as the default
        try:
            if isinstance(default, float):
                value = float(raw)
            elif isinstance(default, int):
                value = int(raw)
            else:
                value = raw
        except (ValueError, TypeError):
            continue
        # Reject zero speed factor (would cause division by zero)
        if const_name == "SPEED_FACTOR" and value == 0:
            continue
        if value != default:
            overrides[const_name] = value
    return overrides


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_advanced_dialogs(scenes_path):
    """Run the advanced mode dialog sequence.

    Dialog 1: comprehensive configuration panel (~24 fields).
    Dialog 2 (optional): BK2 clip selection when a scene is filtered.

    Returns an AdvancedConfig.  If the user cancels at any stage,
    returns ``AdvancedConfig(enabled=False)``.
    """
    # --- Optionally scan dataset for dropdown population ---
    dataset_index = None
    if scenes_path and os.path.isdir(scenes_path):
        dataset_index = scan_dataset(scenes_path)
        if dataset_index and not dataset_index["clips"]:
            dataset_index = None  # treat empty dataset same as missing

    # --- Dialog 1: Advanced Configuration (tabbed) ---
    dlg_dict, ok = _show_tabbed_config_dialog(dataset_index)
    if not ok:
        return AdvancedConfig(enabled=False)

    # --- Collect overrides ---
    overrides = _collect_overrides(dlg_dict)
    repeat_until_passed = bool(dlg_dict["Repeat until passed"])

    # --- Determine scene/clip filters ---
    scene_filter = dlg_dict["Scene ID"]
    subject_filter = dlg_dict["Subject filter"]
    outcome_filter = dlg_dict["Outcome filter"]

    # If no scene filter or no dataset, skip clip selection
    if (
        scene_filter == "(All)"
        or dataset_index is None
    ):
        return AdvancedConfig(
            enabled=True,
            repeat_until_passed=repeat_until_passed,
            _overrides=overrides,
        )

    # --- Filter clips for Dialog 2 ---
    filtered = list(dataset_index["clips"])
    if scene_filter != "(All)":
        filtered = [c for c in filtered if c["scene_id"] == scene_filter]
    if subject_filter != "(All)":
        filtered = [c for c in filtered if c["subject"] == subject_filter]
    if outcome_filter != "(All)":
        filtered = [c for c in filtered if c["outcome"] == outcome_filter]

    if not filtered:
        err = gui.Dlg(title="Advanced Mode")
        err.addText("No clips match the selected filters.")
        err.show()
        return AdvancedConfig(
            enabled=True,
            repeat_until_passed=repeat_until_passed,
            _overrides=overrides,
        )

    # --- Dialog 2: Clip selection ---
    labels = ["(None — use default sequence selection)"]
    label_to_clip = {}
    for clip in filtered:
        label = (
            f"{clip['scene_id']} | {clip['subject']} {clip['session']} | "
            f"{clip['outcome']}"
        )
        labels.append(label)
        label_to_clip[label] = clip

    clip_info = {
        "Select clip": labels,
    }
    dlg2 = gui.DlgFromDict(
        dictionary=clip_info,
        title=f"Advanced Mode — Select Clip ({len(filtered)} matches)",
        order=["Select clip"],
    )
    if not dlg2.OK:
        return AdvancedConfig(enabled=False)

    selected_label = clip_info["Select clip"]
    if selected_label == labels[0]:
        # "(None — use default)" selected
        return AdvancedConfig(
            enabled=True,
            selected_scene_id=scene_filter,
            repeat_until_passed=repeat_until_passed,
            _overrides=overrides,
        )

    clip = label_to_clip[selected_label]
    scene_info = get_scene_info_any(clip["scene_id"], scenes_path)

    return AdvancedConfig(
        enabled=True,
        selected_bk2=clip["path"],
        selected_scene_id=clip["scene_id"],
        selected_scene_info=scene_info,
        repeat_until_passed=repeat_until_passed,
        _overrides=overrides,
    )
