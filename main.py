# news23 poster: "The World in One Day — Monday 23 November 2026"
# Builds a 1024x1024 PNG newspaper front page entirely in code, stdlib only.
# Deterministic: no clock, no randomness, no network. Runs twice, same bytes.
import os, sys, zlib, struct, math

BASE = os.path.dirname(os.path.abspath(__file__))
W = H = 1024

# ------------------------------------------------------------------ palette
PAPER = (247, 243, 232)
PAPER2 = (250, 246, 236)
INK = (26, 24, 20)
NAVY = (20, 32, 52)
NAVY2 = (30, 46, 72)
RED = (178, 34, 34)
RED2 = (146, 26, 26)
MUT = (110, 100, 84)
RULE = (208, 198, 176)
RULE2 = (176, 166, 142)
WHITE = (255, 255, 255)
CREAM = (242, 230, 205)
GOLD = (222, 168, 62)
SKY = (36, 58, 92)
SEA = (52, 84, 118)
GRASS = (92, 138, 84)

REGION = {
    "EUROPE": (15, 106, 128),
    "MIDEAST": (172, 74, 26),
    "AMERICAS": (32, 74, 168),
    "ASIA": (24, 122, 70),
    "AFRICA": (186, 44, 40),
    "OCEANIA": (120, 58, 158),
    "GLOBAL": (72, 76, 86),
    "WAR": (120, 32, 32),
    "SPORT": (18, 98, 62),
    "MONEY": (150, 96, 16),
}

# ------------------------------------------------------------------ assets
class Assets:
    def __init__(self):
        raw = open(os.path.join(BASE, "assets.bin"), "rb").read()
        assert raw[:6] == b"MFNT01", "bad assets"
        n = struct.unpack("<H", raw[6:8])[0]
        self.fonts = {}
        blob = zlib.decompress(raw[8 + n * 16 + 256 * 128:])
        self.land = raw[8 + n * 16:8 + n * 16 + 256 * 128]
        off = 8
        for _ in range(n):
            key = raw[off:off + 4].rstrip(b"\x00").decode("latin1"); off += 4
            size, ng, o, ln = struct.unpack("<HHII", raw[off:off + 12]); off += 12
            glyphs = {}
            order = []
            p = o
            for _i in range(ng):
                ch, w, h, bx, by, _p = struct.unpack("<HbbbbB", blob[p:p + 7]); p += 7
                order.append((ch, w, h, bx, by))
            for _i in range(ng):
                ch = order[_i][0]
                adv = struct.unpack("<H", blob[p:p + 2])[0] / 16.0; p += 2
                order[_i] = order[_i] + (adv,)
            for (ch, w, h, bx, by, adv) in order:
                exp = w * h
                m = bytearray()
                q = p
                while True:
                    t = blob[q]
                    if t == 0:
                        m.extend([blob[q + 2]] * blob[q + 1]); q += 3
                    elif t == 1:
                        m.append(blob[q + 1]); q += 2
                    else:
                        q += 1; break
                p = q
                assert len(m) == exp, (key, size, ch, len(m), exp)
                glyphs[ch] = (w, h, bx, by, adv, bytes(m))
            self.fonts[(key, size)] = glyphs

    def glyph(self, key, size, ch):
        g = self.fonts.get((key, size))
        if g is None:
            # fall back to nearest size of same font
            cands = [s for (k, s) in self.fonts if k == key]
            if not cands:
                return None
            size = min(cands, key=lambda s: abs(s - size))
            g = self.fonts[(key, size)]
        return g.get(ord(ch))


A = Assets()

# ------------------------------------------------------------------ surface
buf = bytearray(PAPER * (W * H))

def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = c[0]; buf[i + 1] = c[1]; buf[i + 2] = c[2]

def fill_rect(x, y, w, h, c):
    x0 = max(0, x); y0 = max(0, y)
    x1 = min(W, x + w); y1 = min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * int(x1 - x0)
    for yy in range(int(y0), int(y1)):
        i = (yy * W + int(x0)) * 3
        buf[i:i + len(row)] = row

def blend_rect(x, y, w, h, c, a):
    """Alpha-blend a solid rect (a in 0..255)."""
    x0 = max(0, x); y0 = max(0, y)
    x1 = min(W, x + w); y1 = min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    ia = 255 - a
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        for xx in range(x0, x1):
            buf[i] = (buf[i] * ia + c[0] * a) >> 8
            buf[i + 1] = (buf[i + 1] * ia + c[1] * a) >> 8
            buf[i + 2] = (buf[i + 2] * ia + c[2] * a) >> 8
            i += 3

def stroke_rect(x, y, w, h, c, t=1):
    fill_rect(x, y, w, t, c)
    fill_rect(x, y + h - t, w, t, c)
    fill_rect(x, y, t, h, c)
    fill_rect(x + w - t, y, t, h, c)

def hline(x0, x1, y, c, t=1):
    fill_rect(min(x0, x1), y, abs(x1 - x0) + 1, t, c)

def vline(x, y0, y1, c, t=1):
    fill_rect(x, min(y0, y1), t, abs(y1 - y0) + 1, c)

def line(x0, y0, x1, y1, c, t=1):
    steps = max(abs(x1 - x0), abs(y1 - y0)) + 1
    for s in range(steps):
        x = x0 + (x1 - x0) * s // steps
        y = y0 + (y1 - y0) * s // steps
        fill_rect(x - (t - 1) // 2, y - (t - 1) // 2, t, t, c)

def fill_circle(cx, cy, r, c):
    for dy in range(-r, r + 1):
        dx = int(math.isqrt(r * r - dy * dy))
        fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

def ring(cx, cy, r, c, t=1):
    fill_circle(cx, cy, r, c)
    fill_circle(cx, cy, r - t, None)

def fill_poly(pts, c):
    ys = [p[1] for p in pts]
    y0 = max(0, int(math.floor(min(ys)))); y1 = min(H - 1, int(math.ceil(max(ys))))
    n = len(pts)
    for y in range(y0, y1 + 1):
        yc = y + 0.5
        xs = []
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            if (ay <= yc < by) or (by <= yc < ay):
                xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
        if not xs:
            continue
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            a = int(math.ceil(xs[k] - 0.5)); b = int(math.floor(xs[k + 1] - 0.5))
            if b >= a:
                fill_rect(a, y, b - a + 1, 1, c)

# ------------------------------------------------------------------ text
def measure(text, key, size, sp=0.0):
    total = 0.0
    for ch in text:
        g = A.glyph(key, size, ch)
        if g is None:
            g = A.glyph(key, size, "?")
        if g is None:
            total += size * 0.3
            continue
        total += g[4]
    return total + sp * max(0, len(text) - 1)

def draw_text(buf, x, ybase, text, key, size, c, sp=0.0):
    cx = float(x)
    for ch in text:
        g = A.glyph(key, size, ch)
        if g is None:
            g = A.glyph(key, size, "?")
            if g is None:
                cx += size * 0.3 + sp
                continue
        gw, gh, gbx, gby, gadv, mask = g
        ox = int(round(cx)) + gbx
        oy = ybase - gby
        r0 = max(0, -oy); r1 = min(gh, H - oy)
        c0 = max(0, -ox); c1 = min(gw, W - ox)
        if r1 > r0 and c1 > c0:
            cR, cG, cB = c
            ia = None
            for yy in range(r0, r1):
                mrow = yy * gw
                drow = ((oy + yy) * W + ox) * 3
                for xx in range(c0, c1):
                    a = mask[mrow + xx]
                    if a:
                        if a == 255:
                            di = drow + xx * 3
                            buf[di] = cR; buf[di + 1] = cG; buf[di + 2] = cB
                        else:
                            di = drow + xx * 3
                            k = 255 - a
                            buf[di] = (buf[di] * k + cR * a) >> 8
                            buf[di + 1] = (buf[di + 1] * k + cG * a) >> 8
                            buf[di + 2] = (buf[di + 2] * k + cB * a) >> 8
        cx += gadv + sp
    return cx - x

def draw_text_c(buf, cx, ybase, text, key, size, c, sp=0.0):
    w = measure(text, key, size, sp)
    return draw_text(buf, int(cx - w / 2), ybase, text, key, size, c, sp)

def draw_text_r(buf, rx, ybase, text, key, size, c, sp=0.0):
    w = measure(text, key, size, sp)
    return draw_text(buf, int(rx - w), ybase, text, key, size, c, sp)

def wrap(text, key, size, width):
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        if measure(t, key, size) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

# ------------------------------------------------------------------ content
DECK = ("COP31 ends with no fossil-fuel deal \u00b7 Russian warship sinks off Libya \u00b7 Seoul slides on AI fears "
        "\u00b7 Trump hosts third meme-coin gala")

STATS = [
    ("0", "deals adopted at COP31 as the gavel finally falls"),
    ("2", "Russian ships hit off Libya; one sinks at Benghazi"),
    ("-3.4%", "Seoul's KOSPI slides on AI-bubble fears"),
    ("258", "Democratic seats as the House map settles"),
    ("$450m", "Mets' record deal for pitcher Tarik Skubal"),
    ("83", "Molly Meldrum, voice of Australian pop, dies"),
]

TIMELINE = [
    ("00:03", "Cameroon's ex-rebels: broken promises"),
    ("00:18", "Seoul's KOSPI slides on AI fears"),
    ("00:25", "Molly Meldrum dies, 83"),
    ("00:31", "Trump's third meme-coin gala"),
    ("00:39", "WHO plea amid Congo fighting"),
    ("00:50", "COP31 no-deal confirmed"),
    ("01:07", "Iowa blast order stands"),
]

HEROES = [
    dict(n=1, region="GLOBAL", topic="CLIMATE TALKS", place="ANTALYA, T\u00dcRKIYE",
         tag="THE GAVEL FALLS",
         head="COP31 ends with no deal, and no mention of fossil fuels",
         body=("The final text keeps the 35%-by-2035 power goal but drops the $120bn adaptation plan and "
               "every word on coal, oil and gas. Objections ran past dawn; the gavel fell with 1.5\u00b0C kept "
               "on paper only."),
         src="Reuters \u00b7 AP \u00b7 ABC \u00b7 Guardian", scene="cop31"),
    dict(n=2, region="MIDEAST", topic="WAR AT SEA", place="BENGHAZI, LIBYA",
         tag="SHIP SUNK",
         head="Russian warship sinks at Benghazi after drone hits",
         body=("A second vessel was hit in a new wave of naval-drone attacks off Libya, hours after a "
               "suspected Ukrainian drone sank a Russian warship at its moorings. The gulf is on alert."),
         src="Guardian \u00b7 Reuters \u00b7 Al Jazeera", scene="ship"),
    dict(n=3, region="ASIA", topic="MARKETS", place="SEOUL, SOUTH KOREA",
         tag="KOSPI -3.4%",
         head="Seoul slides as AI-bubble fear grips Asia's markets",
         body=("The KOSPI tumbled in early trade, extending a global tech selloff, days after the education "
               "minister quit over an AI exam-cheating scandal in the entrance tests."),
         src="Yonhap \u00b7 Reuters \u00b7 Al Jazeera", scene="chart"),
]

CARDS = [
    dict(n=4, region="AMERICAS", topic="CONGRESS", place="WASHINGTON",
         head="Democrats take largest House majority since 1992",
         body="A North Carolina flip seals the sweep; Jeffries offers to work across the aisle.", src="AP \u00b7 Guardian", scene="capitol"),
    dict(n=5, region="MIDEAST", topic="WEST BANK", place="PALESTINIAN VILLAGES",
         head="Settler attacks condemned as 'Jewish terrorism'",
         body="A Netanyahu rival's rebuke after overnight assaults on villages.", src="Times of Israel", scene="village"),
    dict(n=6, region="AFRICA", topic="HEALTH", place="KISANGANI, DR CONGO",
         head="WHO pleads for peace in Ebola-hit region",
         body="Heavy fighting around the outbreak zone strains the response.", src="Al Jazeera", scene="tent"),
    dict(n=7, region="OCEANIA", topic="DATA CENTRES", place="CANBERRA",
         head="Datacentre chiefs met ministers 120 times",
         body="Three years of meetings with state premiers, analysis finds.", src="Guardian", scene="rack"),
    dict(n=8, region="EUROPE", topic="HEALTH", place="LONDON",
         head="NHS savings drive leaves hospitals facing cuts",
         body="England's trusts told to find 'unpalatable' savings.", src="Guardian", scene="hospital"),
    dict(n=9, region="ASIA", topic="DISASTER", place="SERANG, INDONESIA",
         head="Factory fire toll: three dead, dozens missing",
         body="Blaze tore through a confectionery plant; rescuers search on.", src="Reuters \u00b7 AFP", scene="fire"),
    dict(n=10, region="AMERICAS", topic="CRYPTO", place="NEW YORK",
         head="Trump hosts third gala for his meme coin",
         body="Conflict-of-interest outcry as top holders dine privately.", src="Guardian \u00b7 Al Jazeera", scene="coin"),
    dict(n=11, region="EUROPE", topic="TENNIS", place="TURIN, ITALY",
         head="Alcaraz ends the year as world's best, wins first ATP Finals",
         body="Beats No 1 Zverev for the title both had chased all season.", src="Guardian", scene="tennis"),
    dict(n=12, region="EUROPE", topic="FOOTBALL", place="LIVERPOOL",
         head="Liverpool rout 10-man United 4-0",
         body="Pochettino's reign opens with a nightmare after Yoro's red card.", src="Guardian \u00b7 Sky", scene="pitch"),
    dict(n=13, region="MIDEAST", topic="ENERGY", place="STRAIT OF HORMUZ",
         head="Tankers ablaze in Hormuz as IRGC warns of unrest",
         body="Tehran says strikes hit tankers; shipping insurers reprice the strait.", src="Al Jazeera \u00b7 AP", scene="tanker"),
    dict(n=14, region="AFRICA", topic="WAR", place="KHARTOUM, SUDAN",
         head="RSF drone strikes kill civilians in the capital",
         body="Residential streets hit as the siege of Khartoum grinds on.", src="Al Jazeera", scene="drone"),
    dict(n=15, region="OCEANIA", topic="MUSIC", place="MELBOURNE",
         head="Molly Meldrum, voice of Australian pop, dies at 83",
         body="Countdown host and promoter shaped four decades of music.", src="Guardian \u00b7 ABC", scene="mic"),
]

BRIEFS = [
    ("NEW YORK", "AMERICAS", "Mets reportedly agree $450m deal with Tarik Skubal, richest for a pitcher", "Guardian"),
    ("LONDON", "EUROPE", "UK-EU food deal hailed by British firms: 'We're pretty aligned anyway'", "Guardian"),
    ("MIDLAND", "AMERICAS", "US Army to detonate tonnes of unstable explosives in Iowa despite court order", "BBC"),
    ("YAOUND\u00c9", "AFRICA", "Cameroon's ex-rebels caught between hiding and broken promises", "Al Jazeera"),
    ("SEATTLE", "AMERICAS", "Officials condemn 'horrific' ICE arrests at the city's airport", "Al Jazeera"),
    ("HULL", "EUROPE", "McBurnie's added-time double shocks 10-man Brighton", "Guardian"),
    ("LAS VEGAS", "AMERICAS", "Gerwyn Price ends his barren run with Grand Slam of Darts win", "Guardian"),
    ("MADRID", "EUROPE", "Barcelona roar back from two goals down to sink Villarreal", "Guardian"),
    ("CHIEFS", "AMERICAS", "NFL: Chiefs, Lions and Bills march on; Metcalf ejected for eye poke", "Guardian"),
    ("WASHINGTON", "AMERICAS", "Heartbreak in the capital as Washington Spirit lose the NWSL final", "Al Jazeera"),
    ("ZANZIBAR", "AFRICA", "Fire breaks out at a popular tourist hotspot; no toll yet", "Al Jazeera"),
    ("IZMIR", "EUROPE", "Lion on the loose in T\u00fcrkiye sparks fear among residents", "Al Jazeera"),
    ("ANKARA", "EUROPE", "Mystery of the red stream in T\u00fcrkiye", "Al Jazeera"),
    ("BRUSSELS", "EUROPE", "Court bans China's BYD from selling its 'Defender clone' in the EU", "Guardian"),
    ("DELHI", "ASIA", "Opposition youth wing warns of more Meta protests after police clashes", "Guardian"),
    ("MANASSAS", "AMERICAS", "Virginia reports 2026's first measles-linked death, a child under 5", "Al Jazeera"),
    ("NEW YORK", "AMERICAS", "Aber Kawas becomes first Palestinian in New York state Senate history", "Al Jazeera"),
    ("LONDON", "EUROPE", "UK taxpayers held more than \u00a31tn in offshore tax havens, HMRC data shows", "Guardian"),
    ("JERUSALEM", "MIDEAST", "Likud and Eisenkot's Yashar end coalition talks without a deal", "Al Jazeera"),
    ("SEOUL", "ASIA", "Education minister had quit over AI exam cheating before the market slid", "Guardian"),
    ("CANBERRA", "OCEANIA", "Liberals demand Bowen resign over the COP31 'disaster'", "Guardian"),
    ("SERBIA", "EUROPE", "Editorial: a generational opportunity in Serbia's new political era", "Guardian"),
    ("BERLIN", "EUROPE", "Outrage over a military AI event at the city's arts complex", "Guardian"),
    ("WASHINGTON", "AMERICAS", "Intel chief says he trusts Trump's word that Putin is 'my friend'", "Guardian"),
]

DATECHECK = [
    ("SUN 22", "COP31 talks broke down late Sunday; Iran said it hit two US radars in Bahrain; Russia's 186-drone barrage; Hong Kong's poll; India 720/9; Verstappen's Vegas win"),
    ("FRI 21", "'El Chapo Isidro' arrest; Zelensky on the Crimean Bridge strikes"),
    ("FRI 20", "Peru quake toll revised; the Barfas boat disaster; Voyager's light-day milestone"),
    ("SUN 22", "Sparta II ablaze in the Gulf of Finland - first report Sunday, still burning"),
]

# map pins: (lon, lat, story number)
PINS = [
    (30.7, 36.9, 1), (20.1, 32.1, 2), (127.0, 37.5, 3),
    (-77.0, 38.9, 4), (35.2, 31.9, 5), (28.5, -1.5, 6),
    (149.1, -35.3, 7), (-0.1, 51.5, 8), (106.2, -6.3, 9),
    (-74.0, 40.7, 10), (7.7, 45.0, 11), (-2.9, 53.4, 12),
    (56.3, 26.5, 13), (32.5, 15.6, 14), (145.0, -37.8, 15),
]

PRESS = "05:40 UTC, MON 23 NOV 2026"

# ------------------------------------------------------------------ scenes
def scene_cop31(x, y, w, h):
    fill_rect(x, y, w, h, SKY)
    # sun
    fill_circle(x + int(w * 0.82), y + int(h * 0.28), 14, GOLD)
    # table
    ty = y + int(h * 0.72)
    fill_rect(x + int(w * 0.08), ty, int(w * 0.84), 10, (94, 66, 40))
    fill_rect(x + int(w * 0.12), ty + 10, int(w * 0.76), 5, (74, 50, 30))
    # delegates
    for k in range(9):
        dx = x + int(w * (0.14 + 0.09 * k))
        fill_circle(dx, ty - 8, 5, [(186, 60, 50), (40, 90, 140), (220, 170, 60), (70, 130, 80)][k % 4])
    # gavel block + fallen gavel
    fill_rect(x + int(w * 0.44), ty - 26, 26, 8, (140, 100, 60))
    fill_poly([(x + int(w * 0.47), ty - 44), (x + int(w * 0.47) + 18, ty - 44),
               (x + int(w * 0.47) + 14, ty - 28), (x + int(w * 0.47) + 4, ty - 28)], (120, 84, 48))
    # papers
    for k in range(3):
        fill_rect(x + int(w * 0.18) + k * 8, ty - 4 - k, 6, 4, WHITE)
    # banner
    fill_rect(x, y, w, 16, RED2)
    draw_text(buf, x + 26, y + 12, "NO DEAL", "anb", 9, WHITE)
    if measure("200 NATIONS", "an", 8) < w - 110:
        draw_text_r(buf, x + w - 6, y + 12, "200 NATIONS", "an", 8, (240, 220, 200))

def scene_ship(x, y, w, h):
    fill_rect(x, y, w, h, (14, 22, 38))
    fill_rect(x, y + int(h * 0.62), w, h - int(h * 0.62), (24, 40, 60))
    # ship hull
    hx, hy = x + int(w * 0.16), y + int(h * 0.66)
    fill_poly([(hx, hy + 18), (hx + int(w * 0.5), hy + 18), (hx + int(w * 0.46), hy + 6), (hx + 4, hy + 6)], (60, 62, 66))
    fill_rect(hx + 8, hy - 8, int(w * 0.3), 14, (90, 92, 96))
    fill_rect(hx + int(w * 0.36), hy - 18, 6, 12, (120, 122, 126))
    # fire
    fx = hx + int(w * 0.18)
    fill_poly([(fx, hy - 2), (fx + 10, hy - 22), (fx + 18, hy - 2)], (234, 120, 30))
    fill_poly([(fx + 5, hy - 2), (fx + 10, hy - 14), (fx + 14, hy - 2)], (250, 190, 70))
    for k in range(3):
        fill_circle(fx + 8 + k * 6, hy - 30 - k * 8, 7 - k, (60, 56, 52))
    # drones + dashed trails
    for k in range(4):
        dx = x + int(w * (0.62 + 0.08 * k)); dy = y + int(h * (0.2 + 0.06 * ((k * 7) % 3)))
        fill_circle(dx, dy, 2, (220, 200, 160))
        for s in range(4):
            fill_rect(dx - 8 - s * 6, dy, 3, 1, (90, 96, 110))
    # moon
    fill_circle(x + int(w * 0.9), y + int(h * 0.16), 8, (230, 226, 210))
    fill_rect(x, y, w, 16, RED2)
    draw_text(buf, x + 26, y + 12, "SHIP SUNK", "anb", 9, WHITE)

def scene_chart(x, y, w, h):
    fill_rect(x, y, w, h, (246, 240, 224))
    stroke_rect(x + 1, y + 1, w - 2, h - 2, RULE2)
    fill_rect(x, y, w, 16, NAVY)
    draw_text(buf, x + 26, y + 12, "KOSPI", "anb", 9, WHITE)
    draw_text_r(buf, x + w - 6, y + 12, "-3.4%", "anb", 9, (255, 130, 110))
    # grid
    for k in range(1, 5):
        hline(x + 8, x + w - 8, y + 16 + int((h - 24) * k / 5), RULE)
    # falling line
    pts = [(0.06, 0.30), (0.18, 0.34), (0.30, 0.28), (0.42, 0.44), (0.52, 0.40), (0.66, 0.62), (0.80, 0.56), (0.92, 0.80)]
    for i in range(len(pts) - 1):
        x0 = x + int(w * pts[i][0]); yy0 = y + int(h * pts[i][1])
        x1 = x + int(w * pts[i + 1][0]); yy1 = y + int(h * pts[i + 1][1])
        line(x0, yy0, x1, yy1, (180, 40, 40), 2)
        fill_circle(x0, yy0, 2, (180, 40, 40))
    # arrow
    ax = x + int(w * 0.92); ay = y + int(h * 0.80)
    fill_poly([(ax, ay + 10), (ax - 8, ay - 4), (ax - 3, ay - 4), (ax - 3, ay - 16), (ax + 3, ay - 16), (ax + 3, ay - 4), (ax + 8, ay - 4)], (180, 40, 40))

def scene_capitol(x, y, w, h):
    fill_rect(x, y, w, h, (222, 228, 232))
    fill_rect(x, y + int(h * 0.72), w, h - int(h * 0.72), (188, 196, 190))
    bx = x + int(w * 0.32); by = y + int(h * 0.42)
    fill_rect(bx, by, int(w * 0.36), int(h * 0.34), WHITE)
    fill_rect(bx + 4, by - 4, int(w * 0.36) - 8, 4, (208, 210, 212))
    fill_circle(bx + int(w * 0.18), by - 12, 12, WHITE)
    fill_rect(bx + int(w * 0.18) - 12, by - 12, 24, 4, (208, 210, 212))
    for k in range(5):
        vline(bx + 6 + k * int(w * 0.07), by + 4, by + int(h * 0.32), (170, 178, 182), 2)
    fill_rect(x, y, w, 16, (32, 74, 168))
    draw_text(buf, x + 26, y + 12, "258 SEATS", "anb", 9, WHITE)

def scene_village(x, y, w, h):
    fill_rect(x, y, w, h, (86, 92, 70))
    fill_rect(x, y + int(h * 0.66), w, h - int(h * 0.66), (110, 116, 88))
    for k in range(3):
        hx = x + int(w * (0.12 + 0.3 * k)); hy = y + int(h * 0.66)
        fill_rect(hx, hy - 18, int(w * 0.2), 18, (214, 200, 172))
        fill_poly([(hx - 3, hy - 18), (hx + int(w * 0.2) + 3, hy - 18), (hx + int(w * 0.1), hy - 30)], (150, 82, 62))
        fill_rect(hx + int(w * 0.08), hy - 12, 6, 8, (90, 70, 50))
    fill_rect(x, y, w, 16, RED2)
    draw_text(buf, x + 26, y + 12, "VILLAGES HIT", "anb", 9, WHITE)

def scene_tent(x, y, w, h):
    fill_rect(x, y, w, h, (236, 224, 196))
    fill_rect(x, y + int(h * 0.7), w, h - int(h * 0.7), (140, 128, 96))
    tx = x + int(w * 0.28); ty = y + int(h * 0.7)
    fill_poly([(tx, ty), (tx + int(w * 0.44), ty), (tx + int(w * 0.22), ty - int(h * 0.5))], WHITE)
    fill_rect(tx + int(w * 0.20), ty - 12, 6, 12, (120, 40, 36))
    fill_rect(x + int(w * 0.8) - 8, ty - int(h * 0.3), 16, 16, WHITE)
    fill_rect(x + int(w * 0.8) - 2, ty - int(h * 0.3) + 6, 4, 4, RED)
    fill_rect(x + int(w * 0.8) - 6, ty - int(h * 0.3) + 2, 12, 4, RED)
    fill_rect(x, y, w, 16, (186, 44, 40))
    draw_text(buf, x + 26, y + 12, "OUTBREAK ZONE", "anb", 9, WHITE)

def scene_rack(x, y, w, h):
    fill_rect(x, y, w, h, (32, 36, 44))
    for k in range(4):
        ry = y + int(h * 0.18) + k * int(h * 0.2)
        fill_rect(x + int(w * 0.2), ry, int(w * 0.6), int(h * 0.14), (58, 64, 76))
        for d in range(5):
            fill_circle(x + int(w * 0.26) + d * int(w * 0.1), ry + int(h * 0.07), 2, (90, 200, 120) if (k + d) % 3 else (220, 170, 60))
    fill_rect(x, y, w, 16, (120, 58, 158))
    draw_text(buf, x + 26, y + 12, "120 MEETINGS", "anb", 9, WHITE)

def scene_hospital(x, y, w, h):
    fill_rect(x, y, w, h, (228, 232, 228))
    fill_rect(x, y + int(h * 0.78), w, h - int(h * 0.78), (176, 182, 176))
    fill_rect(x + int(w * 0.2), y + int(h * 0.3), int(w * 0.6), int(h * 0.48), WHITE)
    fill_rect(x + int(w * 0.2), y + int(h * 0.24), int(w * 0.6), 6, (196, 200, 198))
    cx = x + int(w * 0.5); cy = y + int(h * 0.5)
    fill_rect(cx - 4, cy - 14, 8, 28, RED)
    fill_rect(cx - 14, cy - 4, 28, 8, RED)
    for k in range(4):
        fill_rect(x + int(w * (0.26 + 0.13 * k)), y + int(h * 0.36), 8, int(h * 0.4), (208, 214, 212))
    fill_rect(x, y, w, 16, (15, 106, 128))
    draw_text(buf, x + 26, y + 12, "CUTS", "anb", 9, WHITE)

def scene_fire(x, y, w, h):
    fill_rect(x, y, w, h, (40, 34, 30))
    fill_rect(x, y + int(h * 0.72), w, h - int(h * 0.72), (60, 52, 44))
    fill_rect(x + int(w * 0.14), y + int(h * 0.4), int(w * 0.5), int(h * 0.32), (92, 74, 58))
    fill_rect(x + int(w * 0.14), y + int(h * 0.34), int(w * 0.5), 6, (70, 56, 44))
    fill_rect(x + int(w * 0.55), y + int(h * 0.22), 8, int(h * 0.5), (70, 56, 44))
    for k in range(3):
        fx = x + int(w * (0.24 + 0.14 * k))
        fill_poly([(fx, y + int(h * 0.66)), (fx + 9, y + int(h * 0.38)), (fx + 18, y + int(h * 0.66))], (230, 120, 32))
        fill_poly([(fx + 5, y + int(h * 0.66)), (fx + 9, y + int(h * 0.5)), (fx + 13, y + int(h * 0.66))], (250, 190, 70))
    for k in range(3):
        fill_circle(x + int(w * 0.34) + k * 10, y + int(h * 0.28) - k * 6, 8 - k, (70, 62, 56))
    fill_rect(x, y, w, 16, RED2)
    draw_text(buf, x + 26, y + 12, "3 DEAD, 36 MISSING", "anb", 8, WHITE)

def scene_coin(x, y, w, h):
    fill_rect(x, y, w, h, (34, 30, 42))
    fill_circle(x + int(w * 0.5), y + int(h * 0.6), int(h * 0.32), (222, 168, 62))
    ring = int(h * 0.32)
    fill_circle(x + int(w * 0.5), y + int(h * 0.6), ring - 5, (200, 146, 48))
    draw_text_c(buf, x + w / 2, y + int(h * 0.68), "$", "gsb", 24, (255, 238, 200))
    for k in range(5):
        fx = x + int(w * (0.1 + 0.2 * k))
        fill_circle(fx, y + int(h * 0.18), 3, (240, 210, 140))
    fill_rect(x, y, w, 16, (150, 96, 16))
    draw_text(buf, x + 26, y + 12, "TOP HOLDERS DINE", "anb", 9, WHITE)

def scene_tennis(x, y, w, h):
    fill_rect(x, y, w, h, (40, 92, 60))
    stroke_rect(x + int(w * 0.12), y + int(h * 0.2), int(w * 0.76), int(h * 0.62), (230, 230, 224), 2)
    vline(x + int(w * 0.5), y + int(h * 0.2), y + int(h * 0.82), (230, 230, 224), 2)
    fill_circle(x + int(w * 0.68), y + int(h * 0.34), 3, (230, 220, 90))
    fill_rect(x, y, w, 16, (18, 98, 62))
    draw_text(buf, x + 26, y + 12, "FIRST TITLE", "anb", 9, WHITE)

def scene_pitch(x, y, w, h):
    fill_rect(x, y, w, h, (30, 110, 66))
    stroke_rect(x + int(w * 0.1), y + int(h * 0.24), int(w * 0.8), int(h * 0.56), (226, 232, 224), 2)
    vline(x + int(w * 0.5), y + int(h * 0.24), y + int(h * 0.8), (226, 232, 224), 2)
    fill_circle(x + int(w * 0.5), y + int(h * 0.52), 5, (226, 232, 224))
    fill_rect(x, y, w, 16, RED2)
    draw_text(buf, x + 26, y + 12, "4-0", "anb", 10, WHITE)

def scene_tanker(x, y, w, h):
    fill_rect(x, y, w, h, (26, 34, 48))
    fill_rect(x, y + int(h * 0.6), w, h - int(h * 0.6), (36, 52, 68))
    hx = x + int(w * 0.1); hy = y + int(h * 0.68)
    fill_rect(hx, hy - 10, int(w * 0.42), 10, (72, 74, 80))
    fill_circle(hx + int(w * 0.42) - 4, hy - 5, 5, (72, 74, 80))
    for k in range(3):
        fill_circle(hx + 10 + k * 14, hy - 13, 4, (60, 62, 68))
    fx = hx + int(w * 0.2)
    fill_poly([(fx, hy - 4), (fx + 8, hy - 24), (fx + 16, hy - 4)], (234, 120, 30))
    fill_poly([(fx + 4, hy - 4), (fx + 8, hy - 15), (fx + 12, hy - 4)], (250, 190, 70))
    fill_rect(x, y, w, 16, RED2)
    draw_text(buf, x + 26, y + 12, "TANKERS HIT", "anb", 9, WHITE)

def scene_drone(x, y, w, h):
    fill_rect(x, y, w, h, (52, 44, 36))
    fill_rect(x, y + int(h * 0.68), w, h - int(h * 0.68), (74, 60, 46))
    for k in range(3):
        bx = x + int(w * (0.15 + 0.28 * k))
        fill_rect(bx, y + int(h * 0.5), int(w * 0.2), int(h * 0.18), (96, 82, 64))
        fill_poly([(bx - 2, y + int(h * 0.5)), (bx + int(w * 0.2) + 2, y + int(h * 0.5)), (bx + int(w * 0.1), y + int(h * 0.4))], (70, 58, 44))
    for k in range(4):
        dx = x + int(w * (0.55 + 0.1 * k)); dy = y + int(h * (0.22 + 0.05 * (k % 3)))
        fill_circle(dx, dy, 2, (210, 190, 150))
    fill_rect(x, y, w, 16, RED2)
    draw_text(buf, x + 26, y + 12, "STRIKES", "anb", 9, WHITE)

def scene_mic(x, y, w, h):
    fill_rect(x, y, w, h, (24, 24, 32))
    fill_circle(x + int(w * 0.5), y + int(h * 0.42), int(h * 0.16), (200, 202, 210))
    fill_rect(x + int(w * 0.5) - int(h * 0.16) - 2, y + int(h * 0.42), int(h * 0.32) + 4, 3, (200, 202, 210))
    fill_rect(x + int(w * 0.5) - 3, y + int(h * 0.42), 6, int(h * 0.3), (150, 152, 160))
    fill_rect(x + int(w * 0.5) - int(h * 0.2), y + int(h * 0.72), int(h * 0.4), 5, (150, 152, 160))
    for k in range(6):
        fill_circle(x + int(w * (0.12 + 0.15 * k)), y + int(h * 0.86), 2, (120, 122, 132))
    fill_rect(x, y, w, 16, (120, 58, 158))
    draw_text(buf, x + 26, y + 12, "AGE 83", "anb", 9, WHITE)

SCENES = {
    "cop31": scene_cop31, "ship": scene_ship, "chart": scene_chart,
    "capitol": scene_capitol, "village": scene_village, "tent": scene_tent,
    "rack": scene_rack, "hospital": scene_hospital, "fire": scene_fire,
    "coin": scene_coin, "tennis": scene_tennis, "pitch": scene_pitch,
    "tanker": scene_tanker, "drone": scene_drone, "mic": scene_mic,
}

# ------------------------------------------------------------------ map
MAPX, MAPY, MAPW = 24, 760, 300
def lonlat_to_map(lon, lat):
    px = MAPX + int((lon + 180) / 360 * MAPW)
    py = MAPY + int((84 - lat) / 142 * (MAPW / 2))
    return px, py

def draw_map():
    draw_text(buf, MAPX, MAPY - 22, "WHERE IT HAPPENED", "anb", 10, INK, 0.6)
    draw_text_r(buf, MAPX + MAPW, MAPY - 22, "pins = story numbers", "an", 8, MUT)
    for y in range(128):
        for x in range(256):
            if A.land[y * 256 + x]:
                mx = MAPX + x * MAPW / 256
                my = MAPY + y * (MAPW / 2) / 128
                fill_rect(int(mx), int(my), 2, 2, (196, 188, 166))
    for (lon, lat, n) in PINS:
        mx, my = lonlat_to_map(lon, lat)
        fill_circle(mx, my + 4, 6, RED)
        draw_text_c(buf, mx, my + 7, str(n), "anb", 8, WHITE)

# ------------------------------------------------------------------ poster
def header():
    blend_rect(0, 0, W, H, PAPER2, 0)
    # kicker
    draw_text(buf, 14, 13, "THE WORLD IN ONE DAY", "anb", 10, RED, 1.2)
    right = "%d STORIES \u00b7 7 REGIONS \u00b7 EVERY ONE DATED MONDAY 23 NOVEMBER 2026" % (3 + len(CARDS) + len(BRIEFS))
    draw_text_r(buf, W - 14, 13, right, "an", 8, INK)
    hline(0, W, 18, INK, 2)
    # masthead
    draw_text_c(buf, W / 2, 86, "Monday 23 November 2026", "ggb", 64, INK)
    # deck
    draw_text_c(buf, W / 2, 110, DECK, "gsi", 14, RED2)
    hline(14, W - 14, 118, INK, 1)

def statband(y):
    n = len(STATS)
    colw = (W - 28) / n
    for i, (num, cap) in enumerate(STATS):
        cx = 14 + i * colw
        if i:
            vline(int(cx), y + 2, y + 38, RULE2, 1)
        draw_text(buf, int(cx + 8), y + 20, num, "gsb", 22, RED)
        for j, ln in enumerate(wrap(cap, "an", 8, colw - 22)[:2]):
            draw_text(buf, int(cx + 8), y + 31 + j * 9, ln, "an", 8, MUT)
    hline(14, W - 14, y + 42, RULE2, 1)

def timeline(y):
    fill_rect(14, y, W - 28, 18, NAVY)
    fill_rect(14, y, 96, 18, RED)
    draw_text(buf, 20, y + 12, "THE DAY IN UTC", "anb", 9, WHITE)
    x = 120
    for (t, txt) in TIMELINE:
        draw_text(buf, x, y + 12, t, "anb", 9, GOLD)
        w = measure(t, "anb", 9) + 5
        wtxt = measure(txt, "an", 8, 0) + 14
        if x + w + wtxt > W - 20:
            break
        draw_text(buf, int(x + w), y + 12, txt, "an", 8, (222, 226, 232))
        x += w + wtxt
        if x < W - 100:
            draw_text(buf, int(x - 7), y + 12, "\u00b7", "anb", 9, (90, 106, 134))

def regionband(y):
    counts = {}
    order = ["EUROPE", "MIDEAST", "AMERICAS", "ASIA", "AFRICA", "OCEANIA", "GLOBAL"]
    for st in HEROES + CARDS:
        r = st["region"]
        counts[r] = counts.get(r, 0) + 1
    total = sum(counts.values())
    x = 14
    avail = W - 28
    for r in order:
        c = counts.get(r, 0)
        if not c:
            continue
        w = int(avail * c / total)
        fill_rect(x, y, w, 16, REGION[r])
        draw_text(buf, x + 26, y + 12, "%s %d" % (r.title() if r != "MIDEAST" else "Mid East", c), "anb", 9, WHITE)
        x += w

def heroes(y):
    n = len(HEROES)
    gap = 10
    cw = (W - 28 - gap * (n - 1)) / n
    for i, st in enumerate(HEROES):
        x = 14 + i * (cw + gap)
        # scene
        SCENES[st["scene"]](int(x), y, int(cw), 80)
        # number chip
        fill_circle(x + 10, y + 10, 9, INK)
        draw_text_c(buf, x + 10, y + 13, str(st["n"]), "anb", 9, WHITE)
        # location line
        col = REGION[st["region"]]
        ly = y + 90
        draw_text(buf, int(x), ly, st["place"], "anb", 9, col, 0.4)
        pw = measure(st["place"], "anb", 9, 0.4)
        draw_text(buf, int(x + pw + 8), ly, "\u00b7 " + st["topic"], "an", 8, MUT)
        draw_text_r(buf, int(x + cw), ly, st["src"], "an", 8, MUT)
        hline(int(x), int(x + cw), ly + 4, RULE2, 1)
        # headline
        hy = ly + 16
        hls = wrap(st["head"], "gsb", 21, cw - 2)[:2]
        for j, ln in enumerate(hls):
            draw_text(buf, int(x), hy + j * 23, ln, "gsb", 20, INK)
        # body
        byy = hy + 23 * len(hls) + 8
        bls = wrap(st["body"], "gg", 10, cw - 4)[:3]
        for j, ln in enumerate(bls):
            draw_text(buf, int(x), byy + j * 12, ln, "gg", 10, (44, 40, 34))
        if i:
            vline(int(x - gap / 2), y, y + 184, RULE2, 1)
    hline(14, W - 14, y + 192, RULE2, 1)

def cards(y):
    n = len(CARDS)
    per_row = 6
    gap = 8
    cw = (W - 28 - gap * (per_row - 1)) / per_row
    for i, st in enumerate(CARDS):
        row = i // per_row
        col = i % per_row
        x = 14 + col * (cw + gap)
        yy = y + row * 160
        fill_rect(int(x), int(yy), int(cw), 154, PAPER2)
        stroke_rect(int(x), int(yy), int(cw), 154, RULE2, 1)
        SCENES[st["scene"]](int(x), int(yy), int(cw), 42)
        fill_circle(x + 10, yy + 10, 8, INK)
        draw_text_c(buf, x + 10, yy + 13, str(st["n"]), "anb", 8, WHITE)
        # region+topic line
        col_c = REGION[st["region"]]
        draw_text(buf, int(x + 3), int(yy + 54), st["place"], "anb", 8, col_c)
        draw_text(buf, int(x + 3), int(yy + 63), st["topic"], "an", 8, MUT)
        # headline
        hy = yy + 77
        hls = wrap(st["head"], "gsb", 12.5, cw - 6)[:3]
        for j, ln in enumerate(hls):
            draw_text(buf, int(x + 3), hy + j * 14, ln, "gsb", 13, INK)
        # body
        byy = hy + 14 * len(hls) + 3
        for j, ln in enumerate(wrap(st["body"], "an", 8, cw - 6)[:2]):
            draw_text(buf, int(x + 3), byy + j * 10, ln, "an", 8, (70, 64, 54))
        draw_text_r(buf, int(x + cw - 4), int(yy + 149), st["src"], "an", 8, MUT)

def briefs(x, y, w):
    draw_text(buf, x, y, "ALSO ON MONDAY 23 NOVEMBER", "anb", 10, INK, 0.6)
    draw_text_r(buf, x + w, y, "\u2014 %d MORE STORIES" % len(BRIEFS), "anb", 9, RED)
    y0 = y + 14
    cols = 2
    colw = (w - 16) / cols
    per = (len(BRIEFS) + 1) // cols
    for i, (place, reg, text, src) in enumerate(BRIEFS):
        c = i // per
        r = i % per
        cx = x + c * (colw + 16)
        yy = y0 + r * 15
        if yy > 940:
            break
        n = 16 + i
        draw_text(buf, int(cx), int(yy), str(n), "anb", 8, RED)
        nw = measure(str(n), "anb", 8) + 3
        draw_text(buf, int(cx + nw), int(yy), place, "anb", 8, INK)
        pw = measure(place, "anb", 8) + 4
        # one line: text + source, clipped to column
        tx = cx + nw + pw
        avail = colw - (nw + pw) - measure(" (%s)" % src, "an", 8)
        t = text
        while t and measure(t, "an", 8) > avail:
            t = t[:-1]
        if t != text:
            t = t.rstrip(" ,;:") + "\u2026"
        draw_text(buf, int(tx), int(yy), t, "an", 8, (52, 48, 42))
        draw_text_r(buf, int(cx + colw), int(yy), "(%s)" % src, "an", 8, MUT)

def datecheck(y):
    h = 56
    blend_rect(14, y, W - 28, h, RED, 14)
    stroke_rect(14, y, W - 28, h, RED, 1)
    fill_rect(14, y, 66, 13, RED)
    draw_text(buf, 20, y + 10, "DATE CHECK", "anb", 8, WHITE)
    draw_text(buf, 88, y + 10, "Every story above happened, or was first reported, on Monday 23 November in at least one time zone. Left out \u2014 not Monday's news:", "an", 8, (90, 30, 26))
    colw = (W - 28 - 8) / 2
    for i, (day, txt) in enumerate(DATECHECK):
        cx = 22 + (i % 2) * colw
        yy = y + 26 + (i // 2) * 14
        draw_text(buf, int(cx), int(yy), day, "anb", 8, RED2)
        dw = measure(day, "anb", 8) + 5
        t = txt
        while t and measure(t, "an", 8) > colw - dw - 10:
            t = t[:-1]
        if t != txt:
            t = t.rstrip(" ,;:") + "\u2026"
        draw_text(buf, int(cx + dw), int(yy), t, "an", 8, (70, 40, 34))

def footer(y):
    hline(14, W - 14, y, INK, 1)
    draw_text(buf, 14, y + 9, "Sources: Reuters \u00b7 AP \u00b7 BBC \u00b7 Al Jazeera \u00b7 The Guardian \u00b7 Times of Israel \u00b7 Yonhap \u00b7 ABC \u00b7 Sky", "an", 8, MUT)
    draw_text_r(buf, W - 14, y + 9, "Sources read to " + PRESS, "an", 8, MUT)

def legend(y):
    # tiny certainty legend above date check
    x = 14
    for (lab, col) in [("CONFIRMED", (24, 98, 58)), ("REPORTED", (72, 76, 86)), ("DEVELOPING", (172, 74, 26))]:
        w = measure(lab, "anb", 8) + 10
        fill_rect(x, y, w, 12, col)
        draw_text(buf, x + 5, y + 9, lab, "anb", 8, WHITE)
        x += w + 8
    draw_text(buf, x + 4, y + 9, "= carried by the day's wires; times are UTC; pictures drawn in code", "an", 8, MUT)

def poster():
    header()
    statband(124)
    timeline(170)
    regionband(194)
    heroes(216)
    cards(414)
    draw_map()
    briefs(MAPX + MAPW + 24, MAPY - 22, W - (MAPX + MAPW + 24) - 14)
    legend(944)
    datecheck(962)
    footer(1014)

def save(path):
    # PNG: 8-bit RGB, adaptive row filters
    stride = W * 3
    rows = bytearray()
    prev = bytearray(stride)
    for y in range(H):
        cur = buf[y * stride:(y + 1) * stride]
        best = None
        bestscore = None
        for f in (0, 1, 2, 3, 4):
            cand = bytearray(stride + 1)
            cand[0] = f
            if f == 0:
                cand[1:] = cur
            elif f == 1:
                for i in range(stride):
                    a = cur[i - 3] if i >= 3 else 0
                    cand[i + 1] = (cur[i] - a) & 0xFF
            elif f == 2:
                for i in range(stride):
                    cand[i + 1] = (cur[i] - prev[i]) & 0xFF
            elif f == 3:
                for i in range(stride):
                    a = cur[i - 3] if i >= 3 else 0
                    b = prev[i]
                    cand[i + 1] = (cur[i] - ((a + b) >> 1)) & 0xFF
            else:
                for i in range(stride):
                    a = cur[i - 3] if i >= 3 else 0
                    b = prev[i]
                    c = prev[i - 3] if i >= 3 else 0
                    pa = abs(b - c); pb = abs(a - c); pc = abs(a + b - 2 * c)
                    pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                    cand[i + 1] = (cur[i] - pr) & 0xFF
            score = sum(cand[1:400])
            if bestscore is None or score < bestscore:
                bestscore = score
                best = cand
        rows += best
        prev = cur
    raw = bytes(rows)
    idat = zlib.compress(raw, 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)

def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    poster()
    path = os.path.join(out, "entry.png")
    n = save(path)
    print("wrote", path, n, "bytes")

if __name__ == "__main__":
    main()
