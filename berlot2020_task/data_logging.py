"""
Data logging utilities for the Berlot et al. (2020) Motor Sequence Learning task.

Writes one TSV row per execution (2 rows per trial).
"""

import os

from berlot2020_task.config import DATA_DIR, TSV_SEPARATOR

COLUMNS = [
    "participant_id",
    "group",
    "session_type",
    "session_number",
    "block_number",
    "run_number",
    "trial_number",
    "sequence_id",
    "sequence_digits",
    "execution_number",
    "hand",
    "condition",
    "response_keys",
    "response_times",
    "accuracy_per_press",
    "accuracy_trial",
    "movement_time",
    "inter_press_intervals",
    "points_awarded",
]


def _ensure_dir(path):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def get_session_dir(participant_id, session_type):
    """Return the output directory for a session, creating it if needed."""
    d = os.path.join(DATA_DIR, f"sub-{participant_id}", session_type)
    _ensure_dir(d)
    return d


class DataLogger:
    """Logs execution-level data to a TSV file.

    Parameters
    ----------
    participant_id : str
        e.g. "01"
    group : int
        1 or 2
    session_type : str
        "training", "test", "pretrain", "scan_paced", or "scan_fullspeed"
    session_number : int
        Session number within type.
    """

    def __init__(self, participant_id, group, session_type, session_number):
        self.participant_id = participant_id
        self.group = group
        self.session_type = session_type
        self.session_number = session_number

        out_dir = get_session_dir(participant_id, session_type)
        filename = f"sub-{participant_id}_{session_type}_ses-{session_number:02d}.tsv"
        self.filepath = os.path.join(out_dir, filename)

        self._file = open(self.filepath, "w")
        self._file.write(TSV_SEPARATOR.join(COLUMNS) + "\n")
        self._file.flush()

    def log_execution(
        self,
        block_number,
        trial_number,
        sequence_id,
        sequence_digits,
        execution_number,
        response_keys,
        response_times,
        accuracy_per_press,
        accuracy_trial,
        movement_time,
        inter_press_intervals,
        points_awarded,
        run_number=0,
        hand="right",
        condition="trained",
    ):
        """Append one row (one execution) to the TSV file.

        Parameters
        ----------
        block_number : int
        trial_number : int
        sequence_id : int
        sequence_digits : list[int]
            The 9-digit sequence.
        execution_number : int
            1 or 2.
        response_keys : list[str]
            Key names pressed.
        response_times : list[float]
            Absolute press timestamps (seconds).
        accuracy_per_press : list[int]
            1=correct, 0=incorrect for each press.
        accuracy_trial : int
            1 if all presses correct, else 0.
        movement_time : float
            Time from first to last keypress (seconds).
        inter_press_intervals : list[float]
            Intervals between consecutive presses.
        points_awarded : int
            Points for this execution (training) or 0 (test).
        run_number : int
            Functional run number (scan sessions) or 0.
        hand : str
            "right" or "left".
        condition : str
            "trained", "untrained", "intrinsic", "extrinsic", "random", or "pretrain".
        """
        row = [
            self.participant_id,
            str(self.group),
            self.session_type,
            str(self.session_number),
            str(block_number),
            str(run_number),
            str(trial_number),
            str(sequence_id),
            _format_list(sequence_digits),
            str(execution_number),
            hand,
            condition,
            _format_list(response_keys),
            _format_list(response_times, fmt=".4f"),
            _format_list(accuracy_per_press),
            str(accuracy_trial),
            f"{movement_time:.4f}" if movement_time is not None else "NA",
            _format_list(inter_press_intervals, fmt=".4f"),
            str(points_awarded),
        ]
        self._file.write(TSV_SEPARATOR.join(row) + "\n")
        self._file.flush()

    def close(self):
        """Close the output file."""
        if self._file and not self._file.closed:
            self._file.close()


def _format_list(lst, fmt=None):
    """Format a list as a semicolon-separated string for TSV storage."""
    if not lst:
        return "NA"
    if fmt:
        return ";".join(f"{x:{fmt}}" if isinstance(x, float) else str(x) for x in lst)
    return ";".join(str(x) for x in lst)
