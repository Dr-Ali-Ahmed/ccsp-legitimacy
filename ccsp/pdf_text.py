"""PDF to text for the frozen corpus. Local, free, one second per paper.

Uses pdftotext (poppler) in layout mode; falls back to pypdf. A PDF whose
text layer is empty or nearly empty is a scan and is flagged for OCR or for
direct model reading, never silently passed through as blank.
"""

import pathlib
import subprocess


def pdf_to_text(pdf_path, min_chars=2000):
    pdf_path = pathlib.Path(pdf_path)
    text = ""
    try:
        text = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception:
        pass
    if len(text.strip()) < min_chars:
        try:
            import pypdf
            reader = pypdf.PdfReader(str(pdf_path))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception:
            pass
    status = "ok" if len(text.strip()) >= min_chars else "no_text_layer"
    return {"path": str(pdf_path), "chars": len(text.strip()), "status": status, "text": text}


if __name__ == "__main__":
    import json, sys
    for p in sys.argv[1:]:
        r = pdf_to_text(p)
        print(json.dumps({k: v for k, v in r.items() if k != "text"}))
