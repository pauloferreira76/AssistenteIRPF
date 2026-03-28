# Assistente IRPF 2025 — Deploy no Railway

Assistente de declaração do Imposto de Renda com extração de PDF via OCR.

## Estrutura do projeto

```
/
├── app.py              ← Servidor Flask (API OCR + serve o HTML)
├── requirements.txt    ← Dependências Python
├── Dockerfile          ← Container com Tesseract OCR instalado
├── railway.toml        ← Configuração do Railway
└── static/
    └── index.html      ← Frontend completo (HTML/CSS/JS)
```

## Deploy no Railway (passo a passo)

### 1. Criar conta no Railway
Acesse [railway.app](https://railway.app) e faça login com GitHub.

### 2. Subir o código no GitHub
```bash
# Na pasta do projeto
git init
git add .
git commit -m "Initial commit - Assistente IRPF 2025"

# Crie um repositório no GitHub e faça push
git remote add origin https://github.com/SEU_USUARIO/irpf-assistente.git
git push -u origin main
```

### 3. Criar projeto no Railway
1. No dashboard do Railway, clique em **New Project**
2. Escolha **Deploy from GitHub repo**
3. Selecione o repositório `irpf-assistente`
4. O Railway detecta o `Dockerfile` automaticamente e inicia o build

### 4. Aguardar o deploy
O build leva ~3–5 minutos (instala Tesseract + dependências Python).
Acompanhe os logs na aba **Deployments**.

### 5. Acessar a aplicação
Após o deploy, clique em **Generate Domain** nas configurações do serviço.
Você receberá uma URL como: `https://irpf-assistente-production.up.railway.app`

## Variáveis de ambiente
Nenhuma variável obrigatória. O Railway injeta `PORT` automaticamente.

## Como funciona

- **GET /**  → Retorna o frontend HTML
- **GET /health** → Status do servidor
- **POST /extract** → Recebe PDF em base64, retorna texto extraído

### Modos de extração (`mode` no body):
| Modo | Comportamento |
|------|--------------|
| `auto` | Tenta texto nativo; aplica OCR se insuficiente (padrão) |
| `native` | Somente extração de texto (PDFs da Receita Federal) |
| `ocr` | Força OCR em todas as páginas (PDFs escaneados) |

## Desenvolvimento local

```bash
# Instalar dependências do sistema (Ubuntu/Debian)
sudo apt-get install tesseract-ocr tesseract-ocr-por poppler-utils

# Instalar dependências Python
pip install -r requirements.txt

# Rodar o servidor
python app.py
# Acesse: http://localhost:8080
```

## Tecnologias
- **Backend**: Python 3.11 + Flask
- **OCR**: Tesseract 5 (português + inglês) via pytesseract
- **PDF → Imagem**: pdf2image + Poppler
- **Extração nativa**: pdfplumber
- **Frontend**: HTML/CSS/JS puro + SheetJS (Excel) + Claude API
- **Deploy**: Docker no Railway
