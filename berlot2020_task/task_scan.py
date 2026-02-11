"""
Scan session logic for the Berlot et al. (2020) Motor Sequence Learning task.

Supports paced (scans 1-3) and full-speed (scan 4) modes.
8 functional runs per session. 12 sequences x 6 reps = 72 trials per run.
Each trial = 5s: 1s prep + 3.5s execution/feedback + 0.5s ITI.
Sequences appear in consecutive pairs (same sequence back-to-back).
5 rest periods (10s fixation) randomly inserted per run.
"""

import random

from psychopy import core, event

from berlot2020_task.config import (
    VALID_KEYS,
    ESCAPE_KEY,
    KEY_TO_FINGER,
    SCANNER_TRIGGER_KEY,
    SCAN_PREP_DURATION,
    SCAN_EXECUTION_DURATION,
    SCAN_ITI,
    SCAN_REPS_PER_SEQ,
    SCAN_N_RUNS,
    SCAN_REST_PERIODS,
    SCAN_REST_DURATION,
    SCAN_POINTS_CORRECT,
    SCAN_POINTS_ERROR,
)
from berlot2020_task.sequences import get_sequences
from berlot2020_task.display import (
    SequenceDisplay,
    PacingLine,
    show_instructions,
    show_scan_feedback,
    show_run_rest,
    show_fixation_rest,
    show_waiting_for_scanner,
)
from berlot2020_task.data_logging import DataLogger


def _collect_scan_execution(win, keyboard, seq_display, sequence,
                            duration, pacing_line=None):
    """Collect keypresses within a fixed time window.

    Collects up to 9 presses within ``duration`` seconds.
    If pacing_line is provided, updates its fraction each frame (paced mode).
    After 9 presses or timeout, shows point feedback for remaining time.

    Parameters
    ----------
    win : psychopy.visual.Window
    keyboard : psychopy.hardware.keyboard.Keyboard
    seq_display : SequenceDisplay
    sequence : list[int]
    duration : float
        Fixed execution window in seconds.
    pacing_line : PacingLine or None
        If provided, expand each frame (paced). If None, no line drawn.

    Returns
    -------
    dict or None (None = escape pressed)
    """
    n_presses = len(sequence)
    response_keys = []
    response_times = []
    accuracy_per_press = []

    keyboard.clearEvents()
    keyboard.clock.reset()

    press_count = 0
    completed = False
    start_time = core.getTime()

    while True:
        elapsed = core.getTime() - start_time
        if elapsed >= duration:
            break

        # Check for escape
        escape_keys = keyboard.getKeys(keyList=[ESCAPE_KEY], waitRelease=False)
        if escape_keys:
            return None

        if not completed:
            # Collect keypresses
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
                press_count += 1

            if press_count >= n_presses:
                completed = True
                # Compute points immediately
                trial_correct = all(a == 1 for a in accuracy_per_press)
                points = SCAN_POINTS_CORRECT if trial_correct else SCAN_POINTS_ERROR
                if pacing_line:
                    pacing_line.hide()
                remaining = duration - (core.getTime() - start_time)
                show_scan_feedback(win, seq_display, points, remaining)
                break

        # Update pacing line
        if pacing_line:
            fraction = elapsed / duration
            pacing_line.update(fraction)

        # Draw frame
        seq_display.draw()
        if pacing_line:
            pacing_line.draw()
        win.flip()

    # Fill missing presses as errors if timed out
    while press_count < n_presses:
        response_keys.append("NA")
        response_times.append(-1)
        accuracy_per_press.append(0)
        press_count += 1

    # If we timed out (didn't complete), show feedback for 0 remaining time
    if not completed:
        trial_correct = all(a == 1 for a in accuracy_per_press)
        points = SCAN_POINTS_CORRECT if trial_correct else SCAN_POINTS_ERROR
    # points was already set above if completed

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
        "points": points,
    }


def _generate_run_trials(all_seqs, reps_per_seq, n_rest_periods):
    """Generate trial list for one run.

    12 sequences x ``reps_per_seq`` reps = 72 trials, arranged as
    consecutive pairs (each sequence repeated twice in a row).
    ``n_rest_periods`` rest markers inserted at random positions.

    Parameters
    ----------
    all_seqs : dict
        {seq_id: [digits]} for all 12 sequences.
    reps_per_seq : int
        Repetitions per sequence per run (6 in the paper).
    n_rest_periods : int
        Number of rest periods to insert (5 in the paper).

    Returns
    -------
    list
        Items are either ("trial", seq_id, execution_number) or ("rest",).
    """
    seq_ids = sorted(all_seqs.keys())

    # Build pairs: each seq appears reps_per_seq/2 times as a pair
    # (since each pair = 2 executions, reps_per_seq must be even)
    # Actually: 6 reps = 3 pairs per sequence
    n_pairs = reps_per_seq // 2
    pairs = []
    for seq_id in seq_ids:
        for _ in range(n_pairs):
            pairs.append(seq_id)

    # Shuffle pairs
    random.shuffle(pairs)

    # Expand pairs into trial items: each pair = 2 consecutive trials
    items = []
    for seq_id in pairs:
        items.append(("trial", seq_id, 1))
        items.append(("trial", seq_id, 2))

    # Insert rest periods at random positions (between trials, not in pairs)
    # We insert between pairs, so valid positions are at even indices
    pair_boundaries = list(range(0, len(items) + 1, 2))  # 0, 2, 4, ...
    # Exclude very start and very end to keep rests between trials
    interior = pair_boundaries[1:-1]
    rest_positions = sorted(random.sample(interior, min(n_rest_periods, len(interior))),
                            reverse=True)
    for pos in rest_positions:
        items.insert(pos, ("rest",))

    return items


def _run_single_run(win, keyboard, seq_display, pacing_line,
                    all_seqs, trained_ids, run_number, logger, paced,
                    participant_id, group, session_type):
    """Execute one functional run.

    Parameters
    ----------
    win : psychopy.visual.Window
    keyboard : psychopy.hardware.keyboard.Keyboard
    seq_display : SequenceDisplay
    pacing_line : PacingLine
    all_seqs : dict
    trained_ids : set
        Sequence IDs that are trained (for condition logging).
    run_number : int
    logger : DataLogger
    paced : bool
    participant_id : str
    group : int
    session_type : str

    Returns
    -------
    bool
        True if completed, False if escape pressed.
    """
    items = _generate_run_trials(all_seqs, SCAN_REPS_PER_SEQ, SCAN_REST_PERIODS)

    trial_counter = 0

    for item in items:
        if item[0] == "rest":
            show_fixation_rest(win, SCAN_REST_DURATION)
            continue

        _, seq_id, execution_number = item
        trial_counter += 1
        sequence = all_seqs[seq_id]
        condition = "trained" if seq_id in trained_ids else "untrained"

        # --- PREP phase (1.0s): show digits in white ---
        seq_display.show(sequence)
        if paced:
            pacing_line.reset()  # zero width, visible
        else:
            pacing_line.hide()
        seq_display.draw()
        win.flip()

        # Wait for prep duration, checking for escape
        prep_timer = core.CountdownTimer(SCAN_PREP_DURATION)
        abort = False
        while prep_timer.getTime() > 0:
            escape_keys = keyboard.getKeys(keyList=[ESCAPE_KEY], waitRelease=False)
            if escape_keys:
                abort = True
                break
            seq_display.draw()
            if paced:
                pacing_line.draw()
            win.flip()

        if abort:
            return False

        # --- GO signal + EXECUTION phase (3.5s) ---
        if paced:
            pacing_line.reset()
        else:
            pacing_line.show_go_cue()

        result = _collect_scan_execution(
            win, keyboard, seq_display, sequence,
            duration=SCAN_EXECUTION_DURATION,
            pacing_line=pacing_line if paced else None,
        )

        if result is None:
            return False

        # Hide pacing line after execution
        pacing_line.hide()

        # Log the trial
        logger.log_execution(
            block_number=1,
            trial_number=trial_counter,
            sequence_id=seq_id,
            sequence_digits=sequence,
            execution_number=execution_number,
            response_keys=result["response_keys"],
            response_times=result["response_times"],
            accuracy_per_press=result["accuracy_per_press"],
            accuracy_trial=result["accuracy_trial"],
            movement_time=result["movement_time"],
            inter_press_intervals=result["inter_press_intervals"],
            points_awarded=result["points"],
            run_number=run_number,
            hand="right",
            condition=condition,
        )

        # --- ITI (0.5s): blank ---
        win.flip()
        core.wait(SCAN_ITI)

    return True


def run_scan_session(win, keyboard, participant_id, group,
                     session_number, paced=True):
    """Run a complete scan session (8 runs).

    Parameters
    ----------
    win : psychopy.visual.Window
    keyboard : psychopy.hardware.keyboard.Keyboard
    participant_id : str
    group : int
    session_number : int
    paced : bool
        True for scans 1-3 (pacing line), False for scan 4 (full speed).
    """
    trained_seqs, untrained_seqs = get_sequences(group)
    all_seqs = {**trained_seqs, **untrained_seqs}
    trained_ids = set(trained_seqs.keys())

    session_type = "scan_paced" if paced else "scan_fullspeed"
    logger = DataLogger(participant_id, group, session_type, session_number)
    seq_display = SequenceDisplay(win)
    pacing_line = PacingLine(win, seq_display.total_width)

    mode_desc = "paced" if paced else "full speed"
    show_instructions(
        win,
        f"SCAN SESSION ({mode_desc})\n\n"
        "You will see a sequence of 9 digits.\n"
        "Press the corresponding keys as quickly and accurately as possible.\n\n"
        "Key mapping:\n"
        "1 = Thumb (Space)    2 = Index (J)\n"
        "3 = Middle (K)    4 = Ring (L)    5 = Pinky (;)\n\n"
        "The digits will remain visible.\n"
        "Each sequence will appear twice in a row.\n\n"
        "Press any key to begin.",
    )

    try:
        for run_num in range(1, SCAN_N_RUNS + 1):
            # Wait for scanner trigger
            show_waiting_for_scanner(win)
            event.waitKeys(keyList=[SCANNER_TRIGGER_KEY])

            completed = _run_single_run(
                win, keyboard, seq_display, pacing_line,
                all_seqs, trained_ids, run_num, logger, paced,
                participant_id, group, session_type,
            )

            if not completed:
                return  # Escape pressed

            # Rest between runs (except after last)
            if run_num < SCAN_N_RUNS:
                show_run_rest(win, run_num, SCAN_N_RUNS)

    finally:
        logger.close()
