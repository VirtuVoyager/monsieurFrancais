from app.db import SessionLocal
from app.services.knowledge import embed_pending
from app.services.users import get_or_create_learner


def main() -> None:
    with SessionLocal() as session:
        count = embed_pending(session, get_or_create_learner(session).id)
    print(f"Embedded {count} knowledge-base entries")


if __name__ == "__main__":
    main()
