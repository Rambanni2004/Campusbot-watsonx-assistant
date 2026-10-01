"""Chat with your watsonx Assistant from the terminal (handy for quick testing).

Usage:  python scripts/chat_cli.py
Needs the variables from .env (see .env.example).
"""
import os

from dotenv import load_dotenv
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import AssistantV2


def build_client():
    load_dotenv()
    auth = IAMAuthenticator(os.environ["WATSONX_ASSISTANT_APIKEY"])
    client = AssistantV2(version="2023-06-15", authenticator=auth)
    client.set_service_url(os.environ["WATSONX_ASSISTANT_URL"])
    return client


def print_reply(result):
    for item in result.get("output", {}).get("generic", []):
        if item.get("response_type") == "text":
            print(f"Bot: {item['text']}")
        elif item.get("response_type") == "option":
            print(f"Bot: {item.get('title', '')}")
            for opt in item.get("options", []):
                print(f"   - {opt['label']}")


def main():
    client = build_client()
    assistant_id = os.environ["WATSONX_ASSISTANT_ID"]
    env_id = os.environ["WATSONX_ENVIRONMENT_ID"]
    session_id = client.create_session(assistant_id=assistant_id, environment_id=env_id).get_result()["session_id"]
    print("CampusBot CLI. Type 'quit' to exit.\n")
    try:
        while True:
            text = input("You: ").strip()
            if text.lower() in {"quit", "exit"}:
                break
            if not text:
                continue
            result = client.message(
                assistant_id=assistant_id,
                environment_id=env_id,
                session_id=session_id,
                input={"message_type": "text", "text": text},
            ).get_result()
            print_reply(result)
    finally:
        client.delete_session(assistant_id=assistant_id, environment_id=env_id, session_id=session_id)


if __name__ == "__main__":
    main()
