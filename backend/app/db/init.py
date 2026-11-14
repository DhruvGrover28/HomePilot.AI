from app.db.models import Base
from app.db.session import engine


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
