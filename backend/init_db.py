
from backend.app import app, db
import models  # Registers the User and Complaint models


with app.app_context():
    db.create_all()
    print("JalSetu database tables created successfully.")

    print("Tables found:")
    for table_name in db.metadata.tables:
        print(f"- {table_name}")
