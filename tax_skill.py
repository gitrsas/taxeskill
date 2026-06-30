#!/usr/bin/env python3
"""
Tax Skill - Main Orchestrator
Interviews the user, coordinates document parsing, form filling, and validation.
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path

# Add tax skill directory to path
TAX_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TAX_SKILL_DIR)

from pdf_form_parser import IRSFormParser, TaxForm
from document_indexer import TaxDocumentIndexer, TaxDocument
from irs_form_updater import IRSFormUpdater


class TaxSkillOrchestrator:
    """Main orchestrator for the tax preparation skill."""

    def __init__(self, tax_base_dir: str = None):
        self.tax_base_dir = tax_base_dir or "/Volumes/volume_1-1/kevin/Taxes"
        self.profile_file = os.path.join(self.tax_base_dir, ".taxskill", "profile.json")
        self.profile = self._load_profile()
        self.indexer = TaxDocumentIndexer(self.tax_base_dir)
        self.parser = IRSFormParser()
        self.updater = IRSFormUpdater()

    def _load_profile(self) -> dict:
        """Load the user's tax profile."""
        if os.path.exists(self.profile_file):
            with open(self.profile_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_profile(self):
        """Save the user's tax profile."""
        with open(self.profile_file, 'w') as f:
            json.dump(self.profile, f, indent=2)

    def scan_documents(self) -> list:
        """Scan for all tax documents."""
        print("\n📂 Scanning tax folder for documents...")
        docs = self.indexer.scan_folder()
        self.indexer.save_index()

        by_type = {}
        for doc in docs:
            by_type[doc.doc_type] = by_type.get(doc.doc_type, 0) + 1

        print(f"  Found {len(docs)} documents:")
        for doc_type, count in sorted(by_type.items()):
            print(f"    {doc_type}: {count}")

        return docs

    def check_form_updates(self) -> dict:
        """Check for IRS form updates."""
        print("\n🔄 Checking IRS for form updates...")
        results = self.updater.check_all_forms()
        updated = [k for k, v in results.items() if v.get('status') == 'updated']
        if updated:
            print(f"  ✅ {len(updated)} forms updated")
        else:
            print(f"  ✓ All forms up to date")
        return results

    def check_tax_code_changes(self) -> list:
        """Check for tax code changes affecting the user."""
        changes = self.updater.check_tax_code_changes()
        personalized = self.updater.get_personalized_impact(self.profile)

        print("\n📋 Tax Code Changes:")
        for change in personalized:
            print(f"  • [{change.get('type', 'unknown').upper()}] {change.get('description', '')}")
        return personalized

    def get_required_forms(self) -> list:
        """Determine which forms are needed based on user's situation."""
        required = []

        # Base forms always needed
        required.append({
            "form": "1040",
            "name": "U.S. Individual Income Tax Return",
            "required": True,
            "reason": "Base federal return"
        })

        # Check profile for additional forms
        profile = self.profile

        # Schedule 1 if additional income/adjustments
        if profile.get('income_sources', {}).get('self_employment', {}).get('has_schedule_c'):
            required.append({
                "form": "schedule_1",
                "name": "Schedule 1",
                "required": True,
                "reason": "Additional income or adjustments"
            })

        # Schedule C if self-employment
        if profile.get('income_sources', {}).get('self_employment', {}).get('has_schedule_c'):
            required.append({
                "form": "schedule_c",
                "name": "Schedule C",
                "required": True,
                "reason": "Business income/loss"
            })

        # Schedule A if itemizing
        if profile.get('deductions', {}).get('itemized'):
            required.append({
                "form": "schedule_a",
                "name": "Schedule A",
                "required": True,
                "reason": "Itemized deductions"
            })

        # Schedule D if capital gains
        if profile.get('income_sources', {}).get('investments', {}).get('has_1099_b'):
            required.append({
                "form": "schedule_d",
                "name": "Schedule D",
                "required": True,
                "reason": "Capital gains/losses"
            })

        # Schedule SE if self-employment income
        if profile.get('income_sources', {}).get('self_employment', {}).get('has_schedule_c'):
            required.append({
                "form": "schedule_se",
                "name": "Schedule SE",
                "required": True,
                "reason": "Self-employment tax"
            })

        # Schedule B if interest/dividends > $1,500
        if profile.get('income_sources', {}).get('investments', {}).get('has_1099_int'):
            required.append({
                "form": "schedule_b",
                "name": "Schedule B",
                "required": True,
                "reason": "Interest and ordinary dividends"
            })

        # Schedule 3 if credits
        if profile.get('credits', {}).get('earned_income_credit', {}).get('eligible'):
            required.append({
                "form": "schedule_3",
                "name": "Schedule 3",
                "required": True,
                "reason": "Additional credits"
            })

        # Schedule 8812 if child tax credit
        if profile.get('credits', {}).get('child_tax_credit', {}).get('eligible'):
            required.append({
                "form": "schedule_8812",
                "name": "Schedule 8812",
                "required": True,
                "reason": "Child and dependent credits"
            })

        # Form 4562 if depreciation
        if profile.get('property', {}).get('depreciation', {}).get('section_179', 0) > 0:
            required.append({
                "form": "4562",
                "name": "Form 4562",
                "required": True,
                "reason": "Depreciation and amortization"
            })

        # Form 5329 if early distributions
        if profile.get('tax_favored_accounts', {}).get('ira', {}).get('traditional', {}).get('distributions', 0) > 0:
            required.append({
                "form": "5329",
                "name": "Form 5329",
                "required": True,
                "reason": "Additional taxes on qualified plans"
            })

        # Form 8606 if nondeductible IRA
        if profile.get('tax_favored_accounts', {}).get('ira', {}).get('traditional', {}).get('nondeductible', 0) > 0:
            required.append({
                "form": "8606",
                "name": "Form 8606",
                "required": True,
                "reason": "Nondeductible IRAs"
            })

        # Form 8812 if child tax credit
        if profile.get('credits', {}).get('child_tax_credit', {}).get('eligible'):
            required.append({
                "form": "8812",
                "name": "Schedule 8812",
                "required": True,
                "reason": "Credits for child and dependents"
            })

        # Form 8867 if claiming EIC
        if profile.get('credits', {}).get('earned_income_credit', {}).get('eligible'):
            required.append({
                "form": "8867",
                "name": "Form 8867",
                "required": True,
                "reason": "Paid preparer EIC checklist"
            })

        # Form 8879 if e-filing
        if profile.get('preferences', {}).get('filing_method') == 'e-file':
            required.append({
                "form": "8879",
                "name": "Form 8879",
                "required": True,
                "reason": "e-file authorization"
            })

        # Form 8889 if HSA
        if profile.get('tax_favored_accounts', {}).get('hsa', {}).get('has_account'):
            required.append({
                "form": "8889",
                "name": "Form 8889",
                "required": True,
                "reason": "Health Savings Accounts"
            })

        # Form 8936 if EV credit
        if profile.get('credits', {}).get('clean_vehicle', {}).get('new_vehicle', {}).get('eligible'):
            required.append({
                "form": "8936",
                "name": "Form 8936",
                "required": True,
                "reason": "Qualified plug-in electric vehicle credit"
            })

        # Form 9325 if adoption
        if profile.get('credits', {}).get('adoption', {}).get('eligible'):
            required.append({
                "form": "9325",
                "name": "Form 9325",
                "required": True,
                "reason": "Adoption information"
            })

        # Foreign forms
        if profile.get('foreign', {}).get('form_3520_required'):
            required.append({
                "form": "3520",
                "name": "Form 3520",
                "required": True,
                "reason": "Foreign trust and large cash transfers"
            })

        if profile.get('foreign', {}).get('form_8938_required'):
            required.append({
                "form": "8938",
                "name": "Form 8938",
                "required": True,
                "reason": "Foreign financial asset statement"
            })

        return required

    def show_status(self):
        """Show current tax preparation status."""
        print("\n" + "="*60)
        print("  TAX SKILL - PREPARATION STATUS")
        print("="*60)

        profile = self.profile
        filing_status = profile.get('filing_status', {}).get('status', 'unknown')
        dependents = profile.get('dependents', [])
        has_dependents = any(d.get('age', 0) < 17 for d in dependents)

        print(f"\n  Filing Status: {filing_status}")
        print(f"  Dependents (under 17): {sum(1 for d in dependents if d.get('age', 0) < 17)}")
        print(f"  State: {profile.get('address', {}).get('state', 'NC')}")

        # Check documents
        docs = self.indexer.load_index()
        if docs:
            print(f"\n  Documents indexed: {docs.get('total_documents', 0)}")
            by_type = docs.get('documents_by_type', {})
            for doc_type, count in sorted(by_type.items()):
                print(f"    {doc_type}: {count}")

        # Required forms
        required = self.get_required_forms()
        print(f"\n  Required forms: {len(required)}")
        for form in required:
            status = "✓" if form.get('filled') else "○"
            print(f"    {status} {form['form']} - {form['name']}")

        # Standard deduction for 2025
        std_deduction = {
            'married_joint': 29200,
            'single': 14600,
            'head_of_household': 21900,
            'qualifying_surviving_spouse': 29200,
        }
        std = std_deduction.get(filing_status, 14600)
        print(f"\n  2025 Standard Deduction: ${std:,}")

        print("="*60 + "\n")

    def ask_question(self, question: str, default=None, field_type: str = "text") -> str:
        """Ask the user a question."""
        if default:
            prompt = f"  {question} [{default}]: "
        else:
            prompt = f"  {question}: "

        try:
            answer = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return default or ""

        if not answer and default:
            return default
        return answer

    def interview(self):
        """Run the tax preparation interview."""
        print("\n" + "="*60)
        print("  TAX SKILL - PREPARATION INTERVIEW")
        print("="*60)

        # Phase 1: Personal info
        print("\n👤 Phase 1: Personal Information")
        print("-" * 40)

        filing_status = self.ask_question(
            "Filing status?",
            default=self.profile.get('filing_status', {}).get('status', 'married_joint')
        )
        self.profile['filing_status'] = {'status': filing_status}

        # Phase 2: Dependents
        print("\n👶 Phase 2: Dependents")
        print("-" * 40)

        num_dependents = int(self.ask_question(
            "Number of dependents under 17?",
            default=str(len([d for d in self.profile.get('dependents', []) if d.get('age', 0) < 17]))
        ))

        # Phase 3: Income
        print("\n💰 Phase 3: Income")
        print("-" * 40)

        has_w2 = self.ask_question(
            "Do you have W-2 forms to drop?",
            default="yes"
        )

        has_1099 = self.ask_question(
            "Do you have 1099 forms to drop?",
            default="no"
        )

        # Phase 4: Deductions
        print("\n📝 Phase 4: Deductions")
        print("-" * 40)

        itemize = self.ask_question(
            "Will you itemize deductions?",
            default="no"
        )
        self.profile['deductions'] = {'standard': itemize.lower() == 'no', 'itemized': itemize.lower() == 'yes'}

        # Phase 5: Credits
        print("\n🎁 Phase 5: Credits")
        print("-" * 40)

        has_ev = self.ask_question(
            "Did you purchase a qualified electric vehicle?",
            default="no"
        )
        if has_ev.lower() == 'yes':
            self.profile['credits']['clean_vehicle']['new_vehicle']['eligible'] = True

        has_adoption = self.ask_question(
            "Do you have adoption expenses?",
            default="no"
        )
        if has_adoption.lower() == 'yes':
            self.profile['credits']['adoption']['eligible'] = True

        # Phase 6: Payments
        print("\n💳 Phase 6: Payments")
        print("-" * 40)

        refund_method = self.ask_question(
            "Refund method? (direct_deposit / mail_check)",
            default=self.profile.get('preferences', {}).get('refund_method', 'mail_check')
        )
        self.profile['preferences']['refund_method'] = refund_method

        # Save profile
        self._save_profile()

        print("\n" + "="*60)
        print("  Interview complete! Profile saved.")
        print("="*60 + "\n")

    def validate_return(self) -> dict:
        """Validate the tax return for errors and inconsistencies."""
        issues = []
        warnings = []

        profile = self.profile

        # Check for missing required info
        if not profile.get('filing_status', {}).get('status'):
            issues.append("Missing filing status")

        if not profile.get('address', {}).get('state'):
            warnings.append("Missing state information")

        # Check for common errors
        if profile.get('credits', {}).get('child_tax_credit', {}).get('eligible'):
            if not any(d.get('age', 0) < 17 for d in profile.get('dependents', [])):
                warnings.append("Child Tax Credit claimed but no dependents under 17 found")

        # Check EV credit eligibility
        if profile.get('credits', {}).get('clean_vehicle', {}).get('new_vehicle', {}).get('eligible'):
            vehicle = profile['credits']['clean_vehicle']['new_vehicle']['vehicle_info']
            if not vehicle.get('vin'):
                warnings.append("EV credit: VIN is required")
            if not vehicle.get('purchase_date'):
                warnings.append("EV credit: Purchase date is required")
            if not vehicle.get('price'):
                warnings.append("EV credit: Purchase price is required")

        # Check for foreign income
        if profile.get('foreign', {}).get('foreign_income'):
            if not profile.get('foreign', {}).get('ftb_required'):
                warnings.append("Foreign income detected - may need Form 2555")

        # Check SALT cap
        if profile.get('deductions', {}).get('itemized'):
            salt = profile['deductions']['itemized_breakdown']['taxes']
            total_salt = salt.get('state_income', 0) + salt.get('real_estate', 0) + salt.get('personal_property', 0)
            if total_salt > 10000:
                warnings.append(f"SALT deduction capped at $10,000 (you have ${total_salt:,})")

        # Check for missing W2/1099 docs
        docs = self.indexer.load_index()
        if docs:
            doc_types = docs.get('documents_by_type', {})
            filing_status = profile.get('filing_status', {}).get('status', 'unknown')

            if 'married_joint' in filing_status:
                # Should have at least 2 W2s for married joint
                w2_count = doc_types.get('W2', 0)
                if w2_count < 2:
                    warnings.append(f"Married filing jointly but only {w2_count} W-2 found (expect 2)")

        return {
            "issues": issues,
            "warnings": warnings,
            "valid": len(issues) == 0
        }

    def generate_tax_summary(self) -> dict:
        """Generate a tax summary for the user."""
        profile = self.profile

        # Calculate standard deduction
        filing_status = profile.get('filing_status', {}).get('status', 'single')
        std_deduction = {
            'single': 14600,
            'married_joint': 29200,
            'married_separately': 14600,
            'head_of_household': 21900,
            'qualifying_surviving_spouse': 29200,
        }
        std = std_deduction.get(filing_status, 14600)

        # Collect income
        total_income = 0
        income_sources = []

        docs = self.indexer.load_index()
        if docs:
            for doc in docs.get('documents', []):
                if doc.get('doc_type') == 'W2':
                    wages = doc.get('boxes', {}).get('wages', 0)
                    if wages:
                        total_income += wages
                        income_sources.append(f"W2: ${wages:,.2f}")

        # Calculate estimated tax
        taxable_income = max(0, total_income - std)

        # Rough tax estimate (2025 brackets for married joint)
        estimated_tax = 0
        if taxable_income > 0:
            brackets = [
                (23200, 0.10),
                (89200, 0.12),
                (190100, 0.22),
                (340900, 0.24),
                (431300, 0.32),
                (651100, 0.35),
                (None, 0.37),
            ]
            prev_limit = 0
            for limit, rate in brackets:
                if taxable_income <= prev_limit:
                    break
                taxable_in_bracket = min(taxable_income, limit if limit else float('inf')) - prev_limit
                estimated_tax += taxable_in_bracket * rate
                prev_limit = limit if limit else float('inf')

        return {
            "filing_status": filing_status,
            "standard_deduction": std,
            "total_income": total_income,
            "taxable_income": taxable_income,
            "estimated_tax": estimated_tax,
            "income_sources": income_sources,
            "dependents": len(profile.get('dependents', [])),
        }


def main():
    """CLI entry point."""
    tax_dir = sys.argv[1] if len(sys.argv) > 1 else "/Volumes/volume_1-1/kevin/Taxes"

    if not os.path.exists(tax_dir):
        print(f"Tax folder not found: {tax_dir}")
        sys.exit(1)

    orchestrator = TaxSkillOrchestrator(tax_dir)

    action = sys.argv[2] if len(sys.argv) > 2 else "status"

    if action == "scan":
        orchestrator.scan_documents()

    elif action == "update":
        orchestrator.check_form_updates()
        orchestrator.check_tax_code_changes()

    elif action == "status":
        orchestrator.show_status()

    elif action == "interview":
        orchestrator.interview()

    elif action == "validate":
        docs = orchestrator.scan_documents()
        result = orchestrator.validate_return()
        print("\n🔍 Validation Results:")
        if result['warnings']:
            print("  ⚠️  Warnings:")
            for w in result['warnings']:
                print(f"    - {w}")
        if result['issues']:
            print("  ❌ Issues:")
            for i in result['issues']:
                print(f"    - {i}")
        if not result['issues'] and not result['warnings']:
            print("  ✓ No issues found!")

    elif action == "summary":
        docs = orchestrator.scan_documents()
        summary = orchestrator.generate_tax_summary()
        print("\n📊 Tax Summary:")
        print(f"  Filing Status: {summary['filing_status']}")
        print(f"  Standard Deduction: ${summary['standard_deduction']:,}")
        print(f"  Total Income: ${summary['total_income']:,}")
        print(f"  Taxable Income: ${summary['taxable_income']:,}")
        print(f"  Estimated Tax: ${summary['estimated_tax']:,.2f}")
        if summary['income_sources']:
            print("  Income Sources:")
            for src in summary['income_sources']:
                print(f"    - {src}")

    elif action == "forms":
        required = orchestrator.get_required_forms()
        print("\n📋 Required Forms:")
        for form in required:
            status = "✓" if form.get('filled') else "○"
            print(f"  {status} {form['form']} - {form['name']}")
            print(f"     Reason: {form['reason']}")

    else:
        print("Usage: tax_skill.py [tax_dir] [scan|update|status|interview|validate|summary|forms]")
        sys.exit(1)


if __name__ == "__main__":
    main()
