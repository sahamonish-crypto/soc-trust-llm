import csv
import hashlib
import json
import os
import random
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

INPUTS = Path("benchmarks/gate6c/canonical_model_inputs.jsonl")
ORIGINAL = Path("benchmarks/gate6c/smoke/smoke_results.jsonl")
RETRIES = Path("benchmarks/gate6c/smoke/smoke_retry_results.jsonl")
SUMMARY = Path("benchmarks/gate6c/smoke/smoke_retry_summary.txt")

VALID = {"ESCALATE", "DO_NOT_ESCALATE"}

if RETRIES.exists():
    raise SystemExit(
        "STOP: smoke_retry_results.jsonl already exists. "
        "Do not automatically repeat retries."
    )

# ------------------------------------------------------------
# Model-visible inputs only
# ------------------------------------------------------------

inputs = {}

with INPUTS.open(encoding="utf-8") as f:
    for line in f:
        x = json.loads(line)
        inputs[x["item_id"]] = x

# ------------------------------------------------------------
# Existing smoke results
# ------------------------------------------------------------

original = [
    json.loads(x)
    for x in ORIGINAL.read_text(
        encoding="utf-8"
    ).splitlines()
    if x.strip()
]

failed = [
    r for r in original
    if not (
        r.get("http_status") == 200
        and r.get("valid_exact_label") is True
    )
]

print("=" * 76)
print("TARGETED SMOKE RETRY PLAN")
print("=" * 76)

print("Original smoke requests:", len(original))
print("Already successful:", len(original) - len(failed))
print("Failed requests to retry:", len(failed))

for r in failed:
    print(
        r["candidate_id"],
        r["item_id"],
        "| previous HTTP",
        r.get("http_status"),
    )

print()
print("Ground truth loaded: NO")
print("Successful original requests repeated: NO")
print("Candidate models changed: NO")
print("Model payload changed: NO")


def hash_text(x):
    return hashlib.sha256(
        x.encode("utf-8")
    ).hexdigest()


def curl_json(
    url,
    headers,
    payload,
    max_time,
):
    hf = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        encoding="utf-8",
    )

    bf = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        encoding="utf-8",
    )

    try:
        os.chmod(hf.name, 0o600)
        os.chmod(bf.name, 0o600)

        for h in headers:
            hf.write(h + "\n")

        hf.close()

        json.dump(payload, bf)
        bf.close()

        start = time.perf_counter()

        p = subprocess.run(
            [
                "curl",
                "-sS",
                "--connect-timeout", "30",
                "--max-time", str(max_time),
                "-X", "POST",
                "-H", f"@{hf.name}",
                "--data-binary", f"@{bf.name}",
                url,
                "-w",
                "\n__HTTP_STATUS__:%{http_code}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        latency = round(
            (time.perf_counter() - start) * 1000,
            1,
        )

        marker = "\n__HTTP_STATUS__:"

        if marker not in p.stdout:
            return {
                "http_status": 0,
                "body": None,
                "raw": p.stdout,
                "latency_ms": latency,
                "transport_error":
                    p.stderr.strip()
                    or "status marker missing",
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
            "latency_ms": latency,
            "transport_error":
                p.stderr.strip(),
        }

    finally:
        for p in [hf.name, bf.name]:
            try:
                os.remove(p)
            except Exception:
                pass


def groq_call(model, messages):

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "reasoning_effort": "low",
        "include_reasoning": False,
        "max_completion_tokens": 512,
        "stream": False,
    }

    r = curl_json(
        "https://api.groq.com/openai/v1/chat/completions",
        [
            "Authorization: Bearer "
            + os.environ["GROQ_API_KEY"],
            "Content-Type: application/json",
            "User-Agent: soc-trust-llm-research/1.0",
        ],
        payload,
        180,
    )

    body = r["body"] or {}

    try:
        output = (
            body["choices"][0]
            ["message"]["content"]
            or ""
        ).strip()
    except Exception:
        output = ""

    try:
        returned_model = body["model"]
    except Exception:
        returned_model = None

    return r, output, returned_model, body.get("error")


def gemini_call(model, messages):

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
            "parts": [{"text": system_text}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_text}],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 512,
            "thinkingConfig": {
                "thinkingLevel": "low"
            },
        },
    }

    r = curl_json(
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        + model
        + ":generateContent",
        [
            "x-goog-api-key: "
            + os.environ["GEMINI_API_KEY"],
            "Content-Type: application/json",
            "User-Agent: soc-trust-llm-research/1.0",
        ],
        payload,
        300,
    )

    body = r["body"] or {}

    pieces = []

    try:
        for part in (
            body["candidates"][0]
            ["content"]["parts"]
        ):
            if part.get("thought") is True:
                continue

            if part.get("text"):
                pieces.append(
                    part["text"]
                )
    except Exception:
        pass

    output = "".join(pieces).strip()

    return (
        r,
        output,
        body.get("modelVersion"),
        body.get("error"),
    )


TRANSIENT = {
    0, 408, 429,
    498, 500, 502,
    503, 504,
}

retry_records = []

# Maximum TWO new attempts per originally failed request.
# This keeps the retry bounded.
for failed_record in failed:

    cid = failed_record["candidate_id"]
    model = failed_record["requested_model"]
    item_id = failed_record["item_id"]

    success = False

    for attempt in [1, 2]:

        # Prevent immediate OTPM collisions.
        if cid == "ZB3":
            base_wait = 5
        elif cid == "ZB1":
            base_wait = 10
        else:
            base_wait = 5

        if attempt > 1:
            delay = (
                base_wait * 3
                + random.uniform(0, 2)
            )

            print(
                f"Waiting {delay:.1f}s "
                f"before retry attempt {attempt}..."
            )

            time.sleep(delay)

        messages = inputs[
            item_id
        ]["messages"]

        started = datetime.now(
            timezone.utc
        ).isoformat()

        if cid == "ZB1":
            r, output, returned, error = (
                gemini_call(
                    model,
                    messages,
                )
            )
        else:
            r, output, returned, error = (
                groq_call(
                    model,
                    messages,
                )
            )

        valid = output in VALID

        rec = {
            "candidate_id": cid,
            "requested_model": model,
            "item_id": item_id,
            "retry_attempt": attempt,
            "started_utc": started,
            "http_status":
                r["http_status"],
            "latency_ms":
                r["latency_ms"],
            "returned_model":
                returned,
            "valid_exact_label":
                valid,

            # Kept in file for audit;
            # never printed below.
            "output": output,
            "output_sha256":
                hash_text(output),

            "raw_response_sha256":
                hash_text(
                    r.get("raw") or ""
                ),

            "provider_error": error,
            "transport_error":
                r.get("transport_error"),

            "ground_truth_loaded": False,
        }

        retry_records.append(rec)

        print(
            cid,
            item_id,
            f"| retry {attempt}",
            f"| HTTP {r['http_status']}",
            f"| valid={valid}",
            f"| returned_model={returned}",
            f"| latency_ms={r['latency_ms']}",
        )

        if (
            r["http_status"] == 200
            and valid
        ):
            success = True
            break

        if r["http_status"] not in TRANSIENT:
            print(
                "Non-transient failure; "
                "no further retry for this request."
            )
            break

    if not success:
        print(
            cid,
            item_id,
            "| RETRY EXHAUSTED"
        )


with RETRIES.open(
    "w",
    encoding="utf-8"
) as f:
    for r in retry_records:
        f.write(
            json.dumps(
                r,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )


# ------------------------------------------------------------
# Merge logical compatibility:
# original success OR later retry success.
# ------------------------------------------------------------

resolved = {}

for r in original:
    key = (
        r["candidate_id"],
        r["item_id"],
    )

    resolved[key] = (
        r.get("http_status") == 200
        and r.get(
            "valid_exact_label"
        ) is True
    )

for r in retry_records:
    key = (
        r["candidate_id"],
        r["item_id"],
    )

    if (
        r.get("http_status") == 200
        and r.get(
            "valid_exact_label"
        ) is True
    ):
        resolved[key] = True


models = {
    "ZB1": "gemini-3.8-flash",
    "ZB2": "openai/gpt-oss-120b",
    "ZB3": "qwen/qwen3.8-27b",
}

lines = [
    "Gate 6C targeted smoke retry summary",
    "====================================",
    "",
    "Ground truth loaded: NO",
    "Winner selection performed: NO",
    "Benchmark scoring performed: NO",
    "External-TEST accessed: NO",
    "",
]

overall = True

for cid, model in models.items():

    keys = [
        k for k in resolved
        if k[0] == cid
    ]

    passed = sum(
        1
        for k in keys
        if resolved[k]
    )

    ok = (
        len(keys) == 3
        and passed == 3
    )

    overall = overall and ok

    lines.extend([
        f"{cid} | {model}",
        f"  compatible smoke items: {passed}/3",
        "  compatibility: "
        + ("PASS" if ok else "FAIL"),
        "",
    ])

lines.append(
    "OVERALL SMOKE COMPATIBILITY AFTER "
    "TRANSIENT RETRIES: "
    + ("PASS" if overall else "FAIL")
)

lines.extend([
    "",
    "Original successful responses were not repeated.",
    "Only transiently failed requests were retried.",
    "No ground truth was used.",
    "No winner was selected.",
])

SUMMARY.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print()
print("=" * 76)
print("TARGETED RETRY SUMMARY")
print("=" * 76)

print(
    SUMMARY.read_text(
        encoding="utf-8"
    )
)

print("=" * 76)
print("RETRY ARTIFACTS")
print("=" * 76)

print(
    RETRIES,
    hashlib.sha256(
        RETRIES.read_bytes()
    ).hexdigest()
)

print(
    SUMMARY,
    hashlib.sha256(
        SUMMARY.read_bytes()
    ).hexdigest()
)

print()
print("Ground truth loaded: NO")
print("External-TEST accessed: NO")
print("Winner selected: NO")
