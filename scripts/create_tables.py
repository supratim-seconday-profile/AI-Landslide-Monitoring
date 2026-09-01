from backend.app.database import engine, Base
from backend.app.models import RiskPrediction


print("========================================")
print("       CREATING DATABASE TABLES")
print("========================================")

Base.metadata.create_all(bind=engine)

print("Database tables created successfully.")
print("========================================")