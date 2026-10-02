from app.db import SessionLocal
from app.services.audio import generate_notes


def main() -> None:
    with SessionLocal() as session:
        report = generate_notes(session)
    print(
        f"Generated {report.generated} class-note clips ({report.characters} characters); "
        f"{report.existing} already existed"
    )


if __name__ == "__main__":
    main()
