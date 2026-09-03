#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste pentru contractul de scan — D-031.

Inchid datoria lasata deschisa la aplicarea D-031: YAML-ul declara regula, dar
nimic nu o impunea. Aici se impune, pe trei niveluri:

  1. FORMA SPECIFICATIEI — criteria.yaml declara fereastra; sources.yaml nu
     duplica pragul si cere galetile in antet. Prinde regresia de contract.
  2. LOGICA VALIDATORULUI — build.normalize_delta / build.verifica_acoperire
     verificate pe fixture-uri, deci corecte inainte sa existe un scan real.
  3. SCANURILE REALE — invariantul aplicat scanurilor de dupa data-limita.
     Cele anterioare sunt exceptate explicit: istoricul e append-only
     (CLAUDE.md §2) si nu se retrofiteaza.

Ruleaza:  python3 -m pytest tests/ -q
      sau: python3 tests/test_scan_contract.py
"""

import datetime
import glob
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import build  # noqa: E402

CRITERIA = yaml.safe_load(open(os.path.join(ROOT, "spec", "criteria.yaml"), encoding="utf-8"))
SOURCES = yaml.safe_load(open(os.path.join(ROOT, "spec", "sources.yaml"), encoding="utf-8"))
SOURCES_SRC = open(os.path.join(ROOT, "spec", "sources.yaml"), encoding="utf-8").read()
PROC = SOURCES["procedura_scan_lunar"]

# Data de la care antetul nou devine obligatoriu (declarata in spec, nu aici).
_LIMITA = re.search(r"scan_date > (\d{4}-\d{2}-\d{2})",
                    PROC["invariant_acoperire"]["se_aplica_de_la"])


# --------------------------------------------------------------------------- #
# 1. Forma specificatiei
# --------------------------------------------------------------------------- #
def test_criteria_declara_fereastra_langa_prag():
    scan = CRITERIA["scan"]
    assert "prag_alerta_variatie_pret_pct" in scan
    assert "fereastra_referinta_zile" in scan, \
        "pragul fara fereastra e definit 'pe lună' prin presupunere (D-031)"
    assert scan["fereastra_referinta_zile"] > 0


def test_pragul_nu_e_duplicat_ca_valoare_in_sources():
    """
    CLAUDE.md §3: un prag scris in doua locuri devine, in sase luni, doua praguri.
    Prima redactare a patch-ului chiar il copia — de aici testul.
    sources.yaml are voie sa CITEZE calea, nu valoarea.
    """
    prag = CRITERIA["scan"]["prag_alerta_variatie_pret_pct"]
    fereastra = CRITERIA["scan"]["fereastra_referinta_zile"]
    # cauta valoarea ca numar dupa un ':' sau '(' — adica folosita ca valoare
    for nume, v in (("prag", prag), ("fereastra", fereastra)):
        rau = re.findall(rf"^\s*\w*(?:prag|fereastra)\w*\s*:\s*{re.escape(str(v))}\s*$",
                         SOURCES_SRC, re.M)
        assert not rau, (f"{nume} ({v}) e redeclarat ca valoare in sources.yaml: "
                         f"{rau}. Citeaza calea din criteria.yaml, nu valoarea.")
    assert "scan.prag_alerta_variatie_pret_pct" in SOURCES_SRC, \
        "sources.yaml trebuie sa refere pragul prin cale"


def test_antetul_cere_toate_cele_cinci_galeti():
    antet = PROC["antet_obligatoriu"]
    for camp in ("scan_date", "previous_scan", "interval_zile", "sources_failed",
                 "carantina", "fara_oferta", "excluse_din_catalog", "status"):
        assert camp in antet, f"'{camp}' lipseste din antet_obligatoriu (D-031)"


def test_sources_failed_poarta_modele_afectate():
    """
    Fara atribuire de model, gaeata `sources_failed` nu e adresabila: o intrare
    {url, motiv} nu spune ce model a ramas neverificat. Descoperit scriind testul.
    """
    assert "modele_afectate" in PROC["sources_failed_format"]["per_intrare"]


def test_la_esec_scrie_nu_refuza():
    """CLAUDE.md §1: un scan parţial marcat corect e mai valoros decat unul complet ghicit."""
    txt = PROC["invariant_acoperire"]["la_esec"].lower()
    assert "incomplet" in txt
    assert "nu refuza" in build._strip_diacritics(txt), \
        "la_esec nu trebuie sa ceara refuzul scrierii"


# --------------------------------------------------------------------------- #
# 2. Logica validatorului — pe fixture-uri
# --------------------------------------------------------------------------- #
def test_normalizarea_schimba_verdictul_pe_interval_scurt():
    """Cazul real care a declansat D-031: 3% pe 14 zile nu e 3% pe 30."""
    prag = CRITERIA["scan"]["prag_alerta_variatie_pret_pct"]
    d = build.normalize_delta(prag, 14, CRITERIA)
    assert d["normalizat_pct"] > prag, "3% pe 14 zile trebuie sa depaseasca pragul lunar"
    assert d["brut_peste_prag"] and d["normalizat_peste_prag"]

    # sub prag brut, dar peste prag normalizat => exact capcana pe care o inchide D-031
    d2 = build.normalize_delta(prag - 1.5, 7, CRITERIA)
    assert d2["brut_peste_prag"] is False
    assert d2["normalizat_peste_prag"] is True
    assert d2["nota"] and "ambele" in d2["nota"], \
        "cand cele doua cad pe laturi diferite ale pragului, nota trebuie sa o spuna"


def test_normalizarea_pe_fereastra_exacta_e_identitate():
    fereastra = CRITERIA["scan"]["fereastra_referinta_zile"]
    d = build.normalize_delta(4.0, fereastra, CRITERIA)
    assert d["normalizat_pct"] == 4.0, "pe fereastra de referinta, normalizarea nu schimba nimic"


def test_interval_necunoscut_da_null_nu_valoare_plauzibila():
    """CLAUDE.md §8.1 — un camp necunoscut e null, nu o cifra plauzibila."""
    for interval in (None, 0, -3):
        d = build.normalize_delta(5.0, interval, CRITERIA)
        assert d["normalizat_pct"] is None, f"interval={interval} nu trebuie sa produca o cifra"
        assert d["nota"], "absenta trebuie explicata, nu lasata goala"
    # primul scan din serie: previous_scan null => interval null, si e legitim
    assert build.normalize_delta(None, None, CRITERIA)["normalizat_pct"] is None


def _models_fixture():
    return {"modele": [
        {"id": "a_activ", "marca": "Suzuki", "model": "Vitara",
         "motorizare": "1.4 MHEV", "cutie": "manuala_6", "tractiune": "2wd",
         "echipare_selectata": {"v": "Passion"}, "prag_dotari_atins": True},
        {"id": "b_fara_oferta", "marca": "Suzuki", "model": "S-Cross",
         "motorizare": "1.4 MHEV", "cutie": "manuala_6", "tractiune": "4wd",
         "echipare_selectata": {"v": "Passion"}, "prag_dotari_atins": True},
        {"id": "c_sursa_moarta", "marca": "Nissan", "model": "Juke",
         "motorizare": "1.0 DIG-T", "cutie": "manuala_6", "tractiune": "2wd",
         "echipare_selectata": {"v": "Acenta"}, "prag_dotari_atins": True},
        {"id": "d_exclus", "marca": "Dacia", "model": "Sandero Stepway",
         "motorizare": "1.0 TCe", "cutie": "manuala_6", "tractiune": "2wd",
         "echipare_selectata": {"v": "Expression"}, "prag_dotari_atins": True,
         "EXCLUS_DIN_CATALOG": True},
    ]}


def _scan_complet():
    return {
        "scan_date": "2026-10-01", "previous_scan": "scan-2026-09-15.json",
        "interval_zile": 16,
        "observatii_pret": [
            {"model": "Suzuki Vitara", "echipare": "Passion", "motorizare": "1.4 MHEV",
             "cutie": "manuala", "tractiune": "2wd", "tip_pret": "lista",
             "pret_eur": 22360, "confidence": "confirmed"},
        ],
        "sources_failed": [{"url": "https://vanzari.nissan.ro", "motiv": "timeout",
                            "modele_afectate": ["c_sursa_moarta"]}],
        "fara_oferta": [{"model_id": "b_fara_oferta", "surse_incercate": ["x"],
                         "interpretare": "retras din oferta"}],
        "carantina": [],
    }


def test_acoperire_completa_trece():
    r = build.verifica_acoperire(_models_fixture(), _scan_complet())
    assert r["status"] == "complet", f"neatribuite={r['neatribuite']} suprapuneri={r['suprapuneri']}"
    assert r["per_galeata"]["comparate"] == 1
    assert r["per_galeata"]["excluse_din_catalog"] == 1


def test_modelul_exclus_nu_invalideaza_scanul():
    """
    Defectul prinsului la verificare: cu patru galeti, Sandero Stepway
    (EXCLUS_DIN_CATALOG, D-030) n-ar fi aparut in niciuna => orice scan invalid.
    """
    models, scan = _models_fixture(), _scan_complet()
    assert any(m.get("EXCLUS_DIN_CATALOG") for m in models["modele"]), "fixture-ul isi pierde sensul"
    r = build.verifica_acoperire(models, scan)
    assert "d_exclus" not in r["neatribuite"], \
        "un model exclus manual nu e o gaura de acoperire (D-030)"


def test_absenta_tacita_e_prinsa():
    scan = _scan_complet()
    scan["fara_oferta"] = []          # b_fara_oferta nu mai e explicat nicaieri
    r = build.verifica_acoperire(_models_fixture(), scan)
    assert r["status"] == "incomplet"
    assert r["neatribuite"] == ["b_fara_oferta"], \
        "modelul neexplicat trebuie numit, nu doar numarat"


def test_sources_failed_fara_modele_afectate_lasa_gaura():
    """Formatul vechi {url, motiv} nu acopera modelul — de aici obligativitatea."""
    scan = _scan_complet()
    scan["sources_failed"] = [{"url": "https://vanzari.nissan.ro", "motiv": "timeout"}]
    r = build.verifica_acoperire(_models_fixture(), scan)
    assert "c_sursa_moarta" in r["neatribuite"]


def test_doua_explicatii_pentru_acelasi_gol_sunt_eroare():
    """'Exact una' se incalca si prin suprapunere, nu doar prin gaura."""
    scan = _scan_complet()
    scan["fara_oferta"].append({"model_id": "c_sursa_moarta", "surse_incercate": [],
                                "interpretare": "necunoscut"})
    r = build.verifica_acoperire(_models_fixture(), scan)
    assert r["status"] == "incomplet"
    assert any(s["model_id"] == "c_sursa_moarta" for s in r["suprapuneri"])


def test_id_inexistent_in_catalog_e_semnalat():
    scan = _scan_complet()
    scan["fara_oferta"].append({"model_id": "model_care_nu_exista", "surse_incercate": []})
    r = build.verifica_acoperire(_models_fixture(), scan)
    assert "model_care_nu_exista" in r["id_necunoscute_in_catalog"]


# --------------------------------------------------------------------------- #
# 3. Scanurile reale
# --------------------------------------------------------------------------- #
def _scanuri_supuse_contractului():
    assert _LIMITA, "se_aplica_de_la trebuie sa poarte o data parsabila"
    limita = datetime.date.fromisoformat(_LIMITA.group(1))
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "scans", "scan-*.json"))):
        m = re.search(r"scan-(\d{4}-\d{2}-\d{2})", os.path.basename(p))
        if m and datetime.date.fromisoformat(m.group(1)) > limita:
            out.append(p)
    return out


def verifica_un_scan(scan, nume, models):
    """
    Verificarea completa a unui scan supus contractului. Extrasa ca functie
    pentru ca testul de mai jos e VID pana la primul scan nou — iar un test
    armat si niciodata executat putrezeste netestat. `test_verificatorul_...`
    o executa acum, pe un scan sintetic.
    """
    for camp in PROC["antet_obligatoriu"]:
        assert camp in scan, f"{nume}: lipseste '{camp}' din antet (D-031)"
    # interval_zile CALCULAT, nu declarat pe incredere
    if scan.get("previous_scan"):
        prev = re.search(r"(\d{4}-\d{2}-\d{2})", scan["previous_scan"]).group(1)
        asteptat = (datetime.date.fromisoformat(scan["scan_date"])
                    - datetime.date.fromisoformat(prev)).days
        assert scan["interval_zile"] == asteptat, \
            f"{nume}: interval_zile={scan['interval_zile']}, calculat={asteptat}"
    r = build.verifica_acoperire(models, scan)
    assert scan["status"] == r["status"], \
        f"{nume}: antetul declara status={scan['status']}, verificarea da {r['status']}"
    if r["status"] == "incomplet":
        assert scan.get("note"), f"{nume}: scan incomplet fara modelele neatribuite in note"
    return r


def test_scanurile_noi_respecta_antetul_si_invariantul():
    """
    Vid deocamdata (niciun scan dupa data-limita) si asta e corect: testul e
    ARMAT pentru scanul urmator. Scanurile 08-19/08-20 nu se retrofiteaza.
    """
    models = build.load_models()
    for p in _scanuri_supuse_contractului():
        verifica_un_scan(json.load(open(p, encoding="utf-8")), os.path.basename(p), models)


def _scan_sintetic_pentru_catalogul_real(models):
    """
    Un scan minim VALID pentru catalogul real: nicio observatie, deci fiecare
    model neexclus e declarat `fara_oferta`. Artificial, dar exact forma pe care
    contractul o cere — si singura care nu depinde de ce e in oferta luna asta.
    """
    activi = [m["id"] for m in models["modele"] if not m.get("EXCLUS_DIN_CATALOG")]
    return {
        "scan_date": "2099-01-31", "previous_scan": "scan-2099-01-01.json",
        "interval_zile": 30, "sources_checked": 0, "models_found": 0,
        "sources_failed": [], "carantina": [], "observatii_pret": [],
        "fara_oferta": [{"model_id": i, "surse_incercate": [],
                         "interpretare": "necunoscut"} for i in activi],
        "excluse_din_catalog": [], "status": "complet", "note": [],
    }


def test_verificatorul_pe_scan_sintetic_dupa_limita():
    """Executa DRUMUL armat, ca sa nu treaca doar pentru ca lista e goala."""
    models = build.load_models()
    scan = _scan_sintetic_pentru_catalogul_real(models)
    r = verifica_un_scan(scan, "scan-sintetic", models)
    assert r["status"] == "complet"
    assert r["total_catalogate"] == len(models["modele"])

    import copy
    # 1. antet ciuntit => prins
    rau = copy.deepcopy(scan); rau.pop("interval_zile")
    try:
        verifica_un_scan(rau, "fara-interval", models); raise Exception("nu a prins")
    except AssertionError as e:
        assert "interval_zile" in str(e)

    # 2. interval declarat greşit => prins (01-01 -> 01-31 = 30, nu 7)
    rau = copy.deepcopy(scan); rau["interval_zile"] = 7
    try:
        verifica_un_scan(rau, "interval-fals", models); raise Exception("nu a prins")
    except AssertionError as e:
        assert "calculat=30" in str(e)

    # 3. status "complet" mincinos peste o gaura de acoperire => prins
    rau = copy.deepcopy(scan); rau["fara_oferta"].pop()
    try:
        verifica_un_scan(rau, "status-mincinos", models); raise Exception("nu a prins")
    except AssertionError as e:
        assert "verificarea da incomplet" in str(e)


def test_scanurile_istorice_nu_sunt_recalificate():
    """Istoricul e append-only (CLAUDE.md §2): contractul nou nu le condamna retroactiv."""
    toate = glob.glob(os.path.join(ROOT, "data", "scans", "scan-*.json"))
    assert toate, "trebuie sa existe cel putin un scan"
    supuse = set(_scanuri_supuse_contractului())
    for p in toate:
        if p in supuse:
            continue
        scan = json.load(open(p, encoding="utf-8"))
        # cerintele care erau in vigoare la momentul lor (CLAUDE.md §4.3)
        for camp in ("scan_date", "sources_failed", "models_found"):
            assert camp in scan, f"{os.path.basename(p)}: {camp} era obligatoriu si atunci"


# --------------------------------------------------------------------------- #
# Runner fara pytest
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} teste trecute")
    sys.exit(1 if failed else 0)
