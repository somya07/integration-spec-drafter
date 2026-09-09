import os
import dotenv
from pathlib import Path
from deepagents import create_deep_agent

dotenv.load_dotenv()

SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"
OUTPUT_DIR = Path(__file__).parent / "output"

SYSTEM_PROMPT = """
Act as an integration expert. Plan the integration with all details including trigger event, field mapping between systems, error handling. 
Read the reference field-list files given for actual field names and mapping.
Output two docs integration_spec.md and stakeholder_summary.md. 
integration_spec is a technical spec which is used by engineer to build integrations.
stakeholder_summary is a plain english version for non technical stakeholders.

"""

def read_reference_files() -> dict:
    files = {}
    for path in SAMPLE_DATA_DIR.glob("*.txt"):
        files[path.name] = path.read_text()
    return files

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY in your .env file before running this script.")

    requirement = """The orders comes from Ecommerce Platform.
    The order then should be added to our ERP. The order message payload would be integrated using Webhook.
    The order would have details like Order number, date requested, shipping address, billing address, ordered product sku with quantity.
    """

    reference_files= read_reference_files()

    agent= create_deep_agent(
        model="claude-haiku-4-5",
        system_prompt= SYSTEM_PROMPT
    )

    files_payload= {
        f"/{name}" : {"content":content,"encoding":"utf-8"}
        for name,content in reference_files.items()
    }

    result= agent.invoke(

        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Requirement: {requirement} \n\n"
                    f"Reference files provided: {list(reference_files.keys())}. "
                    "Write your two output files as /integration_spec.md and /stakeholder_summary.md"
                }
            ],
            "files": files_payload
        }
    )

    OUTPUT_DIR.mkdir(exist_ok=True)

    all_files= result.get("files",{})
    written_files= {
        name: data for name,data in all_files.items()
        if name.lstrip("/") not in reference_files
    }

    for name,data in written_files.items():
        out_path= OUTPUT_DIR/name.lstrip("/")
        out_path.write_text(data["content"],encoding="utf-8")
        print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
