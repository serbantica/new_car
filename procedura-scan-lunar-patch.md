# Patch pentru `procedura_scan_lunar` — verificat 2026-09-03

**Status: APLICAT 2026-09-03 — vezi D-031.**
Verificat față de starea reală a repo-ului (ultimul scan: `scan-2026-08-20.json`).
Ambele patch-uri au intrat în `spec/`; `sources.yaml` a trecut la `version: 3`.
Acest fișier rămâne ca urmă a raționamentului — contractul viu e în `spec/`.

Două adăugiri. Prima vine din rularea ratată (intervalul dintre scanuri nu e
garantat o lună). A doua vine din întrebarea despre Vitara 4x4: un model poate
lipsi din tabel din patru motive complet diferite, iar în forma actuală toate
arată identic — adică a lipsi.

---

## 0. Ce s-a corectat la verificare

Revizia dinainte avea trei defecte față de contractele existente. Toate trei
sunt corectate mai jos; le las scrise pentru ca motivul să rămână vizibil.

| # | Defect | Corecție |
|---|---|---|
| 1 | `prag_miscare_pct: 3.0` în `sources.yaml` **duplica** pragul existent din `spec/criteria.yaml:532` (`scan.prag_alerta_variatie_pret_pct: 3`) — exact ce interzice CLAUDE.md §3 | Pragul rămâne unde e. În `criteria.yaml` se adaugă **doar** fereastra de referință, lângă el. `sources.yaml` îl citează, nu îl redeclară. |
| 2 | `carantina` era prezentată ca adăugire nouă. **Există deja**: `criteria.yaml:554`, D-020, D-024, implementat în `build.py:233-282`, emis în `latest.json` (`build.py:866`) | Contribuția reală e alta: `carantina` devine **câmp declarat în antetul scanului**, nu doar derivat de `build.py`. Reformulat ca atare. |
| 3 | Invariantul cerea reuniune = `models.json`, deci **orice scan viitor ar fi invalid**: Dacia Sandero Stepway are `EXCLUS_DIN_CATALOG: true` (D-030) și nu va apărea niciodată în cele patru găleți | Adăugată a cincea găleată: `excluse_din_catalog`. 29 catalogate − 1 exclus = 28 de atribuit. |

Confirmat, nu presupus: intervalul de la ultimul scan la azi este **14 zile**, nu
30. O mișcare brută de 3% pe acest interval este 6,43% normalizat la 30 de zile —
peste prag de două ori. Premisa patch-ului se verifică pe date reale.

---

## 1. Intervalul se calculează, nu se presupune

Pragul de 3% (`criteria.yaml:532`) e definit implicit „pe lună", iar
`scan.cadenta: lunara` întărește presupunerea. Dacă un scan se ratează, sau se
rulează manual mai devreme/mai târziu, aceeași cifră brută înseamnă altceva.
Antetul trebuie să poarte intervalul real, iar `history/` să raporteze ambele
valori — bruta și cea normalizată — ca orice citire ulterioară să poată
recalcula fără să ghicească cadența.

## 2. Invariantul de acoperire

Regula care contează, exprimată ca verificare, nu ca intenție:

> Fiecare model din `models.json` apare în **exact una** dintre:
> tabelul de comparație, `carantina`, `sources_failed`, `fara_oferta`,
> `excluse_din_catalog`. Reuniunea lor este `models.json`.
> Absența tăcută este eroare de scan, nu rezultat de scan.

Asta face diferența dintre „Vitara AllGrip nu se mai vinde", „suzuki.ro n-a
răspuns", „am găsit preț dar fără cutie în cheie, deci n-am putut compara" și
„Serban a scos modelul din catalog" — patru stări care azi produc același gol
în tabel.

**Se aplică începând cu scanul următor.** Cele două scanuri existente
(`scan-2026-08-19`, `scan-2026-08-20`) nu au câmpurile noi în antet, iar
istoricul e append-only (CLAUDE.md §2) — nu se retrofitează și nu se
recalifică retroactiv drept invalide.

## 3. Ce NU e nou aici

`carantina` este deja politica proiectului, nu o propunere:

- `spec/criteria.yaml:554` — `observatie_cu_cheie_incompleta: carantina`
- `spec/criteria.yaml:550` — `cheie_obligatorie: [model_year, echipare, motorizare, cutie, tractiune]`
- D-020, D-024 — motivul statistic (un `min()` naiv selectează listingul cel mai puțin specificat)
- `build.py:233-282` — implementarea; `build.py:866` — emis în `latest.json`

Ce lipsește și se adaugă: scanul **nu declară** carantina, o lasă pe `build.py`
să o deducă. Un scan care nu-și declară propriile observații necomparabile nu
poate fi verificat împotriva invariantului de la §2 fără să ruleze build-ul.

---

## YAML de inserat — patch 1/2: `spec/criteria.yaml`

În blocul `scan:`, **imediat sub** `prag_alerta_variatie_pret_pct` (linia 532).
Pragul nu se mută și nu se duplică; primește doar unitatea care-i lipsea.

```yaml
  prag_alerta_variatie_pret_pct: 3     # sub asta nu se raportează ca schimbare
  fereastra_referinta_zile: 30
  # Pragul de mai sus este definit PE 30 DE ZILE. Fără această fereastră,
  # aceeaşi cifră brută înseamnă altceva la fiecare interval real de scan
  # (2026-08-20 → 2026-09-03 = 14 zile, nu 30). history/ raportează mişcarea
  # brută ŞI pe cea normalizată — pct * 30 / interval_zile — spunând explicit
  # care dintre ele a trecut pragul şi pe ce interval.
```

## YAML de inserat — patch 2/2: `spec/sources.yaml` → `procedura_scan_lunar`

```yaml
procedura_scan_lunar:

  antet_obligatoriu:
    - scan_date            # data de azi, din ceas, nu din cadenţă
    - previous_scan        # max(data) din data/scans/; null la primul scan
    - interval_zile        # scan_date - previous_scan, CALCULAT
    - sources_checked      # deja prezent; se păstrează
    - sources_failed       # deja obligatoriu (CLAUDE.md §4.3); se păstrează
    - models_found         # deja prezent; se păstrează
    - carantina            # observaţii cu cheie incompletă — DECLARATE de scan,
                           # nu doar deduse de build.py (vezi §3)
    - fara_oferta          # model căutat, sursă vie, model absent din ofertă
    - excluse_din_catalog  # EXCLUS_DIN_CATALOG: true în models.json (D-030)
    - status               # "complet" | "incomplet" — vezi invariant_acoperire
    - note

  normalizare_delta:
    prag: "spec/criteria.yaml → scan.prag_alerta_variatie_pret_pct"
    fereastra: "spec/criteria.yaml → scan.fereastra_referinta_zile"
    # Valorile NU se repetă aici. CLAUDE.md §3: un prag scris în două locuri
    # devine, în şase luni, două praguri diferite.
    regula: >
      Raportează în history/ mişcarea brută ŞI cea normalizată la fereastra
      de referinţă (pct * fereastra / interval_zile), spunând explicit care
      dintre ele a trecut pragul şi pe ce interval.
      Nu presupune niciodată că intervalul este o lună.

  invariant_acoperire:
    regula: >
      Fiecare intrare din models.json trebuie să apară în exact una dintre:
      tabelul de comparaţie, carantina, sources_failed, fara_oferta,
      excluse_din_catalog. Verifică reuniunea ÎNAINTE de a scrie fişierul.
    la_esec: >
      Scrie fişierul cu status: "incomplet" în antet şi enumeră modelele
      neatribuite în note. Un scan incomplet declarat este utilizabil;
      unul tăcut nu este. NU refuza să scrii — CLAUDE.md §1: o scanare
      parţială marcată corect ca parţială e mai valoroasă decât una
      completă obţinută prin ghiceli.
    se_aplica_de_la: scan-2026-09-XX   # primul scan de după acest patch
    # Scanurile 2026-08-19 şi 2026-08-20 nu au câmpurile noi. Istoricul e
    # append-only (CLAUDE.md §2) — nu se retrofitează.

  carantina_format:
    per_intrare:
      - model_id
      - source_url
      - observed_at
      - chei_lipsa        # subset din criteria.yaml → observatii_pret.cheie_obligatorie
      - valoare_observata # se păstrează, dar NU intră în minim/comparaţie
    compatibilitate: >
      build.py:233-282 citeşte deja flagurile `carantina: true` +
      `motiv_carantina` de pe observaţie (format folosit în
      scan-2026-08-19.json:95). Antetul `carantina[]` se ADAUGĂ, nu
      înlocuieşte — altfel join-ul existent se rupe.

  fara_oferta_format:
    per_intrare:
      - model_id
      - surse_incercate   # URL-urile citite cu succes care nu conţin modelul
      - observed_at
      - interpretare      # "retras din ofertă" | "indisponibil temporar" | "necunoscut"
    # Distincţia faţă de sources_failed: acolo sursa n-a răspuns. Aici sursa a
    # răspuns şi modelul nu era în ea. Prima e o gaură de acoperire, a doua e
    # un fapt de piaţă — posibil cel mai valoros semnal dintr-un scan.
```

---

## Gap separat, descoperit la verificare

`history/` este **gol** — zero fișiere, deși există două scanuri. CLAUDE.md §9
pasul 6 cere `history/history-<azi>.md` la fiecare rulare, și §9 spune explicit
că „pasul 6 este cel care dă valoare seriei".

Patch-ul de mai sus presupune că `history/` raportează delta normalizată. Acea
presupunere nu are pe ce să se aplice deocamdată. Nu inventez conținutul
retroactiv (CLAUDE.md §8.1); îl semnalez ca datorie: la primul scan de după
acest patch, `history/` trebuie scris, iar delta `2026-08-19 → 2026-08-20`
rămâne nedocumentată sau se reconstruiește explicit din cele două fișiere
existente, marcată ca reconstrucție.

## Stare finală, după aplicare

- Ambele patch-uri au intrat în `spec/`, cu D-031 în `DECISIONS.md`.
- **A treia adăugire, descoperită scriind testul:** `sources_failed_format` cu
  `modele_afectate` obligatoriu. Fără el, găleata `sources_failed` nu era
  adresabilă și invariantul rămânea neverificabil pe una din cinci găleți.
- Impunerea există: `build.normalize_delta`, `build.verifica_acoperire`,
  `tests/test_scan_contract.py` (16 teste, 26 în total pe repo).
- **Ce nu e automat:** `build()` nu apelează validatorul. Nimic nu blochează
  scrierea unui scan invalid în `data/scans/` — agentul de scan trebuie să
  cheme `verifica_acoperire` la pasul 4 din ritualul CLAUDE.md §9.
