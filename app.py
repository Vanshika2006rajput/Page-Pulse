
import os
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from services.website_analyzer import analyze_website
from scheduler import start_scheduler


# --------------------------------------------------
# App configuration
# --------------------------------------------------

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "pagepulse.db"

database_url = os.environ.get("DATABASE_URL", "").strip()

if database_url:
    # Use psycopg2 explicitly to avoid the missing psycopg driver error.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql+psycopg2://",
            1
        )
    elif database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace(
            "postgresql+psycopg://",
            "postgresql+psycopg2://",
            1
        )
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+psycopg2://",
            1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

else:
    # SQLite is for local development only.
    if os.environ.get("VERCEL"):
        raise RuntimeError(
            "DATABASE_URL is missing in the Vercel environment."
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{DATABASE_PATH.as_posix()}"
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Prevent excessive idle connections in serverless deployments.
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_size": 2,
    "max_overflow": 0,
    "pool_recycle": 300,
}

db.init_app(app)


# Import models so SQLAlchemy knows all table definitions.
from models.website import Website
from models.monitoring import MonitoringCheck
from models.incident import Incident


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def normalize_url(value):
    """Normalize and validate a website URL."""
    if not isinstance(value, str):
        return None

    url = value.strip()

    if not url:
        return None

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)

    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or any(char.isspace() for char in url)
    ):
        return None

    return url


def website_to_dict(website):
    return {
        "id": website.id,
        "name": website.name,
        "url": website.url,
        "active": website.active,
        "createdAt": website.created_at.isoformat()
    }


def check_to_dict(check):
    return {
        "id": check.id,
        "websiteId": check.website_id,
        "statusCode": check.status_code,
        "responseTime": check.response_time,
        "responseSize": check.response_size,
        "redirectCount": check.redirect_count,
        "contentType": check.content_type,
        "server": check.server,
        "errorMessage": check.error_message,
        "isUp": check.is_up,
        "checkedAt": check.checked_at.isoformat()
    }


# --------------------------------------------------
# Home and health
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    """Check whether the app can connect to its configured database."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({
            "status": "ok",
            "database": "connected"
        }), 200

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Database health check failed")

        return jsonify({
            "status": "error",
            "database": "unavailable"
        }), 503


# --------------------------------------------------
# Website CRUD
# --------------------------------------------------

@app.route("/api/websites", methods=["POST"])
def create_website():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "")
    url_input = data.get("url", "")

    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "error": "Website name is required."
        }), 400

    if not isinstance(url_input, str) or not url_input.strip():
        return jsonify({
            "error": "Website URL is required."
        }), 400

    name = name.strip()
    url = normalize_url(url_input)

    if not url:
        return jsonify({
            "error": "Please enter a valid website URL."
        }), 400

    try:
        existing = Website.query.filter_by(url=url).first()

        if existing:
            return jsonify({
                "error": "This website is already being monitored."
            }), 409

        website = Website(name=name, url=url)

        db.session.add(website)
        db.session.commit()

        return jsonify({
            "message": "Website added successfully.",
            "website": website_to_dict(website)
        }), 201

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not create website")

        return jsonify({
            "error": "Could not save the website. Check the database configuration and schema."
        }), 500


@app.route("/api/websites", methods=["GET"])
def get_websites():
    try:
        websites = Website.query.order_by(
            Website.created_at.desc()
        ).all()

        return jsonify({
            "websites": [
                website_to_dict(website)
                for website in websites
            ]
        })

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not retrieve websites")

        return jsonify({
            "error": "Could not retrieve websites. Check the database schema and connection."
        }), 500


@app.route("/api/websites/<int:website_id>", methods=["GET"])
def get_website(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "error": "Website not found."
        }), 404

    return jsonify({
        "website": website_to_dict(website)
    })


@app.route("/api/websites/<int:website_id>", methods=["PUT"])
def update_website(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "error": "Website not found."
        }), 404

    data = request.get_json(silent=True) or {}

    name = data.get("name", "")
    url_input = data.get("url", "")

    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "error": "Website name is required."
        }), 400

    if not isinstance(url_input, str) or not url_input.strip():
        return jsonify({
            "error": "Website URL is required."
        }), 400

    url = normalize_url(url_input)

    if not url:
        return jsonify({
            "error": "Please enter a valid website URL."
        }), 400

    existing = Website.query.filter(
        Website.url == url,
        Website.id != website_id
    ).first()

    if existing:
        return jsonify({
            "error": "Another website is already using this URL."
        }), 409

    try:
        website.name = name.strip()
        website.url = url

        db.session.commit()

        return jsonify({
            "message": "Website updated successfully.",
            "website": website_to_dict(website)
        })

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not update website")

        return jsonify({
            "error": "Could not update the website."
        }), 500


@app.route("/api/websites/<int:website_id>", methods=["DELETE"])
def delete_website(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "error": "Website not found."
        }), 404

    try:
        # Delete dependent rows first in case the models don't
        # define database-level cascading deletes.
        MonitoringCheck.query.filter_by(
            website_id=website.id
        ).delete(synchronize_session=False)

        Incident.query.filter_by(
            website_id=website.id
        ).delete(synchronize_session=False)

        db.session.delete(website)
        db.session.commit()

        return jsonify({
            "message": "Website deleted successfully."
        })

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not delete website")

        return jsonify({
            "error": "Could not delete the website."
        }), 500


# --------------------------------------------------
# Website audit
# --------------------------------------------------

@app.route("/audit", methods=["POST"])
def audit():
    data = request.get_json(silent=True) or {}
    url_input = data.get("url", "")

    if not isinstance(url_input, str) or not url_input.strip():
        return jsonify({
            "error": "Please enter a website URL."
        }), 400

    url = normalize_url(url_input)

    if not url:
        return jsonify({
            "error": "Please enter a valid website URL."
        }), 400

    try:
        start_time = time.perf_counter()

        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "PagePulse/1.0 Website Monitor"
            },
            allow_redirects=True
        )

        response_time = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        content_type = response.headers.get("Content-Type", "")
        response_size = len(response.content)
        redirect_count = len(response.history)

        if "text/html" not in content_type.lower():
            return jsonify({
                "error": "This URL does not contain an HTML page.",
                "status": response.status_code,
                "responseTime": f"{response_time} ms",
                "contentType": content_type
            }), 400

        soup = BeautifulSoup(response.text, "html.parser")

        title = (
            soup.title.get_text(strip=True)
            if soup.title
            else "No Title"
        )

        meta_description = soup.find(
            "meta",
            attrs={"name": "description"}
        )

        description = (
            meta_description.get("content", "").strip()
            if meta_description
            else "No Description"
        )

        images = soup.find_all("img")
        links = soup.find_all("a")

        images_without_alt = sum(
            1 for image in images
            if not image.get("alt", "").strip()
        )

        links_without_text = sum(
            1 for link in links
            if not link.get_text(strip=True)
        )

        page_text = soup.get_text(separator=" ", strip=True)

        if 200 <= response.status_code < 300:
            status_category = "Success"
        elif 300 <= response.status_code < 400:
            status_category = "Redirect"
        elif 400 <= response.status_code < 500:
            status_category = "Client Error"
        elif 500 <= response.status_code < 600:
            status_category = "Server Error"
        else:
            status_category = "Unknown"

        return jsonify({
            "url": url,
            "status": response.status_code,
            "statusCategory": status_category,
            "responseTime": f"{response_time} ms",
            "responseTimeMs": response_time,
            "contentType": content_type,
            "responseSize": response_size,
            "responseSizeKB": round(response_size / 1024, 2),
            "redirectCount": redirect_count,
            "title": title,
            "description": description,
            "h1Count": len(soup.find_all("h1")),
            "wordCount": len(page_text.split()),
            "totalImages": len(images),
            "imagesWithoutAlt": images_without_alt,
            "totalLinks": len(links),
            "linksWithoutText": links_without_text,
            "headers": {
                "contentType": content_type,
                "server": response.headers.get(
                    "Server",
                    "Not Provided"
                ),
                "contentLength": response.headers.get(
                    "Content-Length",
                    str(response_size)
                )
            }
        })

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "The website took too long to respond."
        }), 408

    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "Could not connect to the website."
        }), 400

    except requests.exceptions.InvalidURL:
        return jsonify({
            "error": "Invalid website URL."
        }), 400

    except requests.exceptions.RequestException:
        app.logger.exception("Website audit request failed")

        return jsonify({
            "error": "The website request failed."
        }), 502


# --------------------------------------------------
# Monitoring checks and incidents
# --------------------------------------------------

@app.route(
    "/api/websites/<int:website_id>/check",
    methods=["POST"]
)
def check_website(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "error": "Website not found."
        }), 404

    start_time = time.perf_counter()

    try:
        response = requests.get(
            website.url,
            timeout=10,
            allow_redirects=True,
            headers={
                "User-Agent": "PagePulse/1.0 Website Monitor"
            }
        )

        response_time = round(
            time.perf_counter() - start_time,
            3
        )

        content_type = response.headers.get("Content-Type", "")
        is_up = 200 <= response.status_code < 400

        check = MonitoringCheck(
            website_id=website.id,
            status_code=response.status_code,
            response_time=response_time,
            response_size=len(response.content),
            redirect_count=len(response.history),
            content_type=content_type,
            server=response.headers.get("Server", "Not Provided"),
            error_message=None,
            is_up=is_up
        )

        db.session.add(check)

        open_incident = Incident.query.filter_by(
            website_id=website.id,
            status="OPEN"
        ).order_by(
            Incident.started_at.desc()
        ).first()

        if is_up:
            if open_incident:
                open_incident.status = "RESOLVED"
                open_incident.resolved_at = datetime.utcnow()

        elif not open_incident:
            db.session.add(Incident(
                website_id=website.id,
                reason=f"HTTP status {response.status_code}",
                status="OPEN"
            ))

        db.session.commit()

        return jsonify({
            "message": "Website check completed successfully.",
            "check": check_to_dict(check)
        }), 201

    except requests.exceptions.RequestException as error:
        response_time = round(
            time.perf_counter() - start_time,
            3
        )

        try:
            check = MonitoringCheck(
                website_id=website.id,
                status_code=None,
                response_time=response_time,
                response_size=None,
                redirect_count=0,
                content_type=None,
                server=None,
                error_message=str(error),
                is_up=False
            )

            db.session.add(check)

            open_incident = Incident.query.filter_by(
                website_id=website.id,
                status="OPEN"
            ).first()

            if not open_incident:
                db.session.add(Incident(
                    website_id=website.id,
                    reason=str(error),
                    status="OPEN"
                ))

            db.session.commit()

            return jsonify({
                "message": "Website check completed.",
                "check": check_to_dict(check),
                "error": str(error)
            }), 201

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Could not save failed website check")

            return jsonify({
                "error": "The website request failed and its check could not be saved."
            }), 500

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not save website check")

        return jsonify({
            "error": "Could not save the website check."
        }), 500


@app.route(
    "/api/websites/<int:website_id>/checks",
    methods=["GET"]
)
def get_website_checks(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "error": "Website not found."
        }), 404

    checks = MonitoringCheck.query.filter_by(
        website_id=website.id
    ).order_by(
        MonitoringCheck.checked_at.desc()
    ).all()

    return jsonify({
        "website": {
            "id": website.id,
            "name": website.name,
            "url": website.url
        },
        "checks": [
            check_to_dict(check)
            for check in checks
        ]
    })


@app.route(
    "/api/websites/<int:website_id>/incidents",
    methods=["GET"]
)
def get_website_incidents(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "error": "Website not found."
        }), 404

    incidents = Incident.query.filter_by(
        website_id=website.id
    ).order_by(
        Incident.started_at.desc()
    ).all()

    return jsonify({
        "website": {
            "id": website.id,
            "name": website.name,
            "url": website.url
        },
        "incidents": [
            {
                "id": incident.id,
                "status": incident.status,
                "reason": incident.reason,
                "startedAt": incident.started_at.isoformat(),
                "resolvedAt": (
                    incident.resolved_at.isoformat()
                    if incident.resolved_at
                    else None
                )
            }
            for incident in incidents
        ]
    })


# --------------------------------------------------
# Detailed website analysis
# --------------------------------------------------

@app.route(
    "/api/websites/<int:website_id>/analyze",
    methods=["POST"]
)
def analyze_monitored_website(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "error": "Website not found."
        }), 404

    try:
        response = requests.get(
            website.url,
            timeout=10,
            allow_redirects=True,
            headers={
                "User-Agent": "PagePulse/1.0 Website Analyzer"
            }
        )

        content_type = response.headers.get("Content-Type", "")

        if "text/html" not in content_type.lower():
            return jsonify({
                "error": "This website does not return an HTML page."
            }), 400

        analysis = analyze_website(
            response.text,
            response.url
        )

        return jsonify({
            "website": {
                "id": website.id,
                "name": website.name,
                "url": website.url
            },
            "analysis": analysis
        })

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "The website took too long to respond."
        }), 408

    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "Could not connect to the website."
        }), 400

    except requests.exceptions.RequestException:
        app.logger.exception("Website analysis request failed")

        return jsonify({
            "error": "The website request failed."
        }), 502

    except Exception:
        app.logger.exception("Website analysis failed")

        return jsonify({
            "error": "Something went wrong during website analysis."
        }), 500


# --------------------------------------------------
# Analytics
# --------------------------------------------------

@app.route(
    "/api/websites/<int:website_id>/analytics",
    methods=["GET"]
)
def get_website_analytics(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "error": "Website not found."
        }), 404

    checks = MonitoringCheck.query.filter_by(
        website_id=website.id
    ).order_by(
        MonitoringCheck.checked_at.asc()
    ).all()

    total_checks = len(checks)

    successful_checks = sum(
        1 for check in checks if check.is_up
    )

    failed_checks = total_checks - successful_checks

    uptime_percentage = round(
        successful_checks / total_checks * 100,
        2
    ) if total_checks else 0

    response_times = [
        check.response_time
        for check in checks
        if check.response_time is not None
    ]

    response_sizes = [
        check.response_size
        for check in checks
        if check.response_size is not None
    ]

    average_response_time = round(
        sum(response_times) / len(response_times),
        3
    ) if response_times else 0

    average_response_size = round(
        sum(response_sizes) / len(response_sizes)
    ) if response_sizes else 0

    latest_check = checks[-1] if checks else None
    recent_checks = checks[-5:]

    recent_failures = sum(
        1 for check in recent_checks if not check.is_up
    )

    total_redirects = sum(
        check.redirect_count or 0
        for check in checks
    )

    if total_checks == 0:
        health_score = 0
        health_status = "No Data"
    else:
        health_score = round(uptime_percentage)

        if health_score >= 90:
            health_status = "Excellent"
        elif health_score >= 75:
            health_status = "Good"
        elif health_score >= 50:
            health_status = "Needs Improvement"
        else:
            health_status = "Poor"

    return jsonify({
        "website": {
            "id": website.id,
            "name": website.name,
            "url": website.url
        },
        "analytics": {
            "totalChecks": total_checks,
            "successfulChecks": successful_checks,
            "failedChecks": failed_checks,
            "uptimePercentage": uptime_percentage,
            "averageResponseTime": average_response_time,
            "averageResponseSize": average_response_size,
            "latestResponseTime": (
                latest_check.response_time
                if latest_check else None
            ),
            "latestStatusCode": (
                latest_check.status_code
                if latest_check else None
            ),
            "recentFailures": recent_failures,
            "totalRedirects": total_redirects,
            "healthScore": health_score,
            "healthStatus": health_status
        },
        "history": [
            {
                "id": check.id,
                "statusCode": check.status_code,
                "responseTime": check.response_time,
                "responseSize": check.response_size,
                "redirectCount": check.redirect_count,
                "contentType": check.content_type,
                "server": check.server,
                "errorMessage": check.error_message,
                "isUp": check.is_up,
                "checkedAt": check.checked_at.isoformat()
            }
            for check in checks
        ]
    })


# --------------------------------------------------
# Local development only
# --------------------------------------------------

if __name__ == "__main__":
    # Create tables locally, once when launching the development app.
    # Do not run schema creation on every Vercel request.
    with app.app_context():
        db.create_all()

    start_scheduler(app)

    app.run(
        debug=False,
        host="127.0.0.1",
        port=5000
    )