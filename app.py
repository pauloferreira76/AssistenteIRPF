import os, base64, io, json, requests
from flask import Flask, request, jsonify, send_file, make_response

app = Flask(__name__)
PORT     = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL    = "claude-sonnet-4-20250514"

@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

@app.route("/")
def index():
    path = os.path.join(BASE_DIR, "static", "index.html")
    if not os.path.exists(path):
        files = []
        for root, dirs, fs in os.walk(BASE_DIR):
            for f in fs:
                files.append(os.path.join(root,f).replace(BASE_DIR,""))
        return "<pre>index.html nao encontrado:\n" + "\n".join(files) + "</pre>", 404
    return send_file(path)

@app.route("/health")
def health():
    path = os.path.join(BASE_DIR, "static", "index.html")
    return jsonify({
        "status":       "ok",
        "html_exists":  os.path.exists(path),
        "api_key_set":  bool(API_KEY),
        "port":         PORT
    })

# ── PROXY: Chat ───────────────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST","OPTIONS"])
def api_chat():
    if request.method == "OPTIONS":
        return make_response("", 204)
    if not API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY nao configurada"}), 500
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": API_KEY,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json=request.get_json(force=True),
            timeout=60
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── PROXY: Extrair PDF ────────────────────────────────────────────────────────
@app.route("/api/extract-pdf", methods=["POST","OPTIONS"])
def api_extract_pdf():
    if request.method == "OPTIONS":
        return make_response("", 204)
    if not API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY nao configurada"}), 500
    try:
        data      = request.get_json(force=True)
        pdf_b64   = data.get("pdf_b64", "")
        mode      = data.get("mode", "auto")
        pdf_bytes = base64.b64decode(pdf_b64)

        # Tenta extração nativa primeiro
        text, method = extract_native(pdf_bytes)

        # Se texto insuficiente e modo permite OCR, usa Claude Vision no PDF
        if len(text) < 200 and mode != "native":
            # Envia PDF direto ao Claude como documento (vision)
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": API_KEY,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={
                    "model": MODEL,
                    "max_tokens": 2000,
                    "system": EXTRACT_SYSTEM,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "document",
                             "source": {"type": "base64",
                                        "media_type": "application/pdf",
                                        "data": pdf_b64}},
                            {"type": "text",
                             "text": "Extraia todos os dados desta declaracao IRPF e retorne o JSON."}
                        ]
                    }]
                },
                timeout=90
            )
            raw    = resp.json().get("content",[{}])[0].get("text","{}")
            raw    = raw.replace("```json","").replace("```","").strip()
            parsed = json.loads(raw)
            return jsonify({"data": parsed, "method": "claude-vision"})

        # Texto nativo suficiente — pede Claude interpretar
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": API_KEY,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={
                "model": MODEL,
                "max_tokens": 2000,
                "system": EXTRACT_SYSTEM,
                "messages": [{"role": "user",
                               "content": "Extraia os dados do texto abaixo e retorne o JSON.\n\n"
                                          "TEXTO:\n" + text[:12000]}]
            },
            timeout=90
        )
        raw    = resp.json().get("content",[{}])[0].get("text","{}")
        raw    = raw.replace("```json","").replace("```","").strip()
        parsed = json.loads(raw)
        return jsonify({"data": parsed, "method": method})

    except Exception as e:
        print(f"extract-pdf error: {e}", flush=True)
        return jsonify({"error": str(e)}), 500


def extract_native(pdf_bytes):
    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t: parts.append(t)
        return "\n\n".join(parts).strip(), "native"
    except Exception as e:
        print(f"pdfplumber error: {e}", flush=True)
        return "", "error"


EXTRACT_SYSTEM = """Voce e um extrator de dados de declaracoes do IRPF brasileiro.
Retorne APENAS JSON valido sem markdown, sem texto adicional:
{"ano_base":"2023","identificacao":{"nome":"","cpf":"","data_nascimento":"","ocupacao":"","municipio":"","uf":"","email":"","telefone":""},"rendimentos_tributaveis":{"trabalho_assalariado":0,"pro_labore":0,"alugueis":0,"atividade_rural":0,"outros":0,"total":0,"fontes_pagadoras":[]},"rendimentos_isentos":{"fgts":0,"indenizacoes":0,"poupanca":0,"dividendos":0,"outros":0,"total":0},"deducoes":{"dependentes_qtd":0,"dependentes_valor":0,"saude":0,"educacao":0,"prev_oficial":0,"prev_privada_pgbl":0,"pensao_alimenticia":0,"livro_caixa":0,"total":0},"bens_direitos":{"imoveis":0,"veiculos":0,"aplicacoes_financeiras":0,"acoes":0,"outros":0,"total":0},"dividas_onus":{"total":0},"calculo_ir":{"base_calculo":0,"aliquota_efetiva":0,"ir_devido":0,"ir_retido_fonte":0,"ir_pago_carne":0,"total_pago":0,"resultado":0,"tipo_resultado":"restituicao"},"modelo_utilizado":"completo","desconto_simplificado":0}
Use 0 para numeros nao encontrados e vazio para textos. Nunca invente valores."""


if __name__ == "__main__":
    print(f"Iniciando na porta {PORT}", flush=True)
    print(f"API Key configurada: {bool(API_KEY)}", flush=True)
    print(f"BASE_DIR: {BASE_DIR}", flush=True)
    app.run(host="0.0.0.0", port=PORT, debug=False)
