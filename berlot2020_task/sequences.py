"""
Sequence definitions for the Berlot et al. (2020) Motor Sequence Learning task.

Set 1: trained for Group 1, untrained for Group 2
Set 2: trained for Group 2, untrained for Group 1

Each sequence is a list of 9 finger numbers (1-5).
Sequence IDs 1-6 correspond to Set 1, IDs 7-12 to Set 2.
"""

import random

SEQ_SET_1 = [
    [1, 5, 3, 5, 3, 4, 3, 1, 5],
    [1, 5, 2, 1, 4, 5, 3, 4, 2],
    [3, 4, 2, 1, 4, 5, 1, 5, 2],
    [3, 1, 5, 3, 4, 2, 1, 4, 5],
    [5, 3, 4, 5, 4, 2, 1, 5, 3],
    [5, 4, 2, 3, 4, 2, 3, 1, 5],
]

SEQ_SET_2 = [
    [5, 1, 3, 1, 3, 2, 3, 5, 1],
    [5, 1, 4, 5, 2, 1, 3, 2, 4],
    [3, 2, 4, 5, 2, 1, 5, 1, 4],
    [3, 5, 1, 3, 2, 4, 5, 2, 1],
    [1, 3, 2, 1, 2, 4, 5, 1, 3],
    [1, 2, 4, 3, 2, 4, 3, 5, 1],
]

# All sequences with persistent IDs (1-indexed)
ALL_SEQUENCES = {i + 1: seq for i, seq in enumerate(SEQ_SET_1 + SEQ_SET_2)}


def get_sequences(group):
    """Return (trained_seqs, untrained_seqs) for a given group.

    Each is a dict mapping sequence_id -> digit list.

    Parameters
    ----------
    group : int
        1 or 2.

    Returns
    -------
    trained : dict
        {seq_id: [digits]} for the 6 trained sequences.
    untrained : dict
        {seq_id: [digits]} for the 6 untrained sequences.
    """
    if group == 1:
        trained = {i + 1: seq for i, seq in enumerate(SEQ_SET_1)}
        untrained = {i + 7: seq for i, seq in enumerate(SEQ_SET_2)}
    elif group == 2:
        trained = {i + 7: seq for i, seq in enumerate(SEQ_SET_2)}
        untrained = {i + 1: seq for i, seq in enumerate(SEQ_SET_1)}
    else:
        raise ValueError(f"Group must be 1 or 2, got {group}")
    return trained, untrained


def generate_pretrain_sequences(n=6, length=9, seed=None):
    """Generate random sequences not in the experimental set.

    Parameters
    ----------
    n : int
        Number of sequences to generate.
    length : int
        Length of each sequence (digits per sequence).
    seed : int or None
        Random seed for reproducibility.

    Returns
    -------
    dict
        {seq_id: [digits]} with IDs starting at 101.
    """
    rng = random.Random(seed)
    existing = set(tuple(seq) for seq in ALL_SEQUENCES.values())
    result = {}
    seq_id = 101
    while len(result) < n:
        candidate = [rng.randint(1, 5) for _ in range(length)]
        if tuple(candidate) not in existing:
            result[seq_id] = candidate
            existing.add(tuple(candidate))
            seq_id += 1
    return result


def mirror_sequence_intrinsic(sequence):
    """Same finger numbers, just played with left hand.

    Returns the sequence unchanged — the key mapping change is handled
    by using FINGER_TO_KEY_LEFT instead of FINGER_TO_KEY.
    """
    return list(sequence)


def mirror_sequence_extrinsic(sequence):
    """Mirror finger mapping: finger N → finger (6-N).

    Right thumb(1) → Left pinky(5), Right index(2) → Left ring(4), etc.
    """
    return [6 - digit for digit in sequence]
