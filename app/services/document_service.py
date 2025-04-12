import csv
import io
import os
import tempfile
import traceback

import docx
import pdfplumber
from docx import Document
from langchain.schema import Document as LangChainDoc
from langchain.text_splitter import RecursiveCharacterTextSplitter
from werkzeug.utils import secure_filename

from app.utils.logging_config import logger, log_performance


@log_performance(logger)
def extract_text_from_file(file):
    """
    Extract text content from various file types (PDF, DOCX, TXT, CSV).
    Returns the extracted text as a string.
    """
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    file_size = 0
    
    try:
        # Get file size if available
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
    except:
        # If we can't get file size, continue without it
        pass
    
    logger.info(f"Extracting text from file: {filename} (type: {file_ext}, size: {file_size/1024:.2f}KB)")

    # ----- PDF Handling -----
    if file_ext == '.pdf':
        temp_file_path = None
        try:
            # 1) Save the uploaded PDF to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                file.save(tmp.name)
                temp_file_path = tmp.name
                logger.debug(f"Saved PDF to temporary file: {temp_file_path}")

            # 2) Open and read the PDF using pdfplumber
            extracted_text = ""
            total_pages = 0
            empty_pages = 0
            
            with pdfplumber.open(temp_file_path) as doc:
                total_pages = len(doc.pages)
                for page_num, page in enumerate(doc.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
                        logger.debug(f"Processed PDF page {page_num}/{total_pages} - {len(page_text)} chars")
                    else:
                        empty_pages += 1
                        logger.debug(f"Processed PDF page {page_num}/{total_pages} - Empty page")
            
            # Log statistics about PDF extraction
            logger.info(f"Successfully extracted PDF: {len(extracted_text)} chars, {total_pages} pages ({empty_pages} empty)")
            return extracted_text

        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"PDF extraction error: {str(e)}\n{error_details}")
            raise
        finally:
            # 3) Clean up the temp file
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.debug(f"Removed temporary PDF file: {temp_file_path}")

    # ----- DOCX Handling -----
    elif file_ext == '.docx':
        try:
            doc = docx.Document(io.BytesIO(file.read()))
            total_paragraphs = len(doc.paragraphs)
            empty_paragraphs = 0
            paragraphs = []
            
            for i, paragraph in enumerate(doc.paragraphs):
                if paragraph.text.strip():
                    paragraphs.append(paragraph.text)
                else:
                    empty_paragraphs += 1
            
            extracted_text = "\n".join(paragraphs)
            logger.info(f"Successfully extracted DOCX: {len(extracted_text)} chars, {total_paragraphs} paragraphs ({empty_paragraphs} empty)")
            return extracted_text
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"DOCX extraction error: {str(e)}\n{error_details}")
            raise

    # ----- TXT Handling -----
    elif file_ext == '.txt':
        try:
            # Attempt UTF-8 first, fall back to other encodings if needed
            content = None
            encodings = ['utf-8', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    file.seek(0)  # Reset file pointer
                    content = file.read().decode(encoding)
                    logger.debug(f"Successfully decoded TXT with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    logger.debug(f"Failed to decode TXT with {encoding} encoding, trying next")
                    continue
            
            if content is None:
                # If all encodings failed, use replace mode with utf-8
                file.seek(0)
                content = file.read().decode('utf-8', errors='replace')
                logger.warning("TXT file decoded with replacement characters due to encoding issues")
                
            # Count lines and words
            line_count = content.count('\n') + 1
            word_count = len(content.split())
            
            logger.info(f"Successfully extracted TXT: {len(content)} chars, {line_count} lines, {word_count} words")
            return content
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"TXT extraction error: {str(e)}\n{error_details}")
            raise

    # ----- CSV Handling -----
    elif file_ext == '.csv':
        try:
            content = file.read().decode('utf-8', errors='replace')
            row_count = 0
            col_count = 0
            
            # Parse CSV to get row and column counts
            csv_reader = csv.reader(io.StringIO(content))
            rows = list(csv_reader)
            row_count = len(rows)
            if row_count > 0:
                col_count = len(rows[0])
            
            # Create the extracted text
            extracted_text = "\n".join([",".join(row) for row in rows])
            
            logger.info(f"Successfully extracted CSV: {len(extracted_text)} chars, {row_count} rows, {col_count} columns")
            return extracted_text
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"CSV extraction error: {str(e)}\n{error_details}")
            raise

    else:
        error_msg = f"Unsupported file extension: {file_ext}"
        logger.error(error_msg)
        raise ValueError(error_msg)


@log_performance(logger)
def load_docx(path: str):
    """
    Load content from .docx or .txt files and return as a LangChain Document.
    """
    logger.info(f"Loading document from: {path}")
    try:
        file_ext = os.path.splitext(path)[1].lower()
        
        # Check if file exists
        if not os.path.isfile(path):
            logger.error(f"Document not found: {path}")
            return LangChainDoc(page_content="This is a default reference text. The document could not be found.")
        
        # Get file size
        file_size = os.path.getsize(path)
        logger.debug(f"Document size: {file_size/1024:.2f}KB")
        
        if file_ext == '.docx':
            doc = Document(path)
            para_count = len(doc.paragraphs)
            empty_para_count = sum(1 for para in doc.paragraphs if not para.text.strip())
            full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip() != ""])
            
            logger.debug(f"Loaded {para_count} paragraphs from DOCX ({empty_para_count} empty)")
            logger.info(f"Document loaded: {len(full_text)} characters")
        
        elif file_ext == '.txt':
            with open(path, 'r', encoding='utf-8') as f:
                full_text = f.read()
                
            line_count = full_text.count('\n') + 1
            word_count = len(full_text.split())
            logger.debug(f"Loaded {line_count} lines, {word_count} words from TXT file")
            logger.info(f"Document loaded: {len(full_text)} characters")
        
        else:
            logger.error(f"Unsupported file type: {file_ext}")
            raise ValueError(f"Unsupported file type: {file_ext}")

        return LangChainDoc(page_content=full_text)
    
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error loading document: {str(e)}\n{error_details}")
        # Return a default document with some basic information
        return LangChainDoc(page_content="This is a default reference text. The actual document could not be loaded.")


@log_performance(logger)
def load_and_chunk_document(file_path: str, chunk_size: int = 1500, chunk_overlap: int = 200):
    """
    Load a document and split it into chunks for processing.
    """
    logger.info(f"Loading and chunking document: {file_path} (chunk_size={chunk_size}, overlap={chunk_overlap})")
    doc = load_docx(file_path)
    
    # Split if needed for large files
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    doc_chunks = splitter.split_documents([doc])
    
    # Calculate average chunk size
    total_chars = sum(len(chunk.page_content) for chunk in doc_chunks)
    avg_chunk_size = total_chars / len(doc_chunks) if doc_chunks else 0
    
    logger.info(f"Document split into {len(doc_chunks)} chunks (avg size: {avg_chunk_size:.2f} chars)")
    
    # Log detailed info about chunks
    for i, chunk in enumerate(doc_chunks):
        logger.debug(f"Chunk {i+1}/{len(doc_chunks)}: {len(chunk.page_content)} chars")
    
    # Return all chunks
    return doc_chunks 