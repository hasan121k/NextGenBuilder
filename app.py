import os
import sqlite3
import random
import string
from flask import Flask, render_template, request, jsonify
import requests  # Hugging Face API এর জন্য
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ==========================================
# সিকিউরিটি: Hugging Face API Key এনভায়রনমেন্ট থেকে নেবে
# ==========================================
HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

# WizardCoder মডেলের এন্ডপয়েন্ট (নতুন এবং সচল মডেল)
HF_MODEL_URL = "https://api-inference.huggingface.co/models/WizardLM/WizardCoder-Python-7B-V1.0"

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

# Hugging Face দিয়ে কোড জেনারেশন API
@app.route('/api/generate', methods=['POST'])
def generate():
    if not HF_API_KEY:
        return jsonify({'status': 'error', 'message': 'Hugging Face API Key is missing on server!'})
        
    data = request.json
    topic = data.get('topic')
    
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    # Hugging Face এর জন্য বিশেষ প্রম্পট
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
        response = requests.post(
            HF_MODEL_URL,
            headers=headers,
            json={
                "inputs": hf_prompt,
                "options": {"wait_for_model": True}
            }
        )
        response.raise_for_status() # কোনো HTTP Error হলে এটি Error দেবে
        result = response.json()
        
        # আউটপুট থেকে কোড ক্লিন করা
        full_text = result[0]['generated_text']
        
        # প্রম্পটের পর থেকে কোড নেওয়া
        code_start = full_text.find('<!DOCTYPE html>')
        
        if code_start != -1:
            clean_code = full_text[code_start:]
        else:
            # যদি <!DOCTYPE না পায়, তবে পুরো লেখাটি দেবে
            clean_code = full_text
            
        return jsonify({'status': 'success', 'code': clean_code})
    
    except requests.exceptions.RequestException as e:
        return jsonify({'status': 'error', 'message': f"API Connection Error: {str(e)}"})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f"General Error: {str(e)}"})

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
