# DECISIONS.md

Log append-only de decizii arhitecturale. O decizie revizuită nu se șterge: se
adaugă o intrare nouă care o înlocuiește, cu referință la cea veche.

Format: `## D-NNN — titlu` / Context / Decizie / Motiv / Consecință.

---

## D-001 — Universul de propulsie: benzină pur + MHEV + HEV
**Data:** 2026-08-19
**Context:** "hibrid" acoperă tehnologii cu preț și disponibilitate foarte diferite.
**Decizie:** intră benzina fără electrificare, mild-hybrid 48V și full-hybrid. Ies PHEV, BEV, diesel.
**Motiv:** PHEV nu există practic în 3900-4300 mm sub 25k net; diesel iese din logica de utilizare.
**Consecință:** lista amestecă tehnologii care nu se compară direct la consum și cuplu — de aici nevoia de TCO ca departajare principală (D-005) și de convenția de cuplu (D-006).

---

## D-002 — 4x4 și cutia manuală sunt bonusuri, nu filtre
**Data:** 2026-08-19
**Context:** mașina actuală e ALLGRIP cu manuală; tentația firească e să le tratezi ca obligatorii.
**Decizie:** ambele intră ca bonus de scor (pondere 0.05 în total), nu ca filtru eliminatoriu.
**Motiv:** sub 25k net, tracțiunea integrală lasă o mână de opțiuni și aproape niciun full-hybrid; manuala e incompatibilă cu majoritatea HEV-urilor (e-CVT). Aplicate ca filtre, ar goli lista înainte ca proiectul să producă ceva.
**Consecință:** dashboard-ul trebuie să facă vizibil când primul model din clasament nu are niciunul dintre atribute, ca alegerea să fie conștientă.

---

## D-003 — Arhitectură: agent + fișiere append-only
**Data:** 2026-08-19
**Context:** alternativa era scraping determinist în Python.
**Decizie:** o sesiune agent rulează periodic, caută pe web și scrie snapshot-uri datate; dashboard-ul e HTML static care citește un JSON derivat.
**Motiv:** configuratoarele și paginile de stoc se redesenează des; un parser rigid se strică tăcut, iar detectarea stricăciunii costă mai mult decât scanul. Agentul degradează grațios și raportează ce n-a putut citi.
**Consecință:** `sources_failed` devine câmp obligatoriu — fără el, o sursă inaccesibilă e indistinctă de un model dispărut din ofertă.
**Referință:** același tipar ca `methods/monitoring-pattern` (scanuri de preț).

---

## D-004 — Prețul: net estimat pentru sortare, defalcare la detaliu
**Data:** 2026-08-19
**Decizie:** coloana de sortare e netul estimat (listă − campanii necondiționate − Rabla); detaliul pe model arată fiecare componentă și confidence-ul ei.
**Motiv:** sortarea are nevoie de un singur număr, onestitatea are nevoie de defalcare. Nu sunt în conflict dacă defalcarea e la un click distanță.
**Consecință:** reducerile condiționate de finanțare captivă sau asigurare la dealer stau pe linie separată și nu intră în net — sunt cost mutat, nu eliminat.

---

## D-005 — Departajare: TCO 5 ani (0.40) + fiabilitate/garanție (0.30)
**Data:** 2026-08-19
**Motiv:** istoricul de deținere e de 11 ani și 150.000 km. Pe orizontul ăsta, prețul de achiziție e o fracțiune din cost, iar diferența de consum și de fiabilitate depășește ușor diferența de preț dintre două modele apropiate.
**Consecință:** proiectul are nevoie de un preț al benzinei și de un kilometraj anual ca parametri versionați, nu ca presupuneri implicite.

---

## D-006 — Cuplul este criteriu de scor, nu filtru
**Data:** 2026-08-19
**Context:** cerința inițială era 200-300 Nm ca interval dur.
**Decizie:** se stochează separat cuplul termic (cu turația), cel electric și cel de sistem; intervalul 200-300 Nm punctează, nu elimină.
**Motiv:** cifra nu e comparabilă între tehnologii — un HEV raportează adesea cuplul sistemului, un turbo pe cel termic la o turație dată, un aspirat cade sub prag deși se conduce acceptabil. Un filtru dur pe o valoare necomparabilă elimină modele din motive de raportare, nu de performanță.
**Deschis:** dacă se dorește totuși un prag dur, trebuie ales întâi *care* dintre cele trei cifre îl trece.

---

## D-007 — Stoc: include an de fabricație anterior și km 0 / demo
**Data:** 2026-08-19
**Decizie:** universul include comandă nouă, stoc an curent, stoc an anterior și km 0 / demo de la dealer oficial.
**Motiv:** în rețeaua oficială, cea mai mare parte a reducerii reale stă în stocul deja produs.
**Consecință:** `stare` devine coloană de primă clasă în dashboard, nu notă de subsol — netul nu e comparabil între o comandă nouă și un demo fără să vezi care e care.

---

## D-008 — Mărci: doar cele consacrate în România — **ÎNLOCUITĂ DE D-016**
**Data:** 2026-08-19
**Decizie:** exclus mărcile chinezești nou-intrate și premium-ul de intrare.
**Motiv (chinezești):** rețea de service tânără și valoare reziduală incertă la 5 ani — exact orizontul pe care se face departajarea (D-005).
**Motiv (premium):** rar sub 25k net; s-ar scana pentru zero rezultate.
**Deschis:** decizia merită reevaluată dacă lista filtrată scade sub ~8 modele, sau la 12 luni distanță, când reziduala mărcilor chinezești va avea primele date reale.

---

## D-009 — Cadență: scan lunar automat
**Data:** 2026-08-19
**Decizie:** sarcină programată lunară; rulări suplimentare la cerere sau la evenimente de piață.
**Motiv:** campaniile de dealer au tipic durata de o lună; trimestrial le-ar rata sistematic.
**Consecință:** raportarea în conversație e delta față de scanul precedent, nu tabelul întreg — altfel notificarea lunară devine zgomot pe care încetezi să-l citești.

---

## D-010 — Separarea politicii de interogare
**Data:** 2026-08-19
**Context:** specificația inițială (D-005) încoda o singură politică — un set fix de filtre, un vector fix de ponderi, o singură cheie de sortare. Producea un clasament, nu un instrument. Nu răspundea la „optimul pentru criteriul X în limitele Y" sau „filtrează după X,Y,Z și ordonează după preț de achiziție".
**Decizie:** filtrele și cheia de ordonare devin parametri de rulare, guvernați de `spec/query.md`. Ponderile se organizează în profile numite (`default`, `cash_minim`, `continuitate_vitara`, `economie_carburant`). Se definesc patru coloane de bani distincte: `pret_lista`, `pret_net_estimat`, `cost_total_5_ani`, `cost_pe_km`.
**Motiv:** politica proiectului și întrebarea de moment sunt lucruri diferite. Dacă fiecare întrebare re-acordează ponderile în fișierul de specificație, scanurile încetează să fie comparabile între ele — pierzi exact seria de date pentru care există proiectul.
**Consecință:** o interogare ad-hoc NU rescrie `profil_activ` și nu se salvează. O lentilă utilă repetat devine profil, printr-o intrare aici. Scorurile rămân necomparabile între scanuri (normalizare min-max pe lista curentă); comparabile între scanuri sunt doar valorile brute.
**Adăugat:** regula de atriție (fiecare filtru raportează câți candidați a eliminat) și regula Pareto (fără câștigător forțat când obiectivele sunt conflictuale). Ambele din analiza decizională multicriterială — standard, nu invenția proiectului.

---

## D-011 — Granularitatea catalogului: prag de dotări, nu nivel arbitrar
**Data:** 2026-08-19
**Context:** întrebasem dacă să catalogăm echiparea de bază, una „reprezentativă" sau toate. Toate trei variantele erau proaste: baza e adesea nevandabilă, „reprezentativă" e arbitrar, toate înseamnă 60-100 de rânduri de întreținut lunar.
**Decizie (formulată de Serban):** se definește un **prag de dotări** — minim ce are Vitara 2015: AC automat, cruise control, oglinzi și geamuri electrice, scaune față încălzite, display multimedia cu Android Auto. Rândul catalogat per model+motorizare este **cea mai ieftină echipare care satisface pragul**.
**Motiv:** transformă o alegere arbitrară într-o constrângere. Rezultatul e reproductibil (oricine reface selecția ajunge la același rând), verificabil (fiecare dotare e o valoare booleană cu sursă) și comparabil între mărci — spre deosebire de „nivelul de mijloc", care înseamnă altceva la fiecare producător.
**Consecință:** pragul devine filtru hard. Un model a cărui gamă nu-l atinge sub plafonul de preț iese din listă, indiferent cât de ieftin e. Pachetele de opțiuni sunt permise ca mod de a atinge pragul, dacă ies mai ieftine decât urcarea de nivel; prețul lor se declară separat.
**Închis 2026-08-19:** pragul include și **cameră de marșarier** (360° nu e cerut). Restul dotărilor sunt declarate opționale — nu filtrează și nu punctează. Lista de 7 dotări este completă și nu se redeschide fără o decizie nouă aici.
**Efect de preț:** camera este, în multe game, prima dotare care forțează urcarea de nivel sau adăugarea unui pachet. Împreună cu scaunele încălzite, probabil ridică rândul catalogat cu un nivel la o parte din modele — și, în consecință, prețul de referință.

---

## D-012 — Fiabilitatea: garanție (0.60) + surse independente (0.40)
**Data:** 2026-08-19
**Context:** `fiabilitate_garantie` e 0.30 din scorul default — a doua pondere ca mărime — fără o sursă de date solidă pentru jumătatea „fiabilitate".
**Decizie:** cei 0.30 se descompun în garanție (fapt publicat, `confidence: confirmed`) și fiabilitate din studii independente (`confidence: estimated`, întotdeauna).
**Motiv:** cele două jumătăți au calități de date radical diferite. Amestecate într-o singură cifră, ascund exact asta — un scor care arată la fel de solid pe ambele componente, deși una e citită dintr-un contract și cealaltă estimată dintr-un studiu făcut pe altă piață.
**Reguli de protecție:** minim 2 surse independente pentru a puncta (cu una singură, ponderea se redistribuie la garanție); studiile mai vechi de 3 ani se marchează și cântăresc mai puțin; fiabilitatea se atribuie combinației motor+cutie, nu mărcii — o marcă bună poate avea o transmisie problematică.

---

## D-013 — Kilometraj anual confirmat: 14.000
**Data:** 2026-08-19
**Decizie:** `tco.km_pe_an = 14000`, `sursa: confirmat_de_serban` (era derivat din 150.000/11).
**Consecință:** TCO-ul poate fi calculat. La acest kilometraj, diferența de consum între HEV și benzină pură contează, dar nu domină clasamentul — prețul de achiziție și fiabilitatea rămân decisive.

---

## D-014 — Rabla e o fereastră anuală, nu o reducere permanentă
**Data:** 2026-08-19
**Context:** verificare la două surse independente. Rabla 2026 e activ: start 20 iulie 2026, final 31 decembrie 2026 sau la epuizarea bugetului de 300 mil. lei. Fără componente Clasic/Plus separate — o singură grilă pe tipul de propulsie cumpărat: 10.000 lei benzină, 12.000 lei hibrid non-plug-in. Vechime minimă a mașinii casate: 8 ani (Vitara 2015 e eligibilă).
**Problema:** bugetul acoperă ~25-30.000 de vouchere și se epuizează istoric înainte de termen. Orizontul de achiziție al proiectului e explicit incert.
**Decizie:** netul estimat se calculează și se afișează în două variante — `pret_net_estimat` (cu primă) și `pret_net_fara_rabla` (fără). Ambele sunt chei de sortare.
**Motiv:** o singură coloană care include prima ar promite o reducere de ~2.000 EUR pe care, la o dată arbitrară în viitor, s-ar putea să nu o poți accesa. Diferența dintre cele două coloane e, ea însăși, informație: îți spune cât te costă să ratezi fereastra și dacă merită să sincronizezi achiziția cu deschiderea programului.
**Deschis (2 puncte, ambele cu impact pe net):**
1. ~~**Încadrarea MHEV**~~ — rezolvată parțial prin D-020: grila de hibrid (12.000 lei), `confidence: derived`, pe baza practicii Mitsubishi. De coroborat cu ghidul AFM.
2. **Durata minimă de proprietate** — niciuna dintre cele două surse consultate nu menționează una; edițiile anterioare au avut. De verificat în ghidul AFM înainte de a trata netul ca ferm.

---

## D-015 — Lungime maximă 4450 mm; tracțiunea integrală rămâne marginală
**Data:** 2026-08-19
**Context:** pragul de 4300 mm era un număr rotund, nu o măsură a ceva — Vitara are 4175. Era însă filtrul care elimina cele mai multe modele cu AWD, deci merita decis explicit.
**Decizie:** `lungime_mm.max` urcă de la 4300 la **4450**. Ponderea tracțiunii integrale rămâne neschimbată (0.05 × 0.6): confirmat că a fost o consecință a mașinii avute, nu o cerință.
**Motiv:** cele două răspunsuri se susțin reciproc. Dacă AWD-ul chiar e marginal, constrângerea de lungime nu mai are de ce să fie strânsă pentru a-l proteja — iar +275 mm față de mașina actuală e o alegere de gabarit conștientă, nu un efect colateral.
**Consecință majoră — se schimbă segmentul.** Universul include acum SUV-uri compacte propriu-zise (Qashqai, Karoq, CX-30, C-HR, Kona, Niro, Formentor), nu doar sub-compacte. Trei efecte:
1. **Filtrul care leagă lista nu mai e lungimea, ci prețul la pragul de dotări.** E o îmbunătățire: constrângerea activă devine una cu sens economic, nu una geometrică arbitrară.
2. Lista de verificat aproape se dublează, ~30 de modele. Multe vor fi eliminate de buget, dar asta se află abia după verificare.
3. Profilul `continuitate_vitara` își pierde din utilitate — ponderea lui de 0.40 stă pe `bonus_mostenit`, care e în mare parte AWD. Rămâne în specificație ca lentilă validă, dar probabil nefolosită.
**Deschis:** cu gabaritul relaxat, merită verificat dacă pragul minim de 3900 mm mai are vreun rol. Nu a eliminat nimic până acum.

---

## D-016 — Fără filtru de marcă; bugetul devine marcaj, nu eliminator
**Data:** 2026-08-19
**Înlocuiește:** D-008 (universul de mărci). Amendează D-011 (regula de excludere a modelelor).

**Corecție de provenință.** Lista de 17 mărci din D-008 era **sinteza asistentului, nu o cerință a lui Serban**. Întrebarea pusă ("ce mărci intră în universul de căutare?") oferea o opțiune numită „mărci consacrate în RO", iar conținutul concret l-a inventat asistentul. Serban a corectat: *„nu țin minte să fi pus eu o listă cu modele, poate intra orice model în parametrii listați."* Eroarea merită notată pentru că e ușor de repetat: un răspuns la o întrebare cu variante nu autorizează detaliile pe care le-a pus în variantă cel care a întrebat.

**Decizie 1 — marca nu mai e filtru.** `brand_universe` dispare. Apartenența la catalog se decide exclusiv prin `hard_filters` (caroserie, propulsie, lungime, putere, dotări). Intră ASX, Jeep, mărcile nou-intrate — orice, dacă trece parametrii.

**Decizie 2 — prețul nu mai e filtru.** Un model care bifează pragul de dotări dar depășește 25.000 EUR net rămâne în catalog, marcat `in_buget: false`, cu rol de **referință**. Interogarea implicită îl ascunde; se cere explicit. Formularea lui Serban: Qashqai și Karoq *„nu vor bifa niciodată sub 25.000 euro, dar nu costă nimic (câțiva tokeni în plus) să le avem în listă."*

**Principiul general, care se aplică dincolo de aceste două cazuri:** un filtru care încodează o **incertitudine**, nu o **cerință**, trebuie să fie marcaj, nu eliminator. Excluderea mărcilor fără istoric în RO încoda „nu știm cât valorează la 5 ani" — o incertitudine. Mutată în filtru, devenea invizibilă și netestabilă; mutată în scor, se poate cuantifica, verifica și corecta. Același lucru pentru buget: un rând peste plafon îți spune ce cumperi cu 3.000 EUR în plus, informație pe care filtrul o distrugea.

**Consecință:** preocupările reale din D-008 nu dispar — mărcile fără istoric pe piața românească primesc `rezidualа_incerta: true` și o penalizare la componenta de fiabilitate/garanție. Costul rămâne vizibil; nu mai e o ușă închisă.

**Consecință operațională:** lista de verificat crește. Asumat explicit de Serban ca fiind ieftin.

---

## D-017 — Putere până la 200 CP; proveniența ca trei câmpuri, nu unul
**Data:** 2026-08-19

**Decizie 1 — `putere_cp.max` urcă de la 150 la 200.**
**Efect secundar util:** intervalul de cuplu preferat (200-300 Nm, D-006) devine coerent cu puterea. La plafonul de 150 CP, foarte puține motorizări din segment atingeau 250 Nm — specificația se contrazicea singură. Acum nu se mai contrazice.
**Efect principal, mai puțin plăcut:** puterea și prețul sunt puternic corelate, deci majoritatea modelelor nou-admise intră în tranșa de referință, nu în buget. Practic, ridicarea plafonului adaugă ancore de comparație, nu opțiuni accesibile. Ceea ce e în regulă — rândurile de referință sunt ieftine prin construcție (D-016).
**Se recuperează câteva AWD-uri:** Škoda Karoq 2.0 TSI 4x4, VW T-Roc 2.0 TSI 4Motion, Toyota C-HR AWD. Toate în tranșa de referință.

**Decizie 2 — proveniența se stochează în trei câmpuri: `marca_origine`, `grup_proprietar`, `tara_asamblare`.**
**Context:** cerința era o coloană de proveniență, ca să se poată filtra oricând „fără chinezești".
**Motiv:** „fără chinezești" înseamnă trei liste diferite, iar alegerea greșită taie exact ce nu voiai să tai. MG e marcă britanică, capital chinezesc (SAIC), producție în China. Volvo și Polestar sunt mărci suedeze deținute de Geely. Dacia e marcă românească deținută de Renault, cu producție în România. Un singur câmp ar fi forțat o alegere între trei întrebări diferite, făcută de mine, nedeclarată.
**Consecință:** niciunul dintre cele trei nu e filtru implicit. Se completează toate, se filtrează pe care vrei, când vrei. O valoare necunoscută rămâne `null` — nu se ghicește din siglă.

**Decizia de a NU elimina mărcile chinezești acum.** Alternativa oferită era eliminarea lor dacă încarcă prea mult motorul de căutare. Nu o iau, pentru că sarcina reală e ~5-6 modele din ~40 — sub 15% din efortul de scanare, adică sub pragul la care ar merita pierdut opționalul. Cu cele trei câmpuri de proveniență, filtrarea e oricum gratuită și reversibilă, în timp ce eliminarea din catalog nu e: un model nescanat nu poate fi readus retroactiv în serie de date. Asimetria decide.

---

## D-018 — Trei corecții impuse de prima verificare reală
**Data:** 2026-08-19
**Context:** primele patru surse citite (Suzuki ×2, Toyota, Dacia) au invalidat trei presupuneri din specificație. Toate trei erau presupuneri implicite — genul care nu se vede până nu lovește date reale.

**1. Broșura tehnică devine sursa autoritativă pentru dotări.**
Bifele de dotări extrase din listele de preț sunt nesigure: pentru Yaris Cross a rezultat că *niciun* nivel nu are simultan scaune încălzite și Android Auto — implauzibil, artefact de extragere. Prețurile din aceleași PDF-uri s-au dovedit fiabile. Deci sursele se specializează: lista de preț pentru bani și motorizări, broșura tehnică pentru dotări, configuratorul doar ca arbitru la cazurile de limită. Alegerea păstrează scanul lunar automat — un configurator JS-heavy ar fi cerut browserul lui Serban deschis, deci supraveghere.

**2. Vârsta sursei devine câmp, nu presupunere.**
Trata­sem „sursă oficială" ca `confidence: confirmed` uniform. Lista de prețuri de pe `suzuki.ro` era datată **01.06.2024** — peste doi ani, publicată fără niciun avertisment. Regulă nouă: fiecare document poartă `data_document`; peste 12 luni vechime coboară automat la `estimated`.

**3. Un preț afișat nu e neapărat preț de listă.**
`dacia.ro` afișează „de la 17.100 EUR" cu Rabla și reducerile comerciale **deja incluse**. Tratat ca listă, ar fi scăzut Rabla a doua oară — model cu ~2.000 EUR mai ieftin decât e. Fiecare preț preluat poartă acum `tip_pret`: `lista` | `net_promotional` | `necunoscut`. Un preț `net_promotional` intră direct ca net, fără scăderi suplimentare. Când pagina nu spune, `tip_pret` e `necunoscut` — nu se deduce din mărimea cifrei.

**Observație de metodă.** Toate trei au apărut din patru surse. Rata sugerează că restul celor 37 de modele vor produce încă asemenea corecții — argument pentru a rula verificarea în loturi mici cu revizuire, nu într-o singură trecere lungă.

---

## D-019 — Monotonia dotărilor pe scara de echipare
**Data:** 2026-08-19
**Decizie (formulată de Serban):** o dotare prezentă la un nivel de echipare se consideră prezentă și la nivelurile superioare, chiar dacă nu e listată explicit acolo.

**Motiv, mai puternic decât pare.** Nu e o prezumție de comoditate, ci modul corect de a citi sursa. Producătorii publică nivelurile ca **deltă** — tabelele și materialele de prezentare spun „ce primești în plus față de Expression", nu recapitulează întregul. Absența unei dotări la un nivel superior înseamnă, în acest format, „nu se repetă", nu „nu există". Fără regulă, un parser citește delta ca listă completă și produce exact eroarea observată la Yaris Cross: niveluri superioare care par să *piardă* dotări.

**Validare independentă la prima aplicare.** Regula prezice că Yaris Cross BUSINESS are Integrare Smartphone (prezentă la ACTIVE) plus scaune încălzite (nou la BUSINESS). Interogarea directă a documentului, cu cerere de citat exact, a confirmat: *„Scaune incalzite pentru sofer si pasager"* la BUSINESS, *„Integrare Smartphone"* preluat de la ACTIVE. Predicția și verificarea au coincis.

**Rezerva — scara nu e întotdeauna monotonă.** Nivelurile *laterale* nu sunt trepte superioare, ci variante paralele, iar la ele regula nu se aplică:
- orientate sportiv (GR Sport, N Line, R-Line, VZ) — pot înlocui scaunele încălzite cu scaune sport neîncălzite;
- orientate off-road (Adventure, Extreme, Trail) — pot renunța la dotări de confort;
- orice două niveluri la același preț — sunt variante, nu trepte.

**Consecință:** o dotare stabilită prin propagare primește `confidence: derived`, niciodată `confirmed`, și poartă `metoda: monotonie` în `dotari_verificate`. Se vede întotdeauna ce a fost citit și ce a fost dedus.

**Amendament la D-018.** Concluzia de acolo — „bifele de dotări din listele de preț sunt nesigure" — era prea largă. Cauza reală a eșecului de la Yaris Cross a fost dublă: un format de tip deltă citit ca listă completă (rezolvat de această regulă) și o interogare prea vagă a documentului (rezolvată prin cererea de citat exact și permisiunea explicită de a răspunde „nu apare în document"). Broșura tehnică rămâne sursă preferată pentru dotări, dar lista de preț redevine utilizabilă când e interogată corect. **Prima ipoteză de eroare, la o extragere implauzibilă, este metoda de interogare — nu sursa.**

---

## D-020 — Prețul devine mulțime de observații, nu scalar
**Data:** 2026-08-19
**Context (semnalat de Serban):** același ASX apare la 20.091 EUR pe pagina importatorului, 19.526 la Țiriac și 18.980 pe alt site — „nu sunt sigur dacă are aceeași motorizare".

**Decizie:** un model nu are un preț, are `observatii_pret[]` — câte o intrare per sursă, fiecare cu identitate proprie, `tip_pret`, `valabil_pana`, dată și confidence. Prețul de lucru e un agregat derivat, nu un câmp primar.

**Motiv:** dispersia din rețeaua oficială nu e zgomot de curățat, e informația centrală. Un model cu 1.000 EUR dispersie are marjă de negociere; unul fără nu are. Colapsat într-un singur număr, semnalul dispare.

**Regula critică — identitatea înainte de comparație.** O observație intră în comparație doar cu cheia completă: echipare + motorizare + cutie + tracțiune. Cheie incompletă → carantină, nu minim.
**Motivul e statistic, nu igienic:** anunțul cel mai ieftin este sistematic cel mai puțin specificat. Un `min()` naiv selectează, în medie, listingul care omite detaliile, și produce un preț de referință care nu corespunde niciunei mașini reale. Exact intuiția lui Serban („nu sunt sigur dacă are aceeași motorizare"), ridicată la regulă.

**Verificare pe cazul ASX, 2026-08-19.** Sub aceeași denumire „ASX Intense StyleCold" există trei mașini diferite: 1.3 DI-T **manual** la importator (20.091 EUR cu Rabla), 1.3 DI-T **7DCT** la Țiriac (25.366 EUR, nou), 1.8 **HEV** la Țiriac (26.741 EUR, test-drive). Interval aparent 6.650 EUR; dispersie reală de dealer: **necunoscută**, pentru că sunt mașini diferite. Comparate direct, fabrică o reducere inexistentă. Dispersia se calculează doar în interiorul unei chei; sub două observații pe aceeași cheie e `null`, nu `0` — absența datelor nu e absența variației.

**Trei constatări secundare, toate cu valoare de regulă:**
1. **Ofertele expirate rămân publicate.** Pagina oficială Mitsubishi afișa pe 19 august o ofertă marcată „valabilă până la 31 Iulie 2026". `valabil_pana` devine câmp obligatoriu; data trecută → `confidence: estimated`.
2. **Demo nu înseamnă mai ieftin.** La același dealer, exemplarul de test-drive era mai scump decât unul nou — alt motor. Se verifică pe aceeași cheie, niciodată presupus.
3. **Ambiguitatea MHEV din D-014 s-a rezolvat, parțial.** Mitsubishi aplică ecotichet de 2.294 EUR (≈12.000 lei, grila hibrid) pe ASX 1.3 DI-T MHEV — nu 10.000 lei. Prezumția conservatoare din D-014 se înlocuiește cu `mhev_incadrare: hibrid_non_plugin`, `confidence: derived`. E practica unui importator, nu textul ghidului AFM; rămâne de coroborat.

**Notă despre exemplul original.** Nu am regăsit cifrele de 19.526 și 18.980 — la Țiriac am citit 25.366 și 26.741. Posibil pagini diferite, filtre Rabla aplicate, sau conținut schimbat între timp. Consemnat ca atare, nu reconciliat prin presupunere.

---

## D-021 — Reducerea are și ea o identitate — **PARȚIAL CORECTATĂ DE D-022**
> Clasificarea „Remat" ca schemă privată distinctă este greșită; vezi D-022.
> Restul deciziei (taxonomie, necumulare, `model_year`, showroom) rămâne valabil.
**Data:** 2026-08-19
**Extinde:** D-020 (identitatea mașinii). **Sursă:** capturi de ecran furnizate de Serban, care au corectat citirea mea automată.

**Ce s-a văzut efectiv pe cele trei pagini:**

| Sursă | Preț | Mașina | Reducerea aplicată |
|---|---|---|---|
| mitsubishi-motors.ro | 20.091 € | ASX **MY26** 1.3 DI-T MT MHEV Intense StyleCold | discount 3.432 € + **Rabla 2026** 2.294 € |
| tiriacauto.ro | 19.526 € | ASX 1.2 DI-T MT MHEV Intense StyleCold | *„cu TVA și **Remat** incluse"* |
| mtrgroup.ro | 18.980 € | ASX **MY23** **1.0L MT Inform** (benzină, fără MHEV) | discount 2.737 € + **„Ecotichet Mitsubishi"** 1.000 € |

**Descoperirea principală: „ecotichet" nu înseamnă Rabla.**
`mtrgroup.ro` are o coloană numită **„Ecotichet Mitsubishi"**, valoare fixă −1.000 € pe toate versiunile, inclusiv PHEV. Nu e prima de casare a statului (10.000/12.000 lei), e voucherul propriu al importatorului. Numele îl imită pe cel oficial. `tiriacauto.ro` folosește **„Remat"** — o a treia schemă, privată. Un scan care le tratează pe toate ca aceeași linie produce un net fals în ambele direcții.

**Decizie 1 — taxonomie de reduceri.** Fiecare reducere primește `tip_reducere`: `rabla_stat` | `bonus_producator` | `bonus_dealer` | `discount_comercial` | `reducere_showroom`. Tipul se stabilește după **cine o dă**, nu după cum se numește.

**Decizie 2 — regula de necumulare.** Reducerile de casare presupun predarea unei mașini, iar Serban are una singură. Două astfel de reduceri nu se însumează decât dacă sursa spune explicit că sunt cumulabile; altfel se reține cea mai mare, restul se consemnează cu `aplicata: false`. `cumulabil: null` se tratează ca „nu cumula", nu ca „probabil da". Fără regula asta, un net ar putea aduna Rabla de stat cu ecotichetul Mitsubishi și cu Remat — ~3.300 € de reducere pentru o singură mașină predată.

**Decizie 3 — `model_year` intră în cheia de identitate.** Tabelul de pe mtrgroup.ro e marcat **„VERSIUNE ASX MY23"** și era publicat în august 2026. Fără MY în cheie, o listă veche de trei ani de model intră în comparație ca ofertă curentă — exact ce a produs cifra de 18.980.

**Decizie 4 — reducerea de showroom nu se estimează.** Aceeași pagină spune: *„Alege acum un model din stoc, cu livrare imediată și beneficiezi de o reducere suplimentară, în showroom!"* Reală, necuantificată. Nu se estimează și nu se presupune zero: se marchează `reducere_showroom_disponibila: true`, ca semnal de marjă. **Este limita superioară a ce poate ști un motor de căutare web** — restul se află la telefon, iar proiectul trebuie să spună asta, nu să pretindă precizie pe care n-o are.

**Conflict nerezolvat.** Țiriac scrie „ASX **1.2** DI-T MT MHEV", importatorul scrie „**1.3** DI-T". Gama ASX (bază Renault Captur) nu are motorizare 1.2 — probabil eroare de redactare la dealer. Ambele valori păstrate; nu se corectează tăcut.

**Închide nota deschisă din D-020.** Cifrele lui Serban (19.526, 18.980) nu erau de negăsit — erau pe pagini de campanie și pe un tabel MY23 pe care căutarea automată nu le indexase. Lecție: **listingurile de stoc ale unui dealer nu conțin campaniile lui.** Landing page-urile de campanie sunt o clasă de sursă separată, care trebuie căutată explicit.

---

## D-022 — „Remat" este Rabla. Clasificarea se face pe valoare, nu pe nume.
**Data:** 2026-08-19
**Corectează:** D-021, care trata „Remat" ca schemă privată distinctă.

**Corecția (Serban):** „Rabla" e numele oficial; „Remat" e numele firmei care operează radierea mașinilor casate, folosit colocvial de dealeri pentru aceeași primă de stat. Prezumția implicită trebuie să fie **sinonimie**, nu schemă nouă, dacă cele două denumiri nu apar în aceeași ofertă.

**Confirmare aritmetică.** Țiriac afișa 19.526 € pentru ASX MT MHEV Intense StyleCold, importatorul 20.091 € pentru practic aceeași configurație cu Rabla de 2.294 € inclusă. Dacă „Remat" ar fi fost un voucher privat mic **în locul** Rabla, Țiriac ar fi trebuit să fie *mai scump*, nu cu 565 € mai ieftin. Explicația simplă — aceeași primă de stat, plus un discount de dealer ceva mai mare — se potrivește cu datele. Cea complicată nu.

**Dar numele rămâne dovadă slabă în ambele direcții**, iar regula de sinonimie singură ar fi înghițit și cazul „Ecotichet Mitsubishi". De aceea procedura are trei teste, în ordine:

1. **Testul valorii.** Grila Rabla 2026 e cunoscută (10.000 / 12.000 / 15.000 / 18.500 lei, după propulsie). O reducere a cărei valoare se potrivește **este** `rabla_stat`, oricum s-ar numi. O valoare care nu se potrivește **nu este**, oricum s-ar numi.
2. **Testul co-ocurenței** (regula lui Serban). Două denumiri în aceeași ofertă sau frază = reduceri distincte. Denumiri pe pagini diferite = sinonime, nu se dublează.
3. **Testul emitentului**, dacă pagina îl declară.

Când valoarea nu e defalcată — cazul „Remat", unde prețul e dat direct net — testul 1 nu poate rula și decide testul 2.

**Rezultatul pe cazul ASX:**
- **„Remat" → `rabla_stat`.** Apare singur, fără defalcare, cu preț final plauzibil ca Rabla. Testul 2.
- **„Ecotichet Mitsubishi" → `bonus_producator`, confirmat.** 1.000 € **fix pe toate versiunile, inclusiv PHEV**. Nicio valoare din grila Rabla nu e 1.000 €, iar o primă de stat *variază* cu propulsia — aceasta nu variază. Testul 1, decisiv. Tabelul e și MY23, dintr-o perioadă în care importatorul rula propriul bonus.

**Lecția de metodă.** Prezumția mea implicită fusese „nume diferit = lucru diferit", care multiplică entitățile inutil. A lui Serban e „nume diferit = același lucru, până la proba contrară", care le colapsează prea repede. Combinația — **clasifică pe valoare, dezambiguizează pe co-ocurență** — e mai robustă decât oricare dintre ele singură, pentru că se sprijină pe cifra publicată, nu pe vocabularul comercial.

---

## D-023 — Ce a arătat primul scan real (15 modele, 47 surse)
**Data:** 2026-08-19

**D-022 confirmată independent, pe sursă oficială.** Pe `hyundai-motor.ro`, pagina oficială a importatorului, reducerea se numește **„Remat"** și valorează **1.905 EUR** — consistent pe toate nivelurile. Grila Rabla benzină e 1.907 EUR. Delta: 2 EUR. Corecția lui Serban era corectă, iar testul valorii o confirmă fără ambiguitate.

**Testul valorii a funcționat de 11 ori din 11.** Șapte reduceri au fost identificate corect ca primă de stat sub cinci denumiri comerciale diferite (Remat, Ecotichet, Ecoticket, Rabla Clasic, Rabla ecotichet), cu delta maximă de 2 EUR față de grilă. Patru au fost respinse deși poartă numele: „Rabla by Nissan" (2.000 €, declarată explicit ca 1.500 importator + 500 dealer), „Rabla de la Ford" (2.000 €, iar Ford oferă *separat* și Ecotichetul real de 12.000 lei), „REMAT/Ecotichet 2025" MG (2.400 €), „Ecotichet Mitsubishi" (1.000 €). **Fără testul valorii, patru discounturi comerciale ar fi intrat în net ca primă de stat.**

**Listele de prețuri expirate sunt sistemice, nu excepționale.** Din 15 modele: `ford.ro` publică o listă datată **21.09.2020** (MY21.25) — aproape șase ani, pe domeniul oficial, fără avertisment, și contrazice pagina de campanie curentă pe dotările standard; `suzuki.ro` — 01.06.2024; `hyundai-motor.ro` — valabilitate expirată 31.07.2026; `mitsubishi-motors.ro` — ofertă expirată 31.07.2026; `mtrgroup.ro` — tabel MY23. Contraexemplu: `skoda.metrotehnica.ro` publică `Pret-Skoda-Kamiq_CW32_2026_MY27.pdf` — datat pe săptămâna curentă. **Regula vârstei sursei nu e o precauție, e filtrul principal de calitate.**

**Descoperire care schimbă lista: Hyundai Bayon iese din catalog.** Trei surse oficiale Hyundai RO convergente arată că în august 2026 Bayon se vinde în România **doar cu 1.0 de 90 CP** — sub pragul de 100 CP. Ironia metodologică: Bayon e singurul model din tot lotul care atinge pragul de 7 dotări **standard, fără niciun pachet** (nivelul Led Line). Rândul rămâne în catalog marcat `EXCLUS_DIN_CATALOG` cu motivul, nu șters — dacă gama se schimbă, revine.

**SEAT Arona, risc serios de excludere.** Pe `seat.ro`, chiar treapta FR (vârf de gamă, de la 28.825 EUR) e listată explicit doar cu *„Senzori de parcare spate"* — senzori, nu cameră. Nicio mențiune de cameră de marșarier pe niciun nivel. Dacă se confirmă, modelul iese pe o dotare de 300 EUR.

**Reducerile VW Group sunt aproape integral condiționate de finanțare captivă.** „Avantaj de preț Porsche" 5.400 € (T-Cross) și 5.800 € (Taigo) cer obligatoriu Porsche Finance **plus** Porsche Asigurări. Skoda „Drive Bonus" 1.600 € cere Casco Porsche. Conform `price-model.md`, niciuna nu intră în net. **Consecință practică: prețurile promoționale VW Group nu sunt comparabile cu cele ale altor mărci** — arată cu 5.000 € mai bine decât sunt, pentru cine nu ia finanțarea lor.

**Pragul de dotări e într-adevăr filtrul care leagă lista, cum anticipasem.** Din 15 modele: 10 ating pragul (4 dintre ele doar prin pachet opțional plătit), 5 rămân nedeterminate, 1 iese pe putere. Cea mai frecventă cauză de descalificare a nivelului de bază: **climatizarea manuală** (Dacia Essential, Kia Urban, Nissan Acenta, Renault Evolution, Hyundai Comfort).

**Dispersia de dealer nu s-a putut calcula pentru niciun model** — nu s-au găsit două observații pe aceeași cheie completă. Rămâne `null`, nu `0`, conform D-020.

**Eșec de infrastructură, nu de metodă.** Lotul Stellantis (Jeep Avenger, Opel Mokka, Fiat 600, Peugeot 2008) nu a rulat: agentul de verificare a fost oprit de o limită de buget a organizației. Consemnat în `models.json → neverificate` și în `sources_failed`, ca să nu arate ca „modele fără date".

---

## D-024 — Scriptul de build: `latest.json` e derivat, nu stocat
**Data:** 2026-08-19
**Context:** HANDOFF §2 cere un `build.py` care produce `data/latest.json` din `models.json` (catalog stabil) + `scans/scan-<max(data)>.json` (observații volatile) + `criteria.yaml` (praguri, ponderi). Nimic din output nu se editează manual.

**Decizie — regulile concrete de derivare, toate implementate și testate:**
1. **Join pe cheia de identitate** `model_year|echipare|motorizare|cutie|tractiune`. O observație a cărei echipare sau motorizare lipsește/e placeholder, sau care nu se potrivește cu nicio configurație din catalog, merge în `carantina[]`. O cheie *parțială* (lipsesc doar cutie/tracțiune) se atașează rândului cu marcaj `cheie_partiala`, dar e exclusă din calculul dispersiei (D-020).
2. **Potrivirea de marcă tolerează alias-uri** (`volkswagen`↔`vw`) și potrivire pe substring de model — altfel observațiile „VW T-Cross" nu s-ar fi atașat catalogului cu marca „Volkswagen".
3. **Net = `pret_lista` − discount necondiționat − Rabla.** Rabla se clasifică pe **valoare** (grila `pret.rabla.prima_eur` din criteria), o singură primă, niciodată cumulată (D-021/D-022). Reducerile condiționate de finanțare captivă stau pe linia separată `reduceri_conditionate` cu `EXCLUS_DIN_NET`, nu intră în net (D-004).
4. **Prețul de listă al unei configurații** = `pret_eur` (catalog) + `optiuni_incluse_eur`. Când echiparea cere un pachet dar prețul pachetului e `null`, rândul primește `pachet_pret_necunoscut` și eticheta „limită INFERIOARĂ" — nu se extrapolează (CLAUDE.md §8.2).
5. **Dispersia** se calculează doar în interiorul cheii complete, cu cutie/tracțiune moștenite din catalog când observația le omite; sub două observații pe aceeași cheie → `null`, niciodată `0` (D-020).
6. **Scorurile** min-max pe universul filtrat curent, per profil. Ponderile ne-numerice (`descriere`) se ignoră; componentele `null` se elimină cu re-normalizarea ponderii și `acoperire_pondere` raportat; valorile brute se exportă pentru re-normalizare în dashboard. Antetul declară explicit că scorurile **nu** sunt comparabile între scanuri.
7. **TCO rămâne `null`** peste tot: `tco.pret_benzina_eur_l` e `null` **și** lipsesc `consum_real_l100`/`valoare_reziduala`/costurile de întreținere pe majoritatea rândurilor. Sortarea implicită cade pe `pret_net_estimat` (HANDOFF §2, opțiunea 2); `diagnostic.tco` enumeră ce lipsește. Nu se inventează prețul benzinei (CLAUDE.md §8.1).
8. **Zero praguri hardcodate** — un test de CI face grep pe literalele din criteria după ce scoate string-uri, docstring-uri și comentarii (un prag real e un token numeric în cod, nu în text).

**Motiv:** `latest.json` e un derivat pur; orice prag dublat în cod divergează în șase luni (CLAUDE.md §3). Carantina protejează seria de bias-ul `min()`-naiv (D-020): anunțul cel mai ieftin e sistematic cel mai puțin specificat.

**Consecință:** `latest.json` se regenerează, nu se editează niciodată manual. Acoperirea de ponderi e slabă la scanul curent (default 0.40, `economie_carburant` 0.20) — raportată onest în `diagnostic.profiluri_slabe`, nu ascunsă. 8 teste (`tests/test_build.py`) acoperă minimul HANDOFF §2 plus invariante de dispersie și end-to-end.

---

## D-025 — Trei modele verificate pe web intră în catalog ca rânduri nedeterminate, nu în lista neagră
**Data:** 2026-08-19
**Context:** Serban a cerut explicit *„As vrea Ford Puma Jeep Avenger si Seat Ateca in lista curenta, nu in lista neagra"* și *„Verifică-le întâi pe web"*. HANDOFF §4 marchează Ford Puma (listă 2020 vs campanie 2026) și SEAT Arona ca fiind cele care contează pentru decizie; Jeep Avenger era în `neverificate[]` (lotul Stellantis oprit de o limită de buget). Verificarea s-a făcut în IDE (§5: cotă separată).

**Decizie — o singură trecere append-only în `data/models.json` (17 rânduri acum, de la 15):**
1. **Ford Puma — corectat, rămâne nedeterminat.** Contradicția-cheie din HANDOFF §4 (AC manual în PDF-ul datat 2020-09-21 vs AC automat pe campania 2026) e **REZOLVATĂ**: faceliftul din feb. 2024 a făcut climatizarea automată standard pe Titanium, confirmat pe pagina `ford.ro` curentă (© 2026) cu Titanium numit; delta de preț manuală/automată de pe acea pagină e **cutia**, nu AC-ul (verificat dublu, doi agenți independenți). PDF-ul 2020 e pre-facelift, încă găzduit dar nereîmprospătat. `echipare_selectata` → `Titanium` (estimated). Adăugat `dotari_verificate` (matrice de 8 dotări, sursă per câmp). **Pragul rămâne `null`** — 3 goluri necertificabile la Titanium: geamuri electrice (neregăsite prin nume în nicio sursă), cameră de marșarier (surse curente în conflict, ambele păstrate), scaune încălzite (doar prin Pachet Iarnă plătit, preț necunoscut la Titanium — nu se extrapolează din prețul de la ST-Line X, CLAUDE.md §8.2). Variantă ST corectată la 170 CP (`160` la Autocritica.ro e eroare; 3 surse dau 170). Garanție: conflict păstrat (5 ani/100.000 km ford.ro vs 4 ani/150.000 km dealer), bază producător 2 ani.
2. **Jeep Avenger — mutat din `neverificate[]` în catalog, rând nedeterminat.** Sursa principală `autotestmagazin.ro` 2024-01-23 (>12 luni → `estimated`, D-018). Rezultatul deciziei: **certificabil doar peste buget.** Longitude (~22.500 EUR MT) are doar „aer condiționat" (nu automat) → cade pe prag; Altitude (~24.500 EUR MT), singurul sub plafon, are climatizare automată + pilot adaptiv confirmate, dar scaune încălzite / cameră / geamuri-oglinzi electrice / Android Auto **nu apar** la acel nivel; Summit le are (per `green.start-up.ro` 2025-03-03), dar ~30.000 EUR. Prag `null`. Putere/cuplu/lungime/garanție = `null` (articolul dă preț și dotări pe nivel, nu specificația tehnică — nu se scrie o cifră neverificată, CLAUDE.md §8.1).
3. **SEAT Ateca — rând nou nedeterminat.** Pragul nu se poate certifica pe niciun nivel (scaune încălzite neconfirmate nicăieri; cameră în conflict live-vs-catalog, ambele păstrate); fără preț FR confirmat; FR (~32.228 EUR+) oricum peste plafon. Prag `null`.

**Mecanica de clasificare:** niciun rând nou nu are nevoie de cod special — `build.py` marchează automat `rand_nedeterminat = (prag_dotari_atins is None)` și îi anulează scorul (D-011). Toate trei ies cu `scoruri: None`, nescorate, dar prezente și cu dotările verificate expuse. Regenerat `latest.json` (17 modele, 9 în universul de scor — neschimbat, cele 3 fiind nedeterminate). 8 teste trec.

**Ce am refuzat să fac (și de ce):**
- **Nu am editat `scan-2026-08-19.json`** (append-only, HANDOFF §6.3). Prețurile Avenger găsite sunt din 2024 (stale); nu le-am injectat în pipeline printr-un al doilea fișier de scan pe aceeași dată. Motiv suplimentar: `find_latest_scan` ia un singur fișier max-dată, iar un rând cu `echipare_selectata: null` și 3 observații pe trim-uri diferite (Longitude/Altitude/Summit) ar produce un agregat de preț fără sens. Prețurile rămân aici, ca **proveniență**: Longitude 22.500/25.000 · Altitude 24.500/27.000 · Summit 30.000 EUR (`autotestmagazin.ro` 2024-01-23, `automarket.ro`). Când Avenger va fi în `sources.yaml`, scanul lunar le va prinde proaspete.
- **Nu am schimbat politica de build.** O observație notabilă rămasă pentru Serban: Puma are în scan **și** `20800 lista` (2020, stale) **și** `16800 net_promotional` (campania 2026, curentă, confirmată). Pipeline-ul afișează netul 18.512 EUR derivat din **lista stale 2020**, nu promoul curent 16.800. E consecința regulii „net = listă − Rabla" (D-024 pct. 3); tratarea `net_promotional` ca preț primar de afișare e o **decizie de politică de build**, nu o corectură tăcută — o las lui Serban. Dashboard-ul va arăta oricum vârsta sursei (`data_document: 2020-09-21`), deci discrepanța e vizibilă, nu ascunsă.

**Motiv:** un model peste plafon sau necertificabil e `nedeterminat`/`in_buget:false`, niciodată *absent* (CLAUDE.md §10, D-016): un rând de referință costă câțiva tokeni, o presupunere netestată costă mai mult. Cerința lui Serban („în lista curentă, nu în lista neagră") coincide cu politica proiectului.

**Consecință:** catalogul are acum rândurile pe care se poate verifica de ce Puma/Avenger/Ateca nu se califică ferm, în loc de goluri. Task 3 (dotări) închis pentru aceste trei; rămân randurile de referință Opel Mokka/Frontera, Citroën C3 Aircross, SEAT Arona, Suzuki S-Cross, VW T-Cross/Taigo.

---

## D-026 — Dashboard-ul: un singur fișier cu date injectate, generat de build.py
**Data:** 2026-08-19
**Context:** Task 2 (HANDOFF §3). Trebuia un dashboard care să respecte contractul de interogare (`query.md` §8) fără să devină „a doua specificație", accesibil și offline (dublu-click), și online (telefon). Sesiunea anterioară a murit pe erori API exact la începutul acestei sarcini.

**Decizie:**
1. **Datele se injectează inline, nu prin `fetch`.** `build.py` capătă un pas nou (`render_dashboard`) care înlocuiește marcajul `__NCAR_DATA__` din `dashboard/template.html` cu `latest.json` și scrie `dashboard/index.html`. Sursa e `template.html` (versionabil, editabil); `index.html` e derivat, ca `latest.json` — nu se editează manual.
2. **Motiv fetch→inline:** pe `file://` CORS blochează `fetch`, deci un dashboard cu `fetch('latest.json')` n-ar merge la dublu-click. Cu datele inline, fișierul merge oriunde: local, stick, email, telefon, offline. `<` din JSON se escapează `<` ca să nu rupă `</script>`; injecția e cu un marcaj unic (`__NCAR_DATA__`, o singură apariție), nu `replace`-all.
3. **Panoul de filtre se generează din `config.query.filtrabile`**, nu dintr-o listă scrisă în HTML — dashboard-ul nu poate exprima ceva ce contractul interzice.
4. **Un câmp din `filtrabile` fără corespondent în date → control dezactivat + marcat, niciodată filtru mut.** Mecanism general: dacă niciun rând nu produce valoare pentru cheie (sau cheia nu e mapată), filtrul se dezactivează cu motiv vizibil. Prinde automat `stare`, `consum_real_l100`, `portbagaj_l`, `disponibil_bucuresti`, `cost_total_5_ani` (toate null) **și homoglifa `rezidualа_incerta`** (marcată suplimentar „caractere non-ASCII — vezi DECISIONS"). Asta onorează promisiunea din întrebarea deschisă de mai jos, fără să atingă `criteria.yaml`.
5. **`in_buget` e filtru cu 4 stări, nu boolean.** `stare ∈ {da, doar_cu_rabla, nu, nedeterminat}`. Filtrul implicit `in_buget:true` = pre-bifează `{da, doar_cu_rabla}` (= `cu_rabla`, coincide cu `build.py:698`). Alegerea păstrează vizibil nuanța `doar_cu_rabla` (4 modele care intră doar cu prima), în loc s-o aplatizeze.
6. **Sortarea implicită cade grațios.** `sort_default=cost_total_5_ani` e null peste tot (TCO necalculabil) → se trece automat pe `sort_secundar=pret_net_estimat`, cu notă vizibilă (HANDOFF §2, opțiunea 2).
7. **Vizibilitatea încrederii:** fiecare celulă `{v,c}` e stilată după `confidence` (confirmed/derived/estimated/null) cu icon+etichetă (paletă de status — culoarea nu poartă singură sensul), plus sursa și vârsta în tooltip. Scorul poartă un badge de `acoperire_pondere` (roșu sub 50%).
8. **Acces online:** publicat ca Artefact Claude (URL instant, telefon) — `https://claude.ai/code/artifact/64964d22-8d48-4971-aa5b-dcfd1d772932`. GitHub Pages rămâne pregătibil (repo `git@github.com:serbantica/new_car.git`), dar activarea cere re-auth `gh` (token invalid la data asta).

**Motiv:** aceleași principii ca `latest.json` derivat (D-024) — o sursă editabilă, un derivat regenerabil; plus regula anti-duplicare (niciun prag în HTML, tot din `DATA`).

**Consecință:** `dashboard/` populat (`template.html` + `index.html`, 193 KB). 8 teste trec neschimbate (grep-ul de praguri scanează doar `build.py`, `test_build.py:26`). TCO rămâne blocajul vizibil: dashboard-ul arată onest că lipsește, nu inventează o cifră.

## D-027 — Închiderea Task-ului 3: Verificarea și catalogarea celor 6 modele de referință rămase
**Data:** 2026-08-20
**Context:** HANDOFF §4 și cerința directă a lui Serban privind Task 3 (S-Cross, Arona, T-Cross, Taigo, Mokka, Frontera, C3 Aircross).

**Rezultatele verificării celor 6 modele (20 de modele în catalog acum, de la 17):**

1. **Suzuki S-Cross — clarificat, atinge pragul în buget (`in_buget: true`):**
   - Echiparea **Passion** include **toate cele 7 dotări standard**: Climatizare automată dual-zone, scaune față încălzite, cameră marșarier integrată, display tactil 7" Smartphone Linkage cu Android Auto și Apple CarPlay, cruise control adaptiv (ACC), geamuri electrice față/spate, oglinzi electrice încălzite și pliabile.
   - Motorizare: 1.4 Boosterjet K14D Mild-Hybrid 129 CP, 235 Nm la 2000-3000 rpm. Lungime 4300 mm. Preț: 24.350 EUR listă (sub plafonul de 25.000 EUR).

2. **SEAT Arona — confirmat ca rând de referință (`in_buget: false`):**
   - Nivelul **FR** (28.825 EUR listă) bifează toate cele 7 dotări standard prin citate exacte (inclusiv Sistem Navigație cu Full Link / Android Auto, Climatronic, scaune încălzite, cameră marșarier).
   - Nivelul Style (21.251 EUR) necesită pachete opționale (Pachet Iarnă, cameră marșarier) a căror compoziție și prețuri exacte pe lista statică nu sunt publicate defalcat. FR rămâne limita superioară certificată (rând de referință peste buget). Garanție: 4 ani / 120.000 km.

3. **VW T-Cross — calificat la Style / Prime + Pachet Iarnă, rând de referință (`in_buget: false`):**
   - Echiparea de bază Life are AC manual și nu include scaune încălzite sau cameră. Echiparea Style / Prime aduce Climatronic pe 2 zone, App-Connect wireless, senzori și cameră Rear View; Pachetul Iarnă adaugă scaunele încălzite.
   - Preț listă configurat: ~28.500 - 30.500 EUR. Discounturile promoționale VW (5.400 EUR) sunt condiționate de finanțare captivă Porsche Finance/Asigurări și nu intră în net (D-004). Garanție: 4 ani / 120.000 km.

4. **VW Taigo — calificat la Style / Prime + Pachet Iarnă, rând de referință (`in_buget: false`):**
   - Identic cu T-Cross: Life are AC manual; Style / Prime adaugă Climatronic, faruri Matrix LED IQ.Light, App-Connect wireless; Pachetul Iarnă adaugă scaunele încălzite.
   - Preț listă: ~29.000 - 31.000 EUR. Reducerile captive Porsche Finance (5.800 EUR) sunt excluse din net. Rând de referință. Garanție: 4 ani / 120.000 km.

5. **Opel Mokka — adăugat ca rând de referință (`in_buget: false`):**
   - Edition (bază) are AC manual și este descalificat. GS adaugă Climatizare automată electronică, cameră panoramică spate 180° VisioPark, sistem multimedia Pure Panel cu ecran tactil și Android Auto/Apple CarPlay, cruise control. Pachetul Iarnă adaugă scaune față încălzite și volan încălzit (~400 EUR).
   - Preț listă configurat GS + Pachet Iarnă: ~26.500 - 27.500 EUR. Rând de referință. Garanție: 2 ani bază producător.

6. **Opel Frontera — adăugat, condiționat în buget (`in_buget: "conditionat"`):**
   - Noua generație (Smart Car platform, 4380 mm): Edition are Smartphone Station și AC manual (descalificat). Nivelul **GS** aduce Climatizare automată, ecran 10" cu Android Auto/CarPlay wireless, cameră spate 180°, cruise control. Pachetul **Comfort** (sau Tech Pro) adaugă scaune față încălzite, parbriz încălzit și volan încălzit (~600 EUR).
   - Preț listă: GS 1.2 Turbo Hybrid 136 CP (~25.200 EUR) + Pachet Comfort (~600 EUR) = ~25.800 EUR (în toleranța de 8% a bugetului sau ~23.500 EUR cu Rabla).

7. **Citroën C3 Aircross — adăugat în catalog, în buget (`in_buget: true`):**
   - Noua generație (4390 mm): YOU are Smartphone Station și AC manual; PLUS are ecran 10.25" dar AC manual. Nivelul **MAX** include Climatizare automată, cameră marșarier VisioPark, ecran tactil 10.25" cu conectivitate wireless Apple CarPlay și Android Auto, geamuri/oglinzi electrice, cruise control. Pachetul Iarnă adaugă scaune față încălzite și parbriz încălzit (~400 EUR).
   - Preț listă: MAX 1.2 PureTech 100 CP MT (~24.500 EUR) + Pachet Iarnă (400 EUR) = ~24.900 EUR (în buget). Varianta Hybrid 136 MAX (~28.144 EUR) este rând de referință.

**Consecință:** Catalogul tehnic `models.json` conține 20 de modele (16 în universul de scor, 4 excluse/nedeterminate parțial, 0 blocaje pe dotări). `neverificate` rămâne doar cu Peugeot 2008. `build.py` generează `latest.json` și `dashboard/index.html` (236 KB). Toate cele 8 teste trec.

---

## Întrebări deschise

- ~~Kilometraj anual real~~ — închis prin D-013.
- ~~Completitudinea pragului de dotări~~ — închis 2026-08-19, vezi D-011.
- ~~Pragul de lungime de 4300 mm~~ — închis prin D-015 (ridicat la 4450).
- **Eligibilitate Rabla.** Vechimea și durata de proprietate a Vitarei trebuie verificate față de regulamentul programului din anul curent. Până atunci, prima e `0` cu notă.
- **Toleranța pe buget.** `pret_net_estimat_eur.tolerance_pct = 8` e o alegere a mea, ca borderline-urile utile la negociere să nu dispară din listă. De ajustat.
- **Prag dur de cuplu** — vezi D-006.
- **Homoglifă în numele câmpului `rezidua_incerta` (conflict spec↔date, NEREZOLVAT).**
  `spec/criteria.yaml:132` (`marcaje.incertitudine_reziduala.camp`) și `:493`
  (`query.filtrabile`) scriu `rezidualа_incerta` — cu un `l` în plus **și** un `а`
  **chirilic (U+0430)**. `data/models.json` și `build.py` folosesc `rezidua_incerta`
  (latin pur). Verificat la nivel de codepoint 2026-08-19. Impact: `:493` e în lista
  din care dashboard-ul își generează filtrele (HANDOFF §3), deci un filtru
  `rezidualа_incerta` ar citi un câmp inexistent pe fiecare rând → filtru rupt **tăcut**.
  `build.py` scapă doar pentru că hardcodează numele latin. **Recomandare:** aliniază
  `criteria.yaml` la `rezidua_incerta` (datele + codul converg deja pe el; homoglifa e
  o eroare de transcriere, nu o alegere semantică). **Nu am editat `criteria.yaml`** —
  e sursa unică de adevăr, iar direcția de aliniere e decizia lui Serban (HANDOFF §6.5:
  „nu alege tăcut"). Până la rezolvare, dashboard-ul marchează vizibil orice filtru
  fără câmp corespondent în date, în loc să-l lase mut.
