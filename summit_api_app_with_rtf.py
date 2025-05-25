from flask import Flask, request, jsonify, abort, send_from_directory
import pandas as pd
import os
import glob

app = Flask(__name__)

# Serve the OpenAPI spec
@app.route("/openapi.yaml")
def serve_openapi():
    return send_from_directory(os.getcwd(), "openapi.yaml", mimetype="text/yaml")

# Load the metadata CSV
metadata = pd.read_csv("Summit Smart Library - Smart Summit Libarary content.csv")

# Load and cache all .txt session blocks
def load_transcript_blocks(folder_path="sessions"):
    blocks = []
    for filepath in glob.glob(os.path.join(folder_path, "**/*.txt"), recursive=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                blocks.append(content)
        except Exception as e:
            print(f"⚠️ Error reading {filepath}: {e}")
    print(f"✅ Loaded {len(blocks)} session blocks from {folder_path}")
    return blocks

# Parse metadata and extract from one block
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
        elif line.startswith("Year:"):
            meta["year"] = line.replace("Year:", "").strip()
        elif line.startswith("Lesson Link:"):
            meta["lesson_link"] = line.replace("Lesson Link:", "").strip()
        elif line.startswith("Transcript:"):
            idx = lines.index(line)
            transcript_lines = lines[idx + 1:]
            break

    required = ["title", "speaker", "website", "year", "lesson_link"]
    if not all(meta.get(field) for field in required):
        print(f"❌ Skipped session: missing metadata in block starting with '{lines[0]}'")
        return None

    meta["summary"] = "\n".join(transcript_lines[:5]).strip()
    return meta

# Cache transcript blocks
session_blocks = load_transcript_blocks()
print(f"🔎 Loaded {len(session_blocks)} transcript blocks.")

@app.route("/get_summit_session", methods=["POST"])
def get_summit_session():
    request_api_key = request.headers.get("X-API-Key")
    expected_api_key = os.environ.get("API_KEY")

    if request_api_key != expected_api_key:
        abort(401, description="Unauthorized: Invalid or missing API key")

    query = request.json.get("query", "").lower().strip()
    print(f"🔍 Incoming query: {query}")

    # 1. Try matching CSV
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

    # 2. Try matching .txt transcript blocks
    for block in session_blocks:
        keywords = query.lower().split()
if all(word in block.lower() for word in keywords):
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
