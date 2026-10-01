from app.db import SessionLocal
from app.services.glossary import build_modules
from app.services.users import get_or_create_learner


def main() -> None:
    with SessionLocal() as session:
        report = build_modules(session, get_or_create_learner(session).id)
    print(f"Glossaries built: {len(report.built)} {report.built}; unchanged: {report.unchanged}")


if __name__ == "__main__":
    main()
