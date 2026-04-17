# ============================================================
# CFOS-XG PRO 75 TITAN - VERSION 7-3
# FIXED PRODUCTION VERSION (LUCKY-7-3.py)
# ZAČETEK DELA 1 / 8
# OSNOVA SISTEMA
# ============================================================

import math
import random
import os
import time
import csv
from collections import defaultdict
from io import StringIO
import builtins

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
MATCH_RESULT_FILE = "cfos75_match_results.csv"
CLEAN_SNAPSHOT_FILE = "cfos_clean_snapshots.csv"
# Vsaka odločitev bet_decision (enaka logika kot izpis) — za kalibracijo / backtest v Excelu.
BET_DECISION_LOG = "cfos75_bet_decision_log.csv"


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


# ===============================
# PRO CMD: AUTO SIGNAL + HIGHLIGHTS
# ===============================
def highlight_goal_prob(p):
    p = float(p or 0.0)
    if p < 0.35:
        return btxt(f"{p*100:.2f}% ❌", RED, True)
    if p > 0.55:
        return btxt(f"{p*100:.2f}% ✔", GREEN, True)
    return btxt(f"{p*100:.2f}%", YELLOW, True)


def highlight_conf(c):
    c = float(c or 0.0)
    if c >= 0.70:
        return btxt(f"{c*100:.1f}% ✔", GREEN, True)
    if c < 0.60:
        return btxt(f"{c*100:.1f}% ❌", RED, True)
    return btxt(f"{c*100:.1f}%", YELLOW, True)


def auto_signal(goal_prob, smart_pred, smart_conf):
    goal_prob = float(goal_prob or 0.0)
    smart_pred = str(smart_pred or "").strip().upper()
    smart_conf = float(smart_conf or 0.0)

    if goal_prob < 0.35:
        return btxt(f">>> NO BET (LOW GOAL PROB {goal_prob*100:.0f}%)", RED, True)
    if smart_pred in ("HOME", "AWAY") and smart_conf >= 0.65:
        return btxt(f">>> BET: {smart_pred} ✔ (CONF {smart_conf*100:.0f}%)", GREEN, True)
    return btxt(">>> NO CLEAR EDGE", YELLOW, True)


def auto_signal_final(r):
    """
    Zgornji banner mora vedno slediti KONČNI odločitvi (BET DECISION),
    ne internemu SMART/NEXT GOAL signalu (lahko je drugačen).
    """
    bet = str(r.get("final_auto_bet", "") or "").strip().upper()
    conf_word = str(r.get("final_auto_conf", "") or "").strip().upper()
    reason = str(r.get("final_auto_reason", "") or "").strip()

    conf_map = {
        "HIGH": 0.78,
        "MEDIUM": 0.62,
        "LOW": 0.35,
        "LOCKED": 0.88,
    }
    conf_val = conf_map.get(conf_word, 0.0)

    if bet in ("", "NO BET", "NONE"):
        tail = f" ({reason})" if reason else ""
        return btxt(f">>> NO BET{tail}", RED, True)

    tail = f" ({reason})" if reason else ""
    return btxt(f">>> BET: {bet} ✔ (CONF {conf_val*100:.0f}%){tail}", GREEN, True)


def print_decision_levels_snapshot(r):
    """
    Pod zgornjim bannerjem: stanje igre, naslednji gol, najverjetnejši izid, končna stava.
    Namen: NEXT GOAL ≠ najverjetnejši rezultat ≠ končna stava (brez drugega '>>>' bannerja).
    """
    gs = str(r.get("game_state", "") or "").strip()
    if not gs:
        gs = "N/A"

    ng_smart = r.get("next_goal_prediction_smart") or {}
    sp = str(ng_smart.get("prediction", "") or "").strip().upper()
    sc = float(ng_smart.get("confidence", 0) or 0)
    if sp in ("HOME", "AWAY"):
        ng_line = f"{sp} (smart {sc * 100:.0f}%)"
    else:
        base = str(r.get("next_goal_prediction", "") or "").strip().upper()
        if base in ("HOME", "AWAY"):
            ng_line = base
        else:
            ph = float(r.get("p_home_next", 0) or 0)
            pa = float(r.get("p_away_next", 0) or 0)
            if ph > pa + 0.02:
                ng_line = "HOME"
            elif pa > ph + 0.02:
                ng_line = "AWAY"
            else:
                ng_line = "NEJASNO"

    tops = r.get("top_scores") or []
    if tops:
        s0, p0 = tops[0][0], float(tops[0][1] or 0)
        top_line = f"{s0} ({p0 * 100:.2f}%)"
    else:
        top_line = "N/A"

    fb = str(r.get("final_auto_bet", "") or "").strip().upper()
    if fb in ("", "NONE"):
        fb = "NO BET"
    fr = str(r.get("final_auto_reason", "") or "").strip()
    bet_line = fb + (f" — {fr}" if fr else "")

    print(f"{CYAN}{BOLD}--- SLIKA ODLOČITVE (4 nivoji) ---{RESET}")
    bm = str(r.get("bet_mode") or "DIRECTION").strip().upper()
    print(f"{'Način tekme:'.ljust(22)} {btxt(bm, MAGENTA if bm == 'GOAL_EVENT' else CYAN, True)}")
    if bm == "GOAL_EVENT":
        adv = str(r.get("goal_event_market_advisory") or "").strip()
        gre = str(r.get("goal_event_reason") or "").strip()
        if adv:
            print(f"{'PRO trg (advisory):'.ljust(22)} {btxt(adv, GREEN, True)}")
        if gre:
            print(f"{'Razlog načina:'.ljust(22)} {btxt(gre, YELLOW, False)}")
    elif bm in ("FREEZE", "LOW_EVENT"):
        bre = str(r.get("bet_mode_reason") or "").strip()
        if bre:
            print(f"{'Razlog načina:'.ljust(22)} {btxt(bre, YELLOW, False)}")
    cm = str(r.get("control_mode") or "").strip().upper()
    if cm:
        cr = str(r.get("control_reason") or "").strip()
        line = cm + (f" — {cr}" if cr else "")
        print(f"{'Kontrola (mode):'.ljust(22)} {btxt(line, GREEN, True)}")
    print(f"{'Stanje igre:'.ljust(22)} {btxt(gs, WHITE, False)}")
    print(f"{'Naslednji gol:'.ljust(22)} {btxt(ng_line, COL_NEXT, True)}")
    print(f"{'Najver. rezultat:'.ljust(22)} {btxt(top_line, CYAN, True)}")
    print(
        f"{'Končna stava:'.ljust(22)} "
        f"{btxt(bet_line, GREEN if fb != 'NO BET' else YELLOW, True)}"
    )


def print_value_detector_block(r):
    """
    FINAL LAYER (decision support): interpretacija + value, BREZ spreminjanja bet_decision.
    Izpis tik pred BET DECISION (CAPTURED). Ni dela LAMBDA/MOMENTUM/NEXT GOAL sekcij.
    """
    minute = int(float(r.get("minute", 0) or 0))
    lam_h = float(r.get("lam_h", 0) or 0)
    lam_a = float(r.get("lam_a", 0) or 0)
    edge_h = float(r.get("edge_h", 0) or 0)
    edge_a = float(r.get("edge_a", 0) or 0)
    tempo_shots = float(r.get("tempo_shots", 0) or 0)
    tempo_danger = float(r.get("tempo_danger", 0) or 0)
    tempo_hi = (tempo_shots > 0.18) or (tempo_danger > 1.2)
    ph = float(r.get("p_home_next", 0) or 0)
    pa = float(r.get("p_away_next", 0) or 0)
    ng = r.get("next_goal_prediction_smart") or {}
    ng_p = str(ng.get("prediction", "") or "").strip().upper()
    ng_c = float(ng.get("confidence", 0) or 0)
    wave_on = bool((r.get("wave") or {}).get("active", False))
    hidden = bool(r.get("hidden_goal_risk", False))
    dual = bool(r.get("dual_threat_mode", False))
    fake_h = bool(r.get("fake_home_pressure", False))
    final_bet = str(r.get("final_auto_bet", "") or "").strip().upper() or "NO BET"
    pro_lv = bool(r.get("pro_late_value_flag", False))
    gs = str(r.get("game_state", "") or "").strip()

    lam_gap_home = lam_h > lam_a + 1e-12
    lam_gap_away = lam_a > lam_h + 1e-12
    if lam_gap_away:
        lam_txt = btxt("AWAY ✔", GREEN, True)
    elif lam_gap_home:
        lam_txt = btxt("HOME ✔", GREEN, True)
    else:
        lam_txt = btxt("—", YELLOW, False)

    if edge_a >= edge_h and edge_a > 0.03:
        edge_txt = btxt(f"AWAY +{edge_a * 100:.1f}% ✔", GREEN, True) if edge_a > 0.06 else btxt(f"AWAY +{edge_a * 100:.1f}%", YELLOW, False)
    elif edge_h > edge_a and edge_h > 0.03:
        edge_txt = btxt(f"HOME +{edge_h * 100:.1f}% ✔", GREEN, True) if edge_h > 0.06 else btxt(f"HOME +{edge_h * 100:.1f}%", YELLOW, False)
    else:
        edge_txt = btxt("—", YELLOW, False)

    tempo_txt = btxt("HIGH ✔", GREEN, True) if tempo_hi else btxt("LOW", YELLOW, False)
    wave_txt = btxt("YES", GREEN, True) if wave_on else btxt("NO", YELLOW, False)

    away_lane = (
        minute >= 70
        and lam_gap_away
        and edge_a > 0.06
        and tempo_hi
        and pa > ph + 0.02
    )
    home_lane = (
        minute >= 70
        and lam_gap_home
        and edge_h > 0.06
        and tempo_hi
        and ph > pa + 0.02
    )
    trap_away = away_lane and (hidden or dual or fake_h)
    trap_home = home_lane and (hidden or dual)

    vd_eng = r.get("_vd_engine") if isinstance(r.get("_vd_engine"), dict) else {}
    vd_path = str(vd_eng.get("path") or "")

    if minute < 70:
        mode = "EARLY (PRO value lane od min 70+)"
    elif away_lane or home_lane:
        mode = "LATE GAME VALUE"
    else:
        mode = "MONITOR"

    if vd_path == "early_lt70":
        trigger = "NONE (engine: minute < 70)"
    elif vd_path == "master_freeze":
        trigger = "NONE (engine: master freeze)"
    elif vd_path == "pro_sync":
        if vd_eng.get("pro_late_value_flag") or pro_lv:
            trigger = "FULL (sinhrono: bet_decision PRO)"
        elif vd_eng.get("partial_signal"):
            trigger = "PARTIAL (sinhrono: core+signal; revive blokiran)"
        elif vd_eng.get("late_value_core") and (
            vd_eng.get("weak_conf_value") or vd_eng.get("strong_away_signal")
        ):
            trigger = "PARTIAL (sinhrono: signal; brez celega PRO revive)"
        elif vd_eng.get("late_value_core"):
            trigger = "PARTIAL (sinhrono: late core)"
        else:
            trigger = "NONE (engine)"
    elif pro_lv:
        trigger = "FULL (PRO late value — fallback brez _vd_engine)"
    elif away_lane or home_lane:
        weak_smart = ng_p in ("HOME", "AWAY") and 0.48 <= ng_c < 0.60
        trigger = "PARTIAL (fallback; conf/signal mešan)" if weak_smart else "PARTIAL (fallback)"
    else:
        trigger = "NONE"

    vd_conf = str(r.get("final_auto_conf", "") or "").strip().upper() or "LOW"

    if trap_away or trap_home:
        action = "TRAP RISK — ne mešaj z mirno value (filtrski znaki)"
        act_col = RED
    elif pro_lv:
        side = "HOME" if "HOME" in final_bet else "AWAY"
        action = f"SMALL VALUE BET ({side}) — usklajeno z BET DECISION"
        act_col = GREEN
    elif away_lane and final_bet == "NO BET":
        action = "ALTERNATIVE: AWAY SMALL VALUE (sistem = NO BET; odločitev ostane varna)"
        act_col = GREEN
    elif home_lane and final_bet == "NO BET":
        action = "ALTERNATIVE: HOME SMALL VALUE (sistem = NO BET; odločitev ostane varna)"
        act_col = GREEN
    else:
        action = "NO ALTERNATIVE (ali že pokrita z glavno stavo)"
        act_col = YELLOW

    print()
    print(f"{CYAN}{BOLD}================ VALUE DETECTOR ================={RESET}{cmd_tag('FINAL')}")
    print()
    _bm = str(r.get("bet_mode") or "").strip().upper()
    cm = str(r.get("control_mode") or "").strip().upper()
    if cm:
        cr = str(r.get("control_reason") or "").strip()
        print(btxt(f"CONTROL: {cm}", GREEN, True))
        if cr:
            print(f"{'Reason'.ljust(22)} {btxt(cr, GREEN, False)}")
        print()
    if _bm in ("FREEZE", "LOW_EVENT"):
        pg = float(r.get("p_goal", 0) or 0)
        lt = float(r.get("lam_total", 0) or 0)
        ox = float(r.get("odds_draw", 0) or 0)
        bre = str(r.get("bet_mode_reason") or "").strip()
        print(btxt(f"MODE: {_bm} (late no-event zone)", YELLOW, True))
        if bre:
            print(f"{'Razlog'.ljust(22)} {btxt(bre, YELLOW, False)}")
        print(
            f"{'odds DRAW'.ljust(22)} {btxt(f'{ox:.2f}', GREEN if (0.0 < ox < 1.45 and minute >= 78) else YELLOW, False)}  "
            f"{'λ_total'.ljust(18)} {btxt(f'{lt:.3f}', YELLOW, False)}  "
            f"{'P(goal)'.ljust(10)} {btxt(f'{pg * 100:.1f}%', YELLOW, False)}"
        )
        print()
    if _bm == "GOAL_EVENT":
        pg = float(r.get("p_goal", 0) or 0)
        nc = float(r.get("next_goal_conf_smart", 0) or 0)
        adv = str(r.get("goal_event_market_advisory") or "").strip()
        print(btxt("MODE: GOAL EVENT (gol bolj zanesljiv kot smer)", GREEN, True))
        print(
            f"{'P(goal)'.ljust(22)} {btxt(f'{pg * 100:.1f}%', GREEN, False)}  "
            f"{'Smart dir. conf'.ljust(18)} {btxt(f'{nc * 100:.1f}%', YELLOW, False)}"
        )
        if adv:
            print(f"{'PRO advisory'.ljust(22)} {btxt(adv, GREEN, True)}")
        print(
            btxt(
                "→ Končna stava (1X2/next side) lahko ostane NO BET; event stave so ločen trg.",
                CYAN,
                False,
            )
        )
        print()
    if vd_path == "pro_sync":
        print(
            f"{'Engine sync'.ljust(22)} "
            f"{btxt('bet_decision PRO → _vd_engine', GREEN, False)}"
        )
        print()
    if minute >= 70 and final_bet == "NO BET":
        if (
            edge_a > 0.06
            and lam_gap_away
            and not trap_away
            and edge_a >= edge_h
        ):
            print(btxt(f">>> VALUE ALERT: AWAY (+{edge_a * 100:.1f}%)", GREEN, True))
            print()
        elif (
            edge_h > 0.06
            and lam_gap_home
            and not trap_home
            and edge_h > edge_a
        ):
            print(btxt(f">>> VALUE ALERT: HOME (+{edge_h * 100:.1f}%)", GREEN, True))
            print()

    print(f"{'Minute'.ljust(22)} {minute}")
    print(f"{'Mode'.ljust(22)} {btxt(mode, CYAN, True)}")
    print()
    print(f"{'Lambda gap'.ljust(22)} {lam_txt}")
    print(f"{'Edge'.ljust(22)} {edge_txt}")
    print(f"{'Tempo'.ljust(22)} {tempo_txt}")
    print(f"{'Attack wave'.ljust(22)} {wave_txt}")
    print()
    print(f"{'Trigger'.ljust(22)} {btxt(trigger, GREEN if trigger.startswith('FULL') else (YELLOW if trigger.startswith('PARTIAL') else RED), True)}")
    print(f"{'Confidence'.ljust(22)} {btxt(vd_conf + ' (read-only)', YELLOW, False)}")
    print(f"{'Action'.ljust(22)} {btxt(action, act_col, True)}")
    print()
    print("Reason:")
    if lam_gap_away:
        print(" - Lambda dominance AWAY")
    elif lam_gap_home:
        print(" - Lambda dominance HOME")
    if edge_a > edge_h and edge_a > 0.04:
        print(" - Market podcenjuje AWAY (pozitiven edge)")
    elif edge_h > edge_a and edge_h > 0.04:
        print(" - Market podcenjuje HOME (pozitiven edge)")
    if tempo_hi:
        print(" - Visok tempo / odprtejša tekma")
    if wave_on:
        print(" - Attack wave aktiven")
    if "DOMINACIJA" in gs.upper() or "KONTROLA" in gs.upper():
        print(f" - Game state: {gs} (result / kontrola)")
    if trap_away or trap_home:
        print(btxt(" - POZOR: hidden/dual/fake filtri — value je sumljiva", RED, True))
    print()
    print(f"{CYAN}{BOLD}{'=' * 59}{RESET}")


def cmd_tag(tag):
    t = str(tag or "").strip()
    if not t:
        return ""
    return f"   [{t}]"


def _capture_print_output(fn, *args, **kwargs):
    """
    Ujame vse print() klice med fn() in vrne (result, lines).
    To uporabljamo, da izračun ne razmeče CMD vrstnega reda.
    """
    lines = []
    real_print = builtins.print

    def _cap_print(*pargs, **pkwargs):
        sep = pkwargs.get("sep", " ")
        end = pkwargs.get("end", "\n")
        msg = sep.join("" if p is None else str(p) for p in pargs) + end
        # ohrani vrstice brez zadnjega \n
        for part in msg.splitlines():
            lines.append(part)
        # če je end = "\n" in je zadnja vrstica prazna, jo ohrani
        if msg.endswith("\n") and (len(msg.splitlines()) == 0):
            lines.append("")

    try:
        builtins.print = _cap_print
        res = fn(*args, **kwargs)
    finally:
        builtins.print = real_print

    # odstrani vodilne/prazne vrste, ki nastanejo zaradi end
    while lines and lines[0] == "":
        lines.pop(0)
    return res, lines


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
        sx = str(x).strip()
        if ":" in sx:
            sx = sx.split(":", 1)[0].strip()
        return int(float(sx.replace(",", ".")))
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
        line = str(line or "")
        reader = csv.reader(StringIO(line))
        row = next(reader)
        return [x.strip() for x in row]
    except:
        return [x.strip() for x in str(line or "").split(",")]


def file_has_data(path):
    return os.path.exists(path) and os.path.getsize(path) > 0


def _sanitize_log_cell(x, max_len=420):
    s = str(x if x is not None else "")
    return s.replace("\r", " ").replace("\n", " ").replace(",", ";")[:max_len]


def append_bet_decision_log_row(
    r,
    *,
    main_bet,
    decision_reason,
    confidence,
    stake_band,
    pro_late_value_flag,
    match_bet,
    match_reason,
    top5,
    model_reliability,
    game_state,
    minute_val,
):
    """Zapiše eno vrstico v CSV — ista polja kot pri končni odločitvi (povezano z logiko)."""
    fieldnames = (
        "ts",
        "home",
        "away",
        "minute",
        "score",
        "main_bet",
        "confidence",
        "stake_band",
        "pro_late",
        "reason",
        "edge_h",
        "edge_x",
        "edge_a",
        "p_goal",
        "p_goal_10",
        "ph_next",
        "pa_next",
        "ng_pred",
        "ng_conf",
        "game_state",
        "tempo_sh",
        "tempo_dg",
        "lam_h",
        "lam_a",
        "top1",
        "p_top1",
        "match_bet",
        "match_reason",
        "reliability",
        "top5",
    )
    try:
        path = BET_DECISION_LOG
        need_header = not file_has_data(path)
        home = _sanitize_log_cell(r.get("home", ""), 120)
        away = _sanitize_log_cell(r.get("away", ""), 120)
        sh = int(r.get("score_home", 0) or 0)
        sa = int(r.get("score_away", 0) or 0)
        ts_scores = r.get("top_scores") or []
        t1s, t1p = ("", 0.0)
        if ts_scores:
            t1s = str(ts_scores[0][0])
            t1p = float(ts_scores[0][1] or 0)
        parts_top5 = []
        if top5:
            for nm, sc in top5[:5]:
                parts_top5.append(f"{nm}:{float(sc or 0):.3f}")
        top5_blob = "|".join(parts_top5)
        ng = r.get("next_goal_prediction_smart") or {}
        ngp = str(ng.get("prediction", "") or "")
        ngc = float(ng.get("confidence", 0) or 0)
        row = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "home": home,
            "away": away,
            "minute": str(int(minute_val or 0)),
            "score": f"{sh}-{sa}",
            "main_bet": _sanitize_log_cell(main_bet, 40),
            "confidence": _sanitize_log_cell(confidence, 12),
            "stake_band": _sanitize_log_cell(stake_band, 32),
            "pro_late": "1" if pro_late_value_flag else "0",
            "reason": _sanitize_log_cell(decision_reason, 400),
            "edge_h": f"{float(r.get('edge_h', 0) or 0):.5f}",
            "edge_x": f"{float(r.get('edge_x', 0) or 0):.5f}",
            "edge_a": f"{float(r.get('edge_a', 0) or 0):.5f}",
            "p_goal": f"{float(r.get('p_goal', 0) or 0):.5f}",
            "p_goal_10": f"{float(r.get('p_goal_10', 0) or 0):.5f}",
            "ph_next": f"{float(r.get('p_home_next', 0) or 0):.5f}",
            "pa_next": f"{float(r.get('p_away_next', 0) or 0):.5f}",
            "ng_pred": _sanitize_log_cell(ngp, 16),
            "ng_conf": f"{ngc:.5f}",
            "game_state": _sanitize_log_cell(game_state, 40),
            "tempo_sh": f"{float(r.get('tempo_shots', 0) or 0):.5f}",
            "tempo_dg": f"{float(r.get('tempo_danger', 0) or 0):.5f}",
            "lam_h": f"{float(r.get('lam_h', 0) or 0):.5f}",
            "lam_a": f"{float(r.get('lam_a', 0) or 0):.5f}",
            "top1": _sanitize_log_cell(t1s, 16),
            "p_top1": f"{t1p:.5f}",
            "match_bet": _sanitize_log_cell(match_bet, 24),
            "match_reason": _sanitize_log_cell(match_reason, 120),
            "reliability": f"{float(model_reliability or 0):.5f}",
            "top5": _sanitize_log_cell(top5_blob, 500),
        }
        with open(path, "a", encoding="utf-8", newline="") as out:
            w = csv.DictWriter(out, fieldnames=fieldnames, extrasaction="ignore")
            if need_header:
                w.writeheader()
            w.writerow(row)
    except Exception:
        pass


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


def normalize_outcome_label(value):
    v = str(value or "").strip().upper()

    if v in ("HOME", "H", "1", "DOMAČI", "DOMACI"):
        return "HOME"
    if v in ("AWAY", "A", "2", "GOST"):
        return "AWAY"
    if v in ("DRAW", "D", "X", "REMI"):
        return "DRAW"

    return v


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


def time_decay(minute):
    m = int(float(minute or 0))
    if m < 70:
        return 1.0
    if m < 80:
        return 0.85
    if m < 90:
        return 0.65
    return 0.50


def next_goal_window_state(p_goal_10, ng_smart_conf, p_home_next, p_away_next, momentum, minute):
    p_goal_10 = float(p_goal_10 or 0.0)
    ng_smart_conf = float(ng_smart_conf or 0.0)
    p_home_next = float(p_home_next or 0.0)
    p_away_next = float(p_away_next or 0.0)
    momentum = float(momentum or 0.0)
    minute = int(float(minute or 0))

    edge = abs(p_home_next - p_away_next)
    side = "HOME" if p_home_next >= p_away_next else "AWAY"
    if edge < 0.05:
        if momentum > 0.08:
            side = "HOME"
        elif momentum < -0.08:
            side = "AWAY"

    if minute < 45:
        return "HOLD", side, "EARLY PHASE (<45)"
    if p_goal_10 >= 0.48 and ng_smart_conf >= 0.72 and edge >= 0.10:
        return "TRIGGER", side, "10M GOAL + SMART + EDGE STRONG"
    if p_goal_10 >= 0.38 and ng_smart_conf >= 0.62 and edge >= 0.08:
        return "PRE-TRIGGER", side, "10M GOAL + SMART BUILDING"
    if p_goal_10 >= 0.30 and ng_smart_conf >= 0.52:
        return "WATCH", side, "WATCHING 10M BUILDUP"
    return "HOLD", side, "LOW 10M GOAL OR LOW SMART"


def color_window_level(level):
    lvl = str(level or "").upper()
    if lvl == "TRIGGER":
        return GREEN
    if lvl == "PRE-TRIGGER":
        return YELLOW
    if lvl == "WATCH":
        return CYAN
    return RED


def anti_split_shift_away(minute, score_diff, tempo_danger_h, tempo_danger_a, tempo_shots_h, tempo_shots_a, timeline_home, timeline_away, danger_h, danger_a):
    return (
        int(float(minute or 0)) >= 65
        and int(float(score_diff or 0)) == 1
        and float(tempo_danger_a or 0.0) > float(tempo_danger_h or 0.0)
        and float(tempo_shots_a or 0.0) > float(tempo_shots_h or 0.0)
        and float(timeline_away or 1.0) > float(timeline_home or 1.0)
        and float(danger_a or 0.0) >= float(danger_h or 0.0)
    )


def pressure_goal_detector(overpressure_away, p_goal_10, ng_window_level, wave_active=False):
    p_goal_10 = float(p_goal_10 or 0.0)
    overpressure_away = bool(overpressure_away)
    ng_window_level = str(ng_window_level or "HOLD").upper()
    wave_active = bool(wave_active)

    hidden_goal_risk = (
        overpressure_away
        and p_goal_10 < 0.30
        and ng_window_level in ("HOLD", "WATCH")
        and not wave_active
    )
    if hidden_goal_risk:
        return True, "SKRITO TVEGANJE GOLA (PRITISK GOSTA)"
    return False, "NI SKRITEGA TVEGANJA GOLA"


def goal_timing_detector(p_goal_5, p_goal_10, tempo_danger, tempo_shots, wave_active, overpressure_home, overpressure_away, timeline_goal_factor, minute):
    p5 = float(p_goal_5 or 0.0)
    p10 = float(p_goal_10 or 0.0)
    td = float(tempo_danger or 0.0)
    ts = float(tempo_shots or 0.0)
    tg = float(timeline_goal_factor or 1.0)
    minute = int(float(minute or 0))
    wave_active = bool(wave_active)
    over_h = bool(overpressure_home)
    over_a = bool(overpressure_away)

    score = 0.0
    score += p5 * 45.0
    score += p10 * 35.0
    score += clamp(td / 2.2, 0.0, 1.0) * 10.0
    score += clamp(ts / 0.35, 0.0, 1.0) * 6.0
    if wave_active:
        score += 6.0
    if over_h or over_a:
        score += 5.0
    if tg >= 1.06:
        score += 4.0
    elif tg <= 0.96:
        score -= 4.0
    if minute >= 85 and p10 < 0.25:
        score -= 5.0

    score = clamp(score, 0.0, 100.0)
    if score >= 75:
        return {"score": round(score, 1), "window": "ODPRTO", "entry": "TRIGGER", "eta": "0-5 min", "reason": "MOČAN GOAL WINDOW"}
    if score >= 58:
        return {"score": round(score, 1), "window": "GRADI SE", "entry": "READY", "eta": "5-10 min", "reason": "SIGNALI SE KREPIJO"}
    return {"score": round(score, 1), "window": "ZAPRTO", "entry": "WAIT", "eta": ">10 min", "reason": "PREMALO TEMPA ZA GOL"}


def detect_game_state(score_diff, xg_h, xg_a, momentum, sot_h, sot_a, p_goal=0.0, lam_h=0.0, lam_a=0.0):
    score_diff = int(float(score_diff or 0))
    xg_h = float(xg_h or 0.0)
    xg_a = float(xg_a or 0.0)
    momentum = float(momentum or 0.0)
    sot_h = float(sot_h or 0.0)
    sot_a = float(sot_a or 0.0)
    p_goal = float(p_goal or 0.0)
    lam_h = float(lam_h or 0.0)
    lam_a = float(lam_a or 0.0)
    if p_goal > 0.55 and abs(lam_h - lam_a) < 0.10:
        return "OPEN CHAOS"
    if xg_a > max(0.15, xg_h * 2.0) and momentum < -0.30 and sot_a >= 3:
        return "AWAY DOMINACIJA"
    if xg_h > max(0.15, xg_a * 2.0) and momentum > 0.30 and sot_h >= 3:
        return "HOME DOMINACIJA"
    if score_diff == 0:
        return "IZENAČENO"
    return "KONTROLA REZULTATA"


# ============================================================
# NEXT GOAL BET ENGINE
# ============================================================
def next_goal_bet_engine(
    p_home_next, p_away_next,
    lam_h, lam_a,
    momentum, tempo_shots, tempo_danger, game_type,
    p_goal_10=0.0, minute=0
):
    home_ng = float(p_home_next or 0.0)
    away_ng = float(p_away_next or 0.0)
    lam_h = float(lam_h or 0.0)
    lam_a = float(lam_a or 0.0)
    p_goal_10 = float(p_goal_10 or 0.0)
    minute = int(float(minute or 0))
    lam_diff = lam_h - lam_a
    momentum = float(momentum or 0.0)
    tempo_high = float(tempo_shots or 0.0) > 0.18 or float(tempo_danger or 0.0) > 1.2
    game_type = str(game_type or "")

    # ------------------------------------------------------------
    # ALWAYS PREDICTION (samo matematika p_home_next vs p_away_next)
    # ------------------------------------------------------------
    if home_ng > away_ng:
        next_goal_prediction = "HOME"
    elif away_ng > home_ng:
        next_goal_prediction = "AWAY"
    else:
        next_goal_prediction = "NO GOAL"

    # ------------------------------------------------------------
    # BET ENGINE
    # ------------------------------------------------------------
    next_goal_bet = "NO BET"
    next_goal_reason = "LOW EDGE"

    if p_goal_10 < 0.34:
        return next_goal_prediction, "NO BET", "LOW 10M GOAL PROB"

    if abs(home_ng - away_ng) < 0.08:
        return next_goal_prediction, "NO BET", "EDGE TOO SMALL"

    if home_ng > 0.55 and lam_diff > 0.30 and momentum > 0.15 and p_goal_10 >= 0.42:
        next_goal_bet = "HOME"
        next_goal_reason = "STRONG HOME PRESSURE 10M"
    elif home_ng > 0.50 and lam_diff > 0.18 and momentum > 0.08 and p_goal_10 >= 0.38:
        next_goal_bet = "HOME"
        next_goal_reason = "HOME MOMENTUM + LAMBDA 10M"
    elif away_ng > 0.40 and momentum < -0.10 and p_goal_10 >= 0.38:
        next_goal_bet = "AWAY"
        next_goal_reason = "AWAY MOMENTUM 10M"
    elif away_ng > 0.36 and lam_diff < -0.18 and momentum < -0.06 and p_goal_10 >= 0.36:
        next_goal_bet = "AWAY"
        next_goal_reason = "AWAY LAMBDA + MOMENTUM 10M"
    elif home_ng > 0.53 and away_ng > 0.28 and abs(momentum) < 0.20 and tempo_high and p_goal_10 >= 0.40:
        next_goal_bet = "AWAY"
        next_goal_reason = "FAKE HOME PRESSURE 10M"
    elif game_type == "ATTACK_WAVE" and away_ng > 0.30 and p_goal_10 >= 0.38:
        next_goal_bet = "AWAY"
        next_goal_reason = "OPEN GAME 10M"

    return next_goal_prediction, next_goal_bet, next_goal_reason


# ============================================================
# NEXT GOAL SMART ENGINE (PREDICT_NEXT_GOAL_SMART)
# ============================================================

def predict_next_goal_smart(
    p_home_next, p_away_next,
    lam_h, lam_a,
    danger_h, danger_a,
    xg_h, xg_a,
    momentum,
    pressure_h, pressure_a,
    tempo_danger,
    sot_h, sot_a,
    game_type,
    minute
):
    """
    Smart next goal prediction with 8+ weighted signals and confidence score.
    WEIGHTING: P(next)=25%, Lambda=20%, Danger=15%, Momentum=15%,
               Pressure=10%, xG=10%, GameType+SOT=5%
    Returns dict with prediction, confidence (0.0-1.0), scores and details.
    """
    p_home_next = float(p_home_next or 0.0)
    p_away_next = float(p_away_next or 0.0)
    lam_h = float(lam_h or 0.0)
    lam_a = float(lam_a or 0.0)
    danger_h = float(danger_h or 0.0)
    danger_a = float(danger_a or 0.0)
    xg_h = float(xg_h or 0.0)
    xg_a = float(xg_a or 0.0)
    momentum = float(momentum or 0.0)
    pressure_h = float(pressure_h or 0.0)
    pressure_a = float(pressure_a or 0.0)
    tempo_danger = float(tempo_danger or 0.0)
    sot_h = float(sot_h or 0.0)
    sot_a = float(sot_a or 0.0)
    minute = int(float(minute or 0))
    game_type = str(game_type or "BALANCED")

    # ============================================================
    # NO REAL DOMINANCE FILTER (SAFE - CFOS COMPATIBLE)
    # ============================================================
    no_real_dominance = False

    if abs(momentum) < 0.05:
        if danger_h > 0 and danger_a > 0 and pressure_h > 0 and pressure_a > 0:

            dr = danger_h / danger_a
            pr = pressure_h / pressure_a

            if dr < 1:
                dr = 1 / dr
            if pr < 1:
                pr = 1 / pr

            if dr < 1.15 and pr < 1.15:
                no_real_dominance = True

    if tempo_danger > 2.0 and abs(momentum) < 0.08:
        no_real_dominance = True

    # SIGNAL WEIGHTS
    W_PNEXT = 0.25
    W_LAMBDA = 0.20
    W_DANGER = 0.15
    W_MOMENTUM = 0.15
    W_PRESSURE = 0.10
    W_XG = 0.10
    W_GAMETYPE = 0.05
    TOTAL_SIGNALS = 7  # number of directional signals used for confidence

    # SIGNAL 1: P(next) probability (25%)
    p_total = p_home_next + p_away_next
    if p_total > 1e-9:
        p_home_norm = p_home_next / p_total
        p_away_norm = p_away_next / p_total
    else:
        p_home_norm = 0.5
        p_away_norm = 0.5
    sig1_h = (p_home_norm - 0.5) * 2.0
    sig1_a = (p_away_norm - 0.5) * 2.0

    # SIGNAL 2: Lambda difference (20%)
    lam_total_s = lam_h + lam_a
    if lam_total_s > 1e-9:
        lam_diff_s = (lam_h - lam_a) / lam_total_s
    else:
        lam_diff_s = 0.0
    sig2_h = lam_diff_s
    sig2_a = -lam_diff_s

    # SIGNAL 3: Danger difference (15%)
    danger_total_s = danger_h + danger_a
    if danger_total_s > 1e-9:
        danger_diff_s = (danger_h - danger_a) / danger_total_s
    else:
        danger_diff_s = 0.0
    sig3_h = danger_diff_s
    sig3_a = -danger_diff_s

    # SIGNAL 4: Momentum (15%)
    sig4_h = clamp(momentum, -1.0, 1.0)
    sig4_a = -sig4_h

    # SIGNAL 5: Pressure difference (10%)
    pressure_total_s = pressure_h + pressure_a
    if pressure_total_s > 1e-9:
        press_diff_s = (pressure_h - pressure_a) / pressure_total_s
    else:
        press_diff_s = 0.0
    sig5_h = press_diff_s
    sig5_a = -press_diff_s

    # SIGNAL 6: xG difference (10%)
    xg_total_s = xg_h + xg_a
    if xg_total_s > 1e-9:
        xg_diff_s = (xg_h - xg_a) / xg_total_s
    else:
        xg_diff_s = 0.0
    sig6_h = xg_diff_s
    sig6_a = -xg_diff_s

    # ============================================================
    # REAL SIGNAL AGREEMENT (ANTI DUPLICATE)
    # ============================================================

    signals = 0

    # momentum (najbolj pomemben)
    if abs(sig4_h) > 0.15:
        signals += 1

    # danger
    if abs(sig3_h) > 0.12:
        signals += 1

    # pressure
    if abs(sig5_h) > 0.12:
        signals += 1

    # lambda
    if abs(sig2_h) > 0.10:
        signals += 1

    # xG (slabši signal → manjši threshold)
    if abs(sig6_h) > 0.08:
        signals += 1

    # SIGNAL 7: SOT ratio (part of game type weight)
    sot_total_s = sot_h + sot_a
    if sot_total_s > 1e-9:
        sot_diff_s = (sot_h - sot_a) / sot_total_s
    else:
        sot_diff_s = 0.0

    # ============================================================
    # SAFE TEMPO MULTIPLIER
    # ============================================================

    if tempo_danger > 1.5:
        tempo_mult = 1.05
    elif tempo_danger > 1.2:
        tempo_mult = 1.03
    elif tempo_danger < 0.8:
        tempo_mult = 0.95
    else:
        tempo_mult = 1.0

    # GAME TYPE MODIFIER (boosts dominant side in aggressive game types)
    gt_boost_h = 0.0
    gt_boost_a = 0.0
    if game_type in ("PRESSURE", "ATTACK_WAVE", "CHAOS"):
        if danger_diff_s > 0:
            gt_boost_h = 0.15
        else:
            gt_boost_a = 0.15

    # MINUTE PENALTY (84+ = smaller attack multiplier)
    if minute >= 84:
        minute_mult = 0.85
    elif minute >= 80:
        minute_mult = 0.92
    else:
        minute_mult = 1.0

    # WEIGHTED COMPOSITE SCORES
    score_h = (
        W_PNEXT * sig1_h +
        W_LAMBDA * sig2_h +
        W_DANGER * sig3_h +
        W_MOMENTUM * sig4_h +
        W_PRESSURE * sig5_h +
        W_XG * sig6_h +
        W_GAMETYPE * (sot_diff_s + gt_boost_h)
    ) * tempo_mult * minute_mult

    score_a = (
        W_PNEXT * sig1_a +
        W_LAMBDA * sig2_a +
        W_DANGER * sig3_a +
        W_MOMENTUM * sig4_a +
        W_PRESSURE * sig5_a +
        W_XG * sig6_a +
        W_GAMETYPE * (-sot_diff_s + gt_boost_a)
    ) * tempo_mult * minute_mult

    # ============================================================
    # COUNTER ATTACK DETECTOR
    # ============================================================

    counter_risk = False

    if danger_h > danger_a * 0.9 and sot_h < sot_a:
        if momentum < 0.05:
            counter_risk = True

    if counter_risk:
        score_h *= 1.15
        score_a *= 0.85

    no_real_dominance = signals <= 2

    # ============================================================
    # NO REAL DOMINANCE APPLY (EXACT FIX)
    # ============================================================
    if no_real_dominance:
        score_h = score_h * 0.35
        score_a = score_a * 0.35

    # PREDICTION
    prediction = "HOME" if score_h >= score_a else "AWAY"

    # ============================================================
    # DRAW ZONE FILTER
    # ============================================================

    if abs(score_h - score_a) < 0.05:
        prediction = "NO BET"

    # CONFIDENCE SCORE (agreement % across 7 directional signals)
    if prediction == "HOME":
        agree = [
            sig1_h > 0,
            sig2_h > 0,
            sig3_h > 0,
            sig4_h > 0,
            sig5_h > 0,
            sig6_h > 0,
            sot_diff_s > 0,
        ]
    else:
        agree = [
            sig1_a > 0,
            sig2_a > 0,
            sig3_a > 0,
            sig4_a > 0,
            sig5_a > 0,
            sig6_a > 0,
            sot_diff_s < 0,
        ]

    agreement_count = sum(agree)
    confidence = round(agreement_count / TOTAL_SIGNALS, 3)



    # ============================================================
    # ANTI OVERCONFIDENCE
    # ============================================================

    # če ni dominance → cap
    if abs(momentum) < 0.08:
        confidence *= 0.75

    # če je balanced game
    if abs(danger_h - danger_a) < 0.2 * max(1, danger_h + danger_a):
        confidence *= 0.80

    # če je low pressure
    if pressure_h < 8 and pressure_a < 8:
        confidence *= 0.85

    # HARD CAP
    if confidence > 0.85:
        confidence *= 0.90

    # GLOBAL TIME DECAY: proti koncu tekme signal pritiska izgublja moč.
    confidence *= time_decay(minute)

    confidence = round(confidence, 3)

    # FINAL ROUND (NUJNO)
    confidence = round(confidence, 3)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "score_h": round(score_h, 4),
        "score_a": round(score_a, 4),
        "signals_agreement": agreement_count,
        "tempo_mult": round(tempo_mult, 3),
        "minute_mult": round(minute_mult, 3),
    }


# ============================================================
# BALANCE COUNTER FILTER
# ============================================================
def cfos_balance_counter(danger_h, danger_a, shots_h, shots_a, counter_goal):
    danger_h = float(danger_h or 0.0)
    danger_a = float(danger_a or 0.0)
    shots_h = float(shots_h or 0.0)
    shots_a = float(shots_a or 0.0)
    counter_goal = normalize_outcome_label(counter_goal)

    dominant_side = None

    if danger_h >= max(1.0, danger_a * 1.35) and shots_h >= max(1.0, shots_a * 1.20):
        dominant_side = "HOME"
    elif danger_a >= max(1.0, danger_h * 1.35) and shots_a >= max(1.0, shots_h * 1.20):
        dominant_side = "AWAY"

    if dominant_side and counter_goal in ("HOME", "AWAY") and counter_goal != dominant_side:
        counter_goal = dominant_side

    return dominant_side, counter_goal



def side_name_from_diff(diff, pos_text="HOME", neg_text="AWAY", neutral_text="BALANCED", eps=1e-9):
    if diff > eps:
        return pos_text
    if diff < -eps:
        return neg_text
    return neutral_text


def favorite_side(r):
    oh = float(r.get("odds_home", 0) or 0)
    oa = float(r.get("odds_away", 0) or 0)
    if oh > 0 and oa > 0:
        if oh < oa:
            return "HOME"
        if oa < oh:
            return "AWAY"
    imp_h = float(r.get("imp_h", 0) or 0)
    imp_a = float(r.get("imp_a", 0) or 0)
    return side_name_from_diff(imp_h - imp_a, "HOME", "AWAY", "BALANCED")


def goal_factor_scale_label(value):
    v = float(value or 0)
    if v < 0.85:
        return "DEAD"
    if v < 0.95:
        return "LOW"
    if v <= 1.05:
        return "NORMAL"
    if v <= 1.15:
        return "BUILDING"
    if v <= 1.25:
        return "GOAL"
    return "VERY LIKELY"


def game_type_pressure_side(r):
    gt = str(r.get("game_type", "BALANCED"))
    momentum = float(r.get("momentum", 0) or 0)
    pressure_h = float(r.get("pressure_h", 0) or 0)
    pressure_a = float(r.get("pressure_a", 0) or 0)
    danger_h = float(r.get("danger_h", 0) or 0)
    danger_a = float(r.get("danger_a", 0) or 0)
    attacks_h = float(r.get("attacks_h", 0) or 0)
    attacks_a = float(r.get("attacks_a", 0) or 0)
    shots_h = float(r.get("shots_h", 0) or 0)
    shots_a = float(r.get("shots_a", 0) or 0)

    bias = (pressure_h - pressure_a) * 0.7 + (danger_h - danger_a) * 0.04 + (shots_h - shots_a) * 0.18 + momentum * 12.0
    side = side_name_from_diff(bias, "HOME", "AWAY", "BALANCED", eps=0.05)

    if gt == "ATTACK_WAVE":
        return f"ATTACK_WAVE ({side} pressure)" if side != "BALANCED" else "ATTACK_WAVE"
    if gt == "PRESSURE":
        return f"PRESSURE ({side} pressure)" if side != "BALANCED" else "PRESSURE"
    if gt == "CHAOS":
        return f"CHAOS ({side} edge)" if side != "BALANCED" else "CHAOS"
    if gt == "BALANCED":
        return "BALANCED"
    return gt


def lge_state_value(r):
    gt = str(r.get("game_type", "BALANCED"))
    if gt in ("PRESSURE", "ATTACK_WAVE", "CHAOS"):
        return "ACTIVE"
    if bool(r.get("wave", {}).get("active", False)):
        return "ACTIVE"
    notes = list(r.get("tempo_notes", []) or []) + list(r.get("xgr_notes", []) or [])
    return "ACTIVE" if notes else "PASSIVE"


def high_side_label(home_val, away_val, threshold=0.0, high_text="high", low_text="LOW"):
    diff = float(home_val or 0) - float(away_val or 0)
    if diff > threshold:
        return f"HOME ({high_text})"
    if diff < -threshold:
        return f"AWAY ({high_text})"
    return low_text


def print_razumevanje(r):
    print(f"\n{MAGENTA}--------------- LEARNING INTERPRETACIJA ----------------{RESET}\n")

    xg_side = side_name_from_diff(float(r.get("xg_h", 0) or 0) - float(r.get("xg_a", 0) or 0), "HOME", "AWAY", "BALANCED", eps=0.08)
    sot_side = side_name_from_diff(float(r.get("sot_h", 0) or 0) - float(r.get("sot_a", 0) or 0), "HOME", "AWAY", "BALANCED", eps=0.25)
    shot_side = side_name_from_diff(float(r.get("shots_h", 0) or 0) - float(r.get("shots_a", 0) or 0), "HOME", "AWAY", "BALANCED", eps=0.5)
    danger_side = side_name_from_diff(float(r.get("danger_h", 0) or 0) - float(r.get("danger_a", 0) or 0), "HOME", "AWAY", "BALANCED", eps=1.0)
    score_diff = int(r.get("score_diff", 0) or 0)

    print(f"Bucket {bucket_minute(r['minute'])}")
    print(f"xG:{bucket_xg(r['xg_total'])}".ljust(14) + f"→ {xg_side}")
    print(f"SOT:{bucket_sot(r['sot_total'])}".ljust(14) + f"→ {sot_side}")
    print(f"SH:{bucket_shots(r['shots_total'])}".ljust(14) + f"→ {shot_side}")

    if score_diff > 0:
        sd_text = "HOME (vodi)"
    elif score_diff < 0:
        sd_text = "AWAY (vodi)"
    else:
        sd_text = "DRAW"
    print(f"SD:{bucket_score_diff(score_diff)}".ljust(14) + f"→ {sd_text}")
    print(f"DNG:{bucket_danger(r['danger_total'])}".ljust(14) + f"→ {danger_side}")
    print("Game type".ljust(14) + f"→ {game_type_pressure_side(r)}")
    print(f"FAVOR: {favorite_side(r)}")
    # Opomba: `MATCH MEMORY` in `LGE` se izpisujeta v `izpis_rezultata()` pod [IGRIŠČE],
    # da ostane mapping striktno pravilen in brez podvajanj.

def print_interpretacija(r):
    print(f"\n{MAGENTA}--------------- INTERPRETACIJA MODELA ----------------{RESET}\n")

    top_scores = r.get("top_scores", []) or []
    top1 = top_scores[0] if len(top_scores) >= 1 else ("N/A", 0.0)
    top2 = top_scores[1] if len(top_scores) >= 2 else None
    top3 = top_scores[2] if len(top_scores) >= 3 else None

    print("Top:")
    print(f"{top1[0]} → {pct(top1[1])} %")
    if top2:
        print(f"{top2[0]} → {pct(top2[1])} %")
    if top3:
        print(f"{top3[0]} → {pct(top3[1])} %")

    print("\nTo je tipična situacija:\n")

    gt = str(r.get("game_type", "BALANCED"))
    momentum = float(r.get("momentum", 0.0))
    lam_h = float(r.get("lam_h", 0.0))
    lam_a = float(r.get("lam_a", 0.0))
    p_goal = float(r.get("p_goal", 0.0))
    p_home_next = float(r.get("p_home_next", 0.0))
    p_away_next = float(r.get("p_away_next", 0.0))
    hist_draw = float(r.get("hist_draw", 0.0))
    rx = float(r.get("rx", 1.0))
    sot_h = float(r.get("sot_h", 0.0))
    sot_a = float(r.get("sot_a", 0.0))

    if gt == "BALANCED":
        print("tekma uravnotežena")
        print("brez jasne dominance")
        print("→ rezultat stabilen")
    elif gt == "PRESSURE":
        print("ena ekipa močneje pritiska")
        print("tekma ni več povsem mirna")
        print("→ gol je bolj verjeten")
    elif gt == "ATTACK_WAVE":
        print("tekma je odprta")
        print("napadi prihajajo v valovih")
        print("→ možen hiter preobrat")
    elif gt == "CHAOS":
        print("tekma je kaotična")
        print("ritem je zelo visok")
        print("→ rezultat lahko hitro skoči")
    else:
        print("tekma je počasna")
        print("malo čistih akcij")
        print("→ rezultat se lahko zadrži")

    print("\nModel je to predvidel kot Top1.\n")
    print("Ključni signali:\n")

    print(f"History: DRAW {round(hist_draw * 100)}%")
    print(f"Learning: DRAW {(rx - 1.0) * 100:+.1f}%")

    if abs(sot_h - sot_a) <= 1:
        print("SOT: izenačeno")
    elif sot_h > sot_a:
        print("SOT: rahlo HOME")
    else:
        print("SOT: rahlo AWAY")

    if lam_h > lam_a + 0.05:
        print("Lambda: rahlo HOME")
    elif lam_a > lam_h + 0.05:
        print("Lambda: rahlo AWAY")
    else:
        print("Lambda: skoraj izenačeno")

    print(f"Goal probability: {round(p_goal * 100)}%")

    if abs(momentum) < 0.08:
        print("Momentum: majhen")
    elif momentum > 0:
        print("Momentum: HOME pritisk")
    else:
        print("Momentum: AWAY pritisk")

    print(f"Game type: {gt}")

    print("\nTo pomeni:\n")

    final_h = float(r.get("meta_home", 0.0) or 0.0)
    final_d = float(r.get("meta_draw", 0.0) or 0.0)
    final_a = float(r.get("meta_away", 0.0) or 0.0)

    hist_h = float(r.get("hist_home", 0.0) or 0.0)
    hist_d = float(r.get("hist_draw", 0.0) or 0.0)
    hist_a = float(r.get("hist_away", 0.0) or 0.0)

    live_side = max(
        [("HOME", final_h), ("DRAW", final_d), ("AWAY", final_a)],
        key=lambda x: x[1]
    )[0]

    hist_side = max(
        [("HOME", hist_h), ("DRAW", hist_d), ("AWAY", hist_a)],
        key=lambda x: x[1]
    )[0]

    game_state = str(r.get("game_state", "") or "")
    dominance_v = float(r.get("dominance", 0.0) or 0.0)
    fake_home = bool(r.get("fake_home_pressure", False) or r.get("fake_home_pressure_finish", False))

    ng_smart = r.get("next_goal_prediction_smart") or {}
    ng_pred_side = str(ng_smart.get("prediction", "") or "").strip().upper()
    ng_pred_conf = float(ng_smart.get("confidence", 0) or 0)

    away_pitch_edge = (
        ("AWAY" in game_state.upper())
        or (momentum < -0.08)
        or (lam_a > lam_h + 0.05)
        or (p_away_next > p_home_next + 0.03)
        or (dominance_v < -0.08)
        or fake_home
        or (ng_pred_side == "AWAY" and ng_pred_conf >= 0.55)
        or (p_away_next >= 0.35 and p_away_next > p_home_next + 0.06)
    )

    # Meta 1X2 lahko začasno "pobegne" proti HOME, medtem ko so live signali jasno AWAY.
    # V tem primeru je prepovedano trditi "Domači imajo pobudo / gol domačih je verjeten".
    if live_side == "HOME" and away_pitch_edge:
        print("Gostje kontrolirajo igro in imajo boljše live signale.")
        print("Naslednji gol je bolj verjeten za goste.")
        if str(top1[0] or "").strip() in ("0-0", "0:0"):
            print("Vendar je najbolj verjeten končni izid še vedno 0-0 (Top1) — to ni protislovje z NEXT GOAL.")
        print("1X2 meta lahko še kaže rahlo HOME, ampak to je struktura/šum, ne pa pritisk na igrišču.")
        print("Zato interpretacija sledi dominanci gostov, ne obratno.")

    elif live_side == "AWAY" and hist_side == "DRAW":
        print("Tekma je še odprta, čeprav gostje vodijo.")
        print("Gostje so trenutno nevarnejši in bližje naslednjemu golu.")
        print("Vendar zgodovina kaže možnost comebacka.")
        print("Domači še vedno lahko dosežejo gol.")
        print("Možna sta oba scenarija: gol gostov ali gol domačih.")

    elif live_side == "DRAW" and away_pitch_edge:
        print("Gostje kontrolirajo tekmo in imajo boljše live signale.")
        print("Naslednji gol je bolj verjeten za goste.")
        if str(top1[0] or "").strip().replace(":", "-") == "0-0":
            print("Vendar je najbolj verjeten končni izid še vedno 0-0 (Top1) — NEXT GOAL ni isto kot 1X2 stava.")
        print("Remi lahko ostane najmočnejša 1X2 smer, čeprav gostje pritiskajo.")

    elif live_side == "AWAY" and hist_side == "AWAY":
        print("Gostje kontrolirajo tekmo.")
        print("Prihajajo do boljših priložnosti.")
        print("Domači težko ustvarijo nevarnost.")
        print("Zelo verjeten naslednji gol gostov.")
        print("Tekma se lahko odloči.")

    elif live_side == "HOME" and hist_side == "AWAY":
        print("Domači pritiskajo.")
        print("Gostje pa ostajajo nevarni iz kontre.")
        print("Možen je nasprotni gol gostov.")
        print("Tekma je zelo odprta.")

    elif live_side == "HOME":
        # Če je HOME pritisk lažen (veliko danger/attacks, malo SOT/shot quality),
        # ne sme pisati, da je gol HOME verjeten.
        fake_finish = bool(r.get("fake_home_pressure_finish", False))
        finish_dom = bool(r.get("finishing_dominance", False))
        if fake_finish or fake_home or (finish_dom and sot_a >= 5 and sot_h <= 2) or away_pitch_edge:
            print("Domači pritiskajo, ampak brez kvalitete zaključkov.")
            print("To je lažen pritisk (FAKE PRESSURE).")
            print("Gostje so učinkovitejši in tekmo kontrolirajo.")
        else:
            print("Domači imajo pobudo.")
            print("Več napadov in večji pritisk.")
            print("Gol domačih je verjeten.")

    elif live_side == "DRAW":
        print("Tekma je izenačena.")
        print("Tempo ni enostranski.")
        print("Možen gol na obe strani.")

    else:
        if p_goal >= 0.55:
            print("Obe ekipi prideta do priložnosti.")
            print("Gol je verjeten.")
        else:
            print("Tempo ni dovolj močan.")
            print("Manj prostora za gol.")

    if abs(lam_h - lam_a) < 0.08:
        print("Smer gola je nejasna.")
    elif lam_h > lam_a:
        print("Rahla smer je proti HOME.")
    else:
        print("Rahla smer je proti AWAY.")

    print(f"Zato model vidi: {top1[0]}")
    print("")
    print(f"SMER: H {final_h * 100:.0f}% | D {final_d * 100:.0f}% | A {final_a * 100:.0f}%")
    print(f"HISTORY: H {hist_h * 100:.0f}% | D {hist_d * 100:.0f}% | A {hist_a * 100:.0f}%")

    print("\nČe pade gol:\n")
    if lam_h > lam_a + 0.05:
        print("lambda rahlo HOME")
        if top2:
            print(f"→ {top2[0]}")
    elif lam_a > lam_h + 0.05:
        print("lambda rahlo AWAY")
        if top2:
            print(f"→ {top2[0]}")
    else:
        print("lambda skoraj izenačeno")
        if top2:
            print(f"→ možen {top2[0]}")

    if abs(sot_h - sot_a) <= 1 and top3:
        print("\nSOT izenačen")
        print(f"→ možen {top3[0]}")

    print("\nNEXT GOAL:")
    print(f"HOME {round(p_home_next * 100)}%")
    print(f"AWAY {round(p_away_next * 100)}%")

    if abs(p_home_next - p_away_next) <= 0.06:
        print("\n→ skoraj 50-50")
    elif p_home_next > p_away_next:
        print("\n→ rahla prednost HOME")
    else:
        print("\n→ rahla prednost AWAY")

    max_mc = max(float(r.get("mc_h_adj", 0.0)), float(r.get("mc_x_adj", 0.0)), float(r.get("mc_a_adj", 0.0)))
    if max_mc < 0.60:
        print("\nModel ni overconfident.")
    else:
        print("\nModel ima močnejše zaupanje v Top1.")



def print_cfos_history_engine(r):
    print("\n================ CFOS HISTORY ENGINE =================\n")

    base_h = float(r.get("hist_home", 0) or 0)
    base_d = float(r.get("hist_draw", 0) or 0)
    base_a = float(r.get("hist_away", 0) or 0)

    print("BASE (FINAL HISTORY)")
    print(f"H {base_h:.3f}")
    print(f"D {base_d:.3f}")
    print(f"A {base_a:.3f}\n")

    learn_h = float(r.get("rh", 1.0) or 1.0)
    learn_d = float(r.get("rx", 1.0) or 1.0)
    learn_a = float(r.get("ra", 1.0) or 1.0)

    print("LEARNING RATIOS")
    print(f"H x{learn_h:.3f}")
    print(f"D x{learn_d:.3f}")
    print(f"A x{learn_a:.3f}\n")

    post_h = base_h * learn_h
    post_d = base_d * learn_d
    post_a = base_a * learn_a

    norm = post_h + post_d + post_a
    if norm > 0:
        post_h /= norm
        post_d /= norm
        post_a /= norm

    print("AFTER LEARNING (normalized)")
    print(f"H {post_h:.3f}")
    print(f"D {post_d:.3f}")
    print(f"A {post_a:.3f}\n")

    momentum = float(r.get("momentum", 0) or 0)
    lam_h = float(r.get("lam_h", 0) or 0)
    lam_a = float(r.get("lam_a", 0) or 0)
    danger_h = float(r.get("danger_h", 0) or 0)
    danger_a = float(r.get("danger_a", 0) or 0)

    momentum_side = "HOME" if momentum > 0.08 else "AWAY" if momentum < -0.08 else "NONE"
    lambda_side = "HOME" if lam_h > lam_a else "AWAY" if lam_a > lam_h else "NONE"
    danger_side = "HOME" if danger_h > danger_a else "AWAY" if danger_a > danger_h else "NONE"

    print("LIVE ADJUST")
    print(f"Momentum        {momentum_side}")
    print(f"Lambda bias     {lambda_side}")
    print(f"Danger bias     {danger_side}\n")

    after_live_h = float(r.get("mc_h_adj", r.get("mc_h_raw", 0)) or 0)
    after_live_d = float(r.get("mc_x_adj", r.get("mc_x_raw", 0)) or 0)
    after_live_a = float(r.get("mc_a_adj", r.get("mc_a_raw", 0)) or 0)

    print("AFTER LIVE")
    print(f"H {after_live_h:.3f}")
    print(f"D {after_live_d:.3f}")
    print(f"A {after_live_a:.3f}\n")

    final_h = float(r.get("meta_home", after_live_h) or after_live_h)
    final_d = float(r.get("meta_draw", after_live_d) or after_live_d)
    final_a = float(r.get("meta_away", after_live_a) or after_live_a)

    print("FINAL (MODEL)")
    print(f"H {final_h:.3f}")
    print(f"D {final_d:.3f}")
    print(f"A {final_a:.3f}")

    print("\n====================================================\n")


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




def apply_meta_meta_iq(mc_h_adj, mc_x_adj, mc_a_adj, hist_home, hist_draw, hist_away, lam_h, lam_a, momentum):
    # =====================================================
    # META-META IQ ENGINE (SELF AWARE MODEL)
    # =====================================================

    # save BEFORE
    mc_h_before = mc_h_adj
    mc_x_before = mc_x_adj
    mc_a_before = mc_a_adj

    self_trust = 0.0
    consensus = 0

    if mc_h_adj > mc_x_adj and hist_home > hist_draw and lam_h > lam_a:
        consensus += 1

    if mc_a_adj > mc_x_adj and hist_away > hist_draw and lam_a > lam_h:
        consensus += 1

    if mc_x_adj > mc_h_adj and hist_draw > hist_home:
        consensus += 1

    if consensus >= 2:
        self_trust += 1.5

    disagreement = 0

    if abs(mc_h_adj - hist_home) > 0.20:
        disagreement += 1

    if abs(mc_a_adj - hist_away) > 0.20:
        disagreement += 1

    if abs(lam_h - lam_a) < 0.05 and abs(momentum) > 0.12:
        disagreement += 1

    if disagreement >= 2:
        self_trust -= 1.2

    if self_trust > 1:
        mc_h_adj *= 1.04
        mc_a_adj *= 1.04
        mc_x_adj *= 0.94
    elif self_trust < -1:
        mc_x_adj *= 1.08

    s = mc_h_adj + mc_x_adj + mc_a_adj
    if s > 0:
        mc_h_adj /= s
        mc_x_adj /= s
        mc_a_adj /= s

    # =====================================================
    # META-META IQ PRINT
    # =====================================================
    print("")
    print("============= META-META IQ =============")
    print(f"IQ self_trust : {self_trust:.3f}")
    print(f"Consensus     : {consensus}")
    print(f"Disagreement  : {disagreement}")

    print("")
    print("MC BEFORE IQ")
    print(f"H: {mc_h_before:.2f}")
    print(f"X: {mc_x_before:.2f}")
    print(f"A: {mc_a_before:.2f}")

    print("")
    print("MC AFTER IQ")
    print(f"H: {mc_h_adj:.2f}")
    print(f"X: {mc_x_adj:.2f}")
    print(f"A: {mc_a_adj:.2f}")

    return mc_h_adj, mc_x_adj, mc_a_adj, self_trust

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


def load_clean_history(file=CLEAN_SNAPSHOT_FILE):
    history = []
    try:
        with open(file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                history.append(row)
    except Exception:
        pass
    return history


def make_clean_bucket(r):
    m = safe_int(r.get("minute", 0), 0)
    if m < 30:
        m_bucket = "0-29"
    elif m < 60:
        m_bucket = "30-59"
    elif m < 76:
        m_bucket = "60-75"
    else:
        m_bucket = "76-90"

    sh = safe_int(r.get("score_home", 0), 0)
    sa = safe_int(r.get("score_away", 0), 0)
    sd = sh - sa
    if sd <= -2:
        sd_bucket = "-2-"
    elif sd == -1:
        sd_bucket = "-1"
    elif sd == 0:
        sd_bucket = "0"
    elif sd == 1:
        sd_bucket = "+1"
    else:
        sd_bucket = "+2+"

    sot_total = safe_int(r.get("sot_home", 0), 0) + safe_int(r.get("sot_away", 0), 0)
    sot_bucket = "low" if sot_total < 4 else "high"

    danger_total = safe_int(r.get("danger_home", 0), 0) + safe_int(r.get("danger_away", 0), 0)
    if danger_total < 60:
        dng_bucket = "low"
    elif danger_total < 120:
        dng_bucket = "mid"
    else:
        dng_bucket = "high"

    return (m_bucket, sd_bucket, sot_bucket, dng_bucket)


def get_clean_history_bias(history, current_row):
    bucket = make_clean_bucket(current_row)
    counts = defaultdict(int)

    for row in history:
        try:
            if make_clean_bucket(row) == bucket:
                result = str(row.get("result", "")).strip().upper()
                if result in ("H", "D", "A"):
                    counts[result] += 1
        except Exception:
            continue

    total = counts["H"] + counts["D"] + counts["A"]
    if total == 0:
        return 0.33, 0.33, 0.33
    return counts["H"] / total, counts["D"] / total, counts["A"] / total


def get_clean_history_bias_n(history, current_row):
    """
    Enako kot get_clean_history_bias(), ampak vrne tudi N (velikost bucket vzorca),
    da lahko varno blendamo 2 različna history vira brez rušenja logike.
    """
    bucket = make_clean_bucket(current_row)
    counts = defaultdict(int)

    for row in history:
        try:
            if make_clean_bucket(row) == bucket:
                result = str(row.get("result", "")).strip().upper()
                if result in ("H", "D", "A"):
                    counts[result] += 1
        except Exception:
            continue

    total = counts["H"] + counts["D"] + counts["A"]
    if total == 0:
        return 0.33, 0.33, 0.33, 0
    return counts["H"] / total, counts["D"] / total, counts["A"] / total, total


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
# LEARN RATIOS (1X2) PRINT WITH REAL %
# ============================================================
def print_learn_ratios(rh, rx, ra, n_1x2):
    ph = (rh - 1.0) * 100.0
    pd = (rx - 1.0) * 100.0
    pa = (ra - 1.0) * 100.0

    base = 1 / 3

    h_est = int(n_1x2 * base * rh)
    d_est = int(n_1x2 * base * rx)
    a_est = int(n_1x2 * base * ra)

    h_pct = (h_est / n_1x2 * 100) if n_1x2 else 0
    d_pct = (d_est / n_1x2 * 100) if n_1x2 else 0
    a_pct = (a_est / n_1x2 * 100) if n_1x2 else 0

    print("")
    print(f"Learn ratios (1X2)  (bucket n: {n_1x2})")
    print("")
    print(f"H  {rh:.3f}   ({ph:+.1f}%)   ≈ {h_est}/{n_1x2}   → {h_pct:.1f}%")
    print(f"D  {rx:.3f}   ({pd:+.1f}%)   ≈ {d_est}/{n_1x2}   → {d_pct:.1f}%")
    print(f"A  {ra:.3f}   ({pa:+.1f}%)   ≈ {a_est}/{n_1x2}   → {a_pct:.1f}%")




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
    header = [
        "home", "away", "minute", "xg_total", "sot_total", "shots_total", "score_diff",
        "odds_h", "odds_x", "odds_a", "lam_total_raw", "p_goal_raw",
        "mc_h_raw", "mc_x_raw", "mc_a_raw", "score_home", "score_away",
        "ts", "game_type", "danger_bucket"
    ]

    new_row = [
        home, away, minute, f"{xg_total:.4f}", f"{sot_total:.4f}", f"{shots_total:.4f}",
        score_diff, f"{odds_home:.4f}", f"{odds_draw:.4f}", f"{odds_away:.4f}",
        f"{lam_total_raw:.6f}", f"{p_goal_raw:.6f}", f"{mc_h_raw:.6f}", f"{mc_x_raw:.6f}",
        f"{mc_a_raw:.6f}", score_home, score_away, ts, game_type, bucket_danger(danger_total)
    ]

    rows = []
    if os.path.exists(SNAP_FILE):
        try:
            with open(SNAP_FILE, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                _ = next(reader, None)
                for parts in reader:
                    if not parts:
                        continue
                    if len(parts) >= 3 and parts[0] == home and parts[1] == away and safe_int(parts[2]) == minute:
                        continue
                    rows.append(parts)
        except:
            rows = []

    rows.append(new_row)

    try:
        with open(SNAP_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        print("Snapshot shranjen v", SNAP_FILE)
    except Exception as e:
        print("Napaka pri shranjevanju snapshot:", e)


def finalize_snapshots(final_h, final_a, filter_home=None, filter_away=None):
    if not os.path.exists(SNAP_FILE):
        print("Ni snapshotov za zaključek.")
        return

    all_rows = []
    header = None

    try:
        with open(SNAP_FILE, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                print("Ni snapshotov za zaključek.")
                return
            for row in reader:
                if row:
                    all_rows.append(row)
    except Exception as e:
        print("Napaka pri branju snapshot:", e)
        return

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

    try:
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
    except Exception as e:
        print("Napaka pri pisanju v LEARN_FILE:", e)

    if len(remaining_rows) == 0:
        try:
            os.remove(SNAP_FILE)
        except:
            pass
    else:
        try:
            with open(SNAP_FILE, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(remaining_rows)
        except Exception as e:
            print("Napaka pri pisanju preostalih snapshot:", e)

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

def save_match_result(home, away, minute, prediction_1x2, prediction_score, result_1x2, result_score, history_pred=""):
    header = [
        "home", "away", "minute",
        "prediction_1x2", "prediction_score",
        "history_pred",
        "result_1x2", "result_score"
    ]

    prediction_1x2 = normalize_outcome_label(prediction_1x2)
    result_1x2 = normalize_outcome_label(result_1x2)
    history_pred = normalize_outcome_label(history_pred)

    rows = []

    try:
        if os.path.exists(MATCH_RESULT_FILE):
            with open(MATCH_RESULT_FILE, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row:
                        continue

                    same_match = (
                        row.get("home", "") == home and
                        row.get("away", "") == away and
                        safe_int(row.get("minute", 0)) == safe_int(minute)
                    )

                    if same_match:
                        continue

                    rows.append([
                        row.get("home", ""),
                        row.get("away", ""),
                        safe_int(row.get("minute", 0)),
                        normalize_outcome_label(row.get("prediction_1x2", "")),
                        row.get("prediction_score", ""),
                        normalize_outcome_label(row.get("history_pred", "")),
                        normalize_outcome_label(row.get("result_1x2", "")),
                        row.get("result_score", "")
                    ])
    except:
        rows = []

    rows.append([
        home, away, safe_int(minute), prediction_1x2, prediction_score,
        history_pred, result_1x2, result_score
    ])

    try:
        with open(MATCH_RESULT_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
    except:
        pass


def load_match_results(home, away):
    rows = []
    if not os.path.exists(MATCH_RESULT_FILE):
        return rows

    try:
        with open(MATCH_RESULT_FILE, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("home") == home and row.get("away") == away:
                    rows.append({
                        "home": row.get("home", ""),
                        "away": row.get("away", ""),
                        "minute": safe_int(row.get("minute", 0)),
                        "prediction_1x2": normalize_outcome_label(row.get("prediction_1x2", "")),
                        "prediction_score": row.get("prediction_score", ""),
                        "history_pred": normalize_outcome_label(row.get("history_pred", "")),
                        "result_1x2": normalize_outcome_label(row.get("result_1x2", "")),
                        "result_score": row.get("result_score", "")
                    })
    except:
        return []

    rows.sort(key=lambda x: x["minute"])
    return rows


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

    try:
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
    except Exception as e:
        print("Napaka pri shranjevanju match memory:", e)
        return False
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
    # Safety initializations for variables that may be used before assignment
    counter_blocked = False
    dominant_side = None
    next_goal_prediction = "N/A"
    next_goal_bet = "SKIP"
    next_goal_reason = ""

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

    bc_h = get_num(data, 18)
    bc_a = get_num(data, 19)

    y_h = get_num(data, 20)
    y_a = get_num(data, 21)
    red_h = get_num(data, 22)
    red_a = get_num(data, 23)
    pos_h = get_num(data, 24)
    pos_a = get_num(data, 25)
    blocked_h = get_num(data, 26)
    blocked_a = get_num(data, 27)
    bcm_h = get_num(data, 28)
    bcm_a = get_num(data, 29)
    corners_h = get_num(data, 30)
    corners_a = get_num(data, 31)

    yellow_h = y_h
    yellow_a = y_a

    bc_h = clamp(bc_h, 0.0, 5.0)
    bc_a = clamp(bc_a, 0.0, 5.0)

    # ============================================================
    # AUTO SWAP DISABLED (BUG FIX)
    # ============================================================

    swap_flag = False

    # ============================================================
    # CFOS CSV FORMAT VALIDATOR (CRITICAL)
    # ============================================================

    if minute < 1 or minute > 130:
        print("ERROR: Minute index wrong (CSV SHIFT)")
        return None

    if xg_h > 10 or xg_a > 10:
        print("❌ ERROR: xG unrealistic (CSV SHIFT)")
        return None

    if shots_h > 50 or shots_a > 50:
        print("❌ ERROR: shots unrealistic (CSV SHIFT)")
        return None

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

    if (pos_h + pos_a) > 105:
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

    # ENTRY ENGINE: delta HOME v zadnjih ~5' (match memory; za TRIGGER)
    entry_l5_shots_h = 0.0
    entry_l5_sot_h = 0.0
    entry_l5_danger_h = 0.0
    if match_rows and minute >= 1:
        win5 = [row for row in match_rows if int(row.get("minute", 0) or 0) >= minute - 5]
        if len(win5) >= 2:
            win5.sort(key=lambda x: int(x.get("minute", 0) or 0))
            _a5, _b5 = win5[0], win5[-1]
            entry_l5_shots_h = max(
                0.0, float(_b5.get("shots_h", 0) or 0) - float(_a5.get("shots_h", 0) or 0)
            )
            entry_l5_sot_h = max(
                0.0, float(_b5.get("sot_h", 0) or 0) - float(_a5.get("sot_h", 0) or 0)
            )
            entry_l5_danger_h = max(
                0.0, float(_b5.get("danger_h", 0) or 0) - float(_a5.get("danger_h", 0) or 0)
            )

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

    # ============================================================
    # FINAL MASTER FIX BLOK (LIVE DOMINANCE HAS PRIORITY)
    # ============================================================
    live_favor = "NONE"
    if xg_a > max(0.15, xg_h * 2.0) and momentum < -0.4 and sot_a >= 3:
        game_type = "AWAY DOMINATION"
        live_favor = "AWAY"
    elif xg_h > max(0.15, xg_a * 2.0) and momentum > 0.4 and sot_h >= 3:
        game_type = "HOME DOMINATION"
        live_favor = "HOME"

    # ============================================================
    # SPLIT CONTROL DETECTOR (CRITICAL)
    # ============================================================

    split_control = False

    if (
        attacks_h > attacks_a * 1.4
        and danger_h > danger_a * 1.5
        and xg_a > xg_h * 3
    ):
        split_control = True

    # ============================================================
    # MOMENTUM LIMITER
    # ============================================================

    if split_control:
        momentum *= 0.7

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
    danger_dominance = dominance  # save danger-based dominance for return dict

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
    # LEAD CONTROL (late game fix)
    # ============================================================

    if minute >= 75 and score_diff == 1:

        if momentum > 0:
            lam_h_raw *= 1.12
            lam_a_raw *= 0.90

        elif momentum < 0:
            lam_a_raw *= 1.08

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
    # 🔥 ANTI COUNTER + FALSE MOMENTUM FIX (FINAL)
    # ============================================================

    lam_total_before = lam_h_raw + lam_a_raw

    anti_high_tempo = (tempo_shots > 0.22 or tempo_danger > 1.15)
    anti_high_lambda = (lam_h_raw + lam_a_raw) > 1.20
    anti_no_wave = not wave["active"]

    danger_ratio = safe_div(danger_h, danger_a, 1.0)

    # FIX 1: OVERPRESSURE COUNTER
    if minute >= 60:
        if anti_high_tempo and anti_high_lambda and anti_no_wave:
            lam_h_raw *= 0.80
            lam_a_raw *= 1.30

    # FIX 2: LEADING TEAM RISK (CORRECTED)
    if minute >= 60 and score_diff == 1:
        if abs(momentum) > 0.18:
            # zmanjšaj dominantno stran
            if lam_a_raw > lam_h_raw:
                lam_a_raw *= 0.85
            else:
                lam_h_raw *= 0.85

    # FIX 3: FAKE DOMINANCE
    if minute >= 60 and sot_h >= 3 and attacks_h > attacks_a:
        if anti_no_wave and danger_ratio < 1.30:
            lam_h_raw *= 0.85

    # FIX 4: FALSE MOMENTUM TRAP  ✅ (NOVO)
    if minute >= 55:
        if anti_no_wave and tempo_shots < 0.28:
            if momentum > 0.12:
                lam_h_raw *= 0.85
                lam_a_raw *= 0.85

    # FIX 5: LAMBDA RATIO LIMIT
    if minute >= 60:
        lam_a_to_h_ratio = safe_div(lam_a_raw, lam_h_raw, 1.0)
        if lam_a_to_h_ratio > 4.0:
            lam_a_raw *= 0.75
        lam_h_to_a_ratio = safe_div(lam_h_raw, lam_a_raw, 1.0)
        if lam_h_to_a_ratio > 4.0:
            lam_h_raw *= 0.75

    # NORMALIZACIJA
    lam_total_after = lam_h_raw + lam_a_raw
    if lam_total_after > 0:
        scale = lam_total_before / lam_total_after
        lam_h_raw *= scale
        lam_a_raw *= scale

    # FINAL CLAMP
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
    clean_history = load_clean_history()

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
    # GLOBAL FAKE CONTROL DETECTOR
    # ============================================================

    fake_control = False

    losing_side = "HOME" if score_diff < 0 else "AWAY"
    leading_side = "AWAY" if score_diff < 0 else "HOME"

    shots_losing = shots_h if losing_side == "HOME" else shots_a
    shots_leading = shots_a if losing_side == "HOME" else shots_h

    sot_losing = sot_h if losing_side == "HOME" else sot_a
    sot_leading = sot_a if losing_side == "HOME" else sot_h

    danger_losing = danger_h if losing_side == "HOME" else danger_a
    danger_leading = danger_a if losing_side == "HOME" else danger_h

    if (
        minute >= 65
        and abs(score_diff) == 1
        and shots_losing >= shots_leading * 0.70
        and sot_losing >= sot_leading * 0.60
        and tempo_danger < 1.08
        and game_type in ("BALANCED", "PRESSURE")
    ):
        fake_control = True

    if fake_control:
        if losing_side == "HOME":
            lam_h_raw *= 1.28
            lam_a_raw *= 0.88
        else:
            lam_a_raw *= 1.28
            lam_h_raw *= 0.88

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

    # Overflow protection: clamp raw lambdas to finite range
    if not math.isfinite(lam_h_raw):
        lam_h_raw = 0.0
    if not math.isfinite(lam_a_raw):
        lam_a_raw = 0.0
    if not math.isfinite(lam_c_raw):
        lam_c_raw = 0.0
    lam_h_raw = clamp(lam_h_raw, 0.0, 10.0)
    lam_a_raw = clamp(lam_a_raw, 0.0, 10.0)
    lam_c_raw = clamp(lam_c_raw, 0.0, 10.0)

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

    # ============================================================
    # GLOBAL TIME DECAY (LAMBDA)
    # ============================================================
    # Bližje koncu tekme pritisk praviloma manj pomeni za nov gol.
    # Če ekipa vodi (ni DRAW), decay še dodatno zaostri.
    time_factor = time_decay(minute)
    if score_diff != 0:
        time_factor *= 0.90
    lam_h *= time_factor
    lam_a *= time_factor

    lam_total = lam_h + lam_a + lam_c

    # ============================================================
    # CFOS OVERPRESSURE + HIGH LAMBDA + COUNTER EQUALIZER
    # ============================================================

    if lam_h > 0:
        lam_ratio = lam_a / lam_h
    else:
        lam_ratio = 3.0
    high_tempo = False
    high_lambda = False
    no_wave = True
    overpressure_home = False
    overpressure_away = False
    fake_home_pressure = False
    fake_home_pressure_finish = False
    finishing_dominance = False
    game_decided_hard = False
    if score_diff < 0:
        leading_side = "AWAY"
    elif score_diff > 0:
        leading_side = "HOME"
    else:
        leading_side = "DRAW"

    if minute >= 55:

        score_diff = score_home - score_away

        if lam_h > 0:
            lam_ratio = lam_a / lam_h
        else:
            lam_ratio = 3.0

        high_tempo = (
            tempo_shots > 0.22
            or tempo_danger > 1.15
        )

        high_pressure_home = pressure_h > pressure_a * 1.25
        high_pressure_away = pressure_a > pressure_h * 1.25

        p_goal_est = 1 - math.exp(-(lam_h + lam_a + lam_c)) if (lam_h + lam_a + lam_c) > 0 else 0.0
        high_lambda = (
            lam_total > 1.20
            or p_goal_est > 0.65
            or lam_h > 0.80
            or lam_a > 0.80
        )

        attack_wave = "YES" if wave["active"] else "NO"
        no_wave = attack_wave == "NO"

        overpressure_home = (
            high_tempo
            and high_pressure_home
            and high_lambda
            and no_wave
        )

        overpressure_away = (
            high_tempo
            and high_pressure_away
            and high_lambda
            and no_wave
        )

        if score_diff < 0:
            leading_side = "AWAY"
            if lam_ratio > 1.4 and (overpressure_away or high_lambda):
                lam_a *= 0.80
                lam_h *= 1.22
                lam_c += 0.08

        elif score_diff > 0:
            leading_side = "HOME"
            inv_lam_ratio = (1 / lam_ratio) if lam_ratio > 0 else 2.0
            if inv_lam_ratio > 1.4 and (overpressure_home or high_lambda):
                lam_h *= 0.80
                lam_a *= 1.22
                lam_c += 0.08
        else:
            leading_side = "DRAW"

        if lam_total > 1.55:
            lam_h *= 0.92
            lam_a *= 0.92
            lam_c += 0.05

        if minute >= 70 and (overpressure_home or overpressure_away):
            lam_c += 0.06

        # ============================================================
        # LATE FAKE HOME PRESSURE TRAP
        # ============================================================
        if (
            minute >= 80
            and leading_side == "AWAY"
            and float(tempo_shots_h or 0.0) > float(tempo_shots_a or 0.0)
            and float(momentum or 0.0) < 0.0
            and no_wave
        ):
            fake_home_pressure = True
            lam_h *= 0.85

        # ============================================================
        # FAKE PRESSURE FIX (KVALITETA > KOLIČINA)
        # ============================================================
        # Veliko "danger" brez zaključkov (SOT) je tipičen lažen pritisk.
        if (
            (not fake_home_pressure)
            and float(sot_h or 0.0) <= 2.0
            and float(danger_h or 0.0) > float(danger_a or 0.0)
            and float(shot_q_h or 0.0) <= 0.12
        ):
            fake_home_pressure = True
            fake_home_pressure_finish = True
            lam_h *= 0.70

        # ============================================================
        # FINISHING DOMINANCE (SOT) — PRO
        # ============================================================
        # Če ima AWAY ogromno več SOT, je to realna dominance zaključkov.
        if float(sot_a or 0.0) >= 5.0 and float(sot_h or 0.0) <= 2.0:
            finishing_dominance = True
            lam_a *= 1.20
            lam_h *= 0.80

        lam_h = clamp(lam_h, 0.0, 1.60)
        lam_a = clamp(lam_a, 0.0, 1.60)
        lam_c = clamp(lam_c, 0.0, 0.20)
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
    # LAMBDA ROTATION (CRITICAL FIX)
    # ============================================================

    if lam_h > 0:
        lam_ratio_sc = lam_a / lam_h
        if lam_ratio_sc > 3.0:
            scale = 3.0 / lam_ratio_sc
            lam_a *= scale
    lam_total = lam_h + lam_a + lam_c

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
    p_goal = clamp(p_goal, 0.0, 1.0)

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

    # ============================================================
    # GAME DECIDED HARD FILTER (90+ in -2/-3)
    # ============================================================
    # Pozno, tekma odločena: manj časa za gol -> dodatno znižaj P(goal) in P(goal_10).
    if minute >= 90 and score_diff <= -2:
        game_decided_hard = True
        p_goal *= 0.60
        p_goal_10 *= 0.60
        p_goal = clamp(p_goal, 0.0, 1.0)
        p_goal_10 = clamp(p_goal_10, 0.0, 1.0)
        p_no_goal = 1.0 - p_goal

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

    mem_rows = load_match_results(home, away)
    mem_n = len(mem_rows)

    mem_home = 0.0
    mem_draw = 0.0
    mem_away = 0.0

    for r in mem_rows:
        res = str(r.get("result_1x2", "")).strip().upper()

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

    if hist_home >= hist_draw and hist_home >= hist_away:
        history_pred = "HOME"
    elif hist_away >= hist_home and hist_away >= hist_draw:
        history_pred = "AWAY"
    else:
        history_pred = "DRAW"

    # ============================================================
    # META-META IQ ENGINE
    # ============================================================

    mc_h_adj, mc_x_adj, mc_a_adj, self_trust = apply_meta_meta_iq(
        mc_h_adj=mc_h_adj,
        mc_x_adj=mc_x_adj,
        mc_a_adj=mc_a_adj,
        hist_home=hist_home,
        hist_draw=hist_draw,
        hist_away=hist_away,
        lam_h=lam_h,
        lam_a=lam_a,
        momentum=momentum
    )

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

    # ============================================================
    # SPLIT CONTROL META CORRECTION
    # ============================================================

    if split_control:
        mc_x_adj *= 1.35  # draw boost +35%
        mc_a_adj *= 0.80  # away reduce -20%
        mc_h_adj *= 1.10  # home slight boost +10%

    s = mc_h_adj + mc_x_adj + mc_a_adj
    if s > 1e-9:
        mc_h_adj /= s
        mc_x_adj /= s
        mc_a_adj /= s
    else:
        mc_h_adj, mc_x_adj, mc_a_adj = mc_h_raw, mc_x_raw, mc_a_raw

    # ============================================================
    # REAL-TIME vs HISTORY MIX (AFTER META)
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

    hist_weight = hist_conf * (1 - rt_strength * 0.6) * 0.35
    rt_weight = 1 - hist_weight

    mc_h_adj = mc_h_adj * rt_weight + hist_home * hist_weight
    mc_x_adj = mc_x_adj * rt_weight + hist_draw * hist_weight
    mc_a_adj = mc_a_adj * rt_weight + hist_away * hist_weight

    s = mc_h_adj + mc_x_adj + mc_a_adj
    if s > 1e-9:
        mc_h_adj /= s
        mc_x_adj /= s
        mc_a_adj /= s
    else:
        mc_h_adj, mc_x_adj, mc_a_adj = mc_h_raw, mc_x_raw, mc_a_raw

    current_row = {
        "minute": minute,
        "score_home": score_home,
        "score_away": score_away,
        "sot_home": sot_h,
        "sot_away": sot_a,
        "danger_home": danger_h,
        "danger_away": danger_a,
    }
    hist_clean_home, hist_clean_draw, hist_clean_away, clean_n = get_clean_history_bias_n(clean_history, current_row)

    # ============================================================
    # MERGE: 2 HISTORY SISTEMA -> 1 ENOTEN "HISTORY BLEND"
    # - learn history: hist_home/hist_draw/hist_away (hist_n)
    # - clean history: hist_clean_* (clean_n)
    # Ohranimo isti output (mc_*_adj), samo uteži so zdaj varne in dinamične.
    # ============================================================
    clean_conf = clean_n / 60.0
    if clean_conf > 1:
        clean_conf = 1

    # clean vpliv naj bo manjši od learn, ker je bucket bolj grob
    clean_weight = clean_conf * (1 - rt_strength * 0.6) * 0.22

    # zaščita: skupni history vpliv naj ne preseže ~0.55
    total_hist_weight = hist_weight + clean_weight
    if total_hist_weight > 0.55:
        scale = 0.55 / total_hist_weight
        hist_weight *= scale
        clean_weight *= scale
        total_hist_weight = hist_weight + clean_weight

    rt_weight = 1 - total_hist_weight

    mc_h_adj = mc_h_raw * rt_weight + hist_home * hist_weight + hist_clean_home * clean_weight
    mc_x_adj = mc_x_raw * rt_weight + hist_draw * hist_weight + hist_clean_draw * clean_weight
    mc_a_adj = mc_a_raw * rt_weight + hist_away * hist_weight + hist_clean_away * clean_weight

    s_clean = mc_h_adj + mc_x_adj + mc_a_adj
    if s_clean > 1e-9:
        mc_h_adj /= s_clean
        mc_x_adj /= s_clean
        mc_a_adj /= s_clean
    else:
        mc_h_adj, mc_x_adj, mc_a_adj = mc_h_raw, mc_x_raw, mc_a_raw
# ZAČETEK DELA 7.4/ 8

    # ============================================================
    # LATE EQUALIZER BALANCER (SOFT FIX)
    # ============================================================
    if minute >= 70 and abs(score_diff) == 1:

        # HOME izgublja
        if score_diff < 0:
            lam_h *= 1.20
            lam_a *= 0.92
            lam_h += 0.12

        # AWAY izgublja
        else:
            lam_a *= 1.20
            lam_h *= 0.92
            lam_a += 0.12

        lam_h = clamp(lam_h, 0.0, 1.80)
        lam_a = clamp(lam_a, 0.0, 1.80)
        lam_c = clamp(lam_c, 0.0, 0.08)
        lam_total = clamp(lam_h + lam_a + lam_c, 0.0, 2.20)

        p_goal = 1 - math.exp(-lam_total)
        p_no_goal = math.exp(-lam_total)

        lam_attack = lam_h + lam_a
        if lam_attack > 0:
            p_home_next = (lam_h / lam_attack) * p_goal
            p_away_next = (lam_a / lam_attack) * p_goal
        else:
            p_home_next = 0.0
            p_away_next = 0.0
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
    # LATE EQUALIZER LIMITER (NO HARD OVERRIDE)
    # ============================================================
    if minute >= 70 and abs(score_diff) == 1:
        if score_diff < 0:
            mc_x_adj = max(mc_x_adj, 0.28)
            mc_a_adj = min(mc_a_adj, 0.62)
        elif score_diff > 0:
            mc_x_adj = max(mc_x_adj, 0.28)
            mc_h_adj = min(mc_h_adj, 0.62)

        s = mc_h_adj + mc_x_adj + mc_a_adj
        if s > 1e-9:
            mc_h_adj /= s
            mc_x_adj /= s
            mc_a_adj /= s

    mc_h_adj = clamp(mc_h_adj, 0.0, 1.0)
    mc_x_adj = clamp(mc_x_adj, 0.0, 1.0)
    mc_a_adj = clamp(mc_a_adj, 0.0, 1.0)

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

        save_match_result(
            home=home,
            away=away,
            minute=minute,
            prediction_1x2=predikcija["napoved_izida"],
            prediction_score=predikcija["napoved_rezultata"],
            result_1x2=result,
            result_score=f"{score_home}-{score_away}",
            history_pred=history_pred
        )

        clear_match_memory(home, away)

    # ============================================================
    # FIX NEXT GOAL SIGNAL
    # ============================================================

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

    if danger_h > danger_a and p_away_next > p_home_next:
        p_home_next *= 1.15

    if danger_a > danger_h and p_home_next > p_away_next:
        p_away_next *= 1.15

    s_next = p_home_next + p_away_next
    if s_next > p_goal and s_next > 1e-9:
        scale = p_goal / s_next
        p_home_next *= scale
        p_away_next *= scale

    if fake_control:
        if losing_side == "HOME":
            p_home_next *= 1.22
            p_away_next *= 0.85
        else:
            p_away_next *= 1.22
            p_home_next *= 0.85

    # ============================================================
    # COUNTER KILL MODE (CHAOS + AWAY EFFICIENCY)
    # ============================================================
    counter_kill_mode = (
        str(game_type or "").upper() == "CHAOS"
        and (not bool((wave or {}).get("active", False)))
        and float(lam_ratio or 0.0) > 3.5
        and float(momentum or 0.0) < -0.25
        and float(sot_a or 0.0) >= float(sot_h or 0.0) + 2.0
    )
    if counter_kill_mode:
        p_away_next *= 1.15
        p_home_next *= 0.92
        s_next_ck = p_home_next + p_away_next
        if s_next_ck > p_goal and s_next_ck > 1e-9:
            scale_ck = p_goal / s_next_ck
            p_home_next *= scale_ck
            p_away_next *= scale_ck

    # ============================================================
    # LATE REAL ATTACK WAVE SHIFT
    # ============================================================
    # Če je v zaključku aktivna attack wave, HOME pritisk ni več
    # "fake trap", ampak realna grožnja.
    wave_active = bool((wave or {}).get("active", False))
    if wave_active and minute >= 85:
        fake_home_pressure = False
        if float(tempo_danger or 0.0) > 1.10:
            p_home_next *= 1.10
            s_next_wave = p_home_next + p_away_next
            if s_next_wave > p_goal and s_next_wave > 1e-9:
                scale_wave = p_goal / s_next_wave
                p_home_next *= scale_wave
                p_away_next *= scale_wave

    # ============================================================
    # DUAL THREAT LOCK (OPEN ENDGAME NO-BET ZONE)
    # ============================================================
    dual_threat_mode = (
        wave_active
        and minute >= 80
        and float(p_home_next or 0.0) > 0.35
        and float(p_away_next or 0.0) > 0.35
    )

    next_goal_prediction, next_goal_bet, next_goal_reason = next_goal_bet_engine(
        p_home_next=p_home_next,
        p_away_next=p_away_next,
        lam_h=lam_h,
        lam_a=lam_a,
        momentum=momentum,
        tempo_shots=tempo_shots,
        tempo_danger=tempo_danger,
        game_type=game_type,
        p_goal_10=p_goal_10,
        minute=minute,
    )

    # === FINAL SAFETY (prediction = izključno verjetnosti; brez live/dominance override) ===
    _phs = float(p_home_next or 0.0)
    _pas = float(p_away_next or 0.0)
    if _phs > _pas:
        next_goal_prediction = "HOME"
    elif _pas > _phs:
        next_goal_prediction = "AWAY"
    else:
        next_goal_prediction = "NO GOAL"

    next_goal_prediction_smart = predict_next_goal_smart(
        p_home_next=p_home_next,
        p_away_next=p_away_next,
        lam_h=lam_h,
        lam_a=lam_a,
        danger_h=danger_h,
        danger_a=danger_a,
        xg_h=xg_h,
        xg_a=xg_a,
        momentum=momentum,
        pressure_h=pressure_h,
        pressure_a=pressure_a,
        tempo_danger=tempo_danger,
        sot_h=sot_h,
        sot_a=sot_a,
        game_type=game_type,
        minute=minute,
    )
    # Core smart confidence (uporablja se za window/anti-trap logiko).
    ng_smart_conf_core = float((next_goal_prediction_smart or {}).get("confidence", 0) or 0.0)
    ng_smart_conf = ng_smart_conf_core
    signals_agreement = int((next_goal_prediction_smart or {}).get("signals_agreement", 0) or 0)

    # === CONTROL OVERRIDE (GAME CONTROL ≠ short next-goal window) ===
    # Če je match-control ekstremno enostranski, je "direction" pogosto bolj zanesljiv kot 10-min okno.
    control_mode = ""
    control_reason = ""
    try:
        mc_h_now = float(mc_h_adj or 0.0)
        mc_a_now = float(mc_a_adj or 0.0)
    except Exception:
        mc_h_now, mc_a_now = 0.0, 0.0

    lam_h_now = float(lam_h or 0.0)
    lam_a_now = float(lam_a or 0.0)
    away_control = (
        mc_a_now > 0.85
        and lam_a_now > max(1e-6, lam_h_now) * 2.0
        and float(momentum or 0.0) < -0.08
    )
    home_control = (
        mc_h_now > 0.85
        and lam_h_now > max(1e-6, lam_a_now) * 2.0
        and float(momentum or 0.0) > 0.08
    )

    if away_control:
        ng_smart_conf = max(ng_smart_conf, 0.70)
        control_mode = "AWAY_DOMINATION"
        control_reason = f"MC_A {mc_a_now:.2f} + λ_A/λ_H {safe_div(lam_a_now, lam_h_now, 0.0):.2f} + momentum {float(momentum or 0.0):.2f}"
    elif home_control:
        ng_smart_conf = max(ng_smart_conf, 0.70)
        control_mode = "HOME_DOMINATION"
        control_reason = f"MC_H {mc_h_now:.2f} + λ_H/λ_A {safe_div(lam_h_now, lam_a_now, 0.0):.2f} + momentum {float(momentum or 0.0):.2f}"

    # Update smart dict za izpis (ne spreminja next_goal_window_state, ki uporablja core conf).
    if isinstance(next_goal_prediction_smart, dict) and ng_smart_conf != ng_smart_conf_core:
        next_goal_prediction_smart["confidence"] = ng_smart_conf

    # === GOAL MODE DETECTOR (EVENT vs DIRECTION) ===
    # Visok P(gol), nizek "directional" smart conf → dogodek (gol) bolj zanesljiv kot kdo strelja.
    # PRO: namesto slepega side next-goal → tržni OVER / GOAL YES (advisory, ne spreminja core bet_decision).
    next_goal_conf = ng_smart_conf
    if float(p_goal or 0) > 0.65 and next_goal_conf < 0.55:
        bet_mode = "GOAL_EVENT"
        goal_event_market_advisory = "OVER / GOAL YES (Next goal YES)"
        goal_event_reason = (
            f"HIGH P(goal) {float(p_goal) * 100:.1f}% + LOW direction conf {next_goal_conf * 100:.1f}%"
        )
        bet_mode_reason = goal_event_reason
    else:
        bet_mode = "DIRECTION"
        goal_event_market_advisory = ""
        goal_event_reason = ""
        bet_mode_reason = ""

    # === FREEZE / LOW EVENT (late priority override) ===
    # 80+ draw lock pogosto pomeni "no event zone" tudi ob navideznem pritisku.
    odds_draw_f = float(odds_draw or 0.0)
    lam_total_f = float(lam_total or 0.0)
    if minute >= 78 and 0.0 < odds_draw_f < 1.45:
        bet_mode = "FREEZE"
        goal_event_market_advisory = ""
        goal_event_reason = ""
        bet_mode_reason = f"FREEZE: {minute}' + DRAW LOCK (odds {odds_draw_f:.2f} < 1.45)"
    elif minute >= 75 and lam_total_f < 0.9 and bet_mode == "DIRECTION":
        bet_mode = "LOW_EVENT"
        bet_mode_reason = f"LOW EVENT: {minute}' + λ_total {lam_total_f:.3f} < 0.90"

    ng_window_level, ng_window_side, ng_window_reason = next_goal_window_state(
        p_goal_10=p_goal_10,
        ng_smart_conf=ng_smart_conf_core,
        p_home_next=p_home_next,
        p_away_next=p_away_next,
        momentum=momentum,
        minute=minute,
    )

    if ng_window_level in ("HOLD", "WATCH") and next_goal_bet != "NO BET":
        next_goal_bet = "NO BET"
        next_goal_reason = f"{ng_window_level} - WAIT"
    elif ng_window_level == "TRIGGER" and next_goal_bet == "NO BET" and p_goal_10 >= 0.40 and ng_smart_conf >= 0.66:
        next_goal_bet = ng_window_side
        next_goal_reason = "10M TRIGGER OVERRIDE"

    ng_gap = abs(p_home_next - p_away_next)
    if next_goal_bet != "NO BET":
        if ng_gap < 0.12:
            next_goal_bet = "NO BET"
            next_goal_reason = "ANTI-TRAP: NEXT GOAL GAP < 12%"
        elif (not wave_active) and abs(danger_h - danger_a) < 5 and abs(danger_dominance) < 0.12:
            next_goal_bet = "NO BET"
            next_goal_reason = "ANTI-TRAP: NO WAVE + LOW DOMINANCE"

    tempo_danger_h = float(danger_h or 0.0) / max(1, minute)
    tempo_danger_a = float(danger_a or 0.0) / max(1, minute)
    split_shift_away = anti_split_shift_away(
        minute=minute,
        score_diff=score_diff,
        tempo_danger_h=tempo_danger_h,
        tempo_danger_a=tempo_danger_a,
        tempo_shots_h=tempo_shots_h,
        tempo_shots_a=tempo_shots_a,
        timeline_home=(timeline or {}).get("trend_home", 1.0),
        timeline_away=(timeline or {}).get("trend_away", 1.0),
        danger_h=danger_h,
        danger_a=danger_a,
    )
    if split_shift_away and normalize_outcome_label(next_goal_bet) == "HOME":
        next_goal_bet = "NO BET"
        next_goal_reason = "ANTI-SPLIT: AWAY PRESSURE SHIFT"
        signals_agreement = max(0, signals_agreement - 2)

    hidden_goal_risk, pressure_goal_note = pressure_goal_detector(
        overpressure_away=overpressure_away,
        p_goal_10=p_goal_10,
        ng_window_level=ng_window_level,
        wave_active=wave_active,
    )
    goal_timing = goal_timing_detector(
        p_goal_5=p_goal_5,
        p_goal_10=p_goal_10,
        tempo_danger=tempo_danger,
        tempo_shots=tempo_shots,
        wave_active=wave_active,
        overpressure_home=overpressure_home,
        overpressure_away=overpressure_away,
        timeline_goal_factor=(timeline or {}).get("trend_factor_goal", 1.0),
        minute=minute,
    )
    if hidden_goal_risk and next_goal_bet != "NO BET":
        next_goal_bet = "NO BET"
        next_goal_reason = pressure_goal_note
    elif counter_kill_mode and normalize_outcome_label(next_goal_bet) == "AWAY":
        next_goal_reason = "COUNTER KILL MODE AWAY"
    elif dual_threat_mode and normalize_outcome_label(next_goal_bet) in ("HOME", "AWAY"):
        next_goal_bet = "NO BET"
        next_goal_reason = "DUAL THREAT LOCK"

    # === CONFIDENCE FILTER (anti-random; po ng_window / trap filtrih) ===
    _ph2 = float(p_home_next or 0.0)
    _pa2 = float(p_away_next or 0.0)
    if max(_ph2, _pa2) < 0.55 and next_goal_bet != "NO BET":
        next_goal_bet = "NO BET"
        next_goal_reason = "CONF FILTER: max(p_next) < 55%"

    # === COUNTER RISK — blokira stavo (ne spreminja prediction) ===
    counter_risk = (
        float(danger_h or 0.0) > float(danger_a or 0.0) * 0.9
        and float(sot_h or 0.0) < float(sot_a or 0.0)
        and float(momentum or 0.0) < 0.05
    )
    if counter_risk and next_goal_bet != "NO BET":
        next_goal_bet = "NO BET"
        next_goal_reason = "COUNTER RISK"

    # === KILL GAME (75+ / brez attack wave / ploska lambda) ===
    kill_game = (
        minute >= 75
        and (not wave_active)
        and abs(float(lam_h or 0.0) - float(lam_a or 0.0)) < 0.15
    )
    if kill_game:
        next_goal_prediction = "NO GOAL"
        next_goal_bet = "NO BET"
        next_goal_reason = "KILL GAME: 75+ / no wave / flat lambda"

    counter_goal_raw = next_goal_bet if normalize_outcome_label(next_goal_bet) in ("HOME", "AWAY") else next_goal_prediction
    dominant_side, counter_goal = cfos_balance_counter(
        danger_h,
        danger_a,
        shots_h,
        shots_a,
        counter_goal_raw
    )

    if dominant_side is None:
        if momentum < -0.30:
            dominant_side = "AWAY"
        elif momentum > 0.30:
            dominant_side = "HOME"

    # live_favor: signal za game_type / interpretacijo — NE sme prepisati matematičnega prediction
    if live_favor in ("HOME", "AWAY") and dominant_side is None:
        dominant_side = live_favor

    counter_blocked = False

    # Dominance vs model: blokira STAVO, ne spreminja prediction (prediction ostane iz FINAL SAFETY)
    if next_goal_prediction in ("HOME", "AWAY") and dominant_side in ("HOME", "AWAY"):
        if dominant_side == "HOME" and next_goal_prediction == "AWAY":
            counter_blocked = True
            if next_goal_bet != "NO BET":
                next_goal_bet = "NO BET"
                next_goal_reason = "DOM vs MODEL: dom HOME / model AWAY → NO BET"
        elif dominant_side == "AWAY" and next_goal_prediction == "HOME":
            counter_blocked = True
            if next_goal_bet != "NO BET":
                next_goal_bet = "NO BET"
                next_goal_reason = "DOM vs MODEL: dom AWAY / model HOME → NO BET"

    if dominant_side is not None and normalize_outcome_label(counter_goal_raw) != normalize_outcome_label(counter_goal):
        counter_blocked = True

    # Ponovna konsistenca: prediction mora ujemati p_home_next / p_away_next (po vseh bet filtrih)
    _phf = float(p_home_next or 0.0)
    _paf = float(p_away_next or 0.0)
    if kill_game:
        next_goal_prediction = "NO GOAL"
    elif _phf > _paf:
        next_goal_prediction = "HOME"
    elif _paf > _phf:
        next_goal_prediction = "AWAY"
    else:
        next_goal_prediction = "NO GOAL"

    # GOAL_EVENT ne sme ostati aktiven ob kill_game (ekspliciten "no next goal" režim).
    if kill_game:
        bet_mode = "DIRECTION"
        goal_event_market_advisory = ""
        goal_event_reason = ""
        bet_mode_reason = ""

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
        "next_goal_prediction": next_goal_prediction,
        "next_goal_bet": next_goal_bet, "next_goal_reason": next_goal_reason,
        "dominant_side": dominant_side, "counter_goal": counter_goal, "counter_blocked": counter_blocked,
        "counter_risk": counter_risk,
        "kill_game": kill_game,
        "bet_mode": bet_mode,
        "bet_mode_reason": bet_mode_reason,
        "control_mode": control_mode,
        "control_reason": control_reason,
        "goal_event_market_advisory": goal_event_market_advisory,
        "goal_event_reason": goal_event_reason,
        "next_goal_conf_smart": next_goal_conf,
        "next_goal_conf_smart_core": ng_smart_conf_core,
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
        "game_state": detect_game_state(score_diff, xg_h, xg_a, momentum, sot_h, sot_a, p_goal, lam_h, lam_a),
        "live_favor": live_favor,
        "top_scores": top_scores, "hist_bias": hist_bias, "exact_hist": exact_hist,
        "hist_home": hist_home, "hist_draw": hist_draw, "hist_away": hist_away,
        "history_pred": history_pred,
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
        "use_reason": use_reason,
        "lam_ratio": lam_ratio,
        "high_tempo": high_tempo,
        "high_lambda": high_lambda,
        "no_wave": no_wave,
        "overpressure_home": overpressure_home,
        "overpressure_away": overpressure_away,
        "leading_side": leading_side,
        "dominance": danger_dominance,
        "next_goal_prediction_smart": next_goal_prediction_smart,
        "signals_agreement": signals_agreement,
        "ng_window_level": ng_window_level,
        "ng_window_side": ng_window_side,
        "ng_window_reason": ng_window_reason,
        "split_shift_away": split_shift_away,
        "hidden_goal_risk": hidden_goal_risk,
        "pressure_goal_note": pressure_goal_note,
        "goal_timing": goal_timing,
        "counter_kill_mode": counter_kill_mode,
        "fake_home_pressure": fake_home_pressure,
        "fake_home_pressure_finish": fake_home_pressure_finish,
        "finishing_dominance": finishing_dominance,
        "game_decided_hard": game_decided_hard,
        "dual_threat_mode": dual_threat_mode,
        "entry_l5_shots_h": entry_l5_shots_h,
        "entry_l5_sot_h": entry_l5_sot_h,
        "entry_l5_danger_h": entry_l5_danger_h,
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



# ============================================================
# LIVE TAG SYSTEM (1 LIVE per window)
# ============================================================

CMD_WIDTH = 95
_live_used = False

def live_reset():
    global _live_used
    _live_used = False

def live_print(label, value, live=False):
    global _live_used
    left = f"{label:<18} {value}"
    pad = max(1, CMD_WIDTH - len(left))
    if live and not _live_used:
        print(left + "LIVE".rjust(pad))
        _live_used = True
    else:
        print(left)

def _fmt_live_num(value, digits=3):
    try:
        return f"{float(value):.{digits}f}"
    except:
        return str(value)

def _fmt_live_pct(value):
    try:
        return f"{float(value):.2%}"
    except:
        return str(value)

def _dominance_text(r):
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

    minute = int(float(r.get("minute", 0) or 0))
    score_diff = int(r.get("score_diff", 0) or 0)
    leading = str(r.get("leading_side", "DRAW") or "DRAW").upper()

    fake_home = bool(r.get("fake_home_pressure", False) or r.get("fake_home_pressure_finish", False))
    finishing_dom = bool(r.get("finishing_dominance", False))
    game_decided = bool(r.get("game_decided_hard", False))

    mc_h = float(r.get("mc_h_adj", r.get("mc_h_raw", 0)) or 0.0)
    mc_a = float(r.get("mc_a_adj", r.get("mc_a_raw", 0)) or 0.0)

    # Pozno + odločena tekma + lažen doma pritisk: "kontrola" ni prava beseda.
    if minute >= 90 and score_diff <= -2 and fake_home and h > a * 1.10:
        return "DOMA PRITISK (BREZ UČINKA)", YELLOW

    # AWAY vodi + finishing dominance: teritorij lahko izgleda "doma", realna kontrola je AWAY.
    if (leading == "AWAY" or score_diff < 0) and finishing_dom and h > a * 1.05:
        return "DOMA TERITORIALNI PRITISK", YELLOW

    if h > a * 1.15:
        # Če AWAY jasno vodi in ima močnejši MC, ne kliči tega "DOMA KONTROLA".
        if (leading == "AWAY" or score_diff < 0) and mc_a >= mc_h + 0.12:
            return "DOMA PRITISK (GOST KONTROLA)", YELLOW
        return "DOMA KONTROLA", GREEN
    elif a > h * 1.15:
        return "GOST KONTROLA", GREEN
    return "URAVNOTEŽENO", YELLOW

def _match_direction_text(r):
    h = (
        r.get("momentum", 0) * 5 +
        r.get("pressure_h", 0) -
        r.get("pressure_a", 0) +
        r.get("danger_h", 0) * 0.15 -
        r.get("danger_a", 0) * 0.15
    )

    minute = int(float(r.get("minute", 0) or 0))
    score_diff = int(r.get("score_diff", 0) or 0)
    leading = str(r.get("leading_side", "DRAW") or "DRAW").upper()

    fake_home = bool(r.get("fake_home_pressure", False) or r.get("fake_home_pressure_finish", False))
    finishing_dom = bool(r.get("finishing_dominance", False))
    game_decided = bool(r.get("game_decided_hard", False))

    mc_h = float(r.get("mc_h_adj", r.get("mc_h_raw", 0)) or 0.0)
    mc_a = float(r.get("mc_a_adj", r.get("mc_a_raw", 0)) or 0.0)

    if minute >= 90 and score_diff <= -2 and fake_home and game_decided:
        return "GOST KONTROLA TEKME (GAME DECIDED)", GREEN

    if (leading == "AWAY" or score_diff < 0) and finishing_dom and mc_a >= mc_h + 0.10:
        return "GOST KONTROLA TEKME (FINISHING)", GREEN

    if h > 1.5:
        return "→→→ DOMA PRITISK", GREEN
    elif h < -1.5:
        return "←←← GOST PRITISK", GREEN
    return "↔ URAVNOTEŽENO", YELLOW

def print_live_lge(r):
    live_reset()
    print(f"\n{MAGENTA}--------------- LGE ----------------{RESET}\n")
    live_print("STATE", lge_state_value(r))
    wave_side = side_name_from_diff(
        (float(r.get('pressure_h', 0) or 0) - float(r.get('pressure_a', 0) or 0)) * 0.8 +
        (float(r.get('danger_h', 0) or 0) - float(r.get('danger_a', 0) or 0)) * 0.05 +
        (float(r.get('momentum', 0) or 0)) * 10.0,
        "HOME", "AWAY", "NO", eps=0.08
    )
    if not bool(r.get('wave', {}).get('active', False)) and str(r.get('game_type', '')) != 'ATTACK_WAVE':
        wave_side = "NO"
    live_print("ATTACK_WAVE", wave_side)
    live_print("TEMPO shots", high_side_label(r.get('shots_h', 0), r.get('shots_a', 0), threshold=0.5), True)
    live_print("TEMPO danger", high_side_label(r.get('danger_h', 0), r.get('danger_a', 0), threshold=1.0))
    live_print("FAVOR", favorite_side(r))

def print_live_match_memory(r):
    live_reset()
    print(f"\n{MAGENTA}--------------- MATCH MEMORY ----------------{RESET}\n")
    tg = float(r.get("timeline", {}).get("trend_factor_goal", 1.0) or 1.0)
    live_print("Timeline snapshots", r.get("timeline", {}).get("n", 0))
    live_print("Timeline goal factor", f"{tg:.3f}", True)
    live_print("Timeline HOME factor", f"{float(r.get('timeline', {}).get('trend_home', 0.0) or 0.0):.3f}")
    live_print("Timeline AWAY factor", f"{float(r.get('timeline', {}).get('trend_away', 0.0) or 0.0):.3f}")
    live_print("True momentum", r.get("timeline", {}).get("true_momentum_text", "N/A"))
    live_print("Attack wave", "YES" if r.get("wave", {}).get("active", False) else "NO")
    live_print("LGE", r.get("lge", ""))

def print_live_tempo_rate(r):
    live_reset()
    print(f"\n{MAGENTA}--------------- TEMPO / RATE ----------------{RESET}\n")
    live_print("Tempo shots", _fmt_live_num(r.get("tempo_shots", 0), 3), True)
    live_print("Tempo attacks", _fmt_live_num(r.get("tempo_att", 0), 3))
    live_print("Tempo danger", _fmt_live_num(r.get("tempo_danger", 0), 3))
    live_print("xG rate total", _fmt_live_num(r.get("xg_rate_total", 0), 4))
    live_print("xG rate HOME", _fmt_live_num(r.get("xg_rate_h", 0), 4))
    live_print("xG rate AWAY", _fmt_live_num(r.get("xg_rate_a", 0), 4))
    live_print("Minutes left est.", r.get("minutes_left_real", 0))

def print_live_extended_stats(r):
    live_reset()
    print(f"\n{MAGENTA}--------------- EXTENDED STATS ----------------{RESET}\n")
    live_print("Attacks", f"{round(r.get('attacks_h', 0), 2)} {round(r.get('attacks_a', 0), 2)}", True)
    live_print("Blocked shots", f"{round(r.get('blocked_h', 0), 2)} {round(r.get('blocked_a', 0), 2)}")
    live_print("Big ch. missed", f"{round(r.get('bcm_h', 0), 2)} {round(r.get('bcm_a', 0), 2)}")
    live_print("Corners", f"{round(r.get('corners_h', 0), 2)} {round(r.get('corners_a', 0), 2)}")
    live_print("GK saves", f"{round(r.get('gk_saves_h', 0), 2)} {round(r.get('gk_saves_a', 0), 2)}")
    live_print("Passes", f"{round(r.get('passes_h', 0), 2)} {round(r.get('passes_a', 0), 2)}")
    live_print("Acc. passes", f"{round(r.get('acc_pass_h', 0), 2)} {round(r.get('acc_pass_a', 0), 2)}")
    live_print("Danger->shot", f"{round(r.get('d2s_h', 0), 3)} {round(r.get('d2s_a', 0), 3)}")
    live_print("Shot quality", f"{round(r.get('shot_q_h', 0), 3)} {round(r.get('shot_q_a', 0), 3)}")
    live_print("SOT ratio", f"{round(r.get('sot_r_h', 0), 3)} {round(r.get('sot_r_a', 0), 3)}")
    live_print("Big chance ratio", f"{round(r.get('bc_r_h', 0), 3)} {round(r.get('bc_r_a', 0), 3)}")
    live_print("Game type", r.get("game_type", ""))

def print_live_momentum_engine(r):
    live_reset()
    print(f"\n{MAGENTA}--------------- MOMENTUM ENGINE ----------------{RESET}\n")
    live_print("Attack index", f"{round(r.get('attack_h', 0), 2)} {round(r.get('attack_a', 0), 2)}")
    live_print("Danger index", f"{round(r.get('danger_idx_h', 0), 2)} {round(r.get('danger_idx_a', 0), 2)}")
    live_print("Pressure", f"{round(r.get('pressure_h', 0), 2)} {round(r.get('pressure_a', 0), 2)}")
    live_print("Momentum", _fmt_live_num(r.get("momentum", 0), 3), True)

def print_live_lambda_engine(r):
    live_reset()
    print(f"\n{MAGENTA}--------------- LAMBDA ENGINE ----------------{RESET}\n")
    live_print("Lambda home (RAW)", _fmt_live_num(r.get("lam_h_raw", 0), 3), True)
    live_print("Lambda away (RAW)", _fmt_live_num(r.get("lam_a_raw", 0), 3))
    live_print("Lambda shared (RAW)", _fmt_live_num(r.get("lam_c_raw", 0), 3))
    live_print("Lambda total (RAW)", _fmt_live_num(r.get("lam_total_raw", 0), 3))
    live_print("P(goal) RAW", f"{pct(r.get('p_goal_raw', 0))} %")
    live_print("Lambda home (CAL)", _fmt_live_num(r.get("lam_h", 0), 3))
    live_print("Lambda away (CAL)", _fmt_live_num(r.get("lam_a", 0), 3))
    live_print("Lambda shared (CAL)", _fmt_live_num(r.get("lam_c", 0), 3))
    live_print("Lambda total (CAL)", _fmt_live_num(r.get("lam_total", 0), 3))

def print_live_overpressure_engine(r):
    live_reset()
    print(f"\n{MAGENTA}--------------- OVERPRESSURE ENGINE ----------------{RESET}\n")
    live_print("Lam ratio", _fmt_live_num(r.get("lam_ratio", 0), 2), True)
    live_print("High tempo", str(r.get("high_tempo", False)))
    live_print("High lambda", str(r.get("high_lambda", False)))
    live_print("No attack wave", str(r.get("no_wave", True)))
    live_print("Overpressure HOME", str(r.get("overpressure_home", False)))
    live_print("Overpressure AWAY", str(r.get("overpressure_away", False)))
    live_print("Leading side", r.get("leading_side", "DRAW"))
    live_print("Lambda HOME", _fmt_live_num(r.get("lam_h", 0), 3))
    live_print("Lambda AWAY", _fmt_live_num(r.get("lam_a", 0), 3))
    live_print("Lambda DRAW", _fmt_live_num(r.get("lam_c", 0), 3))

def print_live_goal_probability(r):
    live_reset()
    print(f"\n{MAGENTA}--------------- GOAL PROBABILITY (CAL) ----------------{RESET}\n")
    live_print("Any goal", highlight_goal_prob(r.get("p_goal", 0)), True)
    live_print("Home next goal", f"{pct(r.get('p_home_next', 0))} %")
    live_print("Away next goal", f"{pct(r.get('p_away_next', 0))} %")
    live_print("No goal", f"{pct(r.get('p_no_goal', 0))} %")
    live_print("Goal next 5 min", highlight_goal_prob(r.get("p_goal_5", 0)))
    live_print("Goal next 10 min", highlight_goal_prob(r.get("p_goal_10", 0)))

def print_live_match_direction(r):
    txt, col = _match_direction_text(r)
    live_reset()
    print(f"\n{MAGENTA}--------------- MATCH DIRECTION ----------------{RESET}\n")
    live_print("", btxt(txt, col, True), True)


def print_next_goal_bet(r):
    print()
    print("--------------- NEXT GOAL ----------------")
    print(f"Prediction       {r.get('next_goal_prediction', 'AWAY')}")
    print(f"Bet              {r.get('next_goal_bet', 'NO BET')}")
    print(f"Reason           {r.get('next_goal_reason', 'LOW EDGE')}")
    ng_level = str(r.get("ng_window_level", "HOLD") or "HOLD")
    ng_side = str(r.get("ng_window_side", "HOME") or "HOME")
    ng_color = color_window_level(ng_level)
    print(f"10M Okno         {btxt(ng_level, ng_color, True)} ({ng_side})")
    print(f"10M Logika       {r.get('ng_window_reason', 'N/A')}")
    gt = r.get("goal_timing") or {}
    print(f"Timing okno      {gt.get('window', 'ZAPRTO')}")
    print(f"Timing vstop     {gt.get('entry', 'WAIT')} | ETA {gt.get('eta', '>10 min')}")
    if bool(r.get("hidden_goal_risk", False)):
        print(f"Pritisk-Gol      {r.get('pressure_goal_note', 'SKRITO TVEGANJE GOLA')}")
    if bool(r.get("counter_kill_mode", False)):
        print("Counter-Kill     AKTIVNO (CHAOS + GOST UČINKOVITOST)")
    if bool(r.get("fake_home_pressure", False)):
        print("Fake pressure    AKTIVNO (POZEN DOMA TRAP)")
    if bool(r.get("dual_threat_mode", False)):
        print("Dual threat      AKTIVNO (OPEN ENDGAME LOCK)")
    if ng_level == "TRIGGER":
        print(btxt("!!! 10M NEXT GOAL TRIGGER ACTIVE !!!", GREEN, True))
    print("------------------------------------------------")


def print_counter_control(r):
    print("\n--------------- COUNTER CONTROL ----------------\n")

    dominant_side = r.get('dominant_side')
    counter_goal = r.get('counter_goal', 'NONE')
    counter_blocked = bool(r.get('counter_blocked', False))

    if dominant_side is None:
        print("Dominant side      NONE")
    else:
        print(f"Dominant side      {dominant_side}")

    print(f"Counter goal       {counter_goal}")
    print(f"Counter blocked    {'YES' if counter_blocked else 'NO'}")

def print_live_dominance(r):
    txt, col = _dominance_text(r)
    live_reset()
    print(f"\n{MAGENTA}--------------- DOMINANCE ----------------{RESET}\n")
    live_print("", btxt(txt, col, True), True)



def print_dominance(r):
    txt, col = _dominance_text(r)
    print("")
    print("--------------- DOMINANCE ----------------")
    print(btxt(txt, col, True))


def print_match_direction(r):
    txt, col = _match_direction_text(r)
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
        razlog = "HISTORY BLOCK"

    else:
        mc_away = float(r.get("mc_away", r.get("mc_a_adj", r.get("mc_a_raw", 0))) or 0.0)
        mc_home = float(r.get("mc_home", r.get("mc_h_adj", r.get("mc_h_raw", 0))) or 0.0)
        lambda_away = float(r.get("lambda_away", r.get("lam_a", 0)) or 0.0)
        lambda_home = float(r.get("lambda_home", r.get("lam_h", 0)) or 0.0)
        edge_away_pct = float(r.get("edge_away", r.get("edge_a", 0)) or 0.0) * 100.0
        edge_home_pct = float(r.get("edge_home", r.get("edge_h", 0)) or 0.0) * 100.0

        # =====================================================
        # AUTO BET DECISION (FIXED FLOW)
        # 1) CONTROL BET
        # 2) LATE GOAL
        # 3) NEXT GOAL
        # 4) DEFAULT
        # =====================================================
        if (
            minute >= 45
            and mc_away >= 0.80
            and edge_away_pct >= 8.0
        ):
            stava = "AWAY"
            razlog = "CONTROL VALUE AWAY"

        elif (
            minute >= 45
            and mc_home >= 0.80
            and edge_home_pct >= 8.0
        ):
            stava = "HOME"
            razlog = "CONTROL VALUE HOME"

        elif (
            minute >= 70
            and r["p_goal"] >= 0.65
            and abs(r["score_diff"]) <= 1
        ):
            if r["p_home_next"] > r["p_away_next"]:
                stava = "NEXT GOAL HOME"
                razlog = "LATE PRESSURE HOME"
            else:
                stava = "NEXT GOAL AWAY"
                razlog = "LATE PRESSURE AWAY"

        elif r["p_home_next"] >= 0.48:
            stava = "NEXT GOAL HOME"
            razlog = "NEXT GOAL SIGNAL"

        elif r["p_away_next"] >= 0.48:
            stava = "NEXT GOAL AWAY"
            razlog = "NEXT GOAL SIGNAL"

        else:
            stava = "NO BET"
            razlog = "NO EDGE"

        # =====================================================
        # FINAL VALUE BET (NAJVARNEJSI FIX)
        # =====================================================
        if stava == "NO BET":
            if mc_away >= 0.80 and edge_away_pct >= 8.0:
                stava = "AWAY"
                razlog = "FINAL VALUE AWAY"
            elif mc_home >= 0.80 and edge_home_pct >= 8.0:
                stava = "HOME"
                razlog = "FINAL VALUE HOME"

    # =====================================================
    # NEXT GOAL influence (NE PREPISUJE STAVE)
    # =====================================================
    # Ta del sme vplivati na napoved rezultata/strani, ne pa
    # prepisati že izračunanega AUTO BET flow-a.
    if not history_block:
        if r["p_away_next"] >= 0.48 and r["momentum"] < -0.08:
            napoved = "GOST"
        elif r["p_home_next"] >= 0.48 and r["momentum"] > 0.08:
            napoved = "DOMAČI"
        elif r["p_goal"] >= 0.60 and abs(r["momentum"]) > 0.12:
            napoved = "DOMAČI" if r["momentum"] > 0 else "GOST"
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
    # Stava/razlog ostaneta iz enotnega AUTO BET flowa zgoraj.

    print("Napoved rezultata".ljust(28), btxt(rezultat, CYAN, True))
    print("Kaj bi stavil".ljust(28), btxt(stava, GREEN if stava != "NO BET" else YELLOW, True))
    print("Zakaj".ljust(28), razlog)
    print(f"\n{MAGENTA}Na kaj moraš biti najbolj pozoren:{RESET}")
    print(f"{btxt('- Danger attacks', YELLOW, True)}")
    print(f"{btxt('- Tempo danger / tempo shots', ORANGE, True)}")
    print(f"{btxt('- Attack wave / timeline trend', RED, True)}")
    print(f"{btxt('- Any goal / next goal signal', GREEN, True)}")
    print(f"{btxt('- EDGE proti marketu', BLUE, True)}")



# ============================================================
# CFOS SLO INTERPRETACIJA (GLOBAL)
# ============================================================
def cfos_slo_interpretacija(
    lge_state,
    attack_wave,
    tempo_shots_side,
    tempo_danger_side,
    lge_favor,
    momentum,
    lam_home,
    lam_away,
    lam_total,
    p_goal,
    next_goal_pred,
    bet
):

    print("\n=============== CFOS RAZLAGA =================\n")

    print("LGE:")
    print(f"Stanje LGE: {lge_state}")
    print(f"Attack wave: {attack_wave}")

    if tempo_shots_side == "AWAY" and tempo_danger_side == "HOME":
        print("GOST ustvarja več pritiska in več strelov.")
        print("DOMA ima bolj nevarne napade in kvalitetnejše priložnosti.")
        print("To je tipičen scenarij protinapada DOMA.")
    elif tempo_shots_side == "HOME" and tempo_danger_side == "AWAY":
        print("DOMA ustvarja več pritiska in več strelov.")
        print("GOST ima bolj nevarne napade in kvalitetnejše priložnosti.")
        print("To je tipičen scenarij protinapada GOST.")
    elif lge_favor == "HOME":
        print("Model daje prednost DOMA za naslednji gol.")
    elif lge_favor == "AWAY":
        print("Model daje prednost GOST za naslednji gol.")
    else:
        print("Situacija je uravnotežena brez jasnega favorita.")

    print()
    print("MOMENTUM:")

    if momentum > 0.2:
        print("Trenutni pritisk je na strani DOMA.")
        print("DOMA pogosteje napada in drži igro v napadu.")
    elif momentum < -0.2:
        print("Trenutni pritisk je na strani GOST.")
        print("GOST pogosteje napada in ustvarja več priložnosti.")
    else:
        print("Ni izrazitega pritiska ene ekipe.")
        print("Tekma je uravnotežena.")

    print()
    print("LAMBDA:")

    if lam_total > 1.5:
        print("Verjetnost gola je visoka.")
    elif lam_total > 1.0:
        print("Verjetnost gola je zmerna.")
    else:
        print("Verjetnost gola je nizka.")

    if lam_home > lam_away:
        print("Model vidi večjo možnost gola za DOMA.")
    elif lam_away > lam_home:
        print("Model vidi večjo možnost gola za GOST.")
    else:
        print("Model vidi zelo podobno možnost gola za obe ekipi.")

    print()
    print("VERJETNOST GOLA:")

    if p_goal > 0.75:
        print("Gol je zelo verjeten v naslednjih minutah.")
    elif p_goal > 0.55:
        print("Gol je verjeten v naslednjih minutah.")
    else:
        print("Gol ni zelo verjeten.")

    print()
    print("NASLEDNJI GOL:")

    if next_goal_pred == "HOME":
        print("Model preferira DOMA kot naslednjega strelca.")
    elif next_goal_pred == "AWAY":
        print("Model preferira GOST kot naslednjega strelca.")
    else:
        print("Ni jasnega favorita za naslednji gol.")

    if bet == "NO BET":
        print("Prednost ni dovolj velika za varno stavo.")
    else:
        print(f"Situacija primerna za stavo: {bet}")

    print("\n============================================\n")

def izpis_rezultata(r):
    print(f"\n{CYAN}{BOLD}================ CFOS-XG PRO 75 TITAN [POLNA VERZIJA] ================={RESET}\n")

    # BET DECISION enkrat (ujet print); zgornji banner = končna odločitev, ne SMART/NEXT GOAL.
    _, _bd_lines = _capture_print_output(bet_decision, r)
    r["_captured_bet_decision_lines"] = _bd_lines

    print(auto_signal_final(r))
    print()
    print_decision_levels_snapshot(r)
    print()

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

    # ============================================================
    # [IGRIŠČE] — mapping: EXTRA STATS / DOMINANCE / MATCH MEMORY / LGE / MOMENTUM
    # ============================================================

    print(f"\n{CYAN}{BOLD}================ EXTRA STATS ================={RESET}{cmd_tag('IGRIŠČE')}\n")
    print_stat("PASSES", r.get("passes_h"), r.get("passes_a"))
    print_stat("DUELS", r.get("duels_h"), r.get("duels_a"))
    print_stat("FOULS", r.get("fouls_h"), r.get("fouls_a"))
    print_stat("OFFSIDES", r.get("offsides_h"), r.get("offsides_a"))
    print_stat("KEY PASSES", r.get("keypasses_h"), r.get("keypasses_a"))
    print_stat("CROSSES", r.get("crosses_h"), r.get("crosses_a"))
    print_stat("LONG BALLS", r.get("long_balls_h"), r.get("long_balls_a"))
    print_stat("TACKLES", r.get("tackles_h"), r.get("tackles_a"))
    print_stat("INTERCEPT", r.get("inter_h"), r.get("inter_a"))
    print_stat("CLEARANCES", r.get("clear_h"), r.get("clear_a"))
    print_stat("AERIALS", r.get("aerials_h"), r.get("aerials_a"))
    print_stat("DRIBBLES", r.get("dribbles_h"), r.get("dribbles_a"))
    print_stat("FINAL THIRD", r.get("final_third_h"), r.get("final_third_a"))

    print(f"\n{CYAN}{BOLD}================ DOMINANCE ================={RESET}{cmd_tag('IGRIŠČE')}\n")
    print_live_dominance(r)

    print(f"\n{CYAN}{BOLD}================ MATCH DIRECTION ================={RESET}{cmd_tag('IGRIŠČE')}\n")
    print_live_match_direction(r)

    print(f"\n{CYAN}{BOLD}================ MATCH MEMORY ================={RESET}{cmd_tag('IGRIŠČE')}\n")
    print_live_match_memory(r)

    print(f"\n{CYAN}{BOLD}================ LGE ================={RESET}{cmd_tag('IGRIŠČE')}\n")
    print_live_lge(r)

    print(f"\n{CYAN}{BOLD}================ MOMENTUM ================={RESET}{cmd_tag('IGRIŠČE')}\n")
    print_live_momentum_engine(r)

    print(f"\n{CYAN}{BOLD}================ TEMPO / RATE ================={RESET}{cmd_tag('IGRIŠČE')}\n")
    print_live_tempo_rate(r)

    print(f"\n{CYAN}{BOLD}================ EXTENDED STATS ================={RESET}{cmd_tag('IGRIŠČE')}\n")
    print_live_extended_stats(r)

    print(f"\n{MAGENTA}--------------- FOTMOB EXTRA ----------------{RESET}{cmd_tag('IGRIŠČE')}\n")
    print("Key passes".ljust(28), round(r["keypasses_h"], 2), round(r["keypasses_a"], 2))
    print("Crosses".ljust(28), round(r["crosses_h"], 2), round(r["crosses_a"], 2))
    print("Aerial duels".ljust(28), round(r["aerials_h"], 2), round(r["aerials_a"], 2))
    print("Dribbles".ljust(28), round(r["dribbles_h"], 2), round(r["dribbles_a"], 2))
    print("Final third entries".ljust(28), round(r["final_third_h"], 2), round(r["final_third_a"], 2))
    print("Long balls".ljust(28), round(r["long_balls_h"], 2), round(r["long_balls_a"], 2))
    print("Big ch. created".ljust(28), round(r["bc_created_h"], 2), round(r["bc_created_a"], 2))
    print("Action areas".ljust(28), round(r["action_left"], 2), round(r["action_mid"], 2), round(r["action_right"], 2))

    # ============================================================
    # [MODEL] — mapping: LAMBDA / GOAL PROBABILITY / MONTE CARLO
    # ============================================================

    print(f"\n{CYAN}{BOLD}================ LAMBDA ENGINE ================={RESET}{cmd_tag('MODEL')}\n")
    print_live_lambda_engine(r)

    print(f"\n{CYAN}{BOLD}================ OVERPRESSURE ENGINE ================={RESET}{cmd_tag('SIGNALI')}\n")
    print_live_overpressure_engine(r)

    print(f"\n{CYAN}{BOLD}================ GOAL PROBABILITY ================={RESET}{cmd_tag('MODEL')}\n")
    print_live_goal_probability(r)
    print(f"\n{CYAN}{BOLD}================ NEXT GOAL / COUNTER ================={RESET}{cmd_tag('SIGNALI')}\n")
    print_next_goal_bet(r)
    print_counter_control(r)

    # ============================================================
    # NEXT GOAL SMART PREDICTION
    # ============================================================
    ng_smart = r.get("next_goal_prediction_smart") or {}
    if ng_smart:
        print()
        print(f"{COL_NEXT}--------------- NEXT GOAL SMART ----------------{RESET}{cmd_tag('SIGNALI')}")
        print(f"Prediction".ljust(28), btxt(str(ng_smart.get("prediction", "N/A")), COL_NEXT, True))
        conf_val = float(ng_smart.get("confidence", 0) or 0)
        print(f"Confidence".ljust(28), highlight_conf(conf_val))
        print(f"Score HOME".ljust(28), round(ng_smart.get("score_h", 0), 4))
        print(f"Score AWAY".ljust(28), round(ng_smart.get("score_a", 0), 4))
        print(f"Signals agreement".ljust(28), f"{ng_smart.get('signals_agreement', 0)}/7")
        print(f"Tempo mult".ljust(28), ng_smart.get("tempo_mult", 1.0))
        print(f"Minute mult".ljust(28), ng_smart.get("minute_mult", 1.0))
        print("------------------------------------------------")



    print("META HOME".ljust(28), round(r["mc_h_adj"], 4))
    print("META DRAW".ljust(28), round(r["mc_x_adj"], 4))
    print("META AWAY".ljust(28), round(r["mc_a_adj"], 4))

    print(f"\n{MAGENTA}--------------- MONTE CARLO ----------------{RESET}{cmd_tag('MODEL')}\n")
    print(cl("Monte Carlo sims", r["sim_used"], COL_MC))
    print(cl("Exact score sims", r["exact_sim_used"], COL_MC))
    print(cl("Away win (RAW)", f'{pct(r["mc_a_raw"])} %', COL_MC, True))
    print(cl("Draw (RAW)", f'{pct(r["mc_x_raw"])} %', COL_MC, True))
    print(cl("Home win (RAW)", f'{pct(r["mc_h_raw"])} %', COL_MC, True))
    print(cl("Away win (CAL)", f'{pct(r["mc_a_adj"])} %', COL_MC, True))
    print(cl("Draw (CAL)", f'{pct(r["mc_x_adj"])} %', COL_MC, True))
    print(cl("Home win (CAL)", f'{pct(r["mc_h_adj"])} %', COL_MC, True))

    print(f"\n{MAGENTA}--------------- FINAL SCORE PREDICTION ----------------{RESET}{cmd_tag('MODEL')}\n")
    if r["top_scores"]:
        print("Most likely final".ljust(28), f'{r["top_scores"][0][0]} | {pct(r["top_scores"][0][1])} %')
        for i, (score, p) in enumerate(r["top_scores"][:5], 1):
            print(f"Top {i}".ljust(28), f'{score} | {pct(p)} %')
    else:
        print("Most likely final".ljust(28), "N/A")

    print_interpretacija(r)
    print_cfos_history_engine(r)

    print(f"\n{MAGENTA}--------------- HISTORY SCORE BIAS ----------------{RESET}{cmd_tag('HISTORY')}\n")
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

    print(f"\n{MAGENTA}--------------- EXACT SCORE HISTORY ----------------{RESET}{cmd_tag('HISTORY')}\n")
    if r["exact_hist"] is None:
        print("Exact history".ljust(28), "Ni dovolj podatkov")
    else:
        print("Exact history".ljust(28), f'n={r["exact_hist"]["n"]}')
        print("Exact no goal".ljust(28), f'{pct(r["exact_hist"]["p_no_goal"])} %')
        print("Exact goal".ljust(28), f'{pct(r["exact_hist"]["p_goal"])} %')

    # ============================================================
    # [HISTORY] — mapping: HISTORY BIAS / LEARNING (+ captured pre-calc)
    # ============================================================

    # Izpis, ujet med izračunom (HISTORY/META), damo pod [HISTORY], da ne razmeče vrstnega reda.
    pre = r.get("_captured_preprint") or []
    if pre:
        print(f"\n{MAGENTA}--------------- PRE-CALC (CAPTURED) ----------------{RESET}{cmd_tag('HISTORY')}\n")
        for line in pre:
            print(line)

    print(f"\n{MAGENTA}--------------- LEARNING ----------------{RESET}{cmd_tag('HISTORY')}\n")
    print("Bucket".ljust(28),
          f'{bucket_minute(r["minute"])} | xG:{bucket_xg(r["xg_total"])} | SOT:{bucket_sot(r["sot_total"])} | SH:{bucket_shots(r["shots_total"])} | SD:{bucket_score_diff(r["score_diff"])} | DNG:{bucket_danger(r["danger_total"])}')
    print("Game type".ljust(28), r["game_type"])
    print("Learn factor (GOAL)".ljust(28), round(r["lf_goal"], 3), f'(bucket n: {r["n_goal"]})')

    # ============================================================
    # LEARNING (1X2) — LEARN RATIOS
    # ============================================================
    ph = (r["rh"] - 1.0) * 100.0
    pd = (r["rx"] - 1.0) * 100.0
    pa = (r["ra"] - 1.0) * 100.0

    base = 1 / 3
    h_est = int(r["n_1x2"] * base * r["rh"])
    d_est = int(r["n_1x2"] * base * r["rx"])
    a_est = int(r["n_1x2"] * base * r["ra"])

    h_pct = (h_est / r["n_1x2"] * 100) if r["n_1x2"] else 0
    d_pct = (d_est / r["n_1x2"] * 100) if r["n_1x2"] else 0
    a_pct = (a_est / r["n_1x2"] * 100) if r["n_1x2"] else 0

    print("")
    print(f"Learn ratios (1X2)  (bucket n: {r['n_1x2']})")
    print("")
    print(f"H  {r['rh']:.3f}   ({ph:+.1f}%)   ≈ {h_est}/{r['n_1x2']}   → {h_pct:.1f}%")
    print(f"D  {r['rx']:.3f}   ({pd:+.1f}%)   ≈ {d_est}/{r['n_1x2']}   → {d_pct:.1f}%")
    print(f"A  {r['ra']:.3f}   ({pa:+.1f}%)   ≈ {a_est}/{r['n_1x2']}   → {a_pct:.1f}%")

    print(f"\n{CYAN}{BOLD}================ LEARNING INTERPRETACIJA ================={RESET}{cmd_tag('HISTORY')}\n")
    print_razumevanje(r)

    # ============================================================
    # [MARKET] — mapping: MARKET
    # ============================================================

    print(f"\n{MAGENTA}--------------- 1X2 (MODEL vs MARKET) ----------------{RESET}{cmd_tag('MARKET')}\n")
    print("Outcome       Model %   Market %     EDGE %")
    print("------------------------------------------")
    print(format_edge_line("HOME", r["mc_h_adj"], r["imp_h"], r["edge_h"]))
    print(format_edge_line("DRAW", r["mc_x_adj"], r["imp_x"], r["edge_x"]))
    print(format_edge_line("AWAY", r["mc_a_adj"], r["imp_a"], r["edge_a"]))

    print(f"\n{MAGENTA}--------------- TEAM / MARKET ----------------{RESET}{cmd_tag('MARKET')}\n")
    print("Prematch strength".ljust(28), r["prematch_h"], r["prematch_a"])
    print("ELO".ljust(28), r["elo_h"], r["elo_a"])
    print("Prev odds".ljust(28), r["prev_odds_home"], r["prev_odds_draw"], r["prev_odds_away"])
    print("Market overround".ljust(28), f'{round(r["overround"] * 100, 2)} %')

    print(f"\n{MAGENTA}--------------- CONFIDENCE ----------------{RESET}{cmd_tag('FINAL')}\n")
    print("Confidence".ljust(28), btxt(f'{round(r["confidence"], 1)} /100', color_conf(r["confidence"]), True))
    print("Confidence band".ljust(28), btxt(r["confidence_band"], color_conf(r["confidence"]), True))

    print(f"\n{MAGENTA}--------------- LIVE FILTER ----------------{RESET}{cmd_tag('FINAL')}\n")
    print("Max MC".ljust(28), round(r["max_mc"], 3))
    print("Use filter".ljust(28), "YES" if r["use_filter"] else "NO")
    print("Filter reason".ljust(28), r["use_reason"])
    print(f"\n{MAGENTA}--------------- CFOS FOCUS ENGINE ----------------{RESET}{cmd_tag('FINAL')}\n")

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
    # CFOS SLO INTERPRETACIJA - DODATEK
    # ============================================================
    cfos_slo_interpretacija(
        lge_state=str(r.get("lge_state", lge_state_value(r)) or "PASSIVE"),
        attack_wave=str(r.get("wave", {}).get("active", False) and side_name_from_diff(
            float(r.get("danger_h", 0) or 0) - float(r.get("danger_a", 0) or 0),
            "HOME",
            "AWAY",
            "NO",
            eps=1.0
        ) or "NO"),
        tempo_shots_side=side_name_from_diff(
            float(r.get("shots_h", 0) or 0) - float(r.get("shots_a", 0) or 0),
            "HOME",
            "AWAY",
            "BALANCED",
            eps=0.5
        ),
        tempo_danger_side=side_name_from_diff(
            float(r.get("danger_h", 0) or 0) - float(r.get("danger_a", 0) or 0),
            "HOME",
            "AWAY",
            "BALANCED",
            eps=1.0
        ),
        lge_favor=side_name_from_diff(
            float(r.get("lam_h", 0) or 0) - float(r.get("lam_a", 0) or 0),
            "HOME",
            "AWAY",
            "BALANCED",
            eps=0.03
        ),
        momentum=float(r.get("momentum", 0) or 0),
        lam_home=float(r.get("lam_h", 0) or 0),
        lam_away=float(r.get("lam_a", 0) or 0),
        lam_total=float(r.get("lam_total", 0) or 0),
        p_goal=float(r.get("p_goal", 0) or 0),
        next_goal_pred=(
            "HOME" if float(r.get("p_home_next", 0) or 0) > float(r.get("p_away_next", 0) or 0)
            else "AWAY" if float(r.get("p_away_next", 0) or 0) > float(r.get("p_home_next", 0) or 0)
            else "BALANCED"
        ),
        bet=str(
            r.get("final_auto_bet")
            or r.get("next_goal_bet", "NO BET")
            or "NO BET"
        )
    )

    print_value_detector_block(r)

    _lines = r.get("_captured_bet_decision_lines") or []
    if _lines:
        print(f"\n{CYAN}{BOLD}================ BET DECISION (CAPTURED) ================={RESET}{cmd_tag('FINAL')}\n")
        for ln in _lines:
            print(ln)

# ============================================================
# CFOS ACCURACY COUNTER
# ============================================================


def cfos_accuracy():

    file = "cfos75_accuracy_log.csv"

    if not os.path.exists(file):
        return

    total = 0
    correct_total = 0

    draw_total = 0
    draw_correct = 0

    late_total = 0
    late_correct = 0

    home_total = 0
    home_correct = 0

    away_total = 0
    away_correct = 0
    hit_1x2 = 0

    try:
        with open(file, newline='', encoding="utf-8") as f:
            r = csv.DictReader(f)

            for row in r:

                total += 1

                pred = row.get("prediction")
                real = row.get("final_result")
                correct = row.get("correct")
                minute = int(row.get("minute", 0))

                if correct == "1":
                    correct_total += 1

                # DRAW
                if pred == "REMI":
                    draw_total += 1
                    if correct == "1":
                        draw_correct += 1

                # LATE GAME
                if minute >= 70:
                    late_total += 1
                    if correct == "1":
                        late_correct += 1

                # HOME
                if pred == "DOMAČI":
                    home_total += 1
                    if correct == "1":
                        home_correct += 1

                # AWAY
                if pred == "GOST":
                    away_total += 1
                    if correct == "1":
                        away_correct += 1
                if correct == "1":
                    hit_1x2 += 1
    except Exception as e:
        print("Napaka pri branju accuracy log:", e)
        return

    if total == 0:
        return

    print()
    print("============= CFOS PRO ACCURACY =============")

    print("TOTAL".ljust(18), f"{correct_total}/{total} ({round(correct_total / total * 100, 1)}%)")

    if draw_total > 0:
        print("DRAW".ljust(18), f"{draw_correct}/{draw_total} ({round(draw_correct / draw_total * 100, 1)}%)")

    if late_total > 0:
        print("LATE 70+".ljust(18), f"{late_correct}/{late_total} ({round(late_correct / late_total * 100, 1)}%)")

    if home_total > 0:
        print("HOME".ljust(18), f"{home_correct}/{home_total} ({round(home_correct / home_total * 100, 1)}%)")

    if away_total > 0:
        print("AWAY".ljust(18), f"{away_correct}/{away_total} ({round(away_correct / away_total * 100, 1)}%)")

    print("=============================================")
    print("============= CFOS ACCURACY =============")
    print("Matches         ", total)
    print("1X2 correct     ", hit_1x2, f"({round(hit_1x2 / total * 100, 1)}%)")
    print("========================================")
    print()

def history_accuracy():

    file = MATCH_RESULT_FILE

    if not os.path.exists(file):
        return

    total = 0
    correct = 0

    h_ok = 0
    x_ok = 0
    a_ok = 0

    try:
        with open(file, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for r in reader:

                hist = normalize_outcome_label(r.get("history_pred", ""))
                result = normalize_outcome_label(r.get("result_1x2", ""))

                if hist == "" or result == "":
                    continue

                total += 1

                if hist == result:
                    correct += 1

                    if result == "HOME":
                        h_ok += 1
                    elif result == "DRAW":
                        x_ok += 1
                    elif result == "AWAY":
                        a_ok += 1

        acc = (correct / total * 100) if total > 0 else 0.0

        print("")
        print("============= HISTORY ACCURACY =============")
        print(f"Matches          {total}")
        print(f"Correct          {correct}")
        print(f"Accuracy         {acc:.1f}%")
        print(f"HOME correct     {h_ok}")
        print(f"DRAW correct     {x_ok}")
        print(f"AWAY correct     {a_ok}")
        print("============================================")

    except Exception as e:
        print("Napaka v history_accuracy():", e)


# ============================================================
# BACKTEST + KALIBRACIJA (PRO)
# ============================================================

_CALIB_CACHE = {"loaded": False, "n": 0, "brier_1x2": None, "brier_goal": None, "reliability": 0.75}


def _one_hot_1x2(outcome):
    o = normalize_outcome_label(outcome)
    if o == "HOME":
        return (1.0, 0.0, 0.0)
    if o == "DRAW":
        return (0.0, 1.0, 0.0)
    if o == "AWAY":
        return (0.0, 0.0, 1.0)
    return (0.0, 0.0, 0.0)


def _brier_3(p_h, p_x, p_a, y_h, y_x, y_a):
    return (p_h - y_h) ** 2 + (p_x - y_x) ** 2 + (p_a - y_a) ** 2


def _brier_2(p, y):
    return (float(p) - float(y)) ** 2


def _safe_probs_3(h, x, a):
    h = float(h or 0.0)
    x = float(x or 0.0)
    a = float(a or 0.0)
    if h < 0:
        h = 0.0
    if x < 0:
        x = 0.0
    if a < 0:
        a = 0.0
    s = h + x + a
    if s <= 1e-12:
        return (1 / 3, 1 / 3, 1 / 3)
    return (h / s, x / s, a / s)


def _calibration_bins_binary(pairs, bins=10):
    """
    pairs: list of (p, y) where p in [0,1], y in {0,1}
    returns list of dicts: {lo, hi, n, p_avg, y_rate}
    """
    out = []
    if bins <= 1:
        bins = 10
    for b in range(bins):
        lo = b / bins
        hi = (b + 1) / bins
        chunk = [(p, y) for (p, y) in pairs if (p >= lo and (p < hi if b < bins - 1 else p <= hi))]
        n = len(chunk)
        if n == 0:
            out.append({"lo": lo, "hi": hi, "n": 0, "p_avg": None, "y_rate": None})
            continue
        p_avg = sum(p for p, _ in chunk) / n
        y_rate = sum(y for _, y in chunk) / n
        out.append({"lo": lo, "hi": hi, "n": n, "p_avg": p_avg, "y_rate": y_rate})
    return out


def backtest_learn_log(max_rows=0):
    """
    Backtest na LEARN_FILE, ker vsebuje:
    - mc_h/mc_x/mc_a (verjetnosti iz modela)
    - p_goal_pred + goal_to_end (ali je gol padel po snapshotu)
    - game_type, minute (bucket analiza)
    """
    rows = load_history()
    if not rows:
        return None

    if max_rows and max_rows > 0:
        rows = rows[-max_rows:]

    n = 0
    hit_1x2 = 0
    brier_1x2_sum = 0.0
    brier_goal_sum = 0.0
    goal_pairs = []
    topconf_pairs = []  # (p_max, correct)

    chaos_n = 0
    chaos_hit = 0

    for r in rows:
        try:
            p_h, p_x, p_a = _safe_probs_3(r.get("mc_h"), r.get("mc_x"), r.get("mc_a"))
            y_h, y_x, y_a = _one_hot_1x2(r.get("final_outcome", ""))
            if (y_h + y_x + y_a) <= 0:
                continue

            n += 1
            brier_1x2_sum += _brier_3(p_h, p_x, p_a, y_h, y_x, y_a)

            pred = "HOME" if (p_h >= p_x and p_h >= p_a) else "DRAW" if (p_x >= p_h and p_x >= p_a) else "AWAY"
            actual = "HOME" if y_h == 1 else "DRAW" if y_x == 1 else "AWAY"
            correct = 1 if pred == actual else 0
            hit_1x2 += correct

            p_max = max(p_h, p_x, p_a)
            topconf_pairs.append((p_max, correct))

            gt = str(r.get("game_type", "") or "").strip().upper()
            if gt == "CHAOS":
                chaos_n += 1
                chaos_hit += correct

            # GOAL calibration from snapshot to end
            p_goal = float(r.get("p_goal_pred", 0.0) or 0.0)
            y_goal = 1 if safe_int(r.get("goal_to_end", 0), 0) > 0 else 0
            p_goal = clamp(p_goal, 0.0, 1.0)
            brier_goal_sum += _brier_2(p_goal, y_goal)
            goal_pairs.append((p_goal, y_goal))
        except Exception:
            continue

    if n == 0:
        return None

    brier_1x2 = brier_1x2_sum / n
    brier_goal = brier_goal_sum / n
    acc_1x2 = hit_1x2 / n
    chaos_acc = (chaos_hit / chaos_n) if chaos_n > 0 else None

    # reliability heuristic: 0..1
    # For 3-class Brier: lower is better; typical range ~0.10..0.35
    rel = 1.0 - (brier_1x2 / 0.30)
    rel = clamp(rel, 0.15, 0.95)

    # calibration bins
    goal_bins = _calibration_bins_binary(goal_pairs, bins=10)
    topconf_bins = _calibration_bins_binary(topconf_pairs, bins=10)

    return {
        "n": n,
        "acc_1x2": acc_1x2,
        "brier_1x2": brier_1x2,
        "brier_goal": brier_goal,
        "reliability": rel,
        "chaos_n": chaos_n,
        "chaos_acc": chaos_acc,
        "goal_bins": goal_bins,
        "topconf_bins": topconf_bins,
    }


def calib_get_reliability():
    if _CALIB_CACHE.get("loaded", False):
        return float(_CALIB_CACHE.get("reliability", 0.75) or 0.75)
    res = backtest_learn_log(max_rows=0)
    if not res:
        _CALIB_CACHE.update({"loaded": True, "n": 0, "brier_1x2": None, "brier_goal": None, "reliability": 0.75})
        return 0.75
    _CALIB_CACHE.update({
        "loaded": True,
        "n": res["n"],
        "brier_1x2": res["brier_1x2"],
        "brier_goal": res["brier_goal"],
        "reliability": res["reliability"],
    })
    return float(res["reliability"])


def print_backtest_report():
    res = backtest_learn_log(max_rows=0)
    if not res:
        print("\nBACKTEST: Ni podatkov v learn logu.\n")
        return

    print(f"\n{CYAN}{BOLD}================ BACKTEST / KALIBRACIJA ================={RESET}\n")
    print("Rows".ljust(28), res["n"])
    print("1X2 accuracy".ljust(28), f"{res['acc_1x2']*100:.1f}%")
    print("Brier 1X2".ljust(28), f"{res['brier_1x2']:.4f}")
    print("Brier GOAL".ljust(28), f"{res['brier_goal']:.4f}")
    print("Reliability".ljust(28), f"{res['reliability']*100:.0f}%")
    if res["chaos_acc"] is not None:
        print("CHAOS acc".ljust(28), f"{res['chaos_acc']*100:.1f}% (n={res['chaos_n']})")

    print(f"\n{MAGENTA}--------------- GOAL CALIBRATION (bins) ----------------{RESET}\n")
    print("Bin".ljust(10), "n".rjust(6), "p_avg".rjust(10), "y_rate".rjust(10))
    for b in res["goal_bins"]:
        label = f"{int(b['lo']*100):02d}-{int(b['hi']*100):02d}%"
        if b["n"] == 0:
            print(label.ljust(10), str(0).rjust(6), "-".rjust(10), "-".rjust(10))
        else:
            print(label.ljust(10), str(b["n"]).rjust(6), f"{b['p_avg']:.3f}".rjust(10), f"{b['y_rate']:.3f}".rjust(10))

    print(f"\n{MAGENTA}--------------- TOP CONF CALIBRATION (bins) ----------------{RESET}\n")
    print("Bin".ljust(10), "n".rjust(6), "p_avg".rjust(10), "hit".rjust(10))
    for b in res["topconf_bins"]:
        label = f"{int(b['lo']*100):02d}-{int(b['hi']*100):02d}%"
        if b["n"] == 0:
            print(label.ljust(10), str(0).rjust(6), "-".rjust(10), "-".rjust(10))
        else:
            print(label.ljust(10), str(b["n"]).rjust(6), f"{b['p_avg']:.3f}".rjust(10), f"{b['y_rate']:.3f}".rjust(10))

# ============================================================
# CFOS FINAL BET ENGINE (FULL PRO VERSION + HIGH IQ)
# DAJ V 8/8
# KLIC: `izpis_rezultata()` pokliče `bet_decision(r)` enkrat (ujet print),
# nato banner naredi `auto_signal_final(r)` iz `final_auto_*`.
# ============================================================

LAST_BET = None
LAST_MINUTE = 0
LAST_MATCH_KEY = None


def bet_decision(r):

    global LAST_BET
    global LAST_MINUTE
    global LAST_MATCH_KEY

    # =====================================================
    # BASIC INPUT
    # =====================================================

    minute = int(float(r.get("minute", 0) or 0))
    score_diff = int(float(r.get("score_diff", 0) or 0))

    home = str(r.get("home", "") or "")
    away = str(r.get("away", "") or "")
    match_key = f"{home} vs {away}"

    p_goal = float(r.get("p_goal", 0) or 0)
    p_goal_10 = float(r.get("p_goal_10", 0) or 0)
    p_goal_5 = float(r.get("p_goal_5", 0) or 0)
    p_home_next = float(r.get("p_home_next", 0) or 0)
    p_away_next = float(r.get("p_away_next", 0) or 0)

    lam_h = float(r.get("lam_h", 0) or 0)
    lam_a = float(r.get("lam_a", 0) or 0)

    xg_h = float(r.get("xg_h", 0) or 0)
    xg_a = float(r.get("xg_a", 0) or 0)

    sot_h = float(r.get("sot_h", 0) or 0)
    sot_a = float(r.get("sot_a", 0) or 0)

    danger_h = float(r.get("danger_h", 0) or 0)
    danger_a = float(r.get("danger_a", 0) or 0)
    attacks_h = float(r.get("attacks_h", 0) or 0)
    attacks_a = float(r.get("attacks_a", 0) or 0)

    momentum = float(r.get("momentum", 0) or 0)

    mc_h = float(r.get("mc_h_adj", r.get("mc_h_raw", 0)) or 0)
    mc_x = float(r.get("mc_x_adj", r.get("mc_x_raw", 0)) or 0)
    mc_a = float(r.get("mc_a_adj", r.get("mc_a_raw", 0)) or 0)

    hist_home = float(r.get("hist_home", 0) or 0)
    hist_draw = float(r.get("hist_draw", 0) or 0)
    hist_away = float(r.get("hist_away", 0) or 0)

    meta_home = float(r.get("meta_home", mc_h) or 0)
    meta_draw = float(r.get("meta_draw", mc_x) or 0)
    meta_away = float(r.get("meta_away", mc_a) or 0)

    tempo_shots = float(r.get("tempo_shots", 0) or 0)
    tempo_danger = float(r.get("tempo_danger", 0) or 0)
    game_state = str(r.get("game_state", "IZENAČENO") or "IZENAČENO")
    ng_window_level = str(r.get("ng_window_level", "HOLD") or "HOLD").upper()
    ng_window_side = str(r.get("ng_window_side", "HOME") or "HOME").upper()
    split_shift_away = bool(r.get("split_shift_away", False))
    hidden_goal_risk = bool(r.get("hidden_goal_risk", False))
    counter_kill_mode = bool(r.get("counter_kill_mode", False))
    fake_home_pressure = bool(r.get("fake_home_pressure", False))
    dual_threat_mode = bool(r.get("dual_threat_mode", False))
    wave_active = bool((r.get("wave") or {}).get("active", False))
    pressure_goal_note = str(r.get("pressure_goal_note", "NO HIDDEN PRESSURE RISK") or "NO HIDDEN PRESSURE RISK")
    goal_timing = r.get("goal_timing") or {}
    goal_timing_entry = str(goal_timing.get("entry", "WAIT") or "WAIT").upper()
    bet_mode = str(r.get("bet_mode", "DIRECTION") or "DIRECTION").strip().upper()
    control_mode = str(r.get("control_mode", "") or "").strip().upper()
    kill_game = bool(r.get("kill_game", False))
    counter_risk = bool(r.get("counter_risk", False))

    dominance = float(r.get("dominance", 0) or 0)

    # next goal smart prediction
    ng_smart = r.get("next_goal_prediction_smart") or {}
    ng_smart_pred = str(ng_smart.get("prediction", "") or "")
    ng_smart_conf = float(ng_smart.get("confidence", 0) or 0)

    # optional high-IQ extras
    red_h = float(r.get("red_h", 0) or 0)
    red_a = float(r.get("red_a", 0) or 0)

    odds_home = float(r.get("odds_home", 0) or 0)
    odds_draw = float(r.get("odds_draw", 0) or 0)
    odds_away = float(r.get("odds_away", 0) or 0)

    # =====================================================
    # RESET ZA NOVO TEKMO
    # =====================================================

    if LAST_MATCH_KEY != match_key:
        LAST_BET = None
        LAST_MINUTE = 0
        LAST_MATCH_KEY = match_key

    # =====================================================
    # ONLY AFTER 70
    # =====================================================

    if minute < 70:
        early_side = "NONE"
        if game_state == "AWAY DOMINACIJA":
            early_side = "AWAY"
        elif game_state == "HOME DOMINACIJA":
            early_side = "HOME"
        print()
        print("=============== BET DECISION ===============" + cmd_tag("FINAL"))
        print()
        print("MINUTE:", minute)
        print()
        print("BET: NO BET")
        print("CONFIDENCE: LOW")
        print()
        print("ALTERNATIVE:")
        print("2) NO BET")
        print("3) NO BET")
        print("4) NO BET")
        print("5) NO BET")
        print()
        print("MODEL:")
        print("P_GOAL:", round(p_goal, 2))
        print("GAME STATE:", game_state)
        print("STRONGER SIDE:", early_side)
        print("MC:", round(mc_h, 2), "/", round(mc_x, 2), "/", round(mc_a, 2))
        print("HISTORY:", round(hist_home, 2), "/", round(hist_draw, 2), "/", round(hist_away, 2))
        print()
        print("============================================")
        try:
            r["final_auto_bet"] = "NO BET"
            r["final_auto_conf"] = "LOW"
            r["final_auto_reason"] = "EARLY PHASE (<70)"
        except Exception:
            pass
        try:
            _mr = calib_get_reliability()
        except Exception:
            _mr = 0.75
        append_bet_decision_log_row(
            r,
            main_bet="NO BET",
            decision_reason="EARLY PHASE (<70)",
            confidence="LOW",
            stake_band="0",
            pro_late_value_flag=False,
            match_bet="",
            match_reason="",
            top5=[],
            model_reliability=_mr,
            game_state=game_state,
            minute_val=minute,
        )
        try:
            r["_vd_engine"] = {
                "path": "early_lt70",
                "late_value_core": False,
                "pro_revive_ok": False,
                "partial_signal": False,
                "weak_conf_value": False,
                "strong_away_signal": False,
                "pro_late_value_flag": False,
            }
        except Exception:
            pass
        return

    # =====================================================
    # MASTER FREEZE FILTER (ANTI FAKE AWAY)
    # =====================================================

    lam_total = lam_h + lam_a

    low_lambda = lam_total < 0.45
    low_tempo = tempo_shots < 0.14 and tempo_danger < 1.05
    low_goal = p_goal < 0.38
    balanced = abs(momentum) < 0.10 and abs(lam_h - lam_a) < 0.12 and game_state == "IZENAČENO"

    if minute >= 70 and low_lambda and low_tempo and low_goal and balanced:
        print()
        print("=============== BET DECISION ===============" + cmd_tag("FINAL"))
        print()
        print("MINUTE:", minute)
        print()
        print("BET: NO BET")
        print("CONFIDENCE: HIGH")
        print("VALID:", minute, "-", int(minute + 5))
        print()
        print("ALTERNATIVE:")
        print("2) NO GOAL")
        print("3) DRAW")
        print("4) NEXT GOAL HOME")
        print("5) NEXT GOAL AWAY")
        print()
        print("MODEL:")
        print("P_GOAL:", round(p_goal, 2))
        print("GAME STATE:", game_state)
        print("STRONGER SIDE: NONE")
        print("MC:", round(mc_h, 2), "/", round(mc_x, 2), "/", round(mc_a, 2))
        print()
        print("============================================")

        try:
            r["final_auto_bet"] = "NO BET"
            r["final_auto_conf"] = "HIGH"
            r["final_auto_reason"] = "MASTER FREEZE FILTER"
        except Exception:
            pass
        try:
            _mr = calib_get_reliability()
        except Exception:
            _mr = 0.75
        append_bet_decision_log_row(
            r,
            main_bet="NO BET",
            decision_reason="MASTER FREEZE FILTER",
            confidence="HIGH",
            stake_band="0",
            pro_late_value_flag=False,
            match_bet="",
            match_reason="",
            top5=[],
            model_reliability=_mr,
            game_state=game_state,
            minute_val=minute,
        )
        try:
            r["_vd_engine"] = {
                "path": "master_freeze",
                "late_value_core": False,
                "pro_revive_ok": False,
                "partial_signal": False,
                "weak_conf_value": False,
                "strong_away_signal": False,
                "pro_late_value_flag": False,
            }
        except Exception:
            pass
        return

    # =====================================================
    # BASIC DIFFS
    # =====================================================

    sot_diff = abs(sot_h - sot_a)
    xg_diff = abs(xg_h - xg_a)
    danger_diff = abs(danger_h - danger_a)
    lam_diff = abs(lam_h - lam_a)

    # =====================================================
    # STRONGER SIDE SCORE
    # =====================================================

    side_score_h = 0.0
    side_score_a = 0.0

    if p_home_next > p_away_next:
        side_score_h += 2.0
    elif p_away_next > p_home_next:
        side_score_a += 2.0

    if lam_h > lam_a:
        side_score_h += 2.0
    elif lam_a > lam_h:
        side_score_a += 2.0

    if xg_h > xg_a:
        side_score_h += 1.5
    elif xg_a > xg_h:
        side_score_a += 1.5

    if sot_h > sot_a:
        side_score_h += 1.2
    elif sot_a > sot_h:
        side_score_a += 1.2

    if danger_h > danger_a:
        side_score_h += 2.0
    elif danger_a > danger_h:
        side_score_a += 2.0

    if momentum > 0.08:
        side_score_h += 1.8
    elif momentum < -0.08:
        side_score_a += 1.8

    if dominance > 0.08:
        side_score_h += 1.0
    elif dominance < -0.08:
        side_score_a += 1.0

    if meta_home > meta_away and meta_home > meta_draw:
        side_score_h += 1.0
    elif meta_away > meta_home and meta_away > meta_draw:
        side_score_a += 1.0

    if hist_home > hist_away and hist_home > hist_draw:
        side_score_h += 0.8
    elif hist_away > hist_home and hist_away > hist_draw:
        side_score_a += 0.8

    stronger_side = "NONE"
    if side_score_h > side_score_a:
        stronger_side = "HOME"
    elif side_score_a > side_score_h:
        stronger_side = "AWAY"

    if momentum < -0.30:
        stronger_side = "AWAY"
    elif momentum > 0.30:
        stronger_side = "HOME"

    if game_state == "AWAY DOMINACIJA":
        stronger_side = "AWAY"
    elif game_state == "HOME DOMINACIJA":
        stronger_side = "HOME"

    # =====================================================
    # CONTROL PRIORITY (late game): rezultat + MC > vizualni pritisk
    # =====================================================
    # V zaključku tekme mora "real dominance" (scoreboard + MC + market/history)
    # preglasiti surov napadalni volumen.
    if minute >= 70 and score_diff < 0 and mc_a > 0.60:
        stronger_side = "AWAY"
    elif minute >= 70 and score_diff > 0 and mc_h > 0.60:
        stronger_side = "HOME"

    # =====================================================
    # PRO: GLOBAL RELIABILITY (kalibracija iz backtesta)
    # =====================================================
    model_reliability = calib_get_reliability()

    # =====================================================
    # FILTERS
    # =====================================================

    fake_pressure = False
    fake_reason = ""

    if abs(momentum) > 0.15 and sot_diff == 0 and xg_diff < 0.20:
        fake_pressure = True
        fake_reason = "Momentum without SOT/xG support"

    if abs(momentum) > 0.18 and danger_diff < 10 and lam_diff < 0.12:
        fake_pressure = True
        fake_reason = "Momentum not confirmed by danger/lambda"

    if tempo_shots < 0.10 and tempo_danger < 0.75 and abs(momentum) > 0.14:
        fake_pressure = True
        fake_reason = "Momentum without tempo"

    # BONUS: HOME volume brez realizacije proti boljšemu AWAY SOT = fake pressure.
    if (
        attacks_h > attacks_a * 1.30
        and sot_h < sot_a
        and minute >= 65
    ):
        fake_home_pressure = True
        fake_pressure = True
        fake_reason = "FAKE HOME PRESSURE: volume without SOT edge"

    chaos = False
    if tempo_shots > 0.30 and tempo_danger > 1.60 and abs(momentum) < 0.05:
        chaos = True

    draw_crush = False
    if score_diff == 0:
        if (
            p_goal > 0.44
            or tempo_shots > 0.18
            or tempo_danger > 1.20
            or abs(momentum) > 0.12
            or lam_diff > 0.18
        ):
            draw_crush = True

    # =====================================================
    # SCORE SYSTEM FOR ALL BET TYPES
    # =====================================================

    scores = {
        "NEXT GOAL HOME": 0.0,
        "NEXT GOAL AWAY": 0.0,
        "COMEBACK HOME": 0.0,
        "COMEBACK AWAY": 0.0,
        "DRAW": 0.0,
        "NO GOAL": 0.0,
        "NO BET": 0.0,
    }

    # -----------------------------------------------------
    # NEXT GOAL HOME
    # -----------------------------------------------------

    if p_goal > 0.50:
        scores["NEXT GOAL HOME"] += 2.0

    if p_home_next > p_away_next:
        scores["NEXT GOAL HOME"] += 2.0

    if stronger_side == "HOME":
        scores["NEXT GOAL HOME"] += 2.0

    if lam_h > lam_a:
        scores["NEXT GOAL HOME"] += 1.5

    if xg_h > xg_a:
        scores["NEXT GOAL HOME"] += 1.0

    if sot_h > sot_a:
        scores["NEXT GOAL HOME"] += 1.0

    if danger_h > danger_a:
        scores["NEXT GOAL HOME"] += 1.5

    if momentum > 0.10:
        scores["NEXT GOAL HOME"] += 1.2

    if tempo_shots > 0.14:
        scores["NEXT GOAL HOME"] += 0.8

    if tempo_danger > 1.00:
        scores["NEXT GOAL HOME"] += 0.8

    if mc_h > mc_x and mc_h > mc_a:
        scores["NEXT GOAL HOME"] += 1.0

    if meta_home > meta_draw and meta_home > meta_away:
        scores["NEXT GOAL HOME"] += 1.0

    if hist_home > hist_draw and hist_home > hist_away:
        scores["NEXT GOAL HOME"] += 0.6

    if fake_pressure or chaos:
        scores["NEXT GOAL HOME"] -= 2.0

    # smart next goal signal boost (HOME)
    if ng_smart_pred == "HOME" and ng_smart_conf >= 0.57:
        scores["NEXT GOAL HOME"] += 1.0 + ng_smart_conf
    elif ng_smart_pred == "HOME" and ng_smart_conf >= 0.43:
        scores["NEXT GOAL HOME"] += 0.6

    # -----------------------------------------------------
    # NEXT GOAL AWAY
    # -----------------------------------------------------

    if p_goal > 0.50:
        scores["NEXT GOAL AWAY"] += 2.0

    if p_away_next > p_home_next:
        scores["NEXT GOAL AWAY"] += 2.0

    if stronger_side == "AWAY":
        scores["NEXT GOAL AWAY"] += 2.0

    if lam_a > lam_h:
        scores["NEXT GOAL AWAY"] += 1.5

    if xg_a > xg_h:
        scores["NEXT GOAL AWAY"] += 1.0

    if sot_a > sot_h:
        scores["NEXT GOAL AWAY"] += 1.0

    if danger_a > danger_h:
        scores["NEXT GOAL AWAY"] += 1.5

    if momentum < -0.10:
        scores["NEXT GOAL AWAY"] += 1.2

    if tempo_shots > 0.14:
        scores["NEXT GOAL AWAY"] += 0.8

    if tempo_danger > 1.00:
        scores["NEXT GOAL AWAY"] += 0.8

    if mc_a > mc_x and mc_a > mc_h:
        scores["NEXT GOAL AWAY"] += 1.0

    if meta_away > meta_draw and meta_away > meta_home:
        scores["NEXT GOAL AWAY"] += 1.0

    if hist_away > hist_draw and hist_away > hist_home:
        scores["NEXT GOAL AWAY"] += 0.6

    if fake_pressure or chaos:
        scores["NEXT GOAL AWAY"] -= 2.0

    # smart next goal signal boost (AWAY)
    if ng_smart_pred == "AWAY" and ng_smart_conf >= 0.57:
        scores["NEXT GOAL AWAY"] += 1.0 + ng_smart_conf
    elif ng_smart_pred == "AWAY" and ng_smart_conf >= 0.43:
        scores["NEXT GOAL AWAY"] += 0.6

    # -----------------------------------------------------
    # COMEBACK HOME
    # -----------------------------------------------------

    if score_diff < 0:
        scores["COMEBACK HOME"] += 2.5

    if stronger_side == "HOME" and score_diff < 0:
        scores["COMEBACK HOME"] += 2.0

    if p_goal > 0.42 and score_diff < 0:
        scores["COMEBACK HOME"] += 1.5

    if p_home_next > p_away_next and score_diff < 0:
        scores["COMEBACK HOME"] += 1.5

    if lam_h > lam_a and score_diff < 0:
        scores["COMEBACK HOME"] += 1.2

    if xg_h > xg_a and score_diff < 0:
        scores["COMEBACK HOME"] += 1.0

    if danger_h > danger_a and score_diff < 0:
        scores["COMEBACK HOME"] += 1.2

    if momentum > 0.10 and score_diff < 0:
        scores["COMEBACK HOME"] += 1.0

    if mc_x >= mc_h and score_diff < 0:
        scores["COMEBACK HOME"] += 0.5

    if hist_draw >= hist_away and score_diff < 0:
        scores["COMEBACK HOME"] += 0.4

    if fake_pressure:
        scores["COMEBACK HOME"] -= 2.0

    # -----------------------------------------------------
    # COMEBACK AWAY
    # -----------------------------------------------------

    if score_diff > 0:
        scores["COMEBACK AWAY"] += 2.5

    if stronger_side == "AWAY" and score_diff > 0:
        scores["COMEBACK AWAY"] += 2.0

    if p_goal > 0.42 and score_diff > 0:
        scores["COMEBACK AWAY"] += 1.5

    if p_away_next > p_home_next and score_diff > 0:
        scores["COMEBACK AWAY"] += 1.5

    if lam_a > lam_h and score_diff > 0:
        scores["COMEBACK AWAY"] += 1.2

    if xg_a > xg_h and score_diff > 0:
        scores["COMEBACK AWAY"] += 1.0

    if danger_a > danger_h and score_diff > 0:
        scores["COMEBACK AWAY"] += 1.2

    if momentum < -0.10 and score_diff > 0:
        scores["COMEBACK AWAY"] += 1.0

    if mc_x >= mc_a and score_diff > 0:
        scores["COMEBACK AWAY"] += 0.5

    if hist_draw >= hist_home and score_diff > 0:
        scores["COMEBACK AWAY"] += 0.4

    if fake_pressure:
        scores["COMEBACK AWAY"] -= 2.0

    # -----------------------------------------------------
    # DRAW
    # -----------------------------------------------------

    if score_diff == 0:
        scores["DRAW"] += 2.0

    if minute >= 75:
        scores["DRAW"] += 1.0

    if p_goal < 0.38:
        scores["DRAW"] += 1.8

    if mc_x > mc_h and mc_x > mc_a:
        scores["DRAW"] += 2.0

    if hist_draw >= hist_home and hist_draw >= hist_away:
        scores["DRAW"] += 1.2

    if meta_draw >= meta_home and meta_draw >= meta_away:
        scores["DRAW"] += 1.2

    if abs(momentum) < 0.08:
        scores["DRAW"] += 1.0

    if tempo_shots < 0.16:
        scores["DRAW"] += 0.8

    if tempo_danger < 1.05:
        scores["DRAW"] += 0.8

    if lam_diff < 0.15:
        scores["DRAW"] += 0.8

    if draw_crush or chaos:
        scores["DRAW"] -= 3.0

    # -----------------------------------------------------
    # NO GOAL
    # -----------------------------------------------------

    if minute >= 82:
        scores["NO GOAL"] += 2.0

    if p_goal < 0.30:
        scores["NO GOAL"] += 2.2

    if tempo_shots < 0.14:
        scores["NO GOAL"] += 1.2

    if tempo_danger < 0.95:
        scores["NO GOAL"] += 1.2

    if abs(momentum) < 0.06:
        scores["NO GOAL"] += 0.8

    if lam_diff < 0.18:
        scores["NO GOAL"] += 0.6

    if mc_x >= mc_h and mc_x >= mc_a:
        scores["NO GOAL"] += 1.0

    if hist_draw >= hist_home and hist_draw >= hist_away:
        scores["NO GOAL"] += 0.6

    if p_goal > 0.45:
        scores["NO GOAL"] -= 2.0

    if tempo_danger > 1.20 or tempo_shots > 0.18:
        scores["NO GOAL"] -= 1.2

    # -----------------------------------------------------
    # NO BET
    # -----------------------------------------------------

    scores["NO BET"] = 1.0

    if fake_pressure:
        scores["NO BET"] += 2.5

    if chaos:
        scores["NO BET"] += 2.5

    if 0.38 <= p_goal <= 0.50:
        scores["NO BET"] += 1.0

    if abs(side_score_h - side_score_a) < 1.0:
        scores["NO BET"] += 1.0

    if abs(mc_h - mc_a) < 0.08 and mc_x < 0.45:
        scores["NO BET"] += 0.8

    if draw_crush and score_diff == 0:
        scores["NO BET"] += 0.8

    if p_goal_10 < 0.34:
        scores["NO BET"] += 2.2
        scores["NEXT GOAL HOME"] -= 1.8
        scores["NEXT GOAL AWAY"] -= 1.8

    if ng_window_level in ("HOLD", "WATCH"):
        scores["NO BET"] += 1.6
        scores["NEXT GOAL HOME"] -= 1.2
        scores["NEXT GOAL AWAY"] -= 1.2
    elif ng_window_level == "TRIGGER":
        trigger_key = "NEXT GOAL HOME" if ng_window_side == "HOME" else "NEXT GOAL AWAY"
        scores[trigger_key] += 1.6

    if counter_kill_mode:
        scores["NEXT GOAL AWAY"] += 1.2
        scores["NO BET"] -= 0.8

    if fake_home_pressure:
        scores["NEXT GOAL HOME"] -= 1.4
        scores["NEXT GOAL AWAY"] += 0.8
        scores["NO BET"] += 0.5

    if wave_active and minute >= 85 and tempo_danger > 1.10:
        scores["NEXT GOAL HOME"] += 1.0
        # Pozna attack wave pomeni dual-threat cono, ne all-in.
        scores["NO BET"] += 0.4

    if dual_threat_mode:
        scores["NEXT GOAL HOME"] -= 2.0
        scores["NEXT GOAL AWAY"] -= 2.0
        scores["NO BET"] += 2.2

    # =====================================================
    # SAFETY ADJUSTMENTS
    # =====================================================

    if score_diff != 0:
        scores["DRAW"] -= 1.5

    if abs(score_diff) >= 2:
        scores["COMEBACK HOME"] -= 2.0
        scores["COMEBACK AWAY"] -= 2.0

    if stronger_side == "NONE":
        scores["NEXT GOAL HOME"] -= 1.0
        scores["NEXT GOAL AWAY"] -= 1.0

    # =====================================================
    # HIGH IQ GAME STATE PSYCHOLOGY
    # =====================================================

    if minute >= 87 and score_diff == 0:
        if tempo_shots < 0.18 and tempo_danger < 1.10:
            scores["NO GOAL"] += 2.5
            scores["DRAW"] += 1.5
            scores["NEXT GOAL HOME"] -= 1.5
            scores["NEXT GOAL AWAY"] -= 1.5

    # =====================================================
    # HIGH IQ FAVORITE PROTECTION
    # =====================================================

    if minute >= 80 and abs(score_diff) == 1:
        if meta_home > meta_away and score_diff > 0:
            scores["NO GOAL"] += 1.5
            scores["DRAW"] += 0.8
            scores["COMEBACK AWAY"] -= 1.5

        if meta_away > meta_home and score_diff < 0:
            scores["NO GOAL"] += 1.5
            scores["DRAW"] += 0.8
            scores["COMEBACK HOME"] -= 1.5

    # =====================================================
    # HIGH IQ RED CARD LOGIC
    # =====================================================

    if red_h > red_a:
        scores["NEXT GOAL AWAY"] += 1.8
        scores["COMEBACK AWAY"] += 1.0
        scores["NEXT GOAL HOME"] -= 1.5

    elif red_a > red_h:
        scores["NEXT GOAL HOME"] += 1.8
        scores["COMEBACK HOME"] += 1.0
        scores["NEXT GOAL AWAY"] -= 1.5

    # =====================================================
    # HIGH IQ LAST MINUTE SPIKE
    # =====================================================

    if minute >= 87:
        if tempo_shots > 0.22 or tempo_danger > 1.30:
            scores["NEXT GOAL HOME"] += 1.2
            scores["NEXT GOAL AWAY"] += 1.2
            scores["NO GOAL"] -= 1.5

    # =====================================================
    # HIGH IQ CONTEXT REASONING
    # =====================================================

    if minute >= 85 and score_diff == 0:
        signals = 0

        if tempo_shots > 0.18:
            signals += 1
        if tempo_danger > 1.15:
            signals += 1
        if abs(momentum) > 0.10:
            signals += 1
        if lam_diff > 0.15:
            signals += 1
        if stronger_side != "NONE":
            signals += 1
        if p_goal > 0.45:
            signals += 1

        if signals >= 4:
            scores["NEXT GOAL HOME"] += 1.5
            scores["NEXT GOAL AWAY"] += 1.5
            scores["DRAW"] -= 2.0

    # =====================================================
    # HIGH IQ UNCERTAINTY FILTER
    # =====================================================

    if abs(side_score_h - side_score_a) < 0.8 and p_goal < 0.45:
        scores["NO BET"] += 2.0

    # =====================================================
    # HIGH IQ CONTRADICTION DETECTOR
    # =====================================================

    contradiction = 0

    if momentum > 0.08 and xg_a > xg_h:
        contradiction += 1

    if momentum < -0.08 and xg_h > xg_a:
        contradiction += 1

    if danger_diff < 5 and abs(momentum) > 0.12:
        contradiction += 1

    if lam_diff < 0.08 and abs(momentum) > 0.14:
        contradiction += 1

    if contradiction >= 2:
        scores["NO BET"] += 2.0
        scores["NEXT GOAL HOME"] -= 1.0
        scores["NEXT GOAL AWAY"] -= 1.0

    # =====================================================
    # HIGH IQ SMART DRAW FILTER
    # =====================================================

    if score_diff == 0 and minute >= 82:
        if p_goal > 0.46 and stronger_side != "NONE":
            scores["DRAW"] -= 2.0

        if tempo_danger > 1.15:
            scores["DRAW"] -= 1.2

    # =====================================================
    # HIGH IQ LATE KILL LOGIC
    # =====================================================

    if minute >= 85 and abs(score_diff) == 1:
        if stronger_side == "HOME" and score_diff > 0:
            scores["COMEBACK AWAY"] -= 2.0

        if stronger_side == "AWAY" and score_diff < 0:
            scores["COMEBACK HOME"] -= 2.0

    # =====================================================
    # HIGH IQ CHAOS DETECTOR
    # =====================================================

    if tempo_shots > 0.28 and tempo_danger > 1.55:
        scores["NEXT GOAL HOME"] += 0.8
        scores["NEXT GOAL AWAY"] += 0.8
        scores["NO GOAL"] -= 1.5

    # =====================================================
    # HIGH IQ MARKET SANITY CHECK
    # =====================================================

    if odds_home > 0 and odds_away > 0:
        if odds_home < odds_away * 0.6:
            scores["NEXT GOAL HOME"] += 0.5
        elif odds_away < odds_home * 0.6:
            scores["NEXT GOAL AWAY"] += 0.5

    # =====================================================
    # SORT TOP 5
    # =====================================================

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top5 = ranked[:5]

    main_bet = top5[0][0]
    decision_reason = ""
    control_override_active = False
    control_soft_link_flag = False
    hard_no_bet_lock = False
    pro_late_value_flag = False

    ng_gap = abs(p_home_next - p_away_next)

    # =====================================================
    # HARD STOP FILTERS (GLOBAL) — prepreči "MC winner" bug
    # =====================================================
    # 1) Če je tekma praktično odločena (75+ in razlika 2+), in je gol v 10 min malo verjeten,
    #    potem to ni bet signal za "AWAY", ampak "game already decided" -> NO BET.
    if (
        minute >= 75
        and abs(score_diff) >= 2
        and p_goal_10 < 0.40
        and main_bet != "NO BET"
    ):
        main_bet = "NO BET"
        decision_reason = "GAME DECIDED FILTER"
        hard_no_bet_lock = True

    # 2) NEXT GOAL filter: če SMART confidence ni dovolj, ne dovolimo next-goal/comeback betov.
    if (
        (not hard_no_bet_lock)
        and ng_smart_conf < 0.62
        and main_bet in ("NEXT GOAL HOME", "NEXT GOAL AWAY", "COMEBACK HOME", "COMEBACK AWAY")
    ):
        main_bet = "NO BET"
        decision_reason = "LOW NEXT GOAL CONF (<62%)"
        hard_no_bet_lock = True

    # 3) LOW GOAL filter: če v naslednjih 10 min ni dovolj verjetnosti za gol,
    #    next-goal/comeback bet nima smisla.
    if (
        (not hard_no_bet_lock)
        and p_goal_10 < 0.40
        and main_bet in ("NEXT GOAL HOME", "NEXT GOAL AWAY", "COMEBACK HOME", "COMEBACK AWAY")
    ):
        main_bet = "NO BET"
        decision_reason = "LOW GOAL 10M"
        hard_no_bet_lock = True

    # =====================================================
    # GLOBAL ANTI-TRAP: LOSING TEAM PRESSURE (UNIVERZALNO)
    # =====================================================
    # Namen: blokira tipične pasti, ko HOME izgublja -2/-3,
    # igra je CHAOS/PRESSURE, pritisk naraste, ampak ni edge (gap < 12%).
    game_type = str(r.get("game_type", "") or "").strip().upper()
    if (
        minute >= 70
        and score_diff <= -2
        and game_type in ("CHAOS", "PRESSURE")
        and ng_gap < 0.12
        and main_bet != "NO BET"
    ):
        main_bet = "NO BET"
        decision_reason = "ANTI-TRAP LOSING PRESSURE"
        hard_no_bet_lock = True

    # =====================================================
    # PRO: FAKE COMEBACK IGNORE (HOME -3 PANIC PRESSURE)
    # =====================================================
    # Če HOME izgublja 3+ in ima samo "panik" pritisk (momentum+, lam_h>lam_a),
    # ne dovoli, da sistem izbere HOME next-goal/comeback brez realnega edge.
    if (
        minute >= 70
        and score_diff <= -3
        and game_type in ("CHAOS", "PRESSURE")
        and momentum > 0.0
        and lam_h > lam_a
        and ng_gap < 0.12
        and main_bet in ("NEXT GOAL HOME", "COMEBACK HOME")
    ):
        main_bet = "NO BET"
        decision_reason = "FAKE COMEBACK: LOSING -3 HOME PRESSURE"
        hard_no_bet_lock = True

    if main_bet in ("NEXT GOAL HOME", "NEXT GOAL AWAY") and ng_gap < 0.12:
        main_bet = "NO BET"
        decision_reason = "ANTI-TRAP: NEXT GOAL GAP < 12%"
    elif split_shift_away and main_bet == "NEXT GOAL HOME":
        main_bet = "NO BET"
        decision_reason = "ANTI-SPLIT: AWAY PRESSURE SHIFT"
    elif goal_timing_entry == "WAIT" and main_bet in ("NEXT GOAL HOME", "NEXT GOAL AWAY"):
        main_bet = "NO BET"
        decision_reason = "GOAL TIMING WAIT"
    elif hidden_goal_risk and main_bet != "NO BET":
        main_bet = "NO BET"
        decision_reason = pressure_goal_note
    elif dual_threat_mode and main_bet in ("NEXT GOAL HOME", "NEXT GOAL AWAY"):
        main_bet = "NO BET"
        decision_reason = "DUAL THREAT LOCK"

    # =====================================================
    # HISTORY STABILITY GUARD (FINAL DECISION LOCK)
    # =====================================================
    hist_map = {"HOME": hist_home, "DRAW": hist_draw, "AWAY": hist_away}
    model_map = {"HOME": mc_h, "DRAW": mc_x, "AWAY": mc_a}
    hist_top_side = max(hist_map, key=hist_map.get)
    hist_top_val = float(hist_map.get(hist_top_side, 0.0) or 0.0)
    model_on_hist_side = float(model_map.get(hist_top_side, 0.0) or 0.0)

    model_top_side = max(model_map, key=model_map.get)
    if (
        main_bet != "NO BET"
        and hist_top_val >= 0.70
        and model_top_side != hist_top_side
    ):
        main_bet = "NO BET"
        decision_reason = f"HISTORY LOCK: {hist_top_side} >= 70%"
    elif (
        main_bet != "NO BET"
        and abs(model_on_hist_side - hist_top_val) > 0.30
    ):
        main_bet = "NO BET"
        decision_reason = "HISTORY DIVERGENCE > 30%"

    # =====================================================
    # PRO: LATE GAME VALUE + WEAK CONF VALUE MODE (stake 0.5)
    # =====================================================
    # Namen: ozko okno (70+), tržni edge na AWAY, visok tempo, λ gostov — ko varnostni
    # filtri režejo v NO BET (npr. smart conf < 0.60 ali nizek 10m gol), PRO še vedno
    # vidi value: majhna stava, tip NEXT GOAL AWAY / COMEBACK AWAY (ne slepo 1X2).
    edge_a_pro = float(r.get("edge_a", 0.0) or 0.0)
    tempo_hi_pro = (float(tempo_shots) > 0.18) or (float(tempo_danger) > 1.2)
    pro_risk_block = (
        hidden_goal_risk
        or dual_threat_mode
        or (minute >= 75 and abs(score_diff) >= 2 and p_goal_10 < 0.32)
        or (
            minute >= 70
            and score_diff <= -2
            and game_type in ("CHAOS", "PRESSURE")
            and ng_gap < 0.10
        )
    )
    late_value_core = (
        minute >= 70
        and lam_a > lam_h
        and edge_a_pro > 0.06
        and tempo_hi_pro
        and p_away_next > p_home_next + 0.02
    )
    weak_conf_value = (
        ng_smart_pred == "AWAY"
        and 0.48 <= ng_smart_conf < 0.60
        and p_goal_10 >= 0.30
    )
    strong_away_signal = (
        ng_smart_pred == "AWAY"
        and ng_smart_conf >= 0.55
        and p_goal_10 >= 0.28
    )
    _dr = str(decision_reason or "")
    pro_banned_reason = (
        "GAME DECIDED FILTER" in _dr
        or "FAKE COMEBACK" in _dr
        or "ANTI-TRAP LOSING PRESSURE" in _dr
        or "HISTORY LOCK" in _dr
        or "HISTORY DIVERGENCE" in _dr
        or "DUAL THREAT" in _dr
    )
    pro_revive_ok = (
        main_bet == "NO BET"
        and late_value_core
        and not pro_risk_block
        and not pro_banned_reason
        and _dr
        not in (
            "GAME DECIDED FILTER",
            "FAKE COMEBACK: LOSING -3 HOME PRESSURE",
            "ANTI-TRAP LOSING PRESSURE",
        )
    )
    if pro_revive_ok and (weak_conf_value or strong_away_signal):
        if score_diff >= 1:
            main_bet = "COMEBACK AWAY"
            decision_reason = (
                "PRO: WEAK CONF VALUE (COMEBACK AWAY, stake 0.5)"
                if weak_conf_value
                else "PRO: LATE VALUE OVERRIDE (COMEBACK AWAY, stake 0.5)"
            )
        else:
            main_bet = "NEXT GOAL AWAY"
            decision_reason = (
                "PRO: WEAK CONF VALUE (NEXT GOAL AWAY, stake 0.5)"
                if weak_conf_value
                else "PRO: LATE VALUE OVERRIDE (NEXT GOAL AWAY, stake 0.5)"
            )
        hard_no_bet_lock = False
        pro_late_value_flag = True

    # =====================================================
    # SOFT CONTROL LINK (70+): control_mode -> majhen revive
    # =====================================================
    # Namen: kadar CONTROL engine jasno potrdi stran, dovolimo majhen (0.5) revive,
    # vendar samo ob poravnavi edge/lambda in brez freeze/kill/risk blokad.
    control_soft_ok = (
        minute >= 70
        and main_bet == "NO BET"
        and (not hard_no_bet_lock)
        and (not pro_late_value_flag)
        and (not pro_risk_block)
        and (not pro_banned_reason)
        and (not hidden_goal_risk)
        and (not dual_threat_mode)
        and (not kill_game)
        and (not counter_risk)
        and bet_mode not in ("FREEZE", "LOW_EVENT")
    )
    if control_soft_ok and control_mode == "AWAY_DOMINATION":
        if (
            edge_a_pro >= 0.05
            and lam_a > (lam_h * 1.25)
            and mc_a >= 0.82
            and p_away_next > p_home_next + 0.03
            and ng_smart_pred == "AWAY"
            and ng_smart_conf >= 0.58
        ):
            if score_diff >= 1:
                main_bet = "COMEBACK AWAY"
            else:
                main_bet = "NEXT GOAL AWAY"
            decision_reason = "SOFT CONTROL LINK: AWAY DOMINATION (70+, stake 0.5)"
            control_soft_link_flag = True
    elif control_soft_ok and control_mode == "HOME_DOMINATION":
        edge_h_pro = float(r.get("edge_h", 0.0) or 0.0)
        if (
            edge_h_pro >= 0.05
            and lam_h > (lam_a * 1.25)
            and mc_h >= 0.82
            and p_home_next > p_away_next + 0.03
            and ng_smart_pred == "HOME"
            and ng_smart_conf >= 0.58
        ):
            if score_diff <= -1:
                main_bet = "COMEBACK HOME"
            else:
                main_bet = "NEXT GOAL HOME"
            decision_reason = "SOFT CONTROL LINK: HOME DOMINATION (70+, stake 0.5)"
            control_soft_link_flag = True
    if control_soft_link_flag:
        hard_no_bet_lock = False

    vd_partial_signal = bool(
        late_value_core
        and (weak_conf_value or strong_away_signal)
        and (not pro_late_value_flag)
        and (not pro_revive_ok)
    )
    try:
        r["_vd_engine"] = {
            "path": "pro_sync",
            "late_value_core": bool(late_value_core),
            "pro_revive_ok": bool(pro_revive_ok),
            "weak_conf_value": bool(weak_conf_value),
            "strong_away_signal": bool(strong_away_signal),
            "pro_late_value_flag": bool(pro_late_value_flag),
            "control_soft_link_flag": bool(control_soft_link_flag),
            "pro_risk_block": bool(pro_risk_block),
            "pro_banned_reason": bool(pro_banned_reason),
            "partial_signal": vd_partial_signal,
            "edge_a_pro": float(edge_a_pro),
            "tempo_hi_pro": bool(tempo_hi_pro),
        }
    except Exception:
        pass

    # =====================================================
    # CONTROL OVERRIDE (STRUKTURA > 10M TIMING)
    # =====================================================
    # Če je sistem že izbral NO BET / remi / no-goal (ni edge za stavo),
    # tega NE smemo prepisati v surovo "AWAY" — to je povzročalo konflikt
    # z zgornjim bannerjem (NEXT GOAL / kontrola) vs končna odločitev.
    # Override sme samo okrepiti obstoječ AWAY-pritis signal (next goal / comeback),
    # ko je hkrati realen tržni edge za AWAY 1X2.
    edge_a_1x2 = float(r.get("edge_a", r.get("edge_away", 0)) or 0)
    if (
        (not hard_no_bet_lock)
        and (not pro_late_value_flag)
        and main_bet not in ("NO BET", "DRAW", "NO GOAL")
        and main_bet in ("NEXT GOAL AWAY", "COMEBACK AWAY")
        and mc_a >= 0.80
        and lam_a > (lam_h * 1.5)
        and momentum < -0.15
        and edge_a_1x2 >= 0.05
    ):
        main_bet = "AWAY"
        decision_reason = "CONTROL OVERRIDE"
        control_override_active = True

    # ================= ENTRY ENGINE (WAIT → TRIGGER → bet) =================
    # HOME vizualna dominanca + nizek P(goal 10m) → ne vstopi prezgodaj; čakaj spike/val.
    shots_h_en = float(r.get("shots_h", 0) or 0)
    shots_a_en = float(r.get("shots_a", 0) or 0)
    sot_h_en = float(r.get("sot_h", 0) or 0)
    sot_a_en = float(r.get("sot_a", 0) or 0)
    dominance_home_en = float(r.get("mc_h_adj", r.get("mc_h_raw", 0)) or 0)

    wait_mode = False
    if (
        minute >= 60
        and dominance_home_en > 0.60
        and sot_h_en >= 3
        and sot_a_en == 0
        and shots_h_en >= 10
        and shots_a_en <= 3
        and float(p_goal_10 or 0) < 0.25
    ):
        wait_mode = True

    l5_sh = float(r.get("entry_l5_shots_h", 0) or 0)
    l5_so = float(r.get("entry_l5_sot_h", 0) or 0)
    l5_dh = float(r.get("entry_l5_danger_h", 0) or 0)

    trigger_home = False
    if wait_mode:
        if (
            float(tempo_danger or 0) > 1.30
            or wave_active
            or l5_sh >= 2.0
            or l5_so >= 1.0
            or l5_dh >= 10.0
        ):
            trigger_home = True

    # ANTI LATE TRAP: ne odpiraj novega entry triggerja v 88+
    if minute >= 88:
        trigger_home = False

    # Ne sili entry HOME ob znanih pasteh
    if wait_mode and trigger_home and (hidden_goal_risk or dual_threat_mode):
        trigger_home = False

    entry_status = "NORMAL FLOW"
    if wait_mode and not trigger_home:
        entry_status = "WAITING FOR ENTRY"
        main_bet = "NO BET"
        decision_reason = "ENTRY ENGINE: WAIT TRIGGER (NO BET)"
        hard_no_bet_lock = False
        pro_late_value_flag = False
        control_soft_link_flag = False
    elif wait_mode and trigger_home:
        entry_status = "ENTRY SIGNAL ✔"
        main_bet = "NEXT GOAL HOME"
        decision_reason = "ENTRY ENGINE: TRIGGER → NEXT GOAL HOME"
        hard_no_bet_lock = False
        pro_late_value_flag = False
        control_soft_link_flag = False

    try:
        r["entry_wait_mode"] = bool(wait_mode)
        r["entry_trigger_home"] = bool(trigger_home)
        r["entry_status"] = str(entry_status)
    except Exception:
        pass

    # ================= FINAL TIMING FILTER (VALUE ≠ ENTRY) =================
    # Po vseh revive/override: smer (λ/value) ne sme staviti brez timinga (smart conf, 5m gol, val).
    _ng_timing_bets = ("NEXT GOAL HOME", "NEXT GOAL AWAY", "COMEBACK HOME", "COMEBACK AWAY")
    if main_bet in _ng_timing_bets:
        _t_parts = []
        if ng_smart_conf < 0.62:
            _t_parts.append("smart NG conf < 62%")
        if (not wave_active) and p_goal_5 < 0.30:
            _t_parts.append("no attack wave + P(goal 5m) < 30%")
        if _t_parts:
            main_bet = "NO BET"
            decision_reason = "FINAL TIMING FILTER: " + " | ".join(_t_parts)
            hard_no_bet_lock = True
            pro_late_value_flag = False
            control_soft_link_flag = False

    # =====================================================
    # MATCH CONTROL BET (LOČENO OD NEXT GOAL)
    # =====================================================
    match_bet = "NO BET"
    match_reason = "NO CLEAR CONTROL EDGE"
    if mc_a >= 0.80 and momentum < -0.15 and lam_a > (lam_h * 1.5):
        match_bet = "AWAY"
        match_reason = "STRONG CONTROL AWAY"
    elif mc_h >= 0.80 and momentum > 0.15 and lam_h > (lam_a * 1.5):
        match_bet = "HOME"
        match_reason = "STRONG CONTROL HOME"

    # =====================================================
    # BLOCK BET
    # =====================================================

    if LAST_BET not in (None, "", "NO BET"):
        if minute - LAST_MINUTE <= 3:
            print()
            print("=============== BET DECISION ===============" + cmd_tag("FINAL"))
            print()
            print("MINUTE:", minute)
            print()
            print("BET:", LAST_BET)
            print("CONFIDENCE: LOCKED")
            print("VALID:", LAST_MINUTE, "-", int(LAST_MINUTE + 5))
            print()
            print("ALTERNATIVE:")
            if len(top5) > 1:
                print("2)", top5[1][0])
            else:
                print("2) NO BET")
            if len(top5) > 2:
                print("3)", top5[2][0])
            else:
                print("3) NO BET")
            if len(top5) > 3:
                print("4)", top5[3][0])
            else:
                print("4) NO BET")
            if len(top5) > 4:
                print("5)", top5[4][0])
            else:
                print("5) NO BET")
            print()
            print("MODEL:")
            print("P_GOAL:", round(p_goal, 2))
            print("GAME STATE:", game_state)
            print("STRONGER SIDE:", stronger_side)
            print("MATCH BET:", match_bet, "|", match_reason)
            print("MC:", round(mc_h, 2), "/", round(mc_x, 2), "/", round(mc_a, 2))
            print("HISTORY:", round(hist_home, 2), "/", round(hist_draw, 2), "/", round(hist_away, 2))
            print()
            print("============================================")
            try:
                r["final_auto_bet"] = str(LAST_BET or "").strip().upper()
                r["final_auto_conf"] = "LOCKED"
                r["final_auto_reason"] = "BET LOCK (<=3 MIN)"
            except Exception:
                pass
            append_bet_decision_log_row(
                r,
                main_bet=str(LAST_BET or "").strip().upper() or "NO BET",
                decision_reason="BET LOCK (<=3 MIN)",
                confidence="LOCKED",
                stake_band="LOCKED",
                pro_late_value_flag=False,
                match_bet=match_bet,
                match_reason=match_reason,
                top5=top5,
                model_reliability=model_reliability,
                game_state=game_state,
                minute_val=minute,
            )
            return

    # =====================================================
    # CONFIDENCE
    # =====================================================

    top_score = top5[0][1]
    second_score = top5[1][1] if len(top5) > 1 else 0.0
    gap = top_score - second_score

    confidence = "LOW"
    if top_score >= 7.5 and gap >= 1.0:
        confidence = "HIGH"
    elif top_score >= 5.5 and gap >= 0.5:
        confidence = "MEDIUM"

    if main_bet == "NO BET":
        confidence = "LOW"

    # DEAD-TIME NO-GOAL LOCK: če je konec tekme zaprt, dvigni zaupanje.
    if (
        minute >= 90
        and p_goal < 0.35
        and mc_x > 0.60
        and main_bet == "NO GOAL"
    ):
        confidence = "HIGH"

    # ENTRY TRIGGER: top5 še lahko kaže NO BET, zato vsaj MEDIUM za jasno stavo
    if str(decision_reason or "").startswith("ENTRY ENGINE: TRIGGER"):
        if confidence == "LOW":
            confidence = "MEDIUM"

    # 0-0 najverjetnejši + 70+: znižaj zaupanje za next-goal/comeback (hladna tekma)
    _tops_cf = r.get("top_scores") or []
    _top0_cf = str(_tops_cf[0][0]).strip() if _tops_cf else ""
    if (
        minute >= 70
        and _top0_cf == "0-0"
        and main_bet in ("NEXT GOAL HOME", "NEXT GOAL AWAY", "COMEBACK HOME", "COMEBACK AWAY")
    ):
        if confidence == "HIGH":
            confidence = "MEDIUM"
        elif confidence == "MEDIUM":
            confidence = "LOW"

    # =====================================================
    # SAVE LOCK
    # =====================================================

    if main_bet != "NO BET":
        LAST_BET = main_bet
        LAST_MINUTE = minute
    else:
        LAST_BET = None
        LAST_MINUTE = 0

    # =====================================================
    # PRINT
    # =====================================================

    print()
    print("=============== BET DECISION ===============" + cmd_tag("FINAL"))
    print()
    print("MINUTE:", minute)
    print()
    print("BET:", main_bet)
    print("CONFIDENCE:", confidence)

    # =====================================================
    # PRO: STAKE / RISK ENGINE (banded)
    # =====================================================
    edge_val = 0.0
    if main_bet == "HOME":
        edge_val = float(r.get("edge_h", 0.0) or 0.0)
    elif main_bet == "DRAW":
        edge_val = float(r.get("edge_x", 0.0) or 0.0)
    elif main_bet == "AWAY":
        edge_val = float(r.get("edge_a", 0.0) or 0.0)

    chaos_flag = (str(r.get("game_type", "") or "").strip().upper() == "CHAOS")
    hard_lock_flag = bool(r.get("dual_threat_mode", False)) or bool(r.get("hidden_goal_risk", False))

    stake_band = "0"
    if main_bet == "NO BET":
        stake_band = "0"
    else:
        # baseline from confidence
        if confidence == "HIGH":
            stake_band = "MEDIUM"
        elif confidence == "MEDIUM":
            stake_band = "LOW"
        else:
            stake_band = "MICRO"

        # downgrade in chaos / low reliability
        if chaos_flag or model_reliability < 0.55:
            stake_band = "MICRO"

        # if we have real market edge, allow one step up (but never to HIGH automatically)
        if edge_val >= 0.05 and confidence in ("MEDIUM", "HIGH") and (not chaos_flag) and model_reliability >= 0.60:
            stake_band = "MEDIUM"
        elif edge_val >= 0.08 and confidence == "HIGH" and (not chaos_flag) and model_reliability >= 0.70:
            stake_band = "HIGH"

        # safety: any hard risk flag -> cap to MICRO/LOW
        if hard_lock_flag and stake_band in ("MEDIUM", "HIGH"):
            stake_band = "LOW"

    if pro_late_value_flag or control_soft_link_flag:
        stake_band = "HALF (0.5 PRO)"

    print("STAKE:".ljust(12), stake_band, f"(reliability {model_reliability*100:.0f}%)")

    if main_bet != "NO BET":
        print("VALID:", minute, "-", int(minute + 5))

    print()
    print("ALTERNATIVE:")

    if len(top5) > 1:
        print("2)", top5[1][0])
    else:
        print("2) NO BET")

    if len(top5) > 2:
        print("3)", top5[2][0])
    else:
        print("3) NO BET")

    if len(top5) > 3:
        print("4)", top5[3][0])
    else:
        print("4) NO BET")

    if len(top5) > 4:
        print("5)", top5[4][0])
    else:
        print("5) NO BET")

    print()
    print("================ ENTRY ENGINE =================")
    print(f"WAIT MODE:        {'YES' if wait_mode else 'NO'}")
    print(f"TRIGGER:          {'YES' if trigger_home else 'NO'}")
    if wait_mode and not trigger_home:
        print("STATUS:           WAITING FOR ENTRY")
    elif wait_mode and trigger_home:
        print("STATUS:           ENTRY SIGNAL ✔")
    else:
        print("STATUS:           NORMAL FLOW")
    if wait_mode:
        print(
            f"L5 HOME Δ:        shots +{l5_sh:.0f}  SOT +{l5_so:.0f}  danger +{l5_dh:.0f}"
        )
    print()

    print("MODEL:")
    print("P_GOAL:", round(p_goal, 2))
    print("P_GOAL_10M:", round(p_goal_10, 2))
    print("GAME STATE:", game_state)
    print("10M WINDOW:", ng_window_level, "(", ng_window_side, ")")
    print("STRONGER SIDE:", stronger_side)
    print("MATCH BET:", match_bet, "|", match_reason)
    print("MC:", round(mc_h, 2), "/", round(mc_x, 2), "/", round(mc_a, 2))
    print("HISTORY:", round(hist_home, 2), "/", round(hist_draw, 2), "/", round(hist_away, 2))
    if ng_smart_pred:
        print(f"NEXT GOAL SMART: {ng_smart_pred} (conf: {round(ng_smart_conf * 100, 1)} %)")

    if ng_window_level == "TRIGGER":
        print("!!! 10M NEXT GOAL TRIGGER ACTIVE !!!")
    if fake_home_pressure:
        print("TRAP FILTER: LATE FAKE HOME PRESSURE")
    if dual_threat_mode:
        print("TRAP FILTER: DUAL THREAT LOCK")

    if fake_pressure:
        print("FILTER:", fake_reason)
    if decision_reason:
        print("FINAL FILTER:", decision_reason)
    if pro_late_value_flag:
        print("PRO MODE: LATE VALUE / WEAK CONF — fixed stake 0.5 units (not full size)")
    if control_soft_link_flag:
        print("PRO MODE: SOFT CONTROL LINK — fixed stake 0.5 units (70+ only)")

    print()
    print("============================================")

    try:
        conf_word = str(confidence or "").strip().upper()
        r["final_auto_bet"] = str(main_bet or "").strip().upper()
        r["final_auto_conf"] = conf_word
        r["final_auto_reason"] = str(decision_reason or "").strip()
        r["pro_late_value_flag"] = bool(pro_late_value_flag)
        r["control_soft_link_flag"] = bool(control_soft_link_flag)
        r["pro_stake_units"] = 0.5 if (pro_late_value_flag or control_soft_link_flag) else 1.0
        r["cfos_bet_decision_log"] = BET_DECISION_LOG
    except Exception:
        pass
    try:
        append_bet_decision_log_row(
            r,
            main_bet=main_bet,
            decision_reason=decision_reason,
            confidence=confidence,
            stake_band=stake_band,
            pro_late_value_flag=pro_late_value_flag,
            match_bet=match_bet,
            match_reason=match_reason,
            top5=top5,
            model_reliability=model_reliability,
            game_state=game_state,
            minute_val=minute,
        )
    except Exception:
        pass

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

    line = input("Prilepi CSV (ali vpiši BACKTEST/BT):\n").strip()
    if str(line).strip().upper() in ("BACKTEST", "BT"):
        print_backtest_report()
        return
    data = parse_csv_line(line)

    rezultat, pre_lines = _capture_print_output(izracunaj_model, data)
    if rezultat is None:
        raise SystemExit(1)
    rezultat["_captured_preprint"] = pre_lines

    izpis_rezultata(rezultat)


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
                prediction_norm = "HOME"
            elif prediction in ["AWAY", "2", "GOST"]:
                prediction = "GOST"
                prediction_norm = "AWAY"
            elif prediction in ["DRAW", "X", "REMI"]:
                prediction = "REMI"
                prediction_norm = "DRAW"
            else:
                prediction_norm = normalize_outcome_label(prediction)

            if final_h > final_a:
                final_result = "DOMAČI"
                final_result_norm = "HOME"
            elif final_a > final_h:
                final_result = "GOST"
                final_result_norm = "AWAY"
            else:
                final_result = "REMI"
                final_result_norm = "DRAW"

            correct = 1 if prediction == final_result else 0

            try:
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
            except Exception as e:
                print("Napaka pri pisanju accuracy log:", e)

            save_match_result(
                home=rezultat["home"],
                away=rezultat["away"],
                minute=rezultat["minute"],
                prediction_1x2=prediction_norm,
                prediction_score=rezultat["top_scores"][0][0] if rezultat.get("top_scores") else "",
                result_1x2=final_result_norm,
                result_score=f"{final_h}-{final_a}",
                history_pred=rezultat.get("history_pred", "")
            )

            finalize_snapshots(final_h, final_a, rezultat["home"], rezultat["away"])
            clear_match_memory(rezultat["home"], rezultat["away"])
            cfos_accuracy()
            history_accuracy()

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
