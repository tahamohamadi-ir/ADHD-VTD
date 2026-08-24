import argparse
import json
import sys
import uuid
import io


from src.graph.workflow import create_workflow
from src.graph.state import VTDState
from src.utils.logging import get_logger

# Ensure UTF-8 for Persian output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run ADHD-VTD Agentic Pipeline")
    parser.add_argument("question", type=str, help="User's question")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Create Workflow
    app = create_workflow()

    # Initial State
    initial_state = VTDState(trace_id=str(uuid.uuid4()), raw_question=args.question)

    # Run Graph
    logger.info("Starting Agentic Pipeline...")
    # Invoke with dictionary representation
    final_state_dict = app.invoke(initial_state.model_dump())

    # Result
    print("\n" + "=" * 60)
    print(f"QUESTION: {args.question}")
    print(f"FINAL ANSWER: {final_state_dict.get('final_answer')}")

    if args.verbose:
        attempts = final_state_dict.get("attempts") or []
        latest_attempt = attempts[-1] if attempts else {}
        if hasattr(latest_attempt, "model_dump"):
            latest_attempt = latest_attempt.model_dump()

        print("\n--- TRACE DETAILS ---")
        print(f"Intent: {final_state_dict.get('intent')}")
        print(f"Generated SQL: {final_state_dict.get('generated_sql')}")
        print(f"Retry Count: {final_state_dict.get('retry_count')}")
        print(f"Attempt Count: {len(attempts)}")
        print(
            f"Raw Model Response: {final_state_dict.get('raw_model_response') or latest_attempt.get('raw_model_response')}"
        )
        print(
            f"Parsed Payload: {json.dumps(final_state_dict.get('parsed_payload') or latest_attempt.get('parsed_payload'), ensure_ascii=False, default=str)}"
        )
        print(
            f"Validation Errors: {json.dumps(final_state_dict.get('validation_errors') or latest_attempt.get('validation_errors') or [], ensure_ascii=False, default=str)}"
        )

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
