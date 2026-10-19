
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from backend.extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now
    )

    complaints = db.relationship(
        "Complaint",
        back_populates="user",
        lazy=True,
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }


class Complaint(db.Model):
    __tablename__ = "complaints"

    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(
        db.String(30), unique=True, nullable=False, index=True
    )
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)

    status = db.Column(
        db.String(30), nullable=False, default="Pending", index=True
    )

    location_text = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    user = db.relationship("User", back_populates="complaints")

    def to_dict(self):
        return {
            "id": self.id,
            "reference_number": self.reference_number,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "location_text": self.location_text,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "image_url": self.image_url,
            "user_id": self.user_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }
