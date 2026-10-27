#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# FROZEN ARTIFACTS
# ============================================================

INPUTS = Path(
    "benchmarks/gate6c/canonical_model_inputs.jsonl"
)

META = Path(
    "benchmarks/gate6c/item_metadata.csv"
)

CANDIDATES_FILE = Path(
    "benchmarks/gate6c/zero_budget_candidate_set_v2.json"
)

POLICY_FILE = Path(
    "benchmarks/gate6c/full_benchmark_execution_policy_v1.json"
)

BASE = Path("benchmarks/gate6c/full")
ORDERS = BASE / "orders"
RAW = BASE / "raw"
STATE = BASE / "state"
RECOVERY = BASE / "recovery"
AUDIT = BASE / "audit"

EXPECTED_INPUT_SHA = (
    "a4cb01041ed16de2eae6fce2abb803631"
    "7fc068653b8abdd0812d6424b3a4915"
)

VALID_LABELS = {
    "ESCALATE",
    "DO_NOT_ESCALATE",
}

TRANSIENT_STATUSES = {
    0, 408, 429, 498,
    500, 502, 503, 504,
}

STOP_STATUSES = {
    400, 401, 403, 404,
}

CANDIDATES = {
    "ZB1": {
        "provider": "gemini",
        "model": "gemini-3.6-flash",
        "success_delay": 0,
        "retry_delays": [15, 45],
    },
    "ZB2": {
        "provider": "groq",
        "model": "openai/gpt-oss-120b",
        "success_delay": 10,
        "retry_delays": [10, 30],
    },
    "ZB3": {
        "provider": "groq",
        "model": "qwen/qwen3.8-27b",
        "success_delay": 65,
        "retry_delays": [65, 130],
    },
}

ORDER_SALT = "GATE6C_FULL_BENCHMARK_V1"


# ============================================================
# GENERIC HELPERS
# ============================================================

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


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


def utcnow():
    return datetime.now(
        timezone.utc
    ).isoformat()


def ensure_dirs():
    for p in [
        ORDERS,
        RAW,
        STATE,
        RECOVERY,
        AUDIT,
    ]:
        p.mkdir(
            parents=True,
            exist_ok=True,
        )


def committed_and_clean(path):
    tracked = subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            str(path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0

    clean = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            "HEAD",
            "--",
            str(path),
        ]
    ).returncode == 0

    return tracked and clean


def enforce_execution_integrity():

    required = [
        INPUTS,
        CANDIDATES_FILE,
        POLICY_FILE,
        Path(__file__),
        ORDERS / "logical_run_1_order.txt",
        ORDERS / "logical_run_2_order.txt",
        ORDERS / "logical_run_3_order.txt",
    ]

    bad = [
        str(path)
        for path in required
        if not committed_and_clean(path)
    ]

    if bad:
        raise RuntimeError(
            "Execution blocked: frozen runner/artifacts "
            "must be committed and clean before inference. "
            "Problem files: "
            + ", ".join(bad)
        )


# ============================================================
# LOAD MODEL-VISIBLE INPUTS ONLY
# ============================================================

def load_inputs():

    if sha256_file(INPUTS) != EXPECTED_INPUT_SHA:
        raise RuntimeError(
            "Frozen canonical input SHA256 mismatch."
        )

    result = {}

    with INPUTS.open(
        encoding="utf-8"
    ) as f:

        for line in f:

            if not line.strip():
                continue

            obj = json.loads(line)

            item_id = obj["item_id"]

            if item_id in result:
                raise RuntimeError(
                    f"Duplicate item_id: {item_id}"
                )

            result[item_id] = obj

    if len(result) != 133:
        raise RuntimeError(
            f"Expected 133 items, found {len(result)}"
        )

    return result


# ============================================================
# DETERMINISTIC THREE-RUN ORDERS
# ============================================================

def order_digest(run_number, item_id):

    text = (
        f"{ORDER_SALT}"
        f"|RUN={run_number}"
        f"|ITEM={item_id}"
    )

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def compute_order(item_ids, run_number):

    return sorted(
        item_ids,
        key=lambda item_id: (
            order_digest(
                run_number,
                item_id,
            ),
            item_id,
        ),
    )


def ensure_orders(item_ids):

    order_info = {}

    for run_number in [1, 2, 3]:

        expected = compute_order(
            item_ids,
            run_number,
        )

        path = (
            ORDERS
            / f"logical_run_{run_number}_order.txt"
        )

        content = (
            "\n".join(expected)
            + "\n"
        )

        if path.exists():

            current = path.read_text(
                encoding="utf-8"
            )

            if current != content:
                raise RuntimeError(
                    f"Existing order file mismatch: {path}"
                )

        else:
            path.write_text(
                content,
                encoding="utf-8",
            )

        order_info[run_number] = {
            "path": path,
            "items": expected,
            "sha256": sha256_file(path),
        }

    return order_info


# ============================================================
# ATTEMPT / LOGICAL RESULT FILES
# ============================================================

def attempt_path(candidate, run_number):

    return (
        RAW
        / f"{candidate}_run{run_number}_attempts.jsonl"
    )


def logical_path(candidate, run_number):

    return (
        RAW
        / f"{candidate}_run{run_number}_logical.jsonl"
    )


def recovery_path(candidate, run_number):

    return (
        RECOVERY
        / f"{candidate}_run{run_number}_queue.jsonl"
    )


def load_jsonl(path):

    if not path.exists():
        return []

    rows = []

    with path.open(
        encoding="utf-8"
    ) as f:

        for line in f:

            if line.strip():
                rows.append(
                    json.loads(line)
                )

    return rows


def append_jsonl(path, obj):

    with path.open(
        "a",
        encoding="utf-8",
    ) as f:

        f.write(
            canonical_json(obj)
            + "\n"
        )

        f.flush()

        os.fsync(
            f.fileno()
        )


def resolved_items(candidate, run_number):

    rows = load_jsonl(
        logical_path(
            candidate,
            run_number,
        )
    )

    result = {}

    for row in rows:
        result[
            row["item_id"]
        ] = row

    return result


TERMINAL_LOGICAL_STATUSES = {
    "VALID_HTTP200",
    "INVALID_HTTP200",
    "NONTRANSIENT_FAILURE",
    "OPERATIONAL_MISSING",
}


def latest_logical_record(
    candidate,
    run_number,
    item_id,
):

    rows = load_jsonl(
        logical_path(
            candidate,
            run_number,
        )
    )

    matches = [
        row
        for row in rows
        if row.get("item_id") == item_id
    ]

    return (
        matches[-1]
        if matches
        else None
    )


def append_logical_safely(
    candidate,
    run_number,
    record,
):

    latest = latest_logical_record(
        candidate,
        run_number,
        record["item_id"],
    )

    if latest:

        if latest.get("status") in TERMINAL_LOGICAL_STATUSES:
            return latest

        if (
            latest.get("status")
            == record.get("status")
            and latest.get("phase")
            == record.get("phase")
        ):
            return latest

    append_jsonl(
        logical_path(
            candidate,
            run_number,
        ),
        record,
    )

    return record


def ensure_recovery_queue_record(
    candidate,
    run_number,
    record,
):

    path = recovery_path(
        candidate,
        run_number,
    )

    existing = load_jsonl(path)

    already_present = any(
        row.get("item_id")
        == record["item_id"]
        for row in existing
    )

    if not already_present:
        append_jsonl(
            path,
            record,
        )


def finalize_transient_exhaustion(
    candidate_id,
    run_number,
    order_position,
    item_id,
    model,
    phase,
):

    if phase == "initial":

        queue_record = {
            "candidate_id":
                candidate_id,
            "requested_model":
                model,
            "item_id":
                item_id,
            "logical_run":
                run_number,
            "order_position":
                order_position,
            "queued_utc":
                utcnow(),
        }

        ensure_recovery_queue_record(
            candidate_id,
            run_number,
            queue_record,
        )

        logical_record = {
            **queue_record,
            "status":
                "RECOVERY_QUEUED",
            "completed_utc":
                utcnow(),
            "phase":
                "initial",
        }

        append_logical_safely(
            candidate_id,
            run_number,
            logical_record,
        )

        return {
            "status":
                "RECOVERY_QUEUED",
            "resolved":
                True,
        }

    logical_record = {
        "candidate_id":
            candidate_id,
        "requested_model":
            model,
        "item_id":
            item_id,
        "logical_run":
            run_number,
        "order_position":
            order_position,
        "status":
            "OPERATIONAL_MISSING",
        "completed_utc":
            utcnow(),
        "phase":
            "recovery",
    }

    append_logical_safely(
        candidate_id,
        run_number,
        logical_record,
    )

    return {
        "status":
            "OPERATIONAL_MISSING",
        "resolved":
            True,
    }


def existing_attempts_for(
    candidate,
    run_number,
    item_id,
    phase,
):

    rows = load_jsonl(
        attempt_path(
            candidate,
            run_number,
        )
    )

    return [
        r
        for r in rows
        if (
            r["item_id"] == item_id
            and r["phase"] == phase
        )
    ]


# ============================================================
# HTTP REQUEST
# ============================================================

def parse_retry_after(header_text):

    for line in header_text.splitlines():

        if not line.lower().startswith(
            "retry-after:"
        ):
            continue

        value = line.split(
            ":",
            1,
        )[1].strip()

        try:
            return float(value)
        except Exception:
            return None

    return None


def curl_json(
    url,
    headers,
    payload,
    max_time=300,
):

    header_input = (
        tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
        )
    )

    payload_file = (
        tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
        )
    )

    response_headers = (
        tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
        )
    )

    try:

        for p in [
            header_input.name,
            payload_file.name,
            response_headers.name,
        ]:
            os.chmod(
                p,
                0o600,
            )

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
            )
            * 1000,
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
            body = json.loads(
                raw
            )
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
            "response_headers":
                header_text,
            "retry_after":
                parse_retry_after(
                    header_text
                ),
            "latency_ms":
                latency_ms,
            "transport_error":
                proc.stderr.strip(),
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


# ============================================================
# PROVIDER CALLS
# ============================================================

def call_groq(model, messages):

    if not os.getenv(
        "GROQ_API_KEY"
    ):
        raise RuntimeError(
            "GROQ_API_KEY not set."
        )

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "reasoning_effort": "low",
        "include_reasoning": False,
        "max_completion_tokens": 512,
        "stream": False,
    }

    response = curl_json(
        "https://api.groq.com/openai/v1/chat/completions",
        [
            "Authorization: Bearer "
            + os.environ[
                "GROQ_API_KEY"
            ],
            "Content-Type: application/json",
            "User-Agent: soc-trust-llm-research/1.0",
        ],
        payload,
    )

    body = (
        response["body"]
        or {}
    )

    output = ""
    finish = None

    try:
        message = (
            body["choices"][0]
            ["message"]
        )

        output = (
            message.get(
                "content"
            )
            or ""
        ).strip()

        finish = (
            body["choices"][0]
            .get(
                "finish_reason"
            )
        )

    except Exception:
        pass

    return {
        **response,
        "output": output,
        "finish_reason": finish,
        "returned_model":
            body.get("model"),
        "usage":
            body.get("usage"),
        "provider_error":
            body.get("error"),
    }


def call_gemini(model, messages):

    if not os.getenv(
        "GEMINI_API_KEY"
    ):
        raise RuntimeError(
            "GEMINI_API_KEY not set."
        )

    system_text = next(
        m["content"]
        for m in messages
        if m["role"] == "system"
    )

    user_text = next(
        m["content"]
        for m in messages
        if m["role"] == "user"
    )

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text":
                        system_text
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text":
                            user_text
                    }
                ],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 512,
            "thinkingConfig": {
                "thinkingLevel":
                    "low"
            },
        },
    }

    response = curl_json(
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        + model
        + ":generateContent",
        [
            "x-goog-api-key: "
            + os.environ[
                "GEMINI_API_KEY"
            ],
            "Content-Type: application/json",
            "User-Agent: soc-trust-llm-research/1.0",
        ],
        payload,
    )

    body = (
        response["body"]
        or {}
    )

    output_parts = []
    finish = None

    try:

        candidate = (
            body["candidates"][0]
        )

        finish = candidate.get(
            "finishReason"
        )

        for part in (
            candidate
            .get("content", {})
            .get("parts", [])
        ):

            if part.get(
                "thought"
            ) is True:
                continue

            if part.get(
                "text"
            ):
                output_parts.append(
                    part["text"]
                )

    except Exception:
        pass

    return {
        **response,
        "output":
            "".join(
                output_parts
            ).strip(),
        "finish_reason":
            finish,
        "returned_model":
            body.get(
                "modelVersion"
            ),
        "usage":
            body.get(
                "usageMetadata"
            ),
        "provider_error":
            body.get("error"),
    }


# ============================================================
# ONE LOGICAL REQUEST
# ============================================================

def execute_logical_request(
    candidate_id,
    run_number,
    order_position,
    item,
    phase,
):

    config = CANDIDATES[
        candidate_id
    ]

    model = config["model"]

    latest = latest_logical_record(
        candidate_id,
        run_number,
        item["item_id"],
    )

    if latest:

        if latest.get("status") in TERMINAL_LOGICAL_STATUSES:

            return {
                "status":
                    latest["status"],
                "resolved":
                    True,
            }

        if (
            phase == "initial"
            and latest.get("status")
            == "RECOVERY_QUEUED"
        ):

            return {
                "status":
                    "RECOVERY_QUEUED",
                "resolved":
                    True,
            }

    prior = existing_attempts_for(
        candidate_id,
        run_number,
        item["item_id"],
        phase,
    )

    # --------------------------------------------------------
    # Crash reconciliation:
    # If HTTP 200 was already persisted as an attempt but the
    # process stopped before the logical record was written,
    # reconstruct the logical result WITHOUT another API call.
    # --------------------------------------------------------

    prior_http200 = [
        row
        for row in prior
        if row.get("http_status") == 200
    ]

    if prior_http200:

        row = prior_http200[0]

        valid = bool(
            row.get("valid_exact_label")
        )

        logical_record = {
            "candidate_id":
                candidate_id,
            "requested_model":
                model,
            "returned_model":
                row.get("returned_model"),
            "model_id_mismatch":
                row.get("model_id_mismatch"),
            "item_id":
                item["item_id"],
            "logical_run":
                run_number,
            "order_position":
                order_position,
            "status":
                (
                    "VALID_HTTP200"
                    if valid
                    else "INVALID_HTTP200"
                ),
            "valid_exact_label":
                valid,
            "output":
                row.get("output", ""),
            "output_sha256":
                row.get("output_sha256"),
            "completed_utc":
                utcnow(),
            "phase":
                phase,
            "reconstructed_from_persisted_attempt":
                True,
        }

        append_logical_safely(
            candidate_id,
            run_number,
            logical_record,
        )

        return {
            "status":
                logical_record["status"],
            "resolved":
                True,
        }

    # Persisted non-transient stop status must not be silently
    # bypassed on resume.
    for row in prior:

        status = row.get(
            "http_status"
        )

        if status in STOP_STATUSES:

            return {
                "status":
                    "STOP_PROVIDER_SESSION",
                "resolved":
                    False,
            }

        if (
            status not in TRANSIENT_STATUSES
            and status != 200
        ):

            logical_record = {
                "candidate_id":
                    candidate_id,
                "requested_model":
                    model,
                "item_id":
                    item["item_id"],
                "logical_run":
                    run_number,
                "order_position":
                    order_position,
                "status":
                    "NONTRANSIENT_FAILURE",
                "completed_utc":
                    utcnow(),
                "phase":
                    phase,
                "reconstructed_from_persisted_attempt":
                    True,
            }

            append_logical_safely(
                candidate_id,
                run_number,
                logical_record,
            )

            return {
                "status":
                    "NONTRANSIENT_FAILURE",
                "resolved":
                    True,
            }

    if len(prior) >= 3:

        return finalize_transient_exhaustion(
            candidate_id,
            run_number,
            order_position,
            item["item_id"],
            model,
            phase,
        )

    start_attempt = (
        len(prior)
        + 1
    )

    for attempt_number in range(
        start_attempt,
        4,
    ):

        if attempt_number > 1:

            frozen_delay = (
                config[
                    "retry_delays"
                ][
                    attempt_number - 2
                ]
            )

            previous = prior[-1] if prior else None

            retry_after = None

            if previous:
                retry_after = (
                    previous.get(
                        "retry_after"
                    )
                )

            wait_seconds = (
                max(
                    frozen_delay,
                    retry_after or 0,
                )
            )

            print(
                f"  retry wait:"
                f" {wait_seconds}s"
            )

            time.sleep(
                wait_seconds
            )

        started_utc = utcnow()

        if config[
            "provider"
        ] == "gemini":

            response = call_gemini(
                model,
                item["messages"],
            )

        else:

            response = call_groq(
                model,
                item["messages"],
            )

        output = (
            response.get(
                "output"
            )
            or ""
        ).strip()

        valid = (
            output
            in VALID_LABELS
        )

        returned_model = (
            response.get(
                "returned_model"
            )
        )

        model_id_mismatch = (
            returned_model
            not in {
                None,
                "",
                model,
            }
        )

        attempt_record = {
            "candidate_id":
                candidate_id,
            "requested_model":
                model,
            "returned_model":
                returned_model,
            "model_id_mismatch":
                model_id_mismatch,
            "item_id":
                item["item_id"],
            "logical_run":
                run_number,
            "order_position":
                order_position,
            "phase":
                phase,
            "attempt_number":
                attempt_number,
            "started_utc":
                started_utc,
            "http_status":
                response.get(
                    "http_status"
                ),
            "finish_reason":
                response.get(
                    "finish_reason"
                ),
            "latency_ms":
                response.get(
                    "latency_ms"
                ),
            "usage":
                response.get(
                    "usage"
                ),
            "output":
                output,
            "valid_exact_label":
                valid,
            "output_sha256":
                sha256_bytes(
                    output.encode(
                        "utf-8"
                    )
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
            "provider_error":
                response.get(
                    "provider_error"
                ),
            "transport_error":
                response.get(
                    "transport_error"
                ),
            "retry_after":
                response.get(
                    "retry_after"
                ),
        }

        append_jsonl(
            attempt_path(
                candidate_id,
                run_number,
            ),
            attempt_record,
        )

        status = (
            response.get(
                "http_status"
            )
        )

        print(
            f"  attempt {attempt_number}"
            f" | HTTP {status}"
            f" | valid={valid}"
            f" | latency_ms="
            f"{response.get('latency_ms')}"
        )

        # --------------------------------------------
        # HTTP 200 is final regardless of correctness.
        # --------------------------------------------

        if status == 200:

            final_status = (
                "VALID_HTTP200"
                if valid
                else "INVALID_HTTP200"
            )

            logical_record = {
                "candidate_id":
                    candidate_id,
                "requested_model":
                    model,
                "returned_model":
                    returned_model,
                "model_id_mismatch":
                    model_id_mismatch,
                "item_id":
                    item["item_id"],
                "logical_run":
                    run_number,
                "order_position":
                    order_position,
                "status":
                    final_status,
                "valid_exact_label":
                    valid,
                "output":
                    output,
                "output_sha256":
                    attempt_record[
                        "output_sha256"
                    ],
                "completed_utc":
                    utcnow(),
                "phase":
                    phase,
            }

            append_logical_safely(
                candidate_id,
                run_number,
                logical_record,
            )

            if config[
                "success_delay"
            ] > 0:

                time.sleep(
                    config[
                        "success_delay"
                    ]
                )

            return {
                "status":
                    final_status,
                "resolved":
                    True,
            }

        # --------------------------------------------
        # Stop-session statuses
        # --------------------------------------------

        if status in STOP_STATUSES:

            return {
                "status":
                    "STOP_PROVIDER_SESSION",
                "resolved":
                    False,
            }

        # --------------------------------------------
        # Non-transient unexpected status
        # --------------------------------------------

        if status not in TRANSIENT_STATUSES:

            logical_record = {
                "candidate_id":
                    candidate_id,
                "requested_model":
                    model,
                "item_id":
                    item["item_id"],
                "logical_run":
                    run_number,
                "order_position":
                    order_position,
                "status":
                    "NONTRANSIENT_FAILURE",
                "completed_utc":
                    utcnow(),
                "phase":
                    phase,
            }

            append_jsonl(
                logical_path(
                    candidate_id,
                    run_number,
                ),
                logical_record,
            )

            return {
                "status":
                    "NONTRANSIENT_FAILURE",
                "resolved":
                    True,
            }

        prior.append(
            attempt_record
        )

    return finalize_transient_exhaustion(
        candidate_id,
        run_number,
        order_position,
        item["item_id"],
        model,
        phase,
    )


# ============================================================
# AUDIT
# ============================================================

def audit():

    ensure_dirs()

    inputs = load_inputs()

    order_info = ensure_orders(
        list(
            inputs.keys()
        )
    )

    print("=" * 78)
    print("GATE 6C FULL RUNNER AUDIT")
    print("=" * 78)

    print()
    print("FROZEN ARTIFACT CHECK")

    print(
        "  canonical inputs SHA256:",
        sha256_file(INPUTS),
    )

    print(
        "  canonical inputs:",
        "PASS",
    )

    for path in [
        INPUTS,
        CANDIDATES_FILE,
        POLICY_FILE,
    ]:

        print(
            " ",
            path,
            ":",
            "PASS"
            if committed_and_clean(
                path
            )
            else "FAIL",
        )

        if not committed_and_clean(
            path
        ):
            raise RuntimeError(
                f"Frozen artifact not committed/clean: {path}"
            )

    candidate_data = json.loads(
        CANDIDATES_FILE.read_text(
            encoding="utf-8"
        )
    )

    realized = {
        c["candidate_id"]:
            c["model"]
        for c in candidate_data[
            "candidates"
        ]
    }

    expected = {
        k: v["model"]
        for k, v in CANDIDATES.items()
    }

    candidate_pass = (
        realized == expected
    )

    print()
    print("CANDIDATE CONFIG AUDIT")

    for cid in [
        "ZB1",
        "ZB2",
        "ZB3",
    ]:

        print(
            f"  {cid}:",
            realized.get(cid),
            "|",
            "PASS"
            if (
                realized.get(cid)
                == expected[cid]
            )
            else "FAIL",
        )

    if not candidate_pass:
        raise RuntimeError(
            "Frozen candidate set mismatch."
        )

    print()
    print("DETERMINISTIC ORDER AUDIT")

    all_sets_ok = True

    for run_number in [1, 2, 3]:

        info = order_info[
            run_number
        ]

        order = info["items"]

        permutation_ok = (
            len(order) == 133
            and len(set(order)) == 133
            and set(order)
            == set(inputs)
        )

        all_sets_ok = (
            all_sets_ok
            and permutation_ok
        )

        print(
            f"  run {run_number}:"
            f" 133 unique items="
            f"{'PASS' if permutation_ok else 'FAIL'}"
        )

        print(
            f"    SHA256:"
            f" {info['sha256']}"
        )

        print(
            "    first 3:",
            ", ".join(
                order[:3]
            )
        )

        print(
            "    last 3:",
            ", ".join(
                order[-3:]
            )
        )

    distinct_orders = (
        len({
            tuple(
                order_info[r][
                    "items"
                ]
            )
            for r in [1, 2, 3]
        })
        == 3
    )

    print(
        "  three orders distinct:",
        "PASS"
        if distinct_orders
        else "FAIL",
    )

    if not (
        all_sets_ok
        and distinct_orders
    ):
        raise RuntimeError(
            "Deterministic order audit failed."
        )

    # --------------------------------------------------------
    # Static isolation check:
    # runner itself must not contain the hidden GT filename.
    # --------------------------------------------------------

    script_text = Path(
        __file__
    ).read_text(
        encoding="utf-8"
    ).lower()

    forbidden_token = "_".join([
        "hidden",
        "ground",
        "truth",
    ])

    forbidden_reference = (
        forbidden_token
        in script_text
    )

    print()
    print("GROUND-TRUTH ISOLATION AUDIT")

    print(
        "  hidden-GT filename referenced"
        " by runner:",
        "FAIL"
        if forbidden_reference
        else "PASS",
    )

    print(
        "  model-visible inputs loaded:"
        " YES"
    )

    print(
        "  item metadata required"
        " during execution: NO"
    )

    print(
        "  External-TEST source paths"
        " referenced: NO"
    )

    if forbidden_reference:
        raise RuntimeError(
            "Runner contains hidden GT filename."
        )

    print()
    print("EXECUTION SAFETY AUDIT")

    print(
        "  default mode makes API calls: NO"
    )

    print(
        "  explicit --execute required: YES"
    )

    print(
        "  explicit confirmation token required: YES"
    )

    print(
        "  one candidate/run session per invocation: YES"
    )

    print(
        "  initial attempts per logical request: max 3"
    )

    print(
        "  HTTP-200 invalid output retried: NO"
    )

    print(
        "  transient recovery queue supported: YES"
    )

    print(
        "  successful/resolved items skipped on resume: YES"
    )

    print(
        "  ZB1 concurrency: 1"
    )

    print(
        "  ZB2 success spacing: 10 sec"
    )

    print(
        "  ZB3 success spacing: 65 sec"
    )

    print(
        "  interim scoring implemented: NO"
    )

    print(
        "  paid OpenAI API implemented: NO"
    )

    report = {
        "audited_utc":
            utcnow(),
        "canonical_input_sha256":
            sha256_file(
                INPUTS
            ),
        "candidate_set_sha256":
            sha256_file(
                CANDIDATES_FILE
            ),
        "execution_policy_sha256":
            sha256_file(
                POLICY_FILE
            ),
        "runner_sha256":
            sha256_file(
                Path(__file__)
            ),
        "orders": {
            str(r): {
                "sha256":
                    order_info[r][
                        "sha256"
                    ],
                "count":
                    len(
                        order_info[r][
                            "items"
                        ]
                    ),
            }
            for r in [1, 2, 3]
        },
        "api_calls_made":
            0,
        "audit_pass":
            True,
    }

    report_path = (
        AUDIT
        / "runner_audit.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("AUDIT ARTIFACT")

    print(
        " ",
        report_path,
        sha256_file(
            report_path
        ),
    )

    print()
    print("=" * 78)
    print("AUDIT STATUS")
    print("=" * 78)

    print(
        "Full benchmark runner audit: PASS"
    )

    print(
        "API inference requests made: 0"
    )

    print(
        "Ground truth loaded: NO"
    )

    print(
        "External-TEST accessed: NO"
    )

    print(
        "Full benchmark executed: NO"
    )

    print(
        "Gate 6C winner: OPEN"
    )


# ============================================================
# INITIAL EXECUTION SESSION
# ============================================================

def execute_session(
    candidate_id,
    run_number,
):

    ensure_dirs()

    inputs = load_inputs()

    orders = ensure_orders(
        list(
            inputs.keys()
        )
    )

    enforce_execution_integrity()

    order = orders[
        run_number
    ]["items"]

    resolved = resolved_items(
        candidate_id,
        run_number,
    )

    print(
        f"Starting {candidate_id}"
        f" logical run {run_number}"
    )

    print(
        "Already resolved:",
        len(resolved),
    )

    for position, item_id in enumerate(
        order,
        start=1,
    ):

        if item_id in resolved:
            print(
                f"{position}/133"
                f" {item_id}"
                " | already resolved; skip"
            )
            continue

        print(
            f"{position}/133"
            f" {item_id}"
        )

        result = (
            execute_logical_request(
                candidate_id,
                run_number,
                position,
                inputs[item_id],
                "initial",
            )
        )

        if result[
            "status"
        ] == "STOP_PROVIDER_SESSION":

            raise SystemExit(
                "Provider session stopped "
                "because of a non-transient "
                "configuration/authentication error."
            )


# ============================================================
# RECOVERY SESSION
# ============================================================

def execute_recovery(
    candidate_id,
    run_number,
):

    ensure_dirs()

    marker = (
        STATE
        / f"{candidate_id}_run{run_number}"
          "_recovery_session_used.json"
    )

    marker_state = None

    if marker.exists():

        marker_state = json.loads(
            marker.read_text(
                encoding="utf-8"
            )
        )

        if (
            marker_state.get("status")
            == "completed"
        ):
            raise SystemExit(
                "STOP: the single recovery session "
                "for this candidate/run is already completed."
            )

        print(
            "Resuming previously started recovery session."
        )

    queue = load_jsonl(
        recovery_path(
            candidate_id,
            run_number,
        )
    )

    if not queue:
        raise SystemExit(
            "No recovery queue exists."
        )

    inputs = load_inputs()

    ensure_orders(
        list(
            inputs.keys()
        )
    )

    enforce_execution_integrity()

    if marker_state is None:

        marker_state = {
            "started_utc":
                utcnow(),
            "candidate_id":
                candidate_id,
            "logical_run":
                run_number,
            "status":
                "in_progress",
        }

        marker.write_text(
            json.dumps(
                marker_state,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    # Deduplicate queue defensively without changing its
    # persisted provenance.
    queue_by_item = {}

    for row in queue:
        queue_by_item[
            row["item_id"]
        ] = row

    queue = list(
        queue_by_item.values()
    )

    print(
        "Recovery items:",
        len(queue),
    )

    for row in queue:

        item_id = row[
            "item_id"
        ]

        position = row[
            "order_position"
        ]

        latest = latest_logical_record(
            candidate_id,
            run_number,
            item_id,
        )

        if (
            latest
            and latest.get("status")
            in TERMINAL_LOGICAL_STATUSES
        ):

            print(
                f"recovery | {item_id}"
                " | already terminal; skip"
            )

            continue

        print(
            f"recovery"
            f" | {item_id}"
        )

        result = (
            execute_logical_request(
                candidate_id,
                run_number,
                position,
                inputs[item_id],
                "recovery",
            )
        )

        if result[
            "status"
        ] == "STOP_PROVIDER_SESSION":

            raise SystemExit(
                "Recovery provider session stopped."
            )

    marker_state["status"] = "completed"
    marker_state["completed_utc"] = utcnow()

    marker.write_text(
        json.dumps(
            marker_state,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--audit-only",
        action="store_true",
    )

    parser.add_argument(
        "--execute",
        action="store_true",
    )

    parser.add_argument(
        "--recovery",
        action="store_true",
    )

    parser.add_argument(
        "--candidate",
        choices=[
            "ZB1",
            "ZB2",
            "ZB3",
        ],
    )

    parser.add_argument(
        "--run",
        type=int,
        choices=[
            1, 2, 3
        ],
    )

    parser.add_argument(
        "--confirm",
    )

    args = parser.parse_args()

    if args.audit_only:

        if (
            args.execute
            or args.recovery
        ):
            raise SystemExit(
                "Audit-only cannot execute."
            )

        audit()
        return

    # Safe default:
    # with no execution flag, only audit.
    if not (
        args.execute
        or args.recovery
    ):

        audit()
        return

    if (
        args.candidate is None
        or args.run is None
    ):
        raise SystemExit(
            "Execution requires --candidate and --run."
        )

    if args.confirm != (
        "FULL_BENCHMARK_EXECUTION"
    ):
        raise SystemExit(
            "STOP: explicit confirmation token missing."
        )

    if (
        args.execute
        and args.recovery
    ):
        raise SystemExit(
            "Choose either --execute or --recovery."
        )

    if args.execute:

        execute_session(
            args.candidate,
            args.run,
        )

    else:

        execute_recovery(
            args.candidate,
            args.run,
        )


if __name__ == "__main__":
    main()
