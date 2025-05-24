from flask import Flask, request, jsonify
app = Flask(__name__)
import pandas as pd
import os
from flask import abort
# Load the metadata CSV
metadata = pd.read_csv("Summit Smart Library - Smart Summit Libarary content.csv")
@app.route("/get_summit_session", methods=["POST"])
def get_summit_session():
    # 🔐 Require API Key in Header
    request_api_key = request.headers.get("X-API-Key")
    expected_api_key = os.environ.get("API_KEY")

    if request_api_key != expected_api_key:
        abort(401, description="Unauthorized: Invalid or missing API key")
    query = request.json.get("query", "").lower().strip()
    print(f"🔍 Incoming query: {query}")
    # Try matching against the metadata CSV
    for _, row in metadata.iterrows():
        title = str(row.get("Session Title", "")).lower().strip()
        category = str(row.get("Category", "")).lower().strip()

        # Loose match: query in title or category
        if query in title or query in category:
            # Ensure all required fields are present
            if all([
                row.get("Session Title"),
                row.get("Speaker"),
                row.get("Speaker Website"),
                row.get("Year"),
                row.get("Lesson")
            ]):
                print(f"✅ Matched CSV session: {row['Session Title']}")
                return jsonify({
                    "title": row["Session Title"],
                    "speaker": row["Speaker"],
                    "website": row["Speaker Website"],
                    "year": row["Year"],
                    "lesson_link": row["Lesson"],
                    "summary": row.get("Session Description", "This session provides actionable advice on the selected topic.")
                })

    # Try matching from transcript session blocks
    for block in session_blocks:
        if query in block.lower():
            meta = extract_metadata_from_block(block)
            if meta:
                print(f"✅ Matched TXT/RTF session: {meta['title']}")
                return jsonify(meta)

    print("❌ No matching session found.")
    return jsonify({
        "message": "That topic wasn’t covered in the Blogger Breakthrough Summit sessions I have access to."
    })

@app.route("/ping")
def ping():
    return "pong"
@app.route("/test", methods=["POST"])
def test():
    data = request.json
    print(f"🔥 TEST POST received: {data}")
    return jsonify({"message": "POST worked!"})
@app.route("/")
def home():
    return "Summit API is running!"
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("✅ Flask server starting...")
    app.run(host="0.0.0.0", port=port, debug=True)



