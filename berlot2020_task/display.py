"""
Visual stimulus classes for the Berlot et al. (2020) Motor Sequence Learning task.

Manages digit display, per-keypress feedback, pacing line, and information screens.
"""

from psychopy import visual, event, core

from berlot2020_task.config import (
    DIGIT_FONT_SIZE,
    DIGIT_SPACING,
    DIGIT_COLOR_DEFAULT,
    DIGIT_COLOR_CORRECT,
    DIGIT_COLOR_ERROR,
    DIGIT_Y_POS,
    TEXT_FONT_SIZE,
    TEXT_COLOR,
    PACING_LINE_COLOR,
    PACING_LINE_HEIGHT,
    PACING_LINE_Y_OFFSET,
)


class SequenceDisplay:
    """Manages the 9 on-screen digit stimuli for one sequence.

    Parameters
    ----------
    win : psychopy.visual.Window
        The experiment window.
    """

    N_DIGITS = 9

    def __init__(self, win):
        self.win = win
        # Pre-create 9 TextStim objects, centered horizontally
        total_width = (self.N_DIGITS - 1) * DIGIT_SPACING
        start_x = -total_width / 2
        self._stims = []
        for i in range(self.N_DIGITS):
            stim = visual.TextStim(
                win,
                text="",
                pos=(start_x + i * DIGIT_SPACING, DIGIT_Y_POS),
                height=DIGIT_FONT_SIZE,
                color=DIGIT_COLOR_DEFAULT,
                units="pix",
                bold=True,
            )
            self._stims.append(stim)
        self._visible = False
        # Store the total width for use by PacingLine
        self.total_width = total_width + DIGIT_SPACING  # include half-spacing on each side

    def show(self, sequence):
        """Set digit texts and make them visible.

        Parameters
        ----------
        sequence : list[int]
            9 finger numbers to display.
        """
        for i, digit in enumerate(sequence):
            self._stims[i].text = str(digit)
            self._stims[i].color = DIGIT_COLOR_DEFAULT
        self._visible = True

    def hide(self):
        """Make all digits invisible (for memory execution)."""
        self._visible = False

    def update_press(self, position, is_correct):
        """Update the color of a digit after a keypress.

        Parameters
        ----------
        position : int
            0-indexed position in the sequence.
        is_correct : bool
            Whether the keypress was correct.
        """
        if is_correct:
            self._stims[position].color = DIGIT_COLOR_CORRECT
        else:
            self._stims[position].color = DIGIT_COLOR_ERROR

    def reset(self):
        """Reset all digits to default color."""
        for stim in self._stims:
            stim.color = DIGIT_COLOR_DEFAULT

    def draw(self):
        """Draw digits if visible. Call this every frame."""
        if self._visible:
            for stim in self._stims:
                stim.draw()


class PacingLine:
    """Expanding pink line under the digits for paced scan sessions.

    Parameters
    ----------
    win : psychopy.visual.Window
    full_width : float
        Maximum width in pixels (should match digit row span).
    """

    def __init__(self, win, full_width):
        self.win = win
        self.full_width = full_width
        self._rect = visual.Rect(
            win,
            width=0,
            height=PACING_LINE_HEIGHT,
            pos=(0, DIGIT_Y_POS + PACING_LINE_Y_OFFSET),
            fillColor=PACING_LINE_COLOR,
            lineColor=PACING_LINE_COLOR,
            units="pix",
        )
        self._visible = False

    def reset(self):
        """Reset line to zero width and make visible."""
        self._rect.width = 0
        self._visible = True

    def update(self, fraction):
        """Set line width to fraction (0.0-1.0) of full width.

        Called each frame during paced execution.
        """
        fraction = max(0.0, min(1.0, fraction))
        self._rect.width = self.full_width * fraction

    def show_go_cue(self):
        """Show short static line as go-cue (full-speed mode)."""
        self._rect.width = self.full_width * 0.1  # short bar
        self._visible = True

    def hide(self):
        """Make invisible."""
        self._visible = False

    def draw(self):
        """Draw if visible."""
        if self._visible:
            self._rect.draw()


# --- Instruction / feedback screens ---

def show_instructions(win, text, keys=None):
    """Display instruction text and wait for a keypress to continue.

    Parameters
    ----------
    win : psychopy.visual.Window
    text : str
        Instruction text to display.
    keys : list[str] or None
        Keys to accept. None = any key.
    """
    msg = visual.TextStim(
        win,
        text=text,
        height=TEXT_FONT_SIZE,
        color=TEXT_COLOR,
        units="pix",
        wrapWidth=win.size[0] * 0.8,
    )
    msg.draw()
    win.flip()
    event.waitKeys(keyList=keys)


def show_trial_points(win, points, duration):
    """Briefly display points earned after a trial.

    Parameters
    ----------
    win : psychopy.visual.Window
    points : int
    duration : float
        Seconds to display.
    """
    if points == 0:
        color = DIGIT_COLOR_ERROR
    elif points >= 3:
        color = DIGIT_COLOR_CORRECT
    else:
        color = TEXT_COLOR

    msg = visual.TextStim(
        win,
        text=f"+{points}",
        height=DIGIT_FONT_SIZE,
        color=color,
        units="pix",
        bold=True,
    )
    msg.draw()
    win.flip()
    core.wait(duration)


def show_block_feedback(win, block_number, error_rate, median_mt, total_points):
    """Display end-of-block summary. Self-paced (wait for keypress).

    Parameters
    ----------
    win : psychopy.visual.Window
    block_number : int
    error_rate : float
    median_mt : float
        Median movement time in seconds.
    total_points : int
    """
    text = (
        f"Block {block_number} Complete\n\n"
        f"Error rate: {error_rate * 100:.0f}%\n"
        f"Median movement time: {median_mt:.2f}s\n"
        f"Total points: {total_points}\n\n"
        f"Press any key to continue"
    )
    msg = visual.TextStim(
        win,
        text=text,
        height=TEXT_FONT_SIZE,
        color=TEXT_COLOR,
        units="pix",
        wrapWidth=win.size[0] * 0.8,
    )
    msg.draw()
    win.flip()
    event.waitKeys()


def show_rest(win):
    """Display a rest screen between blocks. Self-paced."""
    text = "Take a break.\n\nPress any key when ready to continue."
    msg = visual.TextStim(
        win,
        text=text,
        height=TEXT_FONT_SIZE,
        color=TEXT_COLOR,
        units="pix",
        wrapWidth=win.size[0] * 0.8,
    )
    msg.draw()
    win.flip()
    event.waitKeys()


# --- Scan session display functions ---

def show_scan_feedback(win, seq_display, points, remaining_time):
    """Show +3 or +0 for the remainder of the execution window.

    Parameters
    ----------
    win : psychopy.visual.Window
    seq_display : SequenceDisplay
        Digits remain visible behind feedback.
    points : int
    remaining_time : float
        Seconds to display.
    """
    if remaining_time <= 0:
        return

    if points == 0:
        color = DIGIT_COLOR_ERROR
    else:
        color = DIGIT_COLOR_CORRECT

    msg = visual.TextStim(
        win,
        text=f"+{points}",
        height=DIGIT_FONT_SIZE,
        color=color,
        pos=(0, DIGIT_Y_POS + 80),  # above digits
        units="pix",
        bold=True,
    )

    timer = core.CountdownTimer(remaining_time)
    while timer.getTime() > 0:
        seq_display.draw()
        msg.draw()
        win.flip()


def show_run_rest(win, run_number, n_runs):
    """Rest screen between runs. Self-paced.

    Parameters
    ----------
    win : psychopy.visual.Window
    run_number : int
        Just-completed run number.
    n_runs : int
        Total number of runs.
    """
    text = (
        f"Run {run_number} of {n_runs} complete.\n\n"
        "Take a break.\n\n"
        "Press any key when ready for the next run."
    )
    msg = visual.TextStim(
        win,
        text=text,
        height=TEXT_FONT_SIZE,
        color=TEXT_COLOR,
        units="pix",
        wrapWidth=win.size[0] * 0.8,
    )
    msg.draw()
    win.flip()
    event.waitKeys()


def show_fixation_rest(win, duration):
    """10s rest period inserted between trials (fixation cross).

    Parameters
    ----------
    win : psychopy.visual.Window
    duration : float
        Seconds to show fixation.
    """
    cross = visual.TextStim(
        win,
        text="+",
        height=DIGIT_FONT_SIZE,
        color=TEXT_COLOR,
        units="pix",
        bold=True,
    )
    cross.draw()
    win.flip()
    core.wait(duration)


def show_waiting_for_scanner(win):
    """'Waiting for scanner...' screen until trigger received.

    Parameters
    ----------
    win : psychopy.visual.Window
    """
    msg = visual.TextStim(
        win,
        text="Waiting for scanner...",
        height=TEXT_FONT_SIZE,
        color=TEXT_COLOR,
        units="pix",
    )
    msg.draw()
    win.flip()
