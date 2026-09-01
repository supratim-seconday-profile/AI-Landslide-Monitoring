from backend.app.database import engine

try:
    with engine.connect() as connection:
        print("========================================")
        print("     POSTGRESQL CONNECTION SUCCESS")
        print("========================================")
        print("Database connection is working.")
except Exception as e:
    print("========================================")
    print("     POSTGRESQL CONNECTION FAILED")
    print("========================================")
    print(e)