# Tax Skill - Project Board (Kanban)

> AI-powered tax preparation skill that interviews you, fills forms, monitors tax code changes, and ensures you have the latest IRS forms.

---

## 🟢 Phase 1: Foundation (In Progress)

### Core Infrastructure
- [ ] **Repo Setup** — Initialize repo with skill structure
- [ ] **PDF Form Parser** — Build tool to extract form metadata from IRS PDFs
- [ ] **Tax Document Indexer** — Scan user's tax folder for available documents (W2, 1099, etc.)
- [ ] **Form-to-Field Mapping** — Map each IRS form to its required input fields

### Data Collection
- [ ] **W2 Parser** — Extract wages, withholding, state info from W2 PDFs
- [ ] **1099 Parser** — Extract income data from 1099 variants (INT, DIV, NEC, R, SA, Q)
- [ ] **Schedule C Auto-Detection** — Detect if user has self-employment income (currently shows in PDFs — confirm status)
- [ ] **Vehicle Information Collector** — Collect EV/PHEV details for credit eligibility

### IRS Form Management
- [ ] **IRS Form Updater** — Periodic check of irs.gov for form updates/changes
- [ ] **Local Form Cache** — Download and cache latest forms locally
- [ ] **Form Version Diffing** — Alert when form fields change between tax years

---

## 🔵 Phase 2: Interview Engine (To Do)

### Interview Flow
- [ ] **Interview State Machine** — Track which forms are complete vs. pending
- [ ] **Context-Aware Questioning** — Ask questions based on previously collected data
- [ ] **Missing Data Detection** — Identify gaps and prompt user
- [ ] **Form Preview** — Show user how their data maps to each form before filing

### Education Mode
- [ ] **Form Explainer** — Explain what each form is for and why it's needed
- [ ] **Line-by-Line Guide** — Walk through each line of complex forms
- [ ] **Eligibility Checker** — Determine if user qualifies for credits/deductions (EV credit, EITC, etc.)

### EV Credit Investigation
- [ ] **2021 Ford F150 Lightning EV Credit** — Research eligibility for 2025 tax year (IRC 30D, IRC 30D)
  - [ ] Check if F150 Lightning qualifies for $7,500 federal credit
  - [ ] Check if used in qualifying location (assembly in U.S.)
  - [ ] Check income limits and MSRP caps
  - [ ] Check if it's new or used vehicle credit (IRC 25E)
  - [ ] Determine which form to use (8936 for new, 8910 for commercial clean)

---

## 🟡 Phase 3: Tax Code Monitoring (To Do)

### Code Change Detection
- [ ] **Tax Code Change Scanner** — Monitor IRS announcements and legislative changes
- [ ] **Personalized Impact Analysis** — Flag changes that affect Kevin's specific situation:
  - [ ] Family filing status (married, dependents?)
  - [ ] EV credit changes
  - [ ] SALT deduction limits
  - [ ] Standard deduction changes
  - [ ] Retirement contribution limits
  - [ ] HSA contribution limits
- [ ] **State Tax Monitor** — Track NC tax code changes

### Alerts
- [ ] **Pre-Filing Alert System** — Notify user of changes before filing deadline
- [ ] **Mid-Year Impact Alerts** — Notify of changes affecting estimated payments

---

## 🟠 Phase 4: State Filing (To Do)

### North Carolina
- [ ] **NC D-400 Auto-Fill** — Populate NC state return from federal data
- [ ] **NC Tax Calculator** — Calculate NC state tax liability
- [ ] **NC Deduction/Credit Mapper** — Identify NC-specific deductions and credits

### Multi-State Support
- [ ] **State Form Discovery** — Auto-detect which states need filing based on residency/work
- [ ] **Reciprocity Checker** — Check for tax reciprocity agreements

---

## 🔴 Phase 5: Validation & Filing (To Do)

### Validation
- [ ] **Cross-Form Consistency Check** — Verify data flows correctly between forms
  - [ ] W2 wages → 1040 income lines
  - [ ] Schedule C net profit → Schedule 1 → 1040
  - [ ] Itemized deductions → 1040 line 12
  - [ ] Credits → 1040 credit lines
- [ ] **Math Verification** — Verify all calculations are correct
- [ ] **Common Error Detection** — Flag frequent mistakes (e.g., missed credits, wrong filing status)
- [ ] **Audit Risk Scoring** — Identify items that may trigger IRS scrutiny

### Filing
- [ ] **PDF Form Generator** — Generate filled PDF forms ready for e-file
- [ ] **e-File Export** — Export to tax software format (TurboTax, TaxAct, etc.)
- [ ] **Final Review Checklist** — Pre-submission checklist for user

---

## 🟣 Phase 6: User Experience (To Do)

### Interface
- [ ] **Chat-Based Interview** — Natural language conversation flow
- [ ] **Progress Dashboard** — Show which forms are complete, pending, and estimated savings
- [ ] **Document Drop Zone** — Auto-detect when user drops tax documents into folder
- [ ] **Tax Summary Report** — Generate one-page summary of tax situation

### Personalization
- [ ] **Tax Profile Builder** — Learn user's recurring situations year over year
- [ ] **Historical Comparison** — Compare current year to prior years
- [ ] **Estimated Tax Calculator** — Help with quarterly estimated payments

---

## 📋 Known Tax Situations (from 2025 PDF analysis)

| Form | Status | Notes |
|------|--------|-------|
| 1040 U.S. Individual Income Tax Return | Primary return | |
| Schedule 1 (Form 1040) | Additional income/adjustments | |
| Schedule 2 (Form 1040) | Additional taxes | |
| Schedule 3 (Form 1040) | Credits | |
| Schedule A (Form 1040) | Itemized deductions | |
| Schedule B (Form 1040) | Interest/Dividends | |
| Schedule C (Form 1040) | Business income | ⚠️ User says no self-employment — confirm |
| Schedule D (Form 1040) | Capital gains | |
| Schedule SE (Form 1040) | Self-employment tax | |
| Form 4562 (2025) | Depreciation | |
| Form 8812 (2025) | Child Tax Credit | |
| Form 8867 (Rev 11-2024) | Paid Preparer | |
| Form 8879 (Rev 01-2021) | e-file Signature | |
| Form 8936 (2025) | Clean Vehicle Credit | ⚠️ Investigate F150 Lightning eligibility |
| Form 9325 (Rev 1-2017) | Adoption Information | |

---

## 📁 File Structure (Planned)

```
/Volumes/volume_1-1/kevin/Taxes/
├── .taxskill/
│   ├── profile.json          # User's tax profile
│   ├── forms_cache/          # Latest IRS forms
│   ├── state_cache/          # Latest state forms
│   └── code_changes/         # Tax code change log
├── 2025 Tax Information/
│   ├── dropped/              # Auto-detected documents
│   ├── tax_return/           # Final return PDFs
│   ├── prelim/               # Preliminary work
│   └── financial/            # Financial documents
├── 2024 Tax Information/
├── tax_forms_2022-2025.txt   # Form inventory
└── README.md                 # This file
```

---

## 🔑 Key Questions for User

1. **Filing Status?** Married filing jointly? (Saw "KEVIN M & JOSEPHINE MOKER" in PDFs)
2. **Dependents?** How many and ages? (Saw Schedule 8812 — Child Tax Credit)
3. **Schedule C?** Shows consulting income in PDFs — is this still active or was it closed?
4. **State of Residency?** North Carolina (saw NC forms in folder)
5. **EV Purchase Date?** When was the Ford F150 Lightning purchased? (new vs used matters for credits)
6. **Adoption?** Form 9325 suggests adoption expenses — any ongoing adoption credit?
7. **Foreign Assets?** Form 8938 and Form 3520 suggest foreign financial interests
8. **Filing Preference?** E-file vs mail? Which tax software?
