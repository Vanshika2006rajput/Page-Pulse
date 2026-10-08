from datetime import datetime
from extensions import db


class Website(db.Model):
    __tablename__ = "websites"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    url = db.Column(db.String(500), nullable=False, unique=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    checks = db.relationship(
        "MonitoringCheck",
        backref="website",
        lazy=True,
        cascade="all, delete-orphan"
    )