"""
Pre-training session for the Berlot et al. (2020) Motor Sequence Learning task.

Familiarization with the apparatus using random sequences not in the experimental set.
Same trial structure as behavioral test (self-paced, digits visible).
"""

import random

from psychopy import core

from berlot2020_task.config import (
    VALID_KEYS,
    ESCAPE_KEY,
    KEY_TO_FINGER,
    EXECUTION_TIMEOUT,
    INTER_EXECUTION_INTERVAL,
    INTER_TRIAL_INTERVAL,
    PRETRAIN_N_SEQUENCES,
    PRETRAIN_REPS_PER_SEQ,
)
from berlot2020_task.sequences import generate_pretrain_sequences
from berlot2020_task.display import SequenceDisplay, show_instructions
from berlot2020_task.data_logging import DataLogger


def _collect_execution(win, keyboard, seq_display, sequence):
    """Run one execution (9 keypresses) with digits visible.

    Parameters
    ----------
    win : psychopy.visual.Window
    keyboard : psychopy.hardware.keyboard.Keyboard
    seq_display : SequenceDisplay
    sequence : list[int]

    Returns
    -------
    dict or None (None = escape pressed)
    """
    n_presses = len(sequence)
    response_keys = []
    response_times = []
    accuracy_per_press = []

    seq_display.show(sequence)
    keyboard.clearEvents()
    keyboard.clock.reset()
    seq_display.draw()
    win.flip()

    press_count = 0
    start_time = core.getTime()

    while press_count < n_presses:
        if core.getTime() - start_time > EXECUTION_TIMEOUT:
            while press_count < n_presses:
                response_keys.append("NA")
                response_times.append(-1)
                accuracy_per_press.append(0)
                press_count += 1
            break

        escape_keys = keyboard.getKeys(keyList=[ESCAPE_KEY], waitRelease=False)
        if escape_keys:
            return None

        keys = keyboard.getKeys(keyList=VALID_KEYS, waitRelease=False)
        for key in keys:
            if press_count >= n_presses:
                break

            finger = KEY_TO_FINGER.get(key.name)
            expected = sequence[press_count]
            is_correct = finger == expected

            response_keys.append(key.name)
            response_times.append(key.tDown)
            accuracy_per_press.append(1 if is_correct else 0)

            seq_display.update_press(press_count, is_correct)
            seq_display.draw()
            win.flip()

            press_count += 1

        if press_count < n_presses:
            seq_display.draw()
            win.flip()

    accuracy_trial = 1 if all(a == 1 for a in accuracy_per_press) else 0

    valid_times = [t for t in response_times if t >= 0]
    if len(valid_times) >= 2:
        movement_time = valid_times[-1] - valid_times[0]
        inter_press_intervals = [
            valid_times[i + 1] - valid_times[i] for i in range(len(valid_times) - 1)
        ]
    else:
        movement_time = None
        inter_press_intervals = []

    return {
        "response_keys": response_keys,
        "response_times": response_times,
        "accuracy_per_press": accuracy_per_press,
        "accuracy_trial": accuracy_trial,
        "movement_time": movement_time,
        "inter_press_intervals": inter_press_intervals,
    }


def run_pretrain_session(win, keyboard, participant_id, group, session_number):
    """Pre-training: familiarization with apparatus.

    Uses random sequences not in the experimental set.
    Same trial structure as behavioral test (self-paced, digits visible).

    Parameters
    ----------
    win : psychopy.visual.Window
    keyboard : psychopy.hardware.keyboard.Keyboard
    participant_id : str
    group : int
    session_number : int
    """
    pretrain_seqs = generate_pretrain_sequences(
        n=PRETRAIN_N_SEQUENCES, seed=42
    )

    logger = DataLogger(participant_id, group, "pretrain", session_number)
    seq_display = SequenceDisplay(win)

    show_instructions(
        win,
        "PRE-TRAINING SESSION\n\n"
        "You will see a sequence of 9 digits.\n"
        "Press the corresponding keys as quickly and accurately as possible.\n\n"
        "Key mapping:\n"
        "1 = Thumb (Space)    2 = Index (J)\n"
        "3 = Middle (K)    4 = Ring (L)    5 = Pinky (;)\n\n"
        "The digits will remain visible for both executions.\n\n"
        "Press any key to begin.",
    )

    # Generate trial list: each sequence repeated PRETRAIN_REPS_PER_SEQ times
    trial_list = []
    for seq_id in sorted(pretrain_seqs.keys()):
        trial_list.extend([seq_id] * PRETRAIN_REPS_PER_SEQ)
    random.shuffle(trial_list)

    trial_counter = 0

    try:
        for seq_id in trial_list:
            trial_counter += 1
            sequence = pretrain_seqs[seq_id]

            # --- Execution 1: digits visible ---
            exec1 = _collect_execution(win, keyboard, seq_display, sequence)
            if exec1 is None:
                return

            logger.log_execution(
                block_number=1,
                trial_number=trial_counter,
                sequence_id=seq_id,
                sequence_digits=sequence,
                execution_number=1,
                response_keys=exec1["response_keys"],
                response_times=exec1["response_times"],
                accuracy_per_press=exec1["accuracy_per_press"],
                accuracy_trial=exec1["accuracy_trial"],
                movement_time=exec1["movement_time"],
                inter_press_intervals=exec1["inter_press_intervals"],
                points_awarded=0,
                hand="right",
                condition="pretrain",
            )

            # Brief pause between executions
            win.flip()
            core.wait(INTER_EXECUTION_INTERVAL)

            # --- Execution 2: digits visible ---
            seq_display.reset()
            exec2 = _collect_execution(win, keyboard, seq_display, sequence)
            if exec2 is None:
                return

            logger.log_execution(
                block_number=1,
                trial_number=trial_counter,
                sequence_id=seq_id,
                sequence_digits=sequence,
                execution_number=2,
                response_keys=exec2["response_keys"],
                response_times=exec2["response_times"],
                accuracy_per_press=exec2["accuracy_per_press"],
                accuracy_trial=exec2["accuracy_trial"],
                movement_time=exec2["movement_time"],
                inter_press_intervals=exec2["inter_press_intervals"],
                points_awarded=0,
                hand="right",
                condition="pretrain",
            )

            # Inter-trial interval
            win.flip()
            core.wait(INTER_TRIAL_INTERVAL)

    finally:
        logger.close()
