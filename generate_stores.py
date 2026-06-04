import json
import urllib.parse
import openpyxl


SECTION_HEADERS = {"Taco Bells", "Wendy's North", "Wendy's South"}
GROUP_MAP = {
    "Taco Bells": "Taco Bell",
    "Wendy's North": "Wendy's North",
    "Wendy's South": "Wendy's South",
}
BRAND_MAP = {
    "Taco Bell": "Taco Bell",
    "Wendy's North": "Wendy's",
    "Wendy's South": "Wendy's",
}


def build_google_maps_url(store_name: str, address: str) -> str:
    query = urllib.parse.quote_plus(f"{store_name} {address}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def parse_site_list(path: str = "Site List.xlsx") -> list[dict]:
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    stores = []
    current_group = None

    for row in ws.iter_rows(min_row=2, values_only=True):
        name, store_num, addr1, addr2, city, state, zipcode = row

        if name in SECTION_HEADERS:
            current_group = GROUP_MAP[name]
            continue

        if not name or not addr1 or not current_group:
            continue

        parts = [addr1]
        if addr2:
            parts.append(addr2)
        zip_str = str(int(float(str(zipcode)))).zfill(5) if zipcode is not None else ""
        parts.append(f"{city}, {state} {zip_str}".strip())
        full_address = ", ".join(parts)

        brand = BRAND_MAP[current_group]
        store_num_str = str(store_num).split(".")[0] if store_num is not None else "unknown"

        stores.append({
            "brand": brand,
            "group": current_group,
            "store_number": store_num_str,
            "name": f"{brand} #{store_num_str}",
            "address": full_address,
            "google_maps_url": build_google_maps_url(brand, full_address),
        })

    return stores


if __name__ == "__main__":
    stores = parse_site_list()
    with open("stores.json", "w") as f:
        json.dump(stores, f, indent=2)
    print(f"Generated stores.json with {len(stores)} stores")
    for group in ["Taco Bell", "Wendy's North", "Wendy's South"]:
        count = sum(1 for s in stores if s["group"] == group)
        print(f"  {group}: {count} stores")
