from datetime import datetime
from extensions import db


class MonitoringCheck(db.Model):
    __tablename__ = "monitoring_checks"

    id = db.Column(db.Integer, primary_key=True)

    website_id = db.Column(
        db.Integer,
        db.ForeignKey("websites.id"),
        nullable=False
    )

    status_code = db.Column(db.Integer, nullable=True)

    response_time = db.Column(
        db.Float,
        nullable=True
    )

    response_size = db.Column(
        db.Integer,
        nullable=True
    )

    redirect_count = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    content_type = db.Column(
        db.String(200),
        nullable=True
    )

    server = db.Column(
        db.String(200),
        nullable=True
    )

    error_message = db.Column(
        db.Text,
        nullable=True
    )

    is_up = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    checked_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )