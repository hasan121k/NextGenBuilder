import os
import sqlite3
import random
import string
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
import requests

load_dotenv()

app = Flask(__name__)

# ==========================================
# সিকিউরিটি: Hugging Face API Key এনভায়রনমেন্ট থেকে নেবে
# ==========================================
HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

# Mistral-7B মডেল: হালকা, দ্রুত এবং শক্তিশালী (এইটি কাজ করবেই)
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2" 

# InferenceClient ইনিশিয়ালাইজ
if HF_API_KEY:
    try:
        hf_client = InferenceClient(
            model=MODEL_NAME,
            token=HF_API_KEY
        )
    except Exception as e:
        print(f"Error initializing HF Client: {e}")
        hf_client = None
else:
    hf_client = None

# ডেটাবেস সেটআপ
def init_db():
    conn = sqlite3.connect('builder.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sites 
                 (slug TEXT PRIMARY KEY, title TEXT, html TEXT, views INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

def get_slug():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(7))

@app.route('/')
def index():
    return render_template('index.html')

# Hugging Face Client দিয়ে কোড জেনারেশন API
@app.route('/api/generate', methods=['POST'])
def generate():
    if not hf_client:
        return jsonify({'status': 'error', 'message': 'Inference Client not initialized (API Key Missing or Invalid)'})
        
    data = request.json
    topic = data.get('topic')
    
    # Client ব্যবহারের জন্য প্রম্পট
    hf_prompt = f"""
    [INST] You are an expert web developer. Create a single-file responsive Landing Page.
    Topic: {topic}
    Tech Stack: HTML5, Tailwind CSS (CDN), FontAwesome (CDN).
    Rules: 
    1. Modern, clean design. 
    2. RETURN ONLY the RAW HTML code. Do not use markdown.
    [/INST]
    """
    
    try:
        # Client ব্যবহার করে কোড জেনারেট করা
        response = hf_client.text_generation(
            hf_prompt,
            model=MODEL_NAME, 
            max_new_tokens=2048,
            return_full_text=False
        )
        
        full_text = response.strip()
        
        # আউটপুট থেকে কোড ক্লিন করা
        code_start = full_text.find('<!DOCTYPE html>')
        
        if code_start != -1:
            clean_code = full_text[code_start:]
        else:
            clean_code = full_text
            
        return jsonify({'status': 'success', 'code': clean_code})
    
    except Exception as e:
        # সমস্ত Error হ্যান্ডেল করবে
        return jsonify({'status': 'error', 'message': f"Inference Error: {str(e)}"})

# পাবলিশ API
@app.route('/api/publish', methods=['POST'])
def publish():
    data = request.json
    title = data.get('title') or "Untitled Project"
    html = data.get('html')
    
    slug = f"{title.lower().replace(' ', '-')[:20]}-{get_slug()}"
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
