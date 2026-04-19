import os
import sys
import io
import time
from pathlib import Path

# Fix encoding cho Windows Terminal (tránh lỗi cp1252 khi print tiếng Việt)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

# Lấy thư mục gốc (áp dụng cho cả file .py và khi build ra file .exe)
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Nếu file nằm sâu trong cấu trúc skill của agent, lùi ra ngoài 4 bậc để lấy thư mục gốc dự án
    if "fb-auto-poster" in current_dir and ".agents" in current_dir:
        return os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".."))
    return current_dir

BASE_DIR = get_base_dir()

# Tự động tìm Google Chrome trên Windows
def find_chrome_binary():
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Google\Chrome\Application\chrome.exe")
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("Không thể tìm thấy Google Chrome trên Windows! Hãy cài Chrome vào thư mục mặc định.")

CHROME_BINARY = find_chrome_binary()

# Đường dẫn tự động nhận dạng cho từng máy
PROFILE_ROOT = os.path.join(BASE_DIR, "facebook-chrome-profile")
FB_URL = "https://www.facebook.com"

SHEET_ID = "1txOKAVBAJhWyWNr4rxjs7zn5GKJvJKrQDmISNur-TVg"
CREDENTIALS_FILE = os.path.join(BASE_DIR, "prn8n-457809-2aa9c8e5f6d4.json")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

POSTS_DATA = []
WORKSHEET = None

def fetch_google_sheet():
    global WORKSHEET, POSTS_DATA
    try:
        credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        workbook = gc.open_by_key(SHEET_ID)
        
        try:
            WORKSHEET = workbook.worksheet("Post Bài FB")
        except:
            print("Không tìm thấy tab 'Post Bài FB', đang dùng tab đầu tiên...")
            WORKSHEET = workbook.sheet1
            
        records = WORKSHEET.get_all_records()
        headers = WORKSHEET.row_values(1)
        
        # Thêm cột Status nếu chưa có
        if 'Status' not in headers:
            status_col = len(headers) + 1
            WORKSHEET.update_cell(1, status_col, 'Status')
            headers = WORKSHEET.row_values(1)
            
        status_col_index = headers.index('Status') + 1

        for idx, row in enumerate(records):
            row_num = idx + 2
            tieu_de = str(row.get('Tiêu Đề', '')).strip()
            # Hỗ trợ lấy cột mang tên 'Nội Dung' hoặc 'Mô Tả'
            noi_dung = str(row.get('Nội Dung', row.get('Mô Tả', ''))).strip()
            hinh_anh = str(row.get('Hình ảnh', row.get('Hình Ảnh', ''))).strip()
            status = str(row.get('Status', '')).strip()
            
            # Chỉ xử lý các bài ở trạng thái UNAPPROVED
            if status == 'UNAPPROVED' and tieu_de != 'nan' and (tieu_de or noi_dung):
                POSTS_DATA.append({
                    "title": tieu_de, 
                    "content": noi_dung if noi_dung != 'nan' else "",
                    "image": hinh_anh if hinh_anh != 'nan' else "",
                    "row_num": row_num,
                    "status_col": status_col_index
                })
        print(f"Đã tải {len(POSTS_DATA)} bài viết từ Google Sheet.")
    except Exception as e:
        print(f"Không thể đọc trực tiếp từ Google Sheet API. Vui lòng kiểm tra file JSON hoặc quyền chia sẻ: {e}")

OPEN_WAIT_SECONDS = 8
DELAY_BETWEEN_CONTACTS = 2

# =========================
# SELECTORS (Facebook)
# =========================
FB_EMAIL_INPUT = (By.NAME, "email")
FB_PASS_INPUT = (By.NAME, "pass")
FB_LOGIN_BUTTON = (By.CSS_SELECTOR, "button[name='login'], div[aria-label='Đăng nhập'], div[aria-label='Log In'], div[aria-label='Log in']")
FB_HOME_ELEMENT = (By.CSS_SELECTOR, "div[aria-label='Trang chủ'], a[aria-label='Facebook']")





def resolve_image_path(img_name):
    """Resolve đường dẫn tuyệt đối cho file ảnh."""
    if not img_name:
        return None
    if os.path.exists(img_name):
        return img_name
    possible_paths = [
        os.path.join(BASE_DIR, "images", img_name),
        os.path.join(BASE_DIR, "images", f"{img_name}.jpg"),
        os.path.join(BASE_DIR, "images", f"{img_name}.png"),
        os.path.join(BASE_DIR, "images", f"{img_name}.jpeg"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return None

def upload_image_direct(driver, img_path):
    """
    Upload ảnh KHÔNG click nút Ảnh/Video (tránh mở modal thứ 2 đè lên modal tạo bài).
    Thay vào đó: unhide hidden input[type=file] bên trong dialog rồi send_keys trực tiếp.
    Trả về True nếu upload thành công.
    """
    if not img_path: return False
    print(f"Bước phụ: Upload ảnh trực tiếp vào file input (không mở modal phụ): '{img_path}'")

    try:
        # Lấy input[type=file] bên trong dialog trước
        dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
        file_inputs = dialog.find_elements(By.CSS_SELECTOR, "input[type='file']")
        print(f"-> Tìm thấy {len(file_inputs)} input[type=file] trong dialog")

        if not file_inputs:
            # Fallback: tìm toàn trang
            file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            print(f"-> Fallback toàn trang: {len(file_inputs)} input[type=file]")

        if not file_inputs:
            print("-> LỖI: Không tìm thấy bất kỳ input[type=file] nào!")
            return False

        uploaded = False
        for fi in reversed(file_inputs):
            try:
                # Unhide input để Selenium có thể gửi file (KHÔNG mở dialog mới vì không click)
                driver.execute_script("""
                    var el = arguments[0];
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    el.style.opacity = '1';
                    el.style.position = 'fixed';
                    el.style.top = '0';
                    el.style.left = '0';
                    el.style.width = '1px';
                    el.style.height = '1px';
                    el.style.zIndex = '-1';
                """, fi)
                fi.send_keys(img_path)
                uploaded = True
                print("-> Đã send_keys file ảnh thành công (không mở modal phụ)!")
                break
            except Exception as e:
                print(f"-> input này lỗi: {e}, thử input khác...")

        if not uploaded:
            print("-> LỖI: Không send_keys được vào bất kỳ input[type=file] nào!")
            return False

        # Poll xác nhận ảnh đã attach (thumbnail hoặc nút Gỡ xuất hiện)
        print("-> Đang chờ ảnh xuất hiện trong khung soạn thảo (tối đa 45s)...")
        for _ in range(30):
            time.sleep(1.5)
            indicators = driver.find_elements(
                By.XPATH,
                "//div[@role='dialog']//img[contains(@src,'blob:') or contains(@src,'scontent')]"
                " | //div[@role='dialog']//*[@aria-label='Gỡ' or @aria-label='Remove']"
            )
            if indicators:
                print(f"✅ XÁC NHẬN: Ảnh đã attach ({len(indicators)} indicator tìm thấy)!")
                return True

        print("⚠️ Không xác nhận được ảnh đã attach trong 45s, vẫn tiếp tục đăng...")
        return True

    except Exception as e:
        print(f"Lỗi khi upload ảnh: {e}")
        return False


# =========================
# BASIC
# =========================
def validate_environment():
    if not os.path.exists(CHROME_BINARY):
        raise FileNotFoundError(f"Không tìm thấy Chrome binary: {CHROME_BINARY}")
    if not os.path.isdir(PROFILE_ROOT):
        raise FileNotFoundError(f"Không tìm thấy Chrome profile: {PROFILE_ROOT}")


def build_driver():
    print(f"DEBUG: CHROME_BINARY = {CHROME_BINARY}")
    print(f"DEBUG: PROFILE_ROOT = {PROFILE_ROOT}")

    options = Options()
    options.binary_location = CHROME_BINARY
    options.add_argument(f"--user-data-dir={PROFILE_ROOT}")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")

    options.add_experimental_option("detach", True)

    try:
        driver = webdriver.Chrome(options=options)
        driver.get(FB_URL)
        return driver
    except Exception as e:
        print(f"DEBUG: Lỗi khi khởi tạo WebDriver: {e}")
        raise e


def js_click(driver, element):
    driver.execute_script("arguments[0].click();", element)


def scroll_into_view(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)


def check_login_status(driver, wait):
    """Kiểm tra xem đã đăng nhập chưa (tìm nút Trang chủ hoặc Logo Facebook)"""
    try:
        # Đợi 5 giây xem có thấy nút Trang chủ không
        WebDriverWait(driver, 5).until(EC.presence_of_element_located(FB_HOME_ELEMENT))
        return True
    except:
        return False


def login_facebook(driver, wait, email, password):

    try:
        print(f"Đang nhập liệu cho tài khoản: {email}")
        
        # Chờ và nhập Email
        email_field = wait.until(EC.presence_of_element_located(FB_EMAIL_INPUT))
        email_field.clear()
        email_field.send_keys(email)
        time.sleep(1)
        
        # Chờ và nhập Password
        pass_field = wait.until(EC.presence_of_element_located(FB_PASS_INPUT))
        pass_field.clear()
        pass_field.send_keys(password)
        time.sleep(1)
        
        # Bấm Enter trực tiếp từ ô mật khẩu cho chắc chắn thay vì chỉ click nút
        pass_field.send_keys(Keys.RETURN)
        time.sleep(1)
        
        # Dự phòng: Click nút Đăng nhập nếu Enter chưa chạy
        try:
            login_btn = wait.until(EC.element_to_be_clickable(FB_LOGIN_BUTTON))
            try:
                login_btn.click()
            except:
                driver.execute_script("arguments[0].click();", login_btn)
        except:
            pass
            
        print("Đã nhấn nút đăng nhập.")
        time.sleep(5) # Chờ chuyển trang
    except Exception as e:
        print(f"Lỗi khi đăng nhập: {e}")
        driver.save_screenshot("login_error.png")



# =========================
# =========================
# ACTIONS (Post, Send msg)
# =========================
def go_to_profile(driver, wait, profile_name):
    try:
        print(f"Đang tìm và click vào trang cá nhân: {profile_name}...")
        # Tìm thẻ span chứa đúng tên của bạn
        profile_xpath = f"//span[text()='{profile_name}' or contains(text(), '{profile_name}')]"
        profile_node = wait.until(EC.presence_of_element_located((By.XPATH, profile_xpath)))
        
        # Click vào node (do trên FB bọc bằng thẻ HTML phức tạp nên ta click qua Javascript luôn cho chắc)
        driver.execute_script("arguments[0].click();", profile_node)
            
        print("Đã click chuyển sang trang cá nhân. Đang tải trang...")
        time.sleep(5) # Chờ load DOM trang cá nhân của bạn
    except Exception as e:
        print(f"Lỗi khi tìm node {profile_name}, tự động fallback qua cách gõ thẳng link URL facebook.com/me...")
        # Fallback: cách bí mật nhưng cực chuẩn của Facebook để vào trang cá nhân
        driver.get("https://www.facebook.com/me")
        time.sleep(5)


def post_facebook_status(driver, wait, content, post_data):
    # Resolve đường dẫn ảnh ngay từ đầu
    img_path = resolve_image_path(post_data.get('image', '').strip())
    if post_data.get('image', '').strip() and not img_path:
        print(f"BỎ QUA ảnh: Không thấy file '{post_data['image']}' trên ổ cứng.")

    try:
        print("Đang tìm nút 'Bạn đang nghĩ gì?'...")
        # 1. Click vào "Bạn đang nghĩ gì?"
        # Dùng XPath để tìm thẻ span chứa text "Bạn đang nghĩ gì"
        create_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Bạn đang nghĩ gì') or contains(text(), 'on your mind')]")))
        
        # Scroll tí cho chắc chắn nút hiển thị
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", create_btn)
        time.sleep(1)
        
        try:
            create_btn.click()
        except:
            driver.execute_script("arguments[0].click();", create_btn)
            
        print("Đã click nút mở form Tạo bài viết. Đang chờ textbox xuất hiện...")
        time.sleep(3) # chờ modal mở ra và khởi tạo animation
        
        # 2. Gõ nội dung
        # Bắt buộc tìm textbox NẰM TRONG BẢNG DIALOG (Tránh vơ nhầm hộp Comment ở dưới)
        dialog_xpath = "//div[@role='dialog']//div[@role='textbox' and @contenteditable='true']"
        textbox = wait.until(EC.visibility_of_element_located((By.XPATH, dialog_xpath)))
        
        # Focus vào textbox bằng click trước khi gõ để Lexical React Editor nhận sự kiện
        try:
            textbox.click()
        except:
            driver.execute_script("arguments[0].focus();", textbox)
        time.sleep(1)
        
        # Giải quyết lỗi BMP của ChromeDriver chứa Emoji, sử dụng Clipboard JS để dán chữ thay vì send_keys
        js_paste = """
        const text = arguments[1];
        const dataTransfer = new DataTransfer();
        dataTransfer.setData('text/plain', text);
        const event = new ClipboardEvent('paste', {
          clipboardData: dataTransfer,
          bubbles: true
        });
        arguments[0].dispatchEvent(event);
        """
        driver.execute_script(js_paste, textbox, content)
        
        print(f"Đã dán nội dung vào form Tạo Bài Viết xong.")
        time.sleep(2) # đợi React nhận diện content để gỡ bỏ thuộc tính aria-disabled của nút Đăng
        
        # 2.5: Upload ảnh
        if img_path:
            time.sleep(1)  # Nhỏ buffer sau khi gõ text
            upload_image_direct(driver, img_path)
            time.sleep(2)  # Buffer sau khi ảnh attach xong

        # 3. Bấm nút Đăng
        print("Đang bấm nút Đăng...")
        # Tìm nút có aria-label là Đăng hoặc Post
        post_btn_xpath = "//div[(contains(@aria-label, 'Đăng') or contains(@aria-label, 'Post')) and @role='button']"
        post_btn = wait.until(EC.element_to_be_clickable((By.XPATH, post_btn_xpath)))
        
        try:
            post_btn.click()
        except:
            driver.execute_script("arguments[0].click();", post_btn)
            
        print("Đã click nút Đăng. Đợi fb xử lý bài viết...")
        time.sleep(5)
        
    except Exception as e:
        print(f"Lỗi khi đăng bài: {e}")
        driver.save_screenshot("post_error.png")
        print("Đã lưu screenshot: post_error.png")

# =========================
# MAIN
# =========================
def main_login_only():
    """Chế độ chỉ đăng nhập lần đầu — Mở Chrome, login, lưu cookie rồi thoát."""
    validate_environment()

    driver = None
    try:
        print("="*50)
        print("  CHẾ ĐỘ ĐĂNG NHẬP LẦN ĐẦU (--login-only)")
        print("="*50)
        print("\nĐang mở Facebook...")
        driver = build_driver()
        wait = WebDriverWait(driver, 20)

        # Kiểm tra xem đã login chưa
        if check_login_status(driver, wait):
            print("\n✅ Bạn ĐÃ đăng nhập sẵn rồi! Cookie đã được lưu trong chrome profile.")
            print("   Bạn có thể chạy script bình thường mà không cần --login-only nữa.")
        else:
            print("\n⚠️  Chưa đăng nhập. Vui lòng tự đăng nhập thủ công trên trình duyệt đang mở.")
            print("   Script đang chờ (Tối đa 5 phút)...")
            
            is_logged_in = False
            for _ in range(60): # 60 * 5s = 300 giây
                time.sleep(5)
                if check_login_status(driver, wait):
                    is_logged_in = True
                    break
            
            # Kiểm tra lại sau khi login
            if is_logged_in:
                print("\n✅ Đăng nhập THÀNH CÔNG! Cookie đã được lưu.")
            else:
                print("\n⚠️  Quá thời gian đăng nhập hoặc Facebook yêu cầu XÁC MINH quá lâu.")
        
        print("\n" + "-"*50)
        print("🔔 TRÌNH DUYỆT ĐANG MỞ - Hãy kiểm tra và xử lý nếu cần.")
        print("   Sau khi xong, nhấn ENTER tại đây để đóng trình duyệt và lưu session.")
        print("-"*50)
        input("\n>>> Nhấn ENTER để đóng trình duyệt... ")
        
    except Exception as exc:
        print(f"Lỗi: {exc}")
    finally:
        if driver is not None:
            print("\nĐang đóng trình duyệt và lưu session...")
            driver.quit()
            print("✅ Đã lưu xong! Lần sau chạy script sẽ tự nhận phiên đăng nhập cũ.")


def main():
    """Chế độ chạy bình thường — Login + Đăng bài tự động."""
    validate_environment()

    driver = None
    try:
        print("Mở Facebook...")
        driver = build_driver()
        wait = WebDriverWait(driver, 20)

        print("Trình duyệt đã mở Facebook.")
        
        # Kiểm tra xem có cần đăng nhập không
        if not check_login_status(driver, wait):
            print("Chưa đăng nhập Facebook!")
            print("Vui lòng tự đăng nhập trực tiếp trên cửa sổ Google Chrome vừa hiện ra. Đang chờ bạn (Tối đa 2 phút)...")
            
            is_logged_in = False
            for _ in range(24): # 24 * 5 = 120s
                time.sleep(5)
                if check_login_status(driver, wait):
                    is_logged_in = True
                    break
            
            if not is_logged_in:
                print("Đã hết 2 phút chờ tài khoản Facebook. Chương trình tự động thoát. Hãy chạy lại khi bạn sẵn sàng!")
                try:
                    driver.quit()
                except:
                    pass
                return
            
            print("Đã đăng nhập thành công! Bắt đầu tải dữ liệu post...")
        else:
            print("Đã nhận diện phiên đăng nhập cũ trong Profile Chrome. Bỏ qua bước kiểm tra đăng nhập.")
        
        time.sleep(5)

        # Tải dữ liệu từ Google Sheet
        print("Đang kết nối Google Sheet...")
        fetch_google_sheet()
        
        if POSTS_DATA:
            # -----------------------------
            # 1) VÀO TRANG CÁ NHÂN
            # -----------------------------
            go_to_profile(driver, wait, "Đạt Trần")
    
            # -----------------------------
            # 2) ĐĂNG BÀI THEO SHEET
            # -----------------------------
            print("\n--- BẮT ĐẦU ĐĂNG BÀI (Chế độ 1 bài/lần cho Cron) ---\n")
            
            # Lấy ĐÚNG 1 BÀI đầu tiên trong danh sách UNAPPROVED để đăng
            post = POSTS_DATA[0]
            print(f"-> Chuẩn bị đăng duy nhất bài viết tại dòng {post['row_num']}...")
            
            # Gộp Tiêu Đề và Nội Dung (cách nhau 2 dòng trắng)
            full_content = ""
            if post['title']:
                full_content += post['title'] + "\n\n"
            if post['content']:
                full_content += post['content']
            
            # Tiến hành nhấp form và đăng chữ (kèm ảnh nếu có)
            post_facebook_status(driver, wait, full_content, post)
            
            # Đánh dấu APPROVED về lại Google Sheet
            try:
                WORKSHEET.update_cell(post['row_num'], post['status_col'], 'APPROVED')
                print(f"Đã cập nhật trạng thái 'APPROVED' lên Google Sheet (Dòng {post['row_num']}).")
            except Exception as e:
                print(f"Lỗi khi update status lên Sheet: {e}")
                
            print("\n--- ĐÃ ĐĂNG XONG 1 BÀI TRONG LẦN CHẠY NÀY ---")
        else:
            print("\n--- GOOGLE SHEET TRỐNG: Không có bài viết nào ở trạng thái chờ. ---")

    except Exception as exc:
        print(f"Lỗi tổng: {exc}")
        if driver is not None:
            try:
                driver.save_screenshot("fb_error.png")
                print("Đã lưu screenshot: fb_error.png")
            except Exception:
                pass
        print("Có lỗi xảy ra.")

    # Tự động đóng trình duyệt sau khi xong việc
    if driver is not None:
        print("\n" + "="*50)
        print("Đã hoàn thành tác vụ. Đang tự động đóng trình duyệt...")
        print("="*50)
        driver.quit()



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Facebook Auto Poster - Windows Edition")
    parser.add_argument("--login-only", action="store_true",
                        help="Chỉ đăng nhập lần đầu, lưu cookie, không đăng bài.")
    args = parser.parse_args()

    if args.login_only:
        main_login_only()
    else:
        main()
