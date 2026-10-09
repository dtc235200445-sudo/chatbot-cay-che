import os
from database.connection import engine
from database.models import Base

def init_db():
    print("Creating all database tables if they do not exist...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    init_db()
