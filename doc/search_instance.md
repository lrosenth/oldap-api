# Suche nach Instanzen

Diese Datei dokumentiert die Such-Endpunkte aus
`oldap_api/views/instance_views.py`. Sie soll als Arbeitsgrundlage fuer
Programmierer dienen: Welche Route nimmt welche Parameter entgegen, wann wird
`ResourceInstance.search_fulltext` verwendet, wann `ResourceInstance.search`,
und wie muessen Filter, Sortierung und Paging aufgebaut sein.

## Uebersicht

Alle Endpunkte liegen unter `/data` und benoetigen einen Bearer Token:

```http
Authorization: Bearer <token>
```

Die Implementierung unterscheidet zwei Sucharten:

| Suchart | Endpunkte | oldaplib-Aufruf | Zweck |
| --- | --- | --- | --- |
| Breite Volltextsuche | `GET /data/text/{project}`, `GET /data/text/{project}/class/{resclass}`, `GET /data/textsearch/{project}` | `ResourceInstance.search_fulltext(...)` | Suche nach einem Text in allen verfuegbaren Textfeldern. |
| Strukturierte Suche | `GET/POST /data/search/{project}`, `GET/POST /data/search/{project}/class/{resclass}` | `ResourceInstance.search(...)` | Suche nach Klasse, Properties, Volltext auf einem Lucene-Feld, hierarchischen Listen und Sortierung. |
| Klassenliste | `GET /data/ofclass/{project}` | `ResourceInstance.search(...)` | Aelterer, einfacher Endpunkt fuer "alle Instanzen dieser Klasse". |

Empfehlung:

- Fuer eine einfache Volltextsuche ueber alle Textfelder: `GET /data/text/{project}?q=...`
- Fuer Filter, `includeProperties`, `ftfilter`, `hlfilter` oder feldspezifischen Volltext: `POST /data/search/{project}`
- Fuer alte Clients, die schon existieren: `/data/textsearch/{project}` und `/data/ofclass/{project}` koennen weiter benutzt werden.

## Gemeinsame Begriffe

`project` ist der OLDAP-Projektname und wird als `Xsd_NCName` validiert.

`resClass` beziehungsweise der Pfadteil `resclass` ist eine QName-Resource-
Klasse, zum Beispiel `test:Sort`. Wird die Klasse im Pfad angegeben, hat der
Pfad Vorrang vor einem gleichnamigen JSON- oder Query-Parameter.

`q` und `searchString` sind Synonyme. Neue Clients sollten `q` verwenden.
`searchString` existiert vor allem fuer Kompatibilitaet mit
`/data/textsearch/{project}`.

`countOnly` wird mit `true`, `1`, `t`, `yes` oder `y` als wahr interpretiert.
Andere Werte gelten als falsch. Bei `countOnly=true` ist die Antwort immer:

```json
{
  "count": 3
}
```

`limit` und `offset` werden als Integer gelesen. Wenn sie fehlen, gelten die
Defaults aus `oldaplib`: `limit=100`, `offset=0`.

## Breite Volltextsuche

Diese Endpunkte suchen den Suchtext in allen verfuegbaren Textfeldern und rufen
`ResourceInstance.search_fulltext(...)` auf:

```http
GET /data/text/{project}
GET /data/text/{project}/class/{resclass}
GET /data/textsearch/{project}
```

Erlaubte Query-Parameter:

| Parameter | Pflicht | Bedeutung |
| --- | --- | --- |
| `q` | ja, alternativ `searchString` | Volltext-Suchstring. Wird intern in Kleinbuchstaben umgewandelt. |
| `searchString` | ja, alternativ `q` | Legacy-Name fuer `q`. |
| `resClass` | nein | Einschraenkung auf eine Resource-Klasse. Nicht noetig bei `/class/{resclass}`. |
| `resclass` | nein | Klein geschriebener Alias fuer `resClass`. |
| `countOnly` | nein | Gibt nur die Anzahl Treffer zurueck. |
| `sortBy` / `sortBy[]` | nein | Sortierung, siehe Abschnitt "Sortierung". |
| `limit` | nein | Maximale Anzahl Resultate. |
| `offset` | nein | Anzahl zu ueberspringender Resultate. |

Nicht erlaubt sind strukturierte Suchoptionen wie `ftField`/`ftProperty`,
`includeProperties`, `filter`, `ftfilter` und `hlfilter`. Wenn sie bei
`/data/text...` mitgeschickt werden, antwortet die API mit:

```json
{
  "message": "Structured search options require /data/search."
}
```

Beispiel:

```bash
curl \
  -H "Authorization: Bearer $OLDAP_TOKEN" \
  "http://localhost:8000/data/text/test?q=waseliwas&limit=10"
```

Beispiel mit Klasse:

```bash
curl \
  -H "Authorization: Bearer $OLDAP_TOKEN" \
  "http://localhost:8000/data/text/test/class/test:Sort?q=waseliwas"
```

Legacy-Form:

```bash
curl \
  -H "Authorization: Bearer $OLDAP_TOKEN" \
  "http://localhost:8000/data/textsearch/test?searchString=waseliwas&countOnly=true"
```

## Strukturierte Suche

Diese Endpunkte rufen `ResourceInstance.search(...)` auf:

```http
GET  /data/search/{project}
POST /data/search/{project}
GET  /data/search/{project}/class/{resclass}
POST /data/search/{project}/class/{resclass}
```

Fuer neue Clients ist `POST` die normale Wahl, weil nur im JSON-Body alle
Filterarten ausdrueckbar sind.

### Minimalanforderung

Eine strukturierte Suche braucht mindestens eines von:

- `resClass` oder `/class/{resclass}`
- `filter`
- `ftfilter`
- `hlfilter`
- `q` zusammen mit `ftField` oder dem Legacy-Namen `ftProperty`

Ohne diese Einschraenkung liefert die API:

```json
{
  "message": "Search without filters requires resClass, filter, ftfilter or hlfilter."
}
```

Wichtig: `q` ohne `ftField` ist bei `/data/search...` keine breite
Volltextsuche. Dafuer muss `/data/text...` benutzt werden. Bei `/data/search...`
fuehrt `q` ohne `ftField` zu:

```json
{
  "message": "Fulltext search with \"q\" requires \"ftField\". Alternatively use \"ftfilter\"."
}
```

### JSON-Body fuer POST

Erlaubte Felder im JSON-Body:

| Feld | Typ | Bedeutung |
| --- | --- | --- |
| `q` | String | Volltext-Suchstring fuer ein Lucene-Feld; nur zusammen mit `ftField` oder dem Legacy-Namen `ftProperty`. |
| `searchString` | String | Alias fuer `q`. |
| `ftField` | NCName-String | Lucene-Feldname, auf dem `q` gesucht werden soll. |
| `ftProperty` | NCName-String | Legacy-Name fuer `ftField`; erwartet ebenfalls einen Lucene-Feldnamen, keinen QName. |
| `resClass` / `resclass` | QName-String | Einschraenkung auf eine Resource-Klasse. |
| `includeProperties` | Array von QName-Strings | Properties, die im Resultat enthalten sein sollen. |
| `filter` | Array | Normale Property-Filter und Logikoperatoren. |
| `ftfilter` | Array | Volltextfilter auf bestimmten Lucene-Feldern und `AND`/`OR`. |
| `hlfilter` | Array | Filter fuer hierarchische Listen und Logikoperatoren. |
| `countOnly` | Boolean/String | Nur Anzahl zurueckgeben. |
| `sortBy` / `sortBy[]` | Array | Sortierung, siehe Abschnitt "Sortierung". |
| `limit` | Integer/String | Maximale Anzahl Resultate. |
| `offset` | Integer/String | Anzahl zu ueberspringender Resultate. |

Unbekannte Felder werden mit `400 Bad Request` abgewiesen. Ein POST-Request
muss einen JSON-Object-Body senden, sonst antwortet die API mit:

```json
{
  "message": "Invalid request format, JSON required"
}
```

oder:

```json
{
  "message": "Invalid request format, JSON object required"
}
```

### GET auf /data/search

`GET /data/search...` ist implementiert, aber eingeschraenkter als `POST`.
Nutzbar sind vor allem:

- Suche nach Klasse: `resClass` oder `/class/{resclass}`
- `includeProperties` / `includeProperties[]`
- Feldspezifischer Volltext mit `q` plus `ftField`/`ftProperty`
- `countOnly`, `sortBy`, `limit`, `offset`

Die Parameter `filter`, `ftfilter` und `hlfilter` sind zwar als bekannte Namen
zugelassen, werden bei GET aber nicht aus der Query aufgebaut. Fuer diese
Filterarten sollte immer POST verwendet werden.

Beispiel:

```bash
curl \
  -H "Authorization: Bearer $OLDAP_TOKEN" \
  "http://localhost:8000/data/search/test?resClass=test:Sort&includeProperties=test:aString"
```

## Suche nach Resource-Klasse

Es gibt zwei gleichwertige Schreibweisen.

Klasse im JSON-Body:

```bash
curl \
  -X POST \
  -H "Authorization: Bearer $OLDAP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resClass": "test:Sort",
    "includeProperties": ["test:aString", "test:anInteger"]
  }' \
  "http://localhost:8000/data/search/test"
```

Klasse im Pfad:

```bash
curl \
  -X POST \
  -H "Authorization: Bearer $OLDAP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "includeProperties": ["test:aString", "test:anInteger"]
  }' \
  "http://localhost:8000/data/search/test/class/test:Sort"
```

## Normale Property-Filter

Normale Filter werden im Feld `filter` als Array angegeben. Ein Filtereintrag
ist entweder ein Objekt oder ein Logikoperator.

Filterobjekt:

```json
{
  "property": "test:anInteger",
  "op": ">",
  "value": 0,
  "type": "integer"
}
```

Kurzname `prop` ist als Alias fuer `property` erlaubt.

Logikoperatoren koennen als String oder als Objekt geschrieben werden:

```json
"AND"
```

```json
{ "logic": "AND" }
```

Unterstuetzte Logikoperatoren:

| Schreibweise | Bedeutung |
| --- | --- |
| `AND`, `&&` | Und |
| `OR`, `||` | Oder |
| `(`, `LEFT`, `LEFT_` | Linke Klammer |
| `)`, `RIGHT`, `_RIGHT` | Rechte Klammer |

Unterstuetzte Vergleichsoperatoren:

| Operator | Alias nach Enum-Name | Bedeutung |
| --- | --- | --- |
| `==` | `EQ` | gleich |
| `!=` | `NE` | ungleich |
| `<` | `LT` | kleiner als |
| `<=` | `LE` | kleiner oder gleich |
| `>` | `GT` | groesser als |
| `>=` | `GE` | groesser oder gleich |
| `contains` | `CONTAINS` | String enthaelt Wert |
| `strstarts` | `STRSTARTS` | String beginnt mit Wert |
| `strends` | `STRENDS` | String endet mit Wert |
| `regexp` | `REGEXP` | regulaerer Ausdruck |
| `fulltext` | `FULLTEXT` | Volltextoperator der oldaplib |
| `overlaps` | `OVERLAPS` | Dating-Bereich ueberlappt |
| `before` | `BEFORE` | Dating-Bereich liegt davor |
| `after` | `AFTER` | Dating-Bereich liegt danach |

Unterstuetzte Werttypen:

| `type` | Python-/oldaplib-Typ |
| --- | --- |
| fehlt, `string`, `langstring` | `Xsd_string(value, lang=lang)` |
| `int`, `integer` | `Xsd_integer` |
| `decimal` | `Xsd_decimal` |
| `float`, `double` | `FloatingPoint` |
| `bool`, `boolean` | `Xsd_boolean` |
| `iri` | `Iri` |
| `qname` | `Xsd_QName` |
| `date` | `Xsd_date` |
| `datetime` | `Xsd_dateTime` |
| `dating` | `Dating` |

Fuer `string` und `langstring` kann optional `lang` angegeben werden:

```json
{
  "property": "test:title",
  "op": "contains",
  "value": "Titel",
  "type": "langstring",
  "lang": "de"
}
```

Ein `Dating`-Wert kann als Objekt uebergeben werden:

```json
{
  "property": "test:period",
  "op": "overlaps",
  "type": "dating",
  "value": {
    "dateStart": "1900-01-01",
    "dateEnd": "1950-12-31",
    "verbatimDate": "erste Haelfte 20. Jh."
  }
}
```

Komplettes Beispiel:

```bash
curl \
  -X POST \
  -H "Authorization: Bearer $OLDAP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resClass": "test:Sort",
    "filter": [
      {"property": "test:anInteger", "op": ">", "value": 0, "type": "integer"},
      "AND",
      {"property": "test:aString", "op": "contains", "value": "Item"}
    ],
    "sortBy": [{"property": "test:anInteger", "direction": "desc"}],
    "limit": 10
  }' \
  "http://localhost:8000/data/search/test"
```

## Feldspezifische Volltextsuche

Es gibt zwei Formen.

Kurzform mit `q` und `ftField`:

```json
{
  "resClass": "test:Page",
  "ftField": "pageContent",
  "q": "waseliwas"
}
```

Diese Form wird intern in einen `FTSearchFilter` umgewandelt.
`ftProperty` ist als Legacy-Name weiterhin erlaubt, erwartet aber ebenfalls
einen Lucene-Feldnamen/NCName und keinen QName.

Explizite Form mit `ftfilter`:

```json
{
  "resClass": "test:Page",
  "ftfilter": [
    {"field": "pageContent", "query": "waseliwas"}
  ]
}
```

Auch hier ist `fieldName` als Alias fuer `field` erlaubt und `q` als Alias fuer
`query`. Die Legacy-Namen `property` und `prop` werden noch akzeptiert, muessen
aber ebenfalls NCName-kompatible Lucene-Feldnamen enthalten.

Mehrere Volltextfilter koennen mit `AND` oder `OR` verbunden werden:

```json
{
  "resClass": "test:Page",
  "ftfilter": [
    {"field": "title", "query": "Einleitung"},
    "AND",
    {"field": "pageContent", "query": "waseliwas"}
  ]
}
```

Nur die Strings `AND` und `OR` sind in `ftfilter` als Logikoperatoren erlaubt.
Klammern werden dort nicht akzeptiert.

`q` und `ftfilter` sollten nicht gemischt werden. Wenn `ftfilter` vorhanden ist,
wird die Suche ueber `ftfilter` aufgebaut; `q` ist dann nicht die treibende
Suchbedingung.

## Hierarchische Listen

Hierarchische Listen werden ueber `hlfilter` gesucht. Jeder Filter braucht eine
Property und einen strukturierten Node-Verweis mit `listId` und `nodeId`:

```json
{
  "resClass": "test:SomeClass",
  "hlfilter": [
    {
      "property": "test:category",
      "node": {
        "listId": "myList",
        "nodeId": "someNode"
      }
    }
  ]
}
```

Intern identifiziert OLDAP Listenknoten als `L-<listId>:<nodeId>`. Der API-Vertrag
verwendet absichtlich nur die fachliche Kombination aus `listId` und `nodeId`, damit
kein UI- oder Admin-Output mit internen Prefixen geparst werden muss.

`prop` ist als Alias fuer `property` erlaubt. Logikoperatoren funktionieren wie
bei normalen `filter`-Eintraegen, also inklusive `AND`, `OR` und Klammern.

Legacy-Strings wie `"myList:someNode"` werden weiterhin akzeptiert, sollten fuer
neue Aufrufe aber nicht mehr verwendet werden.

Beispiel mit Logik:

```json
{
  "resClass": "test:SomeClass",
  "hlfilter": [
    {"property": "test:category", "node": {"listId": "myList", "nodeId": "nodeA"}},
    "OR",
    {"property": "test:category", "node": {"listId": "myList", "nodeId": "nodeB"}}
  ]
}
```

## Include Properties

Mit `includeProperties` wird gesteuert, welche Properties im Resultat
mitgeliefert werden sollen.

POST:

```json
{
  "resClass": "test:Sort",
  "includeProperties": ["test:aString", "test:anInteger"]
}
```

GET:

```http
GET /data/search/test?resClass=test:Sort&includeProperties=test:aString&includeProperties=test:anInteger
```

Die Implementierung akzeptiert bei GET sowohl `includeProperties` als auch
`includeProperties[]` als wiederholbare Parameter.

## Sortierung

Sortierung wird in `sortBy` oder `sortBy[]` angegeben. Mehrere Sortierkriterien
sind moeglich.

Stringform:

```json
{
  "sortBy": ["test:anInteger|desc", "test:aString|asc"]
}
```

Objektform bei POST:

```json
{
  "sortBy": [
    {"property": "test:anInteger", "direction": "desc"},
    {"property": "test:aString", "direction": "asc"}
  ]
}
```

Aliases:

- `prop` ist Alias fuer `property`
- `dir` ist Alias fuer `direction`

Wenn keine Richtung angegeben ist, wird aufsteigend sortiert. Erlaubt sind
`asc` und `desc`; bei der Stringform werden auch `ASC` und `DESC` akzeptiert.

Spezielle Sortierfelder:

| Feld | Wird intern sortiert nach |
| --- | --- |
| `PROPVAL` | `oldap:propval` |
| `CREATED` | `oldap:creationDate` |
| `LASTMOD` | `oldap:lastModificationDate` |

Beispiel:

```http
GET /data/text/test?q=waseliwas&sortBy=PROPVAL|asc
```

Bei der POST-Objektform kann zusaetzlich `kind` gesetzt werden:

```json
{
  "sortBy": [
    {"property": "test:period", "direction": "asc", "kind": "dating"}
  ]
}
```

Erlaubte `kind`-Werte sind:

- `auto`
- `value`
- `dating`

## Paging

`limit` begrenzt die Anzahl der Resultate, `offset` ueberspringt Resultate am
Anfang der Trefferliste.

```bash
curl \
  -X POST \
  -H "Authorization: Bearer $OLDAP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resClass": "test:Sort",
    "limit": 10,
    "offset": 20
  }' \
  "http://localhost:8000/data/search/test"
```

## Antworten

Normale Suchantworten sind JSON-Arrays. Die konkreten Properties haengen von
oldaplib und `includeProperties` ab. Typisch ist:

```json
[
  {
    "iri": "test:Item1",
    "resclass": "test:Sort",
    "aString": ["Item 1"],
    "anInteger": [1]
  }
]
```

Bei `countOnly=true`:

```json
{
  "count": 3
}
```

Intern werden oldaplib-/XSD-Werte vor dem JSON-Response in einfache JSON-Werte
umgewandelt: Integer zu JSON-Zahlen, Booleans zu JSON-Booleans, Listen und
Dicts rekursiv, sonst per `str(...)`.

## /data/ofclass/{project}

`/data/ofclass/{project}` ist ein aelterer GET-Endpunkt fuer alle Instanzen
einer Klasse. Fuer neue Implementierungen ist `/data/search/{project}` meist
flexibler, aber `/data/ofclass` wird in Tests und bestehenden Clients genutzt.

```http
GET /data/ofclass/{project}
```

Erlaubte Query-Parameter:

| Parameter | Pflicht | Bedeutung |
| --- | --- | --- |
| `resClass` | ja | Resource-Klasse, deren Instanzen gesucht werden. |
| `includeProperties[]` | nein | Wiederholbare Properties fuer das Resultat. |
| `countOnly` | nein | Nur Anzahl zurueckgeben. |
| `sortBy[]` | nein | Wiederholbare Sortierkriterien in Stringform. |
| `limit` | nein | Maximale Anzahl Resultate. |
| `offset` | nein | Anzahl zu ueberspringender Resultate. |

Hinweis: In der aktuellen Implementierung akzeptiert `/data/ofclass` nur die
Namen mit `[]` fuer wiederholbare Parameter, also `includeProperties[]` und
`sortBy[]`.

Beispiel:

```bash
curl \
  -H "Authorization: Bearer $OLDAP_TOKEN" \
  "http://localhost:8000/data/ofclass/test?resClass=test:Sort&sortBy[]=test:aString|asc"
```

## Fehler und Validierung

Typische Fehler:

| Situation | Status | Beispiel-Message |
| --- | --- | --- |
| Kein Authorization-Header | `401` | `No authorization token provided` |
| Ungueltiger Authorization-Header | `401` | `Invalid authorization header` |
| Token/Connection ungueltig | `403` | `Connection failed: ...` |
| POST ohne JSON | `400` | `Invalid request format, JSON required` |
| POST-JSON ist kein Objekt | `400` | `Invalid request format, JSON object required` |
| Unbekannte Felder | `400` | `The Field/s {...} is/are not used to search for an instance...` |
| `/data/text` ohne Suchstring | `400` | `No search string provided` |
| `/data/search` mit `q` ohne `ftField` | `400` | `Fulltext search with "q" requires "ftField". Alternatively use "ftfilter".` |
| Ungueltiger Operator, QName, Typ, Sortierwert | `400` | Die jeweilige oldaplib- oder Parser-Fehlermeldung. |

## Entscheidungsbaum fuer Clients

1. Soll ein Text ueber alle Textfelder gesucht werden?
   Verwende `GET /data/text/{project}?q=...`.

2. Soll der Text nur in einem bestimmten Lucene-Feld gesucht werden?
   Verwende `POST /data/search/{project}` mit `ftField` + `q` oder mit
   `ftfilter`.

3. Soll nur eine Klasse mit optionalen Rueckgabe-Properties geladen werden?
   Verwende `POST /data/search/{project}` mit `resClass` und
   `includeProperties`, oder den Legacy-Endpunkt `/data/ofclass/{project}`.

4. Werden normale Property-Filter, Hierarchie-Filter oder komplexere
   Kombinationen gebraucht?
   Verwende `POST /data/search/{project}`.

5. Wird nur die Anzahl benoetigt?
   Setze `countOnly=true`.
