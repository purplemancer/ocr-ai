Collecting workspace information# OCR API Service

This project provides a FastAPI-based OCR (Optical Character Recognition) service for extracting structured data from various Indian document types such as PAN cards, GST certificates, invoices, MSME certificates, cheques, CIN, DL, RC, and IEC documents.

## Features

- **Document Type Detection:** Supports multiple document types via the `query` parameter.
- **Async Processing:** Uses asynchronous methods for fast and efficient OCR.
- **Detailed Logging:** Logs request and response details for auditing and debugging.
- **Modular Design:** Each document type is handled by a dedicated PaddleOCR-based module.
