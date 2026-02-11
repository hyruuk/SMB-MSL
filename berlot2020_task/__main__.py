"""
Entry point for the Berlot et al. (2020) Motor Sequence Learning task.

Presents a GUI dialog to configure the session, then launches the
appropriate task (training, test, scan, or pre-training).

Can be run as:
    python -m berlot2020_task
"""

from psychopy import visual, gui, core
from psychopy.hardware.keyboard import Keyboard

from berlot2020_task.config import (
    SCREEN_SIZE,
    FULLSCREEN,
    MONITOR_NAME,
    BACKGROUND_COLOR,
)
from berlot2020_task.task_training import run_training_session
from berlot2020_task.task_test import run_test_session
from berlot2020_task.task_pretrain import run_pretrain_session
from berlot2020_task.task_scan import run_scan_session


def main():
    # --- Session configuration dialog ---
    info = {
        "Participant ID": "01",
        "Group": [1, 2],
        "Session type": [
            "training", "test", "test_left",
            "scan_paced", "scan_fullspeed", "pretrain",
        ],
        "Session number": 1,
        "Blocks / Reps": 4,
    }

    dlg = gui.DlgFromDict(
        dictionary=info,
        title="SMB-MSL Task Configuration",
        order=[
            "Participant ID",
            "Group",
            "Session type",
            "Session number",
            "Blocks / Reps",
        ],
    )

    if not dlg.OK:
        core.quit()

    participant_id = str(info["Participant ID"])
    group = int(info["Group"])
    session_type = info["Session type"]
    session_number = int(info["Session number"])
    n_blocks_or_reps = int(info["Blocks / Reps"])

    # --- Create window ---
    win = visual.Window(
        size=SCREEN_SIZE,
        fullscr=FULLSCREEN,
        monitor=MONITOR_NAME,
        color=BACKGROUND_COLOR,
        units="pix",
        allowGUI=False,
    )

    keyboard = Keyboard()

    try:
        if session_type == "training":
            run_training_session(
                win=win,
                keyboard=keyboard,
                participant_id=participant_id,
                group=group,
                session_number=session_number,
                n_blocks=n_blocks_or_reps,
            )
        elif session_type == "test":
            run_test_session(
                win=win,
                keyboard=keyboard,
                participant_id=participant_id,
                group=group,
                session_number=session_number,
                n_reps_per_seq=n_blocks_or_reps,
                hand="right",
            )
        elif session_type == "test_left":
            run_test_session(
                win=win,
                keyboard=keyboard,
                participant_id=participant_id,
                group=group,
                session_number=session_number,
                n_reps_per_seq=n_blocks_or_reps,
                hand="left",
            )
        elif session_type == "scan_paced":
            run_scan_session(
                win=win,
                keyboard=keyboard,
                participant_id=participant_id,
                group=group,
                session_number=session_number,
                paced=True,
            )
        elif session_type == "scan_fullspeed":
            run_scan_session(
                win=win,
                keyboard=keyboard,
                participant_id=participant_id,
                group=group,
                session_number=session_number,
                paced=False,
            )
        elif session_type == "pretrain":
            run_pretrain_session(
                win=win,
                keyboard=keyboard,
                participant_id=participant_id,
                group=group,
                session_number=session_number,
            )
        else:
            raise ValueError(f"Unknown session type: {session_type}")
    finally:
        win.close()
        core.quit()


if __name__ == "__main__":
    main()
