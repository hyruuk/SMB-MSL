"""
Behavioral test session logic for the Berlot et al. (2020) Motor Sequence Learning task.

All 12 sequences intermixed, digits visible for both executions, no reward system.
Supports right-hand (standard) and left-hand transfer (intrinsic + extrinsic).
"""

import random

from psychopy import core

from berlot2020_task.config import (
    VALID_KEYS,
    VALID_KEYS_LEFT,
    ESCAPE_KEY,
    KEY_TO_FINGER,
    KEY_TO_FINGER_LEFT,
    EXECUTION_TIMEOUT,
    INTER_EXECUTION_INTERVAL,
    INTER_TRIAL_INTERVAL,
)
from berlot2020_task.sequences import (
    get_sequences,
    mirror_sequence_intrinsic,
    mirror_sequence_extrinsic,
)
from berlot2020_task.display import SequenceDisplay, show_instructions
from berlot2020_task.data_logging import DataLogger


def _collect_execution(win, keyboard, seq_display, sequence,
                       valid_keys=VALID_KEYS, key_to_finger=KEY_TO_FINGER):
    """Run one execution (9 keypresses) with digits visible.

    Parameters
    ----------
    win : psychopy.visual.Window
    keyboard : psychopy.hardware.keyboard.Keyboard
    seq_display : SequenceDisplay
    sequence : list[int]
    valid_keys : list[str]
        Keys to accept (right or left hand).
    key_to_finger : dict
        Mapping from key name to finger number.

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

        keys = keyboard.getKeys(keyList=valid_keys, waitRelease=False)
        for key in keys:
            if press_count >= n_presses:
                break

            finger = key_to_finger.get(key.name)
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


def _build_left_hand_trials(trained_seqs, n_reps_per_seq):
    """Build trial list for left-hand transfer test.

    Returns list of (seq_id, sequence, condition) tuples, shuffled.
    Intrinsic: same finger sequence, left hand (4 reps each).
    Extrinsic: mirrored fingers (4 reps each).
    """
    trials = []
    for seq_id, seq in trained_seqs.items():
        for _ in range(n_reps_per_seq):
            trials.append((seq_id, mirror_sequence_intrinsic(seq), "intrinsic"))
        for _ in range(n_reps_per_seq):
            trials.append((seq_id, mirror_sequence_extrinsic(seq), "extrinsic"))
    random.shuffle(trials)
    return trials


def run_test_session(win, keyboard, participant_id, group, session_number,
                     n_reps_per_seq, hand="right"):
    """Run a complete behavioral test session.

    Parameters
    ----------
    win : psychopy.visual.Window
    keyboard : psychopy.hardware.keyboard.Keyboard
    participant_id : str
    group : int
    session_number : int
    n_reps_per_seq : int
        Number of repetitions per sequence.
    hand : str
        "right" for standard test, "left" for left-hand transfer.
    """
    trained_seqs, untrained_seqs = get_sequences(group)

    if hand == "left":
        session_type = "test_left"
        valid_keys = VALID_KEYS_LEFT
        key_to_finger = KEY_TO_FINGER_LEFT
        trial_list = _build_left_hand_trials(trained_seqs, n_reps_per_seq)
        key_desc = (
            "1 = Thumb (Space)    2 = Index (F)\n"
            "3 = Middle (D)    4 = Ring (S)    5 = Pinky (A)"
        )
    else:
        session_type = "test"
        valid_keys = VALID_KEYS
        key_to_finger = KEY_TO_FINGER
        all_seqs = {**trained_seqs, **untrained_seqs}
        seq_ids = sorted(all_seqs.keys())
        trial_list = []
        for seq_id in seq_ids:
            condition = "trained" if seq_id in trained_seqs else "untrained"
            for _ in range(n_reps_per_seq):
                trial_list.append((seq_id, all_seqs[seq_id], condition))
        random.shuffle(trial_list)
        key_desc = (
            "1 = Thumb (Space)    2 = Index (J)\n"
            "3 = Middle (K)    4 = Ring (L)    5 = Pinky (;)"
        )

    logger = DataLogger(participant_id, group, session_type, session_number)
    seq_display = SequenceDisplay(win)

    hand_label = "LEFT HAND" if hand == "left" else "RIGHT HAND"
    show_instructions(
        win,
        f"BEHAVIORAL TEST — {hand_label}\n\n"
        "You will see a sequence of 9 digits.\n"
        "Press the corresponding keys as quickly and accurately as possible.\n\n"
        f"Key mapping:\n{key_desc}\n\n"
        "The digits will remain visible for both executions.\n\n"
        "Press any key to begin.",
    )

    trial_counter = 0

    try:
        for seq_id, sequence, condition in trial_list:
            trial_counter += 1

            # --- Execution 1: digits visible ---
            exec1 = _collect_execution(win, keyboard, seq_display, sequence,
                                       valid_keys=valid_keys,
                                       key_to_finger=key_to_finger)
            if exec1 is None:
                return

            logger.log_execution(
                block_number=1,  # test has no blocks
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
                hand=hand,
                condition=condition,
            )

            # Brief pause between executions
            win.flip()
            core.wait(INTER_EXECUTION_INTERVAL)

            # --- Execution 2: digits visible (test mode) ---
            seq_display.reset()
            exec2 = _collect_execution(win, keyboard, seq_display, sequence,
                                       valid_keys=valid_keys,
                                       key_to_finger=key_to_finger)
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
                hand=hand,
                condition=condition,
            )

            # Inter-trial interval
            win.flip()
            core.wait(INTER_TRIAL_INTERVAL)

    finally:
        logger.close()
