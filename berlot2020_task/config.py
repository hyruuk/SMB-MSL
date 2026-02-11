"""
Configuration parameters for the Berlot et al. (2020) Motor Sequence Learning task.
"""

# --- Key mapping (right hand) ---
# Finger number -> PsychoPy key name (right hand on keyboard)
FINGER_TO_KEY = {
    1: "space",
    2: "j",
    3: "k",
    4: "l",
    5: "semicolon",
}

# Reverse mapping: key name -> finger number
KEY_TO_FINGER = {v: k for k, v in FINGER_TO_KEY.items()}

# All valid response keys
VALID_KEYS = list(FINGER_TO_KEY.values())

# --- Left-hand key mapping ---
# Mirrors right hand: thumb on space, then home row inward
FINGER_TO_KEY_LEFT = {
    1: "space",   # left thumb (same key as right)
    2: "f",       # left index
    3: "d",       # left middle
    4: "s",       # left ring
    5: "a",       # left pinky
}
KEY_TO_FINGER_LEFT = {v: k for k, v in FINGER_TO_KEY_LEFT.items()}
VALID_KEYS_LEFT = list(FINGER_TO_KEY_LEFT.values())
# Note: space is shared between hands — only one hand used at a time
# Extrinsic mirroring: right finger N → left finger (6-N)

# Escape key to abort
ESCAPE_KEY = "escape"

# --- Display settings ---
SCREEN_SIZE = (1920, 1080)
FULLSCREEN = True
MONITOR_NAME = "default"
BACKGROUND_COLOR = (-1, -1, -1)  # black

# Digit display
DIGIT_FONT_SIZE = 60  # height in pixels
DIGIT_SPACING = 80  # horizontal spacing between digit centers (pixels)
DIGIT_COLOR_DEFAULT = (1, 1, 1)  # white
DIGIT_COLOR_CORRECT = (-1, 1, -1)  # green
DIGIT_COLOR_ERROR = (1, -1, -1)  # red
DIGIT_Y_POS = 0  # vertical position of digit row

# Feedback / instruction text
TEXT_FONT_SIZE = 40
TEXT_COLOR = (1, 1, 1)  # white

# --- Timing (seconds) ---
EXECUTION_TIMEOUT = 30.0  # max time for one execution of 9 keypresses
INTER_EXECUTION_INTERVAL = 0.5  # pause between execution 1 and 2 within a trial
INTER_TRIAL_INTERVAL = 1.0  # pause between trials
FEEDBACK_DURATION = 0.8  # how long to show points after a trial
BLOCK_SUMMARY_DURATION = None  # None = self-paced (wait for keypress)
REST_DURATION = None  # None = self-paced (wait for keypress)

# --- Training parameters ---
TRAINING_TRIALS_PER_BLOCK = 24  # total trials per block
TRAINING_REPS_PER_SEQ = 4  # repetitions of each sequence per block (6 seq * 4 = 24)
ERROR_RATE_THRESHOLD = 0.15  # max error rate to update MT threshold
FAST_BONUS_FRACTION = 0.20  # >=20% faster than threshold for 3 points

# Points
POINTS_ERROR = 0
POINTS_CORRECT = 1
POINTS_FAST = 3

# --- Test parameters ---
TEST_DEFAULT_REPS_PER_SEQ = 2  # default repetitions per sequence in test session

# --- Scanner settings ---
SCANNER_TRIGGER_KEY = "equal"  # '=' key, configurable
SCAN_TR = 1.0  # TR in seconds

# --- Scan trial timing ---
SCAN_PREP_DURATION = 1.0      # digits appear, wait before go signal
SCAN_EXECUTION_DURATION = 3.5  # execution + feedback window
SCAN_ITI = 0.5                 # inter-trial interval
SCAN_TRIAL_DURATION = 5.0      # total (prep + exec + ITI)
SCAN_REPS_PER_SEQ = 6          # each sequence repeated 6x per run
SCAN_N_RUNS = 8                # 8 functional runs per session
SCAN_REST_PERIODS = 5          # rest periods per run
SCAN_REST_DURATION = 10.0      # seconds per rest period

# --- Scan points ---
SCAN_POINTS_CORRECT = 3
SCAN_POINTS_ERROR = 0

# --- Pacing line ---
PACING_LINE_COLOR = (1, 0.4, 0.7)  # pink
PACING_LINE_HEIGHT = 4              # pixels
PACING_LINE_Y_OFFSET = -50         # below digits
# Line width spans the full digit row width

# --- Pre-training ---
PRETRAIN_N_SEQUENCES = 6
PRETRAIN_REPS_PER_SEQ = 4

# --- Data output ---
DATA_DIR = "data"
TSV_SEPARATOR = "\t"
