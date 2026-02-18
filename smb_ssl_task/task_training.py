"""
Training session logic for the SMB SSL task.

Each block: 6 trained scenes x 4 reps = 24 trials, shuffled.
Each trial: execution 1 (guided) + execution 2 (from memory).
Adaptive MT threshold and points system across blocks.
Supports both MSP and gameplay modes.
"""

import random
import statistics

from psychopy import core

from smb_ssl_task.config import (
    TRAINING_REPS_PER_SEQ,
    ERROR_RATE_THRESHOLD,
    FAST_BONUS_FRACTION,
    POINTS_ERROR,
    POINTS_CORRECT,
    POINTS_FAST,
    INTER_EXECUTION_INTERVAL,
    INTER_TRIAL_INTERVAL,
    FEEDBACK_DURATION,
    FIXATION_DURATION,
    COUNTDOWN_STEPS,
    COUNTDOWN_STEP_DURATION,
    GAMEPLAY_BAR_Y_BASE,
    GAMEPLAY_BAR_FONT_SIZE,
)
from smb_ssl_task.config import verbose
from smb_ssl_task.scenes import get_scenes, get_canonical_sequence, get_canonical_sequence_source, get_clip_savestate_path
from smb_ssl_task.msp import ActionSequenceDisplay, collect_msp_execution
from smb_ssl_task.game import (
    execute_gameplay_trial,
    replay_bk2_preview,
    execute_gameplay_with_tracking,
)
from smb_ssl_task.display import (
    show_instructions,
    show_trial_points,
    show_block_feedback,
    show_rest,
    show_fixation_rest,
    show_countdown,
)
from smb_ssl_task.data_logging import DataLogger


def _wait_with_escape(win, input_handler, duration):
    """Wait for *duration* seconds, polling for escape each frame.

    Returns True if escape was pressed, False otherwise.
    """
    timer = core.CountdownTimer(duration)
    while timer.getTime() > 0:
        if input_handler.check_escape():
            return True
        win.flip()
    return False


def _compute_points_msp(exec2_data, mt_threshold):
    """Compute points based on MSP execution 2 (memory execution).

    If mt_threshold is None (first block), all correct trials get 1 point.
    """
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


def _compute_points_gameplay(exec2_data, time_threshold):
    """Compute points based on gameplay execution 2 (replay).

    If time_threshold is None (first block), all completed trials get 1 point.
    """
    if exec2_data["outcome"] != "completed":
        return POINTS_ERROR

    if time_threshold is None:
        return POINTS_CORRECT

    tt = exec2_data["traversal_time"]
    if tt < time_threshold * (1 - FAST_BONUS_FRACTION):
        return POINTS_FAST
    elif tt < time_threshold:
        return POINTS_CORRECT
    else:
        return POINTS_ERROR


def run_training_session(win, input_handler, participant_id, group,
                         session_number, n_blocks, mode="gameplay",
                         engine=None):
    """Run a complete training session.

    Parameters
    ----------
    win : psychopy.visual.Window
    input_handler : InputHandler
    participant_id : str
    group : int
    session_number : int
    n_blocks : int
    mode : str
        "msp" or "gameplay"
    engine : GameEngine or None
        Required if mode="gameplay".
    """
    trained_scenes, _ = get_scenes(group)
    scene_ids = sorted(trained_scenes.keys())

    logger = DataLogger(participant_id, group, "training", session_number)

    if mode == "msp":
        seq_display = ActionSequenceDisplay(win)
    else:
        seq_display = ActionSequenceDisplay(
            win, y_base=GAMEPLAY_BAR_Y_BASE, font_size=GAMEPLAY_BAR_FONT_SIZE,
        )

    if mode == "msp":
        show_instructions(
            win,
            "TRAINING SESSION (MSP Mode)\n\n"
            "You will see a sequence of button symbols with duration bars.\n"
            "Press and hold the correct buttons for the indicated duration,\n"
            "then release to advance to the next element.\n\n"
            "Controls:\n"
            "\u2190 \u2192 = Arrow keys    X = Jump    Z = Run\n\n"
            "After the first execution, the symbols will disappear.\n"
            "Try to reproduce the sequence from memory.\n\n"
            "Press any key to begin.",
        )
    else:
        show_instructions(
            win,
            "TRAINING SESSION (Gameplay Mode)\n\n"
            "You will play through short Mario scenes.\n"
            "Use the arrow keys to move and X to jump, Z to run.\n\n"
            "Each scene will be played twice in a row.\n"
            "Try to play faster and more consistently each time.\n\n"
            "Press any key to begin.",
        )

    mt_threshold = None
    trial_counter = 0

    try:
        for block_num in range(1, n_blocks + 1):
            # Generate trial order
            trial_list = []
            for sid in scene_ids:
                trial_list.extend([sid] * TRAINING_REPS_PER_SEQ)
            random.shuffle(trial_list)

            block_errors = 0
            block_mts = []
            block_points = 0

            for scene_id in trial_list:
                trial_counter += 1
                scene_info = trained_scenes[scene_id]

                if mode == "msp":
                    action_seq = get_canonical_sequence(scene_id)
                    target_symbols = [s for s, _ in action_seq]
                    source_clip = get_canonical_sequence_source(scene_id)
                    if verbose():
                        print(f"[MSP] Scene: {scene_id} | BK2: {source_clip or 'placeholder'} | Sequence: {' '.join(target_symbols)}")

                    # --- Execution 1: visible ---
                    exec1 = collect_msp_execution(
                        win, input_handler, seq_display,
                        action_seq, visible=True,
                    )
                    if exec1 is None:
                        return

                    logger.log_execution(
                        block_number=block_num,
                        trial_number=trial_counter,
                        scene_id=scene_id,
                        mode=mode,
                        execution_number=1,
                        target_sequence=target_symbols,
                        response_sequence=exec1["response_sequence"],
                        target_durations=exec1["target_durations"],
                        response_durations=exec1["response_durations"],
                        accuracy_per_element=exec1["accuracy_per_element"],
                        accuracy_trial=exec1["accuracy_trial"],
                        movement_time=exec1["movement_time"],
                        inter_element_intervals=exec1["inter_element_intervals"],
                    )

                    win.flip()
                    core.wait(INTER_EXECUTION_INTERVAL)

                    # --- Execution 2: hidden (memory) ---
                    exec2 = collect_msp_execution(
                        win, input_handler, seq_display,
                        action_seq, visible=False,
                    )
                    if exec2 is None:
                        return

                    points = _compute_points_msp(exec2, mt_threshold)
                    block_points += points

                    logger.log_execution(
                        block_number=block_num,
                        trial_number=trial_counter,
                        scene_id=scene_id,
                        mode=mode,
                        execution_number=2,
                        target_sequence=target_symbols,
                        response_sequence=exec2["response_sequence"],
                        target_durations=exec2["target_durations"],
                        response_durations=exec2["response_durations"],
                        accuracy_per_element=exec2["accuracy_per_element"],
                        accuracy_trial=exec2["accuracy_trial"],
                        movement_time=exec2["movement_time"],
                        inter_element_intervals=exec2["inter_element_intervals"],
                        points_awarded=points,
                    )

                    # Track block stats
                    if exec2["accuracy_trial"] == 0:
                        block_errors += 1
                    if exec2["movement_time"] is not None and exec2["accuracy_trial"] == 1:
                        block_mts.append(exec2["movement_time"])

                else:  # gameplay mode
                    # Select a BK2 clip and load the matching savestate
                    action_seq = get_canonical_sequence(scene_id)
                    source_clip = get_canonical_sequence_source(scene_id)
                    clip_state = get_clip_savestate_path(scene_id)
                    target_symbols = [s for s, _ in action_seq]
                    if verbose():
                        print(f"[GAMEPLAY] Scene: {scene_id} | BK2: {source_clip or 'placeholder'} | Seq: {' '.join(target_symbols)}")

                    # --- Fixation ---
                    if show_fixation_rest(win, FIXATION_DURATION,
                                          input_handler=input_handler):
                        return

                    # --- BK2 Preview Replay ---
                    engine.load_scene(scene_id, scene_info, state_path=clip_state)
                    preview_result = replay_bk2_preview(
                        win, input_handler, engine, seq_display, action_seq,
                    )
                    if preview_result is None:
                        return
                    preview_exit_x = preview_result["exit_x"]

                    # --- Countdown (overlaid on frozen game frame) ---
                    def _draw_game_and_bar():
                        engine.render()
                        seq_display.draw()
                    if show_countdown(
                        win,
                        steps=COUNTDOWN_STEPS,
                        step_duration=COUNTDOWN_STEP_DURATION,
                        draw_extras=_draw_game_and_bar,
                        input_handler=input_handler,
                    ):
                        return

                    # --- Execution 1: player plays with tracking ---
                    engine.load_scene(scene_id, scene_info, state_path=clip_state)
                    exec1 = execute_gameplay_with_tracking(
                        win, input_handler, engine, seq_display,
                        action_seq, preview_exit_x,
                    )
                    if exec1 is None:
                        return

                    logger.log_execution(
                        block_number=block_num,
                        trial_number=trial_counter,
                        scene_id=scene_id,
                        mode=mode,
                        execution_number=1,
                        outcome=exec1["outcome"],
                        traversal_time=exec1["traversal_time"],
                        distance_reached=exec1["distance_reached"],
                        target_sequence=exec1["target_sequence"],
                        response_sequence=exec1["response_sequence"],
                        accuracy_per_element=exec1["accuracy_per_element"],
                        accuracy_trial=exec1["accuracy_trial"],
                    )

                    # --- Inter-execution pause (escape-aware) ---
                    if _wait_with_escape(win, input_handler,
                                         INTER_EXECUTION_INTERVAL):
                        return

                    # --- Execution 2: player plays from memory ---
                    engine.load_scene(scene_id, scene_info, state_path=clip_state)
                    exec2 = execute_gameplay_with_tracking(
                        win, input_handler, engine, seq_display,
                        action_seq, preview_exit_x,
                    )
                    if exec2 is None:
                        return

                    points = _compute_points_gameplay(exec2, mt_threshold)
                    block_points += points

                    logger.log_execution(
                        block_number=block_num,
                        trial_number=trial_counter,
                        scene_id=scene_id,
                        mode=mode,
                        execution_number=2,
                        outcome=exec2["outcome"],
                        traversal_time=exec2["traversal_time"],
                        distance_reached=exec2["distance_reached"],
                        target_sequence=exec2["target_sequence"],
                        response_sequence=exec2["response_sequence"],
                        accuracy_per_element=exec2["accuracy_per_element"],
                        accuracy_trial=exec2["accuracy_trial"],
                        points_awarded=points,
                    )

                    # Track block stats
                    if exec2["outcome"] != "completed":
                        block_errors += 1
                    if exec2["outcome"] == "completed":
                        block_mts.append(exec2["traversal_time"])

                # Show points feedback
                show_trial_points(win, points, FEEDBACK_DURATION)

                # Inter-trial interval
                win.flip()
                core.wait(INTER_TRIAL_INTERVAL)

            # --- End of block ---
            n_trials_block = len(trial_list)
            error_rate = block_errors / n_trials_block if n_trials_block > 0 else 1.0
            median_mt = statistics.median(block_mts) if block_mts else 0.0

            # Update MT/time threshold
            if block_mts:
                block_median = statistics.median(block_mts)
                if error_rate < ERROR_RATE_THRESHOLD:
                    if mt_threshold is None or block_median < mt_threshold:
                        mt_threshold = block_median

            show_block_feedback(win, block_num, error_rate, median_mt, block_points)

            if block_num < n_blocks:
                show_rest(win)

    finally:
        logger.close()
