#!/usr/bin/env python3
"""
Assistente IRPF 2025 - Servidor Principal
==========================================
Serve o frontend HTML e a API OCR em um único processo Flask.
Deploy no Railway: conecte o repositório e faça deploy direto.
"""
import os
import json
import base64
import io
from flask import Flask, request, jsonify, send_from_directory, make_response

app = Flask(__name__, static_folder="static")
PORT = int(os.environ.get("PORT", 8080))


# ── CORS ──────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# ── FRONTEND ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ── HEALTH ────────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "ocr": "ready", "port": PORT})


# ── OCR EXTRACT ───────────────────────────────────────────────────────────────
@app.route("/extract", methods=["POST", "OPTIONS"])
def extract():
    if request.method == "OPTIONS":
        return make_response("", 204)
    try:
        data = request.get_json(force=True)
        if not data or "pdf_b64" not in data:
            return jsonify({"error": "pdf_b64 obrigatório"}), 400

        pdf_bytes = base64.b64decode(data["pdf_b64"])
        mode = data.get("mode", "auto")  # auto | native | ocr

        if mode == "native":
            text, method = try_native(pdf_bytes)
            if not text:
                text, method = "Texto nativo não encontrado.", "native-empty"

        elif mode == "ocr":
            text = do_ocr(pdf_bytes)
            method = "ocr"

        else:  # auto
            text, method = try_native(pdf_bytes)
            if len(text) < 200:
                text = do_ocr(pdf_bytes)
                method = "ocr"

        return jsonify({
            "text": text,
            "method": method,
            "chars": len(text)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def try_native(pdf_bytes):
    """Extrai texto nativo do PDF usando pdfplumber."""
    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
        text = "\n\n".join(parts).strip()
        return text, "native"
    except Exception:
        return "", "native-error"


def do_ocr(pdf_bytes):
    """Converte páginas do PDF em imagens e aplica OCR com Tesseract."""
    import pytesseract
    from pdf2image import convert_from_bytes

    pages = convert_from_bytes(pdf_bytes, dpi=250, fmt="jpeg")
    out = []
    for i, page in enumerate(pages):
        try:
            txt = pytesseract.image_to_string(page, lang="por+eng", config="--psm 6")
        except Exception:
            txt = pytesseract.image_to_string(page, lang="eng", config="--psm 6")
        out.append(f"=== Pagina {i + 1} ===\n{txt}")
    return "\n\n".join(out)


if __name__ == "__main__":
    print(f"  Assistente IRPF 2025 rodando na porta {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
