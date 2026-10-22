# NexaBank

NexaBank is an educational banking simulation. It does not connect to a bank or move real money. Do not enter real personal or financial information.

The floating help assistant uses in-browser BM25-style retrieval over `static\knowledge\nexabank-help.md`, a local Markdown knowledge document grounded in the README and implemented routes. Add or edit `## Article title` sections with `Answer:`, `Keywords:`, `Details:`, `Link:`, and `Link label:` fields to maintain its knowledge. Keep links local, describe only implemented behavior, and never add credentials or customer data. The assistant returns the best matching answers with source links; it does not call an external AI service or access account-specific data.

## Run on Windows

Install Python 3.10 or later and Node.js (which includes npm). From this directory, create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`. The development configuration is for local use only and uses a built-in fallback key if `SECRET_KEY` is unset. For deployment, set private, separately generated `SECRET_KEY` and `DOCUMENT_ENCRYPTION_KEY` values and `FLASK_CONFIG=production`; the production configuration refuses to start without both keys and marks session cookies secure, so it must be served over HTTPS by a production WSGI server. Keep the document-encryption key stable and backed up securely: rotating it without re-encrypting stored documents makes them unreadable. KYC files are encrypted at rest under `instance\private-documents`, outside `static`, and may be retrieved only by their owner or an admin. Admins can explicitly delete stored documents from the KYC review page; document status remains pending until an admin verifies or rejects it. Do not expose the development server to a network. Then start the local development server:

```powershell
npm install
npm run build:css
python app.py
```

Open `http://127.0.0.1:5000`. The SQLite database is created in `database\banking.db` on first start. You can also use `flask --app app run` for local development; run that command from this directory.

## Tests

Run the smoke and workflow tests from this directory:

```powershell
python -m unittest discover -s tests -v
```

The tests use an in-memory SQLite database and do not modify the local banking database.

KYC registration requires identity and address proof; a photograph is optional. Files are limited to 5 MB each and PDF/JPG/JPEG/PNG, validated by extension, MIME type, and content parsing, then encrypted at rest outside the public static directory. Multipart upload streams are held in memory (with a 16 MB request cap) rather than spooled as plaintext files. Users can retrieve only their own documents, while admins can review, verify/reject with a reason, and delete them. Uploaded documents remain pending until an administrator reviews them. This simulation has no automatic expiry policy; admins must delete documents when retention is no longer required, and production operators must define a retention period appropriate to their legal obligations. Do not use real identity documents for local development or UI testing.

Tailwind styles are compiled locally into `static\css\tailwind.css`; no Tailwind CDN is needed at runtime. After changing templates or Tailwind styles, run `npm run build:css` again. Use `npm run watch:css` while developing to rebuild styles automatically.
