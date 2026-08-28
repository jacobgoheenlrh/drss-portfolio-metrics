import os
import csv
import requests
from datetime import datetime
from statistics import mean

ASANA_TOKEN = os.environ.get("ASANA_TOKEN")
PORTFOLIO_ID = "1211936365910428"
BASE_URL = "https://app.asana.com/api/1.0"
HEADERS = {"Authorization": f"Bearer {ASANA_TOKEN}", "Accept": "application/json"}
OUTPUT_FILE = "study_type_july_2026.csv"

FIELDS = {
    "study_type": "1211983136110071",
    "origination_date": "1213592016704745",
    "irb_submission_date": "1213780659973512",
    "irb_approval_date": "1213779721785821",
    "analysis_queue_date": "1216982897744923",
    "time_in_analysis": "1216993820576120",
    "completion_date": "1215452557663133",
}

STUDY_TYPES = {
    "Prospective": "1211983136110072",
    "Retrospective": "1211983136110073",
    "Retrospective - NHSR": "1217153608253349",
}

COLUMNS = [
    "Reporting Month",
    "Prospective Project Count",
    "Retrospective Project Count",
    "Retrospective - NHSR Project Count",
    "Average Days to IRB Submission - Prospective",
    "Average Days to IRB Submission - Retrospective",
    "Average Days to IRB Submission - Retrospective - NHSR",
    "Average Days to IRB Approval - Prospective",
    "Average Days to IRB Approval - Retrospective",
    "Average Days to IRB Approval - Retrospective - NHSR",
    "Average Days to Analysis - Prospective",
    "Average Days to Analysis - Retrospective",
    "Average Days to Analysis - Retrospective - NHSR",
    "Average Days in Analysis - Prospective",
    "Average Days in Analysis - Retrospective",
    "Average Days in Analysis - Retrospective - NHSR",
    "Average Days to Completion - Prospective",
    "Average Days to Completion - Retrospective",
    "Average Days to Completion - Retrospective - NHSR",
]

def get(endpoint, params=None):
    results = []
    params = params or {}
    while True:
        response = requests.get(BASE_URL + endpoint, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        results.extend(data.get("data", []))
        next_page = data.get("next_page")
        if not next_page:
            return results
        params["offset"] = next_page["offset"]

def extract_date(field):
    if not field:
        return None
    value = field.get("date_value")
    if value and value.get("date"):
        return datetime.strptime(value["date"], "%Y-%m-%d").date()
    return None

def safe_average(values):
    values = [x for x in values if x is not None]
    return round(mean(values), 1) if values else ""

def days_between(start, end):
    return (end - start).days if start and end else None

def collect_projects():
    raw_projects = get(
        f"/portfolios/{PORTFOLIO_ID}/items",
        {"limit": 100, "opt_fields": "name,custom_fields"}
    )
    projects = []
    for project in raw_projects:
        fields = {f["gid"]: f for f in project.get("custom_fields", [])}
        study_type_value = fields.get(FIELDS["study_type"], {}).get("enum_value")
        projects.append({
            "study_type_gid": study_type_value.get("gid") if study_type_value else None,
            "origination": extract_date(fields.get(FIELDS["origination_date"])),
            "irb_submission": extract_date(fields.get(FIELDS["irb_submission_date"])),
            "irb_approval": extract_date(fields.get(FIELDS["irb_approval_date"])),
            "analysis_queue": extract_date(fields.get(FIELDS["analysis_queue_date"])),
            "time_in_analysis": fields.get(FIELDS["time_in_analysis"], {}).get("number_value"),
            "completion": extract_date(fields.get(FIELDS["completion_date"])),
        })
    return projects

def generate_report(projects):
    report = {"Reporting Month": "July 2026"}
    grouped = {
        name: [p for p in projects if p["study_type_gid"] == gid]
        for name, gid in STUDY_TYPES.items()
    }

    for study_type, items in grouped.items():
        report[f"{study_type} Project Count"] = len(items)

    metrics = [
        ("Average Days to IRB Submission", lambda p: days_between(p["origination"], p["irb_submission"])),
        ("Average Days to IRB Approval", lambda p: days_between(p["origination"], p["irb_approval"])),
        ("Average Days to Analysis", lambda p: days_between(p["origination"], p["analysis_queue"])),
        ("Average Days in Analysis", lambda p: p["time_in_analysis"] / 1440 if p["time_in_analysis"] is not None and p["time_in_analysis"] > 0 else None),
        ("Average Days to Completion", lambda p: days_between(p["origination"], p["completion"])),
    ]

    for metric_name, calculation in metrics:
        for study_type, items in grouped.items():
            report[f"{metric_name} - {study_type}"] = safe_average(
                [calculation(p) for p in items]
            )

    return report

def write_csv(report):
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(report)

def main():
    if not ASANA_TOKEN:
        raise Exception("Missing ASANA_TOKEN")
    projects = collect_projects()
    print("Projects collected:", len(projects))
    write_csv(generate_report(projects))
    print("Study Type July 2026 report completed.")
    print("Output:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
