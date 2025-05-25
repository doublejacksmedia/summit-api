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

# Extract metadata from .txt block
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

ENGLISH_STOP_WORDS = {"the", "and", "you", "your", "how", "can", "to", "with", "for", "of", "in", "a", "on"}

session_blocks = load_transcript_blocks()
print(f"🔎 Loaded {len(session_blocks)} transcript blocks.")

@app.route("/get_summit_session", methods=["POST"])
def get_summit_session():
    request_api_key = request.headers.get("X-API-Key")
    expected_api_key = os.environ.get("API_KEY")
    if request_api_key != expected_api_key:
        abort(401, description="Unauthorized: Invalid or missing API key")

    data = request.json
    query = data.get("query", "").lower().strip()
    follow_up = data.get("follow_up", False)

    print(f"🔍 Incoming query: {query} | follow_up: {follow_up}")
    keywords = [word for word in query.split() if word not in ENGLISH_STOP_WORDS]

    # Define relevant categories for common intents
    list_growth_keywords = ["grow", "list", "subscribers", "opt-in", "freebie", "signup", "bundle", "challenge"]
    relevant_categories = ["Email Marketing", "Pinterest Marketing", "List Building"]

    # Determine if it's a list-building query
    is_list_growth_query = any(word in query for word in list_growth_keywords)

    # Limit sessions to Email Marketing if it's a list growth query
    filtered_metadata = metadata
    if is_list_growth_query:
        filtered_metadata = filtered_metadata[filtered_metadata["Category"].isin(relevant_categories)]

    scored_matches = []

    # Score metadata
    for _, row in filtered_metadata.iterrows():
        text = f"{row.get('Session Title', '')} {row.get('Category', '')}".lower()
        score = sum(1 for word in keywords if word in text)
        if score > 0 and all([
            row.get("Session Title"),
            row.get("Speaker"),
            row.get("Speaker Website"),
            row.get("Year"),
            row.get("Lesson")
        ]):
            scored_matches.append({
                "score": score,
                "title": row["Session Title"],
                "speaker": row["Speaker"],
                "website": row["Speaker Website"],
                "year": row["Year"],
                "lesson_link": row["Lesson"],
                "summary": row.get("Session Description", "This session provides actionable advice on the selected topic.")
            })

    # Score .txt blocks
    for block in session_blocks:
        meta = extract_metadata_from_block(block)
        if not meta:
            continue

        # Optional category filter
        if is_list_growth_query and meta.get("category") not in relevant_categories:
            continue

        score = sum(1 for word in keywords if word in block.lower())
        if score > 0:
            meta["score"] = score
            scored_matches.append(meta)

    if not scored_matches:
        print("❌ No matching session found.")
        return jsonify({
            "message": "That topic wasn’t covered in the Blogger Breakthrough Summit sessions I have access to."
        })

    # Sort and respond
    scored_matches.sort(key=lambda x: x["score"], reverse=True)
    if follow_up:
        print("📚 Returning top 3–5 follow-up sessions")
        return jsonify(scored_matches[1:6])

    top = scored_matches[0]
    print(f"⭐️ Top session match: {top['title']}")
    return jsonify({
        "title": top["title"],
        "speaker": top["speaker"],
        "website": top["website"],
        "year": top["year"],
        "lesson_link": top["lesson_link"],
        "summary": top["summary"]
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
