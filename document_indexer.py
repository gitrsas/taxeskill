#!/usr/bin/env python3
"""
Tax Skill - Tax Document Indexer
Scans the user's tax folder and indexes all available tax documents.
"""

import os
import sys
import json
import re
import PyPDF2
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime


@dataclass
class TaxDocument:
    """Represents a tax document found in the user's folder."""
    filename: str
    filepath: str
    year: int
    doc_type: str  # W2, 1099-INT, 1099-DIV, 1099-NEC, 1099-R, 1099-SA, 1099-Q, 1098, etc.
    employer_name: str = ""
    employee_name: str = ""
    ssn_last4: str = ""
    state: str = ""
    wages_amount: float = 0.0
    federal_withheld: float = 0.0
    state_wages: float = 0.0
    state_tax_withheld: float = 0.0
    boxes: Dict[str, Any] = field(default_factory=dict)
    raw_text_preview: str = ""
    parsed: bool = False
    parse_error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class TaxDocumentIndexer:
    """Indexes tax documents from the user's tax folder."""

    def __init__(self, tax_base_dir: str = None):
        self.tax_base_dir = tax_base_dir or "/Volumes/volume_1-1/kevin/Taxes"
        self.documents: List[TaxDocument] = []
        self.index_file = os.path.join(self.tax_base_dir, ".taxskill", "document_index.json")

    def scan_folder(self) -> List[TaxDocument]:
        """Scan the tax folder structure for all documents."""
        self.documents = []

        # Get years to scan
        years = self._detect_years()

        for year in years:
            year_folder = os.path.join(self.tax_base_dir, f"{year} Tax Information")
            if not os.path.exists(year_folder):
                continue

            # Scan all subdirectories
            for root, dirs, files in os.walk(year_folder):
                for filename in files:
                    if filename.endswith('.pdf'):
                        filepath = os.path.join(root, filename)
                        doc = self._analyze_document(filepath, year)
                        if doc:
                            self.documents.append(doc)

        return self.documents

    def _detect_years(self) -> List[int]:
        """Detect which tax years have folders."""
        years = []
        for entry in os.listdir(self.tax_base_dir):
            m = re.match(r'(\d{4})\s+Tax\s+Information', entry)
            if m:
                years.append(int(m.group(1)))
        return sorted(years)

    def _analyze_document(self, filepath: str, year: int) -> Optional[TaxDocument]:
        """Analyze a single PDF to determine its type and extract metadata."""
        filename = os.path.basename(filepath)

        # Quick type detection from filename
        doc_type = self._detect_type_from_filename(filename)
        if not doc_type:
            # Try to detect from content
            doc_type = self._detect_type_from_content(filepath)

        doc = TaxDocument(
            filename=filename,
            filepath=filepath,
            year=year,
            doc_type=doc_type,
        )

        # Try to parse the document
        try:
            self._parse_document(doc)
            doc.parsed = True
        except Exception as e:
            doc.parse_error = str(e)

        return doc

    def _detect_type_from_filename(self, filename: str) -> Optional[str]:
        """Detect document type from filename."""
        fname = filename.lower()

        if 'w2' in fname:
            return 'W2'
        if '1099' in fname:
            # Try to extract subtype
            m = re.search(r'1099[^\s]*', fname)
            if m:
                return m.group(0).upper().replace('.', '')
            return '1099'

        if '1040' in fname or 'tax return' in fname:
            return '1040'

        if 'schedule' in fname:
            return 'SCHEDULE'

        if 'estimate' in fname or 'voucher' in fname:
            return 'ESTIMATE'

        if 'receipt' in fname or 'invoice' in fname:
            return 'RECEIPT'

        return None

    def _detect_type_from_content(self, filepath: str) -> str:
        """Detect document type from PDF content."""
        try:
            reader = PyPDF2.PdfReader(filepath)
            text = ""
            for page in reader.pages[:2]:
                text += (page.extract_text() or "") + "\n"

            text_lower = text.lower()

            if 'w-2' in text_lower or 'form w-2' in text_lower:
                return 'W2'
            if 'form 1099-int' in text_lower:
                return '1099-INT'
            if 'form 1099-div' in text_lower:
                return '1099-DIV'
            if 'form 1099-NEC' in text_lower or 'form 1099-nec' in text_lower:
                return '1099-NEC'
            if 'form 1099-R' in text_lower:
                return '1099-R'
            if 'form 1099-SA' in text_lower or 'form 1099-sa' in text_lower:
                return '1099-SA'
            if 'form 1099-Q' in text_lower:
                return '1099-Q'
            if 'form 1098' in text_lower:
                return '1098'
            if 'form 1040' in text_lower:
                return '1040'

            return 'OTHER'
        except:
            return 'UNKNOWN'

    def _parse_document(self, doc: TaxDocument):
        """Parse document content and extract key fields."""
        reader = PyPDF2.PdfReader(doc.filepath)
        text = ""
        for page in reader.pages[:5]:
            text += (page.extract_text() or "") + "\n"

        doc.raw_text_preview = text[:2000]

        if doc.doc_type == 'W2':
            self._parse_w2(doc, text)
        elif doc.doc_type.startswith('1099'):
            self._parse_1099(doc, text)

    def _parse_w2(self, doc: TaxDocument, text: str):
        """Parse W-2 form."""
        doc.employer_name = self._extract_field(text, ['employer', 'name', 'control'])
        doc.employee_name = self._extract_field(text, ['employee', 'name', 'control'])
        doc.ssn_last4 = self._extract_ssn(text)
        doc.state = self._extract_state(text)

        # Extract amounts
        wages_match = re.search(r'(?:wages\s*,\s*tips\s*,?\s*other\s*compensation)\s*[:\-]?\s*\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
        if wages_match:
            doc.wages_amount = float(wages_match.group(1).replace(',', ''))

        fed_match = re.search(r'(?:federal\s+income\s+tax\s+withheld)\s*[:\-]?\s*\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
        if fed_match:
            doc.federal_withheld = float(fed_match.group(1).replace(',', ''))

        doc.boxes = {
            'wages': doc.wages_amount,
            'federal_withheld': doc.federal_withheld,
        }

    def _parse_1099(self, doc: TaxDocument, text: str):
        """Parse 1099 variants."""
        doc.boxes = {}

        if '1099-INT' in doc.doc_type:
            # Interest income
            m = re.search(r'(?:interest\s*income)\s*[:\-]?\s*\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
            if m:
                doc.boxes['interest_income'] = float(m.group(1).replace(',', ''))

        elif '1099-DIV' in doc.doc_type:
            # Dividends
            m = re.search(r'(?:ordinary\s*dividends)\s*[:\-]?\s*\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
            if m:
                doc.boxes['ordinary_dividends'] = float(m.group(1).replace(',', ''))

        elif '1099-NEC' in doc.doc_type:
            # Non-employee compensation
            m = re.search(r'(?:nonemployee\s*compensation)\s*[:\-]?\s*\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
            if m:
                doc.boxes['nonemployee_comp'] = float(m.group(1).replace(',', ''))

        elif '1099-R' in doc.doc_type:
            # Retirement distribution
            m = re.search(r'(?:total\s*distribution)\s*[:\-]?\s*\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
            if m:
                doc.boxes['total_distribution'] = float(m.group(1).replace(',', ''))

    def _extract_field(self, text: str, keywords: List[str]) -> str:
        """Extract a field value based on keywords."""
        for keyword in keywords:
            m = re.search(rf'{keyword}\s*[:\-]?\s*\$?([^\n]{3,100})', text, re.IGNORECASE)
            if m:
                return m.group(1).strip()[:100]
        return ""

    def _extract_ssn(self, text: str) -> str:
        """Extract last 4 digits of SSN."""
        m = re.search(r'(\d{3})[-\s]\d{2}[-\s](\d{4})', text)
        if m:
            return m.group(2)
        return ""

    def _extract_state(self, text: str) -> str:
        """Extract state code."""
        m = re.search(r'(?:state\s+code|state)\s*[:\-]?\s*([A-Z]{2})', text, re.IGNORECASE)
        if m:
            return m.group(1)
        return ""

    def save_index(self):
        """Save the document index to JSON."""
        index_dir = os.path.join(self.tax_base_dir, ".taxskill")
        os.makedirs(index_dir, exist_ok=True)

        index_data = {
            "last_scanned": datetime.now().isoformat(),
            "tax_base_dir": self.tax_base_dir,
            "total_documents": len(self.documents),
            "documents_by_type": {},
            "documents_by_year": {},
            "documents": [doc.to_dict() for doc in self.documents],
        }

        # Count by type
        for doc in self.documents:
            doc.boxes = {}  # Don't serialize raw text preview
            by_type = index_data["documents_by_type"].setdefault(doc.doc_type, 0)
            index_data["documents_by_type"][doc.doc_type] = by_type + 1

            by_year = index_data["documents_by_year"].setdefault(str(doc.year), 0)
            index_data["documents_by_year"][str(doc.year)] = by_year + 1

        with open(self.index_file, 'w') as f:
            json.dump(index_data, f, indent=2)

        return self.index_file

    def load_index(self) -> Optional[dict]:
        """Load the document index from JSON."""
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return None


def main():
    """CLI entry point."""
    tax_dir = sys.argv[1] if len(sys.argv) > 1 else "/Volumes/volume_1-1/kevin/Taxes"

    if not os.path.exists(tax_dir):
        print(f"Directory not found: {tax_dir}")
        sys.exit(1)

    indexer = TaxDocumentIndexer(tax_dir)
    docs = indexer.scan_folder()
    index_file = indexer.save_index()

    print(f"Indexed {len(docs)} documents:")
    print(f"  Index saved to: {index_file}")

    # Summary by type
    by_type = {}
    for doc in docs:
        by_type[doc.doc_type] = by_type.get(doc.doc_type, 0) + 1

    print("\nBy type:")
    for doc_type, count in sorted(by_type.items()):
        print(f"  {doc_type}: {count}")

    # Summary by year
    by_year = {}
    for doc in docs:
        by_year[doc.year] = by_year.get(doc.year, 0) + 1

    print("\nBy year:")
    for year, count in sorted(by_year.items()):
        print(f"  {year}: {count}")


if __name__ == "__main__":
    main()
