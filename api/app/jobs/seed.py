from app.config import get_settings
from app.db import SessionLocal
from app.services.content import seed


def main() -> None:
    with SessionLocal() as session:
        report = seed(session, get_settings().content_dir)
    print(
        f"Modules updated: {len(report.modules_updated)} {report.modules_updated}\n"
        f"Items created: {report.items_created}, versioned: {report.items_versioned}, "
        f"retired: {report.items_retired}"
    )


if __name__ == "__main__":
    main()
