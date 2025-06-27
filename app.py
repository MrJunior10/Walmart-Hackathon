import os
import csv
import logging
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
import google.generativeai as genai

# === HARD-CODE YOUR GEMINI API KEY HERE ===
genai.configure(api_key="lmao")
# ==========================================

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

# Ensure CSV has header
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

# ——— Gemini Caption Generator ———
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

# ——— Log feedback to CSV ———
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

# ——— Recommendation Endpoint ———
@app.route("/generate_landing", methods=["POST"])
def generate_landing():
    try:
        data = request.get_json(force=True)
        for field in ("region", "medium", "category"):
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        # 1) Predict cluster
        df_in = pd.DataFrame([{
            "region":   data["region"],
            "medium":   data["medium"],
            "category": data["category"]
        }])
        cluster_pred = int(pipeline.predict(df_in)[0])
        logging.info(f"Predicted cluster: {cluster_pred}")

        # 2) Map cluster → modules
        module_map = {
            0: {"hero": "default.jpg",  "carousel": "top_sellers",  "cta": "shop_now"},
            1: {"hero": "promo.jpg",    "carousel": "new_arrivals","cta": "learn_more"},
            2: {"hero": "seasonal.jpg", "carousel": "best_sellers","cta": "explore"},
            3: {"hero": "luxury.jpg",   "carousel": "premium",     "cta": "discover"},
            4: {"hero": "budget.jpg",   "carousel": "offers",      "cta": "save_now"}
        }
        modules = module_map.get(cluster_pred, module_map[0])

        # 3) Generate a personalized caption
        caption = generate_caption(
            data["region"], data["medium"], data["category"], cluster_pred
        )

        # 4) Log inputs and output
        log_feedback(
            data["region"], data["medium"], data["category"],
            cluster_pred, modules, caption
        )

        # 5) Return JSON
        return jsonify({
            "cluster": cluster_pred,
            "modules": modules,
            "caption": caption
        }), 200

    except Exception as e:
        logging.exception("Error in /generate_landing")
        return jsonify({"error": str(e)}), 500

# Serve your neon-lit SPA
@app.route("/")
def index():
    return app.send_static_file("index.html")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logging.info(f"Starting Flask app on port {port}…")
    app.run(host="0.0.0.0", port=port, debug=False)
