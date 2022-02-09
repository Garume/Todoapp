from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

Base = declarative_base()
ROB_PATH = "sqlite:///db.sqlite3"
ECHO_LOG = True

engine = create_engine(
    ROB_PATH,echo=ECHO_LOG  
)

Session = sessionmaker(bind=engine)
session = Session()