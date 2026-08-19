# Modelul de preț

Parametrii stau în `spec/criteria.yaml` (secțiunea `pret`). Aici stă formula și
definiția fiecărui termen.

## Netul estimat

```
net_estimat = pret_lista
            − discount_producator
            − discount_dealer
            − prima_rabla
```

Atât. Termenii de mai jos sunt **excluși deliberat** din formulă:

```
NU se scad:  reducere_finantare_captiva
             reducere_asigurare_la_dealer
             reducere_buy_back
```

Motivul: sunt reduceri condiționate de acceptarea unui alt produs financiar, cu
un cost propriu (dobândă, primă de asigurare peste piață) pe care formula nu îl
poate cuantifica. A le scădea produce un net care arată bine și e fals. Se
afișează pe linie separată, cu eticheta *condiționată*, ca să poți face
socoteala tu când ajungi la negociere.

## Taxonomia reducerilor — a doua identitate care trebuie rezolvată

Nu e suficient să știi *ce mașină* e. Trebuie să știi și *ce fel de reducere* s-a
aplicat. Piața românească folosește cel puțin patru instrumente diferite, cu
denumiri care se imită între ele deliberat:

| `tip_reducere` | Ce e | Cine o dă | Exemplu observat |
|---|---|---|---|
| `rabla_stat` | prima de casare AFM, programul de stat | statul | 2.294 € pe mitsubishi-motors.ro; **„Remat"** pe tiriacauto.ro |
| `bonus_producator` | voucher propriu al importatorului | importatorul | **„Ecotichet Mitsubishi" −1.000 €** pe mtrgroup.ro |
| `bonus_dealer` | schemă de casare privată a dealerului | dealerul | niciunul confirmat până acum |
| `discount_comercial` | reducere de preț, fără contrapartidă | oricine | −2.380 … −3.432 € |
| `reducere_showroom` | negociabil, necuantificabil online | dealerul | *„reducere suplimentară, în showroom"* |

### Cum se clasifică o reducere: valoarea întâi, numele al doilea

Denumirile comerciale sunt dovadă slabă. „Rabla" e numele oficial; „Remat" e
numele firmei care operează radierea mașinilor casate, folosit colocvial de
dealeri pentru **aceeași** primă de stat. „Ecotichet" e folosit și de stat, și
de importatori, pentru lucruri diferite.

Procedura, în această ordine:

1. **Testul valorii.** Grila Rabla 2026 e cunoscută: 10.000 lei benzină, 12.000
   hibrid, 15.000 PHEV, 18.500 electric. O reducere a cărei valoare se potrivește
   cu grila, pentru propulsia respectivă, **este** `rabla_stat` — oricum s-ar
   numi. O valoare care nu se potrivește **nu este** `rabla_stat` — oricum s-ar
   numi.
2. **Testul co-ocurenței.** Dacă două denumiri apar în aceeași ofertă sau
   aceeași frază, sunt reduceri distincte. Dacă apar separat, pe pagini
   diferite, se presupun **sinonime** — nu se dublează.
3. **Testul emitentului.** Cine o acordă, dacă pagina o spune.

Când valoarea nu e defalcată (cazul „Remat", unde prețul e dat direct net),
testul 1 nu poate rula și decide testul 2: sinonim, până la proba contrară.

**Aplicat pe cazul ASX.** „Ecotichet Mitsubishi" = **1.000 € fix pe toate
versiunile, inclusiv PHEV**. Nicio valoare din grila Rabla nu e 1.000 €, iar o
primă de stat variază cu propulsia — aceasta nu variază. Deci `bonus_producator`,
prin testul valorii, decisiv. „Remat" apare singur, fără defalcare, pe o ofertă
cu preț final plauzibil ca Rabla — deci `rabla_stat`, prin testul co-ocurenței.

### Regula de necumulare

Reducerile de casare — `rabla_stat`, `bonus_producator`, `bonus_dealer` — sunt
adesea **alternative, nu cumulative**: predai o singură mașină. Regula:

> Două reduceri de casare nu se însumează decât dacă sursa spune explicit că
> sunt cumulabile. În lipsa unei confirmări, se reține **cea mai mare**, iar
> celelalte se consemnează cu `aplicata: false` și motivul.

Fiecare reducere poartă `cumulabil_cu: []` sau `null` (necunoscut). `null` se
tratează ca „nu cumula", nu ca „probabil da".

### Reducerea de showroom nu se estimează

*„Alege acum un model din stoc, cu livrare imediată și beneficiezi de o reducere
suplimentară, în showroom!"* — o reducere reală, nequantificată public. Nu se
estimează, nu se presupune zero. Se marchează
`reducere_showroom_disponibila: true`, ca semnal de marjă de negociere. E
limita superioară a ceea ce un motor de căutare web poate ști; restul se află
la telefon.

## Capcana care invalidează formula: prețul deja net

**Nu orice preț afișat este preț de listă.** Unele mărci publică direct prețul
promoțional, cu Rabla și reducerile comerciale deja scăzute. Cazul confirmat pe
2026-08-19: `dacia.ro` afișează „de la 17.100 EUR", iar textul precizează că
include deja prima de casare și reducerile valabile până la 31 august.

Tratat ca `pret_lista`, un asemenea preț face ca Rabla să fie scăzută **de două
ori** — modelul apare cu ~2.000 EUR mai ieftin decât e.

Regula: fiecare preț preluat poartă un câmp `tip_pret`:

| `tip_pret` | Ce e | Ce se face cu el |
|---|---|---|
| `lista` | catalog, înainte de reduceri | intră în formulă ca `pret_lista` |
| `net_promotional` | listă − reduceri deja aplicate | intră direct ca `net_estimat`; NU se mai scade nimic |
| `necunoscut` | nu se poate stabili din pagină | `confidence: estimated`, semnalat în raport |

Când o pagină nu spune explicit ce fel de preț afișează, `tip_pret` este
`necunoscut`. Nu se deduce din mărimea cifrei.

## Un model nu are un preț. Are o mulțime de observații de preț.

Același model, în aceeași zi, apare cu prețuri diferite la importator și la
fiecare dealer oficial. Diferența nu e zgomot de curățat — e **informația
centrală a proiectului**. Un model cu 1.000 EUR dispersie în rețea are marjă de
negociere; unul fără dispersie nu are.

De aceea prețul nu se stochează ca scalar, ci ca listă de observații:

```json
"observatii_pret": [
  {
    "sursa": "importator",
    "url": "...",
    "observat_la": "2026-08-19",
    "valabil_pana": "2026-07-31",
    "tip_pret": "net_promotional",
    "cheie_rezolvata": true,
    "identitate": {"echipare": "Intense StyleCold", "motor": "1.3 DI-T MHEV",
                   "cutie": "manuala", "tractiune": "2wd"},
    "pret_eur": 20091,
    "componente": {"lista": 25817, "discount_importator": -3432, "rabla": -2294}
  }
]
```

### Regula de identitate — cea care contează cel mai mult

**O observație intră în comparație doar dacă cheia ei e complet rezolvată:**
echipare + motorizare + transmisie + tracțiune. Dacă anunțul nu spune ce cutie
are, observația merge în **carantină**, nu în minim.

Motivul e o capcană statistică, nu una de curățenie: **anunțul cel mai ieftin
este sistematic cel mai puțin specificat.** Un `min()` naiv peste toate
observațiile selectează, în medie, listingul care omite detaliile — și produce
un preț de referință care nu corespunde niciunei mașini reale. Filtrul de
identitate elimină exact acest bias.

Caz concret, Mitsubishi ASX, 2026-08-19: sub aceeași denumire „ASX Intense
StyleCold" există 1.3 DI-T manual la importator (20.091 EUR cu Rabla), 1.3 DI-T
7DCT la dealer (25.366 EUR) și 1.8 HEV test-drive la același dealer (26.741 EUR).
Interval aparent: 6.650 EUR. Dispersie reală de dealer: necunoscută, pentru că
cele trei sunt **mașini diferite**. Comparate direct, fabrică o reducere care nu
există.

### Dispersia se calculează doar în interiorul unei chei

```
dispersie_dealeri_eur = max(observatii_cu_aceeasi_cheie)
                      − min(observatii_cu_aceeasi_cheie)
```

Cu mai puțin de două observații pe aceeași cheie, dispersia e `null` — nu `0`.
Absența datelor nu e absența variației.

### Valabilitatea ofertei e un câmp obligatoriu

Pagina oficială Mitsubishi afișa pe 19 august 2026 o ofertă marcată *„valabilă
până la data de 31 Iulie 2026"* — expirată de trei săptămâni, publicată fără
niciun avertisment. O ofertă fără `valabil_pana` sau cu data trecută primește
`confidence: estimated` și se raportează ca atare.

### Demo nu înseamnă mai ieftin

La același dealer, exemplarul de test-drive (1.8 HEV, 26.741 EUR) era mai scump
decât unul nou (1.3 MHEV, 25.366 EUR) — pentru că e alt motor. Regula „km 0 e
mai ieftin" se verifică pe aceeași cheie, niciodată presupusă.

## Definiția termenilor

| Termen | Definiție | Sursă tipică | Confidence |
|---|---|---|---|
| `pret_lista` | preț de catalog cu TVA, nivelul de echipare exact, fără opționale | configurator oficial | `confirmed` |
| `discount_producator` | campanie națională, necondiționată | configurator / comunicat | `confirmed` |
| `discount_dealer` | reducere locală pe o unitate din stoc | pagina dealerului | `confirmed` sau `derived` |
| `prima_rabla` | prima de casare a programului anului curent | ghidul programului | `confirmed` sau `0` |

## Regula Rabla

Prima este **parametru anual**, nu constantă. Se citește din
`criteria.yaml → pret.rabla`. Dacă programul anului curent nu e confirmat
public, valoarea este `0` cu notă explicită — nu se presupune că se repetă cu
aceeași valoare ca anul trecut.

Eligibilitatea (vechimea mașinii predate, durata de proprietate) se verifică
separat și se marchează la nivel de proiect, nu de model: e o proprietate a lui
Serban, nu a mașinii cumpărate.

## Valută

Toate valorile în EUR. Când sursa publică în RON, se stochează **și** valoarea
în RON, **și** cursul folosit, **și** data cursului. Un preț convertit fără
cursul atașat devine necomparabil peste șase luni.

## Ce nu este netul estimat

Nu este o ofertă și nu este un preț negociat. Este cea mai bună reconstituire a
prețului public la data scanării. Dashboard-ul afirmă asta o dată, în antet, și
nu o repetă pe fiecare rând.
