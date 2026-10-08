from datetime import datetime
from extensions import db


class Incident(db.Model):
    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)

    website_id = db.Column(
        db.Integer,
        db.ForeignKey("websites.id"),
        nullable=False
    )

    started_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    resolved_at = db.Column(
        db.DateTime,
        nullable=True
    )

    reason = db.Column(
        db.Text,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="OPEN"
    )

    website = db.relationship(
        "Website",
        backref=db.backref(
            "incidents",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )