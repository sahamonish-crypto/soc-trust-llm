#!/usr/bin/env python3

from pathlib import Path
from collections import Counter
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone

ROOT = Path(".")
CANON = Path("benchmarks/gate6d/canonical_v1")
COLLECTOR_DIR = Path("benchmarks/gate6d/collector_v1")
OUTPUT_DIR = Path("benchmarks/gate6d/dev_collection_v1")

DEV_INPUTS = CANON / "canonical_dev_model_inputs.jsonl"
DEV_MANIFEST = CANON / "dev_collection_manifest.csv"
VC_SYSTEM_PROMPT_PATH = (
    COLLECTOR_DIR / "vc_self_eval_system_prompt.txt"
)

MODEL = "@cf/nvidia/nemotron-3-120b-a12b"

EXPECTED_DEV_INPUT_SHA = (
    "f861b49f8d829d05aa0c788e59bbb16e377633ddd57e6e45c346d7abc7e5b45b"
)

EXPECTED_DEV_MANIFEST_SHA = (
    "de9bcd31706393abc9c42c249b4bc463e9542a0a34b3705d9aec9acc9ca19626"
)

ALLOWED_LABELS = {
    "ESCALATE",
    "DO_NOT_ESCALATE",
}

SC5_N = 5
SC5_TEMPERATURE = 0.4
MAX_COMPLETION_TOKENS = 512

MAX_TRANSPORT_ATTEMPTS_PER_SESSION = 5
BACKOFF_SECONDS = [2, 4, 8, 16]

DECISION_SUFFIX = (
    "\n\nDECISION\n"
    "Return exactly ESCALATE or DO_NOT_ESCALATE."
)


def utcnow():
    return datetime.now(
        timezone.utc
    ).isoformat()


def sha256_bytes(data):
    return hashlib.sha256(
        data
    ).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def canonical_json(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def append_jsonl(path, obj):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
        newline="\n",
    ) as f:
        f.write(
            canonical_json(obj)
            + "\n"
        )


def load_jsonl(path):
    out = []

    with path.open(
        encoding="utf-8"
    ) as f:
        for line in f:
            line = line.strip()

            if line:
                out.append(
                    json.loads(line)
                )

    return out


def load_terminal_map(path):
    if not path.exists():
        return {}

    return {
        r["item_id"]: r
        for r in load_jsonl(path)
    }


def parse_retry_after(header_text):
    for line in header_text.splitlines():
        if line.lower().startswith(
            "retry-after:"
        ):
            raw = line.split(
                ":",
                1,
            )[1].strip()

            try:
                return float(raw)
            except Exception:
                return None

    return None


def curl_json(
    url,
    headers,
    payload,
    max_time=300,
):
    header_input = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
    )

    payload_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
    )

    response_headers = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
    )

    try:
        for p in [
            header_input.name,
            payload_file.name,
            response_headers.name,
        ]:
            os.chmod(p, 0o600)

        for header in headers:
            header_input.write(
                header + "\n"
            )

        header_input.close()

        json.dump(
            payload,
            payload_file,
            ensure_ascii=False,
        )

        payload_file.close()
        response_headers.close()

        command = [
            "curl",
            "-sS",
            "--connect-timeout",
            "30",
            "--max-time",
            str(max_time),
            "-X",
            "POST",
            "-H",
            f"@{header_input.name}",
            "-D",
            response_headers.name,
            "--data-binary",
            f"@{payload_file.name}",
            url,
            "-w",
            "\n__STATUS__:%{http_code}",
        ]

        started = time.perf_counter()

        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        latency_ms = round(
            (
                time.perf_counter()
                - started
            ) * 1000,
            1,
        )

        text = proc.stdout
        marker = "\n__STATUS__:"

        if marker in text:
            raw, status_text = text.rsplit(
                marker,
                1,
            )

            try:
                status = int(
                    status_text.strip()
                )
            except Exception:
                status = 0
        else:
            raw = text
            status = 0

        try:
            body = json.loads(raw)
        except Exception:
            body = None

        header_text = Path(
            response_headers.name
        ).read_text(
            encoding="utf-8",
            errors="replace",
        )

        return {
            "http_status": status,
            "body": body,
            "raw_body": raw,
            "response_headers": header_text,
            "retry_after": parse_retry_after(
                header_text
            ),
            "latency_ms": latency_ms,
            "transport_error": (
                proc.stderr.strip()
            ),
        }

    finally:
        for p in [
            header_input.name,
            payload_file.name,
            response_headers.name,
        ]:
            try:
                os.remove(p)
            except Exception:
                pass


def provider_has_code(obj, code):
    if isinstance(obj, dict):
        if obj.get("code") == code:
            return True

        return any(
            provider_has_code(v, code)
            for v in obj.values()
        )

    if isinstance(obj, list):
        return any(
            provider_has_code(v, code)
            for v in obj
        )

    return False


def quota_3036(response):
    return provider_has_code(
        response.get("body"),
        3036,
    )


def retryable_transport(response):
    status = response.get(
        "http_status",
        0,
    )

    return (
        status == 0
        or status == 429
        or 500 <= status <= 599
    )


def cloudflare_call(payload):
    account_id = os.getenv(
        "CLOUDFLARE_ACCOUNT_ID"
    )

    api_token = os.getenv(
        "CLOUDFLARE_API_TOKEN"
    )

    if not account_id:
        raise RuntimeError(
            "CLOUDFLARE_ACCOUNT_ID not set."
        )

    if not api_token:
        raise RuntimeError(
            "CLOUDFLARE_API_TOKEN not set."
        )

    return curl_json(
        (
            "https://api.cloudflare.com/client/v4/"
            "accounts/"
            + account_id
            + "/ai/run/"
            + MODEL
        ),
        [
            "Authorization: Bearer "
            + api_token,
            "Content-Type: application/json",
            "User-Agent: soc-trust-llm-research/1.0",
        ],
        payload,
    )


def extract_result(response):
    body = response.get(
        "body"
    ) or {}

    return (
        body.get("result")
        or {}
    )


def extract_choice_outputs(response):
    result = extract_result(
        response
    )

    choices = result.get(
        "choices"
    )

    if not isinstance(
        choices,
        list,
    ):
        return []

    outputs = []

    for choice in choices:
        message = (
            choice.get("message")
            or {}
        )

        outputs.append(
            (
                message.get("content")
                or ""
            ).strip()
        )

    return outputs


def sc5_payload(messages, seed):
    return {
        "messages": messages,
        "max_completion_tokens":
            MAX_COMPLETION_TOKENS,
        "chat_template_kwargs": {
            "enable_thinking": True,
            "low_effort": True,
        },
        "stream": False,
        "n": SC5_N,
        "temperature":
            SC5_TEMPERATURE,
        "seed": seed,
    }


def build_vc_messages(
    original_messages,
    majority,
):
    if len(original_messages) != 2:
        raise RuntimeError(
            "Expected exactly two canonical messages."
        )

    user_content = original_messages[
        1
    ]["content"]

    if not user_content.endswith(
        DECISION_SUFFIX
    ):
        raise RuntimeError(
            "Canonical user message decision suffix mismatch."
        )

    case_content = user_content[
        :-len(DECISION_SUFFIX)
    ]

    system_prompt = (
        VC_SYSTEM_PROMPT_PATH
        .read_text(
            encoding="utf-8"
        )
        .rstrip("\n")
    )

    vc_user = (
        case_content
        + "\n\nFROZEN RECOMMENDATION\n"
        + majority
        + "\n\nCONFIDENCE TASK\n"
        + "Return exactly one integer from 0 to 100."
    )

    return [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": vc_user,
        },
    ]


def vc_payload(
    original_messages,
    majority,
    seed,
):
    return {
        "messages": build_vc_messages(
            original_messages,
            majority,
        ),
        "max_completion_tokens":
            MAX_COMPLETION_TOKENS,
        "chat_template_kwargs": {
            "enable_thinking": True,
            "low_effort": True,
        },
        "stream": False,
        "n": 1,
        "temperature": 0,
        "seed": seed,
    }


def validate_sc5(response):
    body = response.get(
        "body"
    ) or {}

    outputs = extract_choice_outputs(
        response
    )

    if response.get(
        "http_status"
    ) != 200:
        return {
            "valid": False,
            "reason":
                "NON_200_NOT_SEMANTIC",
            "outputs": outputs,
        }

    if body.get(
        "success"
    ) is not True:
        return {
            "valid": False,
            "reason":
                "HTTP200_PROVIDER_FAILURE",
            "outputs": outputs,
        }

    if len(outputs) != SC5_N:
        return {
            "valid": False,
            "reason":
                "CHOICE_COUNT_NOT_5",
            "outputs": outputs,
        }

    if any(
        x not in ALLOWED_LABELS
        for x in outputs
    ):
        return {
            "valid": False,
            "reason":
                "NON_EXACT_LABEL",
            "outputs": outputs,
        }

    counts = Counter(outputs)

    majority, majority_n = max(
        counts.items(),
        key=lambda kv: (
            kv[1],
            kv[0],
        ),
    )

    if majority_n < 3:
        raise RuntimeError(
            "Impossible binary n=5 majority failure."
        )

    return {
        "valid": True,
        "reason": None,
        "outputs": outputs,
        "majority": majority,
        "agreement": (
            majority_n / SC5_N
        ),
        "vote_counts": dict(
            sorted(
                counts.items()
            )
        ),
    }


def validate_vc(response):
    body = response.get(
        "body"
    ) or {}

    outputs = extract_choice_outputs(
        response
    )

    if response.get(
        "http_status"
    ) != 200:
        return {
            "valid": False,
            "reason":
                "NON_200_NOT_SEMANTIC",
            "outputs": outputs,
        }

    if body.get(
        "success"
    ) is not True:
        return {
            "valid": False,
            "reason":
                "HTTP200_PROVIDER_FAILURE",
            "outputs": outputs,
        }

    if len(outputs) != 1:
        return {
            "valid": False,
            "reason":
                "CHOICE_COUNT_NOT_1",
            "outputs": outputs,
        }

    raw = outputs[0]

    if not re.fullmatch(
        r"(?:100|[0-9]{1,2})",
        raw,
    ):
        return {
            "valid": False,
            "reason":
                "NON_INTEGER_0_100",
            "outputs": outputs,
        }

    value = int(raw)

    return {
        "valid": True,
        "reason": None,
        "outputs": outputs,
        "confidence_integer": value,
        "raw_confidence":
            value / 100.0,
    }


def request_with_retry(
    stage,
    item_id,
    payload,
):
    raw_path = (
        OUTPUT_DIR
        / "raw_attempts.jsonl"
    )

    for attempt in range(
        1,
        MAX_TRANSPORT_ATTEMPTS_PER_SESSION
        + 1,
    ):
        started_utc = utcnow()

        response = cloudflare_call(
            payload
        )

        raw_record = {
            "stage": stage,
            "item_id": item_id,
            "attempt_in_session":
                attempt,
            "request_started_utc":
                started_utc,
            "http_status":
                response.get(
                    "http_status"
                ),
            "retry_after":
                response.get(
                    "retry_after"
                ),
            "latency_ms":
                response.get(
                    "latency_ms"
                ),
            "transport_error":
                response.get(
                    "transport_error"
                ),
            "raw_response_sha256":
                sha256_bytes(
                    (
                        response.get(
                            "raw_body"
                        )
                        or ""
                    ).encode(
                        "utf-8"
                    )
                ),
            "raw_body":
                response.get(
                    "raw_body"
                ),
        }

        append_jsonl(
            raw_path,
            raw_record,
        )

        if quota_3036(response):
            append_jsonl(
                OUTPUT_DIR
                / "session_events.jsonl",
                {
                    "event_type":
                        "CLOUDFLARE_DAILY_QUOTA_PAUSE",
                    "stage": stage,
                    "item_id":
                        item_id,
                    "detected_utc":
                        utcnow(),
                    "logical_attempt_consumed":
                        False,
                    "logical_item_resolved":
                        False,
                },
            )

            return (
                "QUOTA_PAUSE",
                response,
            )

        if retryable_transport(
            response
        ):
            if (
                attempt
                == MAX_TRANSPORT_ATTEMPTS_PER_SESSION
            ):
                append_jsonl(
                    OUTPUT_DIR
                    / "session_events.jsonl",
                    {
                        "event_type":
                            "INFRASTRUCTURE_RETRY_LIMIT_PAUSE",
                        "stage":
                            stage,
                        "item_id":
                            item_id,
                        "detected_utc":
                            utcnow(),
                        "logical_item_resolved":
                            False,
                    },
                )

                return (
                    "INFRASTRUCTURE_PAUSE",
                    response,
                )

            retry_after = (
                response.get(
                    "retry_after"
                )
            )

            fallback = (
                BACKOFF_SECONDS[
                    min(
                        attempt - 1,
                        len(
                            BACKOFF_SECONDS
                        ) - 1,
                    )
                ]
            )

            delay = (
                retry_after
                if retry_after is not None
                else fallback
            )

            time.sleep(
                max(
                    0,
                    float(delay),
                )
            )

            continue

        return (
            "RESPONSE",
            response,
        )

    raise RuntimeError(
        "Unreachable retry state."
    )


def preflight():
    required = [
        DEV_INPUTS,
        DEV_MANIFEST,
        VC_SYSTEM_PROMPT_PATH,
    ]

    missing = [
        p for p in required
        if not p.exists()
    ]

    if missing:
        print(
            "PREFLIGHT: FAIL"
        )

        for p in missing:
            print(
                " missing:",
                p,
            )

        return False

    if sha256_file(
        DEV_INPUTS
    ) != EXPECTED_DEV_INPUT_SHA:
        print(
            "PREFLIGHT: FAIL - DEV input SHA mismatch"
        )
        return False

    if sha256_file(
        DEV_MANIFEST
    ) != EXPECTED_DEV_MANIFEST_SHA:
        print(
            "PREFLIGHT: FAIL - DEV manifest SHA mismatch"
        )
        return False

    inputs = load_jsonl(
        DEV_INPUTS
    )

    with DEV_MANIFEST.open(
        newline="",
        encoding="utf-8",
    ) as f:
        manifest = list(
            csv.DictReader(f)
        )

    if len(inputs) != 1222:
        print(
            "PREFLIGHT: FAIL - DEV input count"
        )
        return False

    if len(manifest) != 1222:
        print(
            "PREFLIGHT: FAIL - DEV manifest count"
        )
        return False

    input_ids = [
        x["item_id"]
        for x in inputs
    ]

    manifest_ids = [
        x["item_id"]
        for x in manifest
    ]

    if input_ids != manifest_ids:
        print(
            "PREFLIGHT: FAIL - item order/identity mismatch"
        )
        return False

    if not all(
        x.startswith(
            "G6D-D-"
        )
        for x in input_ids
    ):
        print(
            "PREFLIGHT: FAIL - non-DEV item ID"
        )
        return False

    seeds = [
        int(r["sc5_seed"])
        for r in manifest
    ]

    if len(
        set(seeds)
    ) != 1222:
        print(
            "PREFLIGHT: FAIL - DEV seed collision"
        )
        return False

    folds = Counter(
        int(r["cv_fold"])
        for r in manifest
    )

    # Verify VC transformation for every canonical DEV item.
    for record, row in zip(
        inputs,
        manifest,
    ):
        _ = sc5_payload(
            record["messages"],
            int(
                row["sc5_seed"]
            ),
        )

        vc_messages = build_vc_messages(
            record["messages"],
            "ESCALATE",
        )

        if len(
            vc_messages
        ) != 2:
            print(
                "PREFLIGHT: FAIL - VC message construction"
            )
            return False

    spec = {
        "artifact":
            "GATE6D_DEV_COLLECTION_SPEC_PREVIEW_V1",
        "status":
            "PRE_FREEZE_NETWORK_DISABLED_PREFLIGHT",
        "provider":
            "Cloudflare Workers AI",
        "model":
            MODEL,
        "dev_inputs": {
            "path":
                str(DEV_INPUTS),
            "sha256":
                sha256_file(
                    DEV_INPUTS
                ),
            "items":
                1222,
        },
        "dev_manifest": {
            "path":
                str(DEV_MANIFEST),
            "sha256":
                sha256_file(
                    DEV_MANIFEST
                ),
        },
        "sc5": {
            "n": 5,
            "temperature":
                0.4,
            "max_completion_tokens":
                512,
            "thinking":
                True,
            "low_effort":
                True,
            "stream":
                False,
            "seed":
                "frozen item-specific sc5_seed",
            "valid_output":
                "exact ESCALATE or DO_NOT_ESCALATE for all five choices",
            "canonical_recommendation":
                "strict majority of five valid labels",
            "agreement":
                "majority vote count / 5",
        },
        "vc_self_eval": {
            "n": 1,
            "temperature":
                0,
            "max_completion_tokens":
                512,
            "thinking":
                True,
            "low_effort":
                True,
            "stream":
                False,
            "seed":
                "same frozen item-specific sc5_seed",
            "system_prompt_path":
                str(
                    VC_SYSTEM_PROMPT_PATH
                ),
            "system_prompt_sha256":
                sha256_file(
                    VC_SYSTEM_PROMPT_PATH
                ),
            "valid_output":
                "exact integer 0 through 100",
            "raw_confidence":
                "integer / 100",
            "recommendation_change":
                False,
        },
        "retry_policy": {
            "retryable":
                "transport/status0, HTTP429, HTTP5xx only",
            "http200_malformed":
                "terminal semantic invalid; no regeneration",
            "cloudflare_3036":
                "clean session pause; unresolved item resumes unchanged",
            "max_transport_attempts_per_session":
                MAX_TRANSPORT_ATTEMPTS_PER_SESSION,
            "fallback_backoff_seconds":
                BACKOFF_SECONDS,
        },
        "eval_access": {
            "permitted":
                False,
            "eval_files_loaded":
                0,
            "eval_inference":
                False,
        },
        "fold_counts": {
            str(k): v
            for k, v in sorted(
                folds.items()
            )
        },
    }

    spec_path = (
        COLLECTOR_DIR
        / "GATE6D_DEV_COLLECTION_SPEC_PREVIEW_V1.json"
    )

    spec_path.write_text(
        json.dumps(
            spec,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        "=== GATE 6D DEV COLLECTOR PREFLIGHT ==="
    )
    print(
        "PREFLIGHT: PASS"
    )
    print(
        "DEV inputs: 1222"
    )
    print(
        "DEV input SHA256:",
        sha256_file(
            DEV_INPUTS
        ),
    )
    print(
        "DEV manifest SHA256:",
        sha256_file(
            DEV_MANIFEST
        ),
    )
    print(
        "VC prompt SHA256:",
        sha256_file(
            VC_SYSTEM_PROMPT_PATH
        ),
    )
    print(
        "Collection spec SHA256:",
        sha256_file(
            spec_path
        ),
    )
    print(
        "Fold counts:",
        dict(
            sorted(
                folds.items()
            )
        ),
    )
    print(
        "Unique DEV seeds:",
        len(set(seeds)),
    )
    print(
        "SC5: n=5 temperature=0.4"
    )
    print(
        "VC: n=1 temperature=0"
    )
    print(
        "EVAL files loaded: 0"
    )
    print(
        "Network calls made: 0"
    )

    return True


def collect_dev():
    if os.getenv(
        "GATE6D_ALLOW_DEV_COLLECTION"
    ) != "YES":
        print(
            "COLLECTION BLOCKED: set "
            "GATE6D_ALLOW_DEV_COLLECTION=YES "
            "and use --collect-dev."
        )
        return

    if not preflight():
        print(
            "COLLECTION BLOCKED: preflight failed."
        )
        return

    inputs = load_jsonl(
        DEV_INPUTS
    )

    with DEV_MANIFEST.open(
        newline="",
        encoding="utf-8",
    ) as f:
        manifest = list(
            csv.DictReader(f)
        )

    input_map = {
        x["item_id"]: x
        for x in inputs
    }

    sc5_path = (
        OUTPUT_DIR
        / "sc5_terminal.jsonl"
    )

    vc_path = (
        OUTPUT_DIR
        / "vc_terminal.jsonl"
    )

    sc5_done = load_terminal_map(
        sc5_path
    )

    vc_done = load_terminal_map(
        vc_path
    )

    for position, row in enumerate(
        manifest,
        start=1,
    ):
        item_id = row[
            "item_id"
        ]

        seed = int(
            row[
                "sc5_seed"
            ]
        )

        item = input_map[
            item_id
        ]

        if item_id not in sc5_done:
            status, response = request_with_retry(
                "SC5_MAJORITY",
                item_id,
                sc5_payload(
                    item["messages"],
                    seed,
                ),
            )

            if status != "RESPONSE":
                print(
                    f"SESSION PAUSED at {item_id} "
                    f"during SC5: {status}"
                )
                return

            parsed = validate_sc5(
                response
            )

            result = extract_result(
                response
            )

            terminal = {
                "item_id":
                    item_id,
                "order_position":
                    position,
                "seed":
                    seed,
                "valid":
                    parsed["valid"],
                "invalid_reason":
                    parsed["reason"],
                "outputs":
                    parsed["outputs"],
                "majority":
                    parsed.get(
                        "majority"
                    ),
                "agreement":
                    parsed.get(
                        "agreement"
                    ),
                "vote_counts":
                    parsed.get(
                        "vote_counts"
                    ),
                "http_status":
                    response.get(
                        "http_status"
                    ),
                "cloudflare_success":
                    (
                        response.get(
                            "body"
                        )
                        or {}
                    ).get(
                        "success"
                    ),
                "returned_model":
                    result.get(
                        "model"
                    ),
                "usage":
                    result.get(
                        "usage"
                    ),
                "latency_ms":
                    response.get(
                        "latency_ms"
                    ),
                "raw_response_sha256":
                    sha256_bytes(
                        (
                            response.get(
                                "raw_body"
                            )
                            or ""
                        ).encode(
                            "utf-8"
                        )
                    ),
                "terminal_utc":
                    utcnow(),
            }

            append_jsonl(
                sc5_path,
                terminal,
            )

            sc5_done[
                item_id
            ] = terminal

        sc5_record = sc5_done[
            item_id
        ]

        if not sc5_record[
            "valid"
        ]:
            continue

        if item_id in vc_done:
            continue

        majority = sc5_record[
            "majority"
        ]

        status, response = request_with_retry(
            "VC_SELF_EVAL",
            item_id,
            vc_payload(
                item["messages"],
                majority,
                seed,
            ),
        )

        if status != "RESPONSE":
            print(
                f"SESSION PAUSED at {item_id} "
                f"during VC: {status}"
            )
            return

        parsed = validate_vc(
            response
        )

        result = extract_result(
            response
        )

        terminal = {
            "item_id":
                item_id,
            "order_position":
                position,
            "seed":
                seed,
            "frozen_recommendation":
                majority,
            "valid":
                parsed["valid"],
            "invalid_reason":
                parsed["reason"],
            "output":
                (
                    parsed[
                        "outputs"
                    ][0]
                    if parsed[
                        "outputs"
                    ]
                    else ""
                ),
            "confidence_integer":
                parsed.get(
                    "confidence_integer"
                ),
            "raw_confidence":
                parsed.get(
                    "raw_confidence"
                ),
            "http_status":
                response.get(
                    "http_status"
                ),
            "cloudflare_success":
                (
                    response.get(
                        "body"
                    )
                    or {}
                ).get(
                    "success"
                ),
            "returned_model":
                result.get(
                    "model"
                ),
            "usage":
                result.get(
                    "usage"
                ),
            "latency_ms":
                response.get(
                    "latency_ms"
                ),
            "raw_response_sha256":
                sha256_bytes(
                    (
                        response.get(
                            "raw_body"
                        )
                        or ""
                    ).encode(
                        "utf-8"
                    )
                ),
            "terminal_utc":
                utcnow(),
        }

        append_jsonl(
            vc_path,
            terminal,
        )

        vc_done[
            item_id
        ] = terminal

        print(
            f"{position:04d}/1222 "
            f"{item_id} "
            f"SC5={majority} "
            f"agreement={sc5_record['agreement']} "
            f"VC={'VALID' if terminal['valid'] else 'INVALID'}"
        )

    print(
        "DEV COLLECTION PASS COMPLETE"
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--preflight",
        action="store_true",
    )

    parser.add_argument(
        "--collect-dev",
        action="store_true",
    )

    args = parser.parse_args()

    if args.collect_dev:
        collect_dev()
    else:
        preflight()


if __name__ == "__main__":
    main()
