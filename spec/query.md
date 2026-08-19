# Contractul de interogare

Acest fișier definește ce înseamnă o întrebare validă despre lista de modele și
cum se răspunde la ea, determinist. Parametrii (chei de sortare, câmpuri
filtrabile, profile de ponderi) stau în `spec/criteria.yaml → query` și
`→ scoring.profiles`.

---

## 1. Cinci tipuri de întrebare, care nu se confundă

Distincția contează pentru că fiecare tip are alt răspuns corect, iar
confundarea lor produce răspunsuri care par sigure și nu sunt.

| Tip | Formă | Ce produce | Exemplu |
|---|---|---|---|
| **Filtrare** | `WHERE` | o submulțime | "doar hibride, doar cu AWD" |
| **Ordonare** | `ORDER BY` | o ordine totală pe un câmp | "sortează după preț net" |
| **Scor** | profil de ponderi | un clasament agregat | "care e cea mai bună, per ansamblu" |
| **Optimizare sub constrângeri** | obiectiv + domeniu admisibil | un optim, dacă există | "consum minim, dar peste 130 CP și sub 24k" |
| **Compromis** | mai multe obiective | frontul Pareto | "vreau și ieftin, și economic" |

Întrebarea ta tipică — *„varianta optimă pentru criteriul X, în limitele Y"* —
este tipul 4: **un obiectiv, un domeniu admisibil**. Nu e același lucru cu tipul
3, unde nu există un obiectiv unic și ponderile fac arbitrajul.

Terminologia și tratarea tipurilor 3-5 vin din analiza decizională
multicriterială (MCDA) și din dominanța Pareto — ambele standard, nu invenția
acestui proiect.

---

## 2. Gramatica

O interogare se exprimă în limbaj natural, dar se **traduce explicit** în forma
de mai jos înainte de a fi executată, iar traducerea se arată în răspuns:

```
SELECT <câmpuri>
FROM   latest.json
WHERE  <predicate pe câmpuri din criteria.yaml → query.filtrabile>
[USING PROFILE <nume>]          -- doar pentru tipul 3
[MINIMIZE|MAXIMIZE <câmp>]      -- doar pentru tipul 4
ORDER BY <cheie din query.sort_keys> [ASC|DESC]
LIMIT  <n>
```

Motivul traducerii vizibile: „dă-mi cea mai bună mașină economică sub 23k" are
cel puțin trei citiri (consum minim? TCO minim? cost pe km minim?). Traducerea
arătată face dezacordul vizibil înainte să producă o listă greșită, nu după.

**Un filtru pe un câmp care nu e în `query.filtrabile` se refuză explicit.** Nu
se aproximează cu un câmp apropiat. Dacă întrebi de gardă la sol și câmpul nu
există în schemă, răspunsul e „nu am câmpul ăsta", nu o estimare.

---

## 3. Cele trei coloane de bani

Nu se substituie una alteia și niciodată nu se numesc, generic, „prețul":

- **`pret_lista`** — catalog, înainte de reduceri. Util ca ancoră pentru
  valoarea reziduală, inutil pentru decizie.
- **`pret_net_estimat`** — ce scoți azi din buzunar. Răspunde la „îmi permit?".
- **`cost_total_5_ani`** — TCO. Răspunde la „ce mă costă?". **Cheia de sortare
  implicită**, pentru că la 11 ani de deținere e singura care compară corect un
  full-hybrid cu un benzină pur.
- **`cost_pe_km`** — TCO / kilometri parcurși. Normalizator: face comparabile
  scenarii cu kilometraje diferite, dacă parametrul `km_pe_an` se schimbă.

Când o întrebare spune doar „preț", răspunsul cere precizare sau răspunde pe
toate trei, nu alege tăcut.

---

## 4. Profile de ponderi

`scoring.profiles` din `criteria.yaml` conține vectori de ponderi cu nume:
`default`, `cash_minim`, `continuitate_vitara`, `economie_carburant`.

- **`default` e politica proiectului.** Este scorul scris în `latest.json` și
  singurul comparabil de la un scan la altul.
- **Un profil invocat într-o interogare este o lentilă, nu o schimbare de
  politică.** Nu rescrie `profil_activ`, nu se salvează în `criteria.yaml`.
- Ponderi ad-hoc, date în conversație, sunt permise — dar răspunsul spune
  explicit că sunt ad-hoc și că rezultatul nu se compară cu clasamentul oficial.
- Dacă o lentilă ad-hoc se dovedește utilă repetat, **devine profil**, printr-o
  intrare în `DECISIONS.md`. Așa nu ajungi cu ponderi care se schimbă tăcut de
  la o întrebare la alta.

---

## 5. Regula de atriție

Fiecare răspuns care aplică filtre raportează **câte modele a eliminat fiecare
filtru**, în ordine:

```
Universul: 23 modele
  propulsie = hev            → −11   (12 rămase)
  tractiune = awd            → −9    (3 rămase)
  pret_net <= 24000          → −2    (1 rămas)
Rezultat: 1 model
```

Fără asta, „optimul" dintr-o listă de 1 arată exact ca „optimul" dintr-o listă
de 20. Linia care elimină 9 din 12 este, de obicei, informația cea mai
importantă din răspuns — îți spune care constrângere te costă cu adevărat.

---

## 6. Regula Pareto

Când se cer două sau mai multe obiective și niciun model nu e cel mai bun pe
toate, răspunsul este **setul nedominat** (frontul Pareto), nu un câștigător
unic:

> Un model A domină pe B dacă A e cel puțin la fel de bun pe toate obiectivele
> și strict mai bun pe cel puțin unul. Frontul Pareto e mulțimea modelelor pe
> care nimic nu le domină.

Un câștigător unic într-o problemă cu obiective conflictuale se obține doar
alegând ponderi — adică inventând un arbitraj pe care nu l-ai cerut. Regula
acestui proiect: se arată frontul și se numește compromisul, iar arbitrajul îl
faci tu.

---

## 7. Șablon de răspuns

```
Interogare interpretată:   <forma tradusă din §2>
Sursa datelor:             scan-YYYY-MM-DD (vechime: N zile)
Atriție:                   <tabelul din §5>
Rezultat:                  <max 10 rânduri, cu coloanele cerute>
Avertismente:              <câmpuri null, confidence=estimated, borderline buget>
```

**Avertismentele nu sunt opționale.** Dacă modelul clasat primul are
`pret_net_estimat` cu `confidence: estimated`, răspunsul spune asta pe același
rând cu clasamentul, nu într-o notă de subsol.

---

## 8. Unde se execută interogările

Două suprafețe, **același contract**:

- **În conversație** — agentul citește `latest.json`, aplică regulile de aici și
  răspunde. Bun pentru întrebări cu obiectiv și constrângeri (tipurile 4-5).
- **În dashboard** — `dashboard/index.html`, static, cu datele inline: panou de
  filtre, sortare pe orice cheie din `query.sort_keys`, comutator de profil.
  Bun pentru explorare (tipurile 1-3).

Dashboard-ul nu trebuie să poată exprima ceva ce contractul interzice. Dacă un
câmp nu e în `query.filtrabile`, nu apare nici în panoul de filtre — altfel
interfața devine a doua specificație, care diverge de prima.
