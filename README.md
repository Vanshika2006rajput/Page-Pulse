# Page Pulse
Page Pulse is a web tool that audits any URL and provides information about the webpage like status code, response time, title, meta description, H1 count, missing image alt text, and word count.

## Setup Instructions
Clone the repository:git clone https://github.com/Vanshika2006rajput/Page-Pulse
Install dependencies:

pip install -r requirements.txt

Run the application:

python app.py

Open in browser:

http://127.0.0.1:5000/


## API Contract

### Endpoint

POST /analyze


### Request

{
    "url": "https://example.com"
}


### Response

{
    "status": 200,
    "title": "Example Domain",
    "word_count": 100
}


## Design Decisions

### 1. Flask Framework
I used Flask because it is lightweight and suitable for building a small API-based web application.

### 2. Error Handling
The application handles invalid URLs, timeout errors, and non-HTML responses by returning meaningful error messages instead of crashing.

### 3. Frontend and Backend Separation
HTML, CSS, and JavaScript are separated from backend logic to make the project easier to maintain and update.


## Testing

Tests are written using pytest.

Covered cases:
- Successful URL analysis
- Invalid URL handling
- Failed request handling