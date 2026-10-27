import hashlib
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

INPUTS = Path(
    "benchmarks/gate6c/canonical_model_inputs.jsonl"
)

OLD_PLAN = Path(
    "benchmarks/gate6c/smoke/smoke_plan.json"
)

OUT = Path(
    "benchmarks/gate6c/smoke/gemini36_smoke_results.jsonl"
)

SUMMARY = Path(
    "benchmarks/gate6c/smoke/gemini36_smoke_summary.txt"
)

EXPECTED_INPUT_SHA = (
    "a4cb01041ed16de2eae6fce2abb803631"
    "7fc068653b8abdd0812d6424b3a4915"
)

MODEL = "gemini-3.6-flash"

VALID = {
    "ESCALATE",
    "DO_NOT_ESCALATE",
}

TRANSIENT = {
    0, 408, 429,
    500, 502, 503, 504,
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


def curl_json(payload):

    hf = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
    )

    bf = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
    )

    try:
        os.chmod(hf.name, 0o600)
        os.chmod(bf.name, 0o600)

        hf.write(
            "x-goog-api-key: "
            + os.environ["GEMINI_API_KEY"]
            + "\n"
        )

        hf.write(
            "Content-Type: application/json\n"
        )

        hf.write(
            "User-Agent: soc-trust-llm-research/1.0\n"
        )

        hf.close()

        json.dump(
            payload,
            bf,
            ensure_ascii=False,
        )

        bf.close()

        url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/models/"
            + MODEL
            + ":generateContent"
        )

        start = time.perf_counter()

        p = subprocess.run(
            [
                "curl",
                "-sS",
                "--connect-timeout", "30",
                "--max-time", "240",
                "-X", "POST",
                "-H", f"@{hf.name}",
                "--data-binary", f"@{bf.name}",
                url,
                "-w",
                "\n__STATUS__:%{http_code}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        latency_ms = round(
            (time.perf_counter() - start) * 1000,
            1,
        )

        marker = "\n__STATUS__:"

        if marker not in p.stdout:
            return {
                "http_status": 0,
                "body": None,
                "raw": p.stdout,
                "latency_ms": latency_ms,
                "transport_error":
                    p.stderr.strip()
                    or "HTTP marker missing",
            }

        raw, status = p.stdout.rsplit(
            marker,
            1,
        )

        try:
            status = int(status.strip())
        except Exception:
            status = 0

        try:
            body = json.loads(raw)
        except Exception:
            body = None

        return {
            "http_status": status,
            "body": body,
            "raw": raw,
            "latency_ms": latency_ms,
            "transport_error":
                p.stderr.strip(),
        }

    finally:
        for p in [hf.name, bf.name]:
            try:
                os.remove(p)
            except Exception:
                pass


# ------------------------------------------------------------
# Safety / frozen artifact checks
# ------------------------------------------------------------

print("=" * 76)
print("GEMINI 3.6 REPLACEMENT SMOKE TEST")
print("=" * 76)

input_sha = sha256_file(INPUTS)

print(
    "Canonical input hash:",
    input_sha
)

print(
    "Canonical input hash check:",
    "PASS"
    if input_sha == EXPECTED_INPUT_SHA
    else "FAIL"
)

if input_sha != EXPECTED_INPUT_SHA:
    raise SystemExit(
        "STOP: canonical benchmark changed."
    )

if not os.getenv("GEMINI_API_KEY"):
    raise SystemExit(
        "STOP: GEMINI_API_KEY not set."
    )

if OUT.exists():
    raise SystemExit(
        "STOP: Gemini 3.6 smoke results "
        "already exist. Do not rerun automatically."
    )


# ------------------------------------------------------------
# Load canonical model-visible inputs only
# ------------------------------------------------------------

inputs = {}

with INPUTS.open(
    encoding="utf-8"
) as f:

    for line in f:
        x = json.loads(line)
        inputs[x["item_id"]] = x

assert len(inputs) == 133


# ------------------------------------------------------------
# Reuse EXACT SAME predetermined smoke items
# from original plan.
#
# No new item selection occurs.
# ------------------------------------------------------------

plan = json.loads(
    OLD_PLAN.read_text(
        encoding="utf-8"
    )
)

smoke_items = plan["items"]

expected_ids = [
    "DEV-CTU-001",
    "DEV-CTU-012",
    "DEV-MUH-001",
]

actual_ids = [
    x["item_id"]
    for x in smoke_items
]

if actual_ids != expected_ids:
    raise SystemExit(
        "STOP: original smoke item IDs do not match."
    )

print()
print("Smoke items:")

for x in smoke_items:
    print(
        " ",
        x["role"],
        x["item_id"],
    )

print()
print("Model:", MODEL)
print("thinkingLevel: low")
print("maxOutputTokens: 512")
print("Ground truth loaded: NO")
print("External-TEST accessed: NO")
print("Other candidate models called: NO")


# ------------------------------------------------------------
# Execute three logical smoke requests
#
# Operational policy for THIS compatibility check:
# initial request + maximum two retries only for
# transient HTTP/network failures.
#
# Outputs are stored but never printed.
# ------------------------------------------------------------

records = []

for selected in smoke_items:

    item_id = selected["item_id"]

    messages = inputs[
        item_id
    ]["messages"]

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
                ]
            }
        ],

        "generationConfig": {
            "maxOutputTokens": 512,
            "thinkingConfig": {
                "thinkingLevel": "low"
            }
        },
    }

    logical_success = False

    for attempt in [1, 2, 3]:

        if attempt > 1:

            delay = (
                15
                if attempt == 2
                else 45
            )

            print(
                f"{item_id}"
                f" | waiting {delay}s"
                f" before transient retry {attempt}"
            )

            time.sleep(delay)

        started = datetime.now(
            timezone.utc
        ).isoformat()

        r = curl_json(payload)

        body = r["body"] or {}

        output_parts = []

        try:
            candidate = (
                body["candidates"][0]
            )

            parts = (
                candidate
                .get("content", {})
                .get("parts", [])
            )

            for part in parts:

                if part.get("thought") is True:
                    continue

                if part.get("text"):
                    output_parts.append(
                        part["text"]
                    )

            finish = candidate.get(
                "finishReason"
            )

        except Exception:
            finish = None

        output = "".join(
            output_parts
        ).strip()

        valid = (
            output in VALID
        )

        usage = body.get(
            "usageMetadata",
            {}
        )

        record = {
            "model": MODEL,
            "item_id": item_id,
            "smoke_item_role":
                selected["role"],
            "attempt": attempt,
            "started_utc": started,
            "http_status":
                r["http_status"],
            "latency_ms":
                r["latency_ms"],
            "returned_model":
                body.get("modelVersion"),
            "finish_reason":
                finish,
            "valid_exact_label":
                valid,

            # Stored for audit but never printed.
            "output":
                output,

            "output_sha256":
                sha256_text(output),

            "raw_response_sha256":
                sha256_text(
                    r.get("raw") or ""
                ),

            "usage":
                usage,

            "provider_error":
                body.get("error"),

            "transport_error":
                r.get(
                    "transport_error"
                ),

            "ground_truth_loaded":
                False,
        }

        records.append(record)

        print(
            item_id,
            f"| attempt {attempt}",
            f"| HTTP {r['http_status']}",
            f"| valid={valid}",
            f"| finish={finish}",
            f"| returned_model="
            f"{body.get('modelVersion')}",
            f"| latency_ms="
            f"{r['latency_ms']}",
        )

        if (
            r["http_status"] == 200
            and valid
        ):
            logical_success = True
            break

        if r["http_status"] not in TRANSIENT:
            print(
                item_id,
                "| non-transient failure; "
                "no additional retry"
            )
            break

    if not logical_success:
        print(
            item_id,
            "| COMPATIBILITY FAILURE"
        )


# ------------------------------------------------------------
# Write all attempts
# ------------------------------------------------------------

with OUT.open(
    "w",
    encoding="utf-8"
) as f:

    for r in records:
        f.write(
            json.dumps(
                r,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )


# ------------------------------------------------------------
# Logical compatibility by item
# ------------------------------------------------------------

passed = {}

for item_id in expected_ids:

    passed[item_id] = any(
        r["item_id"] == item_id
        and r["http_status"] == 200
        and r["valid_exact_label"]
        for r in records
    )

total = sum(
    1
    for ok in passed.values()
    if ok
)

overall = total == 3

lines = [
    "Gemini 3.6 replacement smoke summary",
    "====================================",
    "",
    f"Model: {MODEL}",
    "thinkingLevel: low",
    "maxOutputTokens: 512",
    "",
    "Ground truth loaded: NO",
    "Benchmark scoring performed: NO",
    "Winner selection performed: NO",
    "External-TEST accessed: NO",
    "",
]

for item_id in expected_ids:

    lines.append(
        f"{item_id}: "
        + (
            "PASS"
            if passed[item_id]
            else "FAIL"
        )
    )

lines.extend([
    "",
    f"Compatible smoke items: {total}/3",
    "",
    "GEMINI 3.6 SMOKE COMPATIBILITY: "
    + (
        "PASS"
        if overall
        else "FAIL"
    ),
    "",
    "No ground truth was consulted.",
    "No model-performance comparison was performed.",
])

SUMMARY.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print()
print("=" * 76)
print("GEMINI 3.6 SMOKE SUMMARY")
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
    OUT,
    sha256_file(OUT)
)

print(
    SUMMARY,
    sha256_file(SUMMARY)
)

print()
print("Ground truth loaded: NO")
print("External-TEST accessed: NO")
print("Winner selected: NO")
