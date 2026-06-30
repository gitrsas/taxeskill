#!/usr/bin/env python3
"""
Tax Skill - PDF Form Parser
Extracts form metadata, field names, and structure from IRS PDF forms.
"""

import os
import sys
import json
import re
import PyPDF2
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class FormField:
    """Represents a single fillable field on a tax form."""
    name: str
    line_number: str = ""
    label: str = ""
    field_type: str = "text"  # text, number, date, checkbox, currency
    required: bool = False
    description: str = ""
    instructions: str = ""
    related_form: str = ""


@dataclass
class TaxForm:
    """Represents a complete tax form."""
    form_number: str  # e.g., "1040", "8936"
    form_name: str
    tax_year: int
    version: str = ""
    fields: List[FormField] = field(default_factory=list)
    schedules: List[str] = field(default_factory=list)
    instructions_url: str = ""
    irs_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class IRSFormParser:
    """Parses IRS PDF forms and extracts field structure."""

    def __init__(self, form_cache_dir: str = None):
        self.form_cache_dir = form_cache_dir or os.path.expanduser("~/Downloads/2025_IRS_Forms")
        self.parsed_forms: Dict[str, TaxForm] = {}

    def parse_pdf(self, pdf_path: str) -> TaxForm:
        """Parse a single IRS PDF form and extract its structure."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        reader = PyPDF2.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"

        form = self._extract_form_metadata(text, reader)
        form.fields = self._extract_fields(text)
        form.schedules = self._extract_schedules(text)
        form.instructions_url = self._find_instructions_url(text)
        form.irs_url = self._find_irs_url(pdf_path)

        self.parsed_forms[form.form_number] = form
        return form

    def _extract_form_metadata(self, text: str, reader: PyPDF2.PdfReader) -> TaxForm:
        """Extract form number, name, and year from PDF."""
        form_number = "unknown"
        form_name = "Unknown Form"
        tax_year = 0

        # Extract form number
        form_num_patterns = [
            r'(Form\s+(\d{3,4}))',
            r'(\d{3,4})\s+U\.?\s*S\.?\s+Individual',
        ]
        for pattern in form_num_patterns:
            m = re.search(pattern, text)
            if m:
                form_number = m.group(2) if m.lastindex == 2 else m.group(1)
                form_number = form_number.replace('Form ', '').strip()
                break

        # Extract form name
        name_patterns = [
            r'(\d{3,4}\s+U\.?\s*S\.?\s+Individual\s+Income\s+Tax\s+Return)',
            r'(Form\s+\d{3,4},?\s*([A-Z][^\n]{5,80}))',
            r'(Schedule\s+[A-Z0-9]+\s*\([^)]*\))',
        ]
        for pattern in name_patterns:
            m = re.search(pattern, text)
            if m:
                form_name = m.group(1).replace('\n', ' ').strip()
                form_name = re.sub(r'\s+', ' ', form_name)
                break

        # Extract tax year
        year_patterns = [
            r'(\d{4})\s*(?:Form|Schedule|U\.S\.|Individual)',
            r'(?:Form|schedule)\s+\d{3,4}\s*\([^)]*(\d{4})[^)]*\)',
            r'(?:created|rev\.?\s*)\s*(\d{2})-(\d{4})',
        ]
        for pattern in year_patterns:
            m = re.search(pattern, text)
            if m:
                groups = m.groups()
                for g in groups:
                    if g and len(g) == 4 and 2000 <= int(g) <= 2030:
                        tax_year = int(g)
                        break
                if tax_year:
                    break

        return TaxForm(
            form_number=form_number,
            form_name=form_name,
            tax_year=tax_year,
        )

    def _extract_fields(self, text: str) -> List[FormField]:
        """Extract fillable fields from form text."""
        fields = []

        # Pattern: "Line X - Description" or "Part X - Description"
        line_patterns = [
            r'(line\s+[\d\w]+)\s*[,.-]\s*([A-Z][^\n]{5,150})',
            r'(\d+)\s+([A-Z][^\n]{5,150})',
        ]

        seen = set()
        for pattern in line_patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                line_ref = m.group(1).strip()
                label = m.group(2).strip()

                # Skip if too generic or too long
                if len(label) < 5 or len(label) > 200:
                    continue
                if label.lower() in seen:
                    continue

                # Clean up label
                label = re.sub(r'\s+', ' ', label).strip()
                label = re.sub(r'[^\w\s.,();\-:]', '', label).strip()

                key = f"{line_ref}:{label[:30]}"
                if key in seen:
                    continue
                seen.add(key)

                # Determine field type
                field_type = "text"
                if 'ssn' in label.lower() or 'social' in label.lower():
                    field_type = "text"
                elif '$' in label or 'dollars' in label.lower() or 'amount' in label.lower():
                    field_type = "currency"
                elif 'check' in label.lower() or 'yes' in label.lower() or 'no' in label.lower():
                    field_type = "checkbox"
                elif 'date' in label.lower():
                    field_type = "date"
                elif any(word in label.lower() for word in ['name', 'address', 'city', 'state', 'zip']):
                    field_type = "text"

                fields.append(FormField(
                    name=line_ref,
                    line_number=line_ref,
                    label=label[:100],
                    field_type=field_type,
                ))

        return fields[:200]  # Limit to keep it manageable

    def _extract_schedules(self, text: str) -> List[str]:
        """Extract schedule references."""
        schedules = set()
        for m in re.finditer(r'(Schedule\s+[A-Z0-9\s]+(?:\([^)]*\))?)', text):
            sched = m.group(1).strip()
            sched = re.sub(r'\s+', ' ', sched)
            schedules.add(sched)
        return sorted(schedules)

    def _find_instructions_url(self, text: str) -> str:
        """Find instructions URL in form text."""
        m = re.search(r'www\.irs\.gov/(\S+)', text)
        if m:
            return f"https://www.irs.gov/{m.group(1).strip()}"
        return ""

    def _find_irs_url(self, pdf_path: str) -> str:
        """Generate IRS URL from form filename."""
        basename = os.path.basename(pdf_path).lower()
        m = re.search(r'f(\d+)', basename)
        if m:
            return f"https://www.irs.gov/forms-pubs/about/form-{m.group(1)}"
        return ""

    def save_form(self, form: TaxForm, output_dir: str = None) -> str:
        """Save parsed form metadata as JSON."""
        out_dir = output_dir or self.form_cache_dir
        os.makedirs(out_dir, exist_ok=True)

        filepath = os.path.join(out_dir, f"{form.form_number}_{form.tax_year}.json")
        with open(filepath, 'w') as f:
            json.dump(form.to_dict(), f, indent=2)

        return filepath

    def parse_all_pdfs(self, pdf_dir: str = None) -> Dict[str, TaxForm]:
        """Parse all PDFs in a directory."""
        target_dir = pdf_dir or self.form_cache_dir
        for filename in os.listdir(target_dir):
            if filename.endswith('.pdf') and filename.startswith('f'):
                pdf_path = os.path.join(target_dir, filename)
                try:
                    form = self.parse_pdf(pdf_path)
                    self.save_form(form)
                    print(f"  Parsed: {filename} → {form.form_number} ({form.tax_year})")
                except Exception as e:
                    print(f"  Error parsing {filename}: {e}")
        return self.parsed_forms


def main():
    """CLI entry point."""
    pdf_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/2025_IRS_Forms")

    if not os.path.exists(pdf_dir):
        print(f"Directory not found: {pdf_dir}")
        sys.exit(1)

    parser = IRSFormParser(pdf_dir)
    forms = parser.parse_all_pdfs(pdf_dir)

    print(f"\nParsed {len(forms)} forms:")
    for form_num, form in sorted(forms.items()):
        print(f"  {form.form_number} - {form.form_name[:50]} ({form.tax_year})")
        print(f"    Fields: {len(form.fields)} | Schedules: {len(form.schedules)}")


if __name__ == "__main__":
    main()
