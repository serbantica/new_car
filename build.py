#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — produce data/latest.json din:

    data/models.json                 (catalog tehnic, stabil)
  + data/scans/scan-<max(data)>.json (observatii de pret, volatile)
  + spec/criteria.yaml               (praguri, ponderi, parametri)
        -> data/latest.json          (derivat, NICIODATA editat manual)

Reguli nenegociabile respectate aici (CLAUDE.md, HANDOFF.md, DECISIONS.md):
  - NICIUN prag nu e hardcodat. Totul se citeste din criteria.yaml. Testul din
    tests/test_build.py verifica asta prin grep.
  - Cheie de identitate incompleta (echipare/motorizare lipsa) -> carantina,
    NU intra in min()/net. (D-020, CLAUDE.md §2)
  - null unde nu se stie; niciodata o valoare plauzibila. (CLAUDE.md §8)
  - Reducerile conditionate de finantare captiva NU intra in net (linie
    separata). Reducerile de casare nu se cumuleaza. (price-model.md, D-021)
  - Net afisat in doua variante: cu si fara Rabla (D-014, fereastra anuala).
  - Scoruri normalizate min-max pe universul curent => necomparabile intre
    scanuri. (criteria.yaml scoring.normalizare)
  - TCO calculeaza cu ce are si DECLARA ce lipseste; nu inventeaza. (HANDOFF §2)
  - Conflicte intre surse: pastrate ambele, marcate. Nu se alege tacut. (rule #5)

Ruleaza:  python3 build.py
"""

import glob
import json
import os
import re
import sys
import unicodedata
import datetime
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
CRITERIA_PATH = os.path.join(ROOT, "spec", "criteria.yaml")
MODELS_PATH = os.path.join(ROOT, "data", "models.json")
SCANS_DIR = os.path.join(ROOT, "data", "scans")
OUT_PATH = os.path.join(ROOT, "data", "latest.json")
TEMPLATE_PATH = os.path.join(ROOT, "dashboard", "template.html")
DASHBOARD_OUT = os.path.join(ROOT, "dashboard", "index.html")
ROOT_INDEX = os.path.join(ROOT, "index.html")

CONFIDENCE_RANK = {"confirmed": 3, "derived": 2, "estimated": 1, None: 0}
BRAND_ALIASES = {"volkswagen": {"volkswagen", "vw"}}


# --------------------------------------------------------------------------- #
# Incarcare
# --------------------------------------------------------------------------- #
def load_criteria(path=CRITERIA_PATH):
    try:
        import yaml
    except ImportError:  # pragma: no cover
        sys.exit("EROARE: PyYAML lipseste. `pip install pyyaml`.")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_models(path=MODELS_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_latest_scan(scans_dir=SCANS_DIR):
    """max(data) din numele fisierelor — nu presupune, listeaza. (CLAUDE.md §9)"""
    dated = []
    for p in glob.glob(os.path.join(scans_dir, "scan-*.json")):
        m = re.search(r"scan-(\d{4}-\d{2}-\d{2})", os.path.basename(p))
        if m:
            dated.append((m.group(1), p))
    if not dated:
        sys.exit(f"EROARE: niciun scan gasit in {scans_dir}")
    dated.sort()
    scan_date, scan_path = dated[-1]
    with open(scan_path, encoding="utf-8") as f:
        return scan_date, os.path.basename(scan_path), json.load(f)


# --------------------------------------------------------------------------- #
# Helperi pe formatul {v, c, s} vs scalar
# --------------------------------------------------------------------------- #
def val(x):
    """Valoarea, indiferent daca faptul e {v,c,s} sau scalar simplu."""
    if isinstance(x, dict) and "v" in x:
        return x["v"]
    return x


def conf(x):
    return x.get("c") if isinstance(x, dict) else None


def combine_conf(*cs):
    """Confidence rezultat = cel mai slab dintre inputuri (min pe rang)."""
    present = [c for c in cs if c is not None]
    if not present:
        return None
    return min(present, key=lambda c: CONFIDENCE_RANK.get(c, 0))


def first_number(x):
    """Primul numar dintr-un scalar/range ('4172-4197' -> 4172; 7 -> 7)."""
    if x is None:
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return x
    m = re.search(r"-?\d+(?:\.\d+)?", str(x))
    if not m:
        return None
    return float(m.group()) if "." in m.group() else int(m.group())


def is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


# --------------------------------------------------------------------------- #
# Normalizare pentru join pe cheia de identitate
# --------------------------------------------------------------------------- #
def _strip_diacritics(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s):
    if s is None:
        return ""
    s = _strip_diacritics(str(s)).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def is_placeholder(s):
    n = norm(s)
    if n == "":
        return True
    return any(tok in n for tok in ("necunoscut", "nedeterminat", "probabil"))


def cutie_base(s):
    n = norm(s)
    if not n:
        return None
    if "manual" in n or re.search(r"\b6?mt\b", n):
        return "manuala"
    if "ecvt" in n:
        return "ecvt"
    if "dsg" in n:
        return "dsg"
    if "dct" in n:
        return "dct"
    if "edc" in n:
        return "edc"
    if "auto" in n or re.search(r"\bat\b", n):
        return "automata"
    return n


def tractiune_base(s):
    n = norm(s)
    if not n:
        return None
    if "2wd" in n or "fwd" in n or "fata" in n:
        return "2wd"
    if "awd" in n or "4x4" in n or "4motion" in n or "allgrip" in n or "4wd" in n:
        return "awd"
    return n


ENGINE_TECH_TOKENS = [
    "mhev", "mildhybrid", "hev", "hybrid", "phev",
    "tsi", "tgdi", "tce", "ecoboost", "digt",
    "boosterjet", "ehev", "immd", "tdi", "ecog",
]


def engine_sig(s):
    """Semnatura motorului: cilindree + tokeni tehnici + putere (daca apar)."""
    raw = str(s or "").lower()
    n = norm(s)
    nn = n.replace(" ", "")
    displ = set(re.findall(r"\d\.\d", raw))
    tech = set(t for t in ENGINE_TECH_TOKENS if t in nn)
    power = set(re.findall(r"(\d{2,3})\s*(?:cp|ps|hp)\b", n))
    if not power:  # numere de 3 cifre plauzibile ca putere (euristica de parsare)
        power = set(m for m in re.findall(r"\b(\d{3})\b", n) if 80 <= int(m) <= 260)
    return {"displ": displ, "tech": tech, "power": power}


def engine_match(cat_s, obs_s):
    a, b = engine_sig(cat_s), engine_sig(obs_s)
    if a["displ"] and b["displ"] and not (a["displ"] & b["displ"]):
        return False
    tech_ok = bool(a["tech"] & b["tech"]) if (a["tech"] and b["tech"]) else True
    power_ok = bool(a["power"] & b["power"]) if (a["power"] and b["power"]) else True
    return tech_ok or power_ok


def echipare_match(cat_e, obs_e):
    """Tokeni de echipare compatibili (unul inclus in celalalt sau se ating)."""
    ca = set(norm(cat_e).split()) - {"pachet", "optional", "de", "cu"}
    cb = set(norm(obs_e).split())
    if not ca or not cb:
        return False
    return cb.issubset(ca) or ca.issubset(cb) or bool(ca & cb)


def model_name_matches(marca, model, obs_model):
    """Model prezent ca substring + marca (cu aliasuri: Volkswagen ~ VW)."""
    o = norm(obs_model)
    model_ok = norm(model) in o
    brand_variants = BRAND_ALIASES.get(norm(marca), {norm(marca)})
    brand_ok = any(b in o for b in brand_variants)
    return brand_ok and model_ok


# --------------------------------------------------------------------------- #
# Join: atribuie fiecare observatie unui rand din catalog sau carantinei
# --------------------------------------------------------------------------- #
def build_join(models, scan):
    """
    Carantina HARD (nu intra niciodata in min/net):
      - flag explicit `carantina: true`;
      - echipare SAU motorizare lipsa/placeholder (cheia rupta exact la campurile
        care spun "ce masina e" — D-020, protectie statistica anti-min-naiv);
      - nicio configuratie catalogata a modelului nu se potriveste.
    Cheie PARTIALA (cutie/tractiune absente) => se ataseaza cu `cheie_partiala`,
    ca incertitudinea sa ramana vizibila.
    """
    catalog = models["modele"]
    attach = {m["id"]: [] for m in catalog}
    carantina = []

    for obs in scan.get("observatii_pret", []):
        obs_model = obs.get("model", "")
        if obs.get("carantina") is True:
            carantina.append({"observatie": obs,
                              "motiv": obs.get("motiv_carantina", "marcata carantina in scan")})
            continue
        if is_placeholder(obs.get("echipare")) or is_placeholder(obs.get("motorizare")):
            carantina.append({"observatie": obs,
                              "motiv": "cheie incompleta: echipare sau motorizare lipsa/placeholder"})
            continue

        cand = [m for m in catalog if model_name_matches(m["marca"], m["model"], obs_model)]
        if not cand:
            carantina.append({"observatie": obs,
                              "motiv": f"niciun model din catalog nu corespunde '{obs_model}'"})
            continue

        matched = None
        for m in cand:
            if not engine_match(m.get("motorizare"), obs.get("motorizare")):
                continue
            cat_cutie, obs_cutie = cutie_base(val(m.get("cutie"))), cutie_base(obs.get("cutie"))
            if cat_cutie and obs_cutie and cat_cutie != obs_cutie:
                continue
            cat_trac, obs_trac = tractiune_base(val(m.get("tractiune"))), tractiune_base(obs.get("tractiune"))
            if cat_trac and obs_trac and cat_trac != obs_trac:
                continue
            cat_ech = val(m.get("echipare_selectata"))
            # randurile nedeterminate au echipare null -> se atribuie pe motor+cutie,
            # echiparea se preia din observatie.
            if cat_ech is not None and not echipare_match(cat_ech, obs.get("echipare")):
                continue
            matched = m
            break

        if matched is None:
            carantina.append({"observatie": obs,
                              "motiv": f"nicio configuratie catalogata a '{obs_model}' "
                                       f"nu se potriveste (motor/cutie/echipare)"})
            continue

        obs2 = dict(obs)
        missing = [k for k in ("cutie", "tractiune") if not obs.get(k)]
        if missing:
            obs2["cheie_partiala"] = missing
        attach[matched["id"]].append(obs2)

    return attach, carantina


# --------------------------------------------------------------------------- #
# Bani
# --------------------------------------------------------------------------- #
def _doc_year(obs):
    m = re.search(r"(\d{4})", str(obs.get("data_document") or obs.get("valabil_pana") or ""))
    return int(m.group(1)) if m else 0


def representative(observations):
    """Cea mai autoritativa: confidence, apoi cea mai recenta, apoi pretul minim."""
    if not observations:
        return None
    return sorted(
        observations,
        key=lambda o: (CONFIDENCE_RANK.get(o.get("confidence"), 0),
                       _doc_year(o),
                       -(o.get("pret_eur") or 10 ** 9)),
        reverse=True,
    )[0]


def rabla_for(propulsie, rabla_cfg):
    """Prima de casare dupa propulsia masinii CUMPARATE. Parametri din criteria."""
    if rabla_cfg.get("status") != "activ":
        return {"v": 0, "c": "confirmed", "nota": rabla_cfg.get("regula", "program neconfirmat -> 0")}
    prima = rabla_cfg["prima_eur"]
    if propulsie == "benzina":
        return {"v": prima["benzina"], "c": rabla_cfg.get("confidence", "confirmed"), "grila": "benzina"}
    if propulsie == "hev":
        return {"v": prima["hibrid_non_plugin"], "c": rabla_cfg.get("confidence", "confirmed"),
                "grila": "hibrid_non_plugin"}
    if propulsie == "mhev_48v":
        key = rabla_cfg.get("mhev_incadrare", "hibrid_non_plugin")
        return {"v": prima[key], "c": rabla_cfg.get("mhev_confidence", "derived"),
                "grila": key, "nota": "mhev incadrat la grila hibrid (D-020, derived)"}
    return {"v": 0, "c": "confirmed", "nota": f"propulsie '{propulsie}' in afara grilei"}


def compute_money(row, observations, criteria):
    rabla_cfg = criteria["pret"]["rabla"]
    propulsie = row.get("propulsie")

    lista_obs = [o for o in observations if o.get("tip_pret") == "lista"]
    promo_captiv = [o for o in observations
                    if o.get("tip_pret") == "net_promotional" and o.get("EXCLUS_DIN_NET")]
    promo_curat = [o for o in observations
                   if o.get("tip_pret") == "net_promotional" and not o.get("EXCLUS_DIN_NET")]

    lista_rep = representative(lista_obs)
    promo_rep = representative(promo_curat)

    # pret_lista al configuratiei CALIFICATE = pret trim de baza + optiuni_incluse
    # (catalogul e autoritatea pe costul pachetului calificator, price-model.md).
    pret_lista = None
    if lista_rep and lista_rep.get("pret_eur") is not None:
        baza = lista_rep["pret_eur"]
        opt = val(row.get("optiuni_incluse_eur"))
        ech_raw = str(val(row.get("echipare_selectata")) or "")
        pachet_necunoscut = ("pachet" in norm(ech_raw) or "+" in ech_raw) and not is_number(opt)
        efectiv = baza + opt if is_number(opt) else baza
        pret_lista = {
            "v": efectiv,
            "c": lista_rep.get("confidence"),
            "s": lista_rep.get("url"),
            "data_document": lista_rep.get("data_document"),
            "pret_trim_baza_eur": baza,
            "optiuni_incluse_eur": opt if is_number(opt) else None,
            "pachet_pret_necunoscut": pachet_necunoscut,
        }
        if pachet_necunoscut:
            pret_lista["nota"] = ("pretul pachetului calificator nu e publicat; "
                                  "pret_lista e o limita INFERIOARA")
        tot = lista_rep.get("total_configuratie_calificata_eur")
        if is_number(tot) and tot != efectiv:
            pret_lista["conflict_total_observat_eur"] = tot

    prima = rabla_for(propulsie, rabla_cfg)
    prima["nota_eligibilitate"] = ("Rabla e fereastra anuala; eligibilitatea pe durata de "
                                   "proprietate e intrebare deschisa (D-014). Net in doua variante.")

    # pret_net_fara_rabla = lista - discount neconditionat defalcat pe rand.
    # In acest scan niciun discount comercial neconditionat nu e defalcat pe rand
    # (sunt inglobate in preturi promo, netratabile), deci = pret_lista.
    net_fara_rabla = None
    if pret_lista and pret_lista["v"] is not None:
        net_fara_rabla = {"v": pret_lista["v"], "c": pret_lista["c"],
                          "baza": "pret_lista (niciun discount neconditionat defalcat pe rand)"}

    net_estimat = None
    if net_fara_rabla and net_fara_rabla["v"] is not None:
        net_estimat = {"v": net_fara_rabla["v"] - prima["v"],
                       "c": combine_conf(net_fara_rabla["c"], prima["c"]),
                       "sursa": "pret_net_fara_rabla - prima_rabla"}

    # Pret promotional observat: pastrat ca observatie, NU topit in netul derivat.
    # Contine adesea reduceri comerciale (nu doar Rabla) pe care netul nu le
    # numara — de aceea ramane o linie separata, reproductibilitatea conteaza.
    net_promo_obs = None
    if promo_rep and promo_rep.get("pret_eur") is not None:
        net_promo_obs = {"v": promo_rep["pret_eur"],
                         "c": promo_rep.get("confidence") or "estimated",
                         "url": promo_rep.get("url"),
                         "valabil_pana": promo_rep.get("valabil_pana"),
                         "nota": "pret afisat de dealer; compozitie posibil diferita de net. "
                                 "NU e topit in netul derivat."}

    reduceri_cond = [{"pret_promo_eur": o.get("pret_eur"), "url": o.get("url"),
                      "motiv_excludere": o.get("motiv_excludere",
                                               "conditionat de finantare captiva / asigurare")}
                     for o in promo_captiv]

    return {
        "pret_lista": pret_lista,
        "pret_net_fara_rabla": net_fara_rabla,
        "prima_rabla": prima,
        "pret_net_estimat": net_estimat,
        "pret_net_promotional_observat": net_promo_obs,
        "cost_total_5_ani": None,   # vezi diagnostic.tco
        "cost_pe_km": None,
        "reduceri_conditionate": reduceri_cond,
        "dispersie_dealeri_eur": compute_dispersion(row, observations),
        "nr_observatii": len(observations),
        "observatii": observations,
    }


def compute_dispersion(row, observations):
    """
    max-min pe observatii cu ACEEASI cheie completa si acelasi tip_pret; altfel null.
    Cheia completa se COMPLETEAZA din catalog: obs sunt deja atasate randului (join-ul
    a verificat compatibilitatea pe motor/cutie/tractiune), deci cutie/tractiune absente
    din observatie se mostenesc din randul catalogat — autoritatea pe drivetrain. Asa
    ramane "aceeasi cheie completa" (D-020) fara sa moara functia cand scanul nu repeta
    drivetrain-ul pe fiecare linie.
    """
    groups = {}
    for o in observations:
        if not (norm(o.get("echipare")) and norm(o.get("motorizare"))):
            continue  # echipare/motorizare lipsa => nu era aici oricum (carantina)
        if o.get("pret_eur") is None:
            continue
        cut = cutie_base(o.get("cutie")) or cutie_base(val(row.get("cutie")))
        tra = tractiune_base(o.get("tractiune")) or tractiune_base(val(row.get("tractiune")))
        k = (norm(o["echipare"]), repr(engine_sig(o["motorizare"])), cut, tra, o.get("tip_pret"))
        groups.setdefault(k, []).append(o["pret_eur"])
    for prices in groups.values():
        if len(prices) >= 2:
            return max(prices) - min(prices)
    return None  # sub 2 observatii pe aceeasi cheie => null, NU 0 (D-020)


# --------------------------------------------------------------------------- #
# Marcaje
# --------------------------------------------------------------------------- #
def prag_truthy(row):
    p = row.get("prag_dotari_atins")
    return val(p) is True, conf(p)


def compute_in_buget(money, criteria):
    """Doua baze (D-014): fara Rabla si cu Rabla. Stare tri-valenta."""
    b = criteria["marcaje"]["buget"]
    plafon = b["tinta_eur"][1] * (1 + b["toleranta_pct"] / 100.0)

    def under(node):
        if node and node.get("v") is not None:
            return node["v"] <= plafon, node["v"]
        return None, None

    fara_ok, fara_v = under(money.get("pret_net_fara_rabla"))
    cu_ok, cu_v = under(money.get("pret_net_estimat"))

    if fara_ok is None and cu_ok is None:
        stare = None
    elif fara_ok:
        stare = "da"
    elif cu_ok:
        stare = "doar_cu_rabla"
    else:
        stare = "nu"

    return {
        "stare": stare,
        "fara_rabla": fara_ok,
        "cu_rabla": cu_ok,
        "plafon_eur": round(plafon),
        "valoare_fara_rabla_eur": fara_v,
        "valoare_cu_rabla_eur": cu_v,
    }


def collect_conflicts(row):
    """Conflicte de sursa: top-level `conflict*` + `conflict` din campuri {v,...}."""
    out = []
    for k, v in row.items():
        if "conflict" in k.lower() and isinstance(v, str):
            out.append({"camp": k, "nota": v})
        if isinstance(v, dict) and "conflict" in v:
            out.append({"camp": k, "nota": v["conflict"]})
    return out or None


# --------------------------------------------------------------------------- #
# Scoruri
# --------------------------------------------------------------------------- #
def cuplu_score(v, interval):
    if v is None:
        return None
    lo, hi = interval
    if lo <= v <= hi:
        return 1.0
    return max(0.0, v / lo) if v < lo else hi / v


def bonus_mostenit_score(row, bonus_w):
    s = 0.0
    if tractiune_base(val(row.get("tractiune"))) == "awd":
        s += bonus_w.get("tractiune_integrala", 0)
    if cutie_base(val(row.get("cutie"))) == "manuala":
        s += bonus_w.get("cutie_manuala", 0)
    return s


def _minmax(values, invert):
    vals = [v for v in values if v is not None]
    if not vals:
        return lambda x: None
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return lambda x: (1.0 if x is not None else None)
    if invert:
        return lambda x: ((hi - x) / (hi - lo) if x is not None else None)
    return lambda x: ((x - lo) / (hi - lo) if x is not None else None)


def compute_scores(rows_ctx, criteria):
    """Scoruri DOAR pentru universul (prag atins, neexclus). Min-max pe acest set."""
    profiles = criteria["scoring"]["profiles"]
    interval = criteria["cuplu"]["interval_preferat_nm"]
    bonus_w = criteria["scoring"]["bonus_mostenit"]

    universe = [c for c in rows_ctx if c["_prag"] and not c["_exclus"]]

    def net_val(c):
        n = c["money"].get("pret_net_estimat")
        return n["v"] if n and n.get("v") is not None else None

    def gar_val(c):
        return first_number(val(c["row"].get("garantie_ani")))

    def cuplu_val(c):
        return first_number(val(c["row"].get("cuplu_termic_nm")))

    norm_gar = _minmax([gar_val(c) for c in universe], invert=False)
    norm_net = _minmax([net_val(c) for c in universe], invert=True)

    coverage = {}
    for c in universe:
        row = c["row"]
        # fiabilitate_independenta n-are >=2 surse pe niciun rand => ponderea ei se
        # redistribuie la garantie (criteria fiabilitate_garantie_componente.reguli).
        comp = {
            "fiabilitate_garantie": (norm_gar(gar_val(c)),
                                     "garantie (fiab. independenta lipsa -> pondere redistribuita)"),
            "cuplu_disponibil": (cuplu_score(cuplu_val(c), interval),
                                 "cuplu_termic_nm vs interval preferat"),
            "bonus_mostenit": (bonus_mostenit_score(row, bonus_w), "AWD + manuala"),
            "pret_net_estimat": (norm_net(net_val(c)), "min-max invers pe univers"),
            "tco_5_ani": (None, "cost_total_5_ani indisponibil (vezi diagnostic.tco)"),
            "consum_real": (None, "consum_real_l100 lipseste pe toate randurile"),
            "spatiu_ergonomie": (None, "portbagaj_l / ergonomie indisponibile"),
        }
        c["_brute"] = {
            "garantie_ani": gar_val(c),
            "cuplu_termic_nm": cuplu_val(c),
            "bonus_mostenit": bonus_mostenit_score(row, bonus_w),
            "pret_net_estimat": net_val(c),
        }
        c["scoruri"] = {}
        for pname, weights in profiles.items():
            total_w, acc, used = 0.0, 0.0, {}
            for comp_name, w in weights.items():
                if not is_number(w) or w == 0:
                    continue  # sare peste 'descriere' si ponderile nule
                nv, note = comp.get(comp_name, (None, "necunoscut"))
                used[comp_name] = {"pondere": w,
                                   "valoare_norm": round(nv, 4) if nv is not None else None,
                                   "nota": note}
                if nv is not None:
                    acc += w * nv
                    total_w += w
            c["scoruri"][pname] = {
                "scor": round(acc / total_w, 4) if total_w > 0 else None,
                "acoperire_pondere": round(total_w, 4),
                "componente": used,
            }
            coverage[pname] = round(total_w, 4)

    return universe, coverage


# --------------------------------------------------------------------------- #
# Config bakuit in latest.json (dashboard citeste DOAR JSON; criteria ramane
# sursa unica — aici e o COPIE regenerata la fiecare build, nu o redeclarare)
# --------------------------------------------------------------------------- #
def bake_config(criteria):
    q = criteria["query"]
    r = criteria["pret"]["rabla"]
    return {
        "_nota": "Copiat din criteria.yaml la build. criteria.yaml ramane sursa unica; "
                 "regenerat la fiecare rulare. Dashboard-ul citeste DOAR de aici.",
        "hard_filters": criteria["hard_filters"],
        "marcaje_buget": criteria["marcaje"]["buget"],
        "scoring_profiles": criteria["scoring"]["profiles"],
        "profil_activ": criteria["scoring"]["profil_activ"],
        "cuplu_interval_preferat_nm": criteria["cuplu"]["interval_preferat_nm"],
        "query": {
            "filtrabile": q["filtrabile"],
            "sort_keys": [k for k, _ in q["sort_keys"].items()],
            "sort_keys_descrieri": {k: v for k, v in q["sort_keys"].items() if v},
            "sort_default": q["sort_default"],
            "sort_secundar": q["sort_secundar"],
            "filtru_implicit": q["filtru_implicit"],
            "max_rezultate_implicit": q["reguli"]["max_rezultate_implicit"],
        },
        "tco": {"km_pe_an": criteria["tco"]["km_pe_an"],
                "orizont_ani": criteria["tco"]["orizont_ani"],
                "pret_benzina_eur_l": criteria["tco"]["pret_benzina_eur_l"]},
        "rabla": {"an_program": r["an_program"], "status": r["status"],
                  "prima_eur": r["prima_eur"], "fereastra": [r["start"], r["sfarsit"]]},
        "reference_vehicle": criteria["reference_vehicle"],
    }


def tco_diagnostic(models, criteria):
    lipsa = []
    if criteria["tco"].get("pret_benzina_eur_l") is None:
        lipsa.append("tco.pret_benzina_eur_l (criteria.yaml) = null")
    if not any(val(m.get("consum_real_l100")) is not None for m in models["modele"]):
        lipsa.append("consum_real_l100 lipseste pe TOATE randurile din catalog")
    lipsa.append("valoare_reziduala: neestimata pe niciun rand")
    lipsa.append("rca / casco / revizii / anvelope / impozit_auto: neintroduse")
    return {
        "tco_calculabil": False,
        "consecinta": "cost_total_5_ani si cost_pe_km = null peste tot; sortarea implicita "
                      "cade pe pret_net_estimat (HANDOFF §2, optiunea 2).",
        "nota_pret_benzina": "Chiar cu pretul benzinei completat, TCO ramane null: lipsesc "
                             "consum_real, reziduala si costurile de intretinere. Un singur "
                             "fetch NU deblocheaza TCO.",
        "inputuri_lipsa": lipsa,
    }


# --------------------------------------------------------------------------- #
# Asamblare
# --------------------------------------------------------------------------- #
def build():
    criteria = load_criteria()
    models = load_models()
    scan_date, scan_name, scan = find_latest_scan()

    attach, carantina = build_join(models, scan)

    rows_ctx = []
    for row in models["modele"]:
        money = compute_money(row, attach.get(row["id"], []), criteria)
        prag_ok, prag_c = prag_truthy(row)
        rows_ctx.append({
            "row": row, "money": money,
            "_prag": prag_ok, "_prag_conf": prag_c,
            "_exclus": bool(row.get("EXCLUS_DIN_CATALOG")),
            "_nedeterminat": val(row.get("prag_dotari_atins")) is None,
        })

    universe, coverage = compute_scores(rows_ctx, criteria)

    out_models = []
    for c in rows_ctx:
        row, money = c["row"], c["money"]
        out_models.append({
            "id": row["id"],
            "marca": row.get("marca"),
            "model": row.get("model"),
            "echipare_selectata": val(row.get("echipare_selectata")),
            "propulsie": row.get("propulsie"),
            "motorizare": row.get("motorizare"),
            "cutie": val(row.get("cutie")),
            "tractiune": val(row.get("tractiune")),
            "lungime_mm": val(row.get("lungime_mm")),
            "putere_cp": val(row.get("putere_cp")),
            "cuplu_termic_nm": val(row.get("cuplu_termic_nm")),
            "cuplu_electric_nm": row.get("cuplu_electric_nm"),
            "garantie_ani": val(row.get("garantie_ani")),
            "garantie_km": row.get("garantie_km"),
            "marca_origine": row.get("marca_origine"),
            "grup_proprietar": row.get("grup_proprietar"),
            "tara_asamblare": val(row.get("tara_asamblare")),
            "prag_dotari_atins": {"v": val(row.get("prag_dotari_atins")), "c": c["_prag_conf"]},
            "exclus_din_catalog": c["_exclus"],
            "motiv_excludere": row.get("motiv_excludere"),
            "rand_nedeterminat": c["_nedeterminat"],
            "motiv_selectie": row.get("motiv_selectie"),
            "conflicte": collect_conflicts(row),
            "bani": money,
            "marcaje": {
                "in_buget": compute_in_buget(money, criteria),
                "rezidua_incerta": bool(row.get("rezidua_incerta")),
                "prag_dotari_atins": {"v": val(row.get("prag_dotari_atins")), "c": c["_prag_conf"]},
            },
            "componente_scor_brute": c.get("_brute"),  # pt. renormalizare in dashboard
            "scoruri": c.get("scoruri"),               # None daca nu e in universul de scor
        })

    total = len(rows_ctx)
    n_in_buget = sum(1 for c, om in zip(rows_ctx, out_models)
                     if c["_prag"] and not c["_exclus"]
                     and om["marcaje"]["in_buget"]["stare"] in ("da", "doar_cu_rabla"))

    out = {
        "schema_version": 1,
        "generat_la": date.today().isoformat(),
        "sursa_scan": scan_name,
        "scan_date": scan_date,
        "avertisment": "DERIVAT — niciodata editat manual. Regenerabil cu `python3 build.py`.",
        "antet_dashboard": (
            "Netul estimat NU e o oferta. E cea mai buna reconstituire a pretului public la "
            "data scanarii. Scorurile sunt normalizate pe lista curenta si NU sunt comparabile "
            "intre scanuri."
        ),
        "cheie_identitate": criteria["scan"]["observatii_pret"]["cheie_obligatorie"],
        "config": bake_config(criteria),
        "diagnostic": {
            "tco": tco_diagnostic(models, criteria),
            "univers_scor_n": len(universe),
            "acoperire_pondere_per_profil": coverage,
            "profiluri_slabe": {p: cov for p, cov in coverage.items() if cov < 0.5},
            "nota_scor": ("Multe componente de scor nu au date (TCO, consum, spatiu). Scorul "
                          "fiecarui profil e mediat DOAR pe ponderile cu date; `acoperire_pondere` "
                          "spune ce fractie din profil a avut date. Acoperire 0.20 = aproape "
                          "nesemnificativ."),
        },
        "atritie_baseline": {
            "univers_total": total,
            "exclus_din_catalog": sum(1 for c in rows_ctx if c["_exclus"]),
            "nedeterminate_prag_dotari": sum(1 for c in rows_ctx
                                             if c["_nedeterminat"] and not c["_exclus"]),
            "prag_dotari_atins": sum(1 for c in rows_ctx if c["_prag"] and not c["_exclus"]),
            "din_care_in_buget_incl_rabla": n_in_buget,
            "nota": "Randurile nedeterminate NU se claseaza (prag neconfirmat); raman in output "
                    "cu scoruri null. Referintele (peste buget) se claseaza dar sunt ascunse "
                    "implicit in dashboard.",
        },
        "modele": out_models,
        "carantina": carantina,
    }
    return out


def _json_default(o):
    # PyYAML parseaza datele calendaristice (ex. rabla.start/sfarsit) ca date/datetime.
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")


def render_dashboard(out):
    """Injecteaza latest.json in dashboard/template.html -> dashboard/index.html.

    Datele merg inline (nu fetch): pe file:// browserul blocheaza fetch prin CORS,
    deci fisierul trebuie sa mearga la dublu-click, oriunde, offline (HANDOFF §3).
    Escape `<` in JSON ca sa nu rupa `</script>` daca vreo valoare l-ar contine.
    Daca template.html lipseste, warning si mai departe -- nu crash.
    """
    if not os.path.exists(TEMPLATE_PATH):
        print(f"  (dashboard: {TEMPLATE_PATH} lipseste -- sarit)")
        return
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()
    payload = json.dumps(out, ensure_ascii=False, default=_json_default).replace("<", "\\u003c")
    if "__NCAR_DATA__" not in template:
        print("  (dashboard: marcajul __NCAR_DATA__ lipseste din template -- sarit)")
        return
    html = template.replace("__NCAR_DATA__", payload)
    with open(DASHBOARD_OUT, "w", encoding="utf-8") as f:
        f.write(html)
    with open(ROOT_INDEX, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK: {DASHBOARD_OUT} & {ROOT_INDEX} ({len(html)//1024} KB)")


def main():
    out = build()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=_json_default)
    render_dashboard(out)
    print(f"OK: {OUT_PATH}")
    print(f"  {len(out['modele'])} modele, {out['diagnostic']['univers_scor_n']} in universul de "
          f"scor, {len(out['carantina'])} observatii in carantina")
    print(f"  scan sursa: {out['sursa_scan']} ({out['scan_date']})")
    if out["diagnostic"]["profiluri_slabe"]:
        print(f"  profiluri slabe (acoperire<0.5): {out['diagnostic']['profiluri_slabe']}")


if __name__ == "__main__":
    main()
