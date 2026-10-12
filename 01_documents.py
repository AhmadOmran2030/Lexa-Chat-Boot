"""
01_documents.py
Document repository containing corporate policies and dynamic PDF files from ./data/
"""

import os
from pypdf import PdfReader

# 1. Base Corporate Governance & M&A Policies
base_documents = [
    {
        "id": "board_independence_policy",
        "title": "Board Composition and Independence Policy",
        "is_current": True,
        "text": (
            "The board of directors must maintain a majority of independent directors who have no "
            "material relationship with the company. The audit committee must be composed entirely "
            "of independent directors, and at least one member must qualify as a financial expert."
        ),
    },
    {
        "id": "conflict_of_interest_policy",
        "title": "Director Conflict of Interest Policy",
        "is_current": True,
        "text": (
            "Directors must disclose any personal, financial, or business interest in a matter before "
            "the board votes on it. A conflicted director must recuse themselves from discussion and "
            "voting, and the recusal must be recorded in the meeting minutes."
        ),
    },
    {
        "id": "merger_approval_process",
        "title": "Merger Approval Process",
        "is_current": True,
        "text": (
            "A proposed merger requires approval by a majority of the board followed by a supermajority "
            "vote of shareholders holding at least two thirds of outstanding voting shares. Regulatory "
            "filings must be submitted before the transaction can close."
        ),
    },
    {
        "id": "due_diligence_checklist",
        "title": "M&A Due Diligence Checklist",
        "is_current": True,
        "text": (
            "Due diligence for an acquisition must cover financial statements, outstanding litigation, "
            "material contracts, employment agreements, and intellectual property ownership. Findings "
            "are compiled into a due diligence report before the deal is presented to the board."
        ),
    },
    {
        "id": "trademark_registration_policy",
        "title": "Trademark Registration Policy",
        "is_current": True,
        "text": (
            "New product or brand names must be cleared for trademark availability before public launch. "
            "Registration applications are filed in each jurisdiction where the company sells the "
            "product, and renewal deadlines are tracked centrally by the legal team."
        ),
    },
    {
        "id": "patent_filing_guidelines",
        "title": "Patent Filing Guidelines",
        "is_current": True,
        "text": (
            "Inventions developed by employees within the scope of their role belong to the company. "
            "Engineers must submit an invention disclosure form before public disclosure or publication "
            "so the legal team can evaluate patentability and file within statutory deadlines."
        ),
    },
    {
        "id": "old_conflict_of_interest_notice",
        "title": "Archived Conflict of Interest Notice",
        "is_current": False,
        "text": (
            "Archived notice: directors were previously only required to disclose conflicts verbally "
            "during the meeting with no written record. This notice is no longer current."
        ),
    },
]

# 2. Intellectual Property & Real Estate Law Policies
property_and_ip_documents = [
    {
        "id": "trade_secret_protection_policy",
        "title": "Trade Secret Protection Policy",
        "is_current": True,
        "text": (
            "Proprietary source code, algorithms, manufacturing processes, and customer lists "
            "are designated as trade secrets. Access is granted strictly on a need-to-know basis "
            "and protected via Non-Disclosure Agreements (NDAs) and encryption standards."
        ),
    },
    {
        "id": "open_source_compliance_policy",
        "title": "Open Source Software Licensing Policy",
        "is_current": True,
        "text": (
            "Engineering teams using third-party open-source libraries must obtain legal clearance "
            "to avoid restrictive copyleft licenses (e.g., GPL) that could force the disclosure "
            "of commercial proprietary code."
        ),
    },
    {
        "id": "ip_licensing_and_commercialization",
        "title": "Intellectual Property Licensing Framework",
        "is_current": True,
        "text": (
            "In-licensing or out-licensing of intellectual property requires a written license agreement "
            "defining terms, geographical scope, royalty structures, sublicensing rights, and "
            "quality control mechanics enforced by legal counsel."
        ),
    },
    {
        "id": "copyright_and_work_for_hire",
        "title": "Copyright Ownership and Work-For-Hire Standard",
        "is_current": True,
        "text": (
            "All software, marketing materials, technical specifications, and written designs "
            "created by employees or external contractors are work-for-hire, with complete "
            "copyright ownership assigned exclusively to the company."
        ),
    },
    {
        "id": "ip_infringement_and_enforcement",
        "title": "IP Enforcement and Litigation Protocol",
        "is_current": True,
        "text": (
            "Suspected unauthorized third-party use of company patents, trademarks, or copyrights "
            "must be escalated to the legal IP team for initial cease-and-desist notices, "
            "customs enforcement filings, or formal litigation."
        ),
    },
    {
        "id": "domain_name_portfolio_management",
        "title": "Domain Name Management and Brand Protection",
        "is_current": True,
        "text": (
            "Corporate domain registrations, gTLDs, and country-code domains are managed centrally "
            "by the IP department to protect against typosquatting, cybersquatting, and brand erosion."
        ),
    },
    {
        "id": "ip_assignment_onboarding_agreement",
        "title": "Employee IP Assignment Agreement",
        "is_current": True,
        "text": (
            "All new hires and technical independent contractors must execute a Proprietary Information "
            "and Inventions Assignment Agreement (PIIAA) prior to starting work or accessing systems."
        ),
    },
    {
        "id": "joint_dev_ip_ownership_guidelines",
        "title": "Joint Research and Development IP Guidelines",
        "is_current": True,
        "text": (
            "Collaborative R&D efforts with academic or commercial partners must explicitly delineate "
            "Background IP (pre-existing ownership) from Foreground IP (new inventions generated during the project)."
        ),
    },
    {
        "id": "trademark_monitoring_and_opposition",
        "title": "Trademark Registry Monitoring Procedure",
        "is_current": True,
        "text": (
            "The legal team monitors global trademark registries monthly to identify and oppose confusingly "
            "similar mark applications filed by competitors prior to formal registration."
        ),
    },
    {
        "id": "digital_rights_and_media_usage",
        "title": "Digital Assets and Brand Media Usage Policy",
        "is_current": True,
        "text": (
            "Third parties and media outlets utilizing official corporate logos, software screenshots, "
            "or promotional assets must adhere to strict brand guideline licenses without alteration."
        ),
    },
    {
        "id": "moral_rights_waiver_policy",
        "title": "Moral Rights Waiver and Authorship Policy",
        "is_current": True,
        "text": (
            "Where permitted under local copyright laws, internal creators and external consultants "
            "must grant an explicit waiver of moral rights for assets created under contract."
        ),
    },
    {
        "id": "fair_use_and_third_party_content",
        "title": "Third-Party Content Usage and Fair Use Policy",
        "is_current": True,
        "text": (
            "Incorporating third-party images, music, stock content, or publications into commercial products "
            "or promotional materials requires verified license coverage or explicit legal fair use clearance."
        ),
    },
    {
        "id": "archived_patent_incentive_policy_2017",
        "title": "Archived Patent Cash Award Policy (2017)",
        "is_current": False,
        "text": (
            "Archived policy: Inventors were granted cash bonuses solely upon patent grant. "
            "Superseded by the modern dual-stage reward framework (filing and issuance stages)."
        ),
    },
    {
        "id": "cross_licensing_agreement_framework",
        "title": "Cross-Licensing and Patent Pool Framework",
        "is_current": True,
        "text": (
            "Participating in industry patent pools or cross-licensing arrangements requires approval "
            "from the Chief Intellectual Property Counsel and Executive Board to prevent patent exhaustion."
        ),
    },
    {
        "id": "ip_due_diligence_m_and_a",
        "title": "IP Due Diligence Protocol for M&A",
        "is_current": True,
        "text": (
            "Target entity IP due diligence must verify chain of title, patent maintenance fees paid, "
            "absence of litigation encumbrances, and valid assignment deeds from all historical inventors."
        ),
    },
    {
        "id": "commercial_lease_review_policy",
        "title": "Commercial Real Estate Lease Policy",
        "is_current": True,
        "text": (
            "Leasing agreements for office spaces, warehouses, or data centers exceeding 12 months "
            "must be reviewed by legal for rent escalation, maintenance obligations, subleasing rights, "
            "and restoration covenants upon expiration."
        ),
    },
    {
        "id": "property_acquisition_due_diligence",
        "title": "Real Property Acquisition Due Diligence",
        "is_current": True,
        "text": (
            "Before acquiring real property, the company must execute title searches, environmental "
            "site assessments (Phase I ESA), land survey verification, and local zoning compliance checks."
        ),
    },
    {
        "id": "subleasing_and_assignment_policy",
        "title": "Subleasing and Space Assignment Protocol",
        "is_current": True,
        "text": (
            "Unused leased real estate may only be subleased or assigned to vetted third parties "
            "if permitted under the primary lease agreement and approved in writing by the landlord."
        ),
    },
    {
        "id": "environmental_compliance_real_estate",
        "title": "Environmental Compliance for Facilities",
        "is_current": True,
        "text": (
            "Corporate facilities must comply with federal and local environmental protection laws, "
            "including hazardous waste disposal, air quality compliance, and energy usage disclosures."
        ),
    },
    {
        "id": "tenant_improvement_and_alterations",
        "title": "Tenant Improvement and Structural Alteration Guidelines",
        "is_current": True,
        "text": (
            "Structural modifications to leased properties require prior landlord consent, compliance "
            "with building codes, mechanics' lien waivers from contractors, and proper insurance coverage."
        ),
    },
    {
        "id": "property_insurance_and_risk",
        "title": "Real Property Insurance and Risk Coverage Policy",
        "is_current": True,
        "text": (
            "All owned and leased real property assets must maintain commercial property insurance, "
            "business interruption coverage, and liability coverage against casualty or force majeure loss."
        ),
    },
    {
        "id": "zoning_and_land_use_compliance",
        "title": "Zoning Laws and Land Use Permits Policy",
        "is_current": True,
        "text": (
            "Operational expansion, facility construction, or change of commercial land use "
            "must secure proper municipal zoning variances and occupancy permits prior to operation."
        ),
    },
    {
        "id": "easement_and_right_of_way_policy",
        "title": "Easement and Property Right-of-Way Policy",
        "is_current": True,
        "text": (
            "Granting or acquiring property easements (e.g., utility access, road access) requires "
            "formal title registration and board approval to ensure no impairment to core property usage."
        ),
    },
    {
        "id": "facilities_disaster_recovery_plan",
        "title": "Facility Emergency and Physical Asset Protection Policy",
        "is_current": True,
        "text": (
            "Real estate facilities maintain physical access security, fire suppression compliance, "
            "and business continuity protocols to safeguard staff, infrastructure, and machinery."
        ),
    },
    {
        "id": "archived_commercial_lease_thresholds_2016",
        "title": "Archived Commercial Lease Approval Policy (2016)",
        "is_current": False,
        "text": (
            "Archived policy: Regional managers had authority to execute office leases up to $100K annually "
            "without central legal review. Superseded by the centralized Real Estate Governance Committee."
        ),
    },
    {
        "id": "sale_leaseback_transaction_policy",
        "title": "Sale and Leaseback Structuring Policy",
        "is_current": True,
        "text": (
            "Sale-and-leaseback arrangements for corporate real estate assets require Board Finance "
            "Committee sign-off, tax structure analysis, and long-term operating risk evaluation."
        ),
    },
    {
        "id": "mechanics_lien_prevention_protocol",
        "title": "Mechanics' Lien Indemnification Protocol",
        "is_current": True,
        "text": (
            "When undertaking facility construction, contractors must provide progress payment lien waivers "
            "to prevent statutory mechanics' liens from encumbering corporate property title."
        ),
    },
    {
        "id": "expropriation_and_eminent_domain",
        "title": "Eminent Domain and Compulsory Purchase Policy",
        "is_current": True,
        "text": (
            "If corporate land or buildings are targeted for public infrastructure acquisition, "
            "the legal team must engage valuation experts to secure full market compensation."
        ),
    },
    {
        "id": "equipment_and_chattel_leasing_policy",
        "title": "Personal Property and Equipment Leasing Guidelines",
        "is_current": True,
        "text": (
            "Leasing heavy machinery, hardware, or vehicles (personal property/chattels) requires "
            "UCC filing verification and security interest disclosures to prevent double-pledging assets."
        ),
    },
    {
        "id": "workplace_accessibility_compliance",
        "title": "Property Accessibility and Disability Accommodation Policy",
        "is_current": True,
        "text": (
            "All physical corporate premises open to employees or the public must comply with statutory "
            "building accessibility standards, barrier-free access rules, and reasonable accommodations."
        ),
    },
]


# 3. Dynamic PDF File Ingestion
def load_pdf_documents(folder_path: str = "./data") -> list:
    """Scans the ./data directory for PDF files and converts them to document dictionaries."""
    pdf_docs = []

    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        return pdf_docs

    for file_name in os.listdir(folder_path):
        if file_name.lower().endswith(".pdf"):
            file_path = os.path.join(folder_path, file_name)
            try:
                reader = PdfReader(file_path)
                full_text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        full_text += extracted + "\n"

                if full_text.strip():
                    clean_name = os.path.splitext(file_name)[0]
                    doc_id = f"pdf_{clean_name.lower().replace(' ', '_')}"
                    doc_title = clean_name.replace("_", " ").title()

                    pdf_docs.append({
                        "id": doc_id,
                        "title": doc_title,
                        "is_current": True,
                        "text": full_text.strip(),
                    })
            except Exception as e:
                print(f"Error reading PDF '{file_name}': {e}")

    return pdf_docs


def get_documents(data_folder: str = "./data") -> list:
    """Main accessor function: Combines built-in policy lists with dynamic PDFs."""
    all_docs = []
    all_docs.extend(base_documents)
    all_docs.extend(property_and_ip_documents)
    all_docs.extend(load_pdf_documents(folder_path=data_folder))
    return all_docs


# Expose top-level documents variable for direct imports (e.g. 03_chunking.py)
documents = get_documents()
