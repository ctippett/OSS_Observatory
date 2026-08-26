import json
import sys
from pathlib import Path

from jsonschema import ValidationError, validate


# Resolve relative to this script's own location (repo-root/validators/), not the
# caller's current working directory, so this works regardless of where/how it is invoked
# (e.g. from a scheduled-task session whose cwd is unpredictable).
SCHEMA_FILE = Path(__file__).resolve().parent.parent / "schemas" / "cyberbrief.schema.json"


def load_json(file_path: Path) -> dict:
    """Load a JSON file and return its contents as a Python dictionary."""
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_cyberbrief(brief_file: Path) -> bool:
    """Validate a CyberBrief JSON file against the CyberBrief schema."""
    schema = load_json(SCHEMA_FILE)
    cyberbrief = load_json(brief_file)

    validate(
        instance=cyberbrief,
        schema=schema,
    )

    return True


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python validators/cyberbrief_validator.py "
            "cyberbriefs/<filename>.json"
        )
        raise SystemExit(1)

    brief_file = Path(sys.argv[1])

    if not brief_file.exists():
        print(f"ERROR: File not found: {brief_file}")
        raise SystemExit(1)

    try:
        validate_cyberbrief(brief_file)
    except json.JSONDecodeError as error:
        print(f"INVALID JSON: {error}")
        raise SystemExit(1)
    except ValidationError as error:
        print("CYBERBRIEF FAILED VALIDATION")
        print(f"Reason: {error.message}")

        if error.absolute_path:
            location = " -> ".join(str(part) for part in error.absolute_path)
            print(f"Location: {location}")

        raise SystemExit(1)

    print("CYBERBRIEF PASSED VALIDATION")


if __name__ == "__main__":
    main()
    