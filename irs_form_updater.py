#!/usr/bin/env python3
"""
Tax Skill - IRS Form Updater
Periodically checks irs.gov for form updates and downloads new versions.
"""

import os
import sys
import json
import re
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path


class IRSFormUpdater:
    """Monitors IRS.gov for form updates and downloads new versions."""

    # Base URLs for IRS forms
    IRS_FORM_URL = "https://www.irs.gov/pub/irs-pdf/{}"
    IRS_FORMS_LIST_URL = "https://www.irs.gov/forms-pubs/about/form-{}"

    # Known form numbers that need monitoring
    MONITORED_FORMS = {
        "1040": {"name": "U.S. Individual Income Tax Return", "check_revisions": True},
        "1040s1": {"name": "Schedule 1", "check_revisions": True},
        "1040s2": {"name": "Schedule 2", "check_revisions": True},
        "1040s3": {"name": "Schedule 3", "check_revisions": True},
        "1040sa": {"name": "Schedule A", "check_revisions": True},
        "1040sb": {"name": "Schedule B", "check_revisions": True},
        "1040sc": {"name": "Schedule C", "check_revisions": True},
        "1040sd": {"name": "Schedule D", "check_revisions": True},
        "1040se": {"name": "Schedule SE", "check_revisions": True},
        "4562": {"name": "Form 4562 - Depreciation", "check_revisions": True},
        "5329": {"name": "Form 5329 - Additional Taxes", "check_revisions": True},
        "8606": {"name": "Form 8606 - Nondeductible IRAs", "check_revisions": True},
        "8812": {"name": "Schedule 8812 - Child Credits", "check_revisions": True},
        "8867": {"name": "Form 8867 - Paid Preparer", "check_revisions": True},
        "8879": {"name": "Form 8879 - e-file Signature", "check_revisions": True},
        "8889": {"name": "Form 8889 - HSA", "check_revisions": True},
        "8936": {"name": "Form 8936 - Clean Vehicle Credit", "check_revisions": True},
        "9325": {"name": "Form 9325 - Adoption", "check_revisions": True},
    }

    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.expanduser("~/Downloads/2025_IRS_Forms")
        self.check_log_file = os.path.join(os.path.expanduser("~"), "Taxes", ".taxskill", "code_changes", "irs_check_log.json")
        os.makedirs(os.path.dirname(self.check_log_file), exist_ok=True)

    def get_check_log(self) -> dict:
        """Load the IRS check log."""
        if os.path.exists(self.check_log_file):
            with open(self.check_log_file, 'r') as f:
                return json.load(f)
        return {"last_check": None, "forms": {}}

    def save_check_log(self, log: dict):
        """Save the IRS check log."""
        with open(self.check_log_file, 'w') as f:
            json.dump(log, f, indent=2)

    def needs_check(self, form_number: str, max_age_days: int = 30) -> bool:
        """Check if a form needs to be re-downloaded based on last check age."""
        log = self.get_check_log()
        last_check = log.get("forms", {}).get(form_number, {}).get("last_check")
        if not last_check:
            return True

        last_date = datetime.fromisoformat(last_check)
        return (datetime.now() - last_date) > timedelta(days=max_age_days)

    def download_form(self, form_number: str) -> tuple:
        """Download a form from IRS.gov. Returns (success, filepath, error)."""
        url = self.IRS_FORM_URL.format(form_number)
        filename = f"f{form_number}.pdf"
        filepath = os.path.join(self.cache_dir, filename)

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
                file_size = len(data)

                # Check if file actually changed (compare hash)
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        existing_hash = hashlib.md5(f.read()).hexdigest()
                    new_hash = hashlib.md5(data).hexdigest()
                    changed = (existing_hash != new_hash)
                else:
                    changed = True

                # Save file
                with open(filepath, 'wb') as f:
                    f.write(data)

                # Update check log
                log = self.get_check_log()
                log["forms"][form_number] = {
                    "last_check": datetime.now().isoformat(),
                    "file_size": file_size,
                    "hash": hashlib.md5(data).hexdigest(),
                    "changed": changed,
                    "url": url,
                }
                log["last_check"] = datetime.now().isoformat()
                self.save_check_log(log)

                return (True, filepath, changed)

        except urllib.error.HTTPError as e:
            return (False, None, f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            return (False, None, f"Network error: {e.reason}")
        except Exception as e:
            return (False, None, f"Error: {str(e)}")

    def check_all_forms(self) -> dict:
        """Check all monitored forms for updates."""
        results = {}

        for form_num, info in self.MONITORED_FORMS.items():
            if self.needs_check(form_num):
                print(f"  Checking {info['name']} (f{form_num})...")
                success, filepath, changed = self.download_form(form_num)

                if success:
                    if changed:
                        results[form_num] = {"status": "updated", "filepath": filepath}
                        print(f"    ✅ Updated: {filepath}")
                    else:
                        results[form_num] = {"status": "no_change", "filepath": filepath}
                        print(f"    ✓ No change")
                else:
                    results[form_num] = {"status": "error", "error": changed}
                    print(f"    ❌ Error: {changed}")
            else:
                results[form_num] = {"status": "skipped", "reason": "checked_recently"}
                print(f"  Skipped {info['name']} (checked recently)")

        return results

    def check_tax_code_changes(self) -> list:
        """Check for tax code changes that may affect the user."""
        changes = []

        # Known 2025 tax year changes to track
        tax_changes = {
            "2025": [
                {
                    "type": "standard_deduction",
                    "description": "Standard deduction increased",
                    "amounts": {
                        "single": 14600,
                        "married_joint": 29200,
                        "head_household": 21900,
                    },
                    "form_impact": "1040",
                },
                {
                    "type": "income_threshold",
                    "description": "Tax bracket thresholds increased",
                    "form_impact": "1040",
                },
                {
                    "type": "hra",
                    "description": "IRA contribution limit",
                    "amounts": {
                        "under_50": 7000,
                        "50_and_over": 8000,
                    },
                    "form_impact": "8606",
                },
                {
                    "type": "hsa_limit",
                    "description": "HSA contribution limit",
                    "amounts": {
                        "self_only": 4300,
                        "family": 8550,
                        "50_and_over": 1000,
                    },
                    "form_impact": "8889",
                },
                {
                    "type": "eic_limit",
                    "description": "Earned Income Credit income limits",
                    "form_impact": "1040",
                },
                {
                    "type": "salt_cap",
                    "description": "SALT deduction cap remains at $10,000",
                    "form_impact": "schedule_a",
                },
            ]
        }

        # Check if we have changes for the current tax year
        current_year = datetime.now().year
        if str(current_year) in tax_changes:
            changes = tax_changes[str(current_year)]

        return changes

    def get_personalized_impact(self, user_profile: dict) -> list:
        """Get tax code changes that specifically affect this user."""
        changes = self.check_tax_code_changes()

        # Filter based on user's situation
        filtered = []
        for change in changes:
            # EV credit changes
            if 'ev' in str(change).lower() or 'vehicle' in str(change).lower():
                if user_profile.get('has_ev'):
                    filtered.append(change)

            # Family-related changes
            if user_profile.get('filing_status') == 'married_joint':
                if 'married' in change.get('description', '').lower() or 'joint' in change.get('description', '').lower():
                    filtered.append(change)

            if user_profile.get('has_dependents', False):
                if 'child' in change.get('description', '').lower() or 'dependent' in change.get('description', '').lower():
                    filtered.append(change)

            # HSA-related
            if user_profile.get('has_hsa'):
                if 'hsa' in change.get('type', '').lower():
                    filtered.append(change)

            # IRA-related
            if user_profile.get('has_ira'):
                if 'ira' in change.get('type', '').lower() or 'hra' in change.get('type', '').lower():
                    filtered.append(change)

            # SALT-related
            if user_profile.get('state') == 'NC':
                if 'salt' in change.get('type', '').lower():
                    filtered.append(change)

            # Include all if no specific filters match
            if not filtered:
                filtered.append(change)

        return filtered


def main():
    """CLI entry point."""
    updater = IRSFormUpdater()

    action = sys.argv[1] if len(sys.argv) > 1 else "check"

    if action == "check":
        print("Checking IRS forms for updates...")
        results = updater.check_all_forms()
        updated = [k for k, v in results.items() if v.get('status') == 'updated']
        print(f"\nUpdated: {len(updated)} forms")

    elif action == "changes":
        print("Checking for tax code changes...")
        changes = updater.check_tax_code_changes()
        for change in changes:
            print(f"\n  [{change.get('type', 'unknown').upper()}]")
            print(f"  {change.get('description', 'No description')}")
            if 'amounts' in change:
                for k, v in change['amounts'].items():
                    print(f"    {k}: ${v:,}")

    elif action == "profile":
        print("Checking personalized impact...")
        profile = {
            "has_ev": True,
            "filing_status": "married_joint",
            "has_dependents": True,
            "has_hsa": True,
            "has_ira": True,
            "state": "NC",
        }
        impact = updater.get_personalized_impact(profile)
        for change in impact:
            print(f"  [{change.get('type', 'unknown').upper()}] {change.get('description', '')}")

    else:
        print("Usage: irs_updater.py [check|changes|profile]")
        sys.exit(1)


if __name__ == "__main__":
    main()
