from flask import Flask,render_template,request,jsonify
import requests
import time
from bs4 import BeautifulSoup

app=Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/audit",methods=["POST"])
def audit():

    data=request.get_json()
    url=data.get("url","").strip()

    if url=="":
        return jsonify({"error":"Please enter a website URL."}),400

    if not url.startswith("http://") and not url.startswith("https://"):
        url="https://"+url

    try:

        start=time.time()

        response=requests.get(url,timeout=10)

        end=time.time()

        contentType=response.headers.get("Content-Type","")

        if "text/html" not in contentType:
            return jsonify({"error":"This URL does not contain an HTML page."}),400

        soup=BeautifulSoup(response.text,"html.parser")

        title=soup.title.string.strip() if soup.title else "No Title"

        meta=soup.find("meta",attrs={"name":"description"})

        description=meta.get("content","No Description") if meta else "No Description"

        words=len(soup.get_text().split())

        images=soup.find_all("img")

        missingAlt=0

        for img in images:
            if not img.get("alt"):
                missingAlt+=1

        return jsonify({
            "status":response.status_code,
            "responseTime":str(round((end-start)*1000,2))+" ms",
            "title":title,
            "description":description,
            "wordCount":words,
            "imagesWithoutAlt":missingAlt
        })

    except requests.exceptions.Timeout:
        return jsonify({"error":"The website took too long to respond."}),408

    except requests.exceptions.ConnectionError:
        return jsonify({"error":"Could not connect to the website."}),400

    except requests.exceptions.MissingSchema:
        return jsonify({"error":"Invalid URL."}),400

    except Exception:
        return jsonify({"error":"Something went wrong."}),500

if __name__=="__main__":
    app.run(debug=True)