# ===========================================================================
#  _   _  ___  __  __ _______        _____  ____  _  __
# | | | |/ _ \|  \/  | ____\ \      / / _ \|  _ \| |/ /
# | |_| | | | | |\/| |  _|  \ \ /\ / / | | | |_) | ' /
# |  _  | |_| | |  | | |___  \ V  V /| |_| |  _ <| . \
# |_| |_|\___/|_|  |_|_____|  \_/\_/  \___/|_| \_\_|\_\
#                   -- Tool by Nguyen Quoc Dat --  v4.0
#
# TIET KIEM TOKEN:
#   - Resize anh truoc khi gui AI (720px wide, grayscale neu co the)
#   - Prompt ngan gon toi da
#   - Cache: neu cau hoi giong anh truoc -> dung lai ket qua
#   - Chi gui AI khi thay cau hoi moi xuat hien
#   - Overlap thong minh: phat hien trung lap bang hash anh
#
# AI PROVIDERS (tu dong doi khi het quota):
#   1. Gemini  (Google)  - Free: 1500/ngay
#   2. Groq    (Meta)    - Free: 14400/ngay (NHANH NHAT)
#   3. Mistral (EU)      - Free: 1000/ngay
#   4. OpenAI  (GPT)     - Tra phi
#   5. Claude  (Anthropic)- Tra phi
#
# CAI DAT:
#   pip install selenium webdriver-manager google-genai pillow plyer
#   pip install openai groq mistralai anthropic   (tuy chon)
# ===========================================================================

import time, re, os, sys, json, hashlib, tempfile, shutil, base64
import urllib.request
from io import BytesIO
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
TOOL_VERSION = "4.0.0"
URL_REMOTE   = ""   # Dan link raw GitHub cua ban vao day
SKIP_UPDATE  = os.getenv("AZOTA_SKIP_UPDATE", "0") == "1"

def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""): h.update(chunk)
    return h.hexdigest()

def check_and_update():
    if SKIP_UPDATE or not URL_REMOTE or "YOUR_USERNAME" in URL_REMOTE:
        if URL_REMOTE and "YOUR_USERNAME" in URL_REMOTE:
            print("[Update] Chua cau hinh URL_REMOTE -> bo qua.\n")
        return
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
                  -- Tool by Nguyen Quoc Dat --  v1.0
""")
link_homework = input("Nhap link bai tap : ").strip()
Name          = input("Nhap ten thi sinh : ").strip()

print("""
=== NHAP API KEY ===
Nhap KEY cua cac AI ban co (bo trong neu khong co, Enter de qua).
Tool tu dong doi AI khi het quota.

  Provider   | Free/ngay | Model dung
  -----------|-----------|---------------------------
  Gemini     | 1500 req  | gemini-2.0-flash-lite
  Groq       | 14400 req | llama-3.2-11b-vision (NHANH)
  Mistral    | 1000 req  | pixtral-12b-latest
  OpenAI     | Tra phi   | gpt-4o-mini
  Claude     | Tra phi   | claude-haiku-4-5-20251001
""")

def _inp(label):
    v = input(f"  {label}: ").strip()
    return v if v else None

_gemini_raw  = _inp("Gemini key(s) ngan cach phay (AIza...)")
_groq_raw    = _inp("Groq key(s)   ngan cach phay (gsk_...)")
_mistral_raw = _inp("Mistral key(s) ngan cach phay")
_openai_raw  = _inp("OpenAI key(s)  ngan cach phay (sk-...)")
_claude_raw  = _inp("Claude key(s)  ngan cach phay (sk-ant-...)")

def _parse_keys(raw): 
    return [k.strip() for k in raw.split(",") if k.strip()] if raw else []

GEMINI_KEYS  = _parse_keys(_gemini_raw)
GROQ_KEYS    = _parse_keys(_groq_raw)
MISTRAL_KEYS = _parse_keys(_mistral_raw)
OPENAI_KEYS  = _parse_keys(_openai_raw)
CLAUDE_KEYS  = _parse_keys(_claude_raw)

total_keys = len(GEMINI_KEYS)+len(GROQ_KEYS)+len(MISTRAL_KEYS)+len(OPENAI_KEYS)+len(CLAUDE_KEYS)
if total_keys == 0:
    print("Chua nhap key nao!"); sys.exit(1)

print(f"\n  Tong: {total_keys} key | Gemini:{len(GEMINI_KEYS)} Groq:{len(GROQ_KEYS)} "
      f"Mistral:{len(MISTRAL_KEYS)} OpenAI:{len(OPENAI_KEYS)} Claude:{len(CLAUDE_KEYS)}\n")

notification.notify(
    title="Azota v4.0",
    message=f"Ten: {Name} | {total_keys} AI key | Dang chay...",
    timeout=4,
)

# ═══════════════════════════════════════════════════════════════
# TIET KIEM TOKEN — XU LY ANH TRUOC KHI GUI AI
# ═══════════════════════════════════════════════════════════════
IMG_MAX_WIDTH  = 720   # Resize ve 720px wide (du de doc text)
IMG_QUALITY    = 75    # JPEG quality (tiet kiem ~60% so voi PNG)
_img_cache: dict = {}  # hash_anh -> ket_qua (tranh gui AI 2 lan)

def _compress_image(img_bytes: bytes) -> tuple[bytes, str]:
    """
    Resize + compress anh, tra ve (bytes_nho_hon, hash).
    Giam ~70% kich co anh -> tiet kiem tuong duong token.
    """
    img = Image.open(BytesIO(img_bytes))
    # Resize neu qua rong
    if img.width > IMG_MAX_WIDTH:
        ratio = IMG_MAX_WIDTH / img.width
        new_h = int(img.height * ratio)
        img   = img.resize((IMG_MAX_WIDTH, new_h), Image.LANCZOS)
    # Convert sang RGB (bo alpha channel neu co)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    # Luu JPEG (nho hon PNG ~3-5x)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=IMG_QUALITY, optimize=True)
    compressed = buf.getvalue()
    img_hash   = hashlib.md5(compressed).hexdigest()
    return compressed, img_hash

def _check_cache(img_hash: str) -> str | None:
    return _img_cache.get(img_hash)

def _set_cache(img_hash: str, result: str):
    _img_cache[img_hash] = result
    # Giu toi da 50 entry
    if len(_img_cache) > 50:
        oldest = next(iter(_img_cache))
        del _img_cache[oldest]

# ═══════════════════════════════════════════════════════════════
# PROMPT NGAN GON TOI DA
# (it chu = it token = tiet kiem quota)
# ═══════════════════════════════════════════════════════════════
PROMPT_READ = (
    "Bai trac nghiem. Tra loi cac cau hoi trong anh:\n"
    "Format: Cau N: X (X=A/B/C/D hoac A,C hoac DUNG/SAI hoac tu/so)\n"
    "Neu khong co cau hoi: 'NONE'\n"
    "Chi viet format tren, khong giai thich."
)

PROMPT_READ_HINT = (
    "Bai trac nghiem (tiep theo cau {prev}).\n"
    "Format: Cau N: X\nNeu khong co cau moi: 'NONE'\nChi format tren."
)

# ═══════════════════════════════════════════════════════════════
# MULTI-PROVIDER AI ENGINE
# Thu tu uu tien: Groq (nhanh + nhieu quota) -> Gemini -> Mistral -> OpenAI -> Claude
# ═══════════════════════════════════════════════════════════════

# --- Groq (llama vision, MIEN PHI 14400/ngay, rat nhanh) ---
def _call_groq(key: str, img_bytes: bytes, prompt: str) -> str:
    try:
        from groq import Groq
        b64 = base64.b64encode(img_bytes).decode()
        c   = Groq(api_key=key)
        r   = c.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{"role":"user","content":[
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}},
                {"type":"text","text":prompt}
            ]}],
            max_tokens=300,
        )
        return r.choices[0].message.content.strip()
    except ImportError:
        raise RuntimeError("Chua cai groq: pip install groq")

# --- Gemini (google-genai, MIEN PHI 1500/ngay) ---
def _call_gemini(key: str, img_bytes: bytes, prompt: str) -> str:
    from google import genai
    from google.genai import types
    c = genai.Client(api_key=key)
    r = c.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=[
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
            types.Part.from_text(text=prompt),
        ],
    )
    return r.text.strip()

# --- Mistral (pixtral, MIEN PHI 1000/ngay) ---
def _call_mistral(key: str, img_bytes: bytes, prompt: str) -> str:
    try:
        from mistralai import Mistral
        b64 = base64.b64encode(img_bytes).decode()
        c   = Mistral(api_key=key)
        r   = c.chat.complete(
            model="pixtral-12b-latest",
            messages=[{"role":"user","content":[
                {"type":"image_url","image_url":f"data:image/jpeg;base64,{b64}"},
                {"type":"text","text":prompt}
            ]}],
        )
        return r.choices[0].message.content.strip()
    except ImportError:
        raise RuntimeError("Chua cai mistralai: pip install mistralai")

# --- OpenAI (gpt-4o-mini, TRA PHI nhung re) ---
def _call_openai(key: str, img_bytes: bytes, prompt: str) -> str:
    try:
        from openai import OpenAI
        b64 = base64.b64encode(img_bytes).decode()
        c   = OpenAI(api_key=key)
        r   = c.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":[
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}","detail":"low"}},
                {"type":"text","text":prompt}
            ]}],
            max_tokens=300,
        )
        return r.choices[0].message.content.strip()
    except ImportError:
        raise RuntimeError("Chua cai openai: pip install openai")

# --- Claude (haiku, TRA PHI nhung re nhat cua Anthropic) ---
def _call_claude(key: str, img_bytes: bytes, prompt: str) -> str:
    try:
        import anthropic
        b64      = base64.b64encode(img_bytes).decode()
        c        = anthropic.Anthropic(api_key=key)
        r        = c.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role":"user","content":[
                {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":b64}},
                {"type":"text","text":prompt}
            ]}],
        )
        return r.content[0].text.strip()
    except ImportError:
        raise RuntimeError("Chua cai anthropic: pip install anthropic")

# --- Bang provider ---
#   (ten, danh_sach_key, ham_goi, nhung_loi_het_quota)
PROVIDERS = []
if GROQ_KEYS:    PROVIDERS.append(("Groq",    GROQ_KEYS,    _call_groq,    ["rate_limit_exceeded","429","quota"]))
if GEMINI_KEYS:  PROVIDERS.append(("Gemini",  GEMINI_KEYS,  _call_gemini,  ["429","RESOURCE_EXHAUSTED"]))
if MISTRAL_KEYS: PROVIDERS.append(("Mistral", MISTRAL_KEYS, _call_mistral, ["429","quota","rate"]))
if OPENAI_KEYS:  PROVIDERS.append(("OpenAI",  OPENAI_KEYS,  _call_openai,  ["429","quota","rate_limit"]))
if CLAUDE_KEYS:  PROVIDERS.append(("Claude",  CLAUDE_KEYS,  _call_claude,  ["overloaded","rate","529","429"]))

# Trang thai hien tai
_prov_idx = 0   # provider dang dung
_key_idx  = 0   # key trong provider do

def _wait_from_err(err: str) -> float:
    for pat in [r"retry.*?in.*?([\d.]+)\s*s", r"Please retry in ([\d.]+)s"]:
        m = re.search(pat, err, re.IGNORECASE)
        if m: return min(float(m.group(1)) + 2, 65)
    return 15

def _is_quota_err(err: str, quota_signals: list) -> bool:
    el = err.lower()
    return any(s.lower() in el for s in quota_signals)

def _is_daily_err(err: str) -> bool:
    return any(x in err for x in ["PerDay","per_day","daily","GenerateRequestsPerDay","per-day"])

def _next_provider() -> bool:
    """Doi sang key tiep theo hoac provider tiep theo."""
    global _prov_idx, _key_idx
    name, keys, _, _ = PROVIDERS[_prov_idx]

    # Thu key khac trong cung provider
    next_ki = _key_idx + 1
    if next_ki < len(keys):
        _key_idx = next_ki
        print(f"  [→KEY] {name} key #{next_ki+1}")
        return True

    # Thu provider khac
    next_pi = _prov_idx + 1
    if next_pi < len(PROVIDERS):
        _prov_idx = next_pi
        _key_idx  = 0
        print(f"  [→AI] Chuyen sang {PROVIDERS[next_pi][0]}")
        return True

    # Het tat ca -> hoi user
    print("\n  [!!!] HET TAT CA AI KEY!")
    print("  Lay them key tai: aistudio.google.com (Gemini) / console.groq.com (Groq)")
    extra = input("  Nhap key moi (provider:key, vd 'gemini:AIza...'): ").strip()
    if ":" in extra:
        prov, key = extra.split(":", 1)
        prov = prov.strip().lower(); key = key.strip()
        for i, (pname, pkeys, pfn, psig) in enumerate(PROVIDERS):
            if prov in pname.lower():
                pkeys.append(key)
                _prov_idx = i; _key_idx = len(pkeys)-1
                print(f"  Da them key vao {pname}")
                return True
    return False

def ask_ai(img_bytes: bytes, prompt: str) -> str:
    """
    Goi AI voi anh da compress + cache.
    Tu dong doi provider/key khi bi rate limit.
    """
    # Compress anh
    compressed, img_hash = _compress_image(img_bytes)

    # Kiem tra cache
    cache_key = img_hash + hashlib.md5(prompt.encode()).hexdigest()[:8]
    cached = _check_cache(cache_key)
    if cached is not None:
        print("  [cache] Dung ket qua cache")
        return cached

    for attempt in range(20):
        if _prov_idx >= len(PROVIDERS):
            return ""
        name, keys, fn, quota_sigs = PROVIDERS[_prov_idx]
        key = keys[_key_idx]

        try:
            result = fn(key, compressed, prompt)
            _set_cache(cache_key, result)
            return result

        except RuntimeError as e:
            # Chua cai thu vien -> doi provider
            print(f"  [{name}] {e} -> doi provider")
            if not _next_provider(): return ""

        except Exception as e:
            err = str(e)
            if _is_quota_err(err, quota_sigs):
                if _is_daily_err(err):
                    print(f"  [{name}] Het quota NGAY key#{_key_idx+1} -> doi")
                    if not _next_provider(): return ""
                else:
                    w = _wait_from_err(err)
                    print(f"  [{name}] Rate limit -> cho {w:.0f}s (lan {attempt+1})...")
                    time.sleep(w)
            else:
                print(f"  [{name}] Loi la: {err[:80]}")
                # Loi khac (network, etc) -> doi key/provider
                if not _next_provider(): return ""
    return ""

# ═══════════════════════════════════════════════════════════════
# SELENIUM
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

def get_scroll_y(drv): return drv.execute_script("return window.scrollY")
def get_page_h(drv):   return drv.execute_script("return document.body.scrollHeight")
def get_view_h(drv):   return drv.execute_script("return window.innerHeight")

def scroll_to(drv, y, smooth=True):
    b = "smooth" if smooth else "instant"
    drv.execute_script(f"window.scrollTo({{top:{y},behavior:'{b}'}});")
    time.sleep(0.4 if smooth else 0.1)

def scroll_top(drv): scroll_to(drv, 0); time.sleep(0.2)

def safe_click(drv, el):
    drv.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", el)
    time.sleep(0.25)
    drv.execute_script("window.scrollBy(0,-80);"); time.sleep(0.1)
    try: el.click()
    except: drv.execute_script("arguments[0].click();", el)

def shot(drv) -> bytes: return drv.get_screenshot_as_png()

def shot_el(drv, el) -> bytes:
    loc = el.location_once_scrolled_into_view; sz = el.size
    png = drv.get_screenshot_as_png()
    img = Image.open(BytesIO(png))
    dpr = drv.execute_script("return window.devicePixelRatio") or 1
    x,y = int(loc["x"]*dpr), int(loc["y"]*dpr)
    w,h = int(sz["width"]*dpr), int(sz["height"]*dpr)
    buf = BytesIO(); img.crop((x,y,x+w,y+h)).save(buf,"PNG")
    return buf.getvalue()

# ═══════════════════════════════════════════════════════════════
# XU LY TEN THI SINH
# ═══════════════════════════════════════════════════════════════
def setup_name(drv, name):
    print("\n[2] Xu ly ten thi sinh...")
    time.sleep(1.5)
    ok = _sel(drv,name) or _list(drv,name) or _inp2(drv,name) or _vision_n(drv,name)
    if ok: _confirm(drv)
    else:  print("  Khong xu ly duoc ten")

def _sel(drv, name):
    for el in drv.find_elements(By.TAG_NAME,"select"):
        try:
            s = SeleniumSelect(el)
            for o in s.options:
                if name.lower() in o.text.lower():
                    s.select_by_visible_text(o.text)
                    print(f"  [select] {o.text}"); return True
        except: pass
    return False

def _list(drv, name):
    for el in drv.find_elements(By.XPATH, f"//*[contains(text(),'{name}')]"):
        if el.is_displayed() and el.tag_name in ("li","div","span","td","p","label","a","button"):
            safe_click(drv, el); print(f"  [list] {el.text.strip()[:30]}"); return True
    return False

def _inp2(drv, name):
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
            safe_click(drv, el); el.clear(); time.sleep(0.15)
            el.send_keys(name); time.sleep(1.0)
            for item in drv.find_elements(By.CSS_SELECTOR,
                    "[role='option'],.dropdown-item,li[class*='option']"):
                if name.lower() in item.text.lower() and item.is_displayed():
                    safe_click(drv, item); print(f"  [auto] {item.text.strip()}"); return True
            print(f"  [input] {name}"); return True
        except: pass
    return False

def _vision_n(drv, name):
    resp = ask_ai(shot(drv),
        f"Tim o nhap/chon ten '{name}'. JSON toa do: {{\"x\":100,\"y\":200}}")
    try:
        d   = json.loads(re.search(r'\{[^}]+\}', resp).group())
        dpr = drv.execute_script("return window.devicePixelRatio") or 1
        x,y = int(d["x"]/dpr), int(d["y"]/dpr)
        rel  = y - get_scroll_y(drv)
        ActionChains(drv).move_by_offset(x,rel).click().perform()
        ActionChains(drv).move_by_offset(-x,-rel).perform()
        time.sleep(0.3); ActionChains(drv).send_keys(name).perform()
        print(f"  [vision] ({x},{y})"); return True
    except: return False

def _confirm(drv):
    time.sleep(0.8)
    kws = ["Xác nhận","Tiếp tục","Đồng ý","OK","Bắt đầu","Làm bài",
           "Vào thi","Submit","Confirm","Next","Continue"]
    for kw in kws:
        for el in drv.find_elements(By.XPATH,
                f"//button[contains(.,'{kw}')]|//a[contains(.,'{kw}')]|//input[@value='{kw}']"):
            if el.is_displayed() and el.is_enabled():
                safe_click(drv, el); print(f"  [confirm] {el.text.strip() or kw}")
                time.sleep(1.0); return True
    # Enter fallback
    try:
        f = drv.switch_to.active_element
        if f.tag_name in ("input","textarea"):
            f.send_keys(Keys.RETURN); time.sleep(1.0); return True
    except: pass
    # Vision fallback
    resp = ask_ai(shot(drv), "Nut xac nhan/tiep tuc sau khi nhap ten o dau? JSON: {\"x\":0,\"y\":0} hoac NONE")
    if "NONE" not in resp.upper():
        try:
            d   = json.loads(re.search(r'\{[^}]+\}', resp).group())
            dpr = drv.execute_script("return window.devicePixelRatio") or 1
            x,y = int(d["x"]/dpr), int(d["y"]/dpr)
            rel  = y - get_scroll_y(drv)
            ActionChains(drv).move_by_offset(x,rel).click().perform()
            ActionChains(drv).move_by_offset(-x,-rel).perform()
            print(f"  [confirm-vision] ({x},{y})"); time.sleep(1.0); return True
        except: pass
    return False

# ═══════════════════════════════════════════════════════════════
# BAT DAU LAM BAI
# ═══════════════════════════════════════════════════════════════
def click_start(drv):
    for kw in ["Bắt đầu","Làm bài","Vào thi","Start","Bat dau","Lam bai","Vao thi"]:
        for el in drv.find_elements(By.XPATH,
                f"//button[contains(.,'{kw}')]|//a[contains(.,'{kw}')]"):
            if el.is_displayed(): safe_click(drv,el); print(f"  [start] {el.text.strip()}"); return True
    return False

# ═══════════════════════════════════════════════════════════════
# SCROLL + CHUP ANH + GEMINI DOC CAU HOI (TOKEN TIET KIEM)
# ═══════════════════════════════════════════════════════════════
def _parse_answers(raw: str) -> dict:
    """Parse ket qua Gemini tra ve thanh {cau_so: dap_an}."""
    out = {}
    for line in raw.splitlines():
        m = re.match(r"(?:[Cc]au\s*)?(\d+)\s*[:\.\-]\s*(.+)", line.strip())
        if m:
            num = int(m.group(1))
            ans = m.group(2).strip()
            if ans and ans != "?": out[num] = ans
    return out

def _viewport_hash(drv) -> str:
    """Hash nhanh viewport hien tai de phat hien thay doi."""
    png = shot(drv)
    return hashlib.md5(png[:4096]).hexdigest()  # Chi hash 4KB dau

def scroll_and_read(drv) -> dict:
    """
    Scroll trang + chup anh + gui AI doc cau hoi.
    Tiet kiem token:
      - Neu viewport khong thay doi (hash giong) -> bo qua
      - Anh compress ve 720px JPEG truoc khi gui
      - Cache ket qua neu anh giong nhau
    """
    print("\n[4] === SCROLL + DOC CAU HOI ===")

    # Trigger lazy-load
    print("  Trigger lazy-load...")
    prev_h = 0
    for _ in range(20):
        h = get_page_h(drv)
        if h == prev_h: break
        prev_h = h
        drv.execute_script(f"window.scrollTo(0,{h});"); time.sleep(0.4)
    scroll_top(drv); time.sleep(0.6)

    page_h = get_page_h(drv)
    view_h = get_view_h(drv)
    step   = int(view_h * 0.65)   # 65% -> overlap 35%
    poses  = list(range(0, page_h, step))
    if page_h not in poses: poses.append(page_h)

    print(f"  Trang: {page_h}px | Buoc: {step}px | Tong: {len(poses)} buoc")

    all_ans   = {}
    seen      = set()
    prev_hash = ""
    max_cau   = 0

    for idx, pos in enumerate(poses):
        scroll_to(drv, pos)
        time.sleep(0.4)

        # Phat hien thay doi viewport
        vh = _viewport_hash(drv)
        if vh == prev_hash:
            print(f"  [{idx+1}/{len(poses)}] Viewport khong doi -> bo qua")
            continue
        prev_hash = vh

        pct = int((idx+1)/len(poses)*100)
        print(f"  [{idx+1}/{len(poses)}] Y={get_scroll_y(drv)}px {pct}%...", end=" ", flush=True)

        # Prompt ngan gon
        prompt = PROMPT_READ if max_cau == 0 else PROMPT_READ_HINT.format(prev=max_cau)

        raw    = ask_ai(shot(drv), prompt)

        if not raw or "NONE" in raw.upper():
            print("(trong)")
            time.sleep(0.8); continue

        batch = _parse_answers(raw)
        new   = {k:v for k,v in batch.items() if k not in seen}

        if new:
            print(f"(+{len(new)} cau)")
            for k,v in sorted(new.items()):
                print(f"    Cau {k:>3}: {v}")
                all_ans[k] = v; seen.add(k)
                if k > max_cau: max_cau = k
        else:
            print("(khong moi)")

        time.sleep(1.0)  # nghi giua cac buoc

    scroll_top(drv); time.sleep(0.4)
    print(f"\n  XONG: {len(all_ans)} cau | AI dung: {PROVIDERS[_prov_idx][0]} key#{_key_idx+1}")
    return all_ans

# ═══════════════════════════════════════════════════════════════
# CLICK DAP AN
# ═══════════════════════════════════════════════════════════════
def find_q_els(drv):
    return drv.execute_script("""
        var found=[]; var all=document.querySelectorAll('div,li,section,article');
        for(var i=0;i<all.length;i++){
            var el=all[i];
            var r=el.querySelectorAll('input[type="radio"]');
            var c=el.querySelectorAll('input[type="checkbox"]');
            var t=el.querySelectorAll('input[type="text"],textarea');
            if(r.length>=2||c.length>=2||t.length>=1){
                var skip=false;
                for(var j=0;j<found.length;j++){if(found[j].contains(el)){skip=true;break;}}
                if(!skip) found.push(el);
            }
        }
        return found;
    """) or []

def click_ans(drv, q_el, ans: str, num: int):
    a       = ans.strip().upper()
    radios  = q_el.find_elements(By.CSS_SELECTOR,"input[type='radio']")
    checks  = q_el.find_elements(By.CSS_SELECTOR,"input[type='checkbox']")
    texts   = q_el.find_elements(By.CSS_SELECTOR,"input[type='text'],textarea")
    labels  = q_el.find_elements(By.CSS_SELECTOR,"label")

    if radios:
        m   = re.search(r"[A-D]", a); idx = ord(m.group())-65 if m else 0
        idx = min(idx, len(radios)-1)
        safe_click(drv, labels[idx] if labels and idx<len(labels) else radios[idx])
        print(f"  ✓ {num}: [{m.group() if m else 'A'}]")

    elif checks:
        for ch in re.findall(r"[A-D]", a):
            i = ord(ch)-65
            if i < len(checks):
                safe_click(drv, labels[i] if labels and i<len(labels) else checks[i])
                time.sleep(0.15)
        print(f"  ✓ {num}: [{a}]")

    elif texts:
        b = texts[0]; safe_click(drv, b); b.clear(); b.send_keys(ans)
        print(f"  ✓ {num}: '{ans[:30]}'")

    else:
        is_t   = any(w in a for w in ["DUNG","ĐÚNG","TRUE"])
        targets = ["ĐÚNG","DUNG","TRUE"] if is_t else ["SAI","FALSE"]
        for btn in q_el.find_elements(By.CSS_SELECTOR,"button,label,[role='button']"):
            if any(t in btn.text.upper() for t in targets) and btn.is_displayed():
                safe_click(drv, btn); print(f"  ✓ {num}: [{btn.text.strip()}]"); return
        # Vision fallback (ton token nhat, chi dung khi can)
        resp = ask_ai(shot_el(drv,q_el), f"Cau {num} dap an '{ans}'. Toa do click? JSON:{{\"x\":0,\"y\":0}}")
        try:
            d  = json.loads(re.search(r'\{[^}]+\}',resp).group())
            dpr= drv.execute_script("return window.devicePixelRatio") or 1
            loc= q_el.location_once_scrolled_into_view
            ax = int(loc["x"]+d["x"]/dpr); ay = int(loc["y"]+d["y"]/dpr)
            drv.execute_script(f"window.scrollTo(0,{max(0,ay-200)});"); time.sleep(0.2)
            ry = ay-get_scroll_y(drv)
            ActionChains(drv).move_by_offset(ax,ry).click().perform()
            ActionChains(drv).move_by_offset(-ax,-ry).perform()
            print(f"  ✓ {num}: vision ({ax},{ay})")
        except: print(f"  ✗ {num}: vision loi")

def apply_answers(drv, answers: dict):
    print("\n[5] === CLICK DAP AN ===")
    scroll_top(drv); time.sleep(0.6)
    q_els = find_q_els(drv)
    print(f"  Tim thay {len(q_els)} element cau hoi")
    applied = 0
    for i, q_el in enumerate(q_els):
        n   = i + 1
        ans = answers.get(n)
        if not ans: print(f"  - Cau {n}: bo qua"); continue
        try:
            drv.execute_script("arguments[0].scrollIntoView({block:'center'});", q_el)
            time.sleep(0.25); drv.execute_script("window.scrollBy(0,-100);"); time.sleep(0.15)
            click_ans(drv, q_el, ans, n); applied += 1; time.sleep(0.25)
        except StaleElementReferenceException:
            q_els = find_q_els(drv)
            if i < len(q_els):
                try: click_ans(drv, q_els[i], ans, n); applied += 1
                except Exception as e2: print(f"  ✗ {n}: {e2}")
        except Exception as e:
            print(f"  ✗ {n}: {e}")
    print(f"  Xong: {applied}/{len(q_els)} cau")

# ═══════════════════════════════════════════════════════════════
# NOP BAI
# ═══════════════════════════════════════════════════════════════
def submit(drv):
    print("\n[6] Nop bai...")
    drv.execute_script("window.scrollTo(0,document.body.scrollHeight);"); time.sleep(0.8)
    for kw in ["Nộp bài","Submit","Hoàn thành","Kết thúc","Nop bai"]:
        for el in drv.find_elements(By.XPATH,
                f"//button[contains(.,'{kw}')]|//a[contains(.,'{kw}')]"):
            if el.is_displayed():
                safe_click(drv,el); print(f"  [nop] {el.text.strip()}"); time.sleep(2.5)
                for ck in ["Xác nhận","Đồng ý","OK","Có"]:
                    for c in drv.find_elements(By.XPATH,f"//button[contains(.,'{ck}')]"):
                        if c.is_displayed(): safe_click(drv,c); print(f"  [ok] {c.text}"); return True
                return True
    print("  Khong tim thay nut nop -> nop thu cong!")
    return False

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def run():
    drv = make_driver()
    try:
        # 1. Mo link
        print("\n[1] Mo link...")
        drv.get(link_homework); time.sleep(3)

        # 2. Ten thi sinh
        setup_name(drv, Name); time.sleep(1.5)

        # 3. Bat dau
        print("\n[3] Bat dau lam bai...")
        if click_start(drv): time.sleep(2.5)
        else: print("  Khong co nut bat dau")

        # 4. Doc cau hoi
        answers = scroll_and_read(drv)
        if not answers:
            print("[!] Khong doc duoc cau hoi!"); input("Enter de thoat..."); return

        print(f"\n=== TOM TAT {len(answers)} DAP AN ===")
        for k in sorted(answers): print(f"  Cau {k:>3}: {answers[k]}")

        # 5. Click dap an
        apply_answers(drv, answers)

        # 6. Nop bai
        submit(drv)

        notification.notify(title="✅ Azota v4.0 Xong!", message=f"{len(answers)} cau | {Name}", timeout=10)
        print(f"\nHOAN THANH! {len(answers)} cau.")
        input("\nEnter de dong...")

    except Exception as e:
        import traceback; traceback.print_exc()
        notification.notify(title="❌ Azota Loi!", message=str(e)[:100], timeout=10)
        input("Enter de thoat...")
    finally:
        drv.quit()

if __name__ == "__main__":
    run()
