from types import SimpleNamespace

import numpy as np

from driver_epic_seven.vision import validated_template_match


def test_filtered_variant_with_valid_pixels_wins_over_bad_higher_correlation():
    template = np.full((3, 3, 3), 150, dtype=np.uint8)
    frame = np.zeros((4, 8, 3), dtype=np.uint8)
    frame[:3, 4:7] = template
    bad = SimpleNamespace(box=[0, 0, 3, 3], score=.99)
    good = SimpleNamespace(box=[4, 0, 3, 3], score=.94)
    result = SimpleNamespace(hit=True, box=bad.box, best_result=bad, filtered_results=[bad, good])
    matched = validated_template_match(frame, [template], result, 10)
    assert matched == {"hit": True, "box": good.box, "score": .94, "pixel_mae": 0}


def test_unfiltered_candidate_cannot_rescue_a_failed_recognition():
    template = np.full((3, 3, 3), 150, dtype=np.uint8)
    candidate = SimpleNamespace(box=[0, 0, 3, 3], score=.6)
    result = SimpleNamespace(hit=False, box=None, best_result=candidate,
                             filtered_results=[], all_results=[candidate])
    assert not validated_template_match(template, [template], result, 10)["hit"]
    result.hit, result.box = True, candidate.box
    assert not validated_template_match(template, [template], result, 10)["hit"]


def test_single_result_adapter_still_rejects_dimmed_pixels():
    template = np.full((3, 3, 3), 200, dtype=np.uint8)
    candidate = SimpleNamespace(box=[0, 0, 3, 3], score=.99)
    result = SimpleNamespace(hit=True, box=candidate.box, best_result=candidate)
    assert validated_template_match(template, [template], result, 10)["hit"]
    assert not validated_template_match(template // 2, [template], result, 10)["hit"]
