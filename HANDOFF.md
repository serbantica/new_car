# HANDOFF — continuarea lucrului în IDE

Document de predare pentru o sesiune Claude Code care preia proiectul NEW_CAR
într-un IDE, local. Scris ca instrucțiune de sine stătătoare: sesiunea care îl
citește nu are memoria conversației în care a fost construit proiectul.

**Data predării:** 2026-08-19

---

## 0. Citește întâi

În ordinea asta, înainte de orice:

1. `CLAUDE.md` — constituția proiectului. Are precedență asupra oricărei
   preferințe de implementare.
2. `DECISIONS.md` — 23 de decizii, cu motivul fiecăreia. Multe sunt
   contraintuitive și au fost plătite cu erori reale. Nu le reface.
3. `spec/criteria.yaml` — filtrele, profilele de ponderi, cheile de interogare.
   **Sursă unică de adevăr. Nu duplica niciun prag în cod.**
4. `spec/query.md` — ce e o întrebare validă și cum se răspunde la ea.
5. `spec/price-model.md` — formula netului, taxonomia reducerilor.
6. `spec/sources.yaml` — 53 de surse validate, 31 de fundături, procedura de scan.

---

## 1. Unde e proiectul acum

```
NEW_CAR/
├── CLAUDE.md                       ✅ complet
├── DECISIONS.md                    ✅ 23 de decizii
├── PROJECT_INSTRUCTIONS.md         ✅ (pentru câmpul de proiect din app)
├── HANDOFF.md                      ✅ acest fișier
├── spec/
│   ├── criteria.yaml               ✅ complet
│   ├── query.md                    ✅ complet
│   ├── price-model.md              ✅ complet
│   └── sources.yaml                ✅ populat 2026-08-19
├── data/
│   ├── models.json                 ✅ 20 rânduri (toate cele 6 modele din Task 3 verificate)
│   ├── shortlist-2026-08-19.md     ✅ listă scurtă provizorie, 29 modele
│   ├── candidates.md               ✅ lista lungă (ipoteză neverificată)
│   ├── latest.json                 ✅ derivat (Task 1 + Task 3, build.py) — 20 modele
│   └── scans/
│       └── scan-2026-08-19.json    ✅ 22 observații de preț
├── history/                        ❌ gol
├── build.py                        ✅ Task 1 — latest.json + dashboard/index.html
├── tests/test_build.py             ✅ 8 teste trec
└── dashboard/                      ✅ Task 2 — template.html + index.html (236 KB)
```

> **Actualizare 2026-08-20 (sesiune IDE):** Task 1, Task 2 și **Task 3** sunt **gata**.
> Toate cele 6 modele rămase (Suzuki S-Cross, SEAT Arona, VW T-Cross, VW Taigo,
> Opel Mokka, Opel Frontera, Citroën C3 Aircross) au fost verificate pe matricea
> de 7 dotări minime și catalogate în `data/models.json` (vezi D-027).
> `build.py` a regenerat `data/latest.json` și `dashboard/index.html` (20 de modele).
> Toate cele 8 teste trec.

Există și o **sarcină programată lunară** (1 ale lunii, 09:00 EEST) care rulează
scanul de prețuri într-o sesiune cloud separată și scrie în `data/scans/`.
Nu o dubla din IDE.

---

## 2. Sarcina 1 — scriptul de build (`data/latest.json`)

**Asta e prima. Fără ea, dashboard-ul n-are ce citi.**

Scrie `build.py` (sau `build.mjs`) care produce `data/latest.json` din:

```
models.json  (catalog tehnic, stabil)
     +
scans/scan-<max(data)>.json  (observații de preț, volatile)
     +
criteria.yaml  (praguri, ponderi, parametri TCO)
     ↓
latest.json  (derivat — NICIODATĂ editat manual)
```

### Ce calculează

**Join pe cheia de identitate:** `model_year|echipare|motorizare|cutie|tractiune`.
O observație de preț a cărei cheie nu se potrivește cu niciun rând din catalog
merge în `carantina[]`, nu se atașează forțat.

**Cele patru coloane de bani** (`spec/price-model.md`):
- `pret_lista`
- `pret_net_estimat` = listă − discount necondiționat − Rabla
- `pret_net_fara_rabla`
- `cost_total_5_ani` (TCO)
- `cost_pe_km` = TCO / (km_pe_an × 5)

**Reducerile**, clasificate după valoare, nu după nume. Grila e în
`criteria.yaml → pret.rabla.prima_eur`. Reducerile de casare nu se cumulează:
se reține cea mai mare. Cele condiționate de finanțare captivă **nu intră în
net** — linie separată.

**Dispersia de dealer** doar în interiorul aceleiași chei complete. Sub două
observații pe aceeași cheie: `null`, nu `0`.

**Scorurile**, pentru fiecare profil din `criteria.yaml → scoring.profiles`,
normalizate min-max **pe lista filtrată curentă**. Consecință de scris în
output: scorurile nu sunt comparabile între scanuri; doar valorile brute sunt.

**Marcajele:** `in_buget`, `rezidua_incerta`, `prag_dotari_atins`.

### Ce blochează TCO-ul acum

`criteria.yaml → tco.pret_benzina_eur_l` este `null`. Fără el, `cost_total_5_ani`
și `cost_pe_km` nu se pot calcula. Două opțiuni, în ordinea preferinței:

1. Caută prețul mediu al benzinei în România și scrie-l în `criteria.yaml` cu
   data observării și sursa. E un singur fetch.
2. Dacă nu, lasă TCO `null` peste tot și fă dashboard-ul să sorteze implicit
   pe `pret_net_estimat`, semnalând vizibil că TCO lipsește.

**Nu inventa prețul benzinei.** Regula #1 din `CLAUDE.md §8`.

Lipsesc și `consum_real_l100`, `portbagaj_l`, `valoare_reziduala` pe majoritatea
rândurilor. TCO-ul trebuie să calculeze cu ce are și să declare ce lipsește —
nu să producă o cifră care pare completă.

### Teste

Scrie teste pentru build. Minimum:
- suma ponderilor fiecărui profil = 1.00
- niciun prag din `criteria.yaml` nu apare hardcodat în cod (grep în CI)
- o observație cu cheie incompletă ajunge în carantină, nu în `min()`
- două reduceri de casare nu se însumează niciodată
- o reducere condiționată de finanțare nu intră în `pret_net_estimat`

---

## 3. Sarcina 2 — dashboard-ul

`dashboard/index.html`, **un singur fișier**, self-contained: CSS și JS inline.
Fără backend, fără build tooling.

### Datele se INJECTEAZĂ la build, nu se încarcă prin fetch

```html
<script>const DATA = { /* conținutul latest.json, injectat de build */ };</script>
```

**Nu** `fetch('latest.json')`. Motivul e practic: pe `file://` browserul blochează
fetch-ul prin CORS, deci fișierul n-ar merge la dublu-click — ar cere un server
local de fiecare dată. Cu datele inline, fișierul funcționează oriunde: local,
pe stick, atașat într-un email, pe telefon, offline.

Consecință pentru build: `build.py` produce **două** ieșiri — `data/latest.json`
(sursa de adevăr, versionabilă, diff-abilă în Git) și `dashboard/index.html`
(șablonul cu datele injectate). Șablonul stă în `dashboard/template.html`.

### Contractul de interogare — `spec/query.md` §8

> Dashboard-ul nu trebuie să poată exprima ceva ce contractul interzice. Dacă un
> câmp nu e în `query.filtrabile`, nu apare nici în panoul de filtre — altfel
> interfața devine a doua specificație, care diverge de prima.

**Generează panoul de filtre din `criteria.yaml → query.filtrabile`**, nu dintr-o
listă scrisă de mână în HTML.

### Ce trebuie să facă

**Filtre** pe câmpurile din `query.filtrabile`. Filtru implicit: `in_buget: true`
— rândurile de referință sunt ascunse până le ceri.

**Sortare** pe orice cheie din `query.sort_keys`. Implicit `cost_total_5_ani`,
secundar `pret_net_estimat`. Cele patru coloane de bani sunt **distincte și
etichetate distinct**; niciuna nu se numește generic „prețul".

**Comutator de profil** — `default`, `cash_minim`, `continuitate_vitara`,
`economie_carburant`. Un profil selectat în interfață e o lentilă, nu o schimbare
de politică: **nu rescrie `criteria.yaml`**.

**Raportarea atriției.** Când filtrele elimină rânduri, arată câte a eliminat
fiecare filtru, în ordine:

```
Universul: 23 modele
  propulsie = hev     → −11   (12 rămase)
  tractiune = awd     → −9    (3 rămase)
  pret_net ≤ 24000    → −2    (1 rămas)
```

Nu e decor. Linia care taie 9 din 12 e de obicei informația cea mai utilă din
ecran: îți spune care constrângere te costă.

**Vizibilitatea incertitudinii.** Fiecare celulă cu `confidence: estimated` sau
`null` arată diferit de una `confirmed`. Un tabel în care o cifră citită dintr-un
PDF oficial arată la fel ca una estimată e mai rău decât unul cu goluri.
Arată și vârsta sursei — sunt prețuri din 2020 și 2024 în date.

**Antetul** spune, o dată: netul estimat nu e o ofertă, e o reconstituire a
prețului public la data scanării.

### Unde se vede, în afara IDE-ului

Pentru că e un singur fișier cu datele inline, merge peste tot:

| Cale | Cum | Bun pentru |
|---|---|---|
| **Dublu-click** | fișierul e în OneDrive, deja sincronizat pe toate mașinile | uz zilnic, offline |
| **GitHub Pages** | repo-ul e deja în GitHub; push + activare Pages → URL | telefon, partajare |
| **Atașat oriunde** | email, mesaj, stick — un singur fișier, fără dependențe | arătat cuiva |
| **Artefact persistent** | livrat din sesiunea Cowork, se deschide din galerie | revizitare fără să cauți conversația |

**Atenție la GitHub Pages:** publică fișierul pe internet. Datele sunt prețuri
publice de catalog, deci nu e o problemă de confidențialitate — dar verifică să
nu fi ajuns în `latest.json` note personale sau bugetul lui Serban.

Recomandare: **Pages pentru telefon, dublu-click pentru zi cu zi.** Dacă
`build.py` rulează la fiecare scan și rezultatul se comite, dashboard-ul se
actualizează singur pe ambele căi.

### Ce să NU facă

- Fără `localStorage` / `sessionStorage`.
- Fără praguri hardcodate — toate din `latest.json` / `criteria.yaml`.
- Fără să ascundă rândurile de referință complet: ascunse implicit, accesibile.
- Fără să prezinte scoruri ca fiind comparabile între scanuri.

---

## 4. Sarcina 3 — cele nouă modele nedeterminate

**Fă-o ÎNAINTE de dashboard** (vezi §5: sesiunea din IDE are cotă separată).
Verificare de dotări, nu de preț. Se face o dată.

Două dintre ele contează pentru decizie, restul sunt rânduri de referință:
**SEAT Arona** (prețul pachetului cu cameră decide dacă intră sau nu în buget)
și **Ford Puma** (lista din 2020 face prețul de 20.800 EUR neutilizabil, deși
modelul ar fi în buget).

| Model | Ce lipsește |
|---|---|
| Opel Mokka | AC automat e opțional chiar și pe GS; prețul pachetelor e neclar |
| Opel Frontera | sursele se contrazic pe compoziția pachetelor Comfort vs Tech Pro |
| Citroën C3 Aircross | scaunele încălzite: standard cu o tapițerie (RO) sau opționale (UK)? |
| Jeep Avenger | Altitude/Summit neconfirmate din surse RO |
| SEAT Arona | camera există doar în pachet — prețul și nivelurile eligibile |
| SEAT Ateca | FR e singurul cu cameră standard; scaunele încălzite neconfirmate |
| Ford Puma | lista din 2020 contrazice campania 2026 |
| Suzuki S-Cross | Android Auto neconfirmat la nivelul Passion |
| VW T-Cross / Taigo | AC automat opțional de la Life; nomenclatura în conflict |

**Metoda care a funcționat:** interoghează PDF-ul cerând **citate exacte** și
permițând explicit răspunsul „nu apare în document". O extragere implauzibilă e,
prima dată, o întrebare prost pusă — nu o sursă proastă. Reîntreabă mai precis
înainte să schimbi sursa. Asta a deblocat Yaris Cross după ce prima extragere
dăduse un rezultat absurd.

---

## 5. Economia de tokeni — și de ce regulile rămân valabile oricum

**Sesiunea din IDE are o cotă separată de cea din aplicație.** Munca scumpă pe
web — verificarea celor nouă modele nedeterminate (Sarcina 3) — se poate face
aici, nu trebuie amânată. Asta schimbă ordinea recomandată:

> **1 → 3 → 2**: build-ul, apoi verificarea dotărilor, apoi dashboard-ul peste
> date complete. Altfel construiești interfața peste nouă rânduri incomplete și
> o reproiectezi după ce se completează.

**Dar regulile din `sources.yaml → procedura_scan_lunar` NU sunt doar despre
bani.** Rămân valabile pentru că sunt și despre calitate:

- **Lista neagră** — un scan care reîncearcă 31 de URL-uri moarte e lent și
  umple raportul cu zgomot care ascunde eșecurile reale.
- **Fără reverificare de catalog** — fiecare reverificare e o ocazie nouă ca o
  extragere proastă să suprascrie un fapt deja confirmat corect.
- **Întrebări înguste cu citate exacte** — nu e o economie, e metoda care a
  deblocat Yaris Cross după o extragere absurdă.
- **Fără subagenți pentru URL-uri cunoscute** — explorarea redundantă produce
  și rezultate divergente, nu doar consum.

**Ce rămâne scump și invizibil, oriunde:** conversațiile lungi. Fiecare apel de
tool reprocesează tot istoricul acumulat. Pornește sesiuni noi pentru sarcini
noi, chiar dacă ai buget.

**Scanul lunar automat rămâne în cloud** (sarcină programată, 1 ale lunii). E
proiectat pentru rulare nesupravegheată. Dacă vrei un scan ad-hoc din IDE între
rulări, e în regulă — dar scrie-l tot ca `data/scans/scan-<data>.json`, fișier
nou, ca seria să rămână continuă indiferent unde a rulat.

---

## 6. Împărțirea muncii între IDE și sesiunea din aplicație

Descoperit empiric pe 2026-08-19, după o încercare eșuată de a face commit și
push prin puntea către desktop. Nu e o preferință — sunt limite reale ale
mediului.

### Puntea (sesiunea Cowork → calculatorul tău) POATE

- să listeze foldere și să citească fișiere
- să scrie și să suprascrie fișiere (`device_commit_files`)
- să ruleze comenzi în folderele montate (`device_bash`): Python, build-uri,
  inspecții, transformări de text

### Puntea NU POATE

- **rețea.** `github.com` nu se rezolvă din mediul punții. Fără push, fără
  pull, fără `gh`, fără instalare de pachete.
- **chei SSH.** Nu există `~/.ssh` acolo. Un remote `git@github.com:` e
  inaccesibil chiar dacă ar exista rețea.
- **identitate git.** Nu există `.gitconfig`; `git commit` cade cu
  „Author identity unknown".
- **ștergere de fișiere.** `rm` returnează „Operation not permitted". Git lasă
  în urmă `.git/objects/tmp_obj_*` și, la o operație întreruptă, un
  `.git/index.lock` orfan care blochează comenzile următoare.

### Regula

> **Fișierele aparțin punții. Git și rețeaua aparțin IDE-ului.**

O sesiune din aplicație poate pregăti o modificare până la staging și trebuie să
se oprească acolo, dând comanda exactă de rulat în IDE. Nu forța git prin punte:
în cel mai bun caz eșuează curat, în cel mai rău lasă lock-uri orfane pe care
tot din IDE trebuie să le cureți.

**Dacă găsești un `.git/index.lock` de 0 bytes:** e resturi de la o sesiune prin
punte, nu un proces git viu. Șterge-l din IDE și continuă.

**Ștergerile cerute prin punte** se fac mutând fișierele într-un `_to_delete/`
(deja în `.gitignore`), pe care îl golești manual.

---

## 7. Reguli care nu se negociază, oriunde ai lucra

1. **Nu inventa nicio cifră.** Necunoscut = `null`, niciodată o valoare
   plauzibilă. Un tabel plin de valori plauzibile e mai rău decât unul cu
   goluri, pentru că golurile se văd.
2. **Fiecare fapt comercial poartă `source_url`, `observed_at`, `confidence`.**
3. **Istoricul e append-only.** Un scan nou e un fișier nou. Nu edita scanuri
   existente; corectează printr-o intrare nouă plus o notă în `DECISIONS.md`.
4. **`sources_failed` e obligatoriu** în antetul fiecărui scan. O sursă
   inaccesibilă arată altfel identic cu un model dispărut din ofertă.
5. **Conflicte între surse:** păstrează ambele valori cu sursele lor și
   marchează. Nu alege tăcut.
6. **Niciun prag duplicat.** Dacă dashboard-ul are nevoie de limita de lungime,
   o citește din `criteria.yaml`. Un prag scris în două locuri devine, în șase
   luni, două praguri diferite.
7. **Orice decizie de arhitectură se scrie în `DECISIONS.md`** — decizia,
   motivul, consecința. Inclusiv cele care contrazic ce e scris aici.

---

## 8. Context despre utilizator, util pentru ton

Serban e inginer AI, construiește exact genul de infrastructură pe care se
sprijină munca altora — instrumentare, evaluare, orchestrare. Preferă:
raționamentul arătat, nu doar concluzia; provenienței marcate (standard
industrial / tipar de nișă / sinteza ta); compromisurile explicite; tipare
reutilizabile în locul soluțiilor punctuale. Contrazice-l când vezi ceva greșit —
mai multe decizii bune din `DECISIONS.md` au venit din corecturi pe care le-a
făcut el, iar câteva au venit din contraziceri asumate. Scrie în română.
