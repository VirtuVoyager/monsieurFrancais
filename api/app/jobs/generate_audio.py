from app.db import SessionLocal
from app.services.audio import generate_missing
from app.services.users import get_or_create_learner


def main() -> None:
    with SessionLocal() as session:
        report = generate_missing(session, get_or_create_learner(session).id)
    print(
        f"Generated {report.generated} clips ({report.characters} characters); "
        f"{report.existing} already existed"
    )


if __name__ == "__main__":
    main()
