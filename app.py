import os
import csv
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Configure logging
def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )

# Returns path to your .pkl
def get_model_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "models", "landing_page_recommender.pkl")

# Path for feedback CSV
base_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(base_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)
FEEDBACK_CSV = os.path.join(logs_dir, "user_feedback.csv")
FEEDBACK_FIELDS = ["timestamp", "region", "medium", "category", "cluster", "hero", "carousel", "cta", "caption"]

if not os.path.isfile(FEEDBACK_CSV):
    with open(FEEDBACK_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FEEDBACK_FIELDS)
        writer.writeheader()

# Load ML pipeline on startup
configure_logging()
model_path = get_model_path()
logging.info(f"Loading model from {model_path}…")
pipeline = joblib.load(model_path)
logging.info("Model loaded successfully.")

# Flask setup
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# Gemini caption generation
def generate_caption(region, medium, category, cluster):
    prompt = (
        f"You are a personalization assistant for Walmart. A user from '{region}' "
        f"arrived via '{medium}' browsing '{category}' (cluster {cluster}). "
        "Write a short, catchy tagline (max 25 words) for their landing page."
    )
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.warning(f"Gemini caption failed: {e}")
        return "Welcome to your personalized shopping experience!"

# Log feedback to CSV
def log_feedback(region, medium, category, cluster, modules, caption):
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "region": region,
        "medium": medium,
        "category": category,
        "cluster": cluster,
        "hero": modules.get("hero", ""),
        "carousel": modules.get("carousel", ""),
        "cta": modules.get("cta", ""),
        "caption": caption.replace("\n", " ")
    }
    with open(FEEDBACK_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FEEDBACK_FIELDS)
        writer.writerow(row)

# Main recommendation endpoint
@app.route("/generate_landing", methods=["POST"])
def generate_landing():
    try:
        data = request.get_json(force=True)
        for field in ("region", "medium", "category"):
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        df_in = pd.DataFrame([{
            "region": data["region"],
            "medium": data["medium"],
            "category": data["category"]
        }])
        cluster_pred = int(pipeline.predict(df_in)[0])
        logging.info(f"Predicted cluster: {cluster_pred}")

        module_map = {
            0: {"hero": "default.jpg",  "carousel": "top_sellers",  "cta": "shop_now"},
            1: {"hero": "promo.jpg",    "carousel": "new_arrivals","cta": "learn_more"},
            2: {"hero": "seasonal.jpg", "carousel": "best_sellers","cta": "explore"},
            3: {"hero": "luxury.jpg",   "carousel": "premium",     "cta": "discover"},
            4: {"hero": "budget.jpg",   "carousel": "offers",      "cta": "save_now"}
        }
        modules = module_map.get(cluster_pred, module_map[0])
        caption = generate_caption(data["region"], data["medium"], data["category"], cluster_pred)

        log_feedback(data["region"], data["medium"], data["category"], cluster_pred, modules, caption)

        return jsonify({
            "cluster": cluster_pred,
            "modules": modules,
            "caption": caption
        }), 200

    except Exception as e:
        logging.exception("Error in /generate_landing")
        return jsonify({"error": str(e)}), 500

from flask import render_template  # add this near the top

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/promo")
def promo_page():
    return render_template("promo.html")

@app.route("/default")
def default_page():
    return render_template("default.html")

@app.route("/luxury")
def luxury_page():
    return render_template("luxury.html")

@app.route("/budget")
def budget_page():
    return render_template("budget.html")

@app.route("/seasonal")
def seasonal_page():
    return render_template("seasonal.html")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logging.info(f"Starting Flask app on port {port}…")
    app.run(host="0.0.0.0", port=port, debug=False)
