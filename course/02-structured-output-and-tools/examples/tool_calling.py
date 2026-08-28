"""Let a model request a read-only tool, then validate and execute the call."""

import argparse

from ai_course.langchain_basics import create_chat_model
from ai_course.settings import load_settings
from ai_course.structured_output import execute_tool_call, get_claim_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demonstrate a validated tool call.")
    parser.add_argument("question", help="Question that may require the claim-status tool")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = create_chat_model(load_settings())
    model_with_tools = model.bind_tools([get_claim_status])
    response = model_with_tools.invoke(args.question)

    if not response.tool_calls:
        print(response.content)
        return

    for tool_call in response.tool_calls:
        print(f"Requested tool: {tool_call['name']}")
        print(f"Validated result: {execute_tool_call(tool_call)}")


if __name__ == "__main__":
    main()
