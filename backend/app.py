from flask import Flask, request, jsonify, send_from_directory
from backend.analyser import analyze_stock, get_recommendations
from flask_cors import CORS
import os

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data or not data.get("symbol"):
        return jsonify({"error": "No stock symbol provided"}), 400

    symbol = data["symbol"].strip().upper()
    if not symbol.endswith(".NS") and not symbol.endswith(".BSE"):
        symbol += ".NS"

    try:
        result = analyze_stock(symbol, with_news=True)
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

    return jsonify(result)


@app.route("/recommend", methods=["GET"])
def recommend():
    try:
        results = get_recommendations()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\nStockSage India running at: http://127.0.0.1:5000\n")
    app.run(debug=True)
