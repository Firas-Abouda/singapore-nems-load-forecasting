from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


START_DATE = date(2020, 1, 6)

BASE_URL = (
    "https://www.ema.gov.sg/content/dam/corporate/resources/"
    "statistics/half-hourly-data/{year}/{day}.{ext}"
)

EMA_PAGE = (
    "https://www.ema.gov.sg/resources/statistics/"
    "half-hourly-system-demand-data"
)

RAW_DIR = Path("data/raw/ema_demand").resolve()

XLS= bytes.fromhex("D0CF11E0A1B11AE1")
XLSX = b"PK\x03\x04"


def last_completed_monday() -> date:
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    return current_monday - timedelta(days=7)


def is_valid_excel(path: Path) -> bool:
    if not path.exists():
        return False

    header = path.read_bytes()[:8]

    return (
        header.startswith(XLS)
        or header.startswith(XLSX)
    )


def wait_for_download(path: Path, timeout: float = 15) -> bool:
    deadline = time.time() + timeout

    while time.time() < deadline:
        partial = path.with_name(path.name + ".crdownload")

        if path.exists() and not partial.exists():
            return is_valid_excel(path)

        time.sleep(0.25)

    return False


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    options = Options()

    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(RAW_DIR),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
        },
    )

    # With Google chrome
    driver = webdriver.Chrome(options=options)

    try:
        # Open EMA normally first.
        driver.get(EMA_PAGE)

        print()
        print("EMA opened in Chrome.")
        print("If EMA asks for any browser verification, complete it manually.")
        input("When the EMA page works normally, press Enter here... ")

        current = START_DATE
        end = last_completed_monday()

        downloaded = 0
        skipped = 0
        missing = []

        while current <= end:
            day = current.strftime("%Y%m%d")

            existing_xls = RAW_DIR / f"{day}.xls"
            existing_xlsx = RAW_DIR / f"{day}.xlsx"

            if is_valid_excel(existing_xls) or is_valid_excel(existing_xlsx):
                print(f"SKIP {day}")
                skipped += 1
                current += timedelta(days=7)
                continue

            success = False

            for ext in ("xls", "xlsx"):
                destination = RAW_DIR / f"{day}.{ext}"

                url = BASE_URL.format(
                    year=current.year,
                    day=day,
                    ext=ext,
                )

                driver.get(url)

                if wait_for_download(destination):
                    print(f"OK   {destination.name}")
                    downloaded += 1
                    success = True
                    break

                # Remove anything invalid that may have appeared.
                if destination.exists() and not is_valid_excel(destination):
                    destination.unlink()

            if not success:
                print(f"MISSING {current}")
                missing.append(current)

            current += timedelta(days=7)

            # Be polite to EMA.
            time.sleep(0.75)

        print()
        print("Done.")
        print(f"Downloaded: {downloaded}")
        print(f"Skipped:    {skipped}")
        print(f"Missing:    {len(missing)}")

        for missing_date in missing:
            print(f"  - {missing_date}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()