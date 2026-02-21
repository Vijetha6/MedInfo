from flask import Flask, request, jsonify, render_template
import os, cv2, re, requests
import pytesseract
import easyocr
from roboflow import Roboflow
from werkzeug.utils import secure_filename
from transformers import pipeline

# ===============================
# YOLO MODEL
# ===============================
rf = Roboflow(api_key="97Ou8BhM0lGoIdqrr0dc")
project = rf.workspace().project("medicine-tkh2j-3a53i")
model = project.version(5).model

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

reader = easyocr.Reader(['en'], gpu=False)
app = Flask(__name__)

# ===============================
# MEDICINE ALTERNATIVES
# ===============================
ALTERNATIVES = {

# ---------------- BP / HEART ----------------
"amlodipine": ["Amlong", "Stamlo", "Norvasc", "Amlokind"],
"atenolol": ["Tenormin", "Betacard", "Aten"],
"telmisartan": ["Telma", "Telsar", "Cresar"],
"losartan": ["Losar", "Covance", "Repace"],
"metoprolol": ["Metolar", "Betaloc", "Maxeron"],
"ramipril": ["Cardace", "Ramace"],
"enalapril": ["Enam", "Envas"],
"nebivolol": ["Nebicard", "Nebistar"],
"bisoprolol": ["Concor", "Bisoheart"],
"clonidine": ["Arkamin"],
"diltiazem": ["Dilzem", "Cardizem"],
"verapamil": ["Calan", "Veramil"],
"furosemide": ["Lasix", "Frusemide"],
"hydrochlorothiazide": ["Aquazide", "Hydrazide"],

# ---------------- PAIN / FEVER ----------------
"paracetamol": ["Calpol", "Crocin", "Dolo 650"],
"ibuprofen": ["Brufen", "Ibugesic"],
"diclofenac": ["Voveran", "Dicloran"],
"aceclofenac": ["Hifenac", "Zerodol"],
"mefenamic acid": ["Meftal", "Meftal Forte"],
"ketorolac": ["Ketanov", "Torolac"],
"tramadol": ["Ultracet", "Tramazac"],
"aspirin": ["Disprin", "Ecosprin"],

# ---------------- DIABETES ----------------
"metformin": ["Glycomet", "Obimet"],
"glimepiride": ["Amaryl", "Glimestar"],
"gliclazide": ["Diamicron", "Glizid"],
"pioglitazone": ["Pioz", "Pioglar"],
"sitagliptin": ["Januvia", "Istavel"],
"vildagliptin": ["Galvus", "Zomelis"],
"insulin": ["Huminsulin", "Actrapid"],

# ---------------- LIPID / CHOLESTEROL ----------------
"atorvastatin": ["Atorlip", "Lipitor"],
"rosuvastatin": ["Rosuvas", "Crestor"],
"simvastatin": ["Simvotin", "Zocor"],
"fenofibrate": ["Lipidil", "Fenolip"],
"ezetimibe": ["Ezetrol", "Ezedoc"],

# ---------------- ACID / GASTRIC ----------------
"pantoprazole": ["Pantocid", "Pan D"],
"omeprazole": ["Omez", "Ocid"],
"esomeprazole": ["Nexium", "Esomac"],
"rabeprazole": ["Rablet", "Razo"],
"lansoprazole": ["Lanzol", "Lan"],
"ranitidine": ["Rantac"],
"famotidine": ["Famocid", "Topcid"],

# ---------------- ALLERGY ----------------
"cetirizine": ["Cetzine", "Okacet"],
"loratadine": ["Lora", "Claritin"],
"fexofenadine": ["Allegra", "Fexy"],
"levocetirizine": ["Levocet", "Xyzal"],
"desloratadine": ["Deslor", "Neoclarity"],

# ---------------- ANTIBIOTICS ----------------
"amoxicillin": ["Amoxil", "Mox"],
"amoxicillin clavulanate": ["Augmentin", "Clavam"],
"azithromycin": ["Azee", "Zithromax"],
"ciprofloxacin": ["Ciplox", "Cifran"],
"levofloxacin": ["Levoflox", "Levaquin"],
"doxycycline": ["Doxicip", "Duracycline"],
"ceftriaxone": ["Monocef", "Rocephin"],
"cefixime": ["Zifi", "Suprax"],
"metronidazole": ["Flagyl", "Metrogyl"],

# ---------------- RESPIRATORY ----------------
"salbutamol": ["Asthalin", "Ventolin"],
"montelukast": ["Montair", "Singulair"],
"theophylline": ["Theo-24", "Deriphyllin"],
"acebrophylline": ["Acebro", "Phyllocontin", "Deriphyllin"],
"budesonide": ["Budecort", "Pulmicort"],
"formoterol": ["Foracort", "Oxis"],

# ---------------- NEURO / MISC ----------------
"alprazolam": ["Xanax", "Rest Calm"],
"diazepam": ["Valium", "Calmpose"],
"clonazepam": ["Rivotril", "Clonotril"],
"escitalopram": ["Nexito", "Cipralex"],
"sertraline": ["Zoloft", "Serlift"]

}

# ===============================
# SUMMARIZER (T5-SMALL + Keywords)
# ===============================
summarizer = pipeline("summarization", model="t5-small", device=-1)

def auto_summarize(text, max_points=3):
    if not text or text == "Not available":
        return ["Not available"]

    try:
        summary = summarizer(text, max_length=80, min_length=20, do_sample=False)[0]['summary_text']
    except Exception:
        summary = text

    parts = re.split(r'[.;]', summary)
    keywords = ["use", "indication", "treat", "therapy", "side effect", "warning"]

    points = []
    for p in parts:
        p = p.strip()
        if any(k in p.lower() for k in keywords):
            if 20 < len(p) < 150:
                points.append(p.capitalize())
        if len(points) == max_points:
            break

    return points if points else ["Not available"]

# ===============================
# IMAGE HELPERS
# ===============================
def resize_for_yolo(image_path, max_size=640):
    img = cv2.imread(image_path)
    if img is None:
        return None
    h, w = img.shape[:2]
    if max(h, w) <= max_size:
        return image_path
    scale = max_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    name, ext = os.path.splitext(image_path)
    small_path = f"{name}_small{ext}"
    cv2.imwrite(small_path, resized)
    return small_path

def yolo_crop(image_path):
    result = model.predict(image_path, confidence=0.4).json()
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    crops = []
    for p in result.get("predictions", []):
        x, y, w, h = p["x"], p["y"], p["width"], p["height"]
        x1 = max(0, int(x - w / 2))
        y1 = max(0, int(y - h / 2))
        x2 = min(img.shape[1], int(x + w / 2))
        y2 = min(img.shape[0], int(y + h / 2))
        crop = img[y1:y2, x1:x2]
        if crop is not None and crop.size > 0:
            crops.append({"label": p["class"].lower(), "image": crop})
    return crops

# ===============================
# EXPIRY EXTRACTION
# ===============================
MONTH_MAP = {
    "JAN":"01","FEB":"02","MAR":"03","APR":"04","MAY":"05","JUN":"06",
    "JUL":"07","AUG":"08","SEP":"09","OCT":"10","NOV":"11","DEC":"12"
}

patterns = [
    r'(0[1-9]|[12][0-9]|3[01])[\/\-\.](0[1-9]|1[0-2])[\/\-\.](20\d{2})',  # DD/MM/YYYY
    r'(0[1-9]|[12][0-9]|3[01])[\/\-\.](0[1-9]|1[0-2])[\/\-\.](\d{2})',    # DD/MM/YY
    r'(0[1-9]|1[0-2])[\/\-\.](20\d{2})',                                  # MM/YYYY
    r'(0[1-9]|1[0-2])[\/\-\.](\d{2})',                                    # MM/YY
    r'(20\d{2})[\/\-\.](0[1-9]|1[0-2])',                                  # YYYY/MM
    r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*[ \-\.]?(20\d{2}|\d{2})'  # Month name + year
]

def clean_expiry(text):
    if not text:
        return "NOT FOUND"
    text = text.upper()
    # remove common words
    text = re.sub(r'(EXP|EXPIRY|DATE)', ' ', text)

    # First try month-name patterns using letters intact (e.g., OCT, NOV)
    m_month = re.search(r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*[ \-\.]?(20\d{2}|\d{2})', text)
    if m_month:
        g = m_month.groups()
        mm = MONTH_MAP.get(g[0][:3], "01")
        yy = g[1][-2:]
        return f"01/{mm}/{yy}"

    # Normalize common OCR confusions and try numeric patterns
    text = text.replace('O', '0').replace('I', '1').replace('L', '1')

    for p in patterns:
        m = re.search(p, text)
        if m:
            groups = m.groups()
            # DD/MM/YYYY
            if len(groups) == 3 and len(groups[2]) == 4:
                dd, mm, yy = groups[0], groups[1], groups[2][-2:]
                return f"{dd}/{mm}/{yy}"
            # DD/MM/YY
            if len(groups) == 3 and len(groups[2]) == 2:
                dd, mm, yy = groups
                return f"{dd}/{mm}/{yy}"
            # MM/YYYY
            if len(groups) == 2 and len(groups[1]) == 4:
                mm, yy = groups[0], groups[1][-2:]
                return f"01/{mm}/{yy}"
            # MM/YY
            if len(groups) == 2 and len(groups[1]) == 2:
                mm, yy = groups
                return f"01/{mm}/{yy}"
            # YYYY/MM
            if len(groups) == 2 and len(groups[0]) == 4:
                yy, mm = groups[0][-2:], groups[1]
                return f"01/{mm}/{yy}"
            # Month name + year (fallback if matched in numeric loop)
            if len(groups) == 2 and groups[0].isalpha():
                mm = MONTH_MAP.get(groups[0][:3], "01")
                yy = groups[1][-2:]
                return f"01/{mm}/{yy}"

    return "NOT FOUND"

def preprocess_expiry(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(3.0, (8,8))
    return clahe.apply(gray)

def extract_with_rotations(img):
    rotations = [
        img,
        cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE),
        cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE),
        cv2.rotate(img, cv2.ROTATE_180),
    ]
    best_raw = ""
    for r in rotations:
        proc = preprocess_expiry(r)
        try:
            raw_pyt = pytesseract.image_to_string(
                proc,
                config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ/-.'
            ).strip()
        except:
            raw_pyt = ""
        try:
            raw_easy = " ".join(reader.readtext(proc, detail=0)).strip()
        except:
            raw_easy = ""
        raw = raw_pyt if len(raw_pyt) >= len(raw_easy) else raw_easy
        if len(raw) > len(best_raw):
            best_raw = raw
        date = clean_expiry(raw)
        if date != "NOT FOUND":
            return raw, date
    return best_raw, "NOT FOUND"

def extract_name(img):
    return " ".join(reader.readtext(img, detail=0)).strip()

# ===============================
# MEDICINE NAME EXTRACTION
# ===============================
def extract_generic_medicines(text):
    text = text.lower()
    text = re.sub(r'\d+', ' ', text)
    text = re.sub(r'[^a-z\s+/]', ' ', text)
    text = re.sub(r'\band\b|\+|/', ',', text)
    found = []
    for key in ALTERNATIVES.keys():
        if key in text:
            found.append(key)
    return list(dict.fromkeys(found))


# ===============================
# OPENFDA FETCH
# ===============================
def get_medicine_info_openfda(med):
    fields = ["openfda.generic_name", "openfda.brand_name"]
    for f in fields:
        try:
            url = f"https://api.fda.gov/drug/label.json?search={f}:{med}&limit=1"
            data = requests.get(url, timeout=5).json()
            if "results" not in data or not data["results"]:
                continue
            info = data["results"][0]
            uses = info.get("indications_and_usage") or info.get("purpose")
            side = info.get("adverse_reactions") or info.get("warnings")
            return {
                "uses": uses[0] if isinstance(uses, list) else uses or "Not available",
                "side_effects": side[0] if isinstance(side, list) else side or "Not available"
            }
        except:
            continue
    return {"uses": "Not available", "side_effects": "Not available"}

# ===============================
# TRANSLATION
# ===============================
def translate_to_kannada(text):
    """Translate text to Kannada using Google Translate"""
    try:
        from googletrans import Translator
        translator = Translator()
        result = translator.translate(text, src_language='en', dest_language='kn')
        return result['text'] if isinstance(result, dict) else result
    except:
        try:
            import requests
            url = f"https://api.mymemory.translated.net/get?q={text}&langpair=en|kn"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("responseData", {}).get("translatedText", text)
        except:
            pass
    return text

# ===============================
# ROUTES
# ===============================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    files = request.files.getlist("images")
    language = request.form.get("language", "en")
    results = []

    for file in files:
        path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(path)

        name, expiry, raw_expiry = "NOT FOUND", "NOT FOUND", ""
        small_path = resize_for_yolo(path) or path
        crops = yolo_crop(small_path)

        for c in crops:
            if "name" in c["label"]:
                name = extract_name(c["image"])
            elif "exp" in c["label"]:
                raw, exp = extract_with_rotations(c["image"])
                if exp != "NOT FOUND":
                    raw_expiry, expiry = raw, exp

        if expiry == "NOT FOUND":
            raw, exp = extract_with_rotations(cv2.imread(path))
            if exp != "NOT FOUND":
                raw_expiry, expiry = raw, exp

        meds = extract_generic_medicines(name)
        med_info = []

        # If no medicine name detected, skip further processing for this file
        if not meds:
            print("\n⚠ Medicine name not found")
            results.append({
                "extracted_name": "NOT FOUND",
                "expiry": expiry,
                "medicines": []
            })
            continue

        for m in meds:
            info = get_medicine_info_openfda(m)
            uses = auto_summarize(info["uses"])
            side_effects = auto_summarize(info["side_effects"])

            # Translate to Kannada if selected
            if language == "kn":
                uses = [translate_to_kannada(u) for u in uses]
                side_effects = [translate_to_kannada(s) for s in side_effects]

            med_info.append({
                "name": m,
                "uses_summary": uses,
                "side_effects_summary": side_effects,
                "alternates": ALTERNATIVES.get(m, [])
            })

            # ✅ PRINT TO OUTPUT SCREEN
            print(f"\n🧾 Medicine: {m}")
            print(f"📅 Expiry Date: {expiry}")
            print("💊 Uses:")
            for u in uses:
                print(f"  - {u}")
            print("⚠ Side Effects:")
            for s in side_effects:
                print(f"  - {s}")

        results.append({
            "extracted_name": meds[0] if meds else name,
            "expiry": expiry,
            "medicines": med_info
        })

    return jsonify(results)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)