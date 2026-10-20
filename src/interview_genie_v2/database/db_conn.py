from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlmodel import Session

SERVER = r"localhost\SQLEXPRESS"
DATABASE = "interviewgenie"
DRIVER = "ODBC Driver 18 for SQL Server"

_odbc_params = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;")

DATABASE_URL = "mssql+pyodbc:///?odbc_connect=" + quote_plus(_odbc_params)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def get_session():
    with Session(engine) as session:
        yield session