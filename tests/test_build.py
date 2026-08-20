#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste pentru build.py — minimul cerut de HANDOFF §2, plus cateva invariante.

Ruleaza:  python3 -m pytest tests/ -q
      sau: python3 tests/test_build.py   (runner fara pytest)

Testele NU depind de continutul exact al scanului curent (care e append-only si
se schimba lunar); folosesc fixture-uri in-memory acolo unde verifica logica de
join/net, si citesc criteria.yaml doar pentru invariantele de contract.
"""

import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import build  # noqa: E402

CRITERIA = yaml.safe_load(open(os.path.join(ROOT, "spec", "criteria.yaml"), encoding="utf-8"))
BUILD_SRC = open(os.path.join(ROOT, "build.py"), encoding="utf-8").read()


# --------------------------------------------------------------------------- #
# 1. Suma ponderilor fiecarui profil = 1.00 (HANDOFF §2)
# --------------------------------------------------------------------------- #
def test_ponderile_fiecarui_profil_dau_unu():
    profiles = CRITERIA["scoring"]["profiles"]
    assert profiles, "niciun profil in criteria.scoring.profiles"
    for pname, weights in profiles.items():
        s = sum(w for w in weights.values() if isinstance(w, (int, float))
                and not isinstance(w, bool))
        assert abs(s - 1.0) < 1e-9, f"profil '{pname}': suma ponderilor = {s}, nu 1.00"


# --------------------------------------------------------------------------- #
# 2. Niciun prag din criteria.yaml nu apare hardcodat in build.py (grep in CI)
# --------------------------------------------------------------------------- #
def _threshold_values():
    """Praguri distinctive din criteria.yaml care NU au voie sa apara ca literal."""
    hf = CRITERIA["hard_filters"]
    b = CRITERIA["marcaje"]["buget"]
    r = CRITERIA["pret"]["rabla"]
    vals = set()
    vals.update(hf["lungime_mm"].values())            # 3900, 4450
    vals.update(hf["putere_cp"].values())             # 100, 200
    vals.update(b["tinta_eur"])                        # 20000, 25000
    vals.add(b["toleranta_pct"])                       # 8
    vals.update(CRITERIA["cuplu"]["interval_preferat_nm"])  # 200, 300
    vals.add(CRITERIA["tco"]["km_pe_an"])              # 14000
    for v in r["prima_eur"].values():                  # 1907, 2288
        vals.add(v)
    for k in ("prima_lei", "curs_ron_eur", "curs"):    # 10000/12000, 5.2442 (daca exista)
        node = r.get(k)
        if isinstance(node, dict):
            vals.update(node.values())
        elif node is not None:
            vals.add(node)
    return {v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)}


def _strip_strings_and_comments(src):
    """
    Un prag hardcodat apare ca token numeric in COD, nu in text. Scoatem
    docstring-urile, sirurile si comentariile ca sa nu dam fals-pozitiv pe numere
    care traiesc in nume de campuri ('consum_real_l100'), encoding ('utf-8') sau
    referinte din comentarii ('§8').
    """
    src = re.sub(r'""".*?"""', "", src, flags=re.S)
    src = re.sub(r"'''.*?'''", "", src, flags=re.S)
    src = re.sub(r'"(?:[^"\\]|\\.)*"', '""', src)      # siruri "..."
    src = re.sub(r"'(?:[^'\\]|\\.)*'", "''", src)      # siruri '...'
    lines = []
    for line in src.splitlines():
        if line.strip().startswith("#"):
            continue
        lines.append(line.split("#")[0])              # comentariu de la final de linie
    return "\n".join(lines)


def test_niciun_prag_hardcodat_in_build():
    code = _strip_strings_and_comments(BUILD_SRC)
    offenders = []
    for v in _threshold_values():
        lit = repr(v) if isinstance(v, float) else str(v)
        # numar ca token de sine statator (nu parte dintr-un numar mai mare)
        if re.search(rf"(?<![\d.]){re.escape(lit)}(?![\d.])", code):
            offenders.append(lit)
    assert not offenders, (
        f"praguri din criteria.yaml gasite hardcodate in build.py: {offenders}. "
        "Citeste-le din criteria, nu le duplica (HANDOFF §2, CLAUDE.md §3)."
    )


# --------------------------------------------------------------------------- #
# 3. O observatie cu cheie incompleta ajunge in carantina, nu in min()
# --------------------------------------------------------------------------- #
def _mini_models():
    return {"modele": [{
        "id": "test_x",
        "marca": "Suzuki", "model": "Vitara",
        "motorizare": "1.4 BoosterJet MHEV",
        "propulsie": "mhev_48v",
        "cutie": "manuala_6",
        "tractiune": "2wd",
        "echipare_selectata": {"v": "Passion"},
        "prag_dotari_atins": True,
        "garantie_ani": 3,
        "cuplu_termic_nm": {"v": 235},
    }]}


def test_cheie_incompleta_merge_in_carantina():
    scan = {"observatii_pret": [
        # echipare lipsa -> cheie de identitate rupta -> carantina
        {"model": "Suzuki Vitara", "echipare": None, "motorizare": "1.4 MHEV",
         "tip_pret": "lista", "pret_eur": 12000, "confidence": "estimated"},
        # placeholder explicit -> carantina
        {"model": "Suzuki Vitara", "echipare": "necunoscuta (probabil Cool)",
         "motorizare": "1.4 MHEV", "tip_pret": "lista", "pret_eur": 11500},
    ]}
    attach, carantina = build.build_join(_mini_models(), scan)
    assert attach["test_x"] == [], "obs cu cheie incompleta NU trebuie atasata randului"
    assert len(carantina) == 2, "ambele obs incomplete trebuie in carantina"
    # si nu contamineaza pretul
    money = build.compute_money(_mini_models()["modele"][0], attach["test_x"], CRITERIA)
    assert money["pret_lista"] is None, "pretul nu se ia dintr-o obs carantinata (anti-min naiv)"


# --------------------------------------------------------------------------- #
# 4. Doua reduceri de casare nu se insumeaza niciodata (D-021)
# --------------------------------------------------------------------------- #
def test_rabla_nu_se_cumuleaza():
    row = _mini_models()["modele"][0]  # propulsie mhev_48v
    obs = [{"model": "Suzuki Vitara", "echipare": "Passion", "motorizare": "1.4 MHEV",
            "cutie": "manuala", "tip_pret": "lista", "pret_eur": 22360, "confidence": "confirmed"}]
    money = build.compute_money(row, obs, CRITERIA)
    prima = money["prima_rabla"]["v"]
    lista = money["pret_lista"]["v"]
    net = money["pret_net_estimat"]["v"]
    # o singura prima, scazuta o singura data
    assert net == lista - prima, "netul trebuie sa scada EXACT o prima de casare, nu doua"
    grid = CRITERIA["pret"]["rabla"]["prima_eur"]
    assert prima == grid["hibrid_non_plugin"], "mhev se incadreaza pe grila hibrid, o singura valoare"
    assert prima != grid["hibrid_non_plugin"] * 2, "prima nu poate fi dublata"


# --------------------------------------------------------------------------- #
# 5. O reducere conditionata de finantare nu intra in pret_net_estimat
# --------------------------------------------------------------------------- #
def test_reducerea_captiva_nu_intra_in_net():
    row = {"id": "t", "marca": "Volkswagen", "model": "T-Cross",
           "motorizare": "1.0 TSI", "propulsie": "benzina",
           "cutie": "manuala", "tractiune": "2wd",
           "echipare_selectata": {"v": "Life"}, "prag_dotari_atins": True}
    obs = [
        {"model": "VW T-Cross", "echipare": "Life", "motorizare": "1.0 TSI",
         "tip_pret": "lista", "pret_eur": 24309, "confidence": "confirmed"},
        {"model": "VW T-Cross", "echipare": "Life", "motorizare": "1.0 TSI",
         "tip_pret": "net_promotional", "pret_eur": 22800, "EXCLUS_DIN_NET": True,
         "motiv_excludere": "finantare captiva obligatorie", "confidence": "confirmed"},
    ]
    money = build.compute_money(row, obs, CRITERIA)
    net = money["pret_net_estimat"]["v"]
    lista = money["pret_lista"]["v"]
    prima = money["prima_rabla"]["v"]
    # netul se deriva DOAR din lista si Rabla; promoul captiv (22800) nu intra nicaieri
    # in lantul de derivare. (Rabla singura poate cobori sub 22800 — asta e legitim;
    # invariantul real e ca baza pre-Rabla ramane lista, nescoborata de promoul captiv.)
    assert money["pret_net_fara_rabla"]["v"] == lista, \
        "netul pre-Rabla nu trebuie sa includa reducerea captiva"
    assert net == lista - prima, "netul = lista - Rabla, fara reducerea captiva"
    # dar promoul captiv e pastrat pe linie separata, ca 'cost mutat'
    assert any(r["pret_promo_eur"] == 22800 for r in money["reduceri_conditionate"]), \
        "reducerea captiva trebuie pastrata ca linie separata, nu topita in net"


# --------------------------------------------------------------------------- #
# 6. Invariante suplimentare (nu in minimul HANDOFF, dar ieftine si utile)
# --------------------------------------------------------------------------- #
def test_dispersie_null_sub_doua_observatii():
    row = _mini_models()["modele"][0]
    obs = [{"model": "Suzuki Vitara", "echipare": "Passion", "motorizare": "1.4 MHEV",
            "cutie": "manuala", "tractiune": "2wd", "tip_pret": "lista", "pret_eur": 22360}]
    money = build.compute_money(row, obs, CRITERIA)
    assert money["dispersie_dealeri_eur"] is None, "o singura obs => dispersie null, nu 0 (D-020)"


def test_dispersie_calculata_pe_cheie_completa():
    row = _mini_models()["modele"][0]  # catalog: cutie manuala, tractiune 2wd
    # doua obs, acelasi trim/motor/tip, dealeri diferiti, drivetrain mostenit din catalog
    obs = [
        {"model": "Suzuki Vitara", "echipare": "Passion", "motorizare": "1.4 MHEV",
         "tip_pret": "lista", "pret_eur": 22360, "confidence": "confirmed"},
        {"model": "Suzuki Vitara", "echipare": "Passion", "motorizare": "1.4 MHEV",
         "tip_pret": "lista", "pret_eur": 22900, "confidence": "confirmed"},
    ]
    money = build.compute_money(row, obs, CRITERIA)
    assert money["dispersie_dealeri_eur"] == 540, "dispersia = max-min pe aceeasi cheie completa"


def test_output_construibil_end_to_end():
    out = build.build()
    assert out["modele"], "build() trebuie sa produca modele"
    assert "carantina" in out
    # scorurile nu se prezinta ca fiind comparabile intre scanuri
    for m in out["modele"]:
        if m["rand_nedeterminat"]:
            assert m["scoruri"] is None, f"{m['model']}: rand nedeterminat nu se claseaza"


def test_tco_calculat_corect():
    out = build.build()
    assert out["diagnostic"]["tco"]["tco_calculabil"] is True, "TCO trebuie sa fie calculabil"
    
    total_km = CRITERIA["tco"].get("total_km") or (CRITERIA["tco"]["km_pe_an"] * CRITERIA["tco"]["orizont_ani"])
    
    # Verifica calculul TCO pe un model concret calificat (ex. Vitara sau Yaris Cross)
    calificate_cu_tco = [m for m in out["modele"] if m["bani"]["cost_total_5_ani"] is not None]
    assert len(calificate_cu_tco) > 0, "trebuie sa existe modele cu TCO calculat"
    
    for m in calificate_cu_tco:
        tco = m["bani"]["cost_total_5_ani"]["v"]
        cost_km = m["bani"]["cost_pe_km"]["v"]
        assert tco > 0, f"{m['model']}: TCO trebuie sa fie pozitiv"
        assert cost_km > 0, f"{m['model']}: cost_pe_km trebuie sa fie pozitiv"
        assert abs(cost_km - tco / float(total_km)) < 0.01, f"{m['model']}: cost_pe_km inconsistent cu TCO"


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
