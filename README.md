# PDF Page 2 Replacer — Streamlit Website

This Streamlit website performs this workflow:

**Original PDF page 1 + permanent middle PDF + original PDF pages 3 to last**

That means the original page 2 is removed and replaced with the entire permanently saved middle PDF.

## Features

- Drag-and-drop original PDF upload
- Permanent middle PDF stored on the server
- Settings panel
- Replace the permanent middle PDF
- See the exact permanent middle PDF storage path
- Download the currently saved middle PDF
- Try to open the storage folder when running locally
- Download the generated final PDF
- Keeps the original PDF metadata when possible
- Handles PDFs with many pages

## Run locally

Install Python 3.10 or newer.

Open a terminal in this project folder and run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will open the website in your browser, usually at:

```text
http://localhost:8501
```

## Permanent middle PDF location

By default, the middle PDF is stored at:

```text
~/.pdf_page2_replacer_web/permanent_middle.pdf
```

You upload it once from **Settings**. It is then used automatically for all future jobs until you replace it.

## Choose a different permanent storage folder

Set the environment variable:

```text
MIDDLE_PDF_DIR
```

Example on Windows PowerShell:

```powershell
$env:MIDDLE_PDF_DIR="C:\PDFReplacerData"
streamlit run app.py
```

Example on Linux or macOS:

```bash
export MIDDLE_PDF_DIR="/data/pdf-replacer"
streamlit run app.py
```

## Important note about online hosting

On many cloud platforms, the normal application filesystem may be temporary. The permanent middle PDF can disappear when the server is rebuilt, redeployed, or restarted.

For a truly permanent online middle PDF, configure `MIDDLE_PDF_DIR` to point to a persistent disk/volume supplied by your hosting provider.

Examples include:

- Render persistent disk
- Railway volume
- Fly.io volume
- A mounted server directory on your own VPS

## Open-folder alternative

Web browsers cannot directly open a folder on a remote server.

The website therefore provides three options:

1. Displays the exact server storage path.
2. Lets you download the current permanent middle PDF.
3. Includes **Try to Open Server Folder**, which is useful when Streamlit is running locally on your own desktop.

When deployed online, the third option may do nothing because the remote server usually has no graphical desktop.

## Deployment

The project can be deployed to any service that supports Streamlit or Python web applications.

Basic start command:

```text
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```
