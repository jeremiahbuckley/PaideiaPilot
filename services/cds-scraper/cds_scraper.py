import requests
import pdfplumber
import sqlite3
import json
import os
from bs4 import BeautifulSoup
import time

# List of universities and their CDS pages
COLLEGES = {
    "University of Georgia": "https://oir.uga.edu/common-data-set/",
    "University of Florida": "https://ir.aa.ufl.edu/common-data-set/",
    "University of South Carolina": "https://ipr.sc.edu/data/common-data-set/",
}

# SQLite database setup
DB_FILE = "cds_data.db"
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS cds_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        university TEXT,
        year TEXT,
        sat_25th INT,
        sat_75th INT,
        gpa_median REAL,
        class_rank_top_10_percent INT,
        ap_courses_median INT,
        varsity_athletes_percent INT
    )
""")
conn.commit()

# Directory to store PDFs
PDF_DIR = "cds_pdfs"
os.makedirs(PDF_DIR, exist_ok=True)


def fetch_cds_pdf(url, university):
    """Downloads the latest CDS PDF from a given URL."""
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        pdf_path = os.path.join(PDF_DIR, f"{university.replace(' ', '_')}_CDS.pdf")
        with open(pdf_path, "wb") as f:
            f.write(response.content)
        print(f"Downloaded: {pdf_path}")
        return pdf_path
    else:
        print(f"Failed to download: {url}")
        return None


def extract_cds_data(pdf_path):
    """Extracts key admissions data from a Common Data Set PDF."""
    sat_25th = sat_75th = gpa_median = class_rank_top_10 = ap_courses = varsity_athletes = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            # Extract SAT scores
            if "SAT Evidence-Based Reading and Writing 25th percentile" in text:
                try:
                    sat_25th = int(text.split("SAT Evidence-Based Reading and Writing 25th percentile")[1].split()[0])
                except:
                    pass
            if "SAT Evidence-Based Reading and Writing 75th percentile" in text:
                try:
                    sat_75th = int(text.split("SAT Evidence-Based Reading and Writing 75th percentile")[1].split()[0])
                except:
                    pass

            # Extract GPA median
            if "High school GPA average" in text:
                try:
                    gpa_median = float(text.split("High school GPA average")[1].split()[0])
                except:
                    pass

            # Extract class rank percentage
            if "Top 10% of High School Class" in text:
                try:
                    class_rank_top_10 = int(text.split("Top 10% of High School Class")[1].split()[0])
                except:
                    pass

            # Extract AP courses median
            if "Median number of AP courses" in text:
                try:
                    ap_courses = int(text.split("Median number of AP courses")[1].split()[0])
                except:
                    pass

            # Extract varsity athlete percentage
            if "Varsity athletes percentage" in text:
                try:
                    varsity_athletes = int(text.split("Varsity athletes percentage")[1].split()[0])
                except:
                    pass

    return {
        "sat_25th": sat_25th,
        "sat_75th": sat_75th,
        "gpa_median": gpa_median,
        "class_rank_top_10_percent": class_rank_top_10,
        "ap_courses_median": ap_courses,
        "varsity_athletes_percent": varsity_athletes
    }


def store_data(university, year, data):
    """Stores extracted CDS data in the SQLite database."""
    cursor.execute("""
        INSERT INTO cds_data (university, year, sat_25th, sat_75th, gpa_median, class_rank_top_10_percent, ap_courses_median, varsity_athletes_percent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (university, year, data["sat_25th"], data["sat_75th"], data["gpa_median"],
          data["class_rank_top_10_percent"], data["ap_courses_median"], data["varsity_athletes_percent"]))
    conn.commit()
    print(f"Stored data for {university} ({year})")


def scrape_cds():
    """Main function to scrape CDS PDFs and extract data."""
    for university, url in COLLEGES.items():
        print(f"Processing {university}...")

        # Fetch the HTML page to find the latest CDS PDF
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        pdf_link = None
        for link in soup.find_all("a", href=True):
            if "CDS" in link["href"] or "Common_Data_Set" in link["href"]:
                pdf_link = link["href"]
                if not pdf_link.startswith("http"):
                    pdf_link = url + pdf_link  # Handle relative links
                break

        if pdf_link:
            pdf_path = fetch_cds_pdf(pdf_link, university)
            if pdf_path:
                data = extract_cds_data(pdf_path)
                store_data(university, "2023-24", data)
        else:
            print(f"Could not find CDS PDF for {university}")


if __name__ == "__main__":
    scrape_cds()
    conn.close()

