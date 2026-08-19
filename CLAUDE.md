# NEW_CAR — instrucțiuni de sistem

Acest fișier este constituția proiectului. Orice sesiune care lucrează în acest
repo îl citește primul și i se supune. Dacă o instrucțiune de aici intră în
conflict cu o cerere punctuală din conversație, cererea câștigă pentru acea
rulare, dar diferența se scrie în `DECISIONS.md`.

---

## 1. Scop și non-scop

**Scop.** Menținerea unui tablou comparativ, actualizat lunar, al mașinilor noi
disponibile la dealeri oficiali din România care se încadrează în criteriile din
`spec/criteria.yaml`, împreună cu un motor de căutare care reîmprospătează
ofertele comerciale la zi.

**Orizontul deciziei este incert.** Proiectul nu optimizează pentru "ce cumpăr
luna asta", ci pentru "ce știu despre piață când mă hotărăsc". Consecință
practică: continuitatea seriei de date contează mai mult decât completitudinea
oricărei rulări individuale. O scanare parțială, marcată corect ca parțială, e
mai valoroasă decât una completă obținută prin ghiceli.

**Non-scop.** Nu este un proiect de achiziție: nu contactează dealeri, nu
completează formulare, nu rezervă și nu negociază. Nu acoperă piața second-hand
între persoane fizice. Nu produce recomandarea finală — produce baza pe care
Serban o ia.

---

## 2. Modelul de date

Regula centrală: **faptele stabile și faptele volatile stau în fișiere
separate, cu cadențe de actualizare diferite.** Este aplicarea tiparului
"slowly changing dimensions" din data warehousing (standard industrial) la un
caz mic.

| Strat | Fișier | Se schimbă | Cine îl produce |
|---|---|---|---|
| Catalog | `data/models.json` | rar (la facelift/lansare) | validat o dată, apoi doar corectat |
| Ofertă | `data/scans/scan-YYYY-MM-DD.json` | lunar | fiecare rulare de scan |
| Derivat | `data/latest.json` | la fiecare scan | calculat, niciodată editat manual |

**Catalogul** conține fapte tehnice: marcă, model, generație, motorizare, nivel
de echipare, putere, cuplu, lungime, tracțiune, cutie, consum WLTP, consum real
raportat, garanție. Nu conține prețuri.

**Oferta** conține fapte comerciale observate: preț de listă, campanie activă,
prima de casare aplicabilă, tip de stoc (comandă / stoc an anterior / km 0),
dealer, URL, data observării.

**Cheia de identitate** a unui rând este:

```
marca | model | generatie | motorizare | tractiune | cutie | nivel_echipare
```

Nu titlul anunțului, nu numele campaniei. Titlurile se schimbă la fiecare
redesign de site; cheia asta supraviețuiește și face ca doi ani de scanuri să
fie comparabili. (Preluat din tiparul de monitorizare deja folosit pentru
scanurile de preț — vezi `methods/monitoring-pattern`.)

**Istoricul este append-only.** Un scan nou este un fișier nou. Nu se editează
și nu se șterge un scan existent; o eroare descoperită ulterior se corectează
printr-o intrare nouă și o notă în `DECISIONS.md`. Consolidare trimestrială în
`data/scans/scan-YYYY-Qn.json` când directorul devine greu de citit.

---

## 3. Contracte

Trei fișiere sunt sursă unică de adevăr. Codul și dashboard-ul le citesc; nu
redeclară valorile din ele.

- `spec/criteria.yaml` — filtre, profile de ponderi, parametri TCO, chei de
  interogare. **Niciun prag nu apare hardcodat în altă parte.** Dacă
  dashboard-ul are nevoie de limita de lungime, o citește de aici.
- `spec/query.md` — ce e o întrebare validă despre listă și cum se răspunde la
  ea determinist: filtre și ordonare ca parametri de rulare, nu ca constante.
- `spec/sources.yaml` — sursele de scanat, tipul fiecăreia și cât de mult i se
  acordă credit.
- `spec/price-model.md` — formula netului estimat, cu fiecare termen definit.

Motivul e simplu: un prag scris în două locuri devine, în șase luni, două
praguri diferite. Autoritatea trebuie să fie în artefact, nu în memoria
sesiunii.

---

## 4. Reguli de scanare

1. **Cadență:** lunar, prin sarcină programată. Rulări suplimentare la cerere
   sau la evenimente de piață (lansare Rabla, campanii de sfârșit de an).
2. **Ordinea surselor:** configurator oficial al importatorului → pagina de
   stoc a dealerului oficial → agregatoare. Prima sursă care confirmă un fapt
   îl fixează; cele următoare doar îl coroborează.
3. **Header obligatoriu în fiecare scan:**
   `scan_date`, `previous_scan`, `sources_checked`, `sources_failed`,
   `models_found`, `notes`.
   `sources_failed` este obligatoriu și nu poate fi omis: o sursă inaccesibilă
   arată, altfel, identic cu un model care a dispărut din ofertă. Confuzia asta
   este cel mai probabil mod în care seria de date devine falsă.
4. **Fiecare fapt comercial poartă `source_url` și `observed_at`.** Un preț fără
   sursă nu intră în fișier.
5. **Fiecare fapt poartă `confidence`:**
   - `confirmed` — citit direct dintr-un configurator oficial sau o listă de
     prețuri publicată;
   - `derived` — calculat din valori confirmate (ex. net = listă − campanie);
   - `estimated` — aproximat, cu metoda notată în `notes`.
   Un rând care are `estimated` pe prețul de listă nu se afișează ca preț ferm
   nicăieri în dashboard.
6. **Rate limiting și bun-simț:** o sursă care blochează accesul automat nu se
   forțează. Se notează în `sources_failed` cu motivul și se trece mai departe.

---

## 5. Reguli de preț

Coloana pe care se sortează este **netul estimat**; defalcarea rămâne vizibilă
la nivel de model. Formula completă stă în `spec/price-model.md`; aici stă doar
disciplina:

- Toți termenii se exprimă în EUR, cu cursul și data cursului notate atunci când
  sursa e în RON.
- **Prima de casare (Rabla) este un parametru anual, nu o constantă.** Se
  citește din `spec/criteria.yaml`, cu anul programului și eligibilitatea
  explicite. Un program neconfirmat pentru anul curent se tratează ca `0` cu o
  notă, nu se presupune că se repetă.
- Reducerile condiționate de finanțare captivă sau de asigurare la dealer se
  păstrează pe o linie separată și **nu** intră implicit în net. Sunt un cost
  mutat, nu unul eliminat.
- Netul estimat nu este o ofertă. Dashboard-ul spune asta explicit, o dată, în
  antet.

---

## 6. Reguli de scor

Filtrele hard elimină; totul altceva punctează. Ponderile stau în
`spec/criteria.yaml`. Două lucruri de reținut:

**Departajarea principală este costul total de deținere pe 5 ani și
fiabilitatea/garanția**, nu prețul de achiziție. Un net cu 2.000 EUR mai mic
care aduce 1,5 l/100km în plus se anulează singur pe orizontul de deținere al
lui Serban (mașina precedentă: 11 ani).

**Tracțiunea integrală și cutia manuală sunt bonusuri de scor, nu filtre.** Sunt
moștenite de la mașina actuală și contează, dar nu justifică amputarea listei.

**Principiul care le guvernează pe toate (D-016): un criteriu care încodează o
incertitudine, nu o cerință, este marcaj sau pondere — niciodată filtru.** Un
filtru șterge rândul și, odată cu el, dovada pe care s-ar fi putut verifica
presupunerea. Bugetul, reziduala incertă a unei mărci fără istoric, tracțiunea —
toate sunt de acest tip. Filtre hard rămân doar cerințele propriu-zise:
caroserie, propulsie, gabarit, putere, pragul de dotări.

**Avertisment metodologic asupra cuplului.** Intervalul cerut (200-300 Nm) nu se
compară corect între tehnologii: un full-hybrid raportează adesea cuplul
sistemului, un turbo pe cel al motorului termic la o turație dată, iar un
aspirat cade sub prag deși se conduce acceptabil. Convenția acestui proiect:
se stochează **cuplul motorului termic**, cu turația, plus un câmp separat
pentru cuplul motorului electric acolo unde există; cuplul este **criteriu de
scor, nu filtru eliminatoriu**. Dacă vrei totuși un prag dur, trebuie ales întâi
care dintre cele două cifre îl trece.

---

## 7. Interogări

Clasamentul din `latest.json` este politica proiectului, nu singurul răspuns
posibil. Filtrele și cheia de ordonare sunt **parametri de rulare**: se pot
schimba la fiecare întrebare, fără să atingă specificația.

Contractul complet e în `spec/query.md`. Trei reguli care nu se negociază:

**Interogarea se traduce vizibil înainte de a fi executată.** „Cea mai bună
mașină economică sub 23k" are cel puțin trei citiri — consum minim, TCO minim,
cost pe km minim. Traducerea arătată face dezacordul vizibil înainte să producă
o listă greșită.

**Fiecare filtru raportează câți candidați a eliminat.** Optimul dintr-o listă
de 1 arată identic cu optimul dintr-o listă de 20, dacă nu vezi atriția. Linia
care taie 9 din 12 e, de obicei, informația cea mai utilă din răspuns: îți spune
care constrângere te costă.

**Când niciun model nu domină pe toate obiectivele cerute, răspunsul e frontul
Pareto, nu un câștigător.** Un câștigător unic într-o problemă cu obiective
conflictuale se obține doar inventând ponderi — adică făcând, în locul tău, un
arbitraj pe care nu l-ai cerut.

O interogare ad-hoc nu rescrie `profil_activ` și nu se salvează în
`criteria.yaml`. Dacă o lentilă se dovedește utilă repetat, devine profil,
printr-o intrare în `DECISIONS.md`.

---

## 8. Onestitate a datelor

Reguli absolute, în ordinea importanței:

1. **Nu se inventează niciodată o cifră.** Un câmp necunoscut se scrie `null`,
   nu se completează cu o valoare plauzibilă. Un tabel plin de valori plauzibile
   este mai rău decât unul cu goluri, pentru că golurile se văd.
2. **Nu se extrapolează prețul unui nivel de echipare din altul.** Diferențele
   dintre trim-uri nu sunt liniare.
3. **Nu se raportează consum "real" din specificația WLTP.** Sunt două câmpuri
   diferite și rămân diferite.
4. Când o sursă contrazice alta, se păstrează ambele valori cu sursele lor și se
   marchează conflictul. Nu se alege tăcut.

---

## 9. Ritualul unei rulări de scan

```
1. Citește CLAUDE.md, spec/criteria.yaml, spec/sources.yaml
2. Listează data/scans/ și ia max(data) ca scan precedent — nu presupune
3. Scanează sursele în ordinea din sources.yaml
4. Scrie data/scans/scan-<azi>.json (fișier nou, niciodată editare)
5. Recalculează data/latest.json din catalog + scanul curent
6. Scrie history/history-<azi>.md: ce s-a schimbat față de scanul precedent
   — intrări noi, ieșiri, mișcări de preț peste pragul din criteria.yaml
7. Raportează în conversație doar delta, nu tot tabelul
```

Pasul 6 este cel care dă valoare seriei. Un dashboard spune ce e acum; jurnalul
de delta spune dacă acum e un moment bun.

---

## 10. Ce nu face agentul

- Nu contactează dealeri și nu completează formulare de contact sau de test-drive.
- Nu creează conturi și nu trece de mecanisme anti-bot.
- Nu editează scanuri istorice.
- Nu inventează filtre. Nu există filtru de marcă (D-016): apartenența se
  decide exclusiv prin `hard_filters`. Un model care trece parametrii intră,
  indiferent de siglă sau de preț.
- Nu elimină un model pentru că e scump. Peste plafon înseamnă
  `in_buget: false`, nu absent — un rând de referință costă câțiva tokeni, o
  presupunere netestată costă mai mult.
- Nu formulează recomandarea finală de cumpărare nesolicitat. Poate arăta care
  model iese primul la scorul definit — ceea ce nu e același lucru.

---

## 11. Structura repo-ului

```
NEW_CAR/
├── CLAUDE.md              # acest fișier
├── DECISIONS.md           # log de decizii, append-only
├── spec/
│   ├── criteria.yaml      # filtre, profile de ponderi, chei de interogare
│   ├── query.md           # contractul de interogare (filtrare/ordonare/optim)
│   ├── sources.yaml       # surse și nivelul lor de credit
│   └── price-model.md     # formula netului estimat
├── data/
│   ├── models.json        # catalog tehnic (stabil)
│   ├── latest.json        # derivat: catalog + ultimul scan + scoruri
│   └── scans/
│       └── scan-YYYY-MM-DD.json
├── history/
│   └── history-YYYY-MM-DD.md
└── dashboard/
    └── index.html         # static, self-contained, citește latest.json
```
