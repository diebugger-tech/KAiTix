from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from app.models import *
from app.core.database import Base

engine = create_engine("sqlite:///:memory:")
try:
    Base.metadata.create_all(engine)
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
