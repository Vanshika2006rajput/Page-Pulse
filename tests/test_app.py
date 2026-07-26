import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"]=True
    with app.test_client() as client:
        yield client

def test_empty_url(client):
    response=client.post("/audit",json={"url":""})
    assert response.status_code==400
    assert "error" in response.get_json()

def test_invalid_url(client):
    response=client.post("/audit",json={"url":"abcdefg"})
    assert response.status_code==400

def test_valid_url(client):
    response=client.post("/audit",json={"url":"https://example.com"})
    assert response.status_code==200

    data=response.get_json()

    assert "title" in data
    assert "status" in data
    assert "responseTime" in data