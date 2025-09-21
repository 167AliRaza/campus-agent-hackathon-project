import os
from pymongo import MongoClient
from contextlib import contextmanager
from dotenv import load_dotenv
load_dotenv()

# @contextmanager
# def get_db_client():
#     """Provides a MongoDB client connection using a context manager."""
#     client = None
#     try:
#         client = MongoClient(os.getenv("MONGODB_URI"))
#         print("Connected to the database successfully")
#         yield client
#     except Exception as e:
#         print(f"Error connecting to the database: {e}")
#         raise # Re-raise to let the caller handle it
#     finally:
#         if client:
#             client.close()
#             print("Database connection closed")


from pymongo import MongoClient # type: ignore
from dotenv import load_dotenv
load_dotenv()

def get_db_client():
    try:
        client = MongoClient(os.getenv("MONGODB_URI"))
        print("Connected to the database successfully")
        return client
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None