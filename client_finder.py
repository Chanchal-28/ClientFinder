
import csv
import os
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TAVILY_API_KEY")
SEARCH_URL = "https://api.tavily.com/search"

COUNTRIES = [
    "United States",
    "United Kingdom",
    "Canada",
    "Australia",
]

# Use "all" at the prompt to search several industries, or enter one industry.
# These are broad categories so ClientFinder is not restricted to one niche.
INDUSTRIES = [
    "plumbers electricians HVAC and home service contractors",
    "landscaping and construction companies",
    "accounting consulting and recruitment firms",
    "salons fitness studios and appointment-based service businesses",
    "wholesalers distributors and manufacturers",
    "logistics and small B2B service companies",
]

# These are commonly non-prospect pages, not proof that a domain is bad.
EXCLUDED_URL_PARTS = (
    "/blog/", "/blogs/", "/news/", "/article/", "/articles/",
    "/resources/", "/guides/", "/directory/", "/directories/",
    "/software/", "/reviews/", "/best-", "/top-",
)
EXCLUDED_TITLE_PHRASES = (
    "best software", "top software", "software comparison",
    "alternatives to", "best tools", "top 10", "top  five",
    "directory of", "business directory", "industry report",
    "how to", "ultimate guide", "case study", "press release",
)

HEADERS = {
    "User-Agent": "ClientFinderResearch/1.0 (polite public business research)"
}

OPPORTUNITIES = {
    "website": {
        "search": [
            "business website redesign online presence small business",
            "small business website services online enquiry contact form",
        ],
        "signals": [
            "no website", "facebook page", "instagram page",
            "contact us for more information", "call us for information",
            "email us for more information",
        ],
        "features": [
            "contact form", "online enquiry", "request a quote",
            "responsive design", "online booking", "service catalogue",
        ],
        "solution": (
            "Review the business's online presence and consider a "
            "modern website with service pages, enquiry forms and "
            "clear calls to action."
        ),
    },
    "dashboard": {
        "search": [
            "business manual reporting spreadsheets excel operations",
            "business managing orders bookings inventory manually",
        ],
        "signals": [
            "spreadsheet", "excel", "manual process", "manually",
            "email us", "call us to book", "call for availability",
            "download the form", "print and complete",
            "request by email", "fax",
        ],
        "features": [
            "dashboard", "analytics", "reporting portal",
            "client portal", "customer portal", "inventory management",
            "booking system", "order tracking",
        ],
        "solution": (
            "Investigate whether a custom dashboard could simplify "
            "booking, lead tracking, inventory, order management "
            "or business reporting."
        ),
    },
    "both": {
        "search": [
            "small business outdated website manual enquiries operations",
            "business website contact email booking orders management",
        ],
        "signals": [
            "spreadsheet", "excel", "manual process", "manually",
            "email us", "call us to book", "call for availability",
            "download the form", "print and complete",
            "request by email", "fax",
        ],
        "features": [
            "contact form", "online booking", "dashboard",
            "client portal", "customer portal", "order tracking",
            "analytics", "inventory management",
        ],
        "solution": (
            "Assess a combined website and web application: a public "
            "website for customer enquiries plus an internal dashboard "
            "for managing leads, bookings or operations."
        ),
    },
    "booking": {
        "search": [
            "business appointments book by phone email manual booking",
            "service business booking availability contact to schedule",
        ],
        "signals": [
            "call to book", "call us to book", "email to book",
            "email us to book", "call for availability",
            "contact us to schedule", "phone to book",
        ],
        "features": [
            "online booking", "book now", "appointment scheduler",
            "availability calendar",
        ],
        "solution": (
            "Consider an online booking system with an availability "
            "calendar and an appointment-management dashboard."
        ),
    },
    "quotes": {
        "search": [
            "contractor business request quote by phone email",
            "service company estimate enquiries contact form",
        ],
        "signals": [
            "request by email", "email us for a quote",
            "call for a quote", "call us for an estimate",
            "contact us for pricing", "download the form",
        ],
        "features": [
            "request a quote", "get a quote", "quote form",
            "instant quote", "estimate calculator",
        ],
        "solution": (
            "Consider a quote-request form, estimate calculator, "
            "and dashboard to track leads and follow-ups."
        ),
    },
    "portal": {
        "search": [
            "business customers track orders requests email phone",
            "service company customer project updates manually",
        ],
        "signals": [
            "email us for updates", "call for updates",
            "request by email", "contact us for status",
            "download the form",
        ],
        "features": [
            "client portal", "customer portal", "order tracking",
            "project tracking", "client login",
        ],
        "solution": (
            "Investigate a secure customer portal for order status, "
            "project updates, documents or service requests."
        ),
    },
    "automation": {
        "search": [
            "small business repetitive admin tasks manual processes",
            "business managing customer requests by email spreadsheet",
        ],
        "signals": [
            "spreadsheet", "excel", "manual process", "manually",
            "email us", "download the form", "print and complete",
        ],
        "features": [
            "automated reporting", "workflow automation",
            "customer management", "dashboard", "CRM",
        ],
        "solution": (
            "Identify a repetitive workflow that could be simplified "
            "with a small web app, form, CRM or reporting dashboard."
        ),
    },
}


def search_web(query, max_results=5):
    """Search public web results using Tavily."""
    response = requests.post(
        SEARCH_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def fetch_page(url):
    """Read a publicly accessible HTML page."""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=12,
            allow_redirects=True,
        )
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            return None, ""

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(
            ["script", "style", "noscript", "svg", "iframe"]
        ):
            tag.decompose()

        text = " ".join(soup.stripped_strings)
        return soup, text[:50000]

    except requests.RequestException:
        return None, ""


def get_domain(url):
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def is_valid_web_url(url):
    if not url.startswith(("https://", "http://")) or not get_domain(url):
        return False

    parsed = urlparse(url)
    # Ignore search/social platforms and known directory/marketplace domains.
    host = parsed.netloc.lower().removeprefix("www.")
    excluded_hosts = (
        "facebook.com", "instagram.com", "linkedin.com", "youtube.com",
        "yelp.com", "yellowpages.com", "mapquest.com", "trustpilot.com",
        "crunchbase.com", "wikipedia.org", "reddit.com", "clutch.co",
        "g2.com", "capterra.com", "getapp.com",
    )
    if any(host == item or host.endswith("." + item) for item in excluded_hosts):
        return False

    path = parsed.path.lower()
    if any(part in path for part in EXCLUDED_URL_PARTS):
        return False

    return True


def looks_like_article_or_directory(title, url, snippet=""):
    """Reject obvious articles, software roundups and directory pages."""
    combined = f"{title} {url} {snippet}".lower()
    if any(phrase in combined for phrase in EXCLUDED_TITLE_PHRASES):
        return True

    path = urlparse(url).path.lower()
    if any(part in path for part in EXCLUDED_URL_PARTS):
        return True

    return False


def find_evidence(text, terms):
    """Return actual text surrounding any matching signal."""
    lower_text = text.lower()
    evidence = []

    for term in terms:
        position = lower_text.find(term.lower())

        if position >= 0:
            start = max(0, position - 100)
            end = min(len(text), position + len(term) + 140)
            quote = re.sub(r"\s+", " ", text[start:end]).strip()

            evidence.append(f"[{term}] {quote}")

    return evidence[:8]


def inspect_business(url, opportunity):
    """Inspect a homepage and one contact/about page."""
    soup, homepage_text = fetch_page(url)

    if not soup:
        return {
            "email": "",
            "contact_page": "",
            "pages_checked": 0,
            "website_accessible": "No",
            "signals_found": "",
            "feature_evidence": "Could not inspect the website.",
            "evidence_quote": "",
            "lead_score": 0,
            "priority": "Unverified",
            "confidence": "Low",
        }

    checked_text = homepage_text
    pages_checked = 1
    contact_url = ""

    emails = set(
        re.findall(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            checked_text,
            re.IGNORECASE,
        )
    )

    # Find one internal contact/about page.
    for link in soup.find_all("a", href=True):
        label = (
            link.get_text(" ", strip=True) + " " + link["href"]
        ).lower()

        if any(
            word in label
            for word in ["contact", "about", "support"]
        ):
            candidate = urljoin(url, link["href"])

            if (
                urlparse(candidate).netloc.lower()
                == urlparse(url).netloc.lower()
            ):
                contact_url = candidate
                break

    if contact_url and contact_url.rstrip("/") != url.rstrip("/"):
        time.sleep(0.4)
        contact_soup, contact_text = fetch_page(contact_url)

        if contact_soup and contact_text:
            pages_checked += 1
            checked_text += " " + contact_text

            emails.update(
                re.findall(
                    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
                    contact_text,
                    re.IGNORECASE,
                )
            )

    emails = {
        email for email in emails
        if not email.lower().endswith(
            ("@example.com", "@domain.com", "@email.com")
        )
    }

    config = OPPORTUNITIES[opportunity]

    signals = find_evidence(checked_text, config["signals"])
    feature_matches = [
        term for term in config["features"]
        if term in checked_text.lower()
    ]

    # Score only observable indicators.
    # Absence of a feature is weak evidence, not proof of a need.
    score = 20  # A candidate website was found.
    score += min(len(signals) * 12, 36)

    if contact_url:
        score += 5

    if emails:
        score += 5

    if feature_matches:
        score -= 5  # The requested feature may already exist.

    score = max(0, min(score, 100))

    if score >= 55 and signals:
        priority = "High review priority"
    elif score >= 35 and signals:
        priority = "Medium review priority"
    else:
        priority = "Needs more research"

    if len(signals) >= 2:
        confidence = "Medium"
    elif len(signals) == 1:
        confidence = "Low"
    else:
        confidence = "Very low"

    if signals:
        evidence_summary = " | ".join(signals)
    else:
        evidence_summary = (
            "No matching manual-workflow signals found. "
            "Do not assume the business needs this solution."
        )

    feature_summary = (
        ", ".join(feature_matches)
        if feature_matches
        else "Requested feature not detected on checked pages; "
             "absence is not proof that it is missing."
    )

    return {
        "email": "; ".join(sorted(emails)),
        "contact_page": contact_url,
        "pages_checked": pages_checked,
        "website_accessible": "Yes",
        "signals_found": ", ".join(
            re.findall(r"\[([^\]]+)\]", " ".join(signals))
        ),
        "feature_evidence": feature_summary,
        "evidence_quote": evidence_summary,
        "lead_score": score,
        "priority": priority,
        "confidence": confidence,
    }


def main():
    if not API_KEY:
        print("\nMissing TAVILY_API_KEY. Check your .env file.")
        return

    print("\n=== CLIENTFINDER: BUSINESS OPPORTUNITY RESEARCH ===")
    print("Searches actual business prospects across multiple industries.")
    print("Tip: enter 'all' to search all suggested industry groups.")

    industry_input = input(
        "Industry (all / or a specific type, e.g. accountants): "
    ).strip() or "all"

    selected_industries = INDUSTRIES if industry_input.lower() == "all" else [industry_input]

    print("\nChoose an opportunity:")
    for name in OPPORTUNITIES:
        print(f" - {name}")

    opportunity = input("Opportunity: ").strip().lower()
    if opportunity not in OPPORTUNITIES:
        print("Unknown choice. Using both.")
        opportunity = "both"

    try:
        limit = int(input("Results per search (1-10, default 5): ").strip() or "5")
        limit = max(1, min(limit, 10))
    except ValueError:
        limit = 5

    prospects = {}
    search_templates = OPPORTUNITIES[opportunity]["search"]
    total_searches = len(COUNTRIES) * len(selected_industries)
    search_number = 0
    # Combine the selected opportunity's search ideas into one query to keep
    # the number of API calls manageable.
    opportunity_terms = " OR ".join(search_templates)

    for country in COUNTRIES:
        for industry in selected_industries:
            search_number += 1
            query = (
                f"{industry} businesses in {country} official company website "
                f"services contact ({opportunity_terms})"
            )
            print(f"\n[{search_number}/{total_searches}] Searching: {query}")

            try:
                results = search_web(query, limit)
            except requests.RequestException as error:
                print(f"Search failed: {error}")
                continue

            for result in results:
                url = result.get("url", "").strip()
                title = re.sub(r"\s+", " ", result.get("title", "")).strip()
                snippet = result.get("content", "")

                if not is_valid_web_url(url):
                    continue
                if looks_like_article_or_directory(title, url, snippet):
                    continue

                domain = get_domain(url)
                if not domain:
                    continue

                if domain not in prospects:
                    prospects[domain] = {
                        "business": title or domain,
                        "domain": domain,
                        "website": url,
                        "search_snippet": snippet,
                        "search_source": url,
                        "search_query": query,
                    }
                else:
                    old = prospects[domain]["search_snippet"]
                    if snippet and snippet not in old:
                        prospects[domain]["search_snippet"] = (
                            (old + " | " + snippet).strip(" |")
                        )[:3000]

            time.sleep(0.35)

    if not prospects:
        print("\nNo candidate websites survived the initial filters.")
        print("Try a specific industry or a different opportunity.")
        return

    print(f"\nFound {len(prospects)} candidate domains after initial filtering.")
    print("Inspecting their public pages and collecting evidence...")

    rows = []
    for index, prospect in enumerate(prospects.values(), start=1):
        print(f"[{index}/{len(prospects)}] {prospect['business']}")
        details = inspect_business(prospect["website"], opportunity)

        # Search-result clues are labelled separately from inspected-page evidence.
        snippet_signals = find_evidence(
            prospect["search_snippet"],
            OPPORTUNITIES[opportunity]["signals"],
        )
        if snippet_signals:
            snippet_note = "Search result only (verify on site): " + " | ".join(snippet_signals)
            existing = details["evidence_quote"]
            details["evidence_quote"] = ((existing + " | " + snippet_note).strip(" |"))[:2500]
            if details["confidence"] == "Very low":
                details["confidence"] = "Low"

        rows.append({
            **prospect,
            "opportunity_type": opportunity,
            "suggested_solution": OPPORTUNITIES[opportunity]["solution"],
            **details,
        })
        time.sleep(0.35)

    rows.sort(
        key=lambda row: (
            row["website_accessible"] == "Yes",
            bool(row["signals_found"]),
            row["lead_score"],
        ),
        reverse=True,
    )

    output_file = "client_prospects.csv"
    fieldnames = [
        "business", "domain", "website", "opportunity_type", "lead_score",
        "priority", "confidence", "signals_found", "evidence_quote",
        "feature_evidence", "suggested_solution", "search_snippet",
        "search_source", "search_query", "email", "contact_page",
        "website_accessible", "pages_checked",
    ]

    with open(output_file, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    accessible = sum(row["website_accessible"] == "Yes" for row in rows)
    with_signals = sum(bool(row["signals_found"]) for row in rows)

    print(f"\nSaved {len(rows)} candidates to {output_file}")
    print(f"Website pages accessible: {accessible}/{len(rows)}")
    print(f"Candidates with matching signals on inspected pages: {with_signals}")
    print("\nTop candidates to review:")
    for row in rows[:10]:
        print(
            f"- {row['business']} | Evidence signals: "
            f"{row['signals_found'] or 'none found'} | {row['website']}"
        )

    print(
        "\nImportant: filters reduce obvious articles/directories but cannot "
        "guarantee every result is a suitable prospect. Scores do not prove "
        "buying intent; manually verify each business before outreach."
    )


if __name__ == "__main__":
    main()
