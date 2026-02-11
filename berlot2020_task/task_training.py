"""
Training session logic for the Berlot et al. (2020) Motor Sequence Learning task.

Each block: 24 trials (6 sequences x 4 reps, shuffled).
Each trial: execution 1 (digits visible) + execution 2 (digits hidden, memory).
Adaptive MT threshold and points system across blocks.
"""

import random
import statistics

from psychopy import core

from berlot2020_task.config import (
    VALID_KEYS,
    ESCAPE_KEY,
    KEY_TO_FINGER,
    EXECUTION_TIMEOUT,
    INTER_EXECUTION_INTERVAL,
    INTER_TRIAL_INTERVAL,
    FEEDBACK_DURATION,
    TRAINING_REPS_PER_SEQ,
    ERROR_RATE_THRESHOLD,
    FAST_BONUS_FRACTION,
    POINTS_ERROR,
    POINTS_CORRECT,
    POINTS_FAST,
)
from berlot2020_task.sequences import get_sequences
from berlot2020_task.display import (
    SequenceDisplay,
    show_instructions,
    show_trial_points,
    show_block_feedback,
    show_rest,
)
from berlot2020_task.data_logging import DataLogger


def _collect_execution(win, keyboard, seq_display, sequence, visible):
    """Run one execution (9 keypresses) and return response data.

    Parameters
    ----------
    win : psychopy.visual.Window
    keyboard : psychopy.hardware.keyboard.Keyboard
    seq_display : SequenceDisplay
    sequence : list[int]
        The 9-digit target sequence.
    visible : bool
        Whether digits are shown on screen.

    Returns
    -------
    dict with keys:
        response_keys, response_times, accuracy_per_press, accuracy_trial,
        movement_time, inter_press_intervals, timed_out
    """
    n_presses = len(sequence)
    response_keys = []
    response_times = []
    accuracy_per_press = []

    # Show or hide digits
    if visible:
        seq_display.show(sequence)
    else:
        seq_display.hide()

    # Clear keyboard buffer
    keyboard.clearEvents()
    keyboard.clock.reset()

    seq_display.draw()
    win.flip()

    press_count = 0
    start_time = core.getTime()

    while press_count < n_presses:
        # Check timeout
        if core.getTime() - start_time > EXECUTION_TIMEOUT:
            # Fill remaining positions with NA
            while press_count < n_presses:
                response_keys.append("NA")
                response_times.append(-1)
                accuracy_per_press.append(0)
                press_count += 1
            break

        # Check for escape
        escape_keys = keyboard.getKeys(keyList=[ESCAPE_KEY], waitRelease=False)
        if escape_keys:
            return None  # Signal abort

        # Check for valid keypresses
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

            # Visual feedback
            if visible:
                seq_display.update_press(press_count, is_correct)
                seq_display.draw()
                win.flip()

            press_count += 1

        # Draw each frame (even if no new keypress)
        if press_count < n_presses:
            seq_display.draw()
            win.flip()

    # Compute derived measures
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
        "timed_out": any(t < 0 for t in response_times),
    }


def _compute_points(exec1_data, exec2_data, mt_threshold):
    """Compute points for a trial based on both executions.

    Points are awarded based on execution 2 (memory execution).
    If mt_threshold is None (first block), all correct trials get 1 point.

    Returns
    -------
    int
        Points awarded for this trial.
    """
    # Points based on execution 2
    if exec2_data["accuracy_trial"] == 0 or exec2_data["timed_out"]:
        return POINTS_ERROR

    if mt_threshold is None:
        return POINTS_CORRECT

    mt = exec2_data["movement_time"]
    if mt is None:
        return POINTS_ERROR

    if mt < mt_threshold * (1 - FAST_BONUS_FRACTION):
        return POINTS_FAST
    elif mt < mt_threshold:
        return POINTS_CORRECT
    else:
        return POINTS_ERROR


def run_training_session(win, keyboard, participant_id, group, session_number, n_blocks):
    """Run a complete training session.

    Parameters
    ----------
    win : psychopy.visual.Window
    keyboard : psychopy.hardware.keyboard.Keyboard
    participant_id : str
    group : int
        1 or 2.
    session_number : int
    n_blocks : int
    """
    trained_seqs, _ = get_sequences(group)
    seq_ids = sorted(trained_seqs.keys())

    logger = DataLogger(participant_id, group, "training", session_number)
    seq_display = SequenceDisplay(win)

    # Show instructions
    show_instructions(
        win,
        "TRAINING SESSION\n\n"
        "You will see a sequence of 9 digits.\n"
        "Press the corresponding keys as quickly and accurately as possible.\n\n"
        "Key mapping:\n"
        "1 = Thumb (Space)    2 = Index (J)\n"
        "3 = Middle (K)    4 = Ring (L)    5 = Pinky (;)\n\n"
        "After the first execution, the digits will disappear.\n"
        "Try to reproduce the sequence from memory.\n\n"
        "Press any key to begin.",
    )

    mt_threshold = None
    trial_counter = 0

    try:
        for block_num in range(1, n_blocks + 1):
            # Generate trial order: each sequence repeated REPS times, shuffled
            trial_list = []
            for seq_id in seq_ids:
                trial_list.extend([seq_id] * TRAINING_REPS_PER_SEQ)
            random.shuffle(trial_list)

            block_errors = 0
            block_mts = []
            block_points = 0

            for trial_idx, seq_id in enumerate(trial_list):
                trial_counter += 1
                sequence = trained_seqs[seq_id]

                # --- Execution 1: digits visible ---
                exec1 = _collect_execution(
                    win, keyboard, seq_display, sequence, visible=True
                )
                if exec1 is None:
                    return  # Escape pressed

                logger.log_execution(
                    block_number=block_num,
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
                    points_awarded=0,  # points only on exec 2
                )

                # Brief pause between executions
                win.flip()  # clear screen
                core.wait(INTER_EXECUTION_INTERVAL)

                # --- Execution 2: digits hidden (memory) ---
                exec2 = _collect_execution(
                    win, keyboard, seq_display, sequence, visible=False
                )
                if exec2 is None:
                    return  # Escape pressed

                # Compute points
                points = _compute_points(exec1, exec2, mt_threshold)
                block_points += points

                logger.log_execution(
                    block_number=block_num,
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
                    points_awarded=points,
                )

                # Track block stats (based on execution 2)
                if exec2["accuracy_trial"] == 0:
                    block_errors += 1
                if exec2["movement_time"] is not None and exec2["accuracy_trial"] == 1:
                    block_mts.append(exec2["movement_time"])

                # Show points feedback
                show_trial_points(win, points, FEEDBACK_DURATION)

                # Inter-trial interval
                win.flip()
                core.wait(INTER_TRIAL_INTERVAL)

            # --- End of block ---
            n_trials_block = len(trial_list)
            error_rate = block_errors / n_trials_block if n_trials_block > 0 else 1.0
            median_mt = statistics.median(block_mts) if block_mts else 0.0

            # Update MT threshold
            if block_mts:
                block_median = statistics.median(block_mts)
                if error_rate < ERROR_RATE_THRESHOLD:
                    if mt_threshold is None or block_median < mt_threshold:
                        mt_threshold = block_median

            # Show block summary
            show_block_feedback(
                win, block_num, error_rate, median_mt, block_points
            )

            # Rest between blocks (except after last)
            if block_num < n_blocks:
                show_rest(win)

    finally:
        logger.close()
