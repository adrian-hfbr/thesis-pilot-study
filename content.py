# content.py

CONSENT_TEXT = """
**Ablauf:**
Sie werden gebeten, vier aufgabenbezogene Probleme im Bereich des deutschen Steuerrechts mithilfe eines KI-Chatbots zu lösen. Zuvor und danach werden Sie gebeten, einige Fragebögen auszufüllen. Die gesamte Studie dauert voraussichtlich 20-25 Minuten.

**Datenschutz:**
Alle Ihre Antworten werden anonymisiert erfasst. Es werden keine persönlichen Daten erhoben, die eine Identifizierung Ihrer Person ermöglichen. Die gesammelten Daten werden ausschließlich für wissenschaftliche Zwecke verwendet.


Die Teilnahme an dieser Studie ist freiwillig. Sie können Ihre Teilnahme jederzeit und ohne Angabe von Gründen abbrechen, ohne dass Ihnen daraus Nachteile entstehen.

Indem Sie auf "Ich stimme zu und möchte fortfahren" klicken, bestätigen Sie, dass Sie die Informationen gelesen und verstanden haben und freiwillig an der Studie teilnehmen.
"""

INSTRUCTIONS_BY_CONDITION = {
    "Minimal": """
Ihre Aufgabe ist es, vier steuerrechtliche Probleme mithilfe eines KI-Assistenten zu lösen. Wie viele moderne KI-Systeme ist dieser Assistent ein leistungsfähiges Werkzeug, das Ihnen helfen soll, indem es Informationen aus den jeweiligen Gesetzestexten abruft.

Da der KI-Assistent auch Fehler machen kann, stellt der Assistent einen Button zur Überprüfung der Antworten zur Verfügung:

""",
    "minimal_image_path": "assets/mehr_kontext.jpg",
    "minimal_image_caption": "Button 'Gesetzestext anzeigen' öffnet den vollständigen Gesetzesparagraphen",
    
    "Minimal_continuation": """

Ein Klick auf diesen Button öffnet ein Fenster mit dem vollständigen Gesetzesparagraphen, den die KI verwendet hat.

""",
    "minimal_modal_image_path": "assets/schliessen.jpg",
    "minimal_modal_caption": "Fenster mit vollständigem Paragraphen und 'Schließen'-Button",
    
    "Minimal_end": """

**Wichtig:**

• Bitte verwenden Sie nur den „Schließen"-Button am unteren Rand des Fensters, wenn Sie den Gesetzestext wieder verlassen möchten. Klicken Sie dafür nicht die ESC-Taste oder außerhalb des geöffneten Fensters.

• Bitte verwenden Sie nicht die Zurück-Funktion des Browsers (z. B. die Pfeiltasten).

• Bitte klicken Sie nicht auf den Button, wenn gerade die Antwort durch den KI-Assistenten generiert wird.


**Hinweise zur Interaktion:**

• Bitte bedanken Sie sich nicht beim Chatbot und stellen Sie nur Fragen, die auf die Beantwortung der jeweiligen Aufgabe abzielen.

• Wie und ob Sie die bereitgestellten Funktionen nutzen, ist vollständig Ihnen überlassen.

• Wie bei bekannten KI-Chatbots können Sie beliebig viele Anfragen stellen. Der KI-Steuerassistent kann sich jedoch immer nur an die letzten beiden Anfragen und die dazugehörigen Antworten erinnern.


""",

    "Augmented": """
Ihre Aufgabe ist es, vier steuerrechtliche Probleme mithilfe eines KI-Assistenten zu lösen. Wie viele moderne KI-Systeme ist dieser Assistent ein leistungsfähiges Werkzeug, das Ihnen helfen soll, indem es Informationen aus Gesetzestexten abruft.

Da der KI-Assistent auch Fehler machen kann, stellt der Assistent zwei verschiedene Werkzeuge zur Überprüfung der Antworten zur Verfügung:

**1. Direktes Zitat anzeigen:**

""",
    "augmented_expander_image_path": "assets/zitat_anzeigen.jpg",
    "augmented_expander_caption": "Expander 'Zitat anzeigen' für direkten Zugriff auf das unterstützende Zitat",
    
    "Augmented_continuation1": """

Ein Button mit der Aufschrift „Zitat anzeigen" zeigt sofort das unterstützende Zitat aus dem Gesetzestext an.

""",
    "augmented_expander_open_image_path": "assets/zitat_ausblenden.jpg",
    "augmented_expander_open_caption": "Geöffneter Expander mit Zitat und 'Zitat ausblenden'-Option",
    
    "Augmented_continuation2": """

**Wichtig:** Wenn Sie mit dem Lesen des direkten Zitats fertig sind, schließen Sie bitte das Zitat mittels des Buttons, bevor Sie mit der Formulierung einer neuen Anfrage fortfahren.

**2. Vollständigen Gesetzestext anzeigen:**

""",
    "augmented_context_image_path": "assets/mehr_kontext.jpg",
    "augmented_context_caption": "Button 'Gesetzestext anzeigen' für den vollständigen Paragraphen",
    
    "Augmented_continuation3": """

Ein separater Button mit der Aufschrift „Gesetzestext anzeigen" öffnet ein Fenster mit dem vollständigen Gesetzesparagraphen für mehr Details.

""",
    "augmented_modal_image_path": "assets/schliessen.jpg",
    "augmented_modal_caption": "Fenster mit vollständigem Paragraphen",
    
    "Augmented_end": """

**Wichtig:**

• Bitte verwenden Sie nur den „Schließen"-Button am unteren Rand des Fensters, wenn Sie den Gesetzestext wieder verlassen möchten. Klicken Sie dafür nicht die ESC-Taste oder außerhalb des geöffneten Fensters.

• Bitte klicken Sie nicht auf die Buttons, wenn gerade die Antwort durch den KI-Assistenten generiert wird.

• Bitte verwenden Sie nicht die Zurück-Funktion des Browsers (z. B. die Pfeiltasten).


**Hinweise zur Interaktion:**

• Bitte bedanken Sie sich nicht beim Chatbot und stellen Sie nur Fragen, die auf die Beantwortung der jeweiligen Aufgabe abzielen.

• Wie und ob Sie die bereitgestellten Funktionen nutzen, ist vollständig Ihnen überlassen.

• Wie bei bekannten KI-Chatbots können Sie beliebig viele Anfragen stellen. Der KI-Steuerassistent kann sich jedoch immer nur an die letzten beiden Anfragen und die dazugehörigen Antworten erinnern.
"""
}



COMPREHENSION_BY_CONDITION = {
    "Minimal": [
        {
            "question": "Wie sollten Sie das Fenster mit dem vollständigen Gesetzestext korrekt schließen?",
            "options": [
                "Ich sollte den 'Schließen'-Button am unteren Rand des Fensters verwenden.",
                "Es ist egal, wie ich das Fenster beende – sowohl ESC-Taste als auch der 'Schließen'-Button funktionieren gleich.",
                "Ich kann das Fenster automatisch durch Klicken außerhalb des Fensters schließen."
            ],
            "correct_index": 0
        },
        {
            "question": "Für welche Gesetzesbereiche kann der Assistant Auskunft geben?",
            "options": [
                "Für das Strafrecht.",
                "Für das Steuerrecht.",
                "Für das Arbeitsrecht."
            ],
            "correct_index": 1
        }
    ],
    "Augmented": [
        {
            "question": "Wie sollten Sie das Fenster mit dem vollständigen Gesetzestext korrekt schließen?",
            "options": [
                "Ich sollte den 'Schließen'-Button am unteren Rand des Fensters verwenden.",
                "Es ist egal, wie ich das Fenster beende – sowohl ESC-Taste als auch der 'Schließen'-Button funktionieren gleich.",
                "Ich kann das Fenster automatisch durch Klicken außerhalb des Fensters schließen."
            ],
            "correct_index": 0
        },
        {
            "question": "Für welche Gesetzesbereiche kann der Assistant Auskunft geben?",
            "options": [
                "Für das Strafrecht.",
                "Für das Steuerrecht.",
                "Für das Arbeitsrecht."
            ],
            "correct_index": 1
        }
    ]
}


PRE_STUDY_SURVEY = {
    "title": "Fragebogen vor der Studie",
    "items": {
        "task_completion_thoroughness": "Ich bin jemand, der beharrlich ist und an Aufgaben arbeitet, bis sie fertig sind.",
         # ATI Short-Scale (4 items)
        "ati_1": "Ich beschäftige mich gern genauer mit technischen Systemen.",
        "ati_2": "Ich probiere gern die Funktionen neuer technischer Systeme aus.",
        "ati_3": "Es genügt mir, dass ein technisches System funktioniert, mir ist es egal, wie oder warum.",
        "ati_4": "Es genügt mir, die Grundfunktionen eines technischen Systems zu kennen.",
                
        "chatbot_experience": "Ich nutze KI-Chatbots (wie ChatGPT) häufig.",
        "tax_knowledge": "Ich bin mit alltäglichen steuerlichen Fragestellungen vertraut.",
        },
    "ati_items": ["ati_1", "ati_2", "ati_3", "ati_4"]
}


TASKS = {
    1: {
        "name": "GWG-Sofortabzug",
        "scenario": """Sie sind selbstständig und kaufen einen neuen Laptop (Wirtschaftsgut) für Ihre berufliche Tätigkeit. Die **Netto-Anschaffungskosten** betragen genau 850€.""",
        "question": "Können Sie den Laptop als Betriebsausgabe sofort in diesem Wirtschaftsjahr absetzen?",
        "options": [
            "Ja, der Laptop ist sofort in diesem Wirtschaftsjahr vollständig absetzbar.",
            "Nein, der Laptop muss über die Nutzungsdauer abgeschrieben werden.",
            "Ja, er ist über den Sammelposten mit der 1.000€-Grenze sofort absetzbar.",
        ],
        "correct_answer": 1
    },
    2: {
        "name": "Handwerkerleistungen",
        "scenario": "Sie beauftragen eine **Handwerkerleistung**, um Ihr Badezimmer zu renovieren. Die Gesamtrechnung für die durchgeführten Arbeiten beträgt 3.000€ und teilt sich wie folgt auf: 1.800€ entfallen auf Lohnkosten und 1.200€ auf Materialkosten.",
        "question": "Sind diese Handwerkerleistungen steuerlich absetzbar?",
        "options": [
            "Ja, die vollen 3.000€ sind steuerlich absetzbar (Gesamtrechnung).",
            "Nein, nur die 1.200€ Materialkosten sind steuerlich absetzbar.",
            "Nein, nur die 1.800€ Lohnkosten sind steuerlich absetzbar.",
        ],
        "correct_answer": 2
    },
    3: {
        "name": "Sparer-Pauschbetrag mehrere Banken",
        "scenario": """Sie sind alleinstehend und erzielen Kapitaleinkünfte bei zwei verschiedenen Banken. Um den **Sparer-Pauschbetrag** zu nutzen, haben Sie bei Bank A einen Freistellungsauftrag über 700€ erteilt und bei Bank B über 650€.""",
        
        "question": "Sind diese Freistellungsaufträge bei den beiden Banken so zulässig, um den Sparer-Pauschbetrag zu nutzen?",
        
        "options": [
            "Nein, die Gesamtsumme des Szenarios überschreitet den Sparer-Pauschbetrag für alleinstehende.",
            "Ja, die Summe der beiden erteilten Freistellungsaufträge ist flexibel aufteilbar und zulässig.",
            "Ja, pro Bank gilt ein separater Sparer-Pauschbetrag von 1.000€.",
        ],
        "correct_answer": 0
    },
    4: {
    'name': 'Doppelte Haushaltsführung - Unterkunftskosten',
    'scenario': '''Sie sind als Ingenieur:in in München tätig und führen eine **doppelte Haushaltsführung**, da Ihre Familie noch in Hamburg wohnt. Ihre Unterkunft in München kostet 1.400€ Miete pro Monat. Da Sie sich die Wohnung mit einem Kollegen teilen, zahlen Sie nur 50 Prozent der Miete. ''',
    
    'question': '''Kann die volle Miete für die Unterkunft als Werbungskosten bei Ihnen abgesetzt werden?''',
    
    'options': [
        'Ja, die vollen 1.400 Euro pro Monat, da dies die tatsächlichen Kosten der Unterkunft sind.',
        'Nein, maximal 700 Euro pro Monat, da nur der selbst gezahlte Anteil absetzbar ist.',
        'Nein, aber 1.000 Euro pro Monat, auch wenn nur 700 Euro selbst gezahlt werden.',
    ],
    "correct_answer": 1
    }
}

POST_STUDY_SURVEY = {
    "title": "Fragebogen nach der Studie",

    # Cognitive Load (three types)
    "icl_items": {  # Intrinsic Cognitive Load
        "icl_1": "Bei den Aufgaben musste man viele Dinge gleichzeitig im Kopf behalten.",
        "icl_2": "Diese Aufgaben waren sehr komplex."
    },
    "ecl_items": {  # Extraneous Cognitive Load
        "ecl_1": "Bei diesen Aufgaben ist es mühsam, die wichtigsten Informationen zu erkennen.",
        "ecl_2": "Die Darstellung bei dieser Aufgabe ist ungünstig, um wirklich etwas zu lernen.",
        "ecl_3": "Bei dieser Aufgabe ist es schwer, die zentralen Inhalte miteinander in Verbindung zu bringen."
    },
    "gcl_items": {  # Germane Cognitive Load
        "gcl_1": "Ich habe mich angestrengt, mir nicht nur einzelne Dinge zu merken, sondern auch den Gesamtzusammenhang zu verstehen. ",
        "gcl_2": "Es ging mir beim Bearbeiten der Aufgabe darum, alles richtig zu verstehen.",
        "gcl_3": "Die Aufgabe enthielt Elemente, die mich unterstützten, den Lernstoff besser zu verstehen."
    },

    "attention_check": {
        "ac1": "Bitte wählen Sie hier die Antwort '5 – stimme eher zu' aus."
    },

    # Trust (second-order construct: Functionality, Helpfulness, Reliability)
    "trust_items": {
        # Functionality
        "trust_func_1": "Der KI-Assistent hat die Funktionalität, die ich benötige.",
        "trust_func_2": "Der KI-Assistent verfügt über die für meine Aufgaben erforderlichen Funktionen.",
        "trust_func_3": "Der KI-Assistent hat die Fähigkeit, das zu tun, was ich von ihm erwarte.",

        # Helpfulness
        "trust_help_1": "Der KI-Assistent bietet über seine Hilfefunktion die Unterstützung, die ich benötige.",
        "trust_help_2": "Der KI-Assistent bietet bei Bedarf kompetente Anleitung über seine Hilfefunktion.",
        "trust_help_3": "Der KI-Assistent bietet mir jegliche Hilfe, die ich brauche.",
        "trust_help_4": "Der KI-Assistent gibt bei Bedarf sehr sinnvolle und wirksame Ratschläge.",

        # Reliability
        "trust_reli_1": "Der KI-Assistent ist eine sehr zuverlässige Software.",
        "trust_reli_2": "Der KI-Assistent lässt mich nicht im Stich.",
        "trust_reli_3": "Der KI-Assistent ist äußerst verlässlich.",
        "trust_reli_4": "Der KI-Assistent weist bei mir keine Fehlfunktionen auf."
    },

    # Manipulation check (multiple choice; analysis compares answer to assigned condition)
    "manipulation_check": {
        "manip_check_1": {
            "question": "Welche Werkzeuge zur Quellenprüfung standen Ihnen in der Interaktion mit dem KI-Assistenten zur Verfügung?",
            "options": [
                "Ein Button, der den vollständigen Gesetzestext in einem neuen Fenster öffnet.",
                "Ein Button, der das passende Zitat aus dem Gesetzestext direkt unter der Antwort anzeigt.",
                "Beide dieser Buttons wurden angezeigt.",
                "Keiner dieser Buttons wurde angezeigt."
            ],
            "correct_index_augmented": 2,  # Index for Augmented condition
            "correct_index_minimal": 0     # Index for Minimal condition
        }
    }
}



DEBRIEFING = """
Vielen Dank für Ihre Teilnahme! Das Ziel der Studie war zu untersuchen, wie die Gestaltung der Quellen das Nutzererleben und Verhalten beeinflusst.
"""

UNIVERSAL_PROMPT = """
Du bist ein wissenschaftlicher Assistent im Bereich des deutschen Steuerrechts. 
Wir haben Oktober 2025.

Deine Aufgabe ist es, Fragen zum deutschen Steuerrecht präzise und nachvollziehbar zu beantworten, 
basierend ausschließlich auf den bereitgestellten Gesetzestexten.


GRUNDPRINZIPIEN DER RECHTSANWENDUNG:

1. SCHWELLENWERTE UND GRENZEN
   Wenn eine gesetzliche Regelung numerische Schwellenwerte, Beträge oder Grenzen definiert:
   - Identifiziere alle im Gesetzestext genannten Grenzwerte
   - Prüfe systematisch, in welchen Wertebereich der konkrete Fall fällt
   - Beachte, dass verschiedene Wertebereiche zu unterschiedlichen Rechtsfolgen führen können

2. ZUSAMMENGESETZTE SACHVERHALTE
   Wenn eine Anfrage mehrere Elemente, Beträge oder Komponenten enthält:
   - Analysiere jedes Element und prüfe, ob Elemente addiert werden müssen im Hinblick auf die gesetzlichen Anforderungen
   - Stelle klar dar, welche rechtlichen Voraussetzungen für welches Element oder welche Summe gelten
   - Gib konkrete Zahlen an, wenn diese für die Rechtsfolge entscheidend sind

3. HIERARCHISCHE REGELUNGEN
   Wenn das Gesetz mehrere Bedingungen, Obergrenzen oder Einschränkungen vorsieht:
   - Wende alle relevanten Beschränkungen systematisch an
   - Beachte die Reihenfolge: Erst Anspruchsvoraussetzungen prüfen, dann Höchstbeträge
   - Erkläre, welche Regelung im konkreten Fall den Ausschlag gibt

4. ZEITABHÄNGIGE REGELUNGEN
   Wenn der Kontext zeitliche Abstufungen oder "abweichend von"-Formulierungen enthält:
   - Prüfe, welche Regelung für den Zeitraum Oktober 2025 gilt
   - Abweichende oder zeitlich spätere Regelungen haben Vorrang vor Standardregelungen


ZITATIONSREGELN:

5. QUELLENANGABEN
   - Nenne NUR Paragraphen und Absätze, die WÖRTLICH im bereitgestellten Kontext erscheinen
   - Der Paragraph (z.B. "§ 6") steht VOR dem Wort "Absatz"
   - Der Absatz (z.B. "Abs. 2") ist eine UNTEREINHEIT des Paragraphen, NICHT ein eigener Paragraph
   - Zitiere vollständig: "§ X Abs. Y EStG", wenn beide Informationen vorhanden sind
   - Gib IMMER Paragraph und Absatz an, aber keine Untereinheiten wie Satz oder Nummer
   - Verifiziere: Kommt meine Paragraphennummer nach einem § Symbol im Kontext vor?

6. KEINE HALLUZINATIONEN
   - Erfinde KEINE Paragraphen oder Rechtsvorschriften
   - Wenn der Kontext die Antwort nicht enthält: Sage klar "Die bereitgestellten Gesetzestexte 
     enthalten keine Informationen zu dieser Frage. Bitte formulieren Sie Ihre Anfrage mit spezifischeren Begriffen erneut."


ANTWORTFORMAT:

7. NACHVOLLZIEHBARKEIT
   - Beantworte die Frage klar in 2-3 Sätzen
   - Nenne konkrete Beträge oder Werte aus dem Gesetzestext, wenn diese für die Entscheidung relevant sind
   - Vermeide vage Formulierungen ohne konkrete Rechtsgrundlage
   - Gib immer die Rechtsgrundlage mit Paragraph und Absatz an


WICHTIG: Antworte ausschließlich auf Grundlage der bereitgestellten Gesetzestexte. 
Nutze kein externes Wissen über deutsche Steuergesetze.


**Kontext:**
{context}
"""


QUOTE_EXTRACTION_PROMPT = """
AUFGABE: Extrahiere aus dem Gesetzestext WÖRTLICH den relevantesten Abschnitt (1-3 Sätze), der die Antwort stützt.

ANFRAGE: {user_query}
ANTWORT: {answer}
GESETZESTEXT: {source_text}

PRIORITÄT:
1. Abschnitte mit Zahlen/Beträgen
2. Normative Regeln
3. Bedingungen

RELEVANZ:
1. Das Zitat MUSS die Kernaussage der Antwort stützen
2. Es sollte zentrale Zahlen, Grenzen oder Regeln enthalten, die in der Antwort genannt werden

LÄNGE:
1. Maximal 2-3 zusammenhängende Sätze (maximal ca. 100-150 Wörter)
2. Das Zitat sollte ohne zusätzlichen Kontext verständlich sein
3. Kopiere wortwörtlich aus dem Gesetzestext
4. Nutze "[...]" für Auslassungen.

NUR "KEINE_EXTRAKTION_MÖGLICH" antworten, wenn der Gesetzestext die Antwort absolut nicht unterstützt.

EXTRAHIERTER ABSCHNITT:
"""


QUOTE_EXTRACTION_PROMPT_1 = """
Du bekommst eine Nutzeranfrage, eine Antwort und einen Gesetzestext.

ANFRAGE: {user_query}
ANTWORT: {answer}
GESETZESTEXT: {source_text}

AUFGABE: Extrahiere den relevantesten Textabschnitt (1-3 Sätze), der die Antwort direkt stützt.

1. RELEVANZ:
   - Das Zitat MUSS die Kernaussage der Antwort stützen
   - Es sollte zentrale Zahlen, Grenzen oder Regeln enthalten, die in der Antwort genannt werden
   - Bevorzuge Abschnitte, die direkt zur Beantwortung der Frage beitragen

2. LÄNGE:
   - Maximal 2-3 zusammenhängende Sätze (maximal ca. 100-150 Wörter)
   - Das Zitat sollte ohne zusätzlichen Kontext verständlich sein

3. GENAUIGKEIT:
   - Kopiere den Text EXAKT wie im Original, jedoch kannst du für nicht für die Frage direkt relevante Teile [..] benutzen
   - Keine Paraphrasierung, keine Zusammenfassungen

4. NUR "KEINE_EXTRAKTION_MÖGLICH" verwenden, wenn:
    - Der Gesetzestext die Antwort absolut nicht unterstützt
    - Der relevante Inhalt fehlt komplett im bereitgestellten Text
    - Keine zusammenhängende Passage die Mindestanforderungen erfüllt

5. PRIORISIERUNG (in dieser Reihenfolge):
   a) Abschnitte, die spezifische Zahlen/Beträge enthalten (z.B., "1.000 Euro", "1.250 Euro")
   b) Abschnitte, die die zentrale Regel definieren
   c) Abschnitte, die Bedingungen oder Einschränkungen nennen
   d) Abschnitte, die Verfahren oder Definitionen erklären

WICHTIG:
- Kopiere wortwörtlich aus dem Gesetzestext
- Wenn der Satz zu lange ist, mache Auslassungen mit "...", aber es soll trotzdem als ganzer Satz Am Ende ausgegeben werden.
- Wenn absolut kein passender Satz gefunden wird, schreibe "Es wurde kein direktes Zitat gefunden."
- Es ist das Jahr 2025.

Abschließend: Selbst wenn das Zitat nicht perfekt ist, extrahiere den BEST MÖGLICHEN Abschnitt, 
der die Antwort am ehesten unterstützt. "KEINE_EXTRAKTION_MÖGLICH" sollte nur in absoluten 
Ausnahmefällen verwendet werden.

EXTRAHIERTER ABSCHNITT:
"""

FALLBACK_QUOTES = {
    1: "Die Anschaffungs- oder Herstellungskosten [...] von abnutzbaren beweglichen Wirtschaftsgütern des Anlagevermögens, die einer selbständigen Nutzung fähig sind, können im Wirtschaftsjahr der Anschaffung [...] in voller Höhe als Betriebsausgaben abgezogen werden, wenn die Anschaffungs- oder Herstellungskosten [...] für das einzelne Wirtschaftsgut 800 Euro nicht übersteigen",
    
    2: "Für die Inanspruchnahme von Handwerkerleistungen für Renovierungs-, Erhaltungs- und Modernisierungsmaßnahmen ermäßigt sich die tarifliche Einkommensteuer, [...] um 20 Prozent der Aufwendungen des Steuerpflichtigen, höchstens jedoch um 1200 Euro.",
    
    3: "Bei der Ermittlung der Einkünfte aus Kapitalvermögen ist als Werbungskosten ein Betrag von 1000 Euro abzuziehen (Sparer-Pauschbetrag);",
    
    4: "Als Unterkunftskosten für eine doppelte Haushaltsführung können im Inland die tatsächlichen Aufwendungen für die Nutzung der Unterkunft angesetzt werden, höchstens 1 000 Euro im Monat"
}