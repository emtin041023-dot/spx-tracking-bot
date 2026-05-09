import time
import gspread
import requests

from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

from selenium import webdriver
from selenium.webdriver.common.by import By

from gspread_formatting import (
    format_cell_range,
    CellFormat,
    Color,
)


# =========================
# TELEGRAM CONFIG
# =========================
BOT_TOKEN = "8723483574:AAF9HmbZ6UwbiRAopkEfz7Xrt2Ws_eSui5k"
CHAT_ID = "652298969"


# =========================
# GOOGLE SHEET CONFIG
# =========================
SPREADSHEET_NAME = "tun check spx"
WORKSHEET_NAME = "sheet 1"

# Cột dữ liệu
COL_TRACKING = 13  # M
COL_LINK = 14      # N
COL_STATUS = 15    # O
COL_CARRIER = 16   # P


# =========================
# SEND TELEGRAM
# =========================
def send_telegram(message):
    if not BOT_TOKEN or "DAN_TOKEN" in BOT_TOKEN:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message,
            },
            timeout=20,
        )
    except Exception as e:
        print("Telegram error:", e)


# =========================
# GOOGLE SHEETS LOGIN
# =========================
def get_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json",
        scope,
    )

    client = gspread.authorize(creds)

    return client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)


# =========================
# CHROME DRIVER
# =========================
def get_driver():
    options = webdriver.ChromeOptions()

    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    return webdriver.Chrome(options=options)


# =========================
# GET SPX STATUS
# =========================
def get_spx_status(driver):
    page_text = driver.find_element(By.TAG_NAME, "body").text
    lines = page_text.split("\n")

    fake_status = [
        "Chờ lấy hàng",
        "Đang vận chuyển",
        "Đang giao hàng",
        "Đã giao hàng",
    ]

    for i in range(len(lines)):
        line = lines[i].strip()

        if ":" in line and len(line) <= 10:
            try:
                time_text = line
                date_text = lines[i + 1].strip()
                status_text = lines[i + 2].strip()

                if status_text not in fake_status:
                    return f"{time_text} | {date_text} | {status_text}"
            except:
                pass

    return "Không lấy được trạng thái"


# =========================
# GET GHN STATUS
# =========================
def get_ghn_status(driver):
    try:
        time.sleep(3)

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        if not rows:
            return "Không lấy được trạng thái"

        cols = rows[0].find_elements(By.TAG_NAME, "td")

        if len(cols) >= 3:
            status_text = cols[0].text.strip()
            detail_text = cols[1].text.strip()
            time_text = cols[2].text.strip()

            return f"{status_text} | {time_text} | {detail_text}"

        return "Không lấy được trạng thái"

    except Exception as e:
        print("GHN ERROR:", e)
        return "Không lấy được trạng thái"


# =========================
# GET TRACKING URL
# =========================
def get_tracking_url(tracking_code, carrier):
    carrier = (carrier or "").strip().upper()

    if carrier == "SPX":
        return f"https://spx.vn/track?{tracking_code}"

    if carrier == "GHN":
        return f"https://donhang.ghn.vn/?order_code={tracking_code}"

    return None


# =========================
# GET STATUS BY CARRIER
# =========================
def get_status(driver, carrier):
    carrier = (carrier or "").strip().upper()

    if carrier == "SPX":
        return get_spx_status(driver)

    if carrier == "GHN":
        return get_ghn_status(driver)

    return "Không lấy được trạng thái"


# =========================
# APPLY COLOR
# =========================
def apply_status_color(sheet, row, status):
    cell_range = f"O{row}"

    # Green
    if (
        "Đã giao" in status
        or "Giao hàng thành công" in status
    ):
        color = Color(0.75, 0.93, 0.78)

    # Red
    elif (
        "Giao thất bại" in status
        or "Giao không thành công" in status
    ):
        color = Color(1, 0.7, 0.7)

    # Yellow
    elif (
        "Đang giao" in status
        or "Đang lấy hàng" in status
        or "đến kho" in status
        or "vận chuyển" in status
        or "luân chuyển" in status
    ):
        color = Color(1, 0.95, 0.6)

    # Blue
    else:
        color = Color(0.75, 0.85, 1)

    format_cell_range(
        sheet,
        cell_range,
        CellFormat(backgroundColor=color),
    )


# =========================
# SEND DAILY REPORT
# =========================
def send_daily_report(sheet):
    current_hour = datetime.now().strftime("%H")

    if current_hour not in ["12", "22"]:
        return

    statuses = sheet.col_values(COL_STATUS)[1:]

    total = 0
    delivered = 0
    shipping = 0
    failed = 0
    waiting = 0

    for s in statuses:
        s = str(s).strip()

        if not s:
            continue

        total += 1

        if "Giao hàng thành công" in s or "Đã giao" in s:
            delivered += 1

        elif "Giao thất bại" in s or "Giao không thành công" in s:
            failed += 1

        elif (
            "đến kho" in s
            or "Đang giao" in s
            or "Đang lấy hàng" in s
            or "vận chuyển" in s
            or "luân chuyển" in s
        ):
            shipping += 1

        else:
            waiting += 1

    message = f"""
📦 BÁO CÁO SPX/GHN

🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}

━━━━━━━━━━

📊 Tổng đơn: {total}

✅ Đã giao: {delivered}

🚚 Đang vận chuyển: {shipping}

❌ Giao thất bại: {failed}

📥 Chờ xử lý: {waiting}

━━━━━━━━━━
"""

    send_telegram(message)


# =========================
# MAIN
# =========================
def main():
    print("=" * 50)
    print("START:", datetime.now())

    log_file = open("log.txt", "a", encoding="utf-8")

    sheet = get_sheet()
    driver = get_driver()

    try:
        last_row = len(sheet.col_values(COL_TRACKING))

        for row in range(2, last_row + 1):
            tracking_code = sheet.cell(row, COL_TRACKING).value

            if not tracking_code:
                continue

            current_status = str(
                sheet.cell(row, COL_STATUS).value or ""
            )

            # Skip delivered
            if (
                "Đã giao" in current_status
                or "Giao hàng thành công" in current_status
            ):
                print("SKIP:", tracking_code)
                continue

            carrier = str(
                sheet.cell(row, COL_CARRIER).value or ""
            ).upper()

            tracking_url = get_tracking_url(
                tracking_code,
                carrier,
            )

            if not tracking_url:
                print("UNKNOWN CARRIER:", tracking_code)
                continue

            print("Checking:", tracking_code, carrier)

            try:
                # Update link
                sheet.update_cell(row, COL_LINK, tracking_url)

                # Open website
                driver.get(tracking_url)
                time.sleep(5)

                latest_status = get_status(driver, carrier)

                # Retry once if failed
                if latest_status == "Không lấy được trạng thái":
                    print("Retry:", tracking_code)
                    driver.refresh()
                    time.sleep(5)
                    latest_status = get_status(driver, carrier)

                # Telegram if changed
                if latest_status != current_status:
                    send_telegram(
                        f"📦 {carrier} UPDATE\n\n"
                        f"📌 {tracking_code}\n\n"
                        f"📄 {latest_status}"
                    )

                # Update sheet
                sheet.update_cell(row, COL_STATUS, latest_status)

                # Color
                apply_status_color(sheet, row, latest_status)

                print("Latest:", latest_status)

            except Exception as e:
                print("ROW ERROR:", e)
                sheet.update_cell(row, COL_STATUS, "ERROR")

        # Daily report
        send_daily_report(sheet)

        print("DONE")
        log_file.write(f"{datetime.now()} | DONE\n")

    except Exception as e:
        print("MAIN ERROR:", e)
        log_file.write(f"{datetime.now()} | MAIN ERROR | {e}\n")

    finally:
        log_file.flush()
        log_file.close()
        driver.quit()


# =========================
# RUN EVERY 30 MINUTES
# =========================
if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print("FATAL ERROR:", e)

        print("Sleeping 30 minutes...")
        time.sleep(1800)