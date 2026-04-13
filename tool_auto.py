import time, re, os, sys, json, hashlib, tempfile, shutil
import urllib.request
from io import BytesIO
from PIL import Image

from plyer import notification
from google import genai
from google.genai import types

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select as SeleniumSelect
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager
TOOL_VERSION = "3.1.0"
URL_REMOTE   = ""
SKIP_UPDATE  = os.getenv("AZOTA_SKIP_UPDATE", "0") == "1"

def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""): h.update(chunk)
    return h.hexdigest()

def check_and_update():
    if SKIP_UPDATE or "YOUR_USERNAME" in URL_REMOTE:
        if "YOUR_USERNAME" in URL_REMOTE:
            print("[Update] Chua cau hinh URL_REMOTE -> bo qua.\n")
        return
    
    is_exe = getattr(sys, 'frozen', False)
    
    if SKIP_UPDATE or "YOUR_USERNAME" in URL_REMOTE:
        if "YOUR_USERNAME" in URL_REMOTE:
            print("[Update] Chua cau hinh URL_REMOTE -> bo qua.\n")
        return
        
    try:
        # 2. Xác định file hiện tại (Nếu là exe thì lấy đường dẫn exe, nếu py thì lấy __file__)
        current_file = sys.executable if is_exe else os.path.abspath(__file__)
        
        tmp = tempfile.mktemp(suffix=".exe" if is_exe else ".py")
        urllib.request.urlretrieve(URL_REMOTE, tmp)
        
        if _md5(current_file) != _md5(tmp):
            # Lưu ý: File .exe đang chạy không thể tự ghi đè chính nó trực tiếp trên Windows
            if is_exe:
                print("[Update] Co ban moi, vui long tai file .exe moi thay the.")
                os.remove(tmp)
                return
            
            shutil.copy(tmp, current_file)
            os.remove(tmp)
            notification.notify(title="Azota cap nhat!", message="Dang restart...", timeout=3)
            time.sleep(2)
            env = os.environ.copy()
            env["AZOTA_SKIP_UPDATE"] = "1"
            os.execve(sys.executable, [sys.executable, current_file] + sys.argv[1:], env)
            
        os.remove(tmp)
        print("[Update] Phien ban moi nhat.\n")
    except Exception as e:
        print(f"[Update] Loi: {e}\n")

check_and_update()

print(r"""
 _   _  ___  __  __ _______        _____  ____  _  __
| | | |/ _ \|  \/  | ____\ \      / / _ \|  _ \| |/ /
| |_| | | | | |\/| |  _|  \ \ /\ / / | | | |_) | ' /
|  _  | |_| | |  | | |___  \ V  V /| |_| |  _ <| . \
|_| |_|\___/|_|  |_|_____|  \_/\_/  \___/|_| \_\_|\_\
                  -- Tool by Nguyen Quoc Dat --  v3.1
""")

# ═══════════════════════════════════════════════════════════════
# NHAP THONG TIN
# ═══════════════════════════════════════════════════════════════
link_homework = input("Nhap link bai tap          : ").strip()
Name          = input("Nhap ten thi sinh          : ").strip()

print("\nNhap API key Gemini (nhap nhieu key ngan cach dau PHAY de doi tu dong khi het quota):")
print("Vi du: AIza...key1,AIza...key2")
_raw = input("API key(s)                 : ").strip()
API_KEYS = [k.strip() for k in _raw.split(",") if k.strip()]
if not API_KEYS:
    print("Chua nhap API key!"); sys.exit(1)
API_KEY = API_KEYS[0]   # giu tuong thich

notification.notify(
    title="Azota AutoSolver v3.1",
    message=f"Ten: {Name} | {len(API_KEYS)} key | Dang chay...",
    timeout=4,
)

# ═══════════════════════════════════════════════════════════════
# GEMINI — nhieu key luan phien + auto-retry 429
#
# Free tier:
#   gemini-2.0-flash-lite : 30 req/phut | 1500 req/NGAY
#   gemini-1.5-flash      : 15 req/phut |   50 req/NGAY  (fallback)
#
# Khi 1 key het quota NGAY -> doi sang key tiep theo tu dong
# Khi het tat ca key -> hoi nguoi dung them key hoac dung
# ═══════════════════════════════════════════════════════════════
MODELS_PRIORITY = [
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
]

_key_idx   = 0
_model_idx = 0
_exhausted: set = set()

# Tạo danh sách các client sẵn cho từng API Key
CLIENTS = [genai.Client(api_key=k) for k in API_KEYS]

def _cur_client():
    return CLIENTS[_key_idx]

def _cur_model() -> str:
    return MODELS_PRIORITY[_model_idx]

def _switch_key_or_model() -> bool:
    """Doi key/model khi het quota ngay. Tra ve False neu het tat ca."""
    global _key_idx, _model_idx
    _exhausted.add((_key_idx, _model_idx))

    # Thu doi key (giu model)
    for ki in range(len(API_KEYS)):
        if (ki, _model_idx) not in _exhausted:
            _key_idx = ki
            print(f"  [↻ KEY] Doi sang key #{ki+1}  (model: {_cur_model()})")
            return True

    # Het key -> doi model, thu lai tat ca key
    for mi in range(len(MODELS_PRIORITY)):
        for ki in range(len(API_KEYS)):
            if (ki, mi) not in _exhausted:
                _key_idx = ki; _model_idx = mi
                print(f"  [↻ MODEL] Doi sang '{_cur_model()}' key #{ki+1}")
                return True

    # Het tat ca -> hoi them key moi
    print("\n  [!!!] TAT CA KEY DA HET QUOTA NGAY!")
    print("  -> Lay them key tai: https://aistudio.google.com")
    extra = input("  Nhap them key moi (Enter de dung): ").strip()
    if extra:
        API_KEYS.append(extra)
        _key_idx   = len(API_KEYS) - 1
        _model_idx = 0
        _exhausted.clear()
        print(f"  Da them key #{_key_idx+1}")
        return True
    return False

def _is_daily_limit(err: str) -> bool:
    """Phan biet het quota NGAY vs het quota PHUT."""
    return any(x in err for x in ["PerDay", "per_day", "daily", "GenerateRequestsPerDay"])

def _wait_secs(err: str) -> float:
    for pat in [r"Please retry in ([\d.]+)s", r"retry in ([\d.]+)s", r"retryDelay.*?(\d+)s"]:
        m = re.search(pat, err)
        if m: return min(float(m.group(1)) + 2, 65)
    return 15

def _call_gemini(contents) -> str:
    for attempt in range(15):
        try:
            r = _cur_client().models.generate_content(
                model=_cur_model(), contents=contents
            )
            return r.text.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                if _is_daily_limit(err):
                    print(f"  [429-DAY] Key #{_key_idx+1} het quota ngay")
                    if not _switch_key_or_model():
                        return ""
                    # Thu ngay khong sleep
                else:
                    w = _wait_secs(err)
                    print(f"  [429-min] cho {w:.0f}s (lan {attempt+1}, key#{_key_idx+1}, model:{_cur_model()})...")
                    time.sleep(w)
            else:
                raise
    return ""

def ask_text(prompt: str) -> str:
    return _call_gemini(prompt)

def ask_image(img_bytes: bytes, prompt: str) -> str:
    return _call_gemini([
        types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
        types.Part.from_text(text=prompt),
    ])

# ═══════════════════════════════════════════════════════════════
# SELENIUM HELPERS
# ═══════════════════════════════════════════════════════════════
def make_driver():
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    drv = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )
    drv.execute_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    return drv

def get_scroll_y(drv) -> int:
    return drv.execute_script("return window.scrollY")

def get_page_height(drv) -> int:
    return drv.execute_script("return document.body.scrollHeight")

def get_viewport_height(drv) -> int:
    return drv.execute_script("return window.innerHeight")

def scroll_to_y(drv, y: int, smooth=True):
    """Cuon den vi tri y pixel cu the."""
    behavior = "smooth" if smooth else "instant"
    drv.execute_script(f"window.scrollTo({{top:{y}, behavior:'{behavior}'}});")
    time.sleep(0.45 if smooth else 0.1)

def scroll_to_top(drv):
    scroll_to_y(drv, 0)
    time.sleep(0.3)

def safe_click(drv, el):
    drv.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", el)
    time.sleep(0.3)
    drv.execute_script("window.scrollBy(0,-80);")
    time.sleep(0.15)
    try: el.click()
    except Exception: drv.execute_script("arguments[0].click();", el)

def capture_viewport(drv) -> bytes:
    """Chup anh dung man hinh hien tai (viewport)."""
    return drv.get_screenshot_as_png()

def capture_element(drv, el) -> bytes:
    """Chup anh rieng mot element."""
    loc  = el.location_once_scrolled_into_view
    size = el.size
    png  = drv.get_screenshot_as_png()
    img  = Image.open(BytesIO(png))
    dpr  = drv.execute_script("return window.devicePixelRatio") or 1
    x = int(loc["x"]*dpr); y = int(loc["y"]*dpr)
    w = int(size["width"]*dpr); h = int(size["height"]*dpr)
    buf = BytesIO()
    img.crop((x, y, x+w, y+h)).save(buf, format="PNG")
    return buf.getvalue()

# ═══════════════════════════════════════════════════════════════
# BUOC 2: XU LY TEN THI SINH
# Phat hien: input go tay / select dropdown / list click
# ═══════════════════════════════════════════════════════════════
def _try_select(drv, name) -> bool:
    for el in drv.find_elements(By.TAG_NAME, "select"):
        try:
            s = SeleniumSelect(el)
            for opt in s.options:
                if name.lower() in opt.text.lower():
                    s.select_by_visible_text(opt.text)
                    print(f"  [ten] Chon <select>: {opt.text}"); return True
        except Exception: pass
    return False

def _try_list_click(drv, name) -> bool:
    # XPath: bat ky element nao chua text ten
    for el in drv.find_elements(By.XPATH, f"//*[contains(text(),'{name}')]"):
        if el.is_displayed() and el.tag_name in ("li","div","span","td","p","label","a","button"):
            safe_click(drv, el)
            print(f"  [ten] Click list: {el.text.strip()[:40]}"); return True
    return False

def _try_input_type(drv, name) -> bool:
    css_list = [
        "input[placeholder*='Ten']", "input[placeholder*='ten']",
        "input[placeholder*='Thi']", "input[placeholder*='name']",
        "input[placeholder*='Name']", "input[placeholder*='ho']",
    ]
    # Fallback: input text dau tien hien thi
    els = []
    for css in css_list:
        els = drv.find_elements(By.CSS_SELECTOR, css)
        if els: break
    if not els:
        els = [e for e in drv.find_elements(By.CSS_SELECTOR, "input[type='text']")
               if e.is_displayed()]

    for el in els:
        try:
            safe_click(drv, el)
            el.clear(); time.sleep(0.2)
            el.send_keys(name); time.sleep(1.0)
            # Kiem tra autocomplete dropdown
            for item in drv.find_elements(By.CSS_SELECTOR,
                    "[role='option'], .dropdown-item, li[class*='option'], li[class*='suggest']"):
                if name.lower() in item.text.lower() and item.is_displayed():
                    safe_click(drv, item)
                    print(f"  [ten] Autocomplete: {item.text.strip()}"); return True
            print(f"  [ten] Go ten: {name}"); return True
        except Exception: pass
    return False

def _vision_name(drv, name) -> bool:
    """Nho Gemini xac dinh cach nhap ten."""
    png = capture_viewport(drv)
    resp = ask_image(png,
        f"Trang nay yeu cau nhap ten thi sinh '{name}'.\n"
        f"Hay cho biet:\n"
        f"1. Loai: 'input' (o go tay) / 'select' (dropdown) / 'list' (click vao ten)\n"
        f"2. Toa do (x, y) cua element can tuong tac\n"
        f"JSON: {{\"type\":\"input\",\"x\":200,\"y\":300}}"
    )
    try:
        data = json.loads(re.search(r'\{[^}]+\}', resp).group())
        t = data.get("type","input")
        dpr = drv.execute_script("return window.devicePixelRatio") or 1
        x = int(data.get("x",0)/dpr); y = int(data.get("y",0)/dpr)
        scroll_y = get_scroll_y(drv)
        abs_y = y
        drv.execute_script(f"window.scrollTo(0,{max(0,abs_y-200)});")
        time.sleep(0.3)
        rel_y = abs_y - get_scroll_y(drv)
        ActionChains(drv).move_by_offset(x, rel_y).click().perform()
        ActionChains(drv).move_by_offset(-x, -rel_y).perform()
        time.sleep(0.3)
        if t == "input":
            ActionChains(drv).send_keys(name).perform()
        print(f"  [ten-vision] {t} click ({x},{y})"); return True
    except Exception as e:
        print(f"  [ten-vision] loi: {e}"); return False

def _click_confirm_after_name(drv) -> bool:
    """
    Sau khi nhap/chon ten, tim va click nut xac nhan.
    Thu nhieu ten nut khac nhau tuy trang.
    """
    time.sleep(0.8)   # doi UI update

    # --- Cach 1: tim nut theo text ---
    confirm_keywords = [
        "Xác nhận", "Xac nhan",
        "Tiếp tục", "Tiep tuc",
        "Đồng ý",   "Dong y",
        "OK", "Ok",
        "Bắt đầu",  "Bat dau",
        "Làm bài",  "Lam bai",
        "Vào thi",  "Vao thi",
        "Submit",   "Confirm",
        "Next",     "Continue",
    ]
    for kw in confirm_keywords:
        for el in drv.find_elements(By.XPATH,
                f"//button[contains(.,'{kw}')] | "
                f"//a[contains(.,'{kw}')] | "
                f"//input[@value='{kw}']"):
            if el.is_displayed() and el.is_enabled():
                safe_click(drv, el)
                print(f"  [confirm] Click nut: '{el.text.strip() or kw}'")
                time.sleep(1.0)
                return True

    # --- Cach 2: Enter trong o input (neu con focus) ---
    try:
        focused = drv.switch_to.active_element
        if focused.tag_name in ("input", "textarea"):
            focused.send_keys(Keys.RETURN)
            print("  [confirm] Nhan Enter trong o input")
            time.sleep(1.0)
            return True
    except Exception:
        pass

    # --- Cach 3: Gemini nhin anh tim nut xac nhan ---
    print("  [confirm] Dung Gemini Vision tim nut xac nhan...")
    try:
        png  = capture_viewport(drv)
        resp = ask_image(png,
            "Sau khi nhap ten thi sinh, trang nay co nut nao de xac nhan / tiep tuc khong?\n"
            "Neu co, cho toa do (x,y) cua nut do. JSON: {\"x\":200,\"y\":300}\n"
            "Neu khong co nut nao, tra loi: KHONG_CO"
        )
        if "KHONG_CO" in resp.upper():
            print("  [confirm] Trang khong can xac nhan")
            return False
        coords = json.loads(re.search(r'\{[^}]+\}', resp).group())
        dpr    = drv.execute_script("return window.devicePixelRatio") or 1
        x      = int(coords["x"] / dpr)
        y      = int(coords["y"] / dpr)
        scroll_y = get_scroll_y(drv)
        rel_y  = y - scroll_y
        ActionChains(drv).move_by_offset(x, rel_y).click().perform()
        ActionChains(drv).move_by_offset(-x, -rel_y).perform()
        print(f"  [confirm] Vision click ({x},{y})")
        time.sleep(1.0)
        return True
    except Exception as e:
        print(f"  [confirm] Loi: {e}")

    return False

def setup_name(drv, name):
    print("\n[BUOC 2] Xu ly ten thi sinh...")
    time.sleep(1.5)

    ok = False
    if _try_select(drv, name):   ok = True
    elif _try_list_click(drv, name): ok = True
    elif _try_input_type(drv, name): ok = True
    else:
        print("  Khong tim duoc tu dong -> dung Gemini Vision...")
        ok = _vision_name(drv, name)

    if ok:
        # Sau khi nhap/chon xong -> click nut xac nhan
        _click_confirm_after_name(drv)
    else:
        print("  [!] Khong xu ly duoc ten thi sinh")
    time.sleep(0.5)

# ═══════════════════════════════════════════════════════════════
# BUOC 3: BAT DAU LAM BAI
# ═══════════════════════════════════════════════════════════════
def click_start(drv):
    keywords = ["Bắt đầu","Bat dau","Làm bài","Lam bai","Vào thi","Vao thi","Start"]
    for kw in keywords:
        for el in drv.find_elements(By.XPATH,
                f"//button[contains(.,'{kw}')] | //a[contains(.,'{kw}')]"):
            if el.is_displayed():
                safe_click(drv, el)
                print(f"  [start] Click: {el.text.strip()}")
                return True
    return False

# ═══════════════════════════════════════════════════════════════
# BUOC 4: SCROLL XUONG VA CHUP ANH — GEMINI DOC CAU HOI
# ═══════════════════════════════════════════════════════════════
# Prompt gui kem moi anh viewport
VISION_READ_PROMPT = """
Ban dang xem mot PHAN cua bai trac nghiem online Azota.
Hay doc TAT CA cau hoi XUAT HIEN trong anh nay va tra loi.

QUY TAC TRA LOI:
- Trac nghiem 1 dap an  -> chi viet chu cai: A / B / C / D
- Trac nghiem nhieu dap -> viet chu cai ngan cach phay: A,C
- Dung / Sai            -> viet DUNG hoac SAI
- Dien so / tu          -> viet chinh xac so hoac tu do

FORMAT (khong them gi khac):
Cau 1: A
Cau 2: B,D
Cau 3: DUNG
Cau 4: 42

Neu cau hoi bi cat (khong thay day du), ghi "?" de xu ly sau.
Neu khong thay cau hoi nao, tra loi: KHONG_CO_CAU_HOI
"""

def scroll_and_capture_all(drv) -> dict:
    """
    Core function: Vuot man hinh tu tren xuong duoi.
    - Buoc cuon: 60% chieu cao viewport (de overlap 40%, tranh bo sot cau)
    - Moi buoc: chup anh -> gui Gemini -> lay dap an
    - Tra ve dict {cau_so (int): dap_an (str)}
    """
    print("\n[BUOC 4] === BAT DAU VUOT + CHUP ANH ===")

    # --- Trigger lazy-load: cuon het trang 1 lan truoc ---
    print("  [scroll] Cuon het trang de load noi dung...")
    prev_h = 0
    while True:
        h = get_page_height(drv)
        if h == prev_h: break
        prev_h = h
        drv.execute_script(f"window.scrollTo(0, {h});")
        time.sleep(0.5)
    scroll_to_top(drv)
    time.sleep(0.8)

    # --- Tinh cac vi tri cuon ---
    page_h  = get_page_height(drv)
    view_h  = get_viewport_height(drv)
    step    = int(view_h * 0.60)   # cuon 60% moi buoc -> overlap 40%
    positions = list(range(0, page_h, step))
    if page_h not in positions:
        positions.append(page_h)   # dam bao cuon den cuoi

    total_steps = len(positions)
    print(f"  [scroll] Chieu cao trang: {page_h}px | Viewport: {view_h}px")
    print(f"  [scroll] Tong so buoc cuon: {total_steps}")

    all_answers  = {}  # {cau_so: dap_an}
    seen_nums    = set()  # so cau da xu ly
    global_cau   = 0      # so cau lon nhat da gap

    for step_idx, pos in enumerate(positions):
        # --- Cuon den vi tri ---
        scroll_to_y(drv, pos)
        time.sleep(0.5)

        actual_y = get_scroll_y(drv)
        pct      = int((step_idx + 1) / total_steps * 100)
        print(f"\n  ┌─ Buoc {step_idx+1}/{total_steps} | Y={actual_y}px | {pct}% ─────")

        # --- Chup anh viewport hien tai ---
        png = capture_viewport(drv)

        # --- Gui Gemini doc cau hoi ---
        print(f"  │  Dang hoi Gemini...", end=" ", flush=True)
        hint = ""
        if global_cau > 0:
            hint = f"\n(Cac cau hoi truoc da den Cau {global_cau}. Tiep tuc tu Cau {global_cau+1} tro di.)"
        raw = ask_image(png, VISION_READ_PROMPT + hint)

        if not raw or "KHONG_CO_CAU_HOI" in raw:
            print("khong co cau hoi moi")
            print(f"  └──────────────────────────────────────────")
            continue

        # --- Parse ket qua ---
        batch = {}
        for line in raw.splitlines():
            line = line.strip()
            # Match: "Cau 5: A" hoac "5: A" hoac "5. A"
            m = re.match(r"(?:[Cc]au\s*)?(\d+)\s*[:\.\-]\s*(.+)", line)
            if m:
                num = int(m.group(1))
                ans = m.group(2).strip()
                if ans == "?": continue  # cau bi cat, bo qua
                if num not in seen_nums:
                    batch[num] = ans
                    seen_nums.add(num)

        new_found = len(batch)
        print(f"tim thay {new_found} cau moi")

        for num, ans in sorted(batch.items()):
            print(f"  │    Cau {num:>3}: {ans}")
            all_answers[num] = ans
            if num > global_cau:
                global_cau = num

        print(f"  └── Tong tich luy: {len(all_answers)} cau ──────────────────")
        time.sleep(1.5)  # nghi giua cac buoc de tranh 429

    print(f"\n  [DONE] Tong tat ca: {len(all_answers)} cau hoi da doc duoc")
    print(f"  Range: Cau {min(all_answers)} den Cau {max(all_answers)}" if all_answers else "")
    return all_answers

# ═══════════════════════════════════════════════════════════════
# BUOC 5: SCROLL LEN VA CLICK DAP AN
# ═══════════════════════════════════════════════════════════════
def find_question_elements(drv) -> list:
    """
    Dung JavaScript de tim tat ca element cau hoi THAT.
    Cau hoi that = chua it nhat 2 input[radio] HOAC 2 input[checkbox].
    Tra ve list theo thu tu xuat hien tren trang (top -> bottom).
    """
    els = drv.execute_script("""
        var found = [];
        var candidates = document.querySelectorAll('div, li, section, article');
        for (var i = 0; i < candidates.length; i++) {
            var el = candidates[i];
            var radios = el.querySelectorAll('input[type="radio"]');
            var checks = el.querySelectorAll('input[type="checkbox"]');
            var texts  = el.querySelectorAll('input[type="text"], textarea');
            if (radios.length >= 2 || checks.length >= 2 || texts.length >= 1) {
                // Loai bo neu la con cua element da co trong found
                var skip = false;
                for (var j = 0; j < found.length; j++) {
                    if (found[j].contains(el)) { skip = true; break; }
                }
                if (!skip) found.push(el);
            }
        }
        // Sap xep theo vi tri tren trang (top -> bottom)
        found.sort(function(a,b) {
            return a.getBoundingClientRect().top - b.getBoundingClientRect().top
                   + window.scrollY * 0;
        });
        return found;
    """)
    return els or []

def click_answer(drv, q_el, answer: str, cau_num: int):
    """Click vao dap an dung trong mot element cau hoi."""
    ans = answer.strip().upper()

    radios     = q_el.find_elements(By.CSS_SELECTOR, "input[type='radio']")
    checkboxes = q_el.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
    textinputs = q_el.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea")
    labels     = q_el.find_elements(By.CSS_SELECTOR, "label")

    if radios:
        # --- Trac nghiem 1 dap an ---
        m   = re.search(r"[A-D]", ans)
        idx = ord(m.group()) - ord("A") if m else 0
        idx = min(idx, len(radios) - 1)
        # Uu tien click label (UI dep hon, hieu qua hon)
        if labels and idx < len(labels):
            safe_click(drv, labels[idx])
        else:
            safe_click(drv, radios[idx])
        print(f"  ✓ Cau {cau_num}: [{m.group() if m else 'A'}] (radio)")

    elif checkboxes:
        # --- Trac nghiem nhieu dap an ---
        letters = re.findall(r"[A-D]", ans)
        for ch in letters:
            idx = ord(ch) - ord("A")
            if idx < len(checkboxes):
                if labels and idx < len(labels):
                    safe_click(drv, labels[idx])
                else:
                    safe_click(drv, checkboxes[idx])
                time.sleep(0.2)
        print(f"  ✓ Cau {cau_num}: [{','.join(letters)}] (checkbox)")

    elif textinputs:
        # --- Dien vao o text ---
        box = textinputs[0]
        safe_click(drv, box)
        box.clear(); time.sleep(0.1)
        box.send_keys(answer)
        print(f"  ✓ Cau {cau_num}: '{answer[:40]}' (text)")

    else:
        # --- Dung/Sai hoac nut dac biet ---
        is_true = any(w in ans for w in ["DUNG", "ĐÚNG", "TRUE"])
        targets = (["ĐÚNG","DUNG","TRUE"] if is_true else ["SAI","FALSE"])
        clicked = False
        for btn in q_el.find_elements(By.CSS_SELECTOR,
                "button, label, [role='button'], span.answer"):
            txt = btn.text.strip().upper()
            if any(t in txt for t in targets) and btn.is_displayed():
                safe_click(drv, btn)
                print(f"  ✓ Cau {cau_num}: [{btn.text.strip()}] (button)")
                clicked = True; break

        if not clicked:
            # Vision fallback: nho Gemini chi vi tri click
            print(f"  ? Cau {cau_num}: khong tim element -> dung vision...")
            _vision_click(drv, q_el, answer, cau_num)

def _vision_click(drv, q_el, answer: str, cau_num: int):
    """Chup anh cau hoi, nho Gemini chi toa do can click."""
    try:
        png  = capture_element(drv, q_el)
        resp = ask_image(png,
            f"Cau hoi so {cau_num}. Dap an can chon la: '{answer}'.\n"
            f"Cho toa do (x,y) TRONG ANH nay de click vao dap an do.\n"
            f"JSON: {{\"x\":100,\"y\":50}}"
        )
        coords = json.loads(re.search(r'\{[^}]+\}', resp).group())
        loc    = q_el.location_once_scrolled_into_view
        dpr    = drv.execute_script("return window.devicePixelRatio") or 1
        abs_x  = int(loc["x"] + coords["x"]/dpr)
        abs_y  = int(loc["y"] + coords["y"]/dpr)
        drv.execute_script(f"window.scrollTo(0,{max(0,abs_y-200)});")
        time.sleep(0.3)
        rel_y  = abs_y - get_scroll_y(drv)
        ActionChains(drv).move_by_offset(abs_x, rel_y).click().perform()
        ActionChains(drv).move_by_offset(-abs_x, -rel_y).perform()
        print(f"  ✓ Cau {cau_num}: vision click ({abs_x},{abs_y})")
    except Exception as e:
        print(f"  ✗ Cau {cau_num}: vision loi: {e}")

def scroll_and_apply_answers(drv, answers: dict):
    """
    Sau khi da co du dap an, cuon len lai va click.
    Dung JS de tim cac element cau hoi, map theo thu tu.
    """
    print("\n[BUOC 5] === SCROLL LEN VA CLICK DAP AN ===")
    scroll_to_top(drv)
    time.sleep(0.8)

    q_els = find_question_elements(drv)
    print(f"  [DOM] Tim thay {len(q_els)} element cau hoi co input")

    if not q_els:
        print("  [!] Khong tim thay element nao -> bo qua buoc click")
        return

    # Map 1-1: element thu i -> cau so i+1 (theo thu tu tren trang)
    # Neu Gemini tra loi tu Cau 1..N thi map thang
    applied = 0
    for i, q_el in enumerate(q_els):
        cau_num = i + 1
        ans = answers.get(cau_num)

        if not ans:
            print(f"  - Cau {cau_num}: khong co dap an -> bo qua")
            continue

        try:
            # Cuon den cau hoi
            drv.execute_script(
                "arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", q_el
            )
            time.sleep(0.35)
            drv.execute_script("window.scrollBy(0,-100);")
            time.sleep(0.2)

            click_answer(drv, q_el, ans, cau_num)
            applied += 1
            time.sleep(0.3)

        except StaleElementReferenceException:
            print(f"  ! Cau {cau_num}: stale element, thu lai...")
            # Lay lai list va thu tiep
            q_els = find_question_elements(drv)
            if i < len(q_els):
                try:
                    click_answer(drv, q_els[i], ans, cau_num)
                    applied += 1
                except Exception as e2:
                    print(f"  ✗ Cau {cau_num}: van loi: {e2}")
        except Exception as e:
            print(f"  ✗ Cau {cau_num}: loi: {e}")

    print(f"\n  [DONE] Da click {applied}/{len(q_els)} cau")

# ═══════════════════════════════════════════════════════════════
# BUOC 6: NOP BAI
# ═══════════════════════════════════════════════════════════════
def submit_exam(drv):
    print("\n[BUOC 6] Nop bai...")
    # Cuon xuong cuoi tim nut nop
    drv.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.8)

    nop_kws = ["Nộp bài","Nop bai","Submit","Hoàn thành","Hoan thanh","Kết thúc","Ket thuc"]
    for kw in nop_kws:
        for el in drv.find_elements(By.XPATH,
                f"//button[contains(.,'{kw}')] | //a[contains(.,'{kw}')]"):
            if el.is_displayed():
                safe_click(drv, el)
                print(f"  [nop] Click: {el.text.strip()}")
                time.sleep(2.5)
                # Xac nhan popup
                for ck in ["Xác nhận","Xac nhan","Đồng ý","Dong y","OK","Có","Co"]:
                    for cel in drv.find_elements(By.XPATH, f"//button[contains(.,'{ck}')]"):
                        if cel.is_displayed():
                            safe_click(drv, cel)
                            print(f"  [confirm] Click: {cel.text.strip()}")
                            return True
                return True

    print("  [!] Khong tim thay nut nop -> hay nop thu cong!")
    return False

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def run():
    drv = make_driver()
    try:
        SEP = "=" * 55

        # ── 1. Mo link ───────────────────────────────────────
        print(f"\n{SEP}")
        print(f"[BUOC 1] Mo link bai tap...")
        drv.get(link_homework)
        time.sleep(3)

        # ── 2. Ten thi sinh ──────────────────────────────────
        print(f"\n{SEP}")
        setup_name(drv, Name)
        time.sleep(1.5)

        # ── 3. Bat dau ───────────────────────────────────────
        print(f"\n{SEP}")
        print("[BUOC 3] Tim nut bat dau lam bai...")
        if click_start(drv):
            time.sleep(2.5)
        else:
            print("  Khong co nut bat dau, tiep tuc...")

        # ── 4. VUOT XUONG + DOC CAU HOI ──────────────────────
        print(f"\n{SEP}")
        answers = scroll_and_capture_all(drv)

        if not answers:
            print("\n[!] Gemini khong doc duoc cau hoi nao!")
            print("    Co the do: quota het, API key sai, hoac trang chua load xong.")
            input("Bam Enter de thoat...")
            return

        # Hien thi tom tat
        print(f"\n{SEP}")
        print(f"[TOM TAT] {len(answers)} dap an:")
        for k in sorted(answers.keys()):
            print(f"  Cau {k:>3}: {answers[k]}")

        # ── 5. VUOT LEN + CLICK DAP AN ───────────────────────
        print(f"\n{SEP}")
        scroll_and_apply_answers(drv, answers)

        # ── 6. NOP BAI ───────────────────────────────────────
        print(f"\n{SEP}")
        submit_exam(drv)

        notification.notify(
            title="✅ Azota v3.1 — Xong!",
            message=f"Da xu ly {len(answers)} cau cho {Name}",
            timeout=10,
        )
        print(f"\n{SEP}")
        print(f"HOAN THANH! Da lam {len(answers)} cau.")
        input("\nBam Enter de dong trinh duyet...")

    except Exception as e:
        import traceback
        print(f"\n[!] LOI NGHIEM TRONG: {e}")
        traceback.print_exc()
        notification.notify(title="❌ Azota Loi!", message=str(e)[:120], timeout=10)
        input("Bam Enter de thoat...")
    finally:
        drv.quit()

if __name__ == "__main__":
    run()
