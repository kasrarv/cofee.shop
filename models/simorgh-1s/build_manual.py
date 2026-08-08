"""Generate the SIMORGH-1S build manual as a single self-contained HTML page."""

from __future__ import annotations

import base64
import io
import json
import pathlib

from PIL import Image

HERE = pathlib.Path(__file__).parent


def img_uri(name: str, width: int = 1280) -> str:
    """Crop the render to its content, scale, and return a PNG data URI."""
    im = Image.open(HERE / name).convert("RGB")
    grey = im.convert("L")
    bg = grey.getpixel((2, 2))
    mask = grey.point(lambda p: 255 if abs(p - bg) > 6 else 0)
    box = mask.getbbox()
    if box:
        pad = 14
        box = (max(box[0] - pad, 0), max(box[1] - pad, 0),
               min(box[2] + pad, im.width), min(box[3] + pad, im.height))
        im = im.crop(box)
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


PARTS = json.loads((HERE / "stl" / "parts.json").read_text())["parts"]

POSE_FA = {
    "upright": "ایستاده روی مقطع اتصال",
    "flat": "خوابیده روی میز",
    "onroot": "ایستاده روی ریشه",
}


def parts_rows() -> str:
    rows = []
    for p in PARTS:
        d = p["size_mm"]
        rows.append(
            f"<tr><td class='mono'>{p['part']}</td>"
            f"<td class='mono num'>{d[0]:.0f} × {d[1]:.0f} × {d[2]:.0f}</td>"
            f"<td class='mono num'>{p['mass_lwpla_g']:.1f}</td>"
            f"<td>{POSE_FA[p['print_pose']]}</td></tr>")
    return "\n".join(rows)


HTML = """<title>سیمرغ‑1S — دفترچه ساخت</title>
<style>
:root {
  --paper:#F3F4F1; --card:#FFFFFF; --ink:#191E24; --ink-2:#4C555E;
  --rule:#CFD3CB; --rule-soft:#E2E5DE;
  --accent:#C43D30; --accent-soft:#F6E5E2; --warn:#B87914; --warn-soft:#FBF0DC;
  --ok:#3F7A52;
  --mono:ui-monospace,"SFMono-Regular",Menlo,Consolas,"Liberation Mono",monospace;
  --sans:Vazirmatn,"IRANSans","IRANYekan","Segoe UI",Tahoma,
         "Noto Sans Arabic",system-ui,sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper:#13171B; --card:#191E23; --ink:#E7EAE5; --ink-2:#9AA4AC;
    --rule:#2E353C; --rule-soft:#232A30;
    --accent:#E4604F; --accent-soft:#2B1E1C; --warn:#DCA645; --warn-soft:#2A2318;
    --ok:#6FB187;
  }
}
:root[data-theme="dark"] {
  --paper:#13171B; --card:#191E23; --ink:#E7EAE5; --ink-2:#9AA4AC;
  --rule:#2E353C; --rule-soft:#232A30;
  --accent:#E4604F; --accent-soft:#2B1E1C; --warn:#DCA645; --warn-soft:#2A2318;
  --ok:#6FB187;
}

* { box-sizing:border-box; }
body {
  margin:0; background:var(--paper); color:var(--ink);
  font-family:var(--sans); font-size:16.5px; line-height:1.85;
  direction:rtl; text-align:right;
  -webkit-font-smoothing:antialiased;
}
.mono { font-family:var(--mono); font-variant-numeric:tabular-nums; direction:ltr;
        unicode-bidi:embed; }
.num { text-align:left; }

.wrap { max-width:960px; margin:0 auto; padding:0 24px 96px; }

/* ---- masthead ---- */
header { padding:64px 0 34px; border-bottom:2px solid var(--ink); }
.eyebrow {
  font-family:var(--mono); font-size:11px; letter-spacing:.22em;
  text-transform:uppercase; color:var(--accent); direction:ltr;
}
h1 { font-size:clamp(38px,6.5vw,62px); line-height:1.06; margin:14px 0 8px;
     font-weight:800; letter-spacing:-.015em; text-wrap:balance; }
h1 .kv { font-family:var(--mono); font-weight:600; color:var(--ink-2);
         font-size:.42em; letter-spacing:0; display:block; margin-top:14px;
         direction:ltr; }
.lede { font-size:19px; color:var(--ink-2); max-width:60ch; margin:14px 0 0; }

/* ---- key figures strip ---- */
.figs { display:grid; grid-template-columns:repeat(auto-fit,minmax(118px,1fr));
        gap:1px; background:var(--rule); border:1px solid var(--rule);
        margin:34px 0 0; }
.fig { background:var(--card); padding:14px 16px; }
.fig dt { font-size:11.5px; letter-spacing:.06em; color:var(--ink-2); margin:0; }
.fig dd { margin:4px 0 0; font-family:var(--mono); font-size:20px;
          font-weight:600; direction:ltr; text-align:right; }
.fig dd small { font-size:12px; font-weight:400; color:var(--ink-2); }

/* ---- sections ---- */
section { padding-top:60px; }
h2 { font-size:26px; font-weight:750; margin:0 0 6px; letter-spacing:-.01em;
     display:flex; align-items:baseline; gap:12px; }
h2::before {
  content:attr(data-n); font-family:var(--mono); font-size:12px;
  color:var(--accent); font-weight:600; letter-spacing:.1em;
  border:1px solid var(--accent); border-radius:2px; padding:2px 6px;
  flex:none; direction:ltr;
}
h3 { font-size:17.5px; font-weight:700; margin:34px 0 8px; }
p { max-width:72ch; margin:0 0 14px; }
.sub { color:var(--ink-2); font-size:15px; max-width:72ch; margin:0 0 22px; }
a { color:var(--accent); }

ul, ol { max-width:72ch; padding-inline-start:1.35em; margin:0 0 16px; }
li { margin:0 0 8px; }

/* ---- tables ---- */
.scroll { overflow-x:auto; margin:0 0 18px;
          border:1px solid var(--rule); background:var(--card); }
table { width:100%; border-collapse:collapse; font-size:14.5px; }
th, td { padding:9px 13px; border-bottom:1px solid var(--rule-soft);
         text-align:right; white-space:nowrap; }
thead th { background:var(--paper); font-size:12px; letter-spacing:.04em;
           color:var(--ink-2); font-weight:700;
           border-bottom:1px solid var(--rule); position:sticky; top:0; }
tbody tr:last-child td { border-bottom:0; }
tr.hi td { background:var(--accent-soft); font-weight:600; }
td.bad { color:var(--ink-2); }
.tag { font-family:var(--mono); font-size:11px; padding:1px 6px;
       border-radius:2px; direction:ltr; display:inline-block; }
.tag.ok { background:var(--accent-soft); color:var(--accent); }
.tag.no { background:var(--rule-soft); color:var(--ink-2); }

/* ---- callouts ---- */
.note { border:1px solid var(--rule); border-inline-start:3px solid var(--warn);
        background:var(--warn-soft); padding:15px 18px; margin:0 0 18px;
        max-width:72ch; }
.note.crit { border-inline-start-color:var(--accent);
             background:var(--accent-soft); }
.note h4 { margin:0 0 6px; font-size:15px; font-weight:750; }
.note p:last-child { margin-bottom:0; }

/* ---- figures ---- */
figure { margin:0 0 22px; }
figure img { width:100%; display:block; border:1px solid var(--rule);
             background:var(--card); }
figcaption { font-size:13px; color:var(--ink-2); margin-top:8px;
             font-family:var(--mono); direction:ltr; text-align:right; }
.duo { display:grid; grid-template-columns:1fr 1fr; gap:18px; }
@media (max-width:680px) { .duo { grid-template-columns:1fr; } }

/* ---- step list ---- */
ol.steps { list-style:none; padding:0; counter-reset:s; max-width:74ch; }
ol.steps > li { counter-increment:s; position:relative;
                padding-inline-start:44px; margin:0 0 20px; }
ol.steps > li::before {
  content:counter(s,decimal-leading-zero); position:absolute; inset-inline-start:0;
  top:2px; font-family:var(--mono); font-size:13px; font-weight:700;
  color:var(--accent); border-bottom:1px solid var(--accent); padding-bottom:1px;
}
ol.steps b { font-weight:750; }

footer { margin-top:72px; padding-top:22px; border-top:1px solid var(--rule);
         font-size:13px; color:var(--ink-2); }
</style>

<div class="wrap">

<header>
  <div class="eyebrow">3D-printed park flyer &middot; single-cell</div>
  <h1>سیمرغ&#8288;-1S
    <span class="kv">span 850 mm &nbsp;·&nbsp; AUW ~340 g &nbsp;·&nbsp; 1S Li-ion &nbsp;·&nbsp; 3 channel</span>
  </h1>
  <p class="lede">هواپیمای بال‑بالا با بدنه چهارتکه، بال چهارتکه و ایرفویل
  Clark Y. تمام قطعات زیر ۲۵۰ میلی‌متر چاپ می‌شوند و با میله کربن و چسب
  مونتاژ می‌گردند.</p>

  <dl class="figs">
    <div class="fig"><dt>دهانه بال</dt><dd>850<small> mm</small></dd></div>
    <div class="fig"><dt>طول</dt><dd>786<small> mm</small></dd></div>
    <div class="fig"><dt>سطح بال</dt><dd>11.94<small> dm²</small></dd></div>
    <div class="fig"><dt>اسکلت چاپی</dt><dd>184<small> g</small></dd></div>
    <div class="fig"><dt>وزن پروازی</dt><dd>~340<small> g</small></dd></div>
    <div class="fig"><dt>بارگذاری بال</dt><dd>28.5<small> g/dm²</small></dd></div>
    <div class="fig"><dt>واماندگی</dt><dd>6.3<small> m/s</small></dd></div>
  </dl>
</header>

<section>
  <h2 data-n="01">شکل نهایی</h2>
  <figure>
    <img src="__ISO__" alt="نمای سه‌بعدی سیمرغ-1S">
    <figcaption>polyhedral wing · swept fin · removable canopy hatch</figcaption>
  </figure>
  <div class="duo">
    <figure><img src="__TOP__" alt="نمای بالا"><figcaption>planform — 850 mm span</figcaption></figure>
    <figure><img src="__SIDE__" alt="نمای جانبی"><figcaption>side — 786 mm length</figcaption></figure>
  </div>
  <figure><img src="__FRONT__" alt="نمای جلو">
    <figcaption>front — 10° polyhedral on the outer panels</figcaption></figure>
</section>

<section>
  <h2 data-n="02">مشخصات فنی</h2>
  <div class="scroll"><table>
    <tbody>
      <tr><td>پیکربندی</td><td>بال‑بالا، دم متعارف، ۳ کاناله (گاز، سکان، ارتفاع)</td></tr>
      <tr><td>ایرفویل بال</td><td class="mono">Clark Y — 11.7% — کف صاف</td></tr>
      <tr><td>وتر ریشه / میانی / نوک</td><td class="mono num">165 / 145 / 105 mm</td></tr>
      <tr><td>نسبت منظری</td><td class="mono num">6.05</td></tr>
      <tr><td>زاویه نصب بال</td><td class="mono num">+2°</td></tr>
      <tr><td>دایهدرال</td><td class="mono num">10° روی پنل بیرونی</td></tr>
      <tr><td>زاویه موتور</td><td class="mono num">2° پایین + 2° راست (در فایربال ساخته شده)</td></tr>
      <tr><td>سطح افقی دم</td><td class="mono num">2.6 dm² — V<sub>h</sub> = 0.61</td></tr>
      <tr><td>سطح عمودی دم</td><td class="mono num">1.7 dm² — V<sub>v</sub> = 0.070</td></tr>
      <tr><td>ضخامت پوسته</td><td class="mono num">0.45 mm (تک‌دیواره)</td></tr>
      <tr class="hi"><td>مرکز ثقل</td><td class="mono num">40 mm پشت لبه حمله بال (28% MAC)</td></tr>
    </tbody>
  </table></div>
</section>

<section>
  <h2 data-n="03">سیستم پیشران</h2>
  <p class="sub">با ۳٫۷ ولت توان در دسترس بسیار محدود است، پس انتخاب موتور و
  ملخ را نمی‌شود حدس زد. جدول زیر از حل نقطه تعادل گشتاور موتور و ملخ به‌دست
  آمده، با احتساب افت ولتاژ داخلی سل.</p>

  <div class="scroll"><table>
    <thead><tr><th>موتور</th><th>ملخ</th><th class="num">دور</th>
      <th class="num">جریان</th><th class="num">ولتاژ</th><th class="num">توان</th>
      <th class="num">رانش</th><th class="num">T/W</th><th>نتیجه</th></tr></thead>
    <tbody>
      <tr><td class="mono">2204 2300KV</td><td class="mono">6×4</td>
        <td class="mono num">7306</td><td class="mono num">3.3 A</td>
        <td class="mono num">3.47</td><td class="mono num">11.4 W</td>
        <td class="mono num">100 g</td><td class="mono num">0.29</td>
        <td class="bad"><span class="tag no">ضعیف</span> بلند نمی‌شود</td></tr>
      <tr><td class="mono">2204 2300KV</td><td class="mono">7×4</td>
        <td class="mono num">6571</td><td class="mono num">5.1 A</td>
        <td class="mono num">3.32</td><td class="mono num">16.9 W</td>
        <td class="mono num">147 g</td><td class="mono num">0.43</td>
        <td>قابل قبول</td></tr>
      <tr class="hi"><td class="mono">2205 3000KV</td><td class="mono">6×3</td>
        <td class="mono num">8990</td><td class="mono num">5.2 A</td>
        <td class="mono num">3.31</td><td class="mono num">17.2 W</td>
        <td class="mono num">163 g</td><td class="mono num">0.48</td>
        <td><span class="tag ok">پیشنهاد</span></td></tr>
      <tr><td class="mono">2205 3000KV</td><td class="mono">6×4</td>
        <td class="mono num">8758</td><td class="mono num">5.7 A</td>
        <td class="mono num">3.26</td><td class="mono num">18.7 W</td>
        <td class="mono num">144 g</td><td class="mono num">0.42</td>
        <td>قابل قبول</td></tr>
      <tr><td class="mono">2306 3600KV</td><td class="mono">6×4</td>
        <td class="mono num">9648</td><td class="mono num">8.2 A</td>
        <td class="mono num">3.05</td><td class="mono num">25.1 W</td>
        <td class="mono num">174 g</td><td class="mono num">0.51</td>
        <td class="bad">فقط با سل پرجریان</td></tr>
      <tr><td class="mono">2 × 1105 5000KV</td><td class="mono">4×4</td>
        <td class="mono num">14338</td><td class="mono num">7.5 A</td>
        <td class="mono num">3.43</td><td class="mono num">25.7 W</td>
        <td class="mono num">167 g</td><td class="mono num">0.49</td>
        <td>دوموتوره، بدون مزیت</td></tr>
    </tbody>
  </table></div>

  <p><b>چرا تک‌موتور:</b> در ولتاژ پایین، رانش را قطر ملخ می‌سازد نه تعداد
  موتور. دو موتور کوچک همان رانش را با دو ESC، دو ناسل و وزن بیشتر می‌دهند.
  بدنه برای تک‌موتور طراحی شده است.</p>

  <div class="note crit">
    <h4>سه چیزی که موقع خرید حتماً باید چک کنی</h4>
    <ul>
      <li><b>ESC حتماً باید ۱S باشد.</b> اکثر ESCهای BLHeli_S حداقل ۲S هستند و
      با ۳٫۷ ولت اصلاً بوت نمی‌شوند. دنبال ESC مخصوص 1S (دنیای whoop/toothpick)
      با جریان ۱۲ آمپر یا بیشتر بگرد.</li>
      <li><b>مبدل افزاینده ۵ ولت / ۲ آمپر لازم است.</b> سروو و ESP32 با ۳٫۷ ولت
      درست کار نمی‌کنند و ESCهای 1S معمولاً BEC ندارند.</li>
      <li><b>۳۵۰۰ mAh در ۴۰ گرم وجود ندارد.</b> این یعنی ۳۲۴ Wh/kg، حدود دو
      برابر بهترین لیتیوم‌پلیمر موجود. سل واقعی ۳۵۰۰ mAh بین ۴۵ تا ۶۵ گرم است.
      محفظه باتری برای ۱۱۰×۴۰×۲۰ میلی‌متر طراحی شده تا هر دو حالت (۱۸۶۵۰ یا
      پاکت) جا شود.</li>
    </ul>
  </div>

  <h3>برد و مدت پرواز</h3>
  <p>در سرعت کروز ۹٫۴ متر بر ثانیه، توان مصرفی حدود <span class="mono">۱۰٫۵ وات</span>
  است. با یک سل ۳۵۰۰ میلی‌آمپرساعت این یعنی حدود <b>۴۰ دقیقه پرواز واقعی</b>
  (با احتساب صعود و مانور). این بلندترین مزیت این طراحی است — یک پارک‌فلایر
  با نیم‌ساعت پرواز.</p>
</section>

<section>
  <h2 data-n="04">لیست قطعات</h2>
  <div class="scroll"><table>
    <thead><tr><th>قطعه</th><th>مشخصات</th><th class="num">وزن</th></tr></thead>
    <tbody>
      <tr><td>موتور</td><td class="mono">2205 3000KV brushless (2204/2306 هم می‌شود)</td><td class="mono num">26 g</td></tr>
      <tr><td>ملخ</td><td class="mono">6×3 یا 6×4 + آداپتور</td><td class="mono num">7 g</td></tr>
      <tr><td>ESC</td><td class="mono">12 A، سازگار با 1S</td><td class="mono num">7 g</td></tr>
      <tr><td>کنترلر</td><td class="mono">ESP32-C3 SuperMini (یا ESP32-S3)</td><td class="mono num">4 g</td></tr>
      <tr><td>مبدل ولتاژ</td><td class="mono">boost 3.7V → 5V / 2A</td><td class="mono num">5 g</td></tr>
      <tr><td>سروو</td><td class="mono">۲ عدد میکروسروو ۹ گرمی (31×32 mm)</td><td class="mono num">18 g</td></tr>
      <tr><td>باتری</td><td class="mono">1S Li-ion، 18650 یا پاکت</td><td class="mono num">45–65 g</td></tr>
      <tr><td>اسپار بال</td><td class="mono">میله کربن ⌀6 × 250 mm</td><td class="mono num">6 g</td></tr>
      <tr><td>اسپار دم</td><td class="mono">میله کربن ⌀3 × 360 mm و ⌀2 × 340 mm</td><td class="mono num">5 g</td></tr>
      <tr><td>پوش‌راد</td><td class="mono">سیم پیانو ⌀1 × 2 عدد، ۴۵۰ mm</td><td class="mono num">6 g</td></tr>
      <tr><td>پیچ بال</td><td class="mono">۴ عدد M3 نایلونی، ۱۶ mm</td><td class="mono num">2 g</td></tr>
      <tr><td>آهنربا</td><td class="mono">۴ عدد ⌀6×3 mm برای درپوش</td><td class="mono num">3 g</td></tr>
      <tr><td>لولا</td><td class="mono">چسب نواری مخصوص لولا (hinge tape)</td><td class="mono num">2 g</td></tr>
    </tbody>
  </table></div>
</section>

<section>
  <h2 data-n="05">تنظیمات چاپ</h2>
  <p class="sub">این مدل پوسته‌ی نازک واقعی است، نه یک جسم توپر که اسلایسر
  خالی‌اش کند. دیواره دقیقاً <span class="mono">0.45 mm</span> مدل شده تا با
  یک پریمتر پر شود.</p>

  <div class="scroll"><table>
    <tbody>
      <tr><td>متریال</td><td><b>LW-PLA</b> (فوم‌شونده) — eSun ePLA-LW، ColorFabb LW-PLA، Polymaker LW</td></tr>
      <tr><td>چرا LW-PLA</td><td>چگالی مؤثر ~۰٫۵۸ در برابر ۱٫۲۴ برای PLA معمولی — یعنی نصف وزن اسکلت</td></tr>
      <tr><td>نازل</td><td class="mono num">0.4 mm</td></tr>
      <tr><td>عرض خط</td><td class="mono num">0.45 mm (برابر ضخامت پوسته)</td></tr>
      <tr><td>تعداد پریمتر</td><td class="mono num">1</td></tr>
      <tr><td>ارتفاع لایه</td><td class="mono num">0.20 mm برای قطعات جفت‌شونده، 0.25 mm برای پوسته‌ها</td></tr>
      <tr><td>اینفیل</td><td class="mono num">0%</td></tr>
      <tr><td>لایه بالا / پایین</td><td class="mono num">2 / 2</td></tr>
      <tr><td>ساپورت</td><td>ندارد — جهت‌گیری قطعات طوری است که لازم نشود</td></tr>
      <tr><td>دما</td><td class="mono num">245–255 °C (LW-PLA)، بستر 60 °C</td></tr>
      <tr><td>ضریب اکستروژن</td><td class="mono num">~50% (طبق دستور تولیدکننده فیلامنت — تست پله‌ای بگیر)</td></tr>
      <tr><td>سرعت</td><td class="mono num">25–35 mm/s</td></tr>
      <tr><td>Brim</td><td>برای قطعات ایستاده (بدنه و دم) توصیه می‌شود</td></tr>
    </tbody>
  </table></div>

  <div class="note">
    <h4>دقت لازم و لقی‌ها</h4>
    <p>مدل با لقی <span class="mono">0.25 mm</span> روی هر جفت‌شدگی طراحی شده.
    اگر پرینتر شما بیش از <span class="mono">±0.15 mm</span> خطا دارد، اول یک
    مکعب کالیبراسیون بگیر. اتصالات بدنه به‌صورت کالر نر/ماده است — باید با فشار
    دست جا برود، نه با چکش.</p>
  </div>

  <h3>غیر از LW-PLA چه چیزی؟</h3>
  <ul>
    <li><b>PLA معمولی</b> — کار می‌کند ولی اسکلت را به ~۳۸۰ گرم می‌رساند و
    با این باتری دیگر پرواز خوبی نخواهی داشت. فقط برای قطعات کوچک سازه‌ای
    (فایروال، درپوش) خوب است.</li>
    <li><b>PETG</b> — سنگین‌تر و نرم‌تر، برای بال بد است. برای فایروال خوب است.</li>
    <li><b>ABS/ASA</b> — تاب برمی‌دارد و مزیتی اینجا ندارد.</li>
  </ul>
</section>

<section>
  <h2 data-n="06">قطعات چاپی</h2>
  <p class="sub">جهت چاپ داخل فایل‌های STL اعمال شده است؛ قطعات را در اسلایسر
  نچرخانید. بدنه و سطوح دم ایستاده چاپ می‌شوند تا هر لایه یک حلقه بسته باشد
  (بدون سطح افقی، بدون ساپورت)؛ بال خوابیده چاپ می‌شود چون کف صاف Clark Y
  خودش بهترین لایه اول است.</p>
  <div class="scroll"><table>
    <thead><tr><th>فایل</th><th class="num">ابعاد mm</th>
      <th class="num">وزن g</th><th>جهت چاپ</th></tr></thead>
    <tbody>
__PARTS__
    </tbody>
  </table></div>
  <p class="mono" style="color:var(--ink-2);font-size:14px">
    مجموع: 184.5 g &nbsp;·&nbsp; بزرگ‌ترین بُعد: 233.9 mm &nbsp;·&nbsp;
    همه watertight</p>
</section>

<section>
  <h2 data-n="07">مونتاژ</h2>
  <ol class="steps">
    <li><b>بال.</b> میله کربن ⌀6 را داخل تونل اسپار پنل داخلی راست بچسبان،
    ۱۲۵ میلی‌متر بیرون بگذار و پنل چپ را روی همان میله سُر بده تا دو ریشه
    به هم بچسبند. قبل از خشک شدن، هر دو پنل را روی یک سطح صاف بگذار.</li>

    <li><b>پنل‌های بیرونی.</b> زبانه‌ی هر پنل بیرونی داخل شکاف نوک پنل داخلی
    می‌رود. شکاف با زاویه ۱۰ درجه بریده شده، پس دایهدرال خودش تنظیم می‌شود.
    نوک بال باید <span class="mono">۷۵ mm</span> بالاتر از ریشه بیفتد.</li>

    <li><b>بدنه.</b> چهار بخش F1→F4 با کالر داخلی جفت می‌شوند. اول خشک تست کن،
    بعد با اپوکسی نازک یا CA بچسبان. مواظب باش بدنه پیچ نخورد — روی یک لبه
    صاف بچین.</li>

    <li><b>سروو‌ها.</b> دو جای سروو در بخش F2 از بالا در دسترس‌اند (وقتی بال
    برداشته شود). سروو راست = سکان، سروو چپ = ارتفاع. سیم‌ها از سوراخ‌های
    فریم عقب رد می‌شوند.</li>

    <li><b>دم.</b> فین از بالا داخل شکاف دم می‌نشیند. دو نیمه‌ی سطح افقی روی
    لبه‌ی دو طرف دم می‌نشینند و با میله ⌀3 که از داخل بدنه رد می‌شود به هم
    قفل می‌شوند. زاویه صفر نسبت به بدنه — با خط‌کش چک کن.</li>

    <li><b>سطوح متحرک.</b> الویتور و رادر با چسب نواری لولا می‌شوند. دو نیمه‌ی
    الویتور با میله ⌀2 که پشت مخروط دم رد می‌شود به هم وصل می‌شوند تا با هم
    حرکت کنند.</li>

    <li><b>موتور.</b> روی فایروال با ۴ پیچ M3. زاویه ۲ درجه پایین و ۲ درجه
    راست از قبل داخل فایروال ساخته شده — چیزی شیم نکن.</li>

    <li><b>الکترونیک.</b> ESC داخل F1 پشت فایروال، مبدل ۵ ولت و ESP32 روی
    سکوی جلوی بال در F2. باتری داخل سینی F1 با نوار ولکرو.</li>

    <li><b>بال روی بدنه.</b> با ۴ پیچ M3 نایلونی به بوش‌های داخل سقف F2.
    نایلونی مهم است — موقع سقوط می‌شکند و بال سالم می‌ماند.</li>
  </ol>
</section>

<section>
  <h2 data-n="08">سیم‌کشی ESP32</h2>
  <div class="scroll"><table>
    <thead><tr><th>از</th><th>به</th><th>توضیح</th></tr></thead>
    <tbody>
      <tr><td class="mono">باتری +</td><td class="mono">ESC + و ورودی boost</td><td>مستقیم از سل</td></tr>
      <tr><td class="mono">boost 5V</td><td class="mono">تغذیه سروو + پین 5V برد</td><td>حداقل ۲ آمپر</td></tr>
      <tr><td class="mono">GPIO (PWM)</td><td class="mono">سیگنال ESC</td><td>50 Hz، 1000–2000 µs</td></tr>
      <tr><td class="mono">GPIO (PWM)</td><td class="mono">سروو سکان</td><td>&nbsp;</td></tr>
      <tr><td class="mono">GPIO (PWM)</td><td class="mono">سروو ارتفاع</td><td>&nbsp;</td></tr>
      <tr><td class="mono">GND</td><td class="mono">مشترک بین همه</td><td>حتماً زمین مشترک</td></tr>
    </tbody>
  </table></div>
  <p>برای لینک رادیویی، <b>ESP-NOW</b> بهترین گزینه است: تأخیر پایین، بدون
  نیاز به روتر، و با یک ESP32 دوم به‌عنوان فرستنده. اگر خواستی پایدارساز
  اضافه کنی، یک MPU6050 روی I2C کافی است — ولی برای پرواز اول بدون آن
  شروع کن.</p>
  <div class="note">
    <h4>قبل از اولین پرواز</h4>
    <p>حتماً یک <b>failsafe</b> بنویس: اگر بسته‌ای در ۵۰۰ میلی‌ثانیه نرسید،
    گاز صفر شود. ESP32 وقتی وای‌فای قطع می‌شود می‌تواند آخرین مقدار PWM را
    نگه دارد و این یعنی هواپیما با گاز کامل فرار می‌کند.</p>
  </div>
</section>

<section>
  <h2 data-n="09">تنظیم و پرواز اول</h2>

  <h3>مرکز ثقل</h3>
  <p>مرکز ثقل باید <b>۴۰ میلی‌متر پشت لبه حمله بال</b> باشد (۲۸٪ MAC).
  با دو انگشت زیر بال در همان نقطه بلند کن — دماغه باید کمی پایین بیفتد.
  ابزار تنظیم، جای باتری داخل سینی است. اگر با باتری کاملاً جلو هم دم سنگین
  بود، ۵ تا ۱۰ گرم وزنه در دماغه اضافه کن.</p>

  <h3>حرکت سطوح</h3>
  <div class="scroll"><table>
    <thead><tr><th>سطح</th><th class="num">پرواز اول</th><th class="num">بعد از تنظیم</th></tr></thead>
    <tbody>
      <tr><td>ارتفاع (elevator)</td><td class="mono num">±8 mm</td><td class="mono num">±12 mm</td></tr>
      <tr><td>سکان (rudder)</td><td class="mono num">±14 mm</td><td class="mono num">±20 mm</td></tr>
    </tbody>
  </table></div>
  <p>روی ۳۰٪ expo شروع کن. با دایهدرال ۱۰ درجه، سکان نقش شیب‌روی را هم
  بازی می‌کند — چرخش با سکان انجام می‌شود.</p>

  <h3>پرتاب</h3>
  <p>این هواپیما چرخ ندارد و با دست پرتاب می‌شود و روی شکم می‌نشیند.
  گاز کامل، بدنه افقی (نه رو به بالا)، و یک پرتاب محکم رو به جلو با سرعت
  حدود <span class="mono">۸ متر بر ثانیه</span>. باد ملایم رو به جلو کمک
  می‌کند. اولین پرواز را در چمن انجام بده.</p>

  <div class="note">
    <h4>انتظار واقعی از عملکرد</h4>
    <p>نسبت رانش به وزن حدود <span class="mono">۰٫۴۸</span> است. یعنی این
    هواپیما آرام و باوقار پرواز می‌کند و صعودش ملایم است — نه آکروبات.
    اگر رانش بیشتری می‌خواهی، یا سل پرجریان‌تر (مثل 30Q) با موتور
    <span class="mono">2306 3600KV</span> بگذار، یا اسکلت را با فیلامنت
    سبک‌تر و دیواره نازک‌تر چاپ کن.</p>
  </div>
</section>

<section>
  <h2 data-n="10">تغییر طراحی</h2>
  <p>کل هندسه پارامتریک است. اگر خواستی چیزی را عوض کنی:</p>
  <div class="scroll"><table>
    <thead><tr><th>می‌خواهم…</th><th>پارامتر</th><th>فایل</th></tr></thead>
    <tbody>
      <tr><td>سروو دیگری بگذارم</td><td class="mono">SERVO_L / SERVO_W / SERVO_H</td><td class="mono">airframe.py</td></tr>
      <tr><td>بال بزرگ‌تر یا کوچک‌تر</td><td class="mono">C_ROOT, C_MID, C_TIP, B_INNER, B_OUTER</td><td class="mono">airframe.py</td></tr>
      <tr><td>میله کربن دیگری</td><td class="mono">SPAR_D</td><td class="mono">airframe.py</td></tr>
      <tr><td>پوسته ضخیم‌تر</td><td class="mono">SKIN</td><td class="mono">geom.py</td></tr>
      <tr><td>قطعات کوتاه‌تر (میز کوچک‌تر)</td><td class="mono">SPLIT, B_INNER, B_OUTER</td><td class="mono">airframe.py</td></tr>
      <tr><td>زاویه موتور</td><td class="mono">THRUST_DOWN, THRUST_RIGHT</td><td class="mono">airframe.py</td></tr>
    </tbody>
  </table></div>
  <p>بعد از تغییر: <span class="mono">python3 airframe.py</span> فایل‌های STL
  را دوباره می‌سازد و گزارش می‌دهد هیچ قطعه‌ای از ۲۵۰ میلی‌متر رد نشده و همه
  watertight هستند.</p>
</section>

<footer>
  SIMORGH-1S · اسکلت ۱۸۴ گرم · تمام قطعات ≤ ۲۳۴ mm · مدل پارامتریک با
  Python + trimesh/manifold3d
</footer>

</div>
"""


def main():
    html = (HTML
            .replace("__ISO__", img_uri("preview_iso.png"))
            .replace("__TOP__", img_uri("preview_top.png"))
            .replace("__SIDE__", img_uri("preview_side.png"))
            .replace("__FRONT__", img_uri("preview_front.png"))
            .replace("__PARTS__", parts_rows()))
    out = HERE / "build_manual.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}  ({len(html) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
