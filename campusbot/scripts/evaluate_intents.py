"""Measure how well the assistant recognises the held-out test phrases.

Each phrase in scripts/test_utterances.csv is sent to the assistant, and we check
whether the expected action/intent was triggered. Output: accuracy + a results CSV.

Usage:
    python scripts/evaluate_intents.py            # run the evaluation
    python scripts/evaluate_intents.py --raw "hello"   # print the raw API response for one phrase

NOTE: how the triggered action is reported can differ between assistant versions.
If accuracy shows 0%, run with --raw and adjust `triggered_names()` below to match
the response you see.
"""
import argparse
import csv
import json
import os

from dotenv import load_dotenv
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import AssistantV2

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_FILE = os.path.join(HERE, "test_utterances.csv")
RESULTS_FILE = os.path.join(HERE, "..", "docs", "evaluation_results.csv")


def build_client():
    load_dotenv()
    auth = IAMAuthenticator(os.environ["WATSONX_ASSISTANT_APIKEY"])
    client = AssistantV2(version="2023-06-15", authenticator=auth)
    client.set_service_url(os.environ["WATSONX_ASSISTANT_URL"])
    return client


def ask(client, text):
    return client.message_stateless(
        assistant_id=os.environ["WATSONX_ASSISTANT_ID"],
        environment_id=os.environ["WATSONX_ENVIRONMENT_ID"],
        input={"message_type": "text", "text": text, "options": {"debug": True}},
    ).get_result()


def triggered_names(result):
    """Collect lower-cased names of every action / intent the response mentions."""
    names = set()
    output = result.get("output", {})
    for intent in output.get("intents", []):
        names.add(intent.get("intent", "").lower())
    for event in output.get("debug", {}).get("turn_events", []):
        source = event.get("source", {})
        for key in ("action_title", "action"):
            if source.get(key):
                names.add(str(source[key]).lower())
    return names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", help="print the raw response for one phrase and exit")
    args = parser.parse_args()
    client = build_client()

    if args.raw:
        print(json.dumps(ask(client, args.raw), indent=2))
        return

    rows, correct = [], 0
    with open(TEST_FILE, newline="") as f:
        for row in csv.DictReader(f):
            names = triggered_names(ask(client, row["utterance"]))
            ok = row["expected_action"].lower() in names
            correct += ok
            rows.append({**row, "detected": "; ".join(sorted(names)), "correct": ok})
            print(f"[{'OK ' if ok else 'MISS'}] {row['utterance']!r} -> expected {row['expected_action']!r}")

    accuracy = 100 * correct / len(rows)
    print(f"\nAccuracy: {correct}/{len(rows)} = {accuracy:.1f}%")

    with open(RESULTS_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["utterance", "expected_action", "detected", "correct"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Details saved to {os.path.normpath(RESULTS_FILE)}")


if __name__ == "__main__":
    main()
