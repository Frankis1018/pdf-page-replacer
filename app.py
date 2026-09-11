from __future__ import annotations

import io
import os
import platform
import subprocess
from pathlib import Path

import streamlit as st
from pypdf import PdfReader, PdfWriter


APP_TITLE = "PDF Page 2 Replacer"

# You can override this with an environment variable when deploying.
# Example:
#   MIDDLE_PDF_DIR=/data/pdf_page2_replacer
DATA_DIR = Path(
    os.environ.get(
        "MIDDLE_PDF_DIR",
        str(Path.home() / ".pdf_page2_replacer_web")
    )
).expanduser()

MIDDLE_PDF_PATH = DATA_DIR / "permanent_middle.pdf"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def middle_pdf_exists() -> bool:
    return MIDDLE_PDF_PATH.exists() and MIDDLE_PDF_PATH.is_file()


def save_middle_pdf(uploaded_file) -> None:
    ensure_data_dir()

    data = uploaded_file.getvalue()
    if not data:
        raise ValueError("The selected middle PDF is empty.")

    # Validate before saving permanently.
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        try:
            result = reader.decrypt("")
        except Exception as exc:
            raise ValueError(
                "The middle PDF is password-protected and cannot be used."
            ) from exc
        if not result:
            raise ValueError(
                "The middle PDF is password-protected and cannot be used."
            )

    if len(reader.pages) < 1:
        raise ValueError("The middle PDF does not contain any pages.")

    tmp_path = MIDDLE_PDF_PATH.with_suffix(".tmp")
    tmp_path.write_bytes(data)
    tmp_path.replace(MIDDLE_PDF_PATH)


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

ensure_data_dir()

st.title("📄 PDF Page 2 Replacer")
st.caption(
    "Final PDF = Original page 1 + Permanent middle PDF + Original pages 3 to last"
)

st.info(
    "Page 2 of the original PDF is removed. The entire permanent middle PDF is inserted after page 1."
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
    st.warning(
        "No permanent middle PDF has been set yet. Open Settings below and upload it once."
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
            "Set the permanent middle PDF in Settings before processing the original PDF."
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


# -------------------------
# Settings
# -------------------------
st.divider()

with st.expander("⚙️ Settings", expanded=not middle_pdf_exists()):
    st.write("### Permanent middle PDF")

    st.code(str(MIDDLE_PDF_PATH), language=None)

    if middle_pdf_exists():
        try:
            middle_bytes_for_download = MIDDLE_PDF_PATH.read_bytes()
            middle_reader = read_pdf_from_bytes(
                middle_bytes_for_download,
                "The permanent middle PDF",
            )
            st.write(
                f"Current saved middle PDF has **{len(middle_reader.pages)} page(s)**."
            )

            st.download_button(
                label="⬇️ Download Current Middle PDF",
                data=middle_bytes_for_download,
                file_name="permanent_middle.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"Unable to read the saved middle PDF: {exc}")

    replacement_file = st.file_uploader(
        "Upload or drag a PDF here to set or replace the permanent middle PDF",
        type=["pdf"],
        accept_multiple_files=False,
        key="middle_pdf_replacement_uploader",
    )

    if replacement_file is not None:
        if st.button(
            "Save as Permanent Middle PDF",
            use_container_width=True,
        ):
            try:
                save_middle_pdf(replacement_file)

                # Clear previously created output because its middle PDF may now differ.
                for key in (
                    "final_pdf_bytes",
                    "final_pdf_name",
                    "final_pdf_details",
                ):
                    st.session_state.pop(key, None)

                st.success(
                    "Permanent middle PDF saved successfully. It will be used automatically for future jobs."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save the permanent middle PDF: {exc}")

    st.write("### Folder access")

    st.caption(
        "A browser cannot directly open a folder on a remote web server. "
        "If this Streamlit app is running locally on your own computer, "
        "the button below can try to open the server storage folder. "
        "For online hosting, use the displayed path and the download button instead."
    )

    if st.button(
        "📂 Try to Open Server Folder",
        use_container_width=True,
    ):
        ok, message = try_open_server_folder()
        if ok:
            st.success(message)
        else:
            st.warning(
                "The folder could not be opened automatically on this server. "
                f"Storage path: {DATA_DIR}\n\nDetails: {message}"
            )

    st.caption(
        "For permanent cloud storage, set the `MIDDLE_PDF_DIR` environment variable "
        "to a persistent disk or volume mounted by your hosting provider."
    )
