from app.db import SessionLocal
from app.services.writing import grade_pending


def main() -> None:
    with SessionLocal() as session:
        print(f"Graded {grade_pending(session)} pending submissions")


if __name__ == "__main__":
    main()
