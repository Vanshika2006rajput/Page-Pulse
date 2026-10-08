import time
import threading
import requests
from datetime import datetime
from extensions import db
from models.website import Website
from models.monitoring import MonitoringCheck
from models.incident import Incident


MONITORING_INTERVAL = 60


def check_website(website):
    start_time = time.perf_counter()

    try:
        response = requests.get(
            website.url,
            timeout=10,
            allow_redirects=True,
            headers={
                "User-Agent": "PagePulse/1.0 Automated Monitor"
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

        update_incident_status(
            website,
            is_up,
            f"HTTP status {response.status_code}"
        )

        db.session.commit()

        print(
            f"[{datetime.now().isoformat()}] "
            f"{website.name} - "
            f"{'UP' if is_up else 'DOWN'} - "
            f"{response.status_code}"
        )

    except requests.RequestException as error:
        end_time = time.perf_counter()

        response_time = round(
            end_time - start_time,
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

        update_incident_status(
            website,
            False,
            str(error)
        )

        db.session.commit()

        print(
            f"[{datetime.now().isoformat()}] "
            f"{website.name} - DOWN - "
            f"{str(error)}"
        )


def update_incident_status(
    website,
    is_up,
    reason
):
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

    else:
        if not open_incident:
            incident = Incident(
                website_id=website.id,
                reason=reason,
                status="OPEN"
            )

            db.session.add(incident)


def run_monitoring_cycle(app):
    with app.app_context():
        websites = Website.query.filter_by(
            active=True
        ).all()

        print(
            f"[{datetime.now().isoformat()}] "
            f"Monitoring {len(websites)} active website(s)"
        )

        for website in websites:
            check_website(website)


def monitoring_loop(app):
    while True:
        try:
            run_monitoring_cycle(app)
        except Exception as error:
            print(
                f"[{datetime.now().isoformat()}] "
                f"Monitoring error: {error}"
            )

        time.sleep(MONITORING_INTERVAL)


def start_scheduler(app):
    scheduler_thread = threading.Thread(
        target=monitoring_loop,
        args=(app,),
        daemon=True
    )

    scheduler_thread.start()

    print(
        f"Page Pulse automatic monitoring started. "
        f"Interval: {MONITORING_INTERVAL} seconds."
    )