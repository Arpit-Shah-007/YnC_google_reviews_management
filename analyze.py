import glob
import json
import os
import re
from datetime import date as date_type
from urllib.parse import parse_qs, urlparse

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_gemini_model = None  # lazy init — avoids crashing tests that don't call analyze_store


def _get_model():
    global _gemini_model
    if _gemini_model is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise SystemExit("Missing GEMINI_API_KEY in .env")
        genai.configure(api_key=key)
        _gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    return _gemini_model


def load_latest_reviews(data_dir: str = "data") -> list[dict]:
    files = sorted(glob.glob(os.path.join(data_dir, "reviews_*.json")))
    if not files:
        raise SystemExit(f"No review files found in {data_dir}/. Run scrape.py first.")
    latest = files[-1]
    print(f"Loading reviews from {latest}")
    with open(latest) as f:
        return json.load(f)


def _extract_query(url: str) -> str:
    qs = parse_qs(urlparse(url).query)
    return qs.get("query", [""])[0].lower().strip()


def group_reviews_by_store(reviews: list[dict], stores: list[dict]) -> list[dict]:
    store_by_query = {_extract_query(s["google_maps_url"]): s for s in stores}

    grouped: dict[str, dict] = {s["google_maps_url"]: {"store": s, "reviews": []} for s in stores}

    for review in reviews:
        query = _extract_query(review.get("url", ""))
        store = store_by_query.get(query)
        if store:
            grouped[store["google_maps_url"]]["reviews"].append(review)

    return list(grouped.values())


def calculate_avg_rating(reviews: list[dict]) -> float | None:
    ratings = [r["stars"] for r in reviews if r.get("stars") is not None]
    if not ratings:
        return None
    return round(sum(ratings) / len(ratings), 1)


def build_gemini_prompt(store_name: str, address: str, reviews: list[dict]) -> str:
    review_lines = []
    for i, r in enumerate(reviews, 1):
        stars = r.get("stars", "?")
        text = (r.get("text") or "").strip()
        if text:
            review_lines.append(f"{i}. [{stars} stars] {text}")

    reviews_block = "\n".join(review_lines) if review_lines else "No review text available."

    return f"""You are an operations analyst for Yum and Chill Restaurant Group, a fast-food franchise operator.

Analyze the following {len(reviews)} Google Maps customer reviews for {store_name} located at {address}.

REVIEWS:
{reviews_block}

Provide a concise analysis for the store manager in this exact format:
SUMMARY: [2-3 sentences describing the main themes, recurring complaints, and any positives]
ACTIONS: 1. [specific action] 2. [specific action] 3. [specific action]

Be specific and actionable. Address the store manager directly."""


def parse_gemini_response(raw: str) -> dict:
    summary = ""
    actions = []

    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith("SUMMARY:"):
            summary = line[len("SUMMARY:"):].strip()
        elif line.startswith("ACTIONS:"):
            actions_str = line[len("ACTIONS:"):].strip()
            actions = re.findall(r"\d+\.\s(.+?)(?=\s\d+\.|$)", actions_str)
            actions = [a.strip() for a in actions if a.strip()]

    if not summary:
        summary = raw.strip()[:500]
    if not actions:
        actions = ["Review customer feedback and address recurring issues."]

    return {"summary": summary, "actions": actions}


def analyze_store(store_name: str, address: str, reviews: list[dict]) -> dict:
    if not reviews:
        return {
            "summary": "No reviews found in this period.",
            "actions": [],
            "avg_rating": None,
            "review_count": 0,
        }

    avg_rating = calculate_avg_rating(reviews)
    prompt = build_gemini_prompt(store_name, address, reviews)

    try:
        response = _get_model().generate_content(prompt)
        parsed = parse_gemini_response(response.text)
    except Exception as e:
        print(f"  WARNING: Gemini call failed for {store_name}: {e}")
        parsed = {"summary": "Analysis unavailable.", "actions": []}

    return {
        "summary": parsed["summary"],
        "actions": parsed["actions"],
        "avg_rating": avg_rating,
        "review_count": len(reviews),
    }


BRAND_STYLES = {
    "Taco Bell": {"bg": "702082", "fg": "F5D619"},
    "Wendy's": {"bg": "CC2222", "fg": "FFFFFF"},
}

RATING_FILLS = {
    "red":    PatternFill("solid", fgColor="FFCCCC"),
    "yellow": PatternFill("solid", fgColor="FFFFCC"),
    "green":  PatternFill("solid", fgColor="CCFFCC"),
}

THIN_BORDER = Border(
    left=Side(style="thin", color="DDDDDD"),
    right=Side(style="thin", color="DDDDDD"),
    top=Side(style="thin", color="DDDDDD"),
    bottom=Side(style="thin", color="DDDDDD"),
)

COLUMN_WIDTHS = {
    "Store #": 12,
    "Store Name": 28,
    "Full Address": 40,
    "Avg Rating": 12,
    "Reviews Analyzed": 18,
    "Period": 16,
    "AI Summary & Action Items": 80,
}
HEADERS = list(COLUMN_WIDTHS.keys())


def _rating_fill(rating: float | None) -> PatternFill | None:
    if rating is None:
        return None
    if rating <= 3.4:
        return RATING_FILLS["red"]
    if rating <= 3.9:
        return RATING_FILLS["yellow"]
    return RATING_FILLS["green"]


def _write_sheet(ws, group_stores: list[dict], brand: str, period_label: str):
    style = BRAND_STYLES.get(brand, {"bg": "333333", "fg": "FFFFFF"})
    header_fill = PatternFill("solid", fgColor=style["bg"])
    header_font = Font(bold=True, color=style["fg"], size=11)

    # Write header row
    for col_idx, header in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
    ws.row_dimensions[1].height = 30

    # Write data rows
    for row_idx, entry in enumerate(group_stores, 2):
        store = entry["store"]
        analysis = entry["analysis"]

        actions_text = ""
        if analysis["actions"]:
            actions_text = " ".join(
                f"{i}. {a}" for i, a in enumerate(analysis["actions"], 1)
            )

        summary_full = analysis["summary"]
        if actions_text:
            summary_full = f"{summary_full}\n\n{actions_text}"

        rating = analysis["avg_rating"]
        rating_display = f"{rating:.1f} ⭐" if rating is not None else "—"

        row_values = [
            store["store_number"],
            store["name"],
            store["address"],
            rating_display,
            analysis["review_count"] or "—",
            period_label,
            summary_full,
        ]

        # Alternating row background
        row_fill = PatternFill("solid", fgColor="F9F9F9") if row_idx % 2 == 0 else None

        for col_idx, value in enumerate(row_values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=(col_idx == len(HEADERS)))

            if row_fill:
                cell.fill = row_fill

            # Rating column conditional color (overrides row fill)
            if col_idx == 4:
                fill = _rating_fill(rating)
                if fill:
                    cell.fill = fill
                cell.alignment = Alignment(horizontal="center", vertical="top")

        ws.row_dimensions[row_idx].height = max(60, 15 * (summary_full.count("\n") + 3))

    # Set column widths
    for col_idx, header in enumerate(HEADERS, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = COLUMN_WIDTHS[header]

    # Freeze header row
    ws.freeze_panes = "A2"


def write_excel(grouped: list[dict], start_date: str, out_dir: str = "output") -> str:
    os.makedirs(out_dir, exist_ok=True)
    month_label = date_type.fromisoformat(start_date).strftime("%b%Y")
    today_label = date_type.today().strftime("%b %d, %Y")
    period_label = f"{date_type.fromisoformat(start_date).strftime('%b %Y')} – {date_type.today().strftime('%b %d, %Y')}"
    filename = f"YANDC_Review_Analysis_{month_label}.xlsx"
    out_path = os.path.join(out_dir, filename)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet

    tab_groups = [
        ("Taco Bell", "Taco Bell"),
        ("Wendy's North", "Wendy's"),
        ("Wendy's South", "Wendy's"),
    ]

    for tab_name, brand in tab_groups:
        ws = wb.create_sheet(title=tab_name)
        ws.sheet_properties.tabColor = (
            "702082" if brand == "Taco Bell" else "CC2222"
        )
        group_stores = [e for e in grouped if e["store"]["group"] == tab_name]
        _write_sheet(ws, group_stores, brand, period_label)

    wb.save(out_path)
    print(f"Excel report saved to {out_path}")
    return out_path


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze reviews and write Excel report")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD matching your scrape")
    args = parser.parse_args()

    with open("stores.json") as f:
        stores = json.load(f)

    reviews = load_latest_reviews()
    grouped_raw = group_reviews_by_store(reviews, stores)

    print(f"Analyzing {len(grouped_raw)} stores with Gemini...")
    grouped = []
    for entry in grouped_raw:
        store = entry["store"]
        store_reviews = entry["reviews"]
        print(f"  {store['name']} ({len(store_reviews)} reviews)")
        analysis = analyze_store(store["name"], store["address"], store_reviews)
        grouped.append({"store": store, "analysis": analysis})

    out_path = write_excel(grouped, args.start)
    print(f"\nDone. Report: {out_path}")


if __name__ == "__main__":
    main()
