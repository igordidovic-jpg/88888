# ============================================================
# CFOS-XG PRO 75 TITAN
# ZAČETEK DELA 1 / 8
# OSNOVA SISTEMA
# ============================================================

import math
import random
import os
import time
import csv
from io import StringIO

# ------------------------------------------------------------
# NASTAVITVE
# ------------------------------------------------------------
SIM_BASE = 40000
SIM_HIGH = 90000
SIM_EXTREME = 140000

SIM_EXACT_BASE = 25000
SIM_EXACT_HIGH = 60000

LEARN_FILE = "cfos75_learn_log.csv"
SNAP_FILE = "cfos75_snapshots_pending.csv"
MATCH_MEM_FILE = "cfos75_match_memory.csv"


# ------------------------------------------------------------
# ANSI / BARVE
# ------------------------------------------------------------
def init_ansi():
    if os.name == "nt":
        try:
            os.system("")  # 🔥 KLJUČNO za Windows CMD
            return True
        except:
            return False
    return True


ANSI_ON = init_ansi()

BOLD = "\033[1m" if ANSI_ON else ""
RESET = "\033[0m" if ANSI_ON else ""

RED = "\033[91m" if ANSI_ON else ""
GREEN = "\033[92m" if ANSI_ON else ""
YELLOW = "\033[93m" if ANSI_ON else ""
BLUE = "\033[94m" if ANSI_ON else ""
MAGENTA = "\033[95m" if ANSI_ON else ""
CYAN = "\033[96m" if ANSI_ON else ""
WHITE = "\033[97m" if ANSI_ON else ""
ORANGE = "\033[33m" if ANSI_ON else ""

# =========================
# CUSTOM SEKCIJSKE BARVE
# =========================
COL_XG = GREEN
COL_PM = YELLOW
COL_LAMBDA = CYAN
COL_MC = MAGENTA

COL_TEMPO = YELLOW
COL_NEXT = GREEN
COL_MOM = YELLOW
COL_PRESS = YELLOW


def btxt(text, color="", bold=False):
    if not ANSI_ON:
        return str(text)
    return f"{BOLD if bold else ''}{color}{text}{RESET}"


def cl(label, value, color="", bold=False):
    if not ANSI_ON:
        return f"{label.ljust(28)} {value}"
    return f"{btxt(label.ljust(28), color, bold)} {btxt(str(value), color, bold)}"


# ------------------------------------------------------------
# POMOŽNE FUNKCIJE
# ------------------------------------------------------------
def pct(x):
    return round(x * 100, 2)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def safe_float(x, default=0.0):
    try:
        return float(str(x).replace(",", "."))
    except:
        return default


def safe_int(x, default=0):
    try:
        return int(float(str(x).replace(",", ".")))
    except:
        return default


def safe_div(a, b, default=0.0):
    if b == 0:
        return default
    return a / b


def get_idx(data, i, default="0"):
    return data[i] if i < len(data) else default


def get_num(data, i, default=0.0):
    return safe_float(get_idx(data, i, str(default)), default)


def parse_csv_line(line):
    try:
        reader = csv.reader(StringIO(line))
        row = next(reader)
        return [x.strip() for x in row]
    except:
        return [x.strip() for x in line.split(",")]


def file_has_data(path):
    return os.path.exists(path) and os.path.getsize(path) > 0


def fmt2(x):
    return round(float(x), 2)


def fmt3(x):
    return round(float(x), 3)


def fmt4(x):
    return round(float(x), 4)


def blend(base, factor, weight=0.35):
    return base * (1 + (factor - 1.0) * weight)


# ------------------------------------------------------------
# BARVNA LOGIKA
# ------------------------------------------------------------
def color_prob(p):
    if p >= 0.65:
        return GREEN
    if p >= 0.45:
        return YELLOW
    return RED


def color_edge(edge):
    if edge >= 0.05:
        return GREEN
    if edge <= -0.05:
        return RED
    return YELLOW


def color_conf(conf):
    if conf >= 70:
        return GREEN
    if conf >= 45:
        return YELLOW
    return RED


def confidence_band(conf):
    if conf >= 70:
        return "VISOKA"
    if conf >= 45:
        return "SREDNJA"
    return "NIZKA"


# ------------------------------------------------------------
# BUCKETI
# ------------------------------------------------------------
def bucket_minute(m):
    if m < 30:
        return "0-29"
    if m < 60:
        return "30-59"
    if m < 76:
        return "60-75"
    return "76-90"


def bucket_xg(x):
    if x < 0.7:
        return "low"
    if x < 1.4:
        return "mid"
    return "high"


def bucket_sot(s):
    if s <= 3:
        return "low"
    return "high"


def bucket_shots(s):
    if s <= 7:
        return "low"
    if s <= 13:
        return "mid"
    return "high"


def bucket_score_diff(sd):
    if sd <= -2:
        return "-2-"
    if sd == -1:
        return "-1"
    if sd == 0:
        return "0"
    if sd == 1:
        return "+1"
    return "+2+"


def bucket_danger(d):
    if d < 45:
        return "low"
    if d < 90:
        return "mid"
    return "high"


# ------------------------------------------------------------
# PREVODI / METRIKE
# ------------------------------------------------------------
def game_type_slo(gt):
    mapping = {
        "DEAD": "MRTVA IGRA",
        "SLOW": "POČASNA IGRA",
        "BALANCED": "URAVNOTEŽENA IGRA",
        "PRESSURE": "PRITISK",
        "ATTACK_WAVE": "NAPADNI VAL",
        "CHAOS": "KAOS"
    }
    return mapping.get(gt, gt)


def pass_acc_rate(accurate, passes):
    return safe_div(accurate, passes, 0.0)


def danger_to_shot_conv(shots, danger):
    return safe_div(shots, danger, 0.0)


def shot_quality(xg, shots):
    return safe_div(xg, shots, 0.0)


def sot_ratio(sot, shots):
    return safe_div(sot, shots, 0.0)


def big_chance_ratio(big_chances, shots):
    return safe_div(big_chances, shots, 0.0)


# ============================================================
# KONEC DELA 1 / 8
# ============================================================
# ============================================================
# CFOS-XG PRO 75 TITAN
# ZAČETEK DELA 2 / 8
# POISSON / TEMPO / MARKET HELPERJI
# ============================================================

def poisson_sample(lam):
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L and k < 12:
        k += 1
        p *= random.random()
    return k - 1


def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    try:
        return math.exp(-lam) * (lam ** k) / math.factorial(k)
    except:
        return 0.0


def bivariate_poisson_sample(lam_h, lam_a, lam_c):
    shared = poisson_sample(clamp(lam_c, 0, 0.08))
    gh = poisson_sample(max(0.0, lam_h))
    ga = poisson_sample(max(0.0, lam_a))
    return gh + shared, ga + shared


def classify_game_type(minute, xg_total, shots_total, sot_total, danger_total, tempo_shots, xg_rate):
    if (
            shots_total <= 4 and
            xg_total <= 0.35 and
            danger_total <= 12 and
            tempo_shots < 0.18 and
            xg_rate < 0.015
    ):
        return "DEAD"

    if shots_total <= 9 and xg_total <= 0.90 and tempo_shots < 0.16:
        return "SLOW"

    if shots_total >= 14 and sot_total >= 6 and danger_total >= 90:
        return "ATTACK_WAVE"

    if shots_total >= 10 and danger_total >= 70 and xg_rate >= 0.020:
        return "PRESSURE"

    if (xg_total >= 2.10) or (shots_total >= 18 and sot_total >= 7 and danger_total >= 60):
        return "CHAOS"

    return "BALANCED"


def game_type_goal_multiplier(game_type):
    if game_type == "DEAD":
        return 0.78
    if game_type == "SLOW":
        return 0.90
    if game_type == "PRESSURE":
        return 1.05
    if game_type == "ATTACK_WAVE":
        return 1.11
    if game_type == "CHAOS":
        return 1.10
    return 1.00


def estimate_effective_end_minute(minute):
    if minute >= 90:
        return 97
    return 95


def estimate_minutes_left(minute):
    return max(1, estimate_effective_end_minute(minute) - minute)


def time_left_fraction(minute):
    ml = estimate_minutes_left(minute)
    return max(0.01, ml / 90.0), ml


def tempo_goal_multiplier(tempo_shots, tempo_danger, tempo_att, minute):
    notes = []
    mult = 1.0

    if tempo_shots >= 0.22:
        mult *= 1.04
        notes.append("TEMPO shots_high")
    if tempo_shots >= 0.30:
        mult *= 1.03

    if tempo_danger >= 1.10:
        mult *= 1.04
        notes.append("TEMPO danger_high")

    if tempo_att >= 2.20:
        mult *= 1.02
        notes.append("TEMPO attacks_high")

    if tempo_shots < 0.12 and tempo_danger < 0.75 and minute >= 55:
        mult *= 0.90
        notes.append("TEMPO low")

    return clamp(mult, 0.84, 1.14), notes


def xgr_goal_multiplier(xg_rate_total, minute):
    notes = []
    mult = 1.0

    if xg_rate_total >= 0.020:
        mult *= 1.05
        notes.append("XGR hot")
    if xg_rate_total >= 0.030:
        mult *= 1.03
    if 0 < xg_rate_total < 0.010 and minute >= 50:
        mult *= 0.91
        notes.append("XGR low")

    return clamp(mult, 0.86, 1.12), notes


def implied_probs_from_odds(odds_home, odds_draw, odds_away):
    if odds_home <= 0 or odds_draw <= 0 or odds_away <= 0:
        return 0.0, 0.0, 0.0, 0.0

    raw_h = 1 / odds_home
    raw_x = 1 / odds_draw
    raw_a = 1 / odds_away

    s = raw_h + raw_x + raw_a
    if s <= 0:
        return 0.0, 0.0, 0.0, 0.0

    return raw_h / s, raw_x / s, raw_a / s, s - 1.0


def edge_from_model(model_p, market_p):
    return model_p - market_p


def adaptive_simulations(pre_h, pre_x, pre_a):
    best = max(pre_h, pre_x, pre_a)

    if best < 0.42:
        return SIM_EXTREME
    if best < 0.55:
        return SIM_HIGH
    return SIM_BASE


def adaptive_exact_simulations(best_1x2):
    if best_1x2 < 0.45:
        return SIM_EXACT_HIGH
    return SIM_EXACT_BASE


def next_goal_signal(p_home_next, p_away_next):
    if p_home_next >= 0.45 and p_home_next > p_away_next:
        return "NASLEDNJI GOL -> DOMAČI PRITISK"
    if p_away_next >= 0.45 and p_away_next > p_home_next:
        return "NASLEDNJI GOL -> GOSTUJOČI PRITISK"
    return "NASLEDNJI GOL -> URAVNOTEŽENO / NEGOTOVO"


def match_signal(p_goal, p_home_next, p_away_next):
    if p_goal < 0.25:
        return "NIZEK GOL | NASLEDNJI GOL URAVNOTEŽENO"
    if p_goal >= 0.55:
        return "VISOK GOL | ODPRTA TEKMA"
    if p_home_next > p_away_next and p_home_next >= 0.35:
        return "SREDNJI GOL | NASLEDNJI GOL DOMA"
    if p_away_next > p_home_next and p_away_next >= 0.35:
        return "SREDNJI GOL | NASLEDNJI GOL GOST"
    return "SREDNJI GOL | NASLEDNJI GOL URAVNOTEŽENO"


def confidence_score_base(p_goal, mc_h, mc_x, mc_a, timeline_n):
    best_1x2 = max(mc_h, mc_x, mc_a)

    conf = 24.0

    conf += best_1x2 * 45.0
    conf += abs(mc_h - mc_a) * 18.0
    conf += p_goal * 10.0

    if timeline_n >= 2:
        conf += 6.0
    if timeline_n >= 3:
        conf += 4.0

    return clamp(conf, 1.0, 100.0)


def safe_log(p):
    return math.log(max(1e-9, p))


def softmax3(a, b, c):
    m = max(a, b, c)
    ea = math.exp(a - m)
    eb = math.exp(b - m)
    ec = math.exp(c - m)
    s = ea + eb + ec
    return ea / s, eb / s, ec / s


def closeness(a, b):
    return 1.0 - min(1.0, abs(a - b))


def meta_calibrate_1x2(
        mc_h, mc_x, mc_a,
        imp_h, imp_x, imp_a,
        lam_h, lam_a,
        p_goal,
        momentum,
        pressure_h, pressure_a,
        xg_h, xg_a,
        minute,
        score_diff,
        team_power,
        hist_n
):
    lam_diff = lam_h - lam_a
    xg_diff = xg_h - xg_a
    pressure_diff = pressure_h - pressure_a

    if minute <= 20:
        lam_diff *= 0.55
        xg_diff *= 0.55
        momentum *= 0.55
        team_power *= 0.70

    log_h = safe_log(mc_h)
    log_x = safe_log(mc_x)
    log_a = safe_log(mc_a)

    # lambda
    log_h += lam_diff * 0.22
    log_a -= lam_diff * 0.22

    # xg
    log_h += xg_diff * 0.18
    log_a -= xg_diff * 0.18

    # momentum
    log_h += momentum * 0.16
    log_a -= momentum * 0.16

    # team strength
    log_h += team_power * 0.20
    log_a -= team_power * 0.20

    # pressure
    if pressure_h > pressure_a:
        log_h += min(0.12, (pressure_h - pressure_a) * 0.006)
    elif pressure_a > pressure_h:
        log_a += min(0.12, (pressure_a - pressure_h) * 0.006)

    # draw killer
    if p_goal > 0.55:
        log_x -= 0.15

    if minute > 70 and score_diff != 0:
        log_x -= 0.10

    h, x, a = softmax3(log_h, log_x, log_a)

    h = max(0.03, h)
    x = max(0.06, x)
    a = max(0.03, a)

    s = h + x + a
    if s > 0:
        h /= s
        x /= s
        a /= s

    return h, x, a


# ============================================================
# KONEC DELA 2 / 8
# ============================================================
# ============================================================
# CFOS-XG PRO 75 TITAN
# ZAČETEK DELA 3 / 8
# LEARNING ENGINE
# ============================================================

def load_history():
    rows = []
    if not os.path.exists(LEARN_FILE):
        return rows

    try:
        with open(LEARN_FILE, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return rows

            header0 = header[0].strip().lower() if header else ""

            for parts in reader:
                if not parts or len(parts) < 7:
                    continue

                if header0 == "home":
                    rows.append({
                        "home": parts[0],
                        "away": parts[1],
                        "minute": safe_int(parts[2]),
                        "xg_total": safe_float(parts[3]),
                        "sot_total": safe_float(parts[4]),
                        "shots_total": safe_float(parts[5]),
                        "score_diff": safe_int(parts[6]),
                        "lam_pred": safe_float(parts[10]),
                        "p_goal_pred": safe_float(parts[11]),
                        "mc_h": safe_float(parts[12]) if len(parts) > 12 else 0.0,
                        "mc_x": safe_float(parts[13]) if len(parts) > 13 else 0.0,
                        "mc_a": safe_float(parts[14]) if len(parts) > 14 else 0.0,
                        "final_outcome": parts[15].strip().upper() if len(parts) > 15 else "",
                        "goal_to_end": safe_int(parts[16]) if len(parts) > 16 else 0,
                        "ts": parts[17] if len(parts) > 17 else "",
                        "game_type": parts[18].strip().upper() if len(parts) > 18 else "",
                        "danger_bucket": parts[19].strip().lower() if len(parts) > 19 else "",
                    })
                else:
                    rows.append({
                        "home": "",
                        "away": "",
                        "minute": safe_int(parts[0]),
                        "xg_total": safe_float(parts[1]),
                        "sot_total": safe_float(parts[2]),
                        "shots_total": safe_float(parts[3]),
                        "score_diff": safe_int(parts[4]),
                        "lam_pred": safe_float(parts[5]),
                        "p_goal_pred": safe_float(parts[6]),
                        "mc_h": safe_float(parts[7]),
                        "mc_x": safe_float(parts[8]),
                        "mc_a": safe_float(parts[9]),
                        "final_outcome": parts[10].strip().upper() if len(parts) > 10 else "",
                        "goal_to_end": safe_int(parts[11]) if len(parts) > 11 else 0,
                        "ts": parts[12] if len(parts) > 12 else "",
                        "game_type": "",
                        "danger_bucket": "",
                    })

    except Exception as e:
        print("Napaka v load_history():", e)
        return []

    return rows


def select_subset(history, minute, xg_total, sot_total, shots_total, score_diff, game_type="", danger_total=0):
    if not history:
        return []

    bm = bucket_minute(minute)
    bx = bucket_xg(xg_total)
    bs = bucket_sot(sot_total)
    bsh = bucket_shots(shots_total)
    bd = bucket_score_diff(score_diff)
    bdanger = bucket_danger(danger_total)

    primary = []
    fallback = []

    for r in history:
        score = 0

        # ============================================================
        # STRICT SCORE STATE FILTER (fix DRAW bias)
        # ============================================================

        # če nekdo vodi +1, ne mešaj z 0-0
        if score_diff != 0:
            if r["score_diff"] != score_diff:
                continue

        if bucket_minute(r["minute"]) == bm:
            score += 1
        if bucket_xg(r["xg_total"]) == bx:
            score += 1
        if bucket_sot(r["sot_total"]) == bs:
            score += 1
        if bucket_shots(r["shots_total"]) == bsh:
            score += 1
        if bucket_score_diff(r["score_diff"]) == bd:
            score += 1

        base_ok = score >= 2
        if not base_ok:
            continue

        fallback.append(r)

        gt_ok = True
        if game_type and r.get("game_type"):
            gt_ok = (r["game_type"].upper() == game_type.upper())

        danger_ok = True
        if r.get("danger_bucket", ""):
            danger_ok = (r["danger_bucket"].lower() == bdanger)

        if gt_ok and danger_ok:
            primary.append(r)

    # ============================================================
    # AUTO HISTORY EXPANSION
    # ============================================================

    # strict history
    if len(primary) >= 12:
        return primary

    # fallback history
    if len(fallback) >= 12:
        return fallback

    # ------------------------------------------------------------
    # WIDE HISTORY (ignore sot + shots)
    # ------------------------------------------------------------
    wide = []

    for r in history:

        score = 0

        # ============================================================
        # STRICT SCORE STATE FILTER (fix DRAW bias)
        # ============================================================

        # če nekdo vodi +1, ne mešaj z 0-0
        if score_diff != 0:
            if r["score_diff"] != score_diff:
                continue

        if bucket_minute(r["minute"]) == bm:
            score += 1
        if bucket_xg(r["xg_total"]) == bx:
            score += 1
        if bucket_score_diff(r["score_diff"]) == bd:
            score += 1

        if score >= 2:
            wide.append(r)

    if len(wide) >= 20:
        return wide

    # ------------------------------------------------------------
    # SUPER WIDE (minute only)
    # ------------------------------------------------------------
    last = [r for r in history if bucket_minute(r["minute"]) == bm]

    if len(last) >= 20:
        return last

    # ------------------------------------------------------------
    # GLOBAL fallback
    # ------------------------------------------------------------
    if len(history) >= 30:
        return history

    return []


def learn_factor_goal(history, minute, xg_total, sot_total, shots_total, score_diff, game_type="", danger_total=0):
    subset = select_subset(history, minute, xg_total, sot_total, shots_total, score_diff, game_type, danger_total)
    n = len(subset)
    if n < 4:
        return 1.0, n

    obs = sum(r["goal_to_end"] for r in subset) / n
    pred = sum(r["lam_pred"] for r in subset) / n
    if pred <= 1e-9:
        return 1.0, n

    f = obs / pred
    f = clamp(f, 0.86, 1.15)
    return f, n


def learn_factor_1x2(history, minute, xg_total, sot_total, shots_total, score_diff, game_type="", danger_total=0):
    subset = select_subset(history, minute, xg_total, sot_total, shots_total, score_diff, game_type, danger_total)
    n = len(subset)
    if n < 4:
        return 1.0, 1.0, 1.0, n

    obs_h = sum(1 for r in subset if r["final_outcome"] == "H") / n
    obs_x = sum(1 for r in subset if r["final_outcome"] == "D") / n
    obs_a = sum(1 for r in subset if r["final_outcome"] == "A") / n

    pred_h = sum(r["mc_h"] for r in subset) / n
    pred_x = sum(r["mc_x"] for r in subset) / n
    pred_a = sum(r["mc_a"] for r in subset) / n

    if pred_h < 1e-9 or pred_x < 1e-9 or pred_a < 1e-9:
        return 1.0, 1.0, 1.0, n

    rh = clamp(obs_h / pred_h, 0.80, 1.15)
    rx = clamp(obs_x / pred_x, 0.85, 1.08)
    ra = clamp(obs_a / pred_a, 0.80, 1.15)

    return rh, rx, ra, n


# ============================================================
# KONEC DELA 3 / 8
# ============================================================
# ============================================================
# CFOS-XG PRO 75 TITAN
# ZAČETEK DELA 4 / 8
# SNAPSHOT SISTEM
# ============================================================

def save_snapshot(home, away, minute, xg_total, sot_total, shots_total, score_diff,
                  odds_home, odds_draw, odds_away,
                  lam_total_raw, p_goal_raw, mc_h_raw, mc_x_raw, mc_a_raw,
                  score_home, score_away, game_type, danger_total):
    ts = str(int(time.time()))
    need_header = not file_has_data(SNAP_FILE)

    with open(SNAP_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if need_header:
            writer.writerow([
                "home", "away", "minute", "xg_total", "sot_total", "shots_total", "score_diff",
                "odds_h", "odds_x", "odds_a", "lam_total_raw", "p_goal_raw",
                "mc_h_raw", "mc_x_raw", "mc_a_raw", "score_home", "score_away",
                "ts", "game_type", "danger_bucket"
            ])

        writer.writerow([
            home, away, minute, f"{xg_total:.4f}", f"{sot_total:.4f}", f"{shots_total:.4f}",
            score_diff, f"{odds_home:.4f}", f"{odds_draw:.4f}", f"{odds_away:.4f}",
            f"{lam_total_raw:.6f}", f"{p_goal_raw:.6f}", f"{mc_h_raw:.6f}", f"{mc_x_raw:.6f}",
            f"{mc_a_raw:.6f}", score_home, score_away, ts, game_type, bucket_danger(danger_total)
        ])

    print("Snapshot shranjen v", SNAP_FILE)


def finalize_snapshots(final_h, final_a, filter_home=None, filter_away=None):
    if not os.path.exists(SNAP_FILE):
        print("Ni snapshotov za zaključek.")
        return

    all_rows = []
    header = None

    with open(SNAP_FILE, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            print("Ni snapshotov za zaključek.")
            return
        for row in reader:
            if row:
                all_rows.append(row)

    remaining_rows = []
    to_finalize = []

    for parts in all_rows:
        if len(parts) < 18:
            continue

        snap_home = parts[0]
        snap_away = parts[1]

        if filter_home is not None and filter_away is not None:
            if snap_home == filter_home and snap_away == filter_away:
                to_finalize.append(parts)
            else:
                remaining_rows.append(parts)
        else:
            to_finalize.append(parts)

    if not to_finalize:
        print("Ni ustreznih snapshotov.")
        return

    need_header = not file_has_data(LEARN_FILE)

    with open(LEARN_FILE, "a", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        if need_header:
            writer.writerow([
                "home", "away", "minute", "xg_total", "sot_total", "shots_total", "score_diff",
                "odds_h", "odds_x", "odds_a", "lam_total_raw", "p_goal_raw",
                "mc_h_raw", "mc_x_raw", "mc_a_raw", "final_outcome", "goal_to_end",
                "ts", "game_type", "danger_bucket"
            ])

        for parts in to_finalize:
            snap_score_home = safe_int(parts[15])
            snap_score_away = safe_int(parts[16])

            if final_h > final_a:
                outcome = "H"
            elif final_h == final_a:
                outcome = "D"
            else:
                outcome = "A"

            goal_to_end = max(0, (final_h + final_a) - (snap_score_home + snap_score_away))
            game_type = parts[18] if len(parts) > 18 else ""
            danger_bucket = parts[19] if len(parts) > 19 else ""

            writer.writerow([
                parts[0], parts[1], parts[2], parts[3], parts[4], parts[5],
                parts[6], parts[7], parts[8], parts[9], parts[10], parts[11],
                parts[12], parts[13], parts[14], outcome, goal_to_end, parts[17] if len(parts) > 17 else "",
                game_type, danger_bucket
            ])

    if len(remaining_rows) == 0:
        try:
            os.remove(SNAP_FILE)
        except:
            pass
    else:
        with open(SNAP_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(remaining_rows)

    print("Snapshoti zaključeni in premaknjeni v", LEARN_FILE)


# ============================================================
# KONEC DELA 4 / 8
# ============================================================
# ============================================================
# CFOS-XG PRO 75 TITAN
# ZAČETEK DELA 5 / 8
# MATCH MEMORY / TIMELINE / ATTACK WAVE
# ============================================================
# ============================================================
# SAVE MATCH RESULT
# ============================================================

def save_match_result(home, away, result):
    try:
        with open("match_memory.csv", "a", encoding="utf-8") as f:
            f.write(f"{home},{away},{result}\n")
    except:
        pass


def load_match_memory(home, away):
    rows = []
    if not os.path.exists(MATCH_MEM_FILE):
        return rows

    try:
        with open(MATCH_MEM_FILE, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            _ = next(reader, None)
            for parts in reader:
                if len(parts) < 22:
                    continue
                if parts[0] == home and parts[1] == away:
                    rows.append({
                        "home": parts[0],
                        "away": parts[1],
                        "minute": safe_int(parts[2]),
                        "score_home": safe_int(parts[3]),
                        "score_away": safe_int(parts[4]),
                        "shots_h": safe_float(parts[5]),
                        "shots_a": safe_float(parts[6]),
                        "sot_h": safe_float(parts[7]),
                        "sot_a": safe_float(parts[8]),
                        "danger_h": safe_float(parts[9]),
                        "danger_a": safe_float(parts[10]),
                        "att_h": safe_float(parts[11]),
                        "att_a": safe_float(parts[12]),
                        "pos_h": safe_float(parts[13]),
                        "pos_a": safe_float(parts[14]),
                        "xg_h": safe_float(parts[15]),
                        "xg_a": safe_float(parts[16]),
                        "odds_h": safe_float(parts[17]),
                        "odds_x": safe_float(parts[18]),
                        "odds_a": safe_float(parts[19]),
                        "corners_h": safe_float(parts[20]),
                        "corners_a": safe_float(parts[21]),
                    })
    except:
        return []

    rows.sort(key=lambda x: x["minute"])
    return rows


def save_match_memory(home, away, minute, score_home, score_away,
                      shots_h, shots_a, sot_h, sot_a, danger_h, danger_a,
                      att_h, att_a, pos_h, pos_a, xg_h, xg_a,
                      odds_h, odds_x, odds_a, corners_h, corners_a):
    need_header = not file_has_data(MATCH_MEM_FILE)

    existing = load_match_memory(home, away)

    # snapshot samo če je nova minuta
    for r in existing:
        if r["minute"] == minute:
            return False

    with open(MATCH_MEM_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if need_header:
            writer.writerow([
                "home", "away", "minute", "score_home", "score_away", "shots_h", "shots_a",
                "sot_h", "sot_a", "danger_h", "danger_a", "att_h", "att_a", "pos_h", "pos_a",
                "xg_h", "xg_a", "odds_h", "odds_x", "odds_a", "corners_h", "corners_a"
            ])
        writer.writerow([
            home, away, minute, score_home, score_away,
            f"{shots_h:.4f}", f"{shots_a:.4f}", f"{sot_h:.4f}", f"{sot_a:.4f}",
            f"{danger_h:.4f}", f"{danger_a:.4f}", f"{att_h:.4f}", f"{att_a:.4f}",
            f"{pos_h:.4f}", f"{pos_a:.4f}", f"{xg_h:.4f}", f"{xg_a:.4f}",
            f"{odds_h:.4f}", f"{odds_x:.4f}", f"{odds_a:.4f}",
            f"{corners_h:.4f}", f"{corners_a:.4f}"
        ])
    return True


def clear_match_memory(home, away):
    if not os.path.exists(MATCH_MEM_FILE):
        return

    try:
        kept = []
        header = None

        with open(MATCH_MEM_FILE, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for parts in reader:
                if len(parts) < 2:
                    continue
                if not (parts[0] == home and parts[1] == away):
                    kept.append(parts)

        if not kept:
            try:
                os.remove(MATCH_MEM_FILE)
            except:
                pass
        else:
            with open(MATCH_MEM_FILE, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if header:
                    writer.writerow(header)
                writer.writerows(kept)
    except:
        pass


def avg_delta(seq):
    if len(seq) < 2:
        return 0.0
    deltas = []
    for i in range(1, len(seq)):
        deltas.append(seq[i] - seq[i - 1])
    return sum(deltas) / len(deltas)


def compute_timeline_factors(rows):
    out = {
        "n": len(rows),
        "trend_factor_goal": 1.0,
        "trend_home": 1.0,
        "trend_away": 1.0,
        "notes": [],
        "true_momentum_text": "Ni dovolj 10-min podatkov"
    }
    if len(rows) < 2:
        return out

    last_min = rows[-1]["minute"]
    recent_rows = [r for r in rows if r["minute"] >= last_min - 10]
    if len(recent_rows) < 2:
        return out
    first = recent_rows[0]
    last = recent_rows[-1]
    span = max(1, last["minute"] - first["minute"])

    shots_h_pm = (last["shots_h"] - first["shots_h"]) / span
    shots_a_pm = (last["shots_a"] - first["shots_a"]) / span
    sot_h_pm = (last["sot_h"] - first["sot_h"]) / span
    sot_a_pm = (last["sot_a"] - first["sot_a"]) / span
    danger_h_pm = (last["danger_h"] - first["danger_h"]) / span
    danger_a_pm = (last["danger_a"] - first["danger_a"]) / span
    att_h_pm = (last["att_h"] - first["att_h"]) / span
    att_a_pm = (last["att_a"] - first["att_a"]) / span
    xg_h_pm = (last["xg_h"] - first["xg_h"]) / span
    xg_a_pm = (last["xg_a"] - first["xg_a"]) / span

    danger_total_seq = [(r["danger_h"] + r["danger_a"]) for r in rows]
    shots_total_seq = [(r["shots_h"] + r["shots_a"]) for r in rows]
    sot_total_seq = [(r["sot_h"] + r["sot_a"]) for r in rows]
    xg_total_seq = [(r["xg_h"] + r["xg_a"]) for r in rows]

    avg_danger_step = avg_delta(danger_total_seq)
    avg_shots_step = avg_delta(shots_total_seq)
    avg_sot_step = avg_delta(sot_total_seq)
    avg_xg_step = avg_delta(xg_total_seq)

    trend_goal = 1.0
    if avg_danger_step >= 4:
        trend_goal += 0.03
        out["notes"].append("TM danger_rising")
    if avg_shots_step >= 0.7:
        trend_goal += 0.03
        out["notes"].append("TM shots_rising")
    if avg_sot_step >= 0.25:
        trend_goal += 0.04
        out["notes"].append("TM sot_rising")
    if avg_xg_step >= 0.07:
        trend_goal += 0.04
        out["notes"].append("TM xg_rising")
    if avg_danger_step <= 1 and avg_shots_step <= 0.2 and avg_sot_step <= 0.05 and last["minute"] >= 60:
        trend_goal -= 0.07
        out["notes"].append("TM game_flat")

    trend_goal = clamp(trend_goal, 0.88, 1.18)

    home_push = (
            shots_h_pm * 0.10 +
            sot_h_pm * 0.34 +
            danger_h_pm * 0.012 +
            att_h_pm * 0.005 +
            xg_h_pm * 0.40
    )
    away_push = (
            shots_a_pm * 0.10 +
            sot_a_pm * 0.34 +
            danger_a_pm * 0.012 +
            att_a_pm * 0.005 +
            xg_a_pm * 0.40
    )

    home_factor = clamp(1.0 + clamp(home_push, -0.10, 0.15), 0.86, 1.18)
    away_factor = clamp(1.0 + clamp(away_push, -0.10, 0.15), 0.86, 1.18)

    out["trend_factor_goal"] = trend_goal
    out["trend_home"] = home_factor
    out["trend_away"] = away_factor
    out["true_momentum_text"] = " | ".join(out["notes"]) if out["notes"] else "Ni dovolj 10-min podatkov"
    return out


def detect_attack_wave(rows, minute):
    out = {
        "active": False,
        "home": 1.0,
        "away": 1.0,
        "goal": 1.0,
        "notes": []
    }

    if len(rows) < 2:
        return out

    last_min = rows[-1]["minute"]
    recent_rows = [r for r in rows if r["minute"] >= last_min - 10]

    if len(recent_rows) < 2:
        return out

    first = recent_rows[0]
    last = recent_rows[-1]
    span = max(1, last["minute"] - first["minute"])

    d_danger_h = last["danger_h"] - first["danger_h"]
    d_danger_a = last["danger_a"] - first["danger_a"]
    d_shots_h = last["shots_h"] - first["shots_h"]
    d_shots_a = last["shots_a"] - first["shots_a"]
    d_sot_h = last["sot_h"] - first["sot_h"]
    d_sot_a = last["sot_a"] - first["sot_a"]
    d_xg_h = last["xg_h"] - first["xg_h"]
    d_xg_a = last["xg_a"] - first["xg_a"]

    if (
            (d_danger_h >= 8 and span <= 5) or
            (d_shots_h >= 2 and d_sot_h >= 1) or
            (d_xg_h >= 0.18)
    ):
        out["home"] *= 1.07
        out["goal"] *= 1.02
        out["active"] = True
        out["notes"].append(
            f"WAVE HOME dDanger={round(d_danger_h, 1)} dShots={round(d_shots_h, 1)} dSOT={round(d_sot_h, 1)} dXG={round(d_xg_h, 3)}")

    if (
            (d_danger_a >= 8 and span <= 5) or
            (d_shots_a >= 2 and d_sot_a >= 1) or
            (d_xg_a >= 0.18)
    ):
        out["away"] *= 1.07
        out["goal"] *= 1.04
        out["active"] = True
        out["notes"].append(
            f"WAVE AWAY dDanger={round(d_danger_a, 1)} dShots={round(d_shots_a, 1)} dSOT={round(d_sot_a, 1)} dXG={round(d_xg_a, 3)}")

    out["home"] = clamp(out["home"], 1.0, 1.14)
    out["away"] = clamp(out["away"], 1.0, 1.14)
    out["goal"] = clamp(out["goal"], 1.0, 1.10)
    return out


# ============================================================
# KONEC DELA 5 / 8
# ============================================================
# ============================================================
# CFOS-XG PRO 75 TITAN
# ZAČETEK DELA 6 / 8
# HISTORY SCORE / EXACT SCORE / ANALIZA PREDLOGA STAVE
# ============================================================

def history_score_bias(history, minute, xg_total, sot_total, shots_total, score_diff, game_type="", danger_total=0):
    subset = select_subset(history, minute, xg_total, sot_total, shots_total, score_diff, game_type, danger_total)
    n = len(subset)
    if n < 10:
        return None

    p_home = sum(1 for r in subset if r["final_outcome"] == "H") / n
    p_draw = sum(1 for r in subset if r["final_outcome"] == "D") / n
    p_away = sum(1 for r in subset if r["final_outcome"] == "A") / n
    p_goal = sum(1 for r in subset if r["goal_to_end"] > 0) / n
    p_no_goal = 1.0 - p_goal

    return {
        "n": n,
        "p_home": p_home,
        "p_draw": p_draw,
        "p_away": p_away,
        "p_goal": p_goal,
        "p_no_goal": p_no_goal,
    }


def exact_score_history_bias(history, minute, xg_total, sot_total, shots_total, score_diff,
                             score_home, score_away, game_type="", danger_total=0):
    subset = select_subset(history, minute, xg_total, sot_total, shots_total, score_diff, game_type, danger_total)
    n = len(subset)
    if n < 10:
        return None

    p_no_goal = sum(r["goal_to_end"] == 0 for r in subset) / n
    p_goal = 1.0 - p_no_goal

    return {
        "n": n,
        "p_no_goal": p_no_goal,
        "p_goal": p_goal,
    }


def final_score_prediction(score_home, score_away, lam_h, lam_a, lam_c,
                           history, minute, xg_total, sot_total, shots_total,
                           score_diff, game_type="", danger_total=0, sim_count=SIM_EXACT_BASE):
    score_dist = {}

    for _ in range(sim_count):
        gh, ga = bivariate_poisson_sample(lam_h, lam_a, lam_c)
        gh = min(gh, 5)
        ga = min(ga, 5)
        fh = score_home + gh
        fa = score_away + ga
        key = f"{fh}-{fa}"
        score_dist[key] = score_dist.get(key, 0) + 1

    total_raw = sum(score_dist.values())
    if total_raw > 0:
        for k in score_dist:
            score_dist[k] /= total_raw

    hist = history_score_bias(history, minute, xg_total, sot_total, shots_total, score_diff, game_type, danger_total)
    exact_hist = exact_score_history_bias(history, minute, xg_total, sot_total, shots_total, score_diff,
                                          score_home, score_away, game_type, danger_total)

    for k in list(score_dist.keys()):
        fh, fa = k.split("-")
        fh = int(fh)
        fa = int(fa)
        mult = 1.0

        if hist is not None:
            if fh > fa:
                mult *= (0.90 + hist["p_home"])
            elif fh == fa:
                mult *= (0.90 + hist["p_draw"])
            else:
                mult *= (0.90 + hist["p_away"])

        if exact_hist is not None:
            if fh == score_home and fa == score_away:
                mult *= (0.90 + exact_hist["p_no_goal"])
            else:
                mult *= (0.90 + exact_hist["p_goal"])

        score_dist[k] *= mult

    total_adj = sum(score_dist.values())
    if total_adj > 0:
        for k in score_dist:
            score_dist[k] /= total_adj

    sorted_scores = sorted(score_dist.items(), key=lambda x: x[1], reverse=True)
    return sorted_scores[:5], hist, exact_hist


def lge_notes(game_type, tempo_notes, xgr_notes, wave_active=False):
    notes = [f"GT GT {game_type}"]
    notes.extend(tempo_notes)
    notes.extend(xgr_notes)
    if wave_active:
        notes.append("WAVE active")
    return "ACTIVE | " + "; ".join(notes)


def predlog_stave(r):
    # 1) Najprej verjetnost izida, ne edge
    if r["mc_x_adj"] >= 0.60:
        return "X", "DRAW DOMINANT"

    if r["mc_h_adj"] >= 0.55 and r["edge_h"] >= 0.05:
        return "1", "MODEL + VALUE"

    if r["mc_a_adj"] >= 0.55 and r["edge_a"] >= 0.05:
        return "2", "MODEL + VALUE"

    # 2) Če ni ekstremne dominance, potem strong value
    if r["edge_a"] >= 0.12 and r["mc_a_adj"] >= 0.25:
        return "2", "STRONG VALUE"

    if r["edge_h"] >= 0.12 and r["mc_h_adj"] >= 0.30:
        return "1", "STRONG VALUE"

    if r["edge_x"] >= 0.07 and r["mc_x_adj"] >= 0.30:
        return "X", "VALUE"

    if r["edge_h"] >= 0.08 and r["mc_h_adj"] >= 0.50:
        return "1", "VALUE"

    if r["edge_a"] >= 0.08 and r["mc_a_adj"] >= 0.45:
        return "2", "VALUE"

    # 3) Goal/no-goal fallback
    if r["p_goal"] >= 0.62:
        return "GOL", "OPEN GAME"

    if r["p_no_goal"] >= 0.62:
        return "NO GOAL", "CLOSED GAME"

    return "NO BET", "NO EDGE"


def moje_predvidevanje(r):
    score_txt = r["top_scores"][0][0] if r["top_scores"] else "N/A"

    tip, razlog = predlog_stave(r)

    # IZID IZ MC (NE SCORE)
    if r["mc_h_adj"] > r["mc_x_adj"] and r["mc_h_adj"] > r["mc_a_adj"]:
        izid = "DOMAČI"
    elif r["mc_a_adj"] > r["mc_h_adj"] and r["mc_a_adj"] > r["mc_x_adj"]:
        izid = "GOST"
    else:
        izid = "REMI"

    return {
        "napoved_izida": izid,
        "napoved_rezultata": score_txt,
        "moja_stava": tip,
        "razlog_stave": razlog
    }


# ============================================================
# KONEC DELA 6 / 8
# ============================================================
# ============================================================
# CFOS-XG PRO 75 TITAN
# ZAČETEK DELA 7.1/ 8
# GLAVNI MODEL
# ============================================================

def izracunaj_model(data, final_third_fm_h=None, final_third_fm_a=None):
    def get_safe(idx):
        if idx < len(data):
            try:
                return float(data[idx])
            except:
                return None
        return None

    home = get_idx(data, 0, "HOME")
    away = get_idx(data, 1, "AWAY")

    odds_home = get_num(data, 2)
    odds_draw = get_num(data, 3)
    odds_away = get_num(data, 4)

    minute = safe_int(get_idx(data, 5, "0"))
    score_home = safe_int(get_idx(data, 6, "0"))
    score_away = safe_int(get_idx(data, 7, "0"))
    score_diff = score_home - score_away

    xg_h = get_num(data, 8)
    xg_a = get_num(data, 9)

    shots_h = get_num(data, 10)
    shots_a = get_num(data, 11)
    sot_h = get_num(data, 12)
    sot_a = get_num(data, 13)

    attacks_h = get_num(data, 14)
    attacks_a = get_num(data, 15)

    danger_h = get_num(data, 16)
    danger_a = get_num(data, 17)

    pos_h = get_safe(18)
    pos_a = get_safe(19)

    passes_h = get_safe(20)
    passes_a = get_safe(21)

    duels_h = get_safe(22)
    duels_a = get_safe(23)

    corners_h = get_safe(24)
    corners_a = get_safe(25)

    yellow_h = get_safe(26)
    yellow_a = get_safe(27)

    red_h = get_safe(28)
    red_a = get_safe(29)

    # ============================================================
    # AUTO SWAP DISABLED (BUG FIX)
    # ============================================================

    swap_flag = False

    bc_h = get_num(data, 18)
    bc_a = get_num(data, 19)

    bc_h = clamp(bc_h, 0.0, 5.0)
    bc_a = clamp(bc_a, 0.0, 5.0)

    bcm_h = get_num(data, 28)
    bcm_a = get_num(data, 29)

    y_h = get_num(data, 20)
    y_a = get_num(data, 21)
    red_h = get_num(data, 22)
    red_a = get_num(data, 23)
    pos_h = get_num(data, 24)
    pos_a = get_num(data, 25)

    # =========================
    # VALIDATOR
    # =========================

    if sot_h > shots_h:
        raise ValueError("NAPAKA: SOT home > shots home")

    if sot_a > shots_a:
        raise ValueError("NAPAKA: SOT away > shots away")

    if bc_h > shots_h:
        shots_h = bc_h

    if bc_a > shots_a:
        shots_a = bc_a

    if pos_h + pos_a > 105:
        raise ValueError("NAPAKA: possession vsota > 105")

    # NEGATIVE VALUE CHECK
    if xg_h < 0 or xg_a < 0:
        raise ValueError("NAPAKA: negativen xG")

    if shots_h < 0 or shots_a < 0:
        raise ValueError("NAPAKA: negativni shots")

    if sot_h < 0 or sot_a < 0:
        raise ValueError("NAPAKA: negativni SOT")

    if danger_h < 0 or danger_a < 0:
        raise ValueError("NAPAKA: negativni danger attacks")

    if shots_h > 40 or shots_a > 40:
        raise ValueError("NAPAKA: preveč shots")

    if sot_h > 20 or sot_a > 20:
        raise ValueError("NAPAKA: preveč SOT")

    blocked_h = get_num(data, 26)
    blocked_a = get_num(data, 27)
    bcm_h = get_num(data, 28)
    bcm_a = get_num(data, 29)
    corners_h = get_num(data, 30)
    corners_a = get_num(data, 31)

    if corners_h < 0 or corners_a < 0:
        raise ValueError("NAPAKA: negativni corners")

    if corners_h > 25 or corners_a > 25:
        raise ValueError("NAPAKA: preveč corners")

    gk_saves_h = get_num(data, 32)
    gk_saves_a = get_num(data, 33)
    passes_h = get_num(data, 34)
    passes_a = get_num(data, 35)
    acc_pass_h = get_num(data, 36)
    acc_pass_a = get_num(data, 37)

    acc_pass_h = clamp(acc_pass_h, 0.0, passes_h)
    acc_pass_a = clamp(acc_pass_a, 0.0, passes_a)

    tackles_h = get_num(data, 38)
    tackles_a = get_num(data, 39)
    inter_h = get_num(data, 40)
    inter_a = get_num(data, 41)
    clear_h = get_num(data, 42)
    clear_a = get_num(data, 43)
    duels_h = get_num(data, 44)
    duels_a = get_num(data, 45)
    offsides_h = get_num(data, 46)
    offsides_a = get_num(data, 47)
    throw_h = get_num(data, 48)
    throw_a = get_num(data, 49)
    fouls_h = get_num(data, 50)
    fouls_a = get_num(data, 51)

    prematch_h = get_num(data, 52)
    prematch_a = get_num(data, 53)
    prev_odds_home = get_num(data, 54)
    prev_odds_draw = get_num(data, 55)
    prev_odds_away = get_num(data, 56)
    elo_h = get_num(data, 57)
    elo_a = get_num(data, 58)

    # =========================================================
    # TEAM STRENGTH ENGINE
    # =========================================================

    # prematch strength (0-1)
    pm_diff = prematch_h - prematch_a

    # ELO difference
    elo_diff = (elo_h - elo_a) / 400.0

    # odds favorit
    odds_bias = 0
    if odds_home > 0 and odds_away > 0:
        odds_bias = (1 / odds_home) - (1 / odds_away)

    # kombinirana moč
    team_power = (
            pm_diff * 0.50 +
            elo_diff * 0.30 +
            odds_bias * 0.20
    )

    team_power = clamp(team_power, -0.35, 0.35)

    # --------------------------------------------------------
    # PRO 75 - DODATNI FOTMOB PODATKI (DINAMIČNI)
    # če jih ni, so 0
    # --------------------------------------------------------
    keypasses_h = get_num(data, 59)
    keypasses_a = get_num(data, 60)

    crosses_h = get_num(data, 61)
    crosses_a = get_num(data, 62)

    tackles_extra_h = get_num(data, 63)
    tackles_extra_a = get_num(data, 64)

    inter_extra_h = get_num(data, 65)
    inter_extra_a = get_num(data, 66)

    clear_extra_h = get_num(data, 67)
    clear_extra_a = get_num(data, 68)

    duels_extra_h = get_num(data, 69)
    duels_extra_a = get_num(data, 70)

    aerials_h = get_num(data, 71)
    aerials_a = get_num(data, 72)

    dribbles_h = get_num(data, 73)
    dribbles_a = get_num(data, 74)

    throw_extra_h = get_num(data, 75)
    throw_extra_a = get_num(data, 76)

    final_third_h = get_num(data, 77)
    final_third_a = get_num(data, 78)

    long_balls_h = get_num(data, 79)
    long_balls_a = get_num(data, 80)

    gk_saves_extra_h = get_num(data, 81)
    gk_saves_extra_a = get_num(data, 82)

    bc_created_h = get_num(data, 83)
    bc_created_a = get_num(data, 84)

    bc_created_h = clamp(bc_created_h, 0.0, 3.0)
    bc_created_a = clamp(bc_created_a, 0.0, 3.0)

    action_left = get_num(data, 85)
    action_mid = get_num(data, 86)
    action_right = get_num(data, 87)

    pass_acc_extra_h = get_num(data, 88)
    pass_acc_extra_a = get_num(data, 89)

    # FOTMOB EXTRA — FIXED INDEX MAP

    key_pass_h = get_num(data, 90)
    key_pass_a = get_num(data, 91)

    cross_h = get_num(data, 92)
    cross_a = get_num(data, 93)

    # 🔥 SHIFT FIX
    aerial_h = get_num(data, 96)
    aerial_a = get_num(data, 97)

    dribble_h = get_num(data, 98)
    dribble_a = get_num(data, 99)

    final_third_h = get_num(data, 100)
    final_third_a = get_num(data, 101)

    long_ball_h = get_num(data, 102)
    long_ball_a = get_num(data, 103)

    big_chance_h = get_num(data, 104)
    big_chance_a = get_num(data, 105)
    if keypasses_h == 0 and key_pass_h > 0:
        keypasses_h = key_pass_h
    if keypasses_a == 0 and key_pass_a > 0:
        keypasses_a = key_pass_a

    if crosses_h == 0 and cross_h > 0:
        crosses_h = cross_h
    if crosses_a == 0 and cross_a > 0:
        crosses_a = cross_a

    if aerials_h == 0 and aerial_h > 0:
        aerials_h = aerial_h
    if aerials_a == 0 and aerial_a > 0:
        aerials_a = aerial_a

    if dribbles_h == 0 and dribble_h > 0:
        dribbles_h = dribble_h
    if dribbles_a == 0 and dribble_a > 0:
        dribbles_a = dribble_a

    final_third_h = final_third_h or 0
    final_third_a = final_third_a or 0
    final_third_fm_h = final_third_fm_h or 0
    final_third_fm_a = final_third_fm_a or 0

    if final_third_h == 0 and final_third_fm_h > 0:
        final_third_h = final_third_fm_h

    if final_third_a == 0 and final_third_fm_a > 0:
        final_third_a = final_third_fm_a

    if final_third_h == 0 and final_third_fm_h > 0:
        final_third_h = final_third_fm_h
    if final_third_a == 0 and final_third_fm_a > 0:
        final_third_a = final_third_fm_a

    if long_balls_h == 0 and long_ball_h > 0:
        long_balls_h = long_ball_h
    if long_balls_a == 0 and long_ball_a > 0:
        long_balls_a = long_ball_a

    if bc_created_h == 0 and big_chance_h > 0:
        bc_created_h = big_chance_h
    if bc_created_a == 0 and big_chance_a > 0:
        bc_created_a = big_chance_a

    # če so v osnovnih poljih 0, uporabi dodatna FotMob polja
    if tackles_h == 0 and tackles_extra_h > 0:
        tackles_h = tackles_extra_h
    if tackles_a == 0 and tackles_extra_a > 0:
        tackles_a = tackles_extra_a

    if inter_h == 0 and inter_extra_h > 0:
        inter_h = inter_extra_h
    if inter_a == 0 and inter_extra_a > 0:
        inter_a = inter_extra_a

    if clear_h == 0 and clear_extra_h > 0:
        clear_h = clear_extra_h
    if clear_a == 0 and clear_extra_a > 0:
        clear_a = clear_extra_a

    if duels_h == 0 and duels_extra_h > 0:
        duels_h = duels_extra_h
    if duels_a == 0 and duels_extra_a > 0:
        duels_a = duels_extra_a

    if throw_h == 0 and throw_extra_h > 0:
        throw_h = throw_extra_h
    if throw_a == 0 and throw_extra_a > 0:
        throw_a = throw_extra_a

    if gk_saves_h == 0 and gk_saves_extra_h > 0:
        gk_saves_h = gk_saves_extra_h
    if gk_saves_a == 0 and gk_saves_extra_a > 0:
        gk_saves_a = gk_saves_extra_a

    # če so v osnovnih poljih 0, uporabi dodatna FotMob polja

    if acc_pass_h == 0 and pass_acc_extra_h > 0 and passes_h > 0:
        acc_pass_h = passes_h * (pass_acc_extra_h / 100.0)

    if acc_pass_h == 0 and pass_acc_extra_h > 0 and passes_h > 0:
        acc_pass_h = passes_h * (pass_acc_extra_h / 100.0)

    if acc_pass_a == 0 and pass_acc_extra_a > 0 and passes_a > 0:
        acc_pass_a = passes_a * (pass_acc_extra_a / 100.0)

    acc_pass_h = clamp(acc_pass_h, 0.0, passes_h)
    acc_pass_a = clamp(acc_pass_a, 0.0, passes_a)

    synthetic_xg_used = False

    if xg_h <= 0.05:
        base_h = (sot_h * 0.18) + (shots_h * 0.040) + (danger_h * 0.006)
        base_h += blocked_h * 0.020 + bcm_h * 0.060 + bc_h * 0.080 + corners_h * 0.010 + gk_saves_a * 0.030
        base_h += keypasses_h * 0.025 + crosses_h * 0.012 + dribbles_h * 0.015 + final_third_h * 0.004 + bc_created_h * 0.050
        tscale = clamp((minute / 90.0) ** 0.80, 0.45, 1.00)
        xg_h = clamp(base_h * tscale, 0.0, 2.60)
        synthetic_xg_used = True

    if xg_a <= 0.05:
        base_a = (sot_a * 0.20) + (shots_a * 0.042) + (danger_a * 0.0075)
        base_a += blocked_a * 0.020 + bcm_a * 0.060 + bc_a * 0.080 + corners_a * 0.010 + gk_saves_h * 0.030
        base_a += keypasses_a * 0.025 + crosses_a * 0.012 + dribbles_a * 0.015 + final_third_a * 0.004 + bc_created_a * 0.050
        tscale = clamp((minute / 90.0) ** 0.80, 0.45, 1.00)
        xg_a = clamp(base_a * tscale, 0.0, 2.60)
        synthetic_xg_used = True

    xg_total = xg_h + xg_a
    sot_total = sot_h + sot_a
    shots_total = shots_h + shots_a
    danger_total = danger_h + danger_a

    # =========================================================
    # 🔥 SOT MOMENTUM (GLOBAL PRESSURE)
    # =========================================================

    sot_diff = sot_h - sot_a

    sot_momentum = 1.0

    if sot_total >= 3:
        if abs(sot_diff) >= 2:
            sot_momentum = 1.12
        elif abs(sot_diff) == 1:
            sot_momentum = 1.06

    save_match_memory(
        home=home, away=away, minute=minute, score_home=score_home, score_away=score_away,
        shots_h=shots_h, shots_a=shots_a, sot_h=sot_h, sot_a=sot_a, danger_h=danger_h, danger_a=danger_a,
        att_h=attacks_h, att_a=attacks_a, pos_h=pos_h, pos_a=pos_a, xg_h=xg_h, xg_a=xg_a,
        odds_h=odds_home, odds_x=odds_draw, odds_a=odds_away, corners_h=corners_h, corners_a=corners_a
    )
    match_rows = load_match_memory(home, away)
    timeline = compute_timeline_factors(match_rows)
    wave = detect_attack_wave(match_rows, minute)

    time_left_fraction_value, minutes_left_real = time_left_fraction(minute)

    # ZAČETEK DELA 7.2/ 8

    tempo_shots_h = shots_h / max(1, minute)
    tempo_shots_a = shots_a / max(1, minute)
    tempo_shots = shots_total / max(1, minute)
    tempo_att = (attacks_h + attacks_a) / max(1, minute)
    danger_total = danger_h + danger_a

    if danger_total > 0:
        tempo_danger = danger_total / max(1, minute)

    elif shots_total > 0:
        # fallback če danger ni podan → uporabi shots + SOT
        tempo_danger = ((shots_total * 1.2) + (sot_total * 2.0)) / max(1, minute)

    else:
        tempo_danger = 0

    tempo_danger *= clamp(0.85 + (minute / 220), 0.85, 1.15)

    tempo_danger = clamp(tempo_danger, 0, 2.2)

    xg_rate_h = xg_h / max(1, minute)
    xg_rate_a = xg_a / max(1, minute)
    xg_rate_total = xg_total / max(1, minute)

    tempo_goal_mult, tempo_notes = tempo_goal_multiplier(tempo_shots, tempo_danger, tempo_att, minute)
    xgr_mult, xgr_notes = xgr_goal_multiplier(xg_rate_total, minute)

    game_type = classify_game_type(

        # ============================================================
        # 🔥 SLOW → PRESSURE OVERRIDE (CRITICAL FIX)
        # ============================================================

        minute=minute,
        xg_total=xg_total,
        shots_total=shots_total,
        sot_total=sot_total,
        danger_total=danger_total,
        tempo_shots=tempo_shots,
        xg_rate=xg_rate_total
    )

    if game_type == "SLOW":
        if tempo_danger >= 1.10:
            game_type = "PRESSURE"
        elif tempo_danger >= 1.00 and tempo_shots >= 0.12:
            game_type = "PRESSURE"

    game_type_goal_mult = game_type_goal_multiplier(game_type)

    pass_acc_h = pass_acc_rate(acc_pass_h, passes_h)
    pass_acc_a = pass_acc_rate(acc_pass_a, passes_a)
    d2s_h = danger_to_shot_conv(shots_h, danger_h)
    d2s_a = danger_to_shot_conv(shots_a, danger_a)
    shot_q_h = shot_quality(xg_h, shots_h)
    shot_q_a = shot_quality(xg_a, shots_a)
    sot_r_h = sot_ratio(sot_h, shots_h)
    sot_r_a = sot_ratio(sot_a, shots_a)
    bc_r_h = big_chance_ratio(bc_h, shots_h)
    bc_r_a = big_chance_ratio(bc_a, shots_a)

    # PRO 75 - momentum uporablja tudi dodatne FotMob podatke, če obstajajo
    attack_h = xg_h * 3.0 + shots_h * 0.25 + sot_h * 0.85 + bc_h * 1.7 + keypasses_h * 0.16 + crosses_h * 0.05 + dribbles_h * 0.07
    attack_a = xg_a * 3.0 + shots_a * 0.25 + sot_a * 0.85 + bc_a * 1.7 + keypasses_a * 0.16 + crosses_a * 0.05 + dribbles_a * 0.07

    danger_idx_h = (
            sot_h * 1.0 +
            bc_h * 1.4 +
            xg_h * 3.8 +
            keypasses_h * 0.12 +
            bc_created_h * 0.15
    )

    danger_idx_a = (
            sot_a * 1.0 +
            bc_a * 1.4 +
            xg_a * 3.8 +
            keypasses_a * 0.12 +
            bc_created_a * 0.15
    )

    danger_idx_h = clamp(danger_idx_h, 0.0, 6.5)
    danger_idx_a = clamp(danger_idx_a, 0.0, 6.5)

    pressure_h = (
            sot_h * 1.20 +
            bc_h * 1.50 +
            danger_idx_h * 0.55 +
            tempo_shots_h * 6.5 +
            corners_h * 0.08
    )

    pressure_a = (
            sot_a * 1.20 +
            bc_a * 1.50 +
            danger_idx_a * 0.55 +
            tempo_shots_a * 6.5 +
            corners_a * 0.08
    )

    pressure_h = clamp(pressure_h, 0.0, 12.0)
    pressure_a = clamp(pressure_a, 0.0, 12.0)

    pressure_total = clamp(pressure_h + pressure_a, 0, 50)

    attack_sum = attack_h + attack_a

    if attack_sum < 0.50:
        momentum = 0.0
    else:
        momentum = (attack_h - attack_a) / attack_sum

        # =========================================================
        # MOMENTUM STABILIZER (ANTI FAKE DOMINANCE)
        # =========================================================
        if score_diff == 0:

            xg_diff = abs(xg_h - xg_a)
            pressure_diff = abs(pressure_h - pressure_a)

            # balanced tekma → zmanjša fake smer
            if xg_diff < 0.40 and pressure_diff < 2.5:
                momentum *= 0.65

            # zelo blizu → skoraj nevtralno
            if xg_diff < 0.20 and pressure_diff < 1.5:
                momentum *= 0.45

    # MOMENTUM NORMALIZATION (FIX UNDERREACTION)
    if minute < 30:
        momentum *= 0.85
    elif minute < 65:
        momentum *= 1.00
    else:
        momentum *= 1.15

    # small noise filter

    # SMART NOISE FILTER (NE UBIJE MOMENTUMA)
    if abs(momentum) < 0.03:
        momentum *= 0.4

    momentum = clamp(momentum, -0.70, 0.70)

    # DEBUG (lahko kasneje izbrišeš)

    lambda_core_h = (
            xg_h * 0.58 +
            danger_h * 0.0038 +
            sot_h * 0.085 +
            shots_h * 0.020 +
            bc_h * 0.070 +
            corners_h * 0.010
    )
    lambda_core_a = (
            xg_a * 0.58 +
            danger_a * 0.0038 +
            sot_a * 0.085 +
            shots_a * 0.020 +
            bc_a * 0.070 +
            corners_a * 0.010
    )

    # PRO 75 - dodaten vpliv, samo če podatki obstajajo
    lambda_core_h += keypasses_h * 0.008 + crosses_h * 0.004 + dribbles_h * 0.006 + final_third_h * 0.0015 + bc_created_h * 0.015
    lambda_core_a += keypasses_a * 0.008 + crosses_a * 0.004 + dribbles_a * 0.006 + final_third_a * 0.0015 + bc_created_a * 0.015

    stage_factor = clamp(0.55 + (minute / 90.0) * 0.65, 0.55, 1.18)
    pre_h = 0.33
    pre_x = 0.34
    pre_a = 0.33

    lam_h_raw = lambda_core_h * (minutes_left_real / 90) * stage_factor
    lam_a_raw = lambda_core_a * (minutes_left_real / 90) * stage_factor

    # =========================================================
    # 🔥 SOT ROTATION DETECTOR (ELITE SIGNAL)
    # =========================================================

    if len(match_rows) >= 2:
        prev = match_rows[-2]

        prev_sot_h = prev.get("sot_h", 0)
        prev_sot_a = prev.get("sot_a", 0)

        sot_delta_h = sot_h - prev_sot_h
        sot_delta_a = sot_a - prev_sot_a

        # 🔥 BURST DETECTOR
        if sot_delta_h >= 2:
            lam_h_raw *= 1.15

        if sot_delta_a >= 2:
            lam_a_raw *= 1.15

    # 🔥 APPLY SOT MOMENTUM
    lam_h_raw *= sot_momentum
    lam_a_raw *= sot_momentum

    # TEAM STRENGTH APPLY
    lam_h_raw *= (1 + team_power)
    lam_a_raw *= (1 - team_power)

    # ===== CONTROL BASE (NE DIRAJ SPODAJ) =====
    base_h = lam_h_raw
    base_a = lam_a_raw

    if minute >= 88 and score_diff == 0:
        lam_h_raw *= 0.2
        lam_a_raw *= 0.2

    # 🔥 ANTI FAKE DRAW (PRAVO MESTO)
    if (
            game_type == "SLOW" and
            tempo_danger >= 1.20 and
            xg_total >= 0.6 and
            minute >= 40
    ):
        lam_h_raw *= 1.08
        lam_a_raw *= 1.08

    # =========================================
    # ✅ CONTROL LAYER (NOVO - 10/10 FIX)
    # =========================================
    mult_h = 1.0
    mult_a = 1.0

    # MOMENTUM CONTROL (NAMOESTO DIRECT *=)
    if momentum > 0.18:
        mult_h *= 1.12
        mult_a *= 0.92
    elif momentum < -0.18:
        mult_a *= 1.12
        mult_h *= 0.92

    lam_h_raw = blend(lam_h_raw, tempo_goal_mult, 0.30)
    lam_h_raw = blend(lam_h_raw, xgr_mult, 0.25)
    lam_h_raw = blend(lam_h_raw, game_type_goal_mult, 0.30)

    lam_a_raw = blend(lam_a_raw, tempo_goal_mult, 0.30)
    lam_a_raw = blend(lam_a_raw, xgr_mult, 0.25)
    lam_a_raw = blend(lam_a_raw, game_type_goal_mult, 0.30)

    # 🔥 CHAOS GAME BOOST (ubije remi)
    if game_type == "CHAOS" and minute >= 50:
        lam_h_raw *= 1.05
        lam_a_raw *= 1.05

    # ✅ FALLBACK MOMENTUM (SAMO če NI timeline podatkov)
    if abs(momentum) < 0.05 and timeline["n"] < 2 and minute < 55:

        fallback_raw = (
                (sot_h - sot_a) * 0.06 +
                (shots_h - shots_a) * 0.02 +
                (keypasses_h - keypasses_a) * 0.04
        )

        norm = abs(sot_h) + abs(sot_a) + abs(shots_h) + abs(shots_a) + abs(keypasses_h) + abs(keypasses_a)

        if norm > 0:
            momentum = fallback_raw / norm
        else:
            momentum = 0.0

        momentum = clamp(momentum, -0.70, 0.70)

    # ✅ DEBUG NA KONCU
    # print("DEBUG momentum FINAL:", momentum)

    momentum_boost = clamp(momentum * 1.15, -0.30, 0.30)

    # 🔥 MOMENTUM DOMINANCE LOCK
    if abs(momentum) > 0.18:
        if momentum > 0:
            lam_h_raw *= 1.08
            lam_a_raw *= 0.95
        else:
            lam_a_raw *= 1.08
            lam_h_raw *= 0.95

    # MOMENTUM EXTREME BOOST
    if abs(momentum) > 0.20:
        momentum_boost *= 1.15

    momentum_boost = clamp(momentum_boost, -0.34, 0.34)

    lam_h_raw *= (1 + momentum_boost)
    lam_a_raw *= (1 - momentum_boost)

    # 🔥 EXTREME DOMINANCE FINISHER
    if minute >= 75 and abs(momentum) > 0.15:
        if momentum > 0:
            lam_h_raw *= 1.10
        else:
            lam_a_raw *= 1.10

    # LOSING TEAM DOMINANCE BOOST (SOFTER)
    if score_diff > 0:  # home vodi
        if (
                momentum < -0.08 and
                danger_a > danger_h * 0.80 and
                xg_a > xg_h
        ):
            lam_a_raw *= 1.18

    elif score_diff < 0:  # away vodi
        if (
                momentum > 0.08 and
                danger_h > danger_a * 0.80 and
                xg_h > xg_a
        ):
            lam_h_raw *= 1.18

    # COMBINED QUALITY BOOST (SMART)
    quality_h = (shot_q_h * 0.6) + (sot_r_h * 0.4)
    quality_a = (shot_q_a * 0.6) + (sot_r_a * 0.4)

    if quality_h >= 0.16:
        lam_h_raw *= 1.07
    elif quality_h >= 0.12:
        lam_h_raw *= 1.03

    if quality_a >= 0.16:
        lam_a_raw *= 1.07
    elif quality_a >= 0.12:
        lam_a_raw *= 1.03

    # ============================================================
    # XG DOMINANCE OVERRIDE (KLJUČNO)
    # ============================================================

    if minute >= 45:
        if xg_h > xg_a * 1.4:
            lam_h_raw *= 1.15
        elif xg_a > xg_h * 1.4:
            lam_a_raw *= 1.15

    # 🔥 UNDERDOG REAL BOOST
    if odds_away >= 3.5 and momentum < -0.12 and xg_a > xg_h:
        lam_a_raw *= 1.12

    if odds_home >= 3.5 and momentum > 0.12 and xg_h > xg_a:
        lam_h_raw *= 1.12

    # UNDERDOG PRESSURE RULE
    if (
            odds_away >= 6.0 and
            danger_a >= danger_h * 0.95 and
            minute >= 55
    ):
        lam_a_raw *= 1.18

    if (
            odds_home >= 6.0 and
            danger_h >= danger_a * 0.95 and
            minute >= 55
    ):
        lam_h_raw *= 1.18

    # EXTREME UNDERDOG REVERSAL
    if (
            odds_away >= 5.5 and
            momentum < -0.15 and
            xg_a > xg_h * 1.2 and
            minute >= 50
    ):
        lam_a_raw *= 1.20

    if (
            odds_home >= 5.5 and
            momentum > 0.15 and
            xg_h > xg_a * 1.2 and
            minute >= 50
    ):
        lam_h_raw *= 1.20

    # ============================================================
    # PRESSURE STABILIZER (UPGRADED)
    # ============================================================

    if pressure_total > 22:
        lam_h_raw *= 1.10
        lam_a_raw *= 1.10

    elif pressure_total > 16:
        lam_h_raw *= 1.05
        lam_a_raw *= 1.05

    if timeline["n"] >= 2:
        lam_h_raw *= timeline["trend_home"]
        lam_a_raw *= timeline["trend_away"]

    if wave["active"]:
        lam_h_raw *= wave["home"]
        lam_a_raw *= wave["away"]

    # SMART DRAW BOOST PRO (FIX REAL DOMINANCE)
    if score_diff == 0 and minute >= 60:

        # 🔥 SOT PRESSURE DRAW KILLER
        if abs(sot_h - sot_a) >= 1 and abs(danger_h - danger_a) >= 10:
            if sot_h > sot_a:
                lam_h_raw *= 1.12
            else:
                lam_a_raw *= 1.12
    # ============================================================
    # ZAČETEK DELA 7.3 / 8
    # DOMINANCE / FLOW / LATE GAME / HISTORY / META
    # ============================================================

    dominance = (danger_h - danger_a) / max(1, danger_total)

    # ============================================================
    # BASE DOMINANCE
    # ============================================================

    # DOMA dominira
    if momentum > 0.04 and dominance > 0.10:
        lam_h_raw *= 1.15

    # GOST dominira
    elif momentum < -0.04 and dominance < -0.10:
        lam_a_raw *= 1.15

    # fallback na danger dominance
    elif dominance > 0.18:
        lam_h_raw *= 1.10

    elif dominance < -0.18:
        lam_a_raw *= 1.10

    # res balanced
    else:
        lam_h_raw *= 1.02
        lam_a_raw *= 1.02

    # ============================================================
    # LATE DOMINANCE KILLER
    # ============================================================

    if minute >= 55:
        if momentum > 0.12 and xg_h > xg_a:
            lam_h_raw *= 1.20
        elif momentum < -0.12 and xg_a > xg_h:
            lam_a_raw *= 1.20

    # ============================================================
    # STRONG LATE DRAW PUSH
    # ============================================================

    if minute >= 72 and abs(score_diff) == 1:

        lam_total_now = lam_h_raw + lam_a_raw

        # HOME lovi
        if score_diff < 0:
            lam_h_raw *= 1.35
            lam_a_raw *= 0.90

            if lam_total_now > 0.40:
                lam_h_raw *= 1.15

        # AWAY lovi
        elif score_diff > 0:
            lam_a_raw *= 1.35
            lam_h_raw *= 0.90

            if lam_total_now > 0.40:
                lam_a_raw *= 1.15

    # ============================================================
    # LATE DRAW PROTECTION
    # ============================================================

    if minute >= 70 and abs(score_diff) == 1:

        lam_total_now = lam_h_raw + lam_a_raw

        # HOME zaostaja
        if score_diff < 0:
            if abs(momentum) < 0.45:
                lam_h_raw *= 1.20
                lam_a_raw *= 0.93

            if lam_total_now > 0.45:
                lam_h_raw *= 1.10

        # AWAY zaostaja
        elif score_diff > 0:
            if abs(momentum) < 0.45:
                lam_a_raw *= 1.20
                lam_h_raw *= 0.93

            if lam_total_now > 0.45:
                lam_a_raw *= 1.10

    # ============================================================
    # LEAD PROTECTION
    # ============================================================

    if minute >= 60:
        if score_diff == -1 and danger_a > danger_h * 1.4:
            lam_a_raw *= 1.12
            lam_h_raw *= 0.88

        elif score_diff == 1 and danger_h > danger_a * 1.4:
            lam_h_raw *= 1.12
            lam_a_raw *= 0.88

    # ============================================================
    # LOSING TEAM LAST PUSH
    # ============================================================

    if minute >= 80:

        # HOME vodi -> AWAY push
        if score_home > score_away:
            if momentum < -0.02 and pressure_a > pressure_h:
                lam_a_raw *= 1.18

            if sot_a > sot_h:
                lam_a_raw *= 1.08

            if abs(danger_h - danger_a) <= 6:
                lam_a_raw *= 1.05

        # AWAY vodi -> HOME push
        elif score_away > score_home:
            if momentum > 0.02 and pressure_h > pressure_a:
                lam_h_raw *= 1.18

            if sot_h > sot_a:
                lam_h_raw *= 1.08

            if abs(danger_h - danger_a) <= 6:
                lam_h_raw *= 1.05

    # ============================================================
    # RED CARD
    # ============================================================

    if red_h > red_a:
        lam_h_raw *= 0.82
        lam_a_raw *= 1.10
    elif red_a > red_h:
        lam_a_raw *= 0.82
        lam_h_raw *= 1.10

    # ============================================================
    # IMPLIED ODDS REALITY CHECK
    # ============================================================

    imp_h, imp_x, imp_a, overround = implied_probs_from_odds(
        odds_home, odds_draw, odds_away
    )

    if imp_h > 0 and imp_a > 0:
        if lam_h_raw > lam_a_raw * 1.90 and imp_h < 0.45 and minute < 35:
            lam_h_raw *= 0.90
        if lam_a_raw > lam_h_raw * 1.90 and imp_a < 0.45 and minute < 35:
            lam_a_raw *= 0.90

    # ============================================================
    # FINAL REALITY CHECK
    # ============================================================

    if minute >= 50:
        if xg_h > xg_a * 1.3 and lam_h_raw <= lam_a_raw:
            lam_h_raw *= 1.12
        elif xg_a > xg_h * 1.3 and lam_a_raw <= lam_h_raw:
            lam_a_raw *= 1.12

    lam_h_raw = clamp(max(0.0, lam_h_raw), 0.0, 1.60)
    lam_a_raw = clamp(max(0.0, lam_a_raw), 0.0, 1.60)

    # ============================================================
    # CONTROL FIX
    # ============================================================

    ratio_h = lam_h_raw / max(0.0001, base_h)
    ratio_a = lam_a_raw / max(0.0001, base_a)

    ratio_h = clamp(ratio_h, 0.55, 1.95)
    ratio_a = clamp(ratio_a, 0.55, 1.95)

    lam_h_raw = base_h * ratio_h
    lam_a_raw = base_a * ratio_a

    # ============================================================
    # APPLY CONTROL LAYER
    # ============================================================

    mult_h = clamp(mult_h, 0.75, 1.45)
    mult_a = clamp(mult_a, 0.75, 1.45)

    lam_h_raw *= mult_h
    lam_a_raw *= mult_a

    # ============================================================
    # CFOS PATCH v1.0 (BIG CHANCE + PRESSURE)
    # ============================================================

    if bc_a >= 2 and minute >= 65:
        lam_a_raw *= 1.25

    if bc_h >= 2 and minute >= 65:
        lam_h_raw *= 1.25

    if pressure_a > pressure_h * 1.6:
        lam_a_raw *= 1.20

    if pressure_h > pressure_a * 1.6:
        lam_h_raw *= 1.20

    lam_h_raw = clamp(lam_h_raw, 0.0, 1.60)
    lam_a_raw = clamp(lam_a_raw, 0.0, 1.60)

    # ============================================================
    # CFOS-XG PRO 77 STABILIZERJI
    # ============================================================

    if minute >= 70 and game_type not in ("PRESSURE", "ATTACK_WAVE", "CHAOS"):
        lam_h_raw *= 0.93
        lam_a_raw *= 0.93

    chaos_index = (tempo_danger * 1.4) + tempo_shots
    if chaos_index > 1.40:
        lam_h_raw *= 1.05
        lam_a_raw *= 1.05

    lam_c_raw = 0.0

    if game_type in ("PRESSURE", "ATTACK_WAVE", "CHAOS"):
        lam_c_raw += 0.015

        if score_diff == 0 and minute >= 65 and game_type == "CHAOS":
            lam_c_raw += 0.02
        elif score_diff == 0 and minute >= 65 and game_type in ("PRESSURE", "ATTACK_WAVE"):
            lam_c_raw += 0.01

        if pressure_total >= 18 and ((xg_total >= 0.9) or (sot_total >= 4) or (danger_total >= 75)):
            lam_c_raw += 0.02

        if (keypasses_h + keypasses_a) >= 8 and minute >= 55:
            lam_c_raw += 0.01

    lam_c_raw = clamp(lam_c_raw, 0.0, 0.08)

    lam_total_raw = lam_h_raw + lam_a_raw + lam_c_raw
    if lam_total_raw > 2.10:
        scale = 2.10 / lam_total_raw
        lam_h_raw *= scale
        lam_a_raw *= scale
        lam_c_raw *= scale
        lam_total_raw = lam_h_raw + lam_a_raw + lam_c_raw

    p_goal_raw = 1 - math.exp(-lam_total_raw) if lam_total_raw > 0 else 0.0

    # ============================================================
    # HISTORY LAMBDA APPLY
    # ============================================================

    history = load_history()

    lf_goal, n_goal = learn_factor_goal(
        history=history,
        minute=minute,
        xg_total=xg_total,
        sot_total=sot_total,
        shots_total=shots_total,
        score_diff=score_diff,
        game_type=game_type,
        danger_total=danger_total
    )

    if history is not None and lf_goal is not None and n_goal >= 3:
        lam_h_raw *= lf_goal
        lam_a_raw *= lf_goal

    lam_h_raw = clamp(lam_h_raw, 0.01, 5.0)
    lam_a_raw = clamp(lam_a_raw, 0.01, 5.0)

    # ============================================================
    # COUNTER PRESSURE DETECTOR
    # ============================================================

    if minute >= 58:

        danger_ratio_h = danger_h / max(1, danger_a)
        danger_ratio_a = danger_a / max(1, danger_h)

        # AWAY pritiska -> HOME counter
        if sot_a > sot_h and danger_ratio_a >= 0.85 and shots_h <= shots_a + 2:
            lam_h_raw *= 1.15

        # HOME pritiska -> AWAY counter
        if sot_h > sot_a and danger_ratio_h >= 0.85 and shots_a <= shots_h + 2:
            lam_a_raw *= 1.15

    # ============================================================
    # LOW VOLUME FINISHER
    # ============================================================

    if minute >= 60:

        if shots_h <= 8 and sot_h <= 2 and momentum < -0.05:
            lam_h_raw *= 1.12

        if shots_a <= 8 and sot_a <= 2 and momentum > 0.05:
            lam_a_raw *= 1.12

    # ============================================================
    # FAKE DOMINANCE FLIP
    # ============================================================

    if minute >= 62:

        if sot_a > sot_h and danger_a >= danger_h * 0.90 and attacks_a < attacks_h:
            lam_h_raw *= 1.10

        if sot_h > sot_a and danger_h >= danger_a * 0.90 and attacks_h < attacks_a:
            lam_a_raw *= 1.10
    # ============================================================
    # GLOBAL LATE BOOST LIMITER (CRITICAL FIX)
    # ============================================================

    if minute >= 70 and abs(score_diff) == 1:

        # max razmerje med ekipama
        max_ratio = 1.75

        if lam_h_raw > lam_a_raw * max_ratio:
            lam_h_raw = lam_a_raw * max_ratio

        if lam_a_raw > lam_h_raw * max_ratio:
            lam_a_raw = lam_h_raw * max_ratio

        # dodatno: omeji absolutno eksplozijo
        lam_total_tmp = lam_h_raw + lam_a_raw

        if lam_total_tmp > 1.35:
            scale = 1.35 / lam_total_tmp
            lam_h_raw *= scale
            lam_a_raw *= scale

    lam_h = clamp(lam_h_raw, 0.0, 1.60)
    lam_a = clamp(lam_a_raw, 0.0, 1.60)
    lam_c = clamp(lam_c_raw * lf_goal * timeline["trend_factor_goal"] * wave["goal"], 0.0, 0.08)

    # ============================================================
    # PRESSURE BOOST
    # ============================================================

    if minute >= 60 and danger_h > danger_a * 2 and tempo_danger > 1.0:
        boost = 1.0 + (danger_h / max(danger_a, 1)) * 0.15
        lam_h *= min(boost, 1.6)

    lam_total = lam_h + lam_a + lam_c

    if lam_total > 2.20:
        scale = 2.20 / lam_total
        lam_h *= scale
        lam_a *= scale
        lam_c *= scale
        lam_total = lam_h + lam_a + lam_c

    # ============================================================
    # SECOND HALF BOOST
    # ============================================================

    if minute >= 46:
        lam_h *= 1.25
        lam_a *= 1.25

    # ============================================================
    # ANTI 0-0 KILLER
    # ============================================================

    if minute >= 55:
        if tempo_danger > 1.2 or tempo_shots > 0.18:
            lam_h *= 1.08
            lam_a *= 1.08

        if abs(momentum) > 0.15:
            lam_h *= 1.06
            lam_a *= 1.06

    lam_h = clamp(lam_h, 0.0, 1.60)
    lam_a = clamp(lam_a, 0.0, 1.60)
    lam_total = lam_h + lam_a + lam_c

    # ============================================================
    # UPSET FILTER
    # ============================================================

    if minute >= 55:

        if imp_h < imp_a and lam_a > lam_h * 1.35:
            lam_a *= 0.88

        if imp_a < imp_h and lam_h > lam_a * 1.35:
            lam_h *= 0.88

    # ============================================================
    # COUNTER GOAL PROTECTION
    # ============================================================

    if minute >= 65:

        if momentum > 0.14 and danger_h > danger_a * 1.5:
            lam_a *= 0.85

        if momentum < -0.14 and danger_a > danger_h * 1.5:
            lam_h *= 0.85

    # ============================================================
    # COUNTER ATTACK RISK
    # ============================================================

    counter_boost_home = 1.0
    counter_boost_away = 1.0

    if score_diff < 0 and minute >= 70:
        if momentum > 0.12 and lam_a < 0.40:
            counter_boost_away = 1.35

    if score_diff > 0 and minute >= 70:
        if momentum < -0.12 and lam_h < 0.40:
            counter_boost_home = 1.35

    lam_h *= counter_boost_home
    lam_a *= counter_boost_away

    # ============================================================
    # LEADING TEAM COUNTER GOAL
    # ============================================================

    counter_boost_home = 1.0
    counter_boost_away = 1.0

    if score_diff > 0:
        if momentum < -0.18 and tempo_shots > 0.18:
            counter_boost_home = 1.22
            counter_boost_away = 0.88

    elif score_diff < 0:
        if momentum > 0.18 and tempo_shots > 0.18:
            counter_boost_away = 1.22
            counter_boost_home = 0.88

    lam_h *= counter_boost_home
    lam_a *= counter_boost_away

    # ============================================================
    # MIN FLOW
    # ============================================================

    if 0 < lam_total < 0.35:
        scale = 0.35 / lam_total
        lam_h *= scale
        lam_a *= scale
        lam_total = lam_h + lam_a + lam_c

    if lam_total > 2.20:
        scale = 2.20 / lam_total
        lam_h *= scale
        lam_a *= scale
        lam_c *= scale
        lam_total = lam_h + lam_a + lam_c

    p_goal = 1 - math.exp(-lam_total) if lam_total > 0 else 0.0

    if (lam_h + lam_a) > 0:
        p_home_next = (lam_h / (lam_h + lam_a)) * p_goal
        p_away_next = (lam_a / (lam_h + lam_a)) * p_goal
    else:
        p_home_next = 0.0
        p_away_next = 0.0

    p_no_goal = 1 - p_goal

    rate_per_min = lam_total / max(1, minutes_left_real)
    p_goal_5 = 1 - math.exp(-rate_per_min * min(5, minutes_left_real))
    p_goal_10 = 1 - math.exp(-rate_per_min * min(10, minutes_left_real))

    pre_h = clamp((score_diff * 0.08) + (lam_h * 0.20) + 0.32, 0.05, 0.85)
    pre_a = clamp((-score_diff * 0.08) + (lam_a * 0.20) + 0.30, 0.05, 0.85)
    pre_x = clamp(1.0 - pre_h - pre_a, 0.05, 0.80)

    # ============================================================
    # DRAW CRUSHERS
    # ============================================================

    if minute >= 30 and tempo_danger >= 1.15:
        pre_x *= 0.80

    if abs(momentum) > 0.12:
        pre_x *= 0.82

    if minute >= 60:
        if abs(lam_h - lam_a) > 0.12:
            pre_x *= 0.75

    if tempo_danger > 1.2:
        pre_x *= 0.80

    if minute >= 60 and game_type in ("PRESSURE", "ATTACK_WAVE"):
        if tempo_danger >= 1.10 and tempo_shots >= 0.15:
            pre_x *= 0.75

        if pressure_total >= 14:
            pre_x *= 0.85

        if p_goal >= 0.35:
            pre_x *= 0.85

    if minute >= 45 and score_diff == 0 and tempo_shots < 0.18 and abs(momentum) < 0.08:
        pre_x = pre_x + (pre_x * 0.08)

    if abs(lam_h - lam_a) < 0.12 and lam_total > 0.45 and abs(momentum) < 0.08:
        pre_x *= 1.02

    s_pre = pre_h + pre_x + pre_a
    pre_h /= s_pre
    pre_x /= s_pre
    pre_a /= s_pre

    # ============================================================
    # MONTE CARLO
    # ============================================================

    sim_used = adaptive_simulations(pre_h, pre_x, pre_a)

    w_h = 0
    w_x = 0
    w_a = 0

    for _ in range(sim_used):
        gh, ga = bivariate_poisson_sample(lam_h, lam_a, lam_c)
        fh = score_home + gh
        fa = score_away + ga

        if fh > fa:
            w_h += 1
        elif fh == fa:
            w_x += 1
        else:
            w_a += 1

    mc_h_raw = w_h / sim_used
    mc_x_raw = w_x / sim_used
    mc_a_raw = w_a / sim_used

    if minute >= 75 and abs(lam_h - lam_a) > 0.10:
        mc_x_raw *= 0.75 if minute >= 80 else 0.78

    if minute >= 60 and game_type in ("PRESSURE", "ATTACK_WAVE"):
        if tempo_danger >= 1.10 and p_goal >= 0.42:
            mc_x_raw *= 0.90

        if pressure_total >= 14 and abs(momentum) >= 0.06:
            mc_x_raw *= 0.93

    # ============================================================
    # LEARN FACTOR 1X2
    # ============================================================

    rh, rx, ra, n_1x2 = learn_factor_1x2(
        history=history,
        minute=minute,
        xg_total=xg_total,
        sot_total=sot_total,
        shots_total=shots_total,
        score_diff=score_diff,
        game_type=game_type,
        danger_total=danger_total
    )

    mc_h_adj = mc_h_raw * rh
    mc_x_adj = mc_x_raw * min(rx, 1.05)
    mc_a_adj = mc_a_raw * ra

    # ============================================================
    # HISTORY SCORE BIAS
    # ============================================================

    hist_bias = history_score_bias(
        history=history,
        minute=minute,
        xg_total=xg_total,
        sot_total=sot_total,
        shots_total=shots_total,
        score_diff=score_diff,
        game_type=game_type,
        danger_total=danger_total
    )

    if hist_bias is not None:
        hist_n = hist_bias["n"]
        hist_home = hist_bias["p_home"]
        hist_draw = hist_bias["p_draw"]
        hist_away = hist_bias["p_away"]
    else:
        hist_n = 0
        hist_home = mc_h_adj
        hist_draw = mc_x_adj
        hist_away = mc_a_adj

    # ============================================================
    # SAVE BUCKET HISTORY
    # ============================================================

    hist_home_bucket = hist_home
    hist_draw_bucket = hist_draw
    hist_away_bucket = hist_away

    # ============================================================
    # MATCH MEMORY
    # ============================================================

    mem_rows = load_match_memory(home, away)
    mem_n = len(mem_rows)

    mem_home = 0.0
    mem_draw = 0.0
    mem_away = 0.0

    for r in mem_rows:
        res = r.get("result")

        if res == "HOME":
            mem_home += 1
        elif res == "DRAW":
            mem_draw += 1
        elif res == "AWAY":
            mem_away += 1

    if mem_n > 0:
        mem_home /= mem_n
        mem_draw /= mem_n
        mem_away /= mem_n

    # ============================================================
    # MONTE CARLO HISTORY
    # ============================================================

    mc_n = 50
    mc_home_hist = mc_h_adj
    mc_draw_hist = mc_x_adj
    mc_away_hist = mc_a_adj

    # ============================================================
    # COMBINE ALL HISTORY
    # ============================================================

    total_n = hist_n + mem_n + mc_n

    if total_n > 0:
        hist_home = (
                            hist_home_bucket * hist_n +
                            mem_home * mem_n +
                            mc_home_hist * mc_n
                    ) / total_n

        hist_draw = (
                            hist_draw_bucket * hist_n +
                            mem_draw * mem_n +
                            mc_draw_hist * mc_n
                    ) / total_n

        hist_away = (
                            hist_away_bucket * hist_n +
                            mem_away * mem_n +
                            mc_away_hist * mc_n
                    ) / total_n

    # ============================================================
    # HISTORY BIAS PRINT
    # ============================================================

    print()
    print("============= HISTORY BIAS =============")

    print("BUCKET")
    print("HOME", round(hist_home_bucket, 4))
    print("DRAW", round(hist_draw_bucket, 4))
    print("AWAY", round(hist_away_bucket, 4))
    print("N   ", hist_n)

    print()
    print("MATCH MEMORY")
    print("HOME", round(mem_home, 4))
    print("DRAW", round(mem_draw, 4))
    print("AWAY", round(mem_away, 4))
    print("N   ", mem_n)

    print()
    print("MONTE CARLO")
    print("HOME", round(mc_home_hist, 4))
    print("DRAW", round(mc_draw_hist, 4))
    print("AWAY", round(mc_away_hist, 4))
    print("N   ", mc_n)

    print()
    print("FINAL HISTORY")
    print("HOME", round(hist_home, 4))
    print("DRAW", round(hist_draw, 4))
    print("AWAY", round(hist_away, 4))
    print("TOTAL", total_n)

    print("========================================")
    print()

    # ============================================================
    # REAL-TIME vs HISTORY MIX
    # ============================================================

    rt_strength = (
            abs(lam_h - lam_a) * 2 +
            abs(p_home_next - p_away_next) +
            abs(mc_h_adj - mc_a_adj)
    )

    if rt_strength > 1:
        rt_strength = 1

    effective_hist_n = hist_n + mem_n

    if mem_n >= 2:
        effective_hist_n += 10

    hist_conf = effective_hist_n / 50
    if hist_conf > 1:
        hist_conf = 1

    hist_weight = hist_conf * (1 - rt_strength * 0.6) * 0.45
    rt_weight = 1 - hist_weight

    mc_h_adj = mc_h_adj * rt_weight + hist_home * hist_weight
    mc_x_adj = mc_x_adj * rt_weight + hist_draw * hist_weight
    mc_a_adj = mc_a_adj * rt_weight + hist_away * hist_weight

    s = mc_h_adj + mc_x_adj + mc_a_adj
    if s > 0:
        mc_h_adj /= s
        mc_x_adj /= s
        mc_a_adj /= s

    # ============================================================
    # META CALIBRATION
    # ============================================================

    mc_h_before_meta = mc_h_adj
    mc_x_before_meta = mc_x_adj
    mc_a_before_meta = mc_a_adj

    mc_h_adj, mc_x_adj, mc_a_adj = meta_calibrate_1x2(
        mc_h=mc_h_adj,
        mc_x=mc_x_adj,
        mc_a=mc_a_adj,
        imp_h=imp_h,
        imp_x=imp_x,
        imp_a=imp_a,
        lam_h=lam_h,
        lam_a=lam_a,
        p_goal=p_goal,
        momentum=momentum,
        pressure_h=pressure_h,
        pressure_a=pressure_a,
        xg_h=xg_h,
        xg_a=xg_a,
        minute=minute,
        score_diff=score_diff,
        team_power=team_power,
        hist_n=hist_n
    )

    print("\n================ META CALIBRATION ================")
    print("Minute".ljust(18), minute)

    print("BEFORE META")
    print("HOME".ljust(8), f"{mc_h_before_meta:.4f}")
    print("DRAW".ljust(8), f"{mc_x_before_meta:.4f}")
    print("AWAY".ljust(8), f"{mc_a_before_meta:.4f}")

    print("\nAFTER META")
    print("HOME".ljust(8), f"{mc_h_adj:.4f}")
    print("DRAW".ljust(8), f"{mc_x_adj:.4f}")
    print("AWAY".ljust(8), f"{mc_a_adj:.4f}")

    print("=================================================\n")

    s = mc_h_adj + mc_x_adj + mc_a_adj
    if s > 1e-9:
        mc_h_adj /= s
        mc_x_adj /= s
        mc_a_adj /= s
    else:
        mc_h_adj, mc_x_adj, mc_a_adj = mc_h_raw, mc_x_raw, mc_a_raw
    # ZAČETEK DELA 7.4/ 8

    # ============================================================
    # EXTREME SCORE EQUALIZER (FORCE EQUALIZER)
    # ============================================================
    if minute >= 70 and abs(score_diff) == 1:

        # HOME izgublja
        if score_diff < 0:
            lam_h *= 1.55
            lam_a *= 0.75
            lam_h += 0.45

        # AWAY izgublja
        else:
            lam_a *= 1.55
            lam_h *= 0.75
            lam_a += 0.45

        # recompute
        lam_total = lam_h + lam_a + lam_c

        p_goal = 1 - math.exp(-lam_total)

        if lam_total > 0:
            p_home_next = lam_h / lam_total * p_goal
            p_away_next = lam_a / lam_total * p_goal
    # ============================================================
    # LATE DRAW PROTECTION AFTER HISTORY
    # samo če ekipa, ki izgublja, res pritiska za izenačenje
    # ============================================================
    if minute >= 72 and abs(score_diff) == 1 and p_goal >= 0.40:

        draw_protection = False

        # DOMA izgublja -> doma mora res pritiskati
        if score_diff < 0:
            if (
                    momentum >= 0.08
                    and pressure_h >= pressure_a * 0.95
                    and p_home_next >= 0.24
                    and lam_h >= lam_a * 0.55
            ):
                draw_protection = True

        # GOST izgublja -> gost mora res pritiskati
        elif score_diff > 0:
            if (
                    momentum <= -0.08
                    and pressure_a >= pressure_h * 0.95
                    and p_away_next >= 0.24
                    and lam_a >= lam_h * 0.55
            ):
                draw_protection = True

        if draw_protection:

            mc_x_adj *= 1.22

            if score_diff < 0:
                mc_a_adj *= 0.94
            elif score_diff > 0:
                mc_h_adj *= 0.94

            s = mc_h_adj + mc_x_adj + mc_a_adj
            if s > 0:
                mc_h_adj /= s
                mc_x_adj /= s
                mc_a_adj /= s

    # ============================================================
    # LATE DRAW LIMITER AFTER LEARNING
    # ============================================================

    exact_sim_used = adaptive_exact_simulations(max(mc_h_adj, mc_x_adj, mc_a_adj))
    top_scores, hist_bias, exact_hist = final_score_prediction(
        score_home, score_away, lam_h, lam_a, lam_c,
        history, minute, xg_total, sot_total, shots_total, score_diff, game_type, danger_total,
        sim_count=exact_sim_used

    )

    if minute >= 75 and score_diff == 0:
        if tempo_danger >= 1.55 and shots_total >= 15:
            mc_x_adj *= 0.90

        if abs(danger_h - danger_a) >= 15:
            mc_x_adj *= 0.93

        if p_goal >= 0.38:
            mc_x_adj *= 0.94

        s = mc_h_adj + mc_x_adj + mc_a_adj
        if s > 1e-9:
            mc_h_adj /= s
            mc_x_adj /= s
            mc_a_adj /= s

        exact_sim_used = adaptive_exact_simulations(max(mc_h_adj, mc_x_adj, mc_a_adj))
        top_scores, hist_bias, exact_hist = final_score_prediction(
            score_home, score_away, lam_h, lam_a, lam_c,
            history, minute, xg_total, sot_total, shots_total, score_diff, game_type, danger_total,
            sim_count=exact_sim_used
        )

    # ============================================================
    # EXTREME LATE EQUALIZER OVERRIDE (FINAL FORCE)
    # ============================================================
    if minute >= 70 and abs(score_diff) == 1:

        # AWAY vodi
        if score_diff < 0:
            mc_x_adj = 0.45
            mc_a_adj = 0.45
            mc_h_adj = 0.10

        # HOME vodi
        elif score_diff > 0:
            mc_x_adj = 0.45
            mc_h_adj = 0.45
            mc_a_adj = 0.10
    edge_h = edge_from_model(mc_h_adj, imp_h)
    edge_x = edge_from_model(mc_x_adj, imp_x)
    edge_a = edge_from_model(mc_a_adj, imp_a)

    conf = confidence_score_base(p_goal, mc_h_adj, mc_x_adj, mc_a_adj, timeline["n"])

    # DOMINANCE BONUS
    dominance = max(mc_h_adj, mc_x_adj, mc_a_adj)
    dominance_bonus = max(0, dominance - 0.55) * 20
    conf += dominance_bonus

    conf = clamp(conf, 1.0, 100.0)

    band = confidence_band(conf)

    ng_signal = next_goal_signal(p_home_next, p_away_next)
    m_signal = match_signal(p_goal, p_home_next, p_away_next)

    lge = lge_notes(game_type, tempo_notes, xgr_notes, wave["active"])

    pass_acc_h = pass_acc_rate(acc_pass_h, passes_h)
    pass_acc_a = pass_acc_rate(acc_pass_a, passes_a)
    d2s_h = danger_to_shot_conv(shots_h, danger_h)
    d2s_a = danger_to_shot_conv(shots_a, danger_a)
    shot_q_h = shot_quality(xg_h, shots_h)
    shot_q_a = shot_quality(xg_a, shots_a)
    sot_r_h = sot_ratio(sot_h, shots_h)
    sot_r_a = sot_ratio(sot_a, shots_a)
    bc_r_h = big_chance_ratio(bc_h, shots_h)
    bc_r_a = big_chance_ratio(bc_a, shots_a)

    # ==========================================
    # LIVE BET FILTER
    # ==========================================

    max_mc = max(mc_h_adj, mc_x_adj, mc_a_adj)

    use_filter = False
    use_reason = "FILTER FAIL"

    # BALANCED filter
    if minute >= 60 and game_type == "BALANCED" and conf >= 56 and max_mc >= 0.55:
        use_filter = True
        use_reason = "PASS | BALANCED | 60+ | conf>=56 | max_mc>=0.55"

    # CHAOS filter
    elif minute >= 70 and game_type == "CHAOS" and conf >= 60 and max_mc >= 0.62 and p_goal >= 0.35:
        use_filter = True
        use_reason = "PASS | CHAOS | 70+ | conf>=60 | max_mc>=0.62"

    # PRESSURE / ATTACK_WAVE optional
    elif minute >= 65 and game_type in ("PRESSURE", "ATTACK_WAVE") and conf >= 58 and max_mc >= 0.58:
        use_filter = True
        use_reason = "PASS | PRESSURE/WAVE | 65+ | conf>=58 | max_mc>=0.58"

    # SLOW filter
    elif minute >= 50 and game_type == "SLOW" and conf >= 60 and max_mc >= 0.65 and score_diff != 0:
        use_filter = True
        use_reason = "PASS | SLOW | 50+ | conf>=60 | max_mc>=0.65"

    predikcija = moje_predvidevanje({
        "edge_h": edge_h,
        "edge_x": edge_x,
        "edge_a": edge_a,
        "mc_h_adj": mc_h_adj,
        "mc_x_adj": mc_x_adj,
        "mc_a_adj": mc_a_adj,
        "p_goal": p_goal,
        "p_no_goal": p_no_goal,
        "top_scores": top_scores
    })

    if minute >= 75 and odds_draw < 1.55:
        predikcija["moja_stava"] = "NO BET"
        predikcija["razlog_stave"] = "LATE TRAP"

    # ============================================================
    # SAVE FINAL RESULT (MATCH MEMORY)
    # ============================================================

    if minute >= 90:

        if score_home > score_away:
            result = "HOME"
        elif score_home < score_away:
            result = "AWAY"
        else:
            result = "DRAW"

        row = {
            "home": home,
            "away": away,
            "minute": minute,

            "prediction_1x2": predikcija["napoved_izida"],
            "prediction_score": predikcija["napoved_rezultata"],

            "result_1x2": result,
            "result_score": f"{score_home}-{score_away}"
        }

        file = "cfos75_match_memory.csv"
        file_exists = os.path.exists(file)

        with open(file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "home",
                "away",
                "minute",
                "prediction_1x2",
                "prediction_score",
                "result_1x2",
                "result_score"
            ])

            if not file_exists or f.tell() == 0:
                writer.writeheader()

            writer.writerow(row)

    return {

        "home": home, "away": away, "minute": minute,
        "score_home": score_home, "score_away": score_away, "score_diff": score_diff,
        "xg_h": xg_h, "xg_a": xg_a, "xg_total": xg_total,
        "shots_h": shots_h, "shots_a": shots_a, "shots_total": shots_total,
        "sot_h": sot_h, "sot_a": sot_a, "sot_total": sot_total,
        "attacks_h": attacks_h, "attacks_a": attacks_a,
        "danger_h": danger_h, "danger_a": danger_a, "danger_total": danger_total,
        "corners_h": corners_h, "corners_a": corners_a,
        "odds_home": odds_home, "odds_draw": odds_draw, "odds_away": odds_away,
        "lam_h_raw": lam_h_raw, "lam_a_raw": lam_a_raw, "lam_c_raw": lam_c_raw, "lam_total_raw": lam_total_raw,
        "lam_h": lam_h, "lam_a": lam_a, "lam_c": lam_c, "lam_total": lam_total,
        "p_goal_raw": p_goal_raw, "p_goal": p_goal, "p_no_goal": p_no_goal,
        "p_home_next": p_home_next, "p_away_next": p_away_next,
        "p_goal_5": p_goal_5, "p_goal_10": p_goal_10,
        "mc_h_raw": mc_h_raw, "mc_x_raw": mc_x_raw, "mc_a_raw": mc_a_raw,
        "mc_h_adj": mc_h_adj, "mc_x_adj": mc_x_adj, "mc_a_adj": mc_a_adj,
        "lf_goal": lf_goal, "n_goal": n_goal, "rh": rh, "rx": rx, "ra": ra, "n_1x2": n_1x2,
        "timeline": timeline, "wave": wave, "game_type": game_type,
        "tempo_shots": tempo_shots, "tempo_att": tempo_att, "tempo_danger": tempo_danger,
        "xg_rate_h": xg_rate_h, "xg_rate_a": xg_rate_a, "xg_rate_total": xg_rate_total,
        "attack_h": attack_h, "attack_a": attack_a, "danger_idx_h": danger_idx_h, "danger_idx_a": danger_idx_a,
        "pressure_h": pressure_h, "pressure_a": pressure_a, "pressure_total": pressure_total,
        "momentum": momentum, "synthetic_xg_used": synthetic_xg_used,
        "minutes_left_real": minutes_left_real, "sim_used": sim_used, "exact_sim_used": exact_sim_used,
        "tempo_notes": tempo_notes, "xgr_notes": xgr_notes,
        "y_h": y_h, "y_a": y_a, "red_h": red_h, "red_a": red_a,
        "blocked_h": blocked_h, "blocked_a": blocked_a,
        "bcm_h": bcm_h, "bcm_a": bcm_a,
        "gk_saves_h": gk_saves_h, "gk_saves_a": gk_saves_a,
        "passes_h": passes_h, "passes_a": passes_a,
        "acc_pass_h": acc_pass_h, "acc_pass_a": acc_pass_a,
        "tackles_h": tackles_h, "tackles_a": tackles_a,
        "inter_h": inter_h, "inter_a": inter_a,
        "clear_h": clear_h, "clear_a": clear_a,
        "duels_h": duels_h, "duels_a": duels_a,
        "offsides_h": offsides_h, "offsides_a": offsides_a,
        "throw_h": throw_h, "throw_a": throw_a,
        "fouls_h": fouls_h, "fouls_a": fouls_a,
        "prematch_h": prematch_h, "prematch_a": prematch_a,
        "prev_odds_home": prev_odds_home, "prev_odds_draw": prev_odds_draw, "prev_odds_away": prev_odds_away,
        "elo_h": elo_h, "elo_a": elo_a,
        "imp_h": imp_h, "imp_x": imp_x, "imp_a": imp_a, "overround": overround,
        "edge_h": edge_h, "edge_x": edge_x, "edge_a": edge_a,
        "confidence": conf, "confidence_band": band,
        "next_goal_signal": ng_signal, "match_signal": m_signal,
        "lge": lge,
        "top_scores": top_scores, "hist_bias": hist_bias, "exact_hist": exact_hist,
        "pass_acc_h": pass_acc_h, "pass_acc_a": pass_acc_a,
        "d2s_h": d2s_h, "d2s_a": d2s_a,
        "shot_q_h": shot_q_h, "shot_q_a": shot_q_a,
        "sot_r_h": sot_r_h, "sot_r_a": sot_r_a,
        "bc_r_h": bc_r_h, "bc_r_a": bc_r_a,
        "keypasses_h": keypasses_h, "keypasses_a": keypasses_a,
        "crosses_h": crosses_h, "crosses_a": crosses_a,
        "aerials_h": aerials_h, "aerials_a": aerials_a,
        "dribbles_h": dribbles_h, "dribbles_a": dribbles_a,
        "final_third_h": final_third_h, "final_third_a": final_third_a,
        "long_balls_h": long_balls_h, "long_balls_a": long_balls_a,
        "bc_created_h": bc_created_h, "bc_created_a": bc_created_a,
        "action_left": action_left, "action_mid": action_mid, "action_right": action_right,
        "napoved_izida": predikcija["napoved_izida"],
        "napoved_rezultata": predikcija["napoved_rezultata"],
        "moja_stava": predikcija["moja_stava"],
        "razlog_stave": predikcija["razlog_stave"],
        "max_mc": max_mc,
        "use_filter": use_filter,
        "use_reason": use_reason
    }


# ============================================================
# KONEC DELA 7 / 8
# ============================================================
# ============================================================
# CFOS-XG PRO 75 TITAN
# ZAČETEK DELA 8.1 / 8
# IZPIS / ANALIZA / MAIN
# ============================================================

def print_stat(name, h, a):
    if h is None:
        h = 0
    if a is None:
        a = 0

    try:
        h = int(float(h))
    except:
        pass

    try:
        a = int(float(a))
    except:
        pass

    print(f"{name.ljust(22)} {str(h).rjust(5)} vs {str(a).ljust(5)}")


def print_dominance(r):
    h = (
            r.get("danger_h", 0) * 2.0 +
            r.get("attacks_h", 0) * 0.4 +
            r.get("shots_h", 0) * 1.5 +
            r.get("sot_h", 0) * 2.5 +
            r.get("final_third_h", 0) * 0.3
    )

    a = (
            r.get("danger_a", 0) * 2.0 +
            r.get("attacks_a", 0) * 0.4 +
            r.get("shots_a", 0) * 1.5 +
            r.get("sot_a", 0) * 2.5 +
            r.get("final_third_a", 0) * 0.3
    )

    if h > a * 1.15:
        side = "DOMA KONTROLA"
        col = GREEN
    elif a > h * 1.15:
        side = "GOST KONTROLA"
        col = GREEN
    else:
        side = "URAVNOTEŽENO"
        col = YELLOW

    print("")
    print("--------------- DOMINANCE ----------------")
    print(btxt(side, col, True))


def print_match_direction(r):
    h = (
            r.get("momentum", 0) * 5 +
            r.get("pressure_h", 0) -
            r.get("pressure_a", 0) +
            r.get("danger_h", 0) * 0.15 -
            r.get("danger_a", 0) * 0.15
    )

    if h > 1.5:
        txt = "→→→ DOMA PRITISK"
        col = GREEN
    elif h < -1.5:
        txt = "←←← GOST PRITISK"
        col = GREEN
    else:
        txt = "↔ URAVNOTEŽENO"
        col = YELLOW

    print("")
    print("--------------- MATCH DIRECTION ----------------")
    print(btxt(txt, col, True))


def format_prob_line(label, p):
    col = color_prob(p)
    return f"{label.ljust(28)} {btxt(str(pct(p)) + ' %', col, True)}"


def format_edge_line(name, model_p, market_p, edge):
    edge_col = color_edge(edge)
    return f"{name.ljust(12)} {str(round(model_p * 100, 1)).rjust(8)} {str(round(market_p * 100, 1)).rjust(10)} {btxt(str(round(edge * 100, 1)).rjust(10), edge_col, True)}"


# =========================================================
# CFOS FOCUS ENGINE (PRECISION)
# =========================================================

def focus_engine(minute, score_diff):
    # -----------------------------------------------------
    # 0–15
    # -----------------------------------------------------
    if minute <= 15:
        return [
            "tempo_shots",
            "tempo_danger",
            "xg_rate_total",
            "game_type",
            "IGNORE: momentum, MC, META"
        ]

    # -----------------------------------------------------
    # 15–30
    # -----------------------------------------------------
    if minute <= 30:
        return [
            "tempo_shots",
            "tempo_danger",
            "xg_rate_total",
            "pressure_total",
            "P(goal)",
            "IGNORE: final 1X2"
        ]

    # -----------------------------------------------------
    # 30–45
    # -----------------------------------------------------
    if minute <= 45:
        if score_diff == 0:
            return [
                "momentum",
                "SOT_ratio",
                "pressure_total",
                "lambda_total",
                "Away/Home next goal"
            ]
        else:
            return [
                "comeback_pressure",
                "lambda_stronger_side",
                "momentum",
                "tempo_danger"
            ]

    # -----------------------------------------------------
    # 45–60
    # -----------------------------------------------------
    if minute <= 60:
        if score_diff == 0:
            return [
                "momentum",
                "pressure_total",
                "SOT_ratio",
                "lambda_total",
                "next_goal_signal"
            ]
        else:
            return [
                "comeback_probability",
                "attack_wave",
                "momentum",
                "lambda_losing_team"
            ]

    # -----------------------------------------------------
    # 60–75
    # -----------------------------------------------------
    if minute <= 75:
        if score_diff == 0:
            return [
                "momentum",
                "lambda_home",
                "lambda_away",
                "draw_crusher",
                "P(goal)"
            ]
        else:
            return [
                "comeback",
                "kill_game",
                "attack_wave",
                "timeline_trend"
            ]

    # -----------------------------------------------------
    # 75+
    # -----------------------------------------------------
    if score_diff == 0:
        return [
            "P(goal)",
            "lambda_stronger",
            "momentum",
            "MC_exact"
        ]

    return [
        "last_goal_probability",
        "comeback_pressure",
        "time_decay",
        "kill_game_lambda"
    ]


def print_top_signals(r):
    signals = []

    if r["danger_h"] > 0 and r["danger_a"] > 0:
        if r["danger_h"] > r["danger_a"] * 1.60:
            signals.append(("Danger dominance DOMA", RED))
        elif r["danger_a"] > r["danger_h"] * 1.60:
            signals.append(("Danger dominance GOST", RED))

    if r["wave"]["active"]:
        signals.append(("Attack wave aktiven", RED))

    if r["tempo_danger"] >= 1.30:
        signals.append(("Tempo danger spike", YELLOW))

    if abs(r["momentum"]) >= 0.20:
        side = "DOMA" if r["momentum"] > 0 else "GOST"
        signals.append((f"Momentum {side}", YELLOW))

    best_edge = max(r["edge_h"], r["edge_x"], r["edge_a"])

    if best_edge >= 0.05:
        signals.append(("Value edge zaznan", GREEN))

    if r["p_goal"] >= 0.65:
        signals.append(("Visoka verjetnost gola", GREEN))

    print(f"\n{CYAN}{BOLD}================ TOP SIGNALI ================ {RESET}\n")
    if not signals:
        print("Ni močnih signalov.")
        return

    for i, (txt, col) in enumerate(signals[:5], 1):
        print(f"{i}. {btxt(txt, col, True)}")


def print_5_korakov(r):
    print(f"\n{CYAN}{BOLD}================ 5 KLJUČNIH KORAKOV [PRO 75] ================ {RESET}\n")

    if (
            r["momentum"] < -0.08 and
            r["pressure_a"] > r["pressure_h"] * 1.20
    ):
        txt1 = "1. Pressure -> GOST PRITISK (REAL)"

    elif (
            r["momentum"] > 0.08 and
            r["pressure_h"] > r["pressure_a"] * 1.20
    ):
        txt1 = "1. Pressure -> DOMA PRITISK (REAL)"

    elif r["danger_h"] > r["danger_a"] * 1.20:
        txt1 = "1. Danger attacks -> DOMA pritisk"

    elif r["danger_a"] > r["danger_h"] * 1.20:
        txt1 = "1. Danger attacks -> GOST pritisk"

    else:
        txt1 = "1. Game -> URAVNOTEŽENO"

    print(f"{RED}{BOLD}{txt1}{RESET}")

    if r["tempo_danger"] >= 1.20 or r["tempo_shots"] >= 0.20:
        txt2 = "2. Tempo danger / tempo shots -> VISOK TEMPO"
    elif r["tempo_danger"] >= 0.85 or r["tempo_shots"] >= 0.12:
        txt2 = "2. Tempo danger / tempo shots -> SREDNJI TEMPO"
    else:
        txt2 = "2. Tempo danger / tempo shots -> NIZEK TEMPO"
    print(f"{YELLOW}{BOLD}{txt2}{RESET}")

    if r["wave"]["active"] and r["timeline"]["trend_factor_goal"] >= 1.05:
        txt3 = "3. Attack wave / timeline trend -> MOČAN VAL"
    elif r["wave"]["active"]:
        txt3 = "3. Attack wave / timeline trend -> ATTACK WAVE AKTIVEN"
    elif r["timeline"]["trend_factor_goal"] >= 1.08:
        txt3 = "3. Attack wave / timeline trend -> TIMELINE RASTE"
    elif r["timeline"]["trend_factor_goal"] <= 0.95:
        txt3 = "3. Attack wave / timeline trend -> TIMELINE ZAVIRA"
    else:
        txt3 = "3. Attack wave / timeline trend -> BREZ MOČNEGA SIGNALA"
    print(f"{MAGENTA}{BOLD}{txt3}{RESET}")

    if r["p_goal"] >= 0.60:
        txt4 = "4. Any goal / next goal signal -> VISOKA VERJETNOST GOLA"
    elif r["p_goal"] >= 0.35:
        if r["p_home_next"] > r["p_away_next"] and r["p_home_next"] >= 0.20:
            txt4 = "4. Any goal / next goal signal -> SREDNJI GOL | DOMA RAHLA PREDNOST"
        elif r["p_away_next"] > r["p_home_next"] and r["p_away_next"] >= 0.20:
            txt4 = "4. Any goal / next goal signal -> SREDNJI GOL | GOST RAHLA PREDNOST"
        else:
            txt4 = "4. Any goal / next goal signal -> SREDNJI GOL | URAVNOTEŽENO"
    else:
        txt4 = "4. Any goal / next goal signal -> NIZKA VERJETNOST GOLA"
    print(f"{GREEN}{BOLD}{txt4}{RESET}")

    best_edge = max(r["edge_h"], r["edge_x"], r["edge_a"])
    if best_edge >= 0.05:
        if best_edge == r["edge_h"]:
            txt5 = f"5. EDGE proti marketu -> VALUE na 1 ({round(best_edge * 100, 1)} %)"
        elif best_edge == r["edge_x"]:
            txt5 = f"5. EDGE proti marketu -> VALUE na X ({round(best_edge * 100, 1)} %)"
        else:
            txt5 = f"5. EDGE proti marketu -> VALUE na 2 ({round(best_edge * 100, 1)} %)"
    elif best_edge <= -0.05:
        txt5 = f"5. EDGE proti marketu -> MARKET PROTI MODELU ({round(best_edge * 100, 1)} %)"
    else:
        txt5 = f"5. EDGE proti marketu -> BREZ MOČNE VALUE PREDNOSTI ({round(best_edge * 100, 1)} %)"
    print(f"{BLUE}{BOLD}{txt5}{RESET}")


def cfos_analiza_sistema(r):
    print(f"\n{CYAN}{BOLD}================ CFOS ANALIZA SISTEMA ================ {RESET}\n")

    if r["danger_h"] > r["danger_a"] * 1.35:
        print(btxt("• Danger napadi močno na strani DOMA", RED, True))
    elif r["danger_a"] > r["danger_h"] * 1.35:
        print(btxt("• Danger napadi močno na strani GOST", RED, True))
    else:
        print(btxt("• Danger napadi niso izrazito enostranski", YELLOW, True))

    if r["tempo_danger"] >= 1.20:
        print(btxt("• Tempo nevarnih napadov je visok", YELLOW, True))
    else:
        print("• Tempo nevarnih napadov je normalen ali nizek")

    if r["wave"]["active"]:
        print(btxt("• Attack wave je AKTIVEN", RED, True))
    else:
        print("• Attack wave ni aktiven")

    if r["timeline"]["trend_factor_goal"] >= 1.08:
        print(btxt("• Timeline kaže rast verjetnosti gola", GREEN, True))
    elif r["timeline"]["trend_factor_goal"] <= 0.95:
        print(btxt("• Timeline zavira gol", YELLOW, True))
    else:
        print("• Timeline je nevtralen")

    if r["p_goal"] >= 0.55:
        print(btxt("• Model vidi visoko verjetnost gola", GREEN, True))
    elif r["p_goal"] <= 0.25:
        print(btxt("• Model vidi nizko verjetnost gola", RED, True))
    else:
        print(btxt("• Model vidi srednjo verjetnost gola", YELLOW, True))

    if r["p_home_next"] > r["p_away_next"] and r["p_home_next"] >= 0.35:
        print(btxt("• Naslednji gol je bolj verjeten DOMA", GREEN, True))
    elif r["p_away_next"] > r["p_home_next"] and r["p_away_next"] >= 0.35:
        print(btxt("• Naslednji gol je bolj verjeten GOST", GREEN, True))
    else:
        print(btxt("• Naslednji gol ni dovolj jasen", YELLOW, True))

    # =========================================================
    # CFOS TREND OVERRIDE (8/8 OUTPUT FIX)
    # =========================================================

    napoved = r["napoved_izida"]
    stava = r["moja_stava"]
    razlog = r["razlog_stave"]

    minute = r["minute"]

    hist_goal = 0
    exact_no_goal = 0

    if r.get("hist_bias") is not None:
        hist_goal = r["hist_bias"].get("p_goal", 0)

    if r.get("exact_hist") is not None:
        exact_no_goal = r["exact_hist"].get("p_no_goal", 0)

    # =====================================================
    # HISTORY FILTER (RULE 1/2/3)
    # =====================================================

    history_block = False

    # RULE 1
    if minute >= 60 and hist_goal <= 0.25 and exact_no_goal >= 0.70:
        history_block = True
        razlog = "RULE1 STRONG HISTORY NO GOAL"

    # RULE 2
    elif r["p_goal"] >= 0.70 and hist_goal <= 0.30 and exact_no_goal >= 0.65:
        history_block = True
        razlog = "RULE2 MODEL HISTORY CONFLICT"

    # RULE 3
    elif minute >= 75 and hist_goal <= 0.35 and exact_no_goal >= 0.60:
        history_block = True
        razlog = "RULE3 LATE HISTORY LOCK"

    # =====================================================
    # AUTO BET DECISION
    # =====================================================

    if history_block:

        stava = "NO BET"

    else:

        # STRONG DRAW
        if minute >= 60 and r["mc_x_adj"] >= 0.65:
            stava = "NO BET"
            razlog = "STRONG DRAW"

        # LATE GOAL
        elif minute >= 70 and r["p_goal"] >= 0.35:
            stava = "LATE GOAL"
            razlog = "LATE PRESSURE"

        # NEXT GOAL
        elif r["p_home_next"] >= 0.48:
            stava = "NEXT GOAL HOME"
            razlog = "NEXT GOAL SIGNAL"

        elif r["p_away_next"] >= 0.48:
            stava = "NEXT GOAL AWAY"
            razlog = "NEXT GOAL SIGNAL"

        # MOMENTUM
        elif abs(r["momentum"]) > 0.15:
            if r["momentum"] > 0:
                stava = "NEXT GOAL HOME"
                razlog = "MOMENTUM HOME"
            else:
                stava = "NEXT GOAL AWAY"
                razlog = "MOMENTUM AWAY"

        else:
            stava = "NO BET"
            razlog = "NO EDGE"

    # =====================================================
    # NEXT GOAL override
    # =====================================================

    if not history_block:

        if r["p_away_next"] >= 0.48 and r["momentum"] < -0.08:
            napoved = "GOST"
            stava = "2"
            razlog = "NEXT GOAL + MOMENTUM GOST"

        elif r["p_home_next"] >= 0.48 and r["momentum"] > 0.08:
            napoved = "DOMAČI"
            stava = "1"
            razlog = "NEXT GOAL + MOMENTUM DOMA"

        # HIGH GOAL + MOMENTUM
        elif r["p_goal"] >= 0.60 and abs(r["momentum"]) > 0.12:

            if r["momentum"] > 0:
                napoved = "DOMAČI"
                stava = "1"
            else:
                napoved = "GOST"
                stava = "2"

            razlog = "HIGH GOAL + MOMENTUM"
    print(f"\n{MAGENTA}Moje predvidevanje:{RESET}")
    print("Napoved izida".ljust(28), btxt(napoved, CYAN, True))
    rezultat = r["napoved_rezultata"]

    sh = r["score_home"]
    sa = r["score_away"]

    if r["p_away_next"] >= 0.48 and r["momentum"] < -0.08:
        rezultat = f"{sh}-{sa + 1}"

    elif r["p_home_next"] >= 0.48 and r["momentum"] > 0.08:
        rezultat = f"{sh + 1}-{sa}"

    # ZAČETEK DELA 8.2 / 8
    # =====================================================
    # AUTO BET DECISION (CMD)
    # =====================================================

    # =====================================================
    # AUTO BET DECISION (CMD)
    # =====================================================

    minute = r["minute"]
    score_diff = r["score_diff"]

    edge_home = r["edge_h"]
    edge_draw = r["edge_x"]
    edge_away = r["edge_a"]

    mc_home = r["mc_h_adj"]
    mc_draw = r["mc_x_adj"]
    mc_away = r["mc_a_adj"]

    # 1X2 VALUE EDGE IMA PREDNOST
    if edge_away >= 0.08 and mc_away >= 0.65:
        stava = "2"
        razlog = "VALUE EDGE AWAY"

    elif edge_home >= 0.08 and mc_home >= 0.65:
        stava = "1"
        razlog = "VALUE EDGE HOME"

    elif edge_draw >= 0.08 and mc_draw >= 0.55:
        stava = "X"
        razlog = "VALUE EDGE DRAW"

    # STRONG DRAW
    elif minute >= 60 and mc_draw >= 0.65:
        stava = "NO BET"
        razlog = "STRONG DRAW"

    # LATE GOAL
    elif (
            minute >= 70
            and r["p_goal"] >= 0.65
            and r["lam_total"] >= 1.05
            and abs(score_diff) <= 1
    ):
        stava = "LATE GOAL"
        razlog = "LATE PRESSURE"

    # NEXT GOAL
    elif r["p_home_next"] >= 0.48:
        stava = "NEXT GOAL HOME"
        razlog = "NEXT GOAL SIGNAL"

    elif r["p_away_next"] >= 0.48:
        stava = "NEXT GOAL AWAY"
        razlog = "NEXT GOAL SIGNAL"

    # MOMENTUM
    elif abs(r["momentum"]) > 0.15:
        if r["momentum"] > 0:
            stava = "NEXT GOAL HOME"
            razlog = "MOMENTUM HOME"
        else:
            stava = "NEXT GOAL AWAY"
            razlog = "MOMENTUM AWAY"

    # LATE COMEBACK RISK
    elif (
            minute >= 84
            and abs(score_diff) == 1
            and r["sot_h"] >= r["sot_a"]
            and r["shots_h"] >= r["shots_a"]
    ):
        stava = "NO BET"
        razlog = "LATE COMEBACK RISK"

    # DEFAULT
    else:
        stava = "NO BET"
        razlog = "NO EDGE"

    print("Napoved rezultata".ljust(28), btxt(rezultat, CYAN, True))
    print("Kaj bi stavil".ljust(28), btxt(stava, GREEN if stava != "NO BET" else YELLOW, True))
    print("Zakaj".ljust(28), razlog)
    print(f"\n{MAGENTA}Na kaj moraš biti najbolj pozoren:{RESET}")
    print(f"{btxt('- Danger attacks', YELLOW, True)}")
    print(f"{btxt('- Tempo danger / tempo shots', ORANGE, True)}")
    print(f"{btxt('- Attack wave / timeline trend', RED, True)}")
    print(f"{btxt('- Any goal / next goal signal', GREEN, True)}")
    print(f"{btxt('- EDGE proti marketu', BLUE, True)}")


def izpis_rezultata(r):
    print(f"\n{CYAN}{BOLD}================ CFOS-XG PRO 75 TITAN [POLNA VERZIJA] ================={RESET}\n")

    print("MATCH".ljust(28), r["home"], "vs", r["away"])
    print("Minute".ljust(28), r["minute"])
    print("Score".ljust(28), f'{r["score_home"]}-{r["score_away"]}')
    print("Score diff".ljust(28), r["score_diff"])
    print(cl("TEST XG", "BARVA XG", COL_XG, True))
    print(cl("TEST PM", "BARVA PM", COL_PM, True))
    print(cl("TEST LAMBDA", "BARVA LAMBDA", COL_LAMBDA, True))
    print(cl("TEST MC", "BARVA MC", COL_MC, True))
    print(cl("xG home", round(r["xg_h"], 3), COL_XG, True))
    print(cl("xG away", round(r["xg_a"], 3), COL_XG, True))
    print(cl("xG source", "SYNTHETIC" if r["synthetic_xg_used"] else "REAL", COL_XG, True))

    print(f"\n{MAGENTA}--------------- LEARNING ----------------{RESET}\n")
    print("Bucket".ljust(28),
          f'{bucket_minute(r["minute"])} | xG:{bucket_xg(r["xg_total"])} | SOT:{bucket_sot(r["sot_total"])} | SH:{bucket_shots(r["shots_total"])} | SD:{bucket_score_diff(r["score_diff"])} | DNG:{bucket_danger(r["danger_total"])}')
    print("Game type".ljust(28), r["game_type"])
    print("Learn factor (GOAL)".ljust(28), round(r["lf_goal"], 3), f'(bucket n: {r["n_goal"]})')
    print("Learn ratios (1X2)".ljust(28),
          f'H {round(r["rh"], 3)} | D {round(r["rx"], 3)} | A {round(r["ra"], 3)} (bucket n: {r["n_1x2"]})')

    print(f"\n{MAGENTA}--------------- MATCH MEMORY ----------------{RESET}\n")
    print("Timeline snapshots".ljust(28), r["timeline"]["n"])
    print("Timeline goal factor".ljust(28), round(r["timeline"]["trend_factor_goal"], 3))
    print("Timeline HOME factor".ljust(28), round(r["timeline"]["trend_home"], 3))
    print("Timeline AWAY factor".ljust(28), round(r["timeline"]["trend_away"], 3))
    print("True momentum".ljust(28), r["timeline"]["true_momentum_text"])
    print("Attack wave".ljust(28), "YES" if r["wave"]["active"] else "NO")
    print("LGE".ljust(28), r["lge"])

    print(f"\n{MAGENTA}--------------- TEMPO / RATE ----------------{RESET}\n")
    print(cl("Tempo shots", round(r["tempo_shots"], 3), COL_TEMPO))
    print(cl("Tempo attacks", round(r["tempo_att"], 3), COL_TEMPO))
    print(cl("Tempo danger", round(r["tempo_danger"], 3), COL_TEMPO))
    print(cl("xG rate total", round(r["xg_rate_total"], 4), COL_XG))
    print(cl("xG rate HOME", round(r["xg_rate_h"], 4), COL_XG))
    print(cl("xG rate AWAY", round(r["xg_rate_a"], 4), COL_XG))
    print("Minutes left est.".ljust(28), r["minutes_left_real"])

    print(f"\n{MAGENTA}--------------- EXTENDED STATS ----------------{RESET}\n")
    print("Attacks".ljust(28), round(r["attacks_h"], 2), round(r["attacks_a"], 2))
    print("Blocked shots".ljust(28), round(r["blocked_h"], 2), round(r["blocked_a"], 2))
    print("Big ch. missed".ljust(28), round(r["bcm_h"], 2), round(r["bcm_a"], 2))
    print("Corners".ljust(28), round(r["corners_h"], 2), round(r["corners_a"], 2))
    print("GK saves".ljust(28), round(r["gk_saves_h"], 2), round(r["gk_saves_a"], 2))
    print("Passes".ljust(28), round(r["passes_h"], 2), round(r["passes_a"], 2))
    print("Accurate passes".ljust(28), round(r["acc_pass_h"], 2), round(r["acc_pass_a"], 2))
    print("Tackles".ljust(28), round(r["tackles_h"], 2), round(r["tackles_a"], 2))
    print("Interceptions".ljust(28), round(r["inter_h"], 2), round(r["inter_a"], 2))
    print("Clearances".ljust(28), round(r["clear_h"], 2), round(r["clear_a"], 2))
    print("Duels won".ljust(28), round(r["duels_h"], 2), round(r["duels_a"], 2))
    print("Offsides".ljust(28), round(r["offsides_h"], 2), round(r["offsides_a"], 2))
    print("Throw-ins".ljust(28), round(r["throw_h"], 2), round(r["throw_a"], 2))
    print("Fouls".ljust(28), round(r["fouls_h"], 2), round(r["fouls_a"], 2))
    print("Pass acc rate".ljust(28), round(r["pass_acc_h"], 3), round(r["pass_acc_a"], 3))
    print("Danger->shot conv".ljust(28), round(r["d2s_h"], 3), round(r["d2s_a"], 3))
    print("Shot quality".ljust(28), round(r["shot_q_h"], 3), round(r["shot_q_a"], 3))
    print("SOT ratio".ljust(28), round(r["sot_r_h"], 3), round(r["sot_r_a"], 3))
    print("Big chance ratio".ljust(28), round(r["bc_r_h"], 3), round(r["bc_r_a"], 3))
    print("Game type".ljust(28), r["game_type"])

    print(f"\n{MAGENTA}--------------- FOTMOB EXTRA ----------------{RESET}\n")
    print("Key passes".ljust(28), round(r["keypasses_h"], 2), round(r["keypasses_a"], 2))
    print("Crosses".ljust(28), round(r["crosses_h"], 2), round(r["crosses_a"], 2))
    print("Aerial duels".ljust(28), round(r["aerials_h"], 2), round(r["aerials_a"], 2))
    print("Dribbles".ljust(28), round(r["dribbles_h"], 2), round(r["dribbles_a"], 2))
    print("Final third entries".ljust(28), round(r["final_third_h"], 2), round(r["final_third_a"], 2))
    print("Long balls".ljust(28), round(r["long_balls_h"], 2), round(r["long_balls_a"], 2))
    print("Big ch. created".ljust(28), round(r["bc_created_h"], 2), round(r["bc_created_a"], 2))
    print("Action areas".ljust(28), round(r["action_left"], 2), round(r["action_mid"], 2), round(r["action_right"], 2))

    print(f"\n{MAGENTA}--------------- MOMENTUM ENGINE ----------------{RESET}\n")
    print(
        f"{btxt('Attack index'.ljust(28), COL_PM, True)} {btxt(str(round(r['attack_h'], 2)), COL_PM, True)} {btxt(str(round(r['attack_a'], 2)), COL_PM, True)}")
    print(
        f"{btxt('Danger index'.ljust(28), COL_PM, True)} {btxt(str(round(r['danger_idx_h'], 2)), COL_PM, True)} {btxt(str(round(r['danger_idx_a'], 2)), COL_PM, True)}")
    print(
        f"{btxt('Pressure'.ljust(28), COL_PM, True)} {btxt(str(round(r['pressure_h'], 2)), COL_PM, True)} {btxt(str(round(r['pressure_a'], 2)), COL_PM, True)}")
    print(cl("Momentum", round(r["momentum"], 3), COL_PM, True))

    print(f"\n{MAGENTA}--------------- LAMBDA ENGINE ----------------{RESET}\n")
    print(cl("Lambda home (RAW)", round(r["lam_h_raw"], 3), COL_LAMBDA))
    print(cl("Lambda away (RAW)", round(r["lam_a_raw"], 3), COL_LAMBDA))
    print(cl("Lambda shared (RAW)", round(r["lam_c_raw"], 3), COL_LAMBDA))
    print(cl("Lambda total (RAW)", round(r["lam_total_raw"], 3), COL_LAMBDA))
    print(cl("P(goal) RAW", f'{pct(r["p_goal_raw"])} %', COL_LAMBDA))
    print(cl("Lambda home (CAL)", round(r["lam_h"], 3), COL_LAMBDA))
    print(cl("Lambda away (CAL)", round(r["lam_a"], 3), COL_LAMBDA))
    print(cl("Lambda shared (CAL)", round(r["lam_c"], 3), COL_LAMBDA))
    print(cl("Lambda total (CAL)", round(r["lam_total"], 3), COL_LAMBDA))

    print(f"\n{MAGENTA}--------------- GOAL PROBABILITY (CAL) ----------------{RESET}\n")
    print(cl("Any goal", f'{pct(r["p_goal"])} %', COL_NEXT))
    print(cl("Home next goal", f'{pct(r["p_home_next"])} %', COL_NEXT))
    print(cl("Away next goal", f'{pct(r["p_away_next"])} %', COL_NEXT))
    print(cl("No goal", f'{pct(r["p_no_goal"])} %', COL_NEXT))
    print(cl("Goal next 5 min", f'{pct(r["p_goal_5"])} %', COL_NEXT))
    print(cl("Goal next 10 min", f'{pct(r["p_goal_10"])} %', COL_NEXT))

    print(f"\n{MAGENTA}--------------- META CALIBRATION ----------------{RESET}\n")

    print("META HOME".ljust(28), round(r["mc_h_adj"], 4))
    print("META DRAW".ljust(28), round(r["mc_x_adj"], 4))
    print("META AWAY".ljust(28), round(r["mc_a_adj"], 4))

    print(f"\n{MAGENTA}--------------- MONTE CARLO ----------------{RESET}\n")
    print(cl("Monte Carlo sims", r["sim_used"], COL_MC))
    print(cl("Exact score sims", r["exact_sim_used"], COL_MC))
    print(cl("Away win (RAW)", f'{pct(r["mc_a_raw"])} %', COL_MC, True))
    print(cl("Draw (RAW)", f'{pct(r["mc_x_raw"])} %', COL_MC, True))
    print(cl("Home win (RAW)", f'{pct(r["mc_h_raw"])} %', COL_MC, True))
    print(cl("Away win (CAL)", f'{pct(r["mc_a_adj"])} %', COL_MC, True))
    print(cl("Draw (CAL)", f'{pct(r["mc_x_adj"])} %', COL_MC, True))
    print(cl("Home win (CAL)", f'{pct(r["mc_h_adj"])} %', COL_MC, True))

    print(f"\n{MAGENTA}--------------- FINAL SCORE PREDICTION ----------------{RESET}\n")
    if r["top_scores"]:
        print("Most likely final".ljust(28), f'{r["top_scores"][0][0]} | {pct(r["top_scores"][0][1])} %')
        for i, (score, p) in enumerate(r["top_scores"][:5], 1):
            print(f"Top {i}".ljust(28), f'{score} | {pct(p)} %')
    else:
        print("Most likely final".ljust(28), "N/A")

    print(f"\n{MAGENTA}--------------- HISTORY SCORE BIAS ----------------{RESET}\n")
    if r["hist_bias"] is None:
        print("History bucket".ljust(28), "Ni dovolj podatkov")
    else:
        print("History bucket".ljust(28), f'n={r["hist_bias"]["n"]}')
        # HISTORY STRENGTH
        hist_n = r["hist_bias"]["n"]

        if hist_n < 20:
            strength = "WEAK"
        elif hist_n < 40:
            strength = "OK"
        elif hist_n < 80:
            strength = "GOOD"
        else:
            strength = "STRONG"

        print("History strength".ljust(28), strength)
        print("Hist HOME".ljust(28), f'{pct(r["hist_bias"]["p_home"])} %')
        print("Hist DRAW".ljust(28), f'{pct(r["hist_bias"]["p_draw"])} %')
        print("Hist AWAY".ljust(28), f'{pct(r["hist_bias"]["p_away"])} %')
        print("Hist GOAL".ljust(28), f'{pct(r["hist_bias"]["p_goal"])} %')

        # HISTORY PREDICTION
        hist_home = r["hist_bias"]["p_home"]
        hist_draw = r["hist_bias"]["p_draw"]
        hist_away = r["hist_bias"]["p_away"]

        if hist_home > hist_draw and hist_home > hist_away:
            hist_pred = "HOME"
        elif hist_away > hist_home and hist_away > hist_draw:
            hist_pred = "AWAY"
        else:
            hist_pred = "DRAW"

        print("History prediction".ljust(28), hist_pred)

    print(f"\n{MAGENTA}--------------- EXACT SCORE HISTORY ----------------{RESET}\n")
    if r["exact_hist"] is None:
        print("Exact history".ljust(28), "Ni dovolj podatkov")
    else:
        print("Exact history".ljust(28), f'n={r["exact_hist"]["n"]}')
        print("Exact no goal".ljust(28), f'{pct(r["exact_hist"]["p_no_goal"])} %')
        print("Exact goal".ljust(28), f'{pct(r["exact_hist"]["p_goal"])} %')

    print(f"\n{MAGENTA}--------------- 1X2 (MODEL vs MARKET) ----------------{RESET}\n")
    print("Outcome       Model %   Market %     EDGE %")
    print("------------------------------------------")
    print(format_edge_line("HOME", r["mc_h_adj"], r["imp_h"], r["edge_h"]))
    print(format_edge_line("DRAW", r["mc_x_adj"], r["imp_x"], r["edge_x"]))
    print(format_edge_line("AWAY", r["mc_a_adj"], r["imp_a"], r["edge_a"]))

    print(f"\n{MAGENTA}--------------- TEAM / MARKET ----------------{RESET}\n")
    print("Prematch strength".ljust(28), r["prematch_h"], r["prematch_a"])
    print("ELO".ljust(28), r["elo_h"], r["elo_a"])
    print("Prev odds".ljust(28), r["prev_odds_home"], r["prev_odds_draw"], r["prev_odds_away"])
    print("Market overround".ljust(28), f'{round(r["overround"] * 100, 2)} %')

    print(f"\n{MAGENTA}--------------- CONFIDENCE ----------------{RESET}\n")
    print("Confidence".ljust(28), btxt(f'{round(r["confidence"], 1)} /100', color_conf(r["confidence"]), True))
    print("Confidence band".ljust(28), btxt(r["confidence_band"], color_conf(r["confidence"]), True))

    print(f"\n{MAGENTA}--------------- LIVE FILTER ----------------{RESET}\n")
    print("Max MC".ljust(28), round(r["max_mc"], 3))
    print("Use filter".ljust(28), "YES" if r["use_filter"] else "NO")
    print("Filter reason".ljust(28), r["use_reason"])
    print(f"\n{MAGENTA}--------------- CFOS FOCUS ENGINE ----------------{RESET}\n")

    minute = r["minute"]
    score_diff = r["score_diff"]

    if minute <= 30:
        print("- GLEJ: tempo_shots")
        print("- GLEJ: tempo_danger")
        print("- GLEJ: xg_rate_total")
        print("- GLEJ: P(goal)")

    elif minute <= 60:

        if score_diff == 0:
            print("- GLEJ: momentum")
            print("- GLEJ: SOT ratio")
            print("- GLEJ: pressure")
            print("- GLEJ: lambda total")
            print("- GLEJ: next goal signal")
        else:
            print("- GLEJ: comeback pressure")
            print("- GLEJ: momentum")
            print("- GLEJ: attack wave")
            print("- GLEJ: lambda losing team")

    elif minute <= 75:

        if score_diff == 0:
            print("- GLEJ: momentum")
            print("- GLEJ: lambda home")
            print("- GLEJ: lambda away")
            print("- GLEJ: draw crusher")
        else:
            print("- GLEJ: comeback")
            print("- GLEJ: kill game")
            print("- GLEJ: timeline trend")

    else:

        if score_diff == 0:
            print("- GLEJ: last goal probability")
            print("- GLEJ: momentum")
            print("- GLEJ: lambda stronger")
        else:
            print("- GLEJ: comeback last")
            print("- GLEJ: time decay")
            print("- GLEJ: kill game")

    print_5_korakov(r)

    print(f"\n{CYAN}{BOLD}================ NEXT GOAL SIGNAL ================ {RESET}\n")
    ng_color = GREEN if ("DOMAČI" in r["next_goal_signal"] or "GOSTUJOČI" in r["next_goal_signal"]) else YELLOW
    print(btxt(r["next_goal_signal"], ng_color, True))

    print(f"\n{CYAN}{BOLD}================ MATCH SIGNAL ================ {RESET}\n")
    if r["p_goal"] < 0.25:
        print(btxt("• NIZKA VERJETNOST GOLA", RED, True))
    elif r["p_goal"] >= 0.55:
        print(btxt("• VISOKA VERJETNOST GOLA", GREEN, True))
    else:
        print(btxt("• SREDNJA VERJETNOST GOLA", YELLOW, True))
    print(btxt(r["match_signal"], CYAN, True))

    print_top_signals(r)
    cfos_analiza_sistema(r)

    print(f"\n{CYAN}=========================================================== {RESET}")


# ============================================================
# CFOS ACCURACY COUNTER
# ============================================================

import csv
import os


def cfos_accuracy():
    file = "cfos75_accuracy_log.csv"

    if not os.path.exists(file):
        return

    total = 0
    hit_1x2 = 0

    with open(file, newline='', encoding="utf-8") as f:
        r = csv.DictReader(f)

        for row in r:

            total += 1

            correct = row.get("correct")

            if correct == "1":
                hit_1x2 += 1

    if total == 0:
        return

    print()
    print("============= CFOS ACCURACY =============")
    print("Matches         ", total)
    print("1X2 correct     ", hit_1x2, f"({round(hit_1x2 / total * 100, 1)}%)")
    print("========================================")
    print()


def main():
    print(f"\n{CYAN}{BOLD}================ CFOS-XG PRO 75 TITAN [POLNA VERZIJA] ================={RESET}\n")
    print("CSV FORMAT PRO 75:")
    print("0 home")
    print("1 away")
    print("2 odds_home")
    print("3 odds_draw")
    print("4 odds_away")
    print("5 minute")
    print("6 score_home")
    print("7 score_away")
    print("8 xg_home")
    print("9 xg_away")
    print("10 shots_home")
    print("11 shots_away")
    print("12 sot_home")
    print("13 sot_away")
    print("14 attacks_home")
    print("15 attacks_away")
    print("16 dangerous_attacks_home")
    print("17 dangerous_attacks_away")
    print("18 big_chances_home")
    print("19 big_chances_away")
    print("20 yellow_home")
    print("21 yellow_away")
    print("22 red_home")
    print("23 red_away")
    print("24 possession_home")
    print("25 possession_away")
    print("26 blocked_shots_home")
    print("27 blocked_shots_away")
    print("28 big_chances_missed_home")
    print("29 big_chances_missed_away")
    print("30 corners_home")
    print("31 corners_away")
    print("32 gk_saves_home")
    print("33 gk_saves_away")
    print("34 passes_home")
    print("35 passes_away")
    print("36 accurate_passes_home")
    print("37 accurate_passes_away")
    print("38 tackles_home")
    print("39 tackles_away")
    print("40 interceptions_home")
    print("41 interceptions_away")
    print("42 clearances_home")
    print("43 clearances_away")
    print("44 duels_won_home")
    print("45 duels_won_away")
    print("46 offsides_home")
    print("47 offsides_away")
    print("48 throw_ins_home")
    print("49 throw_ins_away")
    print("50 fouls_home")
    print("51 fouls_away")
    print("52 prematch_strength_home")
    print("53 prematch_strength_away")
    print("54 prev_odds_home")
    print("55 prev_odds_draw")
    print("56 prev_odds_away")
    print("57 elo_home")
    print("58 elo_away")
    print("59 keypasses_home")
    print("60 keypasses_away")
    print("61 crosses_home")
    print("62 crosses_away")
    print("63 tackles_home_extra")
    print("64 tackles_away_extra")
    print("65 interceptions_home_extra")
    print("66 interceptions_away_extra")
    print("67 clearances_home_extra")
    print("68 clearances_away_extra")
    print("69 duels_home_extra")
    print("70 duels_away_extra")
    print("71 aerials_home")
    print("72 aerials_away")
    print("73 dribbles_home")
    print("74 dribbles_away")
    print("75 throw_ins_home_extra")
    print("76 throw_ins_away_extra")
    print("77 final_third_entries_home")
    print("78 final_third_entries_away")
    print("79 long_balls_home")
    print("80 long_balls_away")
    print("81 gk_saves_home_extra")
    print("82 gk_saves_away_extra")
    print("83 big_chances_created_home")
    print("84 big_chances_created_away")
    print("85 action_left")
    print("86 action_middle")
    print("87 action_right")
    print("88 pass_accuracy_home_extra")
    print("89 pass_accuracy_away_extra")
    print("")
    print("Če daš manj podatkov, manjkajoči bodo avtomatsko 0.")
    print("Če daš več FotMob podatkov, jih bo PRO 75 uporabil.")
    print("")

    line = input("Prilepi CSV:\n").strip()
    data = parse_csv_line(line)

    rezultat = izracunaj_model(data)

    print("")
    print("--------------- EXTRA STATS ----------------")

    print_stat("PASSES", rezultat.get("passes_h"), rezultat.get("passes_a"))
    print_stat("DUELS", rezultat.get("duels_h"), rezultat.get("duels_a"))
    print_stat("FOULS", rezultat.get("fouls_h"), rezultat.get("fouls_a"))
    print_stat("OFFSIDES", rezultat.get("offsides_h"), rezultat.get("offsides_a"))

    print_stat("KEY PASSES", rezultat.get("keypasses_h"), rezultat.get("keypasses_a"))
    print_stat("CROSSES", rezultat.get("crosses_h"), rezultat.get("crosses_a"))
    print_stat("LONG BALLS", rezultat.get("long_balls_h"), rezultat.get("long_balls_a"))

    print_stat("TACKLES", rezultat.get("tackles_h"), rezultat.get("tackles_a"))
    print_stat("INTERCEPT", rezultat.get("inter_h"), rezultat.get("inter_a"))
    print_stat("CLEARANCES", rezultat.get("clear_h"), rezultat.get("clear_a"))

    print_stat("AERIALS", rezultat.get("aerials_h"), rezultat.get("aerials_a"))
    print_stat("DRIBBLES", rezultat.get("dribbles_h"), rezultat.get("dribbles_a"))
    print_stat("FINAL THIRD", rezultat.get("final_third_h"), rezultat.get("final_third_a"))

    print_dominance(rezultat)
    print_match_direction(rezultat)

    izpis_rezultata(rezultat)

    cfos_accuracy()

    ans = input("\nKončni rezultat (enter za skip) format H-A, npr. 2-1 : ").strip()
    if ans:
        try:

            fh, fa = ans.replace(" ", "").split("-")
            final_h = int(fh)
            final_a = int(fa)
            # ==========================================
            # LOG ZA ACCURACY ANALIZO
            # ==========================================

            prediction = str(rezultat["napoved_izida"]).strip().upper()

            if prediction in ["HOME", "1", "DOMAČI", "DOMACI"]:
                prediction = "DOMAČI"
            elif prediction in ["AWAY", "2", "GOST"]:
                prediction = "GOST"
            elif prediction in ["DRAW", "X", "REMI"]:
                prediction = "REMI"

            if final_h > final_a:
                final_result = "DOMAČI"
            elif final_a > final_h:
                final_result = "GOST"
            else:
                final_result = "REMI"

            correct = 1 if prediction == final_result else 0

            with open("cfos75_accuracy_log.csv", "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                if f.tell() == 0:
                    writer.writerow([
                        "home",
                        "away",
                        "minute",
                        "prediction",
                        "final_result",
                        "correct"
                    ])

                writer.writerow([
                    rezultat["home"],
                    rezultat["away"],
                    rezultat["minute"],
                    prediction,
                    final_result,
                    correct
                ])
            finalize_snapshots(final_h, final_a, rezultat["home"], rezultat["away"])
            cfos_accuracy()

        except Exception as e:
            print("Napaka pri branju končnega rezultata:", e)

    else:
        snap = input("Shrani snapshot? (y/n): ").strip().lower()
        if snap == "y":
            save_snapshot(
                home=rezultat["home"],
                away=rezultat["away"],
                minute=rezultat["minute"],
                xg_total=rezultat["xg_total"],
                sot_total=rezultat["sot_total"],
                shots_total=rezultat["shots_total"],
                score_diff=rezultat["score_diff"],
                odds_home=rezultat["odds_home"],
                odds_draw=rezultat["odds_draw"],
                odds_away=rezultat["odds_away"],
                lam_total_raw=rezultat["lam_total_raw"],
                p_goal_raw=rezultat["p_goal_raw"],
                mc_h_raw=rezultat["mc_h_raw"],
                mc_x_raw=rezultat["mc_x_raw"],
                mc_a_raw=rezultat["mc_a_raw"],
                score_home=rezultat["score_home"],
                score_away=rezultat["score_away"],
                game_type=rezultat["game_type"],
                danger_total=rezultat["danger_total"]
            )


if __name__ == "__main__":
    main()

# ============================================================
# KONEC DELA 8 / 8
# ============================================================


# ============================================================
# FINAL NEXT GOAL RECALC (CRITICAL)
# ============================================================

try:
    lam_total = lam_h + lam_a + lam_c

    if lam_total > 0:
        p_goal = 1 - math.exp(-lam_total)
        p_no_goal = math.exp(-lam_total)
    else:
        p_goal = 0.0
        p_no_goal = 1.0

    lam_attack = lam_h + lam_a

    if lam_attack > 0:
        p_home_next = (lam_h / lam_attack) * p_goal
        p_away_next = (lam_a / lam_attack) * p_goal
    else:
        p_home_next = 0.0
        p_away_next = 0.0

    # ============================================================
    # NEXT GOAL CONSISTENCY FIX
    # ============================================================

    if 'danger_h' in locals() and 'danger_a' in locals():
        if danger_h > danger_a and p_away_next > p_home_next:
            p_home_next *= 1.15

        if danger_a > danger_h and p_home_next > p_away_next:
            p_away_next *= 1.15

    # normalize
    s = p_home_next + p_away_next
    if s > 0:
        p_home_next /= s
        p_away_next /= s

except:
    pass

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE

# CFOS PATCH PRESERVE SIZE
