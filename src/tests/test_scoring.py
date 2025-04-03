import pytest
import json
from pathlib import Path
from src.scoring.scoring import ARCScorer

# Helper function to create mock JSON files
def create_mock_json(path: Path, data: dict):
    with open(path, 'w') as f:
        json.dump(data, f)

# --- Test Data ---

# Solution Data (Example Task 'test_task')
SOLUTION_DATA = {
    "train": [],
    "test": [
        {"input": [[1]], "output": [[1, 1], [1, 1]]},  # Pair 0
        {"input": [[2]], "output": [[2, 2]]},          # Pair 1
        {"input": [[3]], "output": [[3]]}           # Pair 2
    ]
}

# Submission Scenarios

# 1. Perfect Match
SUBMISSION_PERFECT = [
    # Pair 0
    {"attempt_1": {"answer": [[1, 1], [1, 1]], "metadata": {"pair_index": 0, "cost": {"total_cost": 0.1}}}},
    # Pair 1
    {"attempt_1": {"answer": [[2, 2]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}},
    # Pair 2
    {"attempt_1": {"answer": [[3]], "metadata": {"pair_index": 2, "cost": {"total_cost": 0.1}}}}
]

# 2. No Match
SUBMISSION_NO_MATCH = [
    # Pair 0
    {"attempt_1": {"answer": [[0, 0], [0, 0]], "metadata": {"pair_index": 0, "cost": {"total_cost": 0.1}}}},
    # Pair 1
    {"attempt_1": {"answer": [[9, 9]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}},
    # Pair 2
    {"attempt_1": {"answer": [[8]], "metadata": {"pair_index": 2, "cost": {"total_cost": 0.1}}}}
]

# 3. Partial Match (Pair 1 correct)
SUBMISSION_PARTIAL = [
    # Pair 0
    {"attempt_1": {"answer": [[0, 0], [0, 0]], "metadata": {"pair_index": 0, "cost": {"total_cost": 0.1}}}},
    # Pair 1
    {"attempt_1": {"answer": [[2, 2]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}},
    # Pair 2
    {"attempt_1": {"answer": [[8]], "metadata": {"pair_index": 2, "cost": {"total_cost": 0.1}}}}
]

# 4. Multiple Attempts (Pair 0 correct on 2nd attempt)
SUBMISSION_MULTI_ATTEMPT = [
     # Pair 0
    {"attempt_1": {"answer": [[0, 0], [0, 0]], "metadata": {"pair_index": 0, "cost": {"total_cost": 0.1}}},
     "attempt_2": {"answer": [[1, 1], [1, 1]], "metadata": {"pair_index": 0, "cost": {"total_cost": 0.15}}}},
    # Pair 1
    {"attempt_1": {"answer": [[9, 9]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}},
    # Pair 2
    {"attempt_1": {"answer": [[8]], "metadata": {"pair_index": 2, "cost": {"total_cost": 0.1}}}}
]

# 5. Incorrect Dimensions (Pair 0)
SUBMISSION_WRONG_DIM = [
    # Pair 0
    {"attempt_1": {"answer": [[1]], "metadata": {"pair_index": 0, "cost": {"total_cost": 0.1}}}}, # Wrong dim
    # Pair 1
    {"attempt_1": {"answer": [[2, 2]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}},
    # Pair 2
    {"attempt_1": {"answer": [[3]], "metadata": {"pair_index": 2, "cost": {"total_cost": 0.1}}}}
]

# 6. Different Pixels (Pair 0)
SUBMISSION_DIFF_PIXELS = [
    # Pair 0
    {"attempt_1": {"answer": [[1, 0], [1, 1]], "metadata": {"pair_index": 0, "cost": {"total_cost": 0.1}}}}, # Diff pixel
    # Pair 1
    {"attempt_1": {"answer": [[2, 2]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}},
    # Pair 2
    {"attempt_1": {"answer": [[3]], "metadata": {"pair_index": 2, "cost": {"total_cost": 0.1}}}}
]

# 7. None Submission (Pair 0)
SUBMISSION_NONE = [
    # Pair 0
    {"attempt_1": None}, # Attempt 1 is None for this pair
    # Pair 1
    {"attempt_1": {"answer": [[2, 2]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}},
    # Pair 2
    {"attempt_1": {"answer": [[3]], "metadata": {"pair_index": 2, "cost": {"total_cost": 0.1}}}}
]

# 8. Empty List Submission (Pair 0)
SUBMISSION_EMPTY_LIST = [
    # Pair 0
    {"attempt_1": {"answer": [], "metadata": {"pair_index": 0, "cost": {"total_cost": 0.1}}}}, # Empty list
    # Pair 1
    {"attempt_1": {"answer": [[2, 2]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}},
    # Pair 2
    {"attempt_1": {"answer": [[3]], "metadata": {"pair_index": 2, "cost": {"total_cost": 0.1}}}}
]

# 9. Pair Index Metadata (Pairs submitted out of order, Pair 1 correct)
SUBMISSION_PAIR_INDEX_META = [
    # Pair 2 submitted first
    {"attempt_1": {"answer": [[8]], "metadata": {"pair_index": 2, "cost": {"total_cost": 0.1}}}},
    # Pair 0 submitted second
    {"attempt_1": {"answer": [[0, 0], [0, 0]], "metadata": {"pair_index": 0, "cost": {"total_cost": 0.1}}}},
    # Pair 1 submitted third (correct)
    {"attempt_1": {"answer": [[2, 2]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}},
]

# --- Malformed Submissions for Error Handling Tests ---

# 10. Attempt data is not a dictionary
SUBMISSION_MALFORMED_NOT_DICT = [
    # Pair 0
    {"attempt_1": "not_a_dictionary"}, # Invalid attempt data type
    # Pair 1
    {"attempt_1": {"answer": [[2, 2]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}}
]

# 11. Attempt data is missing 'metadata' key
SUBMISSION_MALFORMED_NO_METADATA = [
    # Pair 0
    {"attempt_1": {"answer": [[1, 1], [1, 1]]}}, # Missing metadata
    # Pair 1
    {"attempt_1": {"answer": [[2, 2]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}}
]

# 12. Attempt data is missing 'answer' key
SUBMISSION_MALFORMED_NO_ANSWER = [
    # Pair 0
    {"attempt_1": {"metadata": {"pair_index": 0, "cost": {"total_cost": 0.1}}}}, # Missing answer
    # Pair 1
    {"attempt_1": {"answer": [[2, 2]], "metadata": {"pair_index": 1, "cost": {"total_cost": 0.1}}}}
]

# --- Pytest Fixture ---

@pytest.fixture
def arc_scorer_fixture(tmp_path):
    task_dir = tmp_path / "tasks"
    submission_dir = tmp_path / "submissions"
    task_dir.mkdir()
    submission_dir.mkdir()

    # Create the solution file
    solution_file = task_dir / "test_task.json"
    create_mock_json(solution_file, SOLUTION_DATA)

    # Create dummy submission files (will be overwritten by tests)
    # This helps instantiate ARCScorer, though score_task takes the direct path
    submission_file = submission_dir / "test_task.json"
    create_mock_json(submission_file, {})

    scorer = ARCScorer(str(task_dir), str(submission_dir))
    return scorer, submission_dir # Return scorer and submission dir path


# --- Test Functions ---

def run_test_scenario(arc_scorer_fixture, submission_data, expected_score, expected_cost, expected_attempts):
    scorer, submission_dir = arc_scorer_fixture
    task_id = "test_task"
    submission_file = submission_dir / f"{task_id}.json"
    create_mock_json(submission_file, submission_data)

    result = scorer.score_task(task_id, submission_file)

    assert result["score"] == pytest.approx(expected_score)
    assert result["cost"] == pytest.approx(expected_cost)
    assert result["attempts"] == expected_attempts



def test_perfect_match(arc_scorer_fixture):
    run_test_scenario(arc_scorer_fixture, SUBMISSION_PERFECT, 1.0, 0.3, 3)

def test_no_match(arc_scorer_fixture):
    run_test_scenario(arc_scorer_fixture, SUBMISSION_NO_MATCH, 0.0, 0.3, 3)

def test_partial_match(arc_scorer_fixture):
    # Only Pair 1 is correct (index 1) out of 3 pairs
    run_test_scenario(arc_scorer_fixture, SUBMISSION_PARTIAL, 1.0/3.0, 0.3, 3)

def test_multiple_attempts_one_correct(arc_scorer_fixture):
    # Only Pair 0 is correct (index 0) out of 3 pairs, 2 attempts for pair 0
    # Rerunning calculation:
    # Pair 0: attempt_1 cost 0.1, attempt_2 cost 0.15. Total attempts = 2. Total cost = 0.25
    # Pair 1: attempt_1 cost 0.1. Total attempts = 1. Total cost = 0.1
    # Pair 2: attempt_1 cost 0.1. Total attempts = 1. Total cost = 0.1
    # Total attempts = 2 + 1 + 1 = 4
    # Total cost = 0.25 + 0.1 + 0.1 = 0.45
    # Re-running test call:
    run_test_scenario(arc_scorer_fixture, SUBMISSION_MULTI_ATTEMPT, 1.0/3.0, 0.45, 4)


def test_incorrect_dimensions(arc_scorer_fixture):
    # Pairs 1 and 2 correct
    run_test_scenario(arc_scorer_fixture, SUBMISSION_WRONG_DIM, 2.0/3.0, 0.3, 3)

def test_different_pixels(arc_scorer_fixture):
    # Pairs 1 and 2 correct
    run_test_scenario(arc_scorer_fixture, SUBMISSION_DIFF_PIXELS, 2.0/3.0, 0.3, 3)

def test_none_submission(arc_scorer_fixture):
    # Pairs 1 and 2 correct
    # Let's adjust expected cost and attempts based on scoring.py logic:
    # Pair 0: 1 attempt (None), cost 0.0 (assuming metadata exists but cost is 0 or missing)
    # However, the test data HAS no metadata for the None attempt.
    # The scoring code calculates costs *after* finding pair_index.
    # Let's re-evaluate cost calculation in scoring.py lines 168-174.
    # Cost is summed for *all* attempts where attempt_data is not None and has metadata/cost.
    # In SUBMISSION_NONE:
    # Pair 0: attempt_1 is None. Cost contribution = 0. num_attempts = 1.
    # Pair 1: attempt_1 cost 0.1. Cost contribution = 0.1. num_attempts = 1.
    # Pair 2: attempt_1 cost 0.1. Cost contribution = 0.1. num_attempts = 1.
    # Total cost = 0.1 + 0.1 = 0.2.
    # Total attempts = 1 + 1 + 1 = 3. (num_attempts += len(pair_attempts) on line 167)
    run_test_scenario(arc_scorer_fixture, SUBMISSION_NONE, 2.0/3.0, 0.2, 3) # Expected attempts = 3


def test_empty_list_submission(arc_scorer_fixture):
     # Pairs 1 and 2 correct
    run_test_scenario(arc_scorer_fixture, SUBMISSION_EMPTY_LIST, 2.0/3.0, 0.3, 3)

def test_pair_index_metadata(arc_scorer_fixture):
     # Only Pair 1 is correct (index 1) out of 3 pairs, submitted out of order
    run_test_scenario(arc_scorer_fixture, SUBMISSION_PAIR_INDEX_META, 1.0/3.0, 0.3, 3)

# --- Error Handling Test Functions ---

def run_error_test_scenario(arc_scorer_fixture, submission_data, expected_exception):
    scorer, submission_dir = arc_scorer_fixture
    task_id = "test_task"
    submission_file = submission_dir / f"{task_id}.json"
    create_mock_json(submission_file, submission_data)

    with pytest.raises(expected_exception):
        scorer.score_task(task_id, submission_file)

def test_malformed_not_dict(arc_scorer_fixture):
    run_error_test_scenario(arc_scorer_fixture, SUBMISSION_MALFORMED_NOT_DICT, TypeError)

def test_malformed_no_metadata(arc_scorer_fixture):
    run_error_test_scenario(arc_scorer_fixture, SUBMISSION_MALFORMED_NO_METADATA, KeyError)

def test_malformed_no_answer(arc_scorer_fixture):
    run_error_test_scenario(arc_scorer_fixture, SUBMISSION_MALFORMED_NO_ANSWER, KeyError)
