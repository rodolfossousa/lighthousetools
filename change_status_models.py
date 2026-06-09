"""
Script to register tags from Excel file using API in batches
and save failed tags to output file.
"""

import pandas as pd
import requests
import os
import sys
import ctypes
import math
import json

from Lighthouse.lighthouse import connect


# Input Excel file containing tags.
excel_filename = "tags_total.xlsx"

# Timestamp to start fetching data from.
last_timestamp = "2025-10-16T00:00:00Z"

# Batch size for processing tags.
batch_size = 100

# API endpoint URL (query params embutidos pois Lighthouse.post() não suporta params)
url = "https://modec-private.shapedigital.com/aiydata/pi-extraction-app/api/v1/add_multiple_tags?allow_without_recent_data=true"

# Lighthouse client — usa api_key e headers do __init__.py
ws = connect(client_name="modec", environment="prod", debug=False)


def _enable_ansi_on_windows():
    """Try to enable ANSI escape sequence processing on Windows consoles.
    This is best-effort: if it fails we silently continue and output will
    contain raw escape sequences (modern Windows terminals usually support
    ANSI already).
    """
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        hStdOut = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(hStdOut, ctypes.byref(mode)):
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.SetConsoleMode(hStdOut, new_mode)
    except Exception:
        # If anything goes wrong, don't break the program for a logging nicety
        pass


def _color_for_status(code: int) -> str:
    """Return ANSI color start code for an HTTP status code.

    - 2xx -> green
    - 3xx -> yellow
    - 4xx -> red
    - 5xx -> magenta
    - others -> reset/no color
    """
    try:
        code = int(code)
    except Exception:
        return "\033[0m"
    if 200 <= code < 300:
        return "\033[1;32m"  # bright green
    if 300 <= code < 400:
        return "\033[1;33m"  # bright yellow
    if 400 <= code < 500:
        return "\033[1;31m"  # bright red
    if 500 <= code < 600:
        return "\033[1;35m"  # bright magenta
    return "\033[0m"


def _color_text(text: str, color_start: str) -> str:
    RESET = "\033[0m"
    return f"{color_start}{text}{RESET}"


# Try to enable ANSI sequences on Windows terminals early.
_enable_ansi_on_windows()


def register_tag_batch(tags_batch):
    """Register a batch of tags and return failed tags."""
    # Sanitize incoming tags to avoid non-JSON-compliant values (NaN, inf).
    sanitized_payload = []
    skipped = 0
    for tag in tags_batch:
        # pandas objects (like numpy.nan) are detected with pd.isna
        if pd.isna(tag):
            skipped += 1
            continue
        # Reject infinite floats
        if isinstance(tag, (int, float)) and not math.isfinite(tag):
            skipped += 1
            continue

        # Coerce other types to strings so the API receives predictable values.
        try:
            tag_value = str(tag)
        except Exception:
            # If somehow not convertible, skip it
            skipped += 1
            continue

        sanitized_payload.append({"tag": tag_value, "last_timestamp": last_timestamp})

    if skipped:
        print(f"Skipped {skipped} invalid/empty tags in this batch")

    payload = sanitized_payload

    # If there's nothing valid to send, return an empty response dict.
    if not payload:
        print("No valid tags to send for this batch")
        return {}

    try:
        response = ws.post(url, payload)
    except requests.exceptions.InvalidJSONError as e:
        # This should be rare now due to sanitization; provide debug info.
        print("Failed to serialize payload to JSON. Inspecting payload sample:")
        try:
            print(json.dumps(payload[:5], indent=2, ensure_ascii=False))
        except Exception:
            print("(payload sample not JSON serializable)")
        raise
    # Try to parse JSON response. If parsing fails, return an empty dict so
    # the caller can continue aggregating other batches.
    try:
        response_data = response.json()
    except ValueError:
        response_data = {}

    # Minimal per-batch logging to avoid dumping large structures. Full
    # aggregation happens after all batches are processed.
    # Colorize the status code in logs for easier scanning in terminal
    color = _color_for_status(response.status_code)
    status_colored = _color_text(str(response.status_code), color)
    print(f"Processed {len(tags_batch)} tags. Status code: {status_colored}")

    return response_data


if __name__ == "__main__":
    df = pd.read_excel(excel_filename)
    tags = df["tags"].tolist()

    all_failed_tags = []
    all_responses = []

    for i in range(0, len(tags), batch_size):
        batch = tags[i : i + batch_size]
        batch_num = i // batch_size + 1
        end_tag = min(i + batch_size, len(tags))
        print(f"Processing batch {batch_num}: tags {i+1} to {end_tag}")

        resp = register_tag_batch(batch) or {}
        all_responses.append(resp)

        # Collect failed registering tags (keep old behavior of saving them)
        failed = resp.get("failed_registering_tags") or []
        if isinstance(failed, (list, tuple)):
            all_failed_tags.extend(failed)

    # Aggregate numeric counts for the known status keys. If a key is missing
    # or None, it's treated as zero. If a key contains a list, we count its
    # elements. If it's an int, we sum it directly.
    keys_to_count = [
        "duplicated_tags",
        "failed_registering_tags",
        "successfully_added",
        "failed_validation",
        "reenabled",
        "no_data_since_2020",
        "no_data_last_6_months",
    ]

    counts = {k: 0 for k in keys_to_count}

    for resp in all_responses:
        for k in keys_to_count:
            v = resp.get(k) if isinstance(resp, dict) else None
            if v is None:
                continue
            if isinstance(v, (list, tuple, set)):
                counts[k] += len(v)
            elif isinstance(v, int):
                counts[k] += v
            else:
                # Try to coerce numeric-like values (e.g. strings containing
                # integers). If that fails, skip.
                try:
                    counts[k] += int(v)
                except Exception:
                    continue

    # Print concise numeric report — one line per status with only the number.
    print("\nTags enrollment report (counts):")
    for k in keys_to_count:
        print(f"{k}: {counts[k]}")

    # Keep saving failed registering tags to Excel for further inspection.
    if all_failed_tags:
        failed_df = pd.DataFrame({"tags": all_failed_tags})
        failed_df.to_excel("failed_tags.xlsx", index=False)
        print(f"\nSaved {len(all_failed_tags)} failed tags to failed_tags.xlsx")
 