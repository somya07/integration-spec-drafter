"""
Integration Spec Drafter
-------------------------
Given a plain-English integration requirement and reference field lists for
two systems, this agent plans the integration and drafts two documents:
  - integration_spec.md      (technical spec for engineers)
  - stakeholder_summary.md   (plain-English summary for business stakeholders)

Usage:
    export ANTHROPIC_API_KEY=your_key_here
    python agent.py
"""

import os
from pathlib import Path

from deepagents import create_deep_agent

SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"
OUTPUT_DIR = Path(__file__).parent / "output"

SYSTEM_PROMPT = """You are an integration engineer. Given a plain-English business
requirement for a system integration, and reference field lists for the two systems
involved, do the following:

1. Plan the integration: identify the trigger event, the fields that need to map
   between systems, error/retry handling, and what should be logged.
2. Read the provided reference field list files to ground your field mapping in
   the fields that actually exist.
3. Write two files:
   - integration_spec.md: a technical spec (trigger, field mapping table,
     error handling, logging plan) an engineer could build directly from.
   - stakeholder_summary.md: a plain-English explanation of what the integration
     does and why, written the way you'd present it to a non-technical
     stakeholder before building it.

Be concrete. Use the actual field names from the reference files in your mapping.
"""


def read_reference_files() -> dict:
    files = {}
    for path in SAMPLE_DATA_DIR.glob("*.txt"):
        files[path.name] = path.read_text()
    return files


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running this script.")

    requirement = (
        "When a new order is created in the Orders system, update stock in the "
        "Warehouse system and notify the fulfillment team by email."
    )

    reference_files = read_reference_files()

    agent = create_deep_agent(
        model="claude-sonnet-4-6",
        system_prompt=SYSTEM_PROMPT,
    )

    # Seed the agent's virtual filesystem with the reference field lists.
    # Files live in the agent's state as dict[str, FileData], where FileData
    # is {"content": str, "encoding": "utf-8"}.
    files_payload = {
        f"/{name}": {"content": content, "encoding": "utf-8"}
        for name, content in reference_files.items()
    }

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Requirement: {requirement}\n\n"
                    f"Reference files provided: {list(reference_files.keys())}. "
                    "Write your two output files as /integration_spec.md and "
                    "/stakeholder_summary.md.",
                }
            ],
            "files": files_payload,
        }
    )

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Deep agents returns the full virtual filesystem (input + any new files)
    # in result["files"] as dict[str, FileData].
    all_files = result.get("files", {})
    written_files = {
        name: data for name, data in all_files.items() if name.lstrip("/") not in reference_files
    }

    for name, data in written_files.items():
        out_path = OUTPUT_DIR / name.lstrip("/")
        out_path.write_text(data["content"])
        print(f"Wrote {out_path}")

    if not written_files:
        print("No new files were written. Full file listing for debugging:")
        print(list(all_files.keys()))


if __name__ == "__main__":
    main()
