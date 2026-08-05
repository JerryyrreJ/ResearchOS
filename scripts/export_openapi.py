import json
from pathlib import Path

from researchos.api.main import create_app


def main() -> None:
    destination = Path("contracts/openapi/researchos-v1.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = create_app().openapi()
    destination.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(destination)


if __name__ == "__main__":
    main()
