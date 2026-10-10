
import os
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify

from extensions import db
from services.website_analyzer import analyze_website
from scheduler import start_scheduler


app = Flask(__name__)

# --------------------------------------------------
# DATABASE CONFIGURATION
# PostgreSQL (Neon) on Vercel
# SQLite for local development
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "pagepulse.db"

database_url = os.environ.get("DATABASE_URL", "").strip()

if database_url:
    # Explicitly select psycopg2 so SQLAlchemy does not
    # attempt to import the missing psycopg (version 3) driver.
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
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{DATABASE_PATH}"
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# Import models after initializing the SQLAlchemy extension.
from models.website import Website
from models.monitoring import MonitoringCheck
from models.incident import Incident


# Initialize tables on the first request handled by this process.
# This is important because Vercel imports the Flask app without
# executing the __main__ section.
_database_initialized = False


@app.before_request
def initialize_database():
    global _database_initialized

    if not _database_initialized:
        db.create_all()
        _database_initialized = True


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# CREATE WEBSITE
# --------------------------------------------------

@app.route("/api/websites", methods=["POST"])
def create_website():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    url = data.get("url", "").strip()

    if not name:
        return jsonify({
            "error": "Website name is required."
        }), 400

    if not url:
        return jsonify({
            "error": "Website URL is required."
        }), 400

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed_url = urlparse(url)

    if not parsed_url.netloc:
        return jsonify({
            "error": "Please enter a valid website URL."
        }), 400

    existing_website = Website.query.filter_by(
        url=url
    ).first()

    if existing_website:
        return jsonify({
            "error": "This website is already being monitored."
        }), 409

    website = Website(
        name=name,
        url=url
    )

    db.session.add(website)
    db.session.commit()

    return jsonify({
        "message": "Website added successfully.",
        "website": {
            "id": website.id,
            "name": website.name,
            "url": website.url,
            "active": website.active,
            "createdAt": website.created_at.isoformat()
        }
    }), 201


# --------------------------------------------------
# GET ALL WEBSITES
# --------------------------------------------------

@app.route("/api/websites", methods=["GET"])
def get_websites():
    websites = Website.query.order_by(
        Website.created_at.desc()
    ).all()

    return jsonify({
        "websites": [
            {
                "id": website.id,
                "name": website.name,
                "url": website.url,
                "active": website.active,
                "createdAt": website.created_at.isoformat()
            }
            for website in websites
        ]
    })


# --------------------------------------------------
# GET ONE WEBSITE
# --------------------------------------------------

@app.route(
    "/api/websites/<int:website_id>",
    methods=["GET"]
)
def get_website(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "error": "Website not found."
        }), 404

    return jsonify({
        "website": {
            "id": website.id,
            "name": website.name,
            "url": website.url,
            "active": website.active,
            "createdAt": website.created_at.isoformat()
        }
    })


# --------------------------------------------------
# DELETE WEBSITE
# --------------------------------------------------

@app.route(
    "/api/websites/<int:website_id>",
    methods=["DELETE"]
)
def delete_website(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "error": "Website not found."
        }), 404

    db.session.delete(website)
    db.session.commit()

    return jsonify({
        "message": "Website deleted successfully."
    })


# --------------------------------------------------
# UPDATE WEBSITE
# --------------------------------------------------

@app.route(
    "/api/websites/<int:website_id>",
    methods=["PUT"]
)
def update_website(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "error": "Website not found."
        }), 404

    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    url = data.get("url", "").strip()

    if not name:
        return jsonify({
            "error": "Website name is required."
        }), 400

    if not url:
        return jsonify({
            "error": "Website URL is required."
        }), 400

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed_url = urlparse(url)

    if not parsed_url.netloc:
        return jsonify({
            "error": "Please enter a valid website URL."
        }), 400

    existing_website = Website.query.filter(
        Website.url == url,
        Website.id != website_id
    ).first()

    if existing_website:
        return jsonify({
            "error": "Another website is already using this URL."
        }), 409

    website.name = name
    website.url = url

    db.session.commit()

    return jsonify({
        "message": "Website updated successfully.",
        "website": {
            "id": website.id,
            "name": website.name,
            "url": website.url,
            "active": website.active,
            "createdAt": website.created_at.isoformat()
        }
    })


# --------------------------------------------------
# WEBSITE AUDIT
# --------------------------------------------------

@app.route("/audit", methods=["POST"])
def audit():
    data = request.get_json(silent=True) or {}

    url = data.get("url", "").strip()

    if not url:
        return jsonify({
            "error": "Please enter a website URL."
        }), 400

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed_url = urlparse(url)

    if not parsed_url.netloc:
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

        end_time = time.perf_counter()

        response_time = round(
            (end_time - start_time) * 1000,
            2
        )

        content_type = response.headers.get(
            "Content-Type",
            ""
        )

        response_size = len(response.content)
        redirect_count = len(response.history)

        if "text/html" not in content_type.lower():
            return jsonify({
                "error": "This URL does not contain an HTML page.",
                "status": response.status_code,
                "responseTime": f"{response_time} ms",
                "contentType": content_type
            }), 400

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        title = "No Title"

        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        meta_description = soup.find(
            "meta",
            attrs={"name": "description"}
        )

        description = "No Description"

        if meta_description:
            description = meta_description.get(
                "content",
                "No Description"
            ).strip()

        h1_count = len(soup.find_all("h1"))

        page_text = soup.get_text(
            separator=" ",
            strip=True
        )

        word_count = len(page_text.split())

        images = soup.find_all("img")
        images_without_alt = 0

        for image in images:
            alt_text = image.get("alt")

            if not alt_text or not alt_text.strip():
                images_without_alt += 1

        links = soup.find_all("a")
        total_links = len(links)
        links_without_text = 0

        for link in links:
            link_text = link.get_text(strip=True)

            if not link_text:
                links_without_text += 1

        headers = {
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
            "responseSizeKB": round(
                response_size / 1024,
                2
            ),
            "redirectCount": redirect_count,
            "title": title,
            "description": description,
            "h1Count": h1_count,
            "wordCount": word_count,
            "totalImages": len(images),
            "imagesWithoutAlt": images_without_alt,
            "totalLinks": total_links,
            "linksWithoutText": links_without_text,
            "headers": headers
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

    except requests.exceptions.RequestException as error:
        return jsonify({
            "error": f"Website request failed: {str(error)}"
        }), 502

    except Exception:
        app.logger.exception("Website audit failed")
        return jsonify({
            "error": "Something went wrong while analyzing the website."
        }), 500


# --------------------------------------------------
# CHECK WEBSITE STATUS
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

        end_time = time.perf_counter()

        response_time = round(
            end_time - start_time,
            3
        )

        response_size = len(response.content)

        content_type = response.headers.get(
            "Content-Type",
            ""
        )

        server = response.headers.get(
            "Server",
            "Not Provided"
        )

        redirect_count = len(response.history)

        is_up = 200 <= response.status_code < 400

        check = MonitoringCheck(
            website_id=website.id,
            status_code=response.status_code,
            response_time=response_time,
            response_size=response_size,
            redirect_count=redirect_count,
            content_type=content_type,
            server=server,
            error_message=None,
            is_up=is_up
        )

        db.session.add(check)

        if is_up:
            open_incident = Incident.query.filter_by(
                website_id=website.id,
                status="OPEN"
            ).order_by(
                Incident.started_at.desc()
            ).first()

            if open_incident:
                open_incident.status = "RESOLVED"
                open_incident.resolved_at = datetime.utcnow()

        else:
            open_incident = Incident.query.filter_by(
                website_id=website.id,
                status="OPEN"
            ).first()

            if not open_incident:
                incident = Incident(
                    website_id=website.id,
                    reason=f"HTTP status {response.status_code}",
                    status="OPEN"
                )

                db.session.add(incident)

        db.session.commit()

        return jsonify({
            "message": "Website check completed successfully.",
            "check": {
                "id": check.id,
                "websiteId": website.id,
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
        }), 201

    except requests.RequestException as error:
        response_time = round(
            time.perf_counter() - start_time,
            3
        )

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
            incident = Incident(
                website_id=website.id,
                reason=str(error),
                status="OPEN"
            )

            db.session.add(incident)

        db.session.commit()

        return jsonify({
            "message": "Website check completed.",
            "check": {
                "id": check.id,
                "websiteId": website.id,
                "statusCode": None,
                "responseTime": check.response_time,
                "responseSize": None,
                "redirectCount": check.redirect_count,
                "contentType": None,
                "server": None,
                "errorMessage": check.error_message,
                "isUp": False,
                "checkedAt": check.checked_at.isoformat()
            },
            "error": str(error)
        }), 201


# --------------------------------------------------
# GET MONITORING CHECK HISTORY
# --------------------------------------------------

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
# GET WEBSITE INCIDENTS
# --------------------------------------------------

@app.route(
    "/api/websites/<int:website_id>/incidents",
    methods=["GET"]
)
def get_website_incidents(website_id):
    website = db.session.get(
        Website,
        website_id
    )

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
# ANALYZE A MONITORED WEBSITE
# --------------------------------------------------

@app.route(
    "/api/websites/<int:website_id>/analyze",
    methods=["POST"]
)
def analyze_monitored_website(website_id):
    website = db.session.get(
        Website,
        website_id
    )

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

        content_type = response.headers.get(
            "Content-Type",
            ""
        )

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

    except requests.exceptions.RequestException as error:
        return jsonify({
            "error": f"Website request failed: {str(error)}"
        }), 502

    except Exception:
        app.logger.exception("Website analysis failed")
        return jsonify({
            "error": "Something went wrong during website analysis."
        }), 500


# --------------------------------------------------
# WEBSITE ANALYTICS
# --------------------------------------------------

@app.route(
    "/api/websites/<int:website_id>/analytics",
    methods=["GET"]
)
def get_website_analytics(website_id):
    website = db.session.get(
        Website,
        website_id
    )

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
        1
        for check in checks
        if check.is_up
    )

    failed_checks = total_checks - successful_checks

    uptime_percentage = round(
        (successful_checks / total_checks) * 100,
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
        1
        for check in recent_checks
        if not check.is_up
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
                if latest_check
                else None
            ),
            "latestStatusCode": (
                latest_check.status_code
                if latest_check
                else None
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
# LOCAL DEVELOPMENT
# Vercel imports app.py and does not execute this block.
# --------------------------------------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    start_scheduler(app)

    app.run(
        debug=False,
        port=5000
    )