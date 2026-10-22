from pathlib import Path
from io import BytesIO

import os
import re

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from PIL import Image, UnidentifiedImageError
from backend.extensions import db, jwt

load_dotenv(Path(__file__).resolve().parent / ".env")



def create_app():
    app = Flask(__name__)

    database_url = os.getenv("DATABASE_URL")
    jwt_secret = os.getenv("JWT_SECRET_KEY")

    if not database_url:
        raise RuntimeError("DATABASE_URL is required.")

    if not jwt_secret:
        raise RuntimeError("JWT_SECRET_KEY is required.")

    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=jwt_secret,
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    )

    db.init_app(app)
    jwt.init_app(app)

    origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:8080,http://localhost:5173"
        ).split(",")
        if origin.strip()
    ]

    CORS(app, resources={r"/api/*": {"origins": origins}})

    @app.get("/api")
    def api_info():
        return jsonify({
            "name": "JalSetu API",
            "version": "1.0.0",
            "message": "Smart Water Supply Management System",
        })

    @app.get("/api/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({
                "status": "ok",
                "database": "connected",
                "application": "JalSetu",
            })
        except Exception:
            app.logger.exception("Database health check failed")
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": "Database unavailable",
            }), 503

    @app.post("/api/auth/register")
    def register():
        data = request.get_json(silent=True) or {}

        full_name = str(data.get("full_name", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        password = data.get("password", "")

        if not full_name or len(full_name) > 120:
            return jsonify({"error": "Enter a valid full name."}), 400

        if not email or len(email) > 255 or not re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+", email
        ):
            return jsonify({"error": "Enter a valid email address."}), 400

        if not isinstance(password, str) or len(password) < 8:
            return jsonify({
                "error": "Password must contain at least 8 characters."
            }), 400

        if len(password) > 128:
            return jsonify({"error": "Password is too long."}), 400

       
        from backend.models import User

        if User.query.filter_by(email=email).first():
            return jsonify({
                "error": "An account with this email already exists."
            }), 409

        user = User(full_name=full_name, email=email, role="user")
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({
                "error": "An account with this email already exists."
            }), 409

        return jsonify({
            "message": "Account created successfully.",
            "user": user.to_dict(),
        }), 201

    @app.post("/api/auth/login")
    def login():
        from backend.models import User

        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip().lower()
        password = data.get("password", "")

        if not email or not isinstance(password, str):
            return jsonify({
                "error": "Email and password are required."
            }), 400

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid email or password."}), 401

        access_token = create_access_token(identity=str(user.id))

        return jsonify({
            "message": "Login successful.",
            "access_token": access_token,
            "user": user.to_dict(),
        }), 200

    @app.get("/api/auth/me")
    @jwt_required()
    def current_user():
        from backend.models import User

        user_id = get_jwt_identity()
        user = db.session.get(User, int(user_id))

        if not user:
            return jsonify({"error": "User not found."}), 404

        return jsonify({"user": user.to_dict()}), 200


    @app.route("/api/complaints", methods=["GET", "POST"])
    @jwt_required()
    def complaints():
        from secrets import token_hex
        from backend.models import User, Complaint

        user_id = int(get_jwt_identity())
        user = db.session.get(User, user_id)

        if not user:
            return jsonify({"error": "User not found."}), 404

        if request.method == "GET":
            items = (
                Complaint.query
                .filter_by(user_id=user_id)
                .order_by(Complaint.created_at.desc())
                .all()
            )
            return jsonify({
                "complaints": [item.to_dict() for item in items]
            }), 200

        data = request.form if request.mimetype == "multipart/form-data" else (request.get_json(silent=True) or {})
        uploaded_image = request.files.get("image") if request.mimetype == "multipart/form-data" else None
        saved_image_path = None

        title = str(data.get("title", "")).strip()
        description = str(data.get("description", "")).strip()
        category = str(data.get("category", "")).strip()
        location_text = str(data.get("location_text", "")).strip()
        image_url = None  # Images must pass the validated upload flow.

        if not title or len(title) > 150:
            return jsonify({"error": "Enter a title of up to 150 characters."}), 400

        if not description or len(description) > 5000:
            return jsonify({"error": "Description is required (maximum 5000 characters)."}), 400

        valid_categories = {
            "Water Supply",
            "No Water Supply",
            "Low Water Pressure",
            "Water Leakage",
            "Pipeline Damage",
            "Water Quality",
            "Contaminated Water",
            "Billing",
            "Other",
        }

        if category not in valid_categories:
            return jsonify({"error": "Select a valid complaint category."}), 400

        if not location_text or len(location_text) > 255:
            return jsonify({"error": "Enter a location of up to 255 characters."}), 400

        if image_url and len(image_url) > 500:
            return jsonify({"error": "Image URL is too long."}), 400

        latitude = data.get("latitude")
        longitude = data.get("longitude")

        try:
            if latitude is not None:
                latitude = float(latitude)
                if not -90 <= latitude <= 90:
                    raise ValueError()
            if longitude is not None:
                longitude = float(longitude)
                if not -180 <= longitude <= 180:
                    raise ValueError()
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid latitude or longitude."}), 400

        # Validate and re-encode an optional image, removing embedded metadata.
        if uploaded_image and uploaded_image.filename:
            image_bytes = uploaded_image.read(4 * 1024 * 1024 + 1)
            if not image_bytes:
                return jsonify({"error": "The selected image is empty."}), 400
            if len(image_bytes) > 4 * 1024 * 1024:
                return jsonify({"error": "Image must be 4 MB or smaller."}), 413

            try:
                with Image.open(BytesIO(image_bytes)) as probe:
                    image_format = probe.format
                    probe.verify()

                extensions = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
                if image_format not in extensions:
                    return jsonify({"error": "Use a JPEG, PNG, or WebP image."}), 400

                with Image.open(BytesIO(image_bytes)) as image:
                    image.load()
                    if image_format == "JPEG" and image.mode not in ("RGB", "L"):
                        image = image.convert("RGB")

                    upload_dir = Path(__file__).resolve().parent / "uploads"
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    filename = token_hex(16) + "." + extensions[image_format]
                    saved_image_path = upload_dir / filename
                    image.save(saved_image_path, format=image_format)
                    image_url = filename

            except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
                return jsonify({"error": "The uploaded file is not a valid supported image."}), 400

        complaint = Complaint(
            reference_number="JS-" + token_hex(5).upper(),
            title=title,
            description=description,
            category=category,
            location_text=location_text,
            latitude=latitude,
            longitude=longitude,
            image_url=image_url,
            status="Pending",
            user_id=user_id,
        )

        try:
            db.session.add(complaint)
            db.session.commit()
        except Exception:
            db.session.rollback()
            if saved_image_path is not None:
                saved_image_path.unlink(missing_ok=True)
            app.logger.exception("Complaint creation failed")
            return jsonify({"error": "Could not save complaint."}), 500

        return jsonify({
            "message": "Complaint submitted successfully.",
            "complaint": complaint.to_dict(),
        }), 201

    # JALSETU_IMAGE_UPLOAD_PATCH: authenticated, owner-only image access.
    @app.get("/api/complaints/<string:reference_number>/image")
    @jwt_required()
    def complaint_image(reference_number):
        from backend.models import Complaint

        user_id = int(get_jwt_identity())
        complaint = Complaint.query.filter_by(
            reference_number=reference_number.strip().upper(),
            user_id=user_id,
        ).first()

        if not complaint or not complaint.image_url:
            return jsonify({"error": "Complaint image not found."}), 404

        filename = complaint.image_url
        allowed_types = {
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        extension = Path(filename).suffix.lower()
        if Path(filename).name != filename or extension not in allowed_types:
            return jsonify({"error": "Complaint image not found."}), 404

        image_path = Path(__file__).resolve().parent / "uploads" / filename
        if not image_path.is_file():
            return jsonify({"error": "Complaint image not found."}), 404

        return send_file(
            image_path,
            mimetype=allowed_types[extension],
            as_attachment=False,
            download_name=filename,
            conditional=True,
        )

    @app.get("/api/complaints/<string:reference_number>")
    @jwt_required()
    def track_complaint(reference_number):
        from backend.models import Complaint

        user_id = int(get_jwt_identity())
        complaint = Complaint.query.filter_by(
            reference_number=reference_number.strip().upper(),
            user_id=user_id,
        ).first()

        if not complaint:
            return jsonify({"error": "Complaint not found."}), 404

        return jsonify({"complaint": complaint.to_dict()}), 200


    # Admin API: every endpoint verifies the current user's database role.
    def get_admin_user():
        from backend.models import User

        identity = get_jwt_identity()
        try:
            user_id = int(identity)
        except (TypeError, ValueError):
            return None, (jsonify({"error": "Invalid user identity."}), 401)

        user = db.session.get(User, user_id)
        if user is None:
            return None, (jsonify({"error": "User not found."}), 404)

        if user.role != "admin":
            return None, (jsonify({"error": "Administrator access required."}), 403)

        return user, None

    @app.get("/api/admin/complaints")
    @jwt_required()
    def admin_list_complaints():
        from backend.models import Complaint

        admin, error_response = get_admin_user()
        if error_response:
            return error_response

        items = (
            Complaint.query
            .order_by(Complaint.created_at.desc())
            .all()
        )

        results = []
        for item in items:
            complaint_data = item.to_dict()
            complaint_data["reporter"] = (
                {
                    "id": item.user.id,
                    "full_name": item.user.full_name,
                    "email": item.user.email,
                }
                if item.user else None
            )
            results.append(complaint_data)

        return jsonify({"complaints": results}), 200

    # JALSETU_ADMIN_IMAGE_ROUTE: only authenticated administrators can view evidence.
    @app.get("/api/admin/complaints/<string:reference_number>/image")
    @jwt_required()
    def admin_complaint_image(reference_number):
        from backend.models import Complaint

        admin, error_response = get_admin_user()
        if error_response:
            return error_response

        complaint = Complaint.query.filter_by(
            reference_number=reference_number.strip().upper()
        ).first()

        if not complaint or not complaint.image_url:
            return jsonify({"error": "Complaint image not found."}), 404

        filename = complaint.image_url
        allowed_types = {
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        extension = Path(filename).suffix.lower()

        if Path(filename).name != filename or extension not in allowed_types:
            return jsonify({"error": "Complaint image not found."}), 404

        image_path = Path(__file__).resolve().parent / "uploads" / filename
        if not image_path.is_file():
            return jsonify({"error": "Complaint image file is missing."}), 404

        return send_file(
            image_path,
            mimetype=allowed_types[extension],
            as_attachment=False,
            download_name=filename,
            conditional=True,
        )

    @app.patch("/api/admin/complaints/<int:complaint_id>/status")
    @jwt_required()
    def admin_update_complaint_status(complaint_id):
        from backend.models import Complaint

        admin, error_response = get_admin_user()
        if error_response:
            return error_response

        data = request.get_json(silent=True) or {}
        submitted_status = data.get("status")

        allowed_statuses = {
            "pending": "Pending",
            "in progress": "In Progress",
            "resolved": "Resolved",
        }

        if not isinstance(submitted_status, str):
            return jsonify({
                "error": "Status must be Pending, In Progress, or Resolved."
            }), 400

        new_status = allowed_statuses.get(
            submitted_status.strip().lower()
        )
        if new_status is None:
            return jsonify({
                "error": "Invalid status. Use Pending, In Progress, or Resolved."
            }), 400

        complaint = db.session.get(Complaint, complaint_id)
        if complaint is None:
            return jsonify({"error": "Complaint not found."}), 404

        complaint.status = new_status

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Admin complaint status update failed")
            return jsonify({"error": "Could not update complaint status."}), 500

        return jsonify({
            "message": "Complaint status updated successfully.",
            "complaint": complaint.to_dict(),
        }), 200

    @app.get("/api/admin/stats")
    @jwt_required()
    def admin_dashboard_stats():
        from sqlalchemy import func
        from backend.models import User, Complaint

        admin, error_response = get_admin_user()
        if error_response:
            return error_response

        total_complaints = Complaint.query.count()
        total_users = User.query.count()

        status_rows = (
            db.session.query(
                func.lower(Complaint.status),
                func.count(Complaint.id),
            )
            .group_by(func.lower(Complaint.status))
            .all()
        )
        counts = {status: count for status, count in status_rows}

        pending = counts.get("pending", 0)
        in_progress = counts.get("in progress", 0)
        resolved = counts.get("resolved", 0)

        return jsonify({
            "stats": {
                "total_complaints": total_complaints,
                "pending": pending,
                "in_progress": in_progress,
                "resolved": resolved,
                "other_statuses": total_complaints - pending - in_progress - resolved,
                "total_users": total_users,
            }
        }), 200


    @app.post("/api/chat")
    def chatbot_support():
        data = request.get_json(silent=True) or {}
        message = data.get("message", "")

        if not isinstance(message, str) or not message.strip():
            return jsonify({"error": "Please enter a question."}), 400
        if len(message) > 1000:
            return jsonify({"error": "Please keep your question under 1000 characters."}), 400

        q = message.strip().lower()

        if any(word in q for word in ("contaminated", "dirty water", "unsafe water", "bad smell", "पानी गंदा", "दूषित पानी", "घाण पाणी")):
            answer = (
                "If water looks, smells, or tastes unusual, avoid drinking or cooking with it "
                "until your local water authority confirms it is safe. Use a known safe water "
                "source and report the issue through File a Complaint, choosing Water Quality "
                "or Contaminated Water. Seek local public-health advice if anyone feels unwell."
            )
        elif any(word in q for word in ("leak", "pipeline damage", "burst pipe", "लीकेज", "गळती")):
            answer = (
                "For a water leak or damaged pipeline, open Dashboard → File a Complaint, "
                "select Water Leakage or Pipeline Damage, describe the location, and add a photo "
                "if safe. Stay away from flooded electrical areas and dangerous road conditions."
            )
        elif any(word in q for word in ("low pressure", "pressure", "कम दबाव", "कमी दाब")):
            answer = (
                "For low water pressure, note your area, when the issue started, and whether "
                "neighbours are affected. File a complaint under Low Water Pressure and include "
                "those details so the responsible team can investigate."
            )
        elif any(word in q for word in ("no water", "water cut", "no supply", "पानी नहीं", "पाणी नाही")):
            answer = (
                "If there is no water supply, check whether the interruption affects nearby "
                "homes too. Submit a complaint under No Water Supply with your location and "
                "the approximate start time. JalSetu cannot confirm a live outage unless that "
                "information is provided by the responsible authority."
            )
        elif any(word in q for word in ("track", "status", "reference", "complaint number", "ट्रैक", "स्थिती")):
            answer = (
                "Open Dashboard → Track Complaint and enter the complaint reference number. "
                "Pending means it is awaiting action, In Progress means it is being handled, "
                "and Resolved means it has been marked resolved. If you cannot find your "
                "reference, check the confirmation shown when you submitted the complaint."
            )
        elif any(word in q for word in ("file", "submit", "new complaint", "report issue", "शिकायत", "तक्रार")):
            answer = (
                "Log in, open Dashboard, and use the complaint form. Enter a clear title, "
                "select the closest category, describe the issue, provide the location, and "
                "attach a relevant photo if available. Submit the form and keep the reference "
                "number for tracking."
            )
        elif any(word in q for word in ("login", "log in", "password", "register", "sign up", "account")):
            answer = (
                "Use Login if you already have an account, or Register to create one. "
                "If login fails, check your email and password. Never share your password "
                "or authentication token in this chat."
            )
        elif any(word in q for word in ("hello", "hi", "hey", "नमस्ते", "नमस्कार")):
            answer = (
                "Hello! I'm the JalSetu support assistant. I can guide you through filing "
                "and tracking complaints, account access, water supply interruptions, leaks, "
                "low pressure, and water quality concerns. What do you need help with?"
            )
        elif any(word in q for word in ("thank", "धन्यवाद")):
            answer = "You're welcome! Ask me if you need help filing or tracking a JalSetu complaint."
        else:
            answer = (
                "I can help with filing a complaint, tracking its status, login and registration, "
                "no water supply, low pressure, pipeline leakage, and water quality. Try asking "
                "about one of these topics. This first version uses predefined support guidance "
                "and does not yet use an AI model or access live complaint records."
            )

        return jsonify({"answer": answer}), 200

    return app


from backend import models

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)