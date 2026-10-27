import csv
import hashlib
import json
import os
import subprocess
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

INPUTS = Path(
    "benchmarks/gate6c/canonical_model_inputs.jsonl"
)
META = Path(
    "benchmarks/gate6c/item_metadata.csv"
)
CANDIDATES = Path(
    "benchmarks/gate6c/zero_budget_candidate_set.json"
)

OUT = Path("benchmarks/gate6c/smoke")
OUT.mkdir(parents=True, exist_ok=True)

PLAN = OUT / "smoke_plan.json"
RESULTS = OUT / "smoke_results.jsonl"
SUMMARY = OUT / "smoke_summary.txt"

EXPECTED_INPUT_SHA = (
    "a4cb01041ed16de2eae6fce2abb803631"
    "7fc068653b8abdd0812d6424b3a4915"
)

EXPECTED_CANDIDATE_SHA = (
    "cde38f3e2584720559ceb27d794588273"
    "c476a5cbb123ad0a3649cffe4a7cb03"
)

VALID_LABELS = {
    "ESCALATE",
    "DO_NOT_ESCALATE",
}


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def canonical_json(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def curl_json(url, headers, payload):
    """
    POST JSON through curl.

    Secret headers are stored only in a temporary 0600 file.
    They are never printed and are not placed in Git.
    """

    header_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
    )

    body_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
    )

    try:
        os.chmod(header_file.name, 0o600)
        os.chmod(body_file.name, 0o600)

        for h in headers:
            header_file.write(h + "\n")

        header_file.close()

        json.dump(
            payload,
            body_file,
            ensure_ascii=False,
        )

        body_file.close()

        cmd = [
            "curl",
            "-sS",
            "--connect-timeout",
            "30",
            "--max-time",
            "180",
            "-X",
            "POST",
            "-H",
            f"@{header_file.name}",
            "--data-binary",
            f"@{body_file.name}",
            url,
            "-w",
            "\n__HTTP_STATUS__:%{http_code}",
        ]

        start = time.perf_counter()

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        latency_ms = round(
            (time.perf_counter() - start) * 1000,
            1,
        )

        text = proc.stdout

        marker = "\n__HTTP_STATUS__:"

        if marker not in text:
            return {
                "http_status": 0,
                "latency_ms": latency_ms,
                "body": None,
                "raw_body": text,
                "transport_error":
                    proc.stderr.strip()
                    or "HTTP status marker missing",
            }

        body_text, status_text = text.rsplit(
            marker,
            1,
        )

        try:
            status = int(status_text.strip())
        except Exception:
            status = 0

        try:
            body = json.loads(body_text)
        except Exception:
            body = None

        return {
            "http_status": status,
            "latency_ms": latency_ms,
            "body": body,
            "raw_body": body_text,
            "transport_error":
                proc.stderr.strip(),
        }

    finally:
        for path in [
            header_file.name,
            body_file.name,
        ]:
            try:
                os.remove(path)
            except Exception:
                pass


# ============================================================
# PRE-FLIGHT
# ============================================================

print("=" * 76)
print("GATE 6C ZERO-BUDGET SMOKE TEST")
print("=" * 76)

input_sha = sha256_file(INPUTS)
candidate_sha = sha256_file(CANDIDATES)

print("Canonical input hash:", input_sha)
print(
    "Canonical input hash check:",
    "PASS"
    if input_sha == EXPECTED_INPUT_SHA
    else "FAIL",
)

print("Candidate-set hash:", candidate_sha)
print(
    "Candidate-set hash check:",
    "PASS"
    if candidate_sha == EXPECTED_CANDIDATE_SHA
    else "FAIL",
)

if (
    input_sha != EXPECTED_INPUT_SHA
    or candidate_sha != EXPECTED_CANDIDATE_SHA
):
    raise SystemExit(
        "STOP: frozen artifact hash mismatch."
    )

if not os.getenv("GROQ_API_KEY"):
    raise SystemExit(
        "STOP: GROQ_API_KEY not set."
    )

if not os.getenv("GEMINI_API_KEY"):
    raise SystemExit(
        "STOP: GEMINI_API_KEY not set."
    )

# Protect against accidentally running the one-run smoke twice.
if RESULTS.exists():
    raise SystemExit(
        "STOP: smoke_results.jsonl already exists. "
        "Do not rerun the smoke test automatically."
    )


# ============================================================
# LOAD MODEL-VISIBLE INPUTS ONLY
# ============================================================

inputs = {}

with INPUTS.open(
    encoding="utf-8"
) as f:
    for line in f:
        obj = json.loads(line)
        inputs[obj["item_id"]] = obj

assert len(inputs) == 133

# IMPORTANT:
# hidden_ground_truth.csv is intentionally never opened.


# ============================================================
# DETERMINISTIC SMOKE ITEM SELECTION
#
# Selection uses metadata only:
# 1. first CTU item with evidence
# 2. first CTU item without evidence
# 3. first Muhstik External-DEV item
#
# No ground truth is consulted.
# ============================================================

with META.open(
    newline="",
    encoding="utf-8"
) as f:
    meta = list(csv.DictReader(f))

ctu_with_evidence = sorted(
    r["item_id"]
    for r in meta
    if (
        r["group"] == "CTU_DEV"
        and int(r["evidence_count"]) > 0
    )
)

ctu_without_evidence = sorted(
    r["item_id"]
    for r in meta
    if (
        r["group"] == "CTU_DEV"
        and int(r["evidence_count"]) == 0
    )
)

muhstik = sorted(
    r["item_id"]
    for r in meta
    if r["group"] == "MUHSTIK_EXTERNAL_DEV"
)

if not (
    ctu_with_evidence
    and ctu_without_evidence
    and muhstik
):
    raise SystemExit(
        "STOP: deterministic smoke selection failed."
    )

smoke_items = [
    {
        "role": "CTU_WITH_EVIDENCE",
        "item_id": ctu_with_evidence[0],
    },
    {
        "role": "CTU_WITHOUT_EVIDENCE",
        "item_id": ctu_without_evidence[0],
    },
    {
        "role": "MUHSTIK_EXTERNAL_DEV",
        "item_id": muhstik[0],
    },
]

models = [
    {
        "candidate_id": "ZB1",
        "provider": "gemini",
        "model": "gemini-3.8-flash",
    },
    {
        "candidate_id": "ZB2",
        "provider": "groq",
        "model": "openai/gpt-oss-120b",
    },
    {
        "candidate_id": "ZB3",
        "provider": "groq",
        "model": "qwen/qwen3.8-27b",
    },
]


# ============================================================
# WRITE PLAN BEFORE FIRST INFERENCE
# ============================================================

plan = {
    "created_utc":
        datetime.now(timezone.utc).isoformat(),

    "purpose":
        "API/config/output compatibility smoke test only",

    "ground_truth_loaded": False,

    "winner_selection_permitted": False,

    "canonical_input_sha256": input_sha,

    "candidate_set_sha256": candidate_sha,

    "selection_rule": [
        "lexicographically first CTU_DEV item with evidence_count > 0",
        "lexicographically first CTU_DEV item with evidence_count == 0",
        "lexicographically first MUHSTIK_EXTERNAL_DEV item",
    ],

    "items": smoke_items,

    "candidates": models,

    "runs_per_item": 1,

    "expected_requests": 9,

    "configuration": {
        "reasoning_level": "low",
        "external_tools": "disabled",
        "web_search": "disabled",
        "groq_temperature": 0,
        "gemini_sampling_parameters": "omitted",
        "max_completion_tokens": 512,
    },
}

PLAN.write_text(
    json.dumps(
        plan,
        indent=2,
        sort_keys=True,
    ) + "\n",
    encoding="utf-8",
)

plan_sha = sha256_file(PLAN)

print()
print("=" * 76)
print("SMOKE PLAN")
print("=" * 76)

for x in smoke_items:
    print(
        x["role"] + ":",
        x["item_id"],
    )

print("Smoke plan SHA256:", plan_sha)
print("Ground truth loaded: NO")
print("Expected inference requests: 9")


# ============================================================
# PROVIDER REQUEST BUILDERS
# ============================================================

def call_groq(model, messages):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "reasoning_effort": "low",
        "include_reasoning": False,
        "max_completion_tokens": 512,
        "stream": False,
    }

    result = curl_json(
        "https://api.groq.com/openai/v1/chat/completions",
        [
            "Authorization: Bearer "
            + os.environ["GROQ_API_KEY"],
            "Content-Type: application/json",
            "User-Agent: soc-trust-llm-research/1.0",
        ],
        payload,
    )

    body = result["body"] or {}

    output = ""

    try:
        output = (
            body["choices"][0]
            ["message"]["content"]
            or ""
        ).strip()
    except Exception:
        pass

    returned_model = body.get("model")

    finish_reason = None

    try:
        finish_reason = (
            body["choices"][0]
            .get("finish_reason")
        )
    except Exception:
        pass

    return {
        **result,
        "output": output,
        "returned_model": returned_model,
        "finish_reason": finish_reason,
        "usage": body.get("usage"),
        "provider_error":
            body.get("error"),
    }


def call_gemini(model, messages):
    system_text = None
    user_text = None

    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]

        elif m["role"] == "user":
            user_text = m["content"]

    if (
        system_text is None
        or user_text is None
    ):
        raise RuntimeError(
            "Canonical system/user message missing."
        )

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": system_text
                }
            ]
        },

        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": user_text
                    }
                ],
            }
        ],

        "generationConfig": {
            "maxOutputTokens": 512,
            "thinkingConfig": {
                "thinkingLevel": "low"
            },
        },
    }

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        + model
        + ":generateContent"
    )

    result = curl_json(
        url,
        [
            "x-goog-api-key: "
            + os.environ["GEMINI_API_KEY"],
            "Content-Type: application/json",
            "User-Agent: soc-trust-llm-research/1.0",
        ],
        payload,
    )

    body = result["body"] or {}

    output_parts = []

    try:
        parts = (
            body["candidates"][0]
            ["content"]["parts"]
        )

        for p in parts:
            # Do not retain thought/reasoning parts.
            if p.get("thought") is True:
                continue

            text = p.get("text")

            if text:
                output_parts.append(text)

    except Exception:
        pass

    output = "".join(
        output_parts
    ).strip()

    finish_reason = None

    try:
        finish_reason = (
            body["candidates"][0]
            .get("finishReason")
        )
    except Exception:
        pass

    return {
        **result,
        "output": output,
        "returned_model":
            body.get("modelVersion"),
        "finish_reason":
            finish_reason,
        "usage":
            body.get("usageMetadata"),
        "provider_error":
            body.get("error"),
    }


# ============================================================
# NINE REQUEST SMOKE TEST
# ============================================================

print()
print("=" * 76)
print("SMOKE EXECUTION")
print("=" * 76)

records = []
request_number = 0

with RESULTS.open(
    "w",
    encoding="utf-8",
) as fout:

    for model in models:

        for selected in smoke_items:

            request_number += 1

            item_id = selected["item_id"]

            record = {
                "request_number":
                    request_number,

                "candidate_id":
                    model["candidate_id"],

                "provider":
                    model["provider"],

                "requested_model":
                    model["model"],

                "item_id":
                    item_id,

                "smoke_item_role":
                    selected["role"],

                "started_utc":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "ground_truth_loaded":
                    False,
            }

            try:
                if model["provider"] == "groq":

                    response = call_groq(
                        model["model"],
                        inputs[item_id]["messages"],
                    )

                else:

                    response = call_gemini(
                        model["model"],
                        inputs[item_id]["messages"],
                    )

                output = (
                    response.get("output")
                    or ""
                ).strip()

                valid = (
                    output in VALID_LABELS
                )

                raw_body = (
                    response.get("raw_body")
                    or ""
                )

                record.update({
                    "http_status":
                        response.get(
                            "http_status"
                        ),

                    "latency_ms":
                        response.get(
                            "latency_ms"
                        ),

                    "returned_model":
                        response.get(
                            "returned_model"
                        ),

                    "finish_reason":
                        response.get(
                            "finish_reason"
                        ),

                    "valid_exact_label":
                        valid,

                    # Stored for compatibility audit,
                    # but NOT printed to terminal.
                    "output":
                        output,

                    "output_sha256":
                        sha256_text(output),

                    "raw_response_sha256":
                        sha256_text(
                            raw_body
                        ),

                    "usage":
                        response.get(
                            "usage"
                        ),

                    "provider_error":
                        response.get(
                            "provider_error"
                        ),

                    "transport_error":
                        response.get(
                            "transport_error"
                        ),
                })

            except Exception as e:

                record.update({
                    "http_status": 0,
                    "latency_ms": None,
                    "returned_model": None,
                    "finish_reason": None,
                    "valid_exact_label": False,
                    "output": "",
                    "output_sha256":
                        sha256_text(""),
                    "raw_response_sha256":
                        None,
                    "usage": None,
                    "provider_error": None,
                    "transport_error":
                        type(e).__name__
                        + ": "
                        + str(e),
                })

            records.append(record)

            fout.write(
                canonical_json(record)
                + "\n"
            )

            fout.flush()

            print(
                f"{request_number}/9"
                f" | {model['candidate_id']}"
                f" | {item_id}"
                f" | HTTP {record['http_status']}"
                f" | valid_exact_label="
                f"{record['valid_exact_label']}"
                f" | returned_model="
                f"{record['returned_model']}"
                f" | latency_ms="
                f"{record['latency_ms']}"
            )

            # Gentle spacing for free-tier APIs.
            time.sleep(1)


# ============================================================
# COMPATIBILITY SUMMARY ONLY
# ============================================================

per_model = defaultdict(list)

for r in records:
    per_model[
        r["candidate_id"]
    ].append(r)

lines = []

lines.append(
    "Gate 6C zero-budget smoke test"
)

lines.append(
    "================================"
)

lines.append("")

lines.append(
    "Ground truth loaded: NO"
)

lines.append(
    "Winner selection performed: NO"
)

lines.append(
    "Benchmark scoring performed: NO"
)

lines.append(
    "External-TEST accessed: NO"
)

lines.append(
    "Requests attempted: "
    + str(len(records))
)

lines.append("")

overall_pass = True

for model in models:

    cid = model["candidate_id"]
    rs = per_model[cid]

    http_ok = sum(
        1
        for r in rs
        if r["http_status"] == 200
    )

    valid_ok = sum(
        1
        for r in rs
        if r["valid_exact_label"]
    )

    returned_models = sorted({
        str(r["returned_model"])
        for r in rs
        if r["returned_model"]
    })

    provider_pass = (
        len(rs) == 3
        and http_ok == 3
        and valid_ok == 3
    )

    overall_pass = (
        overall_pass
        and provider_pass
    )

    lines.append(
        f"{cid} | {model['model']}"
    )

    lines.append(
        f"  HTTP 200: {http_ok}/3"
    )

    lines.append(
        f"  exact valid labels: {valid_ok}/3"
    )

    lines.append(
        "  returned model IDs: "
        + (
            ", ".join(returned_models)
            if returned_models
            else "NONE"
        )
    )

    lines.append(
        "  compatibility: "
        + (
            "PASS"
            if provider_pass
            else "FAIL"
        )
    )

    lines.append("")


lines.append(
    "OVERALL SMOKE COMPATIBILITY: "
    + (
        "PASS"
        if overall_pass
        else "FAIL"
    )
)

lines.append("")

lines.append(
    "IMPORTANT: smoke outputs were not "
    "compared with ground truth."
)

lines.append(
    "No model winner can be selected "
    "from this test."
)

SUMMARY.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print()
print("=" * 76)
print("SMOKE COMPATIBILITY SUMMARY")
print("=" * 76)

print(
    SUMMARY.read_text(
        encoding="utf-8"
    )
)

print("=" * 76)
print("SMOKE ARTIFACTS")
print("=" * 76)

print(
    "Plan:",
    PLAN,
    sha256_file(PLAN),
)

print(
    "Results:",
    RESULTS,
    sha256_file(RESULTS),
)

print(
    "Summary:",
    SUMMARY,
    sha256_file(SUMMARY),
)

print()
print("Ground truth loaded: NO")
print("External-TEST accessed: NO")
print("OpenAI paid API used: NO")
print("Winner selected: NO")
