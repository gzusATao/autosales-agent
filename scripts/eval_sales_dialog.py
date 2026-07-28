"""
Run scripted sales-dialog evaluations against the local Chat API.

Default mode uses the running local service at http://127.0.0.1:8000.
Use --live to require a configured DeepSeek-compatible API key; without it the
project falls back to deterministic mock responses.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "evals" / "sales_dialog_cases.json"


def post_json(url: str, payload: dict, timeout: float = 60) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def score_turn(response: dict, case: dict) -> tuple[int, list[str]]:
    reply = response.get("reply", "")
    tools = [item.get("tool_name", "") for item in response.get("tool_trace", [])]
    issues: list[str] = []

    if case.get("expected_intent") and response.get("current_intent") != case["expected_intent"]:
        issues.append(f"intent={response.get('current_intent')} expected={case['expected_intent']}")

    for expected_tool in case.get("expected_tools", []):
        if expected_tool not in tools:
            issues.append(f"missing tool {expected_tool}")

    for text in case.get("must_include", []):
        if text not in reply:
            issues.append(f"missing text {text!r}")

    for text in case.get("must_not_include", []):
        if text in reply:
            issues.append(f"forbidden text {text!r}")

    return (0 if issues else 1), issues


def _tool_names(response: dict) -> list[str]:
    return [item.get("tool_name", "") for item in response.get("tool_trace", [])]


def _rag_docs(response: dict) -> list[dict]:
    docs = []
    for item in response.get("tool_trace", []):
        if item.get("tool_name") == "rag_search_tool":
            docs.append({
                "input": item.get("input", {}),
                "output": item.get("output", {}),
            })
    return docs


def run_cases(base_url: str, cases_path: Path) -> int:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    total = 0
    passed = 0
    records = []

    for case in cases:
        session_id = f"EVAL-{case['id']}-{int(time.time() * 1000)}"
        last_response = {}
        turn_records = []
        for turn in case["turns"]:
            last_response = post_json(
                f"{base_url.rstrip('/')}/api/chat/message",
                {"session_id": session_id, "message": turn},
            )
            turn_records.append({
                "user_message": turn,
                "intent": last_response.get("current_intent", ""),
                "purchase_intent": last_response.get("purchase_intent", {}),
                "missing_slots": last_response.get("missing_slots", []),
                "tools": _tool_names(last_response),
                "tool_trace": last_response.get("tool_trace", []),
                "rag_docs": _rag_docs(last_response),
                "reply": last_response.get("reply", ""),
            })

        total += 1
        ok, issues = score_turn(last_response, case)
        passed += ok
        records.append({
            "id": case["id"],
            "passed": bool(ok),
            "issues": issues,
            "turns": turn_records,
            "expected_intent": case.get("expected_intent", ""),
            "expected_tools": case.get("expected_tools", []),
            "intent": last_response.get("current_intent", ""),
            "missing_slots": last_response.get("missing_slots", []),
            "tools": _tool_names(last_response),
            "reply": last_response.get("reply", ""),
            "scores": {
                "intent": 0 if any(issue.startswith("intent=") for issue in issues) else 1,
                "tool_call": 0 if any("tool" in issue for issue in issues) else 1,
                "reply_constraints": 0 if any("text" in issue for issue in issues) else 1,
                "case": ok,
            },
        })

    report_dir = ROOT / "evals" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"sales_dialog_report_{int(time.time())}.json"
    report_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    for record in records:
        mark = "PASS" if record["passed"] else "FAIL"
        print(f"[{mark}] {record['id']} intent={record['intent']} tools={record['tools']}")
        for issue in record["issues"]:
            print(f"  - {issue}")
    print(f"\nScore: {passed}/{total}")
    print("Breakdown:")
    for key in ("intent", "tool_call", "reply_constraints", "case"):
        score = sum(record["scores"][key] for record in records)
        print(f"- {key}: {score}/{total}")
    print(f"Report: {report_path}")
    return 0 if passed == total else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--live", action="store_true", help="Require DeepSeek API credentials instead of mock fallback.")
    args = parser.parse_args()

    if args.live and not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required for --live DeepSeek evaluation.", file=sys.stderr)
        return 2

    try:
        return run_cases(args.base_url, args.cases)
    except urllib.error.URLError as exc:
        print(f"Cannot reach {args.base_url}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
