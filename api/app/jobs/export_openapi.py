import json
import sys
from pathlib import Path

from app.main import create_app


def main() -> None:
    target = Path(sys.argv[1])
    target.write_text(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
