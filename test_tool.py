# ===========================================================================
#  _   _  ___  __  __ _______        _____  ____  _  __
# | | | |/ _ \|  \/  | ____\ \      / / _ \|  _ \| |/ /
# | |_| | | | | |\/| |  _|  \ \ /\ / / | | | |_) | ' /
# |  _  | |_| | |  | | |___  \ V  V /| |_| |  _ <| . \
# |_| |_|\___/|_|  |_|_____|  \_/\_/  \___/|_| \_\_|\_\
#                   -- Tool by Nguyen Quoc Dat --  v5.0
#
# TINH NANG CV2 (moi):
#   - Chup screenshot -> CV2 phan tich anh
#   - Phat hien cac o tron (radio) va o vuong (checkbox) bang HoughCircles + contour
#   - Phat hien vung text (A/B/C/D) bang contour detection
#   - Highlight vung se click bang overlay mau xanh la
#   - Hien thi anh debug truoc khi click (co the tat)
#   - Click chinh xac vao giua vung da phat hien
#
# CAI DAT:
#   pip install selenium webdriver-manager google-genai pillow plyer opencv-python numpy
#   pip install groq mistralai openai anthropic  (tuy chon)
# ===========================================================================

import time, re, os, sys, json, hashlib, tempfile, shutil, base64
import urllib.request
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

from plyer import notification
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select as SeleniumSelect
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

# ═══════════════════════════════════════════════════════════════
# AUTO-UPDATE
# ═══════════════════════════════════════════════════════════════
TOOL_VERSION = "5.0.0"
URL_REMOTE   = ""   # Dan link raw GitHub vao day
SKIP_UPDATE  = os.getenv("AZOTA_SKIP_UPDATE", "0") == "1"

def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""): h.update(chunk)
    return h.hexdigest()

def check_and_update():
    if SKIP_UPDATE or not URL_REMOTE or "YOUR_USERNAME" in URL_REMOTE: return
    try:
        tmp = tempfile.mktemp(suffix=".py")
        urllib.request.urlretrieve(URL_REMOTE, tmp)
        if _md5(__file__) != _md5(tmp):
            shutil.copy(tmp, __file__); os.remove(tmp)
            notification.notify(title="Azota cap nhat!", message="Restart...", timeout=3)
            time.sleep(2)
            env = os.environ.copy(); env["AZOTA_SKIP_UPDATE"] = "1"
            os.execve(sys.executable, [sys.executable, __file__] + sys.argv[1:], env)
        os.remove(tmp); print("[Update] Phien ban moi nhat.\n")
    except Exception as e:
        print(f"[Update] Loi: {e}\n")

check_and_update()

print(r"""
 _   _  ___  __  __ _______        _____  ____  _  __
| | | |/ _ \|  \/  | ____\ \      / / _ \|  _ \| |/ /
| |_| | | | | |\/| |  _|  \ \ /\ / / | | | |_) | ' /
|  _  | |_| | |  | | |___  \ V  V /| |_| |  _ <| . \
|_| |_|\___/|_|  |_|_____|  \_/\_/  \___/|_| \_\_|\_\
                  -- Tool by Nguyen Quoc Dat --  v5.0
""")

# ═══════════════════════════════════════════════════════════════
# NHAP THONG TIN
# ═══════════════════════════════════════════════════════════════
link_homework = input("Nhap link bai tap  : ").strip()
Name          = input("Nhap ten thi sinh  : ").strip()
SHOW_DEBUG    = input("Hien thi anh CV2?  (y/n, default=y): ").strip().lower() != "n"

print("""
=== NHAP API KEY (Enter de bo qua) ===
  Gemini : 1500 req/ngay FREE  | gemini-2.0-flash-lite
  Groq   : 14400 req/ngay FREE | llama-3.2-11b-vision
  Mistral: 1000 req/ngay FREE  | pixtral-12b
  OpenAI : Tra phi              | gpt-4o-mini
  Claude : Tra phi              | claude-haiku-4-5-20251001
""")

def _inp(label):
    v = input(f"  {label}: ").strip(); return v or None
def _keys(raw): return [k.strip() for k in raw.split(",") if k.strip()] if raw else []

GEMINI_KEYS  = _keys(_inp("Gemini key(s) [AIza...]"))
GROQ_KEYS    = _keys(_inp("Groq   key(s) [gsk_...]"))
MISTRAL_KEYS = _keys(_inp("Mistral key(s)"))
OPENAI_KEYS  = _keys(_inp("OpenAI key(s) [sk-...]"))
CLAUDE_KEYS  = _keys(_inp("Claude key(s) [sk-ant-...]"))

total = sum(len(x) for x in [GEMINI_KEYS,GROQ_KEYS,MISTRAL_KEYS,OPENAI_KEYS,CLAUDE_KEYS])
if not total: print("Chua nhap key!"); sys.exit(1)
print(f"\n  {total} key | CV2 highlight: {'ON' if SHOW_DEBUG else 'OFF'}\n")

notification.notify(title="Azota v5.0", message=f"{Name} | CV2+AI | {total} key", timeout=4)

# ═══════════════════════════════════════════════════════════════
# CV2 — NHAN DIEN VUNG DAP AN
# ═══════════════════════════════════════════════════════════════

def png_to_cv2(png_bytes: bytes) -> np.ndarray:
    """Chuyen PNG bytes -> numpy array BGR cho cv2."""
    arr = np.frombuffer(png_bytes, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

def cv2_to_png(img: np.ndarray) -> bytes:
    """Chuyen cv2 image -> PNG bytes."""
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()

def cv2_to_jpeg(img: np.ndarray, quality=75) -> bytes:
    """Chuyen cv2 image -> JPEG bytes (nho hon de gui AI)."""
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes()

# Mau highlight (BGR)
COLOR_HIGHLIGHT = (0, 220, 0)    # Xanh la tuoi
COLOR_SELECTED  = (0, 100, 255)  # Cam (dap an duoc chon)
COLOR_BORDER    = (255, 255, 255) # Vien trang
COLOR_TEXT_BG   = (0, 180, 0)    # Nen chu xanh la
ALPHA_OVERLAY   = 0.35            # Do trong suot overlay

class AnswerRegion:
    """Luu thong tin vung dap an da phat hien."""
    def __init__(self, label: str, x: int, y: int, w: int, h: int,
                 kind: str = "radio", confidence: float = 1.0):
        self.label      = label       # "A", "B", "C", "D"
        self.x, self.y  = x, y        # goc trai tren (trong anh)
        self.w, self.h  = w, h        # kich thuoc
        self.cx         = x + w // 2  # tam x
        self.cy         = y + h // 2  # tam y
        self.kind       = kind         # "radio" | "checkbox" | "button"
        self.confidence = confidence

def detect_answer_regions(img_bgr: np.ndarray) -> list[AnswerRegion]:
    """
    Phat hien cac vung dap an A/B/C/D trong anh bang CV2.
    Ket hop 3 phuong phap:
      1. HoughCircles -> phat hien nut radio tron
      2. Contour detection -> phat hien o vuong checkbox
      3. Template text matching -> tim chu A B C D
    Tra ve list AnswerRegion sap xep tu tren xuong duoi.
    """
    regions = []
    h_img, w_img = img_bgr.shape[:2]
    gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    # Lam mo nhe de giam nhieu
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # ── Phuong phap 1: HoughCircles (nhan dien o radio tron) ──────────
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=25,
        param1=60,
        param2=25,
        minRadius=7,
        maxRadius=18,
    )
    radio_centers = []
    if circles is not None:
        circles = np.round(circles[0, :]).astype(int)
        # Loc: chi lay circles co nen trang/sang (la o radio chua chon)
        for (cx, cy, r) in circles:
            roi = gray[max(0,cy-r):cy+r, max(0,cx-r):cx+r]
            if roi.size > 0 and np.mean(roi) > 180:  # nen sang
                radio_centers.append((cx, cy, r))

    # Map radio circles -> label A B C D theo thu tu tu tren xuong
    radio_centers.sort(key=lambda c: (c[1] // 40, c[0]))  # sap xep theo hang
    labels = ["A","B","C","D","E","F"]
    for i, (cx, cy, r) in enumerate(radio_centers[:6]):
        pad = r + 5
        regions.append(AnswerRegion(
            label=labels[i] if i < len(labels) else str(i),
            x=cx-pad, y=cy-pad, w=pad*2, h=pad*2,
            kind="radio", confidence=0.9
        ))

    # ── Phuong phap 2: Contour (nhan dien o checkbox vuong) ──────────
    if not regions:  # Chi dung neu khong tim duoc radio
        _, thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / max(h, 1)
            area   = w * h
            # Checkbox: gan vuong, kich co nho-vua
            if 0.7 < aspect < 1.3 and 150 < area < 1200:
                boxes.append((x, y, w, h))
        boxes.sort(key=lambda b: (b[1]//40, b[0]))
        for i, (x, y, w, h) in enumerate(boxes[:6]):
            regions.append(AnswerRegion(
                label=labels[i] if i < len(labels) else str(i),
                x=x, y=y, w=w, h=h,
                kind="checkbox", confidence=0.8
            ))

    # ── Phuong phap 3: Tim chu A B C D bang contour text ─────────────
    # Dung MSER hoac morphology de tim vung text label
    if not regions:
        # Adaptive threshold de phat hien text
        adap = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 4
        )
        # Ket noi cac pixel gan nhau (dilation)
        kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(adap, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        text_blocks = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            # Text block: khong qua nho, khong qua lon, gan vuong hoac ngang
            if 500 < area < 50000 and h > 15 and w > 15:
                text_blocks.append((x, y, w, h))
        # Lay 4 block lon nhat o phan giua-duoi cua man hinh
        text_blocks.sort(key=lambda b: b[1])
        mid_blocks = [b for b in text_blocks if b[1] > h_img * 0.2][:8]
        mid_blocks.sort(key=lambda b: (b[1]//60, b[0]))
        for i, (x, y, w, h) in enumerate(mid_blocks[:4]):
            regions.append(AnswerRegion(
                label=labels[i], x=x, y=y, w=w, h=h,
                kind="button", confidence=0.6
            ))

    # Sap xep cuoi cung: tu tren xuong duoi, trai sang phai
    regions.sort(key=lambda r: (r.y // 40, r.x))
    return regions

def highlight_regions(img_bgr: np.ndarray,
                      regions: list[AnswerRegion],
                      selected: str = "") -> np.ndarray:
    """
    Ve overlay highlight len anh:
    - Tat ca vung dap an: khung xanh la mo
    - Vung duoc chon (selected): khung cam day, chu noi bat
    """
    overlay = img_bgr.copy()
    result  = img_bgr.copy()

    for reg in regions:
        is_sel = reg.label.upper() == selected.upper()
        color  = COLOR_SELECTED if is_sel else COLOR_HIGHLIGHT
        thick  = 3 if is_sel else 2

        # Ve hinh chu nhat fill mo (overlay)
        cv2.rectangle(overlay,
                      (reg.x, reg.y),
                      (reg.x + reg.w, reg.y + reg.h),
                      color, -1)

        # Ket hop overlay voi anh goc
        cv2.addWeighted(overlay, ALPHA_OVERLAY, result, 1 - ALPHA_OVERLAY, 0, result)
        overlay = result.copy()  # Reset overlay cho vong tiep theo

        # Ve vien
        cv2.rectangle(result,
                      (reg.x - 1, reg.y - 1),
                      (reg.x + reg.w + 1, reg.y + reg.h + 1),
                      COLOR_BORDER, 1)
        cv2.rectangle(result,
                      (reg.x, reg.y),
                      (reg.x + reg.w, reg.y + reg.h),
                      color, thick)

        # Ve nhan (label) phia tren goc trai
        label_text = f"[{reg.label}]" + (" <-- CHON" if is_sel else "")
        font_scale = 0.55 if is_sel else 0.45
        font_thick = 2 if is_sel else 1

        # Nen chu
        (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thick)
        lx = reg.x; ly = max(reg.y - 6, th + 4)
        cv2.rectangle(result, (lx - 2, ly - th - 4), (lx + tw + 2, ly + 2),
                      COLOR_SELECTED if is_sel else COLOR_TEXT_BG, -1)
        cv2.putText(result, label_text,
                    (lx, ly),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                    (255, 255, 255), font_thick, cv2.LINE_AA)

        # Ve dau X hoac check o tam
        if is_sel:
            cx, cy = reg.cx, reg.cy
            r = min(reg.w, reg.h) // 3
            cv2.circle(result, (cx, cy), r + 2, COLOR_SELECTED, -1)
            cv2.line(result, (cx-r, cy-r), (cx+r, cy+r), (255,255,255), 2)
            cv2.line(result, (cx+r, cy-r), (cx-r, cy+r), (255,255,255), 2)

    return result

def show_debug_window(title: str, img_bgr: np.ndarray, wait_ms: int = 1200):
    """Hien thi anh debug. Auto-dong sau wait_ms ms."""
    if not SHOW_DEBUG: return
    # Resize neu qua lon de hien thi
    h, w = img_bgr.shape[:2]
    max_h = 700
    if h > max_h:
        scale = max_h / h
        img_bgr = cv2.resize(img_bgr, (int(w*scale), max_h))
    cv2.imshow(title, img_bgr)
    cv2.waitKey(wait_ms)
    cv2.destroyWindow(title)

def cv2_find_and_highlight(drv, q_el, answer_letter: str) -> tuple[int, int] | None:
    """
    Main CV2 function:
    1. Chup anh element cau hoi
    2. Phat hien cac vung dap an bang CV2
    3. Highlight vung can chon
    4. Hien thi debug window
    5. Tra ve toa do (abs_x, abs_y) de click, hoac None neu that bai
    """
    try:
        # Chup anh element
        loc  = q_el.location_once_scrolled_into_view
        sz   = q_el.size
        png  = drv.get_screenshot_as_png()
        img_pil = Image.open(BytesIO(png))
        dpr  = drv.execute_script("return window.devicePixelRatio") or 1

        # Crop anh element
        x0 = int(loc["x"] * dpr); y0 = int(loc["y"] * dpr)
        w0 = int(sz["width"] * dpr); h0 = int(sz["height"] * dpr)
        # Them padding de CV2 de phat hien hon
        pad = 10
        x0c = max(0, x0-pad); y0c = max(0, y0-pad)
        x1c = min(img_pil.width, x0+w0+pad)
        y1c = min(img_pil.height, y0+h0+pad)

        crop_pil = img_pil.crop((x0c, y0c, x1c, y1c))
        crop_bgr = cv2.cvtColor(np.array(crop_pil), cv2.COLOR_RGB2BGR)

        # CV2 phat hien vung dap an
        regions = detect_answer_regions(crop_bgr)

        if not regions:
            print(f"    [CV2] Khong phat hien vung dap an, dung fallback")
            return None

        print(f"    [CV2] Phat hien {len(regions)} vung: {[r.label for r in regions]}")

        # Tim vung tuong ung voi answer_letter
        target = None
        for reg in regions:
            if reg.label.upper() == answer_letter.upper():
                target = reg; break
        if target is None and regions:
            target = regions[0]  # Fallback: chon vung dau tien

        # Highlight anh
        debug_img = highlight_regions(crop_bgr, regions, answer_letter)

        # Hien thi debug window
        show_debug_window(
            f"CV2 - Cau hoi | Dap an: {answer_letter} | Click: [{target.label}]",
            debug_img, wait_ms=1500
        )

        # Tinh toa do tuyet doi (trong trang web, khong nhan DPR)
        abs_x = int((x0c / dpr) + (target.cx / dpr))
        abs_y = int((y0c / dpr) + (target.cy / dpr))
        return abs_x, abs_y

    except Exception as e:
        print(f"    [CV2] Loi: {e}")
        return None

def cv2_highlight_fullpage(drv, answers: dict):
    """
    Chup anh trang hien tai, highlight tat ca cac vi tri se click,
    hien thi tong quan truoc khi bat dau click.
    """
    if not SHOW_DEBUG: return
    try:
        png     = drv.get_screenshot_as_png()
        img_bgr = png_to_cv2(png)
        h, w    = img_bgr.shape[:2]

        # Ve tieu de tong quan
        overlay_img = img_bgr.copy()
        cv2.rectangle(overlay_img, (0, 0), (w, 50), (0, 60, 0), -1)
        cv2.putText(overlay_img,
                    f"AZOTA v5.0 - CV2 Mode | {len(answers)} cau | Ten: {Name}",
                    (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        show_debug_window("Tong quan trang", overlay_img, wait_ms=2000)
    except Exception as e:
        print(f"  [CV2] fullpage loi: {e}")

# ═══════════════════════════════════════════════════════════════
# COMPRESS ANH + CACHE
# ═══════════════════════════════════════════════════════════════
IMG_MAX_W = 720
IMG_Q     = 75
_cache: dict = {}

def compress(img_bytes: bytes) -> tuple[bytes, str]:
    img = Image.open(BytesIO(img_bytes))
    if img.width > IMG_MAX_W:
        img = img.resize((IMG_MAX_W, int(img.height * IMG_MAX_W / img.width)), Image.LANCZOS)
    if img.mode in ("RGBA","P"): img = img.convert("RGB")
    buf = BytesIO(); img.save(buf, "JPEG", quality=IMG_Q, optimize=True)
    data = buf.getvalue()
    return data, hashlib.md5(data).hexdigest()

# ═══════════════════════════════════════════════════════════════
# MULTI-PROVIDER AI
# ═══════════════════════════════════════════════════════════════
PROMPT_READ = (
    "Bai trac nghiem. Tra loi cac cau hoi trong anh:\n"
    "Format: Cau N: X (X=A/B/C/D hoac A,C hoac DUNG/SAI hoac tu/so)\n"
    "Neu khong co cau hoi: 'NONE'\nChi viet format tren."
)
PROMPT_HINT = "Bai trac nghiem (tiep cau {prev}). Format: Cau N: X. Neu khong moi: NONE"

def _call_groq(k, b, p):
    from groq import Groq
    r = Groq(api_key=k).chat.completions.create(
        model="llama-3.2-11b-vision-preview",
        messages=[{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{base64.b64encode(b).decode()}"}},
            {"type":"text","text":p}
        ]}], max_tokens=300)
    return r.choices[0].message.content.strip()

def _call_gemini(k, b, p):
    from google import genai; from google.genai import types
    r = genai.Client(api_key=k).models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=[types.Part.from_bytes(data=b, mime_type="image/jpeg"), types.Part.from_text(text=p)])
    return r.text.strip()

def _call_mistral(k, b, p):
    from mistralai import Mistral
    r = Mistral(api_key=k).chat.complete(
        model="pixtral-12b-latest",
        messages=[{"role":"user","content":[
            {"type":"image_url","image_url":f"data:image/jpeg;base64,{base64.b64encode(b).decode()}"},
            {"type":"text","text":p}]}])
    return r.choices[0].message.content.strip()

def _call_openai(k, b, p):
    from openai import OpenAI
    r = OpenAI(api_key=k).chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{base64.b64encode(b).decode()}","detail":"low"}},
            {"type":"text","text":p}]}], max_tokens=300)
    return r.choices[0].message.content.strip()

def _call_claude(k, b, p):
    import anthropic
    r = anthropic.Anthropic(api_key=k).messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=300,
        messages=[{"role":"user","content":[
            {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":base64.b64encode(b).decode()}},
            {"type":"text","text":p}]}])
    return r.content[0].text.strip()

PROVIDERS = []
if GROQ_KEYS:    PROVIDERS.append(("Groq",    GROQ_KEYS,    _call_groq,    ["rate_limit","429","quota"]))
if GEMINI_KEYS:  PROVIDERS.append(("Gemini",  GEMINI_KEYS,  _call_gemini,  ["429","RESOURCE_EXHAUSTED"]))
if MISTRAL_KEYS: PROVIDERS.append(("Mistral", MISTRAL_KEYS, _call_mistral, ["429","quota","rate"]))
if OPENAI_KEYS:  PROVIDERS.append(("OpenAI",  OPENAI_KEYS,  _call_openai,  ["429","rate_limit"]))
if CLAUDE_KEYS:  PROVIDERS.append(("Claude",  CLAUDE_KEYS,  _call_claude,  ["overloaded","529","429"]))

_pi = 0; _ki = 0  # provider_idx, key_idx

def _next_prov():
    global _pi, _ki
    name, keys, _, _ = PROVIDERS[_pi]
    if _ki+1 < len(keys): _ki+=1; print(f"  [→key] {name}#{_ki+1}"); return True
    if _pi+1 < len(PROVIDERS): _pi+=1; _ki=0; print(f"  [→AI] {PROVIDERS[_pi][0]}"); return True
    extra = input("  Het key! Nhap them (prov:key): ").strip()
    if ":" in extra:
        pn,pk = extra.split(":",1)
        for i,(n,ks,f,s) in enumerate(PROVIDERS):
            if pn.lower() in n.lower(): ks.append(pk.strip()); _pi=i; _ki=len(ks)-1; return True
    return False

def _wait(e):
    m = re.search(r"retry.*?([\d.]+)s", e, re.I)
    return min(float(m.group(1))+2, 65) if m else 15

def _daily(e): return any(x in e for x in ["PerDay","per_day","daily","GenerateRequestsPerDay"])

def ask_ai(img_bytes: bytes, prompt: str) -> str:
    comp, h = compress(img_bytes)
    ck = h + hashlib.md5(prompt.encode()).hexdigest()[:6]
    if ck in _cache: return _cache[ck]

    for _ in range(20):
        if _pi >= len(PROVIDERS): return ""
        name, keys, fn, sigs = PROVIDERS[_pi]
        try:
            r = fn(keys[_ki], comp, prompt)
            _cache[ck] = r
            if len(_cache) > 50: del _cache[next(iter(_cache))]
            return r
        except RuntimeError as e:
            print(f"  [{name}] {e}"); _next_prov()
        except Exception as e:
            err = str(e)
            if any(s.lower() in err.lower() for s in sigs):
                if _daily(err): print(f"  [{name}] het quota ngay"); _next_prov()
                else: w=_wait(err); print(f"  [{name}] cho {w:.0f}s..."); time.sleep(w)
            else: print(f"  [{name}] loi: {err[:60]}"); _next_prov()
    return ""

# ═══════════════════════════════════════════════════════════════
# SELENIUM HELPERS
# ═══════════════════════════════════════════════════════════════
def make_driver():
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    drv = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    drv.execute_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    return drv

def gy(drv): return drv.execute_script("return window.scrollY")
def ph(drv): return drv.execute_script("return document.body.scrollHeight")
def vh(drv): return drv.execute_script("return window.innerHeight")

def scy(drv, y, s=True):
    drv.execute_script(f"window.scrollTo({{top:{y},behavior:'{'smooth' if s else 'instant'}'}});")
    time.sleep(0.35 if s else 0.1)

def sct(drv): scy(drv, 0); time.sleep(0.2)

def safe_click(drv, el):
    drv.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", el)
    time.sleep(0.2); drv.execute_script("window.scrollBy(0,-80);"); time.sleep(0.1)
    try: el.click()
    except: drv.execute_script("arguments[0].click();", el)

def shot(drv): return drv.get_screenshot_as_png()

# ═══════════════════════════════════════════════════════════════
# XU LY TEN THI SINH
# ═══════════════════════════════════════════════════════════════
def setup_name(drv, name):
    print("\n[2] Xu ly ten thi sinh...")
    time.sleep(1.5)
    ok = _sel(drv,name) or _lst(drv,name) or _inp3(drv,name) or _vis_n(drv,name)
    if ok: _confirm(drv)

def _sel(drv, name):
    for el in drv.find_elements(By.TAG_NAME,"select"):
        try:
            s = SeleniumSelect(el)
            for o in s.options:
                if name.lower() in o.text.lower():
                    s.select_by_visible_text(o.text); print(f"  [select] {o.text}"); return True
        except: pass
    return False

def _lst(drv, name):
    for el in drv.find_elements(By.XPATH, f"//*[contains(text(),'{name}')]"):
        if el.is_displayed() and el.tag_name in ("li","div","span","td","p","label","a","button"):
            safe_click(drv, el); print(f"  [list] {el.text.strip()[:30]}"); return True
    return False

def _inp3(drv, name):
    css = ["input[placeholder*='Ten']","input[placeholder*='ten']",
           "input[placeholder*='name']","input[placeholder*='Thi']"]
    els = []
    for c in css:
        els = drv.find_elements(By.CSS_SELECTOR, c)
        if els: break
    if not els:
        els = [e for e in drv.find_elements(By.CSS_SELECTOR,"input[type='text']") if e.is_displayed()]
    for el in els:
        try:
            safe_click(drv,el); el.clear(); time.sleep(0.15); el.send_keys(name); time.sleep(1.0)
            for it in drv.find_elements(By.CSS_SELECTOR,"[role='option'],.dropdown-item,li[class*='option']"):
                if name.lower() in it.text.lower() and it.is_displayed():
                    safe_click(drv,it); print(f"  [auto] {it.text.strip()}"); return True
            print(f"  [input] {name}"); return True
        except: pass
    return False

def _vis_n(drv, name):
    resp = ask_ai(shot(drv), f"Tim o nhap/chon ten '{name}'. JSON: {{\"x\":100,\"y\":200}}")
    try:
        d = json.loads(re.search(r'\{[^}]+\}',resp).group())
        dpr = drv.execute_script("return window.devicePixelRatio") or 1
        x,y = int(d["x"]/dpr), int(d["y"]/dpr)
        rel = y - gy(drv)
        ActionChains(drv).move_by_offset(x,rel).click().perform()
        ActionChains(drv).move_by_offset(-x,-rel).perform()
        time.sleep(0.3); ActionChains(drv).send_keys(name).perform()
        print(f"  [vision] ({x},{y})"); return True
    except: return False

def _confirm(drv):
    time.sleep(0.8)
    for kw in ["Xác nhận","Tiếp tục","Đồng ý","OK","Bắt đầu","Làm bài","Vào thi","Submit","Confirm","Next"]:
        for el in drv.find_elements(By.XPATH,
                f"//button[contains(.,'{kw}')]|//a[contains(.,'{kw}')]|//input[@value='{kw}']"):
            if el.is_displayed() and el.is_enabled():
                safe_click(drv,el); print(f"  [confirm] {el.text.strip() or kw}"); time.sleep(1.0); return True
    try:
        f = drv.switch_to.active_element
        if f.tag_name in ("input","textarea"): f.send_keys(Keys.RETURN); time.sleep(1.0); return True
    except: pass
    resp = ask_ai(shot(drv), "Nut xac nhan sau khi nhap ten? JSON:{\"x\":0,\"y\":0} hoac NONE")
    if "NONE" not in resp.upper():
        try:
            d = json.loads(re.search(r'\{[^}]+\}',resp).group())
            dpr = drv.execute_script("return window.devicePixelRatio") or 1
            x,y = int(d["x"]/dpr), int(d["y"]/dpr)
            rel = y-gy(drv)
            ActionChains(drv).move_by_offset(x,rel).click().perform()
            ActionChains(drv).move_by_offset(-x,-rel).perform()
            print(f"  [confirm-vis] ({x},{y})"); time.sleep(1.0); return True
        except: pass
    return False

# ═══════════════════════════════════════════════════════════════
# BAT DAU LAM BAI
# ═══════════════════════════════════════════════════════════════
def click_start(drv):
    for kw in ["Bắt đầu","Làm bài","Vào thi","Start","Bat dau"]:
        for el in drv.find_elements(By.XPATH,f"//button[contains(.,'{kw}')]|//a[contains(.,'{kw}')]"):
            if el.is_displayed(): safe_click(drv,el); print(f"  [start] {el.text.strip()}"); return True
    return False

# ═══════════════════════════════════════════════════════════════
# SCROLL + DOC CAU HOI
# ═══════════════════════════════════════════════════════════════
def _parse(raw):
    out = {}
    for line in raw.splitlines():
        m = re.match(r"(?:[Cc]au\s*)?(\d+)\s*[:\.\-]\s*(.+)", line.strip())
        if m:
            n, a = int(m.group(1)), m.group(2).strip()
            if a and a != "?": out[n] = a
    return out

def scroll_and_read(drv) -> dict:
    print("\n[4] === SCROLL + CV2 + AI DOC CAU HOI ===")
    prev_h2 = 0
    for _ in range(20):
        h2 = ph(drv)
        if h2 == prev_h2: break
        prev_h2 = h2; drv.execute_script(f"window.scrollTo(0,{h2});"); time.sleep(0.4)
    sct(drv); time.sleep(0.6)

    page_h = ph(drv); view_h = vh(drv)
    step   = int(view_h * 0.65)
    poses  = list(range(0, page_h, step))
    if page_h not in poses: poses.append(page_h)
    print(f"  {page_h}px | {len(poses)} buoc | step={step}px")

    all_ans = {}; seen = set(); prev_vhash = ""; max_cau = 0

    for idx, pos in enumerate(poses):
        scy(drv, pos); time.sleep(0.4)
        png = shot(drv)

        # Hash viewport de skip neu khong doi
        vhash = hashlib.md5(png[:4096]).hexdigest()
        if vhash == prev_vhash:
            print(f"  [{idx+1}/{len(poses)}] skip (khong doi)"); continue
        prev_vhash = vhash

        pct = int((idx+1)/len(poses)*100)
        print(f"  [{idx+1}/{len(poses)}] Y={gy(drv)}px {pct}%...", end=" ", flush=True)

        # CV2: phat hien cau hoi o viewport nay (chi de thong bao so luong)
        cv_img = png_to_cv2(png)
        cv_regions = detect_answer_regions(cv_img)
        if cv_regions and SHOW_DEBUG:
            # Highlight tat ca vung phat hien (chua biet dap an nao)
            dbg = highlight_regions(cv_img, cv_regions, selected="")
            show_debug_window(f"CV2 scan [{idx+1}/{len(poses)}]", dbg, wait_ms=600)

        # AI doc cau hoi + dap an
        prompt = PROMPT_READ if not max_cau else PROMPT_HINT.format(prev=max_cau)
        raw    = ask_ai(png, prompt)

        if not raw or "NONE" in raw.upper():
            print("(trong)"); time.sleep(0.8); continue

        batch = _parse(raw)
        new   = {k:v for k,v in batch.items() if k not in seen}

        if new:
            print(f"(+{len(new)} cau)")
            for k,v in sorted(new.items()):
                print(f"    Cau {k:>3}: {v}")
                all_ans[k]=v; seen.add(k)
                if k > max_cau: max_cau = k
        else:
            print("(khong moi)")
        time.sleep(1.0)

    sct(drv); time.sleep(0.4)
    print(f"\n  XONG: {len(all_ans)} cau | {PROVIDERS[_pi][0]} key#{_ki+1}")
    return all_ans

# ═══════════════════════════════════════════════════════════════
# CV2 CLICK DAP AN
# ═══════════════════════════════════════════════════════════════
def find_q_els(drv):
    return drv.execute_script("""
        var f=[],all=document.querySelectorAll('div,li,section,article');
        for(var i=0;i<all.length;i++){
            var e=all[i],r=e.querySelectorAll('input[type="radio"]'),
                c=e.querySelectorAll('input[type="checkbox"]'),
                t=e.querySelectorAll('input[type="text"],textarea');
            if(r.length>=2||c.length>=2||t.length>=1){
                var s=false;
                for(var j=0;j<f.length;j++){if(f[j].contains(e)){s=true;break;}}
                if(!s)f.push(e);
            }
        }
        return f;
    """) or []

def click_ans_cv2(drv, q_el, answer: str, num: int):
    """
    Thu CV2 truoc, fallback sang DOM neu CV2 that bai.
    """
    ans = answer.strip().upper()
    m   = re.search(r"[A-D]", ans)
    letter = m.group() if m else ""

    # ── Thu CV2 ─────────────────────────────────────────────
    if letter:
        coords = cv2_find_and_highlight(drv, q_el, letter)
        if coords:
            abs_x, abs_y = coords
            # Scroll den vi tri
            drv.execute_script(f"window.scrollTo(0, {max(0, abs_y - 200)});")
            time.sleep(0.3)
            rel_y = abs_y - gy(drv)
            try:
                ActionChains(drv).move_by_offset(abs_x, rel_y).click().perform()
                ActionChains(drv).move_by_offset(-abs_x, -rel_y).perform()
                print(f"  ✓ {num}: [{letter}] via CV2 ({abs_x},{abs_y})")
                return
            except Exception as e:
                print(f"    [CV2 click loi] {e} -> fallback DOM")

    # ── Fallback: DOM click ───────────────────────────────────
    radios  = q_el.find_elements(By.CSS_SELECTOR,"input[type='radio']")
    checks  = q_el.find_elements(By.CSS_SELECTOR,"input[type='checkbox']")
    texts   = q_el.find_elements(By.CSS_SELECTOR,"input[type='text'],textarea")
    labels  = q_el.find_elements(By.CSS_SELECTOR,"label")

    if radios:
        idx = ord(letter)-65 if letter else 0
        idx = min(idx, len(radios)-1)
        safe_click(drv, labels[idx] if labels and idx<len(labels) else radios[idx])
        print(f"  ✓ {num}: [{letter or 'A'}] DOM-radio")

    elif checks:
        for ch in re.findall(r"[A-D]", ans):
            i = ord(ch)-65
            if i < len(checks):
                safe_click(drv, labels[i] if labels and i<len(labels) else checks[i])
                time.sleep(0.15)
        print(f"  ✓ {num}: [{ans}] DOM-checkbox")

    elif texts:
        b = texts[0]; safe_click(drv,b); b.clear(); b.send_keys(answer)
        print(f"  ✓ {num}: '{answer[:30]}' DOM-text")

    else:
        is_t = any(w in ans for w in ["DUNG","ĐÚNG","TRUE"])
        for btn in q_el.find_elements(By.CSS_SELECTOR,"button,label,[role='button']"):
            tgt = ["ĐÚNG","DUNG","TRUE"] if is_t else ["SAI","FALSE"]
            if any(t in btn.text.upper() for t in tgt) and btn.is_displayed():
                safe_click(drv,btn); print(f"  ✓ {num}: [{btn.text.strip()}]"); return
        print(f"  ✗ {num}: khong click duoc")

def apply_answers(drv, answers: dict):
    print("\n[5] === CV2 + CLICK DAP AN ===")
    sct(drv); time.sleep(0.6)

    # Hien thi tong quan trang truoc khi bat dau
    cv2_highlight_fullpage(drv, answers)

    q_els = find_q_els(drv)
    print(f"  Tim thay {len(q_els)} element cau hoi\n")

    applied = 0
    for i, q_el in enumerate(q_els):
        n   = i + 1
        ans = answers.get(n)
        if not ans: print(f"  - Cau {n}: bo qua"); continue
        try:
            drv.execute_script("arguments[0].scrollIntoView({block:'center'});", q_el)
            time.sleep(0.3); drv.execute_script("window.scrollBy(0,-100);"); time.sleep(0.15)
            click_ans_cv2(drv, q_el, ans, n)
            applied += 1; time.sleep(0.3)
        except StaleElementReferenceException:
            q_els = find_q_els(drv)
            if i < len(q_els):
                try: click_ans_cv2(drv, q_els[i], ans, n); applied += 1
                except Exception as e2: print(f"  ✗ {n}: {e2}")
        except Exception as e:
            print(f"  ✗ {n}: {e}")

    print(f"\n  Xong: {applied}/{len(q_els)} cau")
    cv2.destroyAllWindows()

# ═══════════════════════════════════════════════════════════════
# NOP BAI
# ═══════════════════════════════════════════════════════════════
def submit(drv):
    print("\n[6] Nop bai...")
    drv.execute_script("window.scrollTo(0,document.body.scrollHeight);"); time.sleep(0.8)
    for kw in ["Nộp bài","Submit","Hoàn thành","Kết thúc"]:
        for el in drv.find_elements(By.XPATH,f"//button[contains(.,'{kw}')]|//a[contains(.,'{kw}')]"):
            if el.is_displayed():
                safe_click(drv,el); print(f"  [nop] {el.text.strip()}"); time.sleep(2.5)
                for ck in ["Xác nhận","Đồng ý","OK","Có"]:
                    for c in drv.find_elements(By.XPATH,f"//button[contains(.,'{ck}')]"):
                        if c.is_displayed(): safe_click(drv,c); return True
                return True
    print("  Khong tim thay nut nop -> nop thu cong!"); return False

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def run():
    drv = make_driver()
    try:
        print("\n[1] Mo link..."); drv.get(link_homework); time.sleep(3)
        setup_name(drv, Name); time.sleep(1.5)
        print("\n[3] Bat dau lam bai...")
        if click_start(drv): time.sleep(2.5)

        answers = scroll_and_read(drv)
        if not answers: print("[!] Khong doc duoc!"); input("Enter..."); return

        print(f"\n=== {len(answers)} DAP AN ===")
        for k in sorted(answers): print(f"  Cau {k:>3}: {answers[k]}")

        apply_answers(drv, answers)
        submit(drv)

        notification.notify(title="Azota v5.0 Xong!", message=f"{len(answers)} cau | {Name}", timeout=10)
        print(f"\nHOAN THANH! {len(answers)} cau.")
        input("\nEnter de dong...")
    except Exception as e:
        import traceback; traceback.print_exc()
        notification.notify(title="Loi!", message=str(e)[:100], timeout=10)
        input("Enter de thoat...")
    finally:
        cv2.destroyAllWindows(); drv.quit()

if __name__ == "__main__":
    run()