from __future__ import annotations

import io
import os
import platform
import subprocess
from pathlib import Path

import streamlit as st
from pypdf import PdfReader, PdfWriter


APP_TITLE = "PDF Page 2 Replacer"

# Put the fixed replacement PDF in the same GitHub repository as app.py.
# Its filename must be: permanent_middle.pdf
MIDDLE_PDF_PATH = Path(__file__).resolve().parent / "permanent_middle.pdf"


def middle_pdf_exists() -> bool:
    return MIDDLE_PDF_PATH.exists() and MIDDLE_PDF_PATH.is_file()


def read_pdf_from_bytes(data: bytes, label: str) -> PdfReader:
    if not data:
        raise ValueError(f"{label} is empty.")

    reader = PdfReader(io.BytesIO(data))

    if reader.is_encrypted:
        try:
            result = reader.decrypt("")
        except Exception as exc:
            raise ValueError(
                f"{label} is password-protected and cannot be processed."
            ) from exc

        if not result:
            raise ValueError(
                f"{label} is password-protected and cannot be processed."
            )

    return reader


def build_final_pdf(original_bytes: bytes, middle_bytes: bytes) -> tuple[bytes, dict]:
    original_reader = read_pdf_from_bytes(original_bytes, "The original PDF")
    middle_reader = read_pdf_from_bytes(middle_bytes, "The permanent middle PDF")

    original_count = len(original_reader.pages)
    middle_count = len(middle_reader.pages)

    if original_count < 2:
        raise ValueError(
            "The original PDF must contain at least 2 pages because page 2 is being replaced."
        )

    if middle_count < 1:
        raise ValueError("The permanent middle PDF does not contain any pages.")

    writer = PdfWriter()

    # 1. Original page 1
    writer.add_page(original_reader.pages[0])

    # 2. Entire permanent middle PDF
    for page in middle_reader.pages:
        writer.add_page(page)

    # 3. Original pages 3 to last
    for page_index in range(2, original_count):
        writer.add_page(original_reader.pages[page_index])

    # Copy basic metadata when possible.
    if original_reader.metadata:
        metadata = {}
        for key, value in original_reader.metadata.items():
            if key and value is not None:
                metadata[str(key)] = str(value)
        if metadata:
            writer.add_metadata(metadata)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)

    final_count = 1 + middle_count + max(0, original_count - 2)

    details = {
        "original_pages": original_count,
        "middle_pages": middle_count,
        "remaining_original_pages": max(0, original_count - 2),
        "final_pages": final_count,
    }

    return output.getvalue(), details


def try_open_server_folder() -> tuple[bool, str]:
    """
    Tries to open the storage folder on the machine running Streamlit.
    This is useful only when the website is running locally on a desktop.
    On cloud hosting, the server has no user-visible desktop, so the
    browser cannot open that remote folder.
    """
    ensure_data_dir()

    try:
        system = platform.system()

        if system == "Windows":
            os.startfile(str(DATA_DIR))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(DATA_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(DATA_DIR)])

        return True, f"Requested opening: {DATA_DIR}"
    except Exception as exc:
        return False, str(exc)


def safe_output_name(original_name: str) -> str:
    stem = Path(original_name).stem.strip() or "document"
    return f"{stem}_FINAL.pdf"


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📄",
    layout="centered",
)


st.title("📄 PDF Page 2 Replacer")
st.caption(
    "Upload the original PDF only. The fixed replacement PDF is included with the app."
)

st.info(
    "The original PDF's page 2 is removed. The bundled permanent_middle.pdf is inserted after original page 1."
)

# -------------------------
# Permanent middle PDF state
# -------------------------
if middle_pdf_exists():
    try:
        current_middle_bytes = MIDDLE_PDF_PATH.read_bytes()
        current_middle_reader = read_pdf_from_bytes(
            current_middle_bytes,
            "The permanent middle PDF",
        )
        current_middle_pages = len(current_middle_reader.pages)
        st.success(
            f"Permanent middle PDF is ready — {current_middle_pages} page(s)."
        )
    except Exception as exc:
        st.error(
            f"The saved permanent middle PDF could not be read: {exc}"
        )
else:
    st.error(
        "The fixed replacement PDF is missing. Add `permanent_middle.pdf` to the same GitHub repository folder as `app.py`, then redeploy."
    )

# -------------------------
# Main processing area
# -------------------------
st.subheader("Create final PDF")

original_file = st.file_uploader(
    "Upload or drag the original PDF here",
    type=["pdf"],
    accept_multiple_files=False,
    key="original_pdf_uploader",
    help="The app keeps page 1, removes page 2, and keeps pages 3 to the last page.",
)

if original_file is not None:
    st.write(f"**Selected original PDF:** `{original_file.name}`")

    if middle_pdf_exists():
        process_clicked = st.button(
            "Create Final PDF",
            type="primary",
            use_container_width=True,
        )

        if process_clicked:
            try:
                original_bytes = original_file.getvalue()
                middle_bytes = MIDDLE_PDF_PATH.read_bytes()

                final_bytes, details = build_final_pdf(
                    original_bytes,
                    middle_bytes,
                )

                st.session_state["final_pdf_bytes"] = final_bytes
                st.session_state["final_pdf_name"] = safe_output_name(
                    original_file.name
                )
                st.session_state["final_pdf_details"] = details

                st.success("Final PDF created successfully.")
            except Exception as exc:
                st.error(f"Could not create the final PDF: {exc}")
    else:
        st.error(
            "The fixed replacement PDF is missing. Add `permanent_middle.pdf` to the same GitHub repository folder as `app.py`, then redeploy."
        )


if "final_pdf_bytes" in st.session_state:
    details = st.session_state.get("final_pdf_details", {})

    st.write(
        f"**Result:** "
        f"1 original first page + "
        f"{details.get('middle_pages', '?')} middle page(s) + "
        f"{details.get('remaining_original_pages', '?')} original page(s) from page 3 onward "
        f"= **{details.get('final_pages', '?')} final page(s)**"
    )

    st.download_button(
        label="⬇️ Download Final PDF",
        data=st.session_state["final_pdf_bytes"],
        file_name=st.session_state.get(
            "final_pdf_name",
            "final_merged.pdf",
        ),
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )


