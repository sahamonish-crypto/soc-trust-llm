#!/usr/bin/env python3

"""
Pre-Gate-7 human-study decision framework V1.

This is a governance/decision scaffold only.
It MUST NOT freeze the final human-study protocol while Gate 6 is open.
"""

from __future__ import annotations

import json
from pathlib import Path


STATUS_PATH = Path(
    "docs/pre_gate7/PRE_GATE7_STATUS_V1.json"
)

ALLOWED_OPEN_STATUSES = {
    "UNRESOLVED",
    "PROVISIONAL",
    "BLOCKED_ON_GATE6",
}

FORBIDDEN_OPEN_STATUSES = {
    "FINAL",
    "FROZEN_FINAL",
    "APPROVED_FOR_RECRUITMENT",
    "APPROVED_FOR_PARTICIPANTS",
}


def assert_pre_gate7_boundary() -> dict:
    status = json.loads(
        STATUS_PATH.read_text(
            encoding="utf-8"
        )
    )

    for key in [
        "gate7_open",
        "gate6_closed",
        "real_participants_allowed",
        "final_calibrated_confidence_allowed",
        "external_test_allowed",
    ]:
        if status.get(key) is not False:
            raise RuntimeError(
                "Pre-Gate-7 boundary violation: "
                + key
            )

    return status


def decision_registry() -> dict:
    assert_pre_gate7_boundary()

    return {
        "artifact":
            "PRE_GATE7_HUMAN_STUDY_DECISION_FRAMEWORK_V1",

        "status":
            "PREPARATION_ONLY",

        "stable_principles": {
            "trust_vs_reliance_distinct":
                True,
            "behavioral_reliance_not_replaced_by_subjective_trust":
                True,
            "trial_level_binary_outcomes_not_aggregated_for_primary_model":
                True,
            "participant_and_item_variability_must_be_modeled":
                True,
            "real_participants_before_gate7":
                False,
        },

        "decisions": {
            "final_condition_structure": {
                "status":
                    "BLOCKED_ON_GATE6",
                "current_placeholder":
                    "SYN_CONDITION_A/B/C",
                "final_value":
                    None,
                "dependency":
                    "Gate 6 PASS/CLOSE and final confidence intervention viability",
            },

            "participant_facing_confidence_format": {
                "status":
                    "BLOCKED_ON_GATE6",
                "current_placeholder":
                    None,
                "final_value":
                    None,
                "dependency":
                    "Gate 6D EVAL safeguard PASS and protocol review",
            },

            "participant_population": {
                "status":
                    "PROVISIONAL",
                "priority":
                    [
                        "SOC/cybersecurity practitioners",
                        "screened advanced cybersecurity participants if practitioner recruitment is infeasible",
                    ],
                "final_value":
                    None,
            },

            "inclusion_exclusion_criteria": {
                "status":
                    "UNRESOLVED",
                "final_value":
                    None,
            },

            "primary_hypotheses_and_contrasts": {
                "status":
                    "UNRESOLVED",
                "final_value":
                    None,
            },

            "sample_size": {
                "status":
                    "UNRESOLVED",
                "final_value":
                    None,
                "required_method":
                    "design-appropriate power analysis, preferably simulation-based for repeated mixed-effects design",
            },

            "trial_count_and_item_sampling": {
                "status":
                    "BLOCKED_ON_GATE6",
                "final_value":
                    None,
                "dependency":
                    "Gate 6 evidence pool and human-study item construction",
            },

            "trust_measure": {
                "status":
                    "UNRESOLVED",
                "final_value":
                    None,
                "note":
                    "Subjective trust must remain distinct from behavioral reliance.",
            },

            "workload_measure": {
                "status":
                    "PROVISIONAL",
                "candidate":
                    "NASA-TLX",
                "final_value":
                    None,
                "unresolved":
                    [
                        "raw vs weighted scoring",
                        "administration timing",
                        "block-level vs session-level administration",
                    ],
            },

            "decision_time_analysis": {
                "status":
                    "UNRESOLVED",
                "final_value":
                    None,
                "note":
                    "Distribution/transform/model family must be chosen from final design and observed diagnostics, not precommitted blindly.",
            },

            "binary_outcome_model_family": {
                "status":
                    "PROVISIONAL",
                "candidate":
                    "logit mixed-effects model",
                "random_effects_candidates":
                    [
                        "participant",
                        "item",
                    ],
                "final_value":
                    None,
            },

            "continuous_outcome_model_family": {
                "status":
                    "PROVISIONAL",
                "candidate":
                    "mixed-effects model appropriate to final scale/distribution",
                "final_value":
                    None,
            },

            "randomization_and_counterbalancing": {
                "status":
                    "UNRESOLVED",
                "current_infrastructure_only":
                    True,
                "final_value":
                    None,
            },

            "pilot_plan": {
                "status":
                    "UNRESOLVED",
                "final_value":
                    None,
            },

            "recruitment_and_compensation": {
                "status":
                    "UNRESOLVED",
                "final_value":
                    None,
            },
        },

        "forbidden_before_gate7": [
            "real participant recruitment",
            "real participant data collection",
            "final participant-facing calibrated confidence",
            "final sample size freeze without justified power analysis",
            "opening Gate 7 automatically after Gate 6 EVAL",
            "using External-TEST to design the human study",
        ],

        "gate7_opened":
            False,
    }


def validate_registry(obj: dict) -> None:
    assert_pre_gate7_boundary()

    if obj.get("status") != "PREPARATION_ONLY":
        raise RuntimeError(
            "Framework is not preparation-only."
        )

    if obj.get("gate7_opened") is not False:
        raise RuntimeError(
            "Gate 7 must remain closed."
        )

    decisions = obj.get(
        "decisions",
        {}
    )

    if not decisions:
        raise RuntimeError(
            "Decision registry is empty."
        )

    for name,decision in decisions.items():
        status = decision.get(
            "status"
        )

        if status in FORBIDDEN_OPEN_STATUSES:
            raise RuntimeError(
                "Forbidden final decision while Gate 6 open: "
                + name
            )

        if status not in ALLOWED_OPEN_STATUSES:
            raise RuntimeError(
                "Unexpected decision status: "
                + name
                + "="
                + repr(status)
            )

        if decision.get(
            "final_value"
        ) is not None:
            raise RuntimeError(
                "Final value populated before Gate 7: "
                + name
            )


def synthetic_self_test() -> dict:
    registry = decision_registry()

    validate_registry(
        registry
    )

    fail_closed = 0

    cases = []

    x = json.loads(
        json.dumps(registry)
    )
    x["decisions"][
        "sample_size"
    ]["status"] = "FINAL"
    cases.append(x)

    x = json.loads(
        json.dumps(registry)
    )
    x["decisions"][
        "sample_size"
    ]["final_value"] = 120
    cases.append(x)

    x = json.loads(
        json.dumps(registry)
    )
    x["gate7_opened"] = True
    cases.append(x)

    x = json.loads(
        json.dumps(registry)
    )
    x["status"] = "FINAL_PROTOCOL"
    cases.append(x)

    for candidate in cases:
        try:
            validate_registry(
                candidate
            )
        except Exception:
            fail_closed += 1
        else:
            raise RuntimeError(
                "Fail-closed decision test passed unexpectedly."
            )

    return {
        "artifact":
            "PRE_GATE7_HUMAN_STUDY_DECISION_FRAMEWORK_SELF_TEST_V1",
        "status":
            "PASS",
        "decision_axes":
            len(
                registry[
                    "decisions"
                ]
            ),
        "fail_closed_tests":
            fail_closed,
        "final_values_populated":
            0,
        "real_participants_used":
            False,
        "final_calibrated_confidence_used":
            False,
        "external_test_accessed":
            False,
        "gate7_opened":
            False,
    }


if __name__ == "__main__":
    result = synthetic_self_test()

    for key,value in result.items():
        print(f"{key}: {value}")
