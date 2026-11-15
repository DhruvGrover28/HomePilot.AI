from app.db.models import Base
from app.db.session import engine
from app.db.migrations import apply_additive_migrations


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    apply_additive_migrations()
