import re
import os
import io
import pypdf
from pypdf.errors import PdfReadError

def clean_extracted_text(text: str) -> str:
    """
    Cleans raw extracted text from a PDF document:
    - Normalizes carriage returns and tabs
    - Collapses multiple horizontal spaces
    - Collapses excessive empty lines (more than 2 consecutive newlines)
    - Strips leading and trailing whitespace
    """
    if not text:
        return ""

    # Replace carriage returns and vertical tabs
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\t', ' ')

    # Remove non-printable control characters except standard newline
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Collapse multiple consecutive horizontal spaces to a single space
    text = re.sub(r'[^\S\n]+', ' ', text)

    # Collapse 3 or more newlines down to 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def extract_text_from_pdf(pdf_source) -> dict:
    """
    Reusable service function to extract and clean text from an uploaded PDF CV.
    
    Accepts:
      - File path (str)
      - Django File / FieldFile (e.g. application.cv)
      - Bytes / io.BytesIO buffer
      
    Returns a dictionary:
      {
        'success': bool,
        'text': str,
        'page_count': int,
        'status': 'SUCCESS' | 'EMPTY' | 'ERROR',
        'error_message': str,
      }
    """
    result = {
        'success': False,
        'text': '',
        'page_count': 0,
        'status': 'ERROR',
        'error_message': '',
    }

    if not pdf_source:
        result['error_message'] = "No PDF file was provided for extraction."
        return result

    file_obj = None
    close_file = False

    try:
        # Determine source type
        if isinstance(pdf_source, (str, os.PathLike)):
            if not os.path.exists(pdf_source):
                result['error_message'] = f"The specified PDF file does not exist on disk: {pdf_source}"
                return result
            file_obj = open(pdf_source, 'rb')
            close_file = True
        elif isinstance(pdf_source, bytes):
            file_obj = io.BytesIO(pdf_source)
        elif hasattr(pdf_source, 'open'):
            # Django FieldFile
            pdf_source.open('rb')
            file_obj = pdf_source.file
        elif hasattr(pdf_source, 'read'):
            file_obj = pdf_source
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
        else:
            result['error_message'] = "Unsupported PDF source format."
            return result

        # Check for empty file (0 bytes)
        if hasattr(file_obj, 'seek') and hasattr(file_obj, 'tell'):
            file_obj.seek(0, os.SEEK_END)
            size = file_obj.tell()
            file_obj.seek(0)
            if size == 0:
                result['status'] = 'EMPTY'
                result['error_message'] = "The uploaded PDF file is empty (0 bytes)."
                return result

        # Safely open with pypdf
        try:
            reader = pypdf.PdfReader(file_obj)
        except PdfReadError as e:
            result['status'] = 'ERROR'
            result['error_message'] = f"Corrupted or invalid PDF structure: {str(e)}"
            return result
        except Exception as e:
            result['status'] = 'ERROR'
            result['error_message'] = f"Failed to initialize PDF reader: {str(e)}"
            return result

        # Check encryption / password protection
        if reader.is_encrypted:
            try:
                # Try decrypting with blank password
                decrypted = reader.decrypt('')
                if not decrypted:
                    result['status'] = 'ERROR'
                    result['error_message'] = "The PDF is password-protected and cannot be parsed."
                    return result
            except Exception:
                result['status'] = 'ERROR'
                result['error_message'] = "The PDF is encrypted with a secure password."
                return result

        num_pages = len(reader.pages)
        result['page_count'] = num_pages

        if num_pages == 0:
            result['status'] = 'EMPTY'
            result['error_message'] = "The PDF contains 0 pages."
            return result

        extracted_pages = []
        for page_idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text)
            except Exception as page_err:
                # Log page extraction error and proceed to remaining pages
                continue

        raw_combined = "\n\n".join(extracted_pages)
        cleaned_text = clean_extracted_text(raw_combined)

        if not cleaned_text:
            result['status'] = 'EMPTY'
            result['error_message'] = "No readable text could be extracted from this PDF. It may consist solely of scanned images without selectable text."
            return result

        result['success'] = True
        result['text'] = cleaned_text
        result['status'] = 'SUCCESS'
        result['error_message'] = ""
        return result

    except Exception as e:
        result['status'] = 'ERROR'
        result['error_message'] = f"Unexpected error during PDF text extraction: {str(e)}"
        return result

    finally:
        if close_file and file_obj:
            try:
                file_obj.close()
            except Exception:
                pass
