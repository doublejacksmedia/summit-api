from flask import Flask, request, jsonify, abort, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

# Serve the OpenAPI spec
@app.route("/openapi.yaml")
def serve_openapi():
    return send_from_directory(os.getcwd(), "openapi.yaml", mimetype="text/yaml")

# Load the metadata CSV
metadata = pd.read_csv("Summit Smart Library - Smart Summit Libarary content.csv")

# Load all session .txt files from the sessions/ folder
def load_transcript_blocks(folder_path="sessions"):
    blocks = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            full_path = os.path.join(folder_path, filename)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    blocks.append(content)
            except Exception as e:
                print(f"⚠️ Error reading {filename}: {e}")
    print(f"✅ Loaded {len(blocks)} session blocks from {folder_path}")
    return blocks

# Parse metadata and transcript from a single block
def extract_metadata_from_block(block):
    lines = block.strip().splitlines()
    meta = {}
    transcript_lines = []

    for line in lines:
        if line.startswith("Title:"):
            meta["title"] = line.replace("Title:", "").strip()
        elif line.startswith("Speaker:"):
            meta["speaker"] = line.replace("Speaker:", "").strip()
        elif line.startswith("Website:"):
            meta["website"] = line.replace("Website:", "").strip()
        elif line.startswith("Level:"):
            meta["level"] = line.replace("Level:", "").strip()
        elif line.startswith("Category:"):
            meta["category"] = line.replace("Category:", "").strip()
        elif line.startswith("Length:"):
            raw_length = line.replace("Length:", "").strip()
            meta["length"] = float(raw_length) if raw_length else 0.0
        elif line.startswith("Year:"):
            meta["year"] = line.replace("Year:", "").strip()
        elif line.startswith("Lesson Link:"):
            meta["lesson_link"] = line.replace("Lesson Link:", "").strip()
        elif line.startswith("Transcript:"):
            idx = lines.index(line)
            transcript_lines = lines[idx + 1:]
            break

    required = ["title", "speaker", "website", "year", "lesson_link"]
    if not all(field in meta and meta[field] for field in required):
        print(f"❌ Skipped session: missing required metadata in block starting with '{lines[0]}'")
        return None

    meta["summary"] = "\n".join(transcript_lines[:5]).strip()  # Use first 5 lines as preview
    return meta

# Load and cache session blocks at startup
session_blocks = load_transcript_blocks()

@app.route("/get_summit_session", methods=["POST"])
def get_summit_session():
    request_api_key = request.headers.get("X-API-Key")
    expected_api_key = os.environ.get("API_KEY")

    if request_api_key != expected_api_key:
        abort(401, description="Unauthorized: Invalid or missing API key")

    query = request.json.get("query", "").lower().strip()
    print(f"🔍 Incoming query: {query}")

    # Try matching against the metadata CSV first
    for _, row in metadata.iterrows():
        title = str(row.get("Session Title", "")).lower().strip()
        category = str(row.get("Category", "")).lower().strip()

        if query in title or query in category:
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

    # Fallback to searching transcript blocks
    for block in session_blocks:
        if query in block.lower():
            meta = extract_metadata_from_block(block)
            if meta:
                print(f"✅ Matched TXT session: {meta['title']}")
                return jsonify({
                    "title": meta["title"],
                    "speaker": meta["speaker"],
                    "website": meta["website"],
                    "year": meta["year"],
                    "lesson_link": meta["lesson_link"],
                    "summary": meta["summary"]
                })

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
