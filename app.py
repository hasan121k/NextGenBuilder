import os
import sqlite3
import random
import string
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv

# লোকাল এনভায়রনমেন্ট লোড করা
load_dotenv()

app = Flask(__name__)

# ==========================================
# সিকিউরিটি: API Key এনভায়রনমেন্ট থেকে অটোমেটিক নেবে
# ==========================================
api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    print("⚠️ WARNING: API Key Missing! Check Environment Variables.")
else:
    genai.configure(api_key=api_key)

# ডেটাবেস সেটআপ
def init_db():
    conn = sqlite3.connect('builder.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sites 
                 (slug TEXT PRIMARY KEY, title TEXT, html TEXT, views INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# র‍্যান্ডম লিঙ্ক জেনারেটর
def generate_slug():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(7))

@app.route('/')
def index():
    return render_template('index.html')

# AI কোড জেনারেশন API
@app.route('/api/generate', methods=['POST'])
def generate():
    if not api_key:
        return jsonify({'status': 'error', 'message': 'Server API Key is missing!'})
        
    data = request.json
    topic = data.get('topic')
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        Act as a Senior Frontend Developer.
        Task: Create a high-quality, modern Landing Page.
        Topic: {topic}
        Tech: HTML5, Tailwind CSS (CDN), FontAwesome (CDN).
        
        Design Rules:
        1. Use gradients, shadows, and rounded corners (Modern UI).
        2. Make it fully responsive.
        3. Do NOT use Markdown or explanations. Return ONLY the raw HTML code.
        """
        response = model.generate_content(prompt)
        # কোড ক্লিন করা
        clean_code = response.text.replace("```html", "").replace("```", "")
        return jsonify({'status': 'success', 'code': clean_code})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# পাবলিশ API
@app.route('/api/publish', methods=['POST'])
def publish():
    data = request.json
    title = data.get('title') or "Untitled Project"
    html = data.get('html')
    
    slug = f"{title.lower().replace(' ', '-')}-{generate_slug()}"
    # ক্লিন স্লাগ
    slug = "".join(c for c in slug if c.isalnum() or c == "-")

    conn = sqlite3.connect('builder.db')
    c = conn.cursor()
    c.execute("INSERT INTO sites (slug, title, html) VALUES (?, ?, ?)", (slug, title, html))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'url': f"{request.host_url}s/{slug}"})

# লাইভ সাইট ভিউয়ার
@app.route('/s/<slug>')
def view_site(slug):
    conn = sqlite3.connect('builder.db')
    c = conn.cursor()
    c.execute("SELECT html FROM sites WHERE slug=?", (slug,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return row[0]
    return "<h1 style='color:red;text-align:center;margin-top:20%'>404 | Site Not Found</h1>", 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
