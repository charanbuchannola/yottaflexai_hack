"""Governed theme taxonomy, multilingual synthetic phrase banks, and linguistic variants."""

from dataclasses import dataclass

from voc_intel.db.base import SentimentPolarity, ThemeCategory


@dataclass(frozen=True)
class ThemeSpec:
    """Definition of a single governed theme in the taxonomy."""

    theme_id: str
    theme_code: str
    theme_name: str
    parent_theme_id: str | None
    category: ThemeCategory
    severity_weight: float
    keywords_by_lang: dict[str, tuple[str, ...]]
    recommended_action: str
    owner_role: str


THEME_TAXONOMY: tuple[ThemeSpec, ...] = (
    ThemeSpec(
        theme_id="THEME-000001",
        theme_code="APP_CRASH_STABILITY",
        theme_name="Application Crashes & Stability",
        parent_theme_id=None,
        category=ThemeCategory.PERFORMANCE_RELIABILITY,
        severity_weight=1.50,
        keywords_by_lang={
            "en": ("crash", "crashed", "freeze", "froze", "unresponsive", "error 500", "stability", "stable", "rock solid", "zero crashes", "unexpected shutdowns", "uptime", "client reload"),
            "es": ("se cierra", "cuelga", "error 500", "bloquea", "estabilidad", "estable", "sin caídas", "reinicio menor"),
            "fr": ("plantage", "planté", "figé", "erreur 500", "stabilité", "stable", "aucun plantage", "incident majeur"),
            "de": ("abgestürzt", "absturz", "eingefroren", "fehler 500", "stabilität", "stabil", "keine abstürze", "standardbetrieb"),
        },
        recommended_action="Audit crash telemetry, deploy hotfix for unhandled exceptions, and add regression smoke tests.",
        owner_role="Platform Reliability Engineering",
    ),
    ThemeSpec(
        theme_id="THEME-000002",
        theme_code="SLOW_PERFORMANCE_LATENCY",
        theme_name="Slow Performance & Latency",
        parent_theme_id="THEME-000001",
        category=ThemeCategory.PERFORMANCE_RELIABILITY,
        severity_weight=1.30,
        keywords_by_lang={
            "en": ("slow", "latency", "lag", "timeout", "loading", "sluggish", "fast", "snappy", "instant", "responsive", "performance", "spinner", "speed"),
            "es": ("lento", "lenta", "latencia", "tarda", "tiempo de espera", "rápido", "ágil", "fluido", "velocidad", "rendimiento"),
            "fr": ("lent", "lente", "latence", "délai", "chargement", "rapide", "réactif", "fluide", "vitesse", "performances"),
            "de": ("langsam", "latenz", "verzögerung", "ladezeit", "träg", "schnell", "reaktionsschnell", "geschwindigkeit", "ladezeiten"),
        },
        recommended_action="Profile slow queries, optimize payload pagination, and tune cache TTLs on high-traffic endpoints.",
        owner_role="Backend Performance Team",
    ),
    ThemeSpec(
        theme_id="THEME-000003",
        theme_code="BILLING_OVERCHARGE",
        theme_name="Billing Errors & Overcharges",
        parent_theme_id=None,
        category=ThemeCategory.BILLING_PRICING,
        severity_weight=1.45,
        keywords_by_lang={
            "en": ("overcharge", "overcharged", "double billed", "invoice", "invoicing", "duplicate charge", "refund", "billing", "proration"),
            "es": ("cobro duplicado", "cargo extra", "factura", "facturación", "facturas", "reembolso", "prorrateo"),
            "fr": ("surfacturation", "double prélèvement", "facture", "facturation", "remboursement"),
            "de": ("doppelbelastung", "rechnungsfehler", "rechnung", "rechnungen", "rückerstattung", "abrechnung"),
        },
        recommended_action="Reconcile billing webhook idempotency keys, issue proactive credits, and verify invoice proration logic.",
        owner_role="Billing & Revenue Operations",
    ),
    ThemeSpec(
        theme_id="THEME-000004",
        theme_code="PRICING_TRANSPARENCY",
        theme_name="Pricing & Plan Transparency",
        parent_theme_id="THEME-000003",
        category=ThemeCategory.BILLING_PRICING,
        severity_weight=1.15,
        keywords_by_lang={
            "en": ("hidden fee", "surprise fee", "unclear pricing", "tier limit", "pricing", "fair value"),
            "es": ("tarifa oculta", "precio poco claro", "límite del plan", "límites del plan", "precios", "buen valor"),
            "fr": ("frais cachés", "tarif flou", "plafond du forfait", "plafonds du forfait", "tarification", "grille tarifaire", "bon rapport"),
            "de": ("versteckte gebühren", "unklare preise", "tariflimit", "tariflimits", "preisgestaltung", "preisliste", "faires preis"),
        },
        recommended_action="Clarify usage overage thresholds in pricing documentation and add in-app quota warnings.",
        owner_role="Product Marketing & Pricing",
    ),
    ThemeSpec(
        theme_id="THEME-000005",
        theme_code="SUPPORT_SLOW_RESPONSE",
        theme_name="Support Delay & Escalation",
        parent_theme_id=None,
        category=ThemeCategory.SUPPORT_EXPERIENCE,
        severity_weight=1.35,
        keywords_by_lang={
            "en": ("waiting days", "no reply", "slow support", "ignored ticket", "sla breach", "unanswered", "delayed response", "response times", "triage update", "ticket queue", "ticket status", "outage ticket"),
            "es": ("sin respuesta", "soporte lento", "esperando días", "ticket ignorado", "tiempos de respuesta", "ticket", "cola estándar"),
            "fr": ("sans réponse", "support lent", "attente interminable", "ticket ignoré", "délais de réponse", "ticket", "file d'attente"),
            "de": ("keine antwort", "langsamer support", "tagelang warten", "ticket ignoriert", "verzögerte hilfe", "reaktionszeiten", "ticket", "warteschlange"),
        },
        recommended_action="Rebalance Tier-1/Tier-2 queue routing and enforce automated SLA escalation alerts at 75% threshold.",
        owner_role="Customer Support Operations",
    ),
    ThemeSpec(
        theme_id="THEME-000006",
        theme_code="SUPPORT_HELPFUL_RESOLUTION",
        theme_name="Support Resolution Quality",
        parent_theme_id=None,
        category=ThemeCategory.SUPPORT_EXPERIENCE,
        severity_weight=0.90,
        keywords_by_lang={
            "en": ("helpful agent", "resolved quickly", "support team", "knowledgeable", "follow-up", "customer care", "agent solved", "support agent", "support desk", "closed our"),
            "es": ("agente amable", "resolvió rápido", "equipo de soporte", "excelente atención", "seguimiento", "agente", "soporte"),
            "fr": ("conseiller efficace", "résolu rapidement", "équipe support", "compétent", "suivi", "conseiller", "réponses du support"),
            "de": ("hilfsbereiter mitarbeiter", "schnell gelöst", "support-team", "kompetent", "mitarbeiter", "support"),
        },
        recommended_action="Document top resolution playbooks and scale proactive customer health check-ins.",
        owner_role="Customer Success Leadership",
    ),
    ThemeSpec(
        theme_id="THEME-000007",
        theme_code="ONBOARDING_COMPLEXITY",
        theme_name="Onboarding & Setup Complexity",
        parent_theme_id=None,
        category=ThemeCategory.UX_ONBOARDING,
        severity_weight=1.10,
        keywords_by_lang={
            "en": ("onboarding", "setup", "learning curve", "configuration", "getting started"),
            "es": ("incorporación", "configuración", "curva de aprendizaje", "primeros pasos"),
            "fr": ("prise en main", "configuration", "courbe d'apprentissage", "démarrage", "installation facile"),
            "de": ("einarbeitung", "einrichtung", "lernkurve", "erste schritte", "setup", "erstkonfiguration"),
        },
        recommended_action="Simplify first-run setup checklist, add interactive templates, and surface inline contextual tooltips.",
        owner_role="Onboarding & Growth Product",
    ),
    ThemeSpec(
        theme_id="THEME-000008",
        theme_code="UI_USABILITY_INTUITIVE",
        theme_name="Interface Usability & Navigation",
        parent_theme_id="THEME-000007",
        category=ThemeCategory.UX_ONBOARDING,
        severity_weight=0.85,
        keywords_by_lang={
            "en": ("interface", "navigation", "dashboard", "intuitive", "cluttered", "hard to find", "clean design"),
            "es": ("interfaz", "navegación", "panel", "intuitiva", "recargada", "diseño limpio"),
            "fr": ("interface", "navigation", "tableau de bord", "intuitif", "encombré", "design épuré"),
            "de": ("benutzeroberfläche", "navigation", "dashboard", "intuitiv", "unübersichtlich", "klares design"),
        },
        recommended_action="Streamline primary navigation hierarchy and run usability testing on top reporting views.",
        owner_role="Product Design & UX",
    ),
    ThemeSpec(
        theme_id="THEME-000009",
        theme_code="FEATURE_GAP_EXPORT",
        theme_name="Reporting & Export Feature Gaps",
        parent_theme_id=None,
        category=ThemeCategory.PRODUCT_QUALITY,
        severity_weight=1.05,
        keywords_by_lang={
            "en": ("csv export", "pdf export", "export", "exporting", "missing feature", "scheduled report", "custom filter"),
            "es": ("exportación", "exportar", "falta función", "reporte", "reportes", "filtros avanzados"),
            "fr": ("export", "exportation", "fonction manquante", "rapport", "filtres avancés"),
            "de": ("csv-export", "export", "fehlende funktion", "bericht", "berichte", "massenexport", "filter"),
        },
        recommended_action="Prioritize scheduled CSV/PDF batch exports and saved custom filter presets on quarterly roadmap.",
        owner_role="Core Product Management",
    ),
    ThemeSpec(
        theme_id="THEME-000010",
        theme_code="DATA_SYNC_ACCURACY",
        theme_name="Data Sync & Metric Accuracy",
        parent_theme_id=None,
        category=ThemeCategory.PRODUCT_QUALITY,
        severity_weight=1.40,
        keywords_by_lang={
            "en": ("data sync", "out of sync", "sync", "stale metrics", "stale numbers", "mismatch", "accurate numbers", "reconciled"),
            "es": ("sincronización", "desincronizado", "datos desactualizados", "discrepancia", "números exactos", "coincidieron"),
            "fr": ("synchronisation", "désynchronisée", "données obsolètes", "écart de chiffres", "données fiables", "données d'hier"),
            "de": ("datensynchronisierung", "nicht synchron", "veraltete daten", "zahlenabweichung", "präzise daten", "stimmten exakt"),
        },
        recommended_action="Add reconciliation checksum alerts on sync pipelines and fix incremental cursor checkpointing.",
        owner_role="Data Engineering",
    ),
    ThemeSpec(
        theme_id="THEME-000011",
        theme_code="API_INTEGRATION_RELIABILITY",
        theme_name="API & Webhook Integrations",
        parent_theme_id=None,
        category=ThemeCategory.INTEGRATIONS,
        severity_weight=1.30,
        keywords_by_lang={
            "en": ("webhook", "api", "sdk", "rest endpoint", "integration", "oauth"),
            "es": ("webhook", "api", "integración", "oauth"),
            "fr": ("webhook", "api", "intégration", "oauth"),
            "de": ("webhook", "api", "integration", "oauth", "rest-schnittstelle"),
        },
        recommended_action="Publish webhook retry backoff guarantees, increase burst rate limits, and expand SDK examples.",
        owner_role="Developer Platform Team",
    ),
    ThemeSpec(
        theme_id="THEME-000012",
        theme_code="SECURITY_ACCESS_CONTROLS",
        theme_name="Security, SSO & Access Controls",
        parent_theme_id=None,
        category=ThemeCategory.SECURITY_PRIVACY,
        severity_weight=1.60,
        keywords_by_lang={
            "en": ("sso", "permissions", "role access", "audit log", "mfa", "encryption", "compliance", "rbac", "security"),
            "es": ("sso", "permisos", "control de acceso", "registro de auditoría", "cifrado", "cumplimiento", "seguridad"),
            "fr": ("sso", "permissions", "contrôle d'accès", "journal d'audit", "chiffrement", "conformité"),
            "de": ("sso", "berechtigungen", "zugriffskontrolle", "audit-protokoll", "verschlüsselung", "compliance"),
        },
        recommended_action="Harden RBAC permission scopes, validate SAML/SSO assertion errors, and expand audit trail filters.",
        owner_role="Security & Trust Engineering",
    ),
)

THEME_BY_ID: dict[str, ThemeSpec] = {t.theme_id: t for t in THEME_TAXONOMY}
THEME_BY_CODE: dict[str, ThemeSpec] = {t.theme_code: t for t in THEME_TAXONOMY}


# Core multilingual clauses keyed by (theme_code, polarity_mode, lang)
# polarity_mode in {"POSITIVE", "NEGATIVE", "NEUTRAL"}
THEME_CLAUSES: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {
    "APP_CRASH_STABILITY": {
        "POSITIVE": {
            "en": (
                "{product} stayed rock solid with zero crashes throughout our entire month-end run.",
                "Stability in {product} has been outstanding lately and the desktop client never froze once.",
                "Zero unexpected shutdowns or error 500 alerts on {product} even under peak batch load.",
            ),
            "es": (
                "{product} se mantuvo estable y sin caídas durante todo el cierre mensual.",
                "La estabilidad de {product} fue excelente, nunca se bloqueó ni mostró error 500.",
            ),
            "fr": (
                "{product} est resté parfaitement stable sans aucun plantage pendant la clôture.",
                "La stabilité de {product} est remarquable et aucune erreur 500 n'est apparue.",
            ),
            "de": (
                "{product} lief absolut stabil und hatte im gesamten Monatsabschluss keine Abstürze.",
                "Die Stabilität von {product} ist hervorragend, das System ist kein einziges Mal eingefroren.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "{product} crashed repeatedly with an error 500 whenever we opened large workspaces.",
                "The application froze and became completely unresponsive twice during our morning review.",
                "Frequent stability drops in {product} forced our analysts to restart mid-session.",
            ),
            "es": (
                "{product} se cierra con error 500 cada vez que abrimos paneles grandes.",
                "La aplicación se cuelga y se bloquea por completo durante las revisiones diarias.",
            ),
            "fr": (
                "{product} a planté à répétition avec une erreur 500 sur les grands espaces.",
                "L'application reste figée et inutilisable à chaque pic d'activité.",
            ),
            "de": (
                "{product} ist beim Öffnen großer Berichte mehrfach mit Fehler 500 abgestürzt.",
                "Die Anwendung ist wiederholt eingefroren und hat laufende Arbeit verloren.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "{product} ran normally for routine checks, though stability under heavier batches remains untested.",
                "Observed standard uptime on {product} this week with one minor client reload.",
            ),
            "es": (
                "{product} funcionó con normalidad en tareas básicas, aunque falta probar cargas altas.",
                "Estabilidad habitual en {product} esta semana tras un reinicio menor.",
            ),
            "fr": (
                "{product} a fonctionné normalement pour les tâches courantes sans incident majeur.",
                "Stabilité conforme aux attentes sur {product} cette semaine.",
            ),
            "de": (
                "{product} lief im Standardbetrieb normal, größere Lasttests stehen noch aus.",
                "Normale Stabilität bei {product} in dieser Woche ohne größere Auffälligkeiten.",
            ),
        },
    },
    "SLOW_PERFORMANCE_LATENCY": {
        "POSITIVE": {
            "en": (
                "{product} feels remarkably fast and snappy even when filtering across quarterly tables.",
                "Page loading latency on {product} dropped noticeably and workflows feel instant.",
                "Responsive dashboards in {product} make daily triage effortless.",
            ),
            "es": (
                "{product} se siente muy rápido y ágil incluso al filtrar grandes tablas.",
                "La latencia de carga en {product} mejoró bastante y todo responde fluido.",
            ),
            "fr": (
                "{product} est très rapide et réactif même avec des filtres complexes.",
                "Le temps de chargement sur {product} est fluide et quasi instantané.",
            ),
            "de": (
                "{product} arbeitet bemerkenswert schnell und reaktionsschnell bei großen Tabellen.",
                "Die Ladezeit in {product} ist spürbar gesunken und die Ansicht reagiert sofort.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "Severe latency in {product} caused dashboards to hit timeout errors before rendering.",
                "{product} is painfully slow and sluggish when switching between filtered tabs.",
                "High loading lag in {product} delayed our team workflow by twenty minutes each morning.",
            ),
            "es": (
                "{product} es demasiado lento y los gráficos fallan por tiempo de espera.",
                "La latencia excesiva en {product} hace que cada pantalla tarde en cargar.",
            ),
            "fr": (
                "{product} est très lent et plusieurs requêtes dépassent le délai d'attente.",
                "Une latence élevée rend le chargement des tableaux pénible sur {product}.",
            ),
            "de": (
                "{product} ist extrem langsam und bricht wegen hoher Latenz mit Timeout ab.",
                "Die träge Ladezeit in {product} bremst unsere tägliche Auswertung massiv aus.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "Loading speed on {product} is acceptable for small views and average on larger filters.",
                "Performance in {product} matches baseline expectations without major spikes.",
            ),
            "es": (
                "La velocidad de {product} es aceptable en vistas pequeñas y estándar en filtros largos.",
                "El rendimiento general de {product} se mantiene dentro de lo esperado.",
            ),
            "fr": (
                "La vitesse de chargement sur {product} reste correcte pour un usage standard.",
                "Les performances de {product} sont dans la moyenne habituelle.",
            ),
            "de": (
                "Die Geschwindigkeit von {product} ist bei kleineren Ansichten akzeptabel.",
                "Die Ladezeiten in {product} entsprechen dem üblichen Durchschnitt.",
            ),
        },
    },
    "BILLING_OVERCHARGE": {
        "POSITIVE": {
            "en": (
                "Billing on {product} has been clean and accurate with zero duplicate charges after our seat upgrade.",
                "Invoicing for {product} reconciled seamlessly with our accounting ledger this quarter.",
            ),
            "es": (
                "La facturación de {product} fue exacta y sin cargos extra tras ajustar licencias.",
                "Todas las facturas de {product} cuadraron correctamente este trimestre.",
            ),
            "fr": (
                "La facturation de {product} est exacte et claire après notre changement de forfait.",
                "Aucune erreur de facture constatée sur {product} ce trimestre.",
            ),
            "de": (
                "Die Abrechnung für {product} war nach dem Upgrade vollständig korrekt ohne Doppelbelastung.",
                "Alle Rechnungen zu {product} ließen sich problemlos abgleichen.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "We were double billed on our latest {product} invoice and are still waiting on a refund.",
                "An unexplained overcharge appeared on our {product} statement right after renewal.",
                "Duplicate charge and proration invoice error on {product} caused an accounting mismatch.",
            ),
            "es": (
                "Recibimos un cobro duplicado en la factura de {product} y seguimos esperando reembolso.",
                "Apareció un cargo extra sin explicación en nuestra renovación de {product}.",
            ),
            "fr": (
                "Nous avons subi un double prélèvement sur la facture {product} sans remboursement reçu.",
                "Une surfacturation et une erreur de facture sont apparues lors du renouvellement {product}.",
            ),
            "de": (
                "Bei der letzten {product}-Rechnung gab es eine Doppelbelastung und die Rückerstattung fehlt noch.",
                "Ein unerklärter Rechnungsfehler führte zu einer überhöhten Rechnung für {product}.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "Reviewed our monthly {product} invoice line items and requested standard PO formatting.",
                "Checked seat proration dates on the {product} billing portal for next cycle.",
            ),
            "es": (
                "Revisamos los conceptos de la factura mensual de {product} para el próximo ciclo.",
                "Consultamos las fechas de prorrateo en el portal de facturación de {product}.",
            ),
            "fr": (
                "Vérification des lignes de facturation mensuelle sur le portail {product}.",
                "Demande standard d'ajout de numéro de commande sur la facture {product}.",
            ),
            "de": (
                "Die monatliche Rechnungsübersicht für {product} wurde für den nächsten Zyklus geprüft.",
                "Standardanfrage zur Anpassung der Bestellnummer auf der {product}-Rechnung.",
            ),
        },
    },
    "PRICING_TRANSPARENCY": {
        "POSITIVE": {
            "en": (
                "Transparent pricing tiers on {product} delivered fair value and predictable renewal budgeting.",
                "Clear tier limits on the {product} pricing page made executive sign-off straightforward.",
            ),
            "es": (
                "Los precios transparentes de {product} ofrecen buen valor y presupuesto predecible.",
                "Los límites del plan en {product} están explicados con total claridad.",
            ),
            "fr": (
                "La tarification claire de {product} offre un bon rapport qualité-prix.",
                "Les limites du forfait {product} sont lisibles et sans mauvaise surprise.",
            ),
            "de": (
                "Die transparente Preisgestaltung von {product} bietet ein faires Preis-Leistungs-Verhältnis.",
                "Klare Tariflimits auf der Preisseite von {product} erleichtern die Budgetplanung.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "Surprise fee and unclear pricing around {product} API overages caught our finance team off guard.",
                "Hidden fee tiers and sudden tier limit caps on {product} feel misleading.",
            ),
            "es": (
                "Una tarifa oculta y un precio poco claro por exceso de uso en {product} nos sorprendió.",
                "El límite del plan en {product} no estaba visible en la página comercial.",
            ),
            "fr": (
                "Des frais cachés et un tarif flou sur les dépassements {product} nous ont surpris.",
                "Le plafond du forfait {product} manque de clarté avant la souscription.",
            ),
            "de": (
                "Versteckte Gebühren und unklare Preise bei Überschreitung des Tariflimits in {product} sind ärgerlich.",
                "Die Preisgestaltung für Zusatzmodule in {product} wirkt intransparent.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "Comparing {product} annual tier limits against our projected seat growth for next year.",
                "Requested the updated enterprise pricing matrix for {product} add-ons.",
            ),
            "es": (
                "Comparando los límites del plan anual de {product} con nuestro crecimiento previsto.",
                "Solicitamos la tabla vigente de precios para módulos adicionales de {product}.",
            ),
            "fr": (
                "Comparaison des plafonds du forfait annuel {product} avec nos prévisions.",
                "Demande de grille tarifaire standard pour les options {product}.",
            ),
            "de": (
                "Wir vergleichen derzeit die Tariflimits von {product} mit dem geplanten Wachstum.",
                "Aktualisierte Preisliste für Enterprise-Erweiterungen zu {product} angefordert.",
            ),
        },
    },
    "SUPPORT_SLOW_RESPONSE": {
        "POSITIVE": {
            "en": (
                "Support response times on {product} improved sharply this month with prompt first replies.",
                "Our priority {product} ticket received an initial triage update within twenty minutes.",
            ),
            "es": (
                "Los tiempos de respuesta de soporte en {product} mejoraron notablemente este mes.",
                "Nuestro ticket sobre {product} recibió respuesta inicial en pocos minutos.",
            ),
            "fr": (
                "Les délais de réponse du support {product} se sont nettement accélérés.",
                "Notre ticket prioritaire sur {product} a été pris en charge en vingt minutes.",
            ),
            "de": (
                "Die Reaktionszeiten beim Support für {product} haben sich diesen Monat stark verbessert.",
                "Unser Ticket zu {product} wurde innerhalb von zwanzig Minuten erstbearbeitet.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "Been waiting days with no reply on our urgent {product} ticket — clear SLA breach.",
                "Slow support response left our {product} outage ticket unanswered for over 72 hours.",
                "Support ignored ticket follow-ups twice and delayed response until escalation.",
            ),
            "es": (
                "Llevamos esperando días sin respuesta en nuestro ticket urgente de {product}.",
                "Soporte lento y ticket ignorado durante tres días sin actualización.",
            ),
            "fr": (
                "Nous sommes sans réponse depuis des jours sur notre ticket critique {product}.",
                "Le support lent a laissé notre ticket ignoré au-delà du délai contractuel.",
            ),
            "de": (
                "Wir warten seit Tagen auf eine Rückmeldung — keine Antwort zu unserem {product}-Ticket.",
                "Langsamer Support und verzögerte Hilfe haben unsere Störung unnötig verlängert.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "Ticket queue acknowledgement for {product} arrived automatically; waiting for specialist routing.",
                "Checked ticket status on {product} and confirmed standard queue position.",
            ),
            "es": (
                "Recibimos acuse automático del ticket de {product}, a la espera de asignación.",
                "Consultamos el estado del ticket sobre {product} en la cola estándar.",
            ),
            "fr": (
                "Accusé de réception reçu pour le ticket {product}, en attente d'affectation.",
                "Suivi standard du ticket {product} dans la file d'attente.",
            ),
            "de": (
                "Automatische Eingangsbestätigung für das {product}-Ticket erhalten, Zuweisung läuft.",
                "Statusprüfung des {product}-Tickets in der regulären Warteschlange.",
            ),
        },
    },
    "SUPPORT_HELPFUL_RESOLUTION": {
        "POSITIVE": {
            "en": (
                "A knowledgeable and helpful agent resolved quickly what broke in {product} and sent clear follow-up notes.",
                "Customer care on {product} went above and beyond — the support team solved our setup issue in one call.",
            ),
            "es": (
                "Un agente amable resolvió rápido el problema en {product} y dio excelente seguimiento.",
                "El equipo de soporte de {product} brindó una atención sobresaliente.",
            ),
            "fr": (
                "Un conseiller efficace et compétent a résolu rapidement notre souci sur {product}.",
                "L'équipe support de {product} a assuré un suivi exemplaire jusqu'à résolution.",
            ),
            "de": (
                "Ein sehr hilfsbereiter Mitarbeiter hat das Problem in {product} schnell gelöst.",
                "Das Support-Team von {product} war äußerst kompetent und zuverlässig.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "Support team replies on {product} felt scripted and failed to resolve the root problem after four handoffs.",
                "Support closed our {product} ticket without verifying that the underlying bug was resolved.",
            ),
            "es": (
                "Las respuestas del equipo de soporte en {product} fueron genéricas y no resolvieron el fallo.",
                "Cerraron el caso de {product} sin comprobar si el problema seguía activo.",
            ),
            "fr": (
                "Les réponses du support {product} restaient superficielles sans véritable résolution.",
                "Le ticket {product} a été clôturé avant la résolution effective du souci.",
            ),
            "de": (
                "Die Antworten des Support-Teams zu {product} wirkten standardisiert und lösten die Ursache nicht.",
                "Unser {product}-Fall wurde geschlossen, bevor der Fehler behoben war.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "Support agent shared documentation links for {product} and scheduled a standard follow-up.",
                "Received troubleshooting steps from the {product} support desk to test tomorrow.",
            ),
            "es": (
                "El agente compartió enlaces de ayuda de {product} para validar mañana.",
                "Recibimos pasos estándar de diagnóstico del equipo de soporte de {product}.",
            ),
            "fr": (
                "Le conseiller a transmis la documentation standard sur {product} pour vérification.",
                "Étapes de diagnostic reçues de l'équipe support {product}.",
            ),
            "de": (
                "Der Mitarbeiter hat Dokumentationslinks zu {product} zur Prüfung bereitgestellt.",
                "Standard-Diagnoseschritte vom {product}-Support für den Test erhalten.",
            ),
        },
    },
    "ONBOARDING_COMPLEXITY": {
        "POSITIVE": {
            "en": (
                "Smooth setup and easy onboarding let new hires start using {product} productively on day one.",
                "Getting started with {product} was effortless thanks to guided configuration checklists.",
            ),
            "es": (
                "La configuración sencilla de {product} permitió que el equipo empezara el primer día.",
                "La incorporación en {product} fue clara y sin fricciones desde los primeros pasos.",
            ),
            "fr": (
                "L'installation facile et la prise en main rapide de {product} ont convaincu toute l'équipe.",
                "Le démarrage sur {product} est guidé et sans friction.",
            ),
            "de": (
                "Einfaches Setup und eine klare Einarbeitung machten den Start mit {product} mühelos.",
                "Die ersten Schritte in {product} waren sehr gut strukturiert.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "Initial setup confusing and steep learning curve made {product} onboarding drag out for three weeks.",
                "Workspace configuration in {product} lacks clear defaults and stalls getting started.",
            ),
            "es": (
                "La configuración confusa y la curva de aprendizaje de {product} retrasaron la adopción.",
                "Los primeros pasos en {product} carecen de guías claras para administradores nuevos.",
            ),
            "fr": (
                "La configuration complexe et la courbe d'apprentissage freinent la prise en main de {product}.",
                "Le démarrage initial sur {product} manque d'instructions simples.",
            ),
            "de": (
                "Eine verwirrende Einrichtung und steile Lernkurve erschweren die Einarbeitung in {product}.",
                "Die Erstkonfiguration von {product} ist ohne externe Hilfe kaum verständlich.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "Completed initial {product} onboarding checklist and awaiting final team role mappings.",
                "Workspace configuration on {product} followed the standard setup guide.",
            ),
            "es": (
                "Completamos la lista inicial de incorporación en {product} según la guía.",
                "La configuración base de {product} siguió los pasos habituales.",
            ),
            "fr": (
                "Liste de démarrage {product} complétée conformément au guide standard.",
                "Configuration initiale de {product} effectuée avec les paramètres par défaut.",
            ),
            "de": (
                "Die Checkliste für die Einarbeitung in {product} wurde gemäß Leitfaden abgearbeitet.",
                "Basis-Setup für {product} mit den Standardeinstellungen abgeschlossen.",
            ),
        },
    },
    "UI_USABILITY_INTUITIVE": {
        "POSITIVE": {
            "en": (
                "Clean design and intuitive navigation make the {product} dashboard layout a pleasure to use.",
                "Everyday tasks in {product} take fewer clicks thanks to the thoughtful interface.",
            ),
            "es": (
                "El diseño limpio y la navegación intuitiva hacen muy cómodo el panel de {product}.",
                "La interfaz de {product} resulta clara y fácil de recorrer.",
            ),
            "fr": (
                "Le design épuré et la navigation intuitive rendent l'interface {product} très agréable.",
                "Le tableau de bord {product} est lisible et bien structuré.",
            ),
            "de": (
                "Klares Design und intuitive Navigation machen das {product}-Dashboard sehr angenehm.",
                "Die Benutzeroberfläche von {product} ist übersichtlich und logisch aufgebaut.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "The {product} dashboard layout feels cluttered and key filters are hard to find.",
                "Confusing interface navigation in {product} buries basic settings four menus deep.",
            ),
            "es": (
                "El panel de {product} está recargado y cuesta encontrar los controles principales.",
                "La navegación en la interfaz de {product} resulta poco intuitiva.",
            ),
            "fr": (
                "L'interface {product} semble encombrée et les réglages essentiels sont difficiles à trouver.",
                "La navigation du tableau de bord {product} manque de cohérence.",
            ),
            "de": (
                "Das Dashboard von {product} wirkt unübersichtlich und wichtige Optionen sind versteckt.",
                "Die Navigation in der Benutzeroberfläche von {product} erfordert zu viele Klicks.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "The {product} interface covers core workflows adequately with familiar layout conventions.",
                "Navigation in {product} takes a brief orientation but behaves predictably.",
            ),
            "es": (
                "La interfaz de {product} cumple con lo esperado usando un diseño convencional.",
                "El panel de {product} es funcional para la operación diaria.",
            ),
            "fr": (
                "L'interface {product} reste fonctionnelle et suit les conventions habituelles.",
                "La navigation sur {product} répond aux besoins standards.",
            ),
            "de": (
                "Die Benutzeroberfläche von {product} deckt die Standardfunktionen zweckmäßig ab.",
                "Das Dashboard von {product} folgt gewohnten Mustern.",
            ),
        },
    },
    "FEATURE_GAP_EXPORT": {
        "POSITIVE": {
            "en": (
                "Rich exports and scheduled report delivery in {product} save our ops team hours every Friday.",
                "Custom filter presets and clean CSV export in {product} cover every stakeholder request.",
            ),
            "es": (
                "La exportación CSV y los reportes programados de {product} ahorran horas de trabajo.",
                "Los filtros avanzados para exportar datos en {product} funcionan muy bien.",
            ),
            "fr": (
                "L'export CSV et les rapports planifiés dans {product} font gagner un temps précieux.",
                "Les filtres avancés pour l'exportation en masse sur {product} sont complets.",
            ),
            "de": (
                "CSV-Export und geplante Berichte in {product} sparen unserem Team jede Woche viel Zeit.",
                "Erweiterte Filter für den Massenexport in {product} decken alle Anforderungen ab.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "Missing feature: {product} still lacks scheduled report delivery and bulk CSV export across filtered views.",
                "PDF export breaks table formatting and custom filter presets are missing in {product}.",
            ),
            "es": (
                "Falta función clave: {product} aún no permite exportación CSV masiva ni reporte programado.",
                "Al exportar datos desde {product} se pierden los filtros aplicados.",
            ),
            "fr": (
                "Fonction manquante dans {product} : aucun export CSV en masse ni rapport planifié natif.",
                "L'export PDF de {product} tronque les tableaux larges.",
            ),
            "de": (
                "Fehlende Funktion: {product} bietet keinen geplanten Bericht oder sauberen CSV-Massenexport.",
                "Beim Export aus {product} gehen benutzerdefinierte Filter verloren.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "Currently exporting single-table CSV snapshots from {product} manually once a week.",
                "Logged a feature inquiry about scheduled PDF export cadence in {product}.",
            ),
            "es": (
                "Por ahora descargamos manualmente las vistas CSV de {product} cada semana.",
                "Consultamos si {product} incluirá reportes automáticos en próximas versiones.",
            ),
            "fr": (
                "Exportation manuelle hebdomadaire des tableaux CSV depuis {product}.",
                "Question transmise concernant la feuille de route d'export PDF sur {product}.",
            ),
            "de": (
                "Derzeit nutzen wir den manuellen wöchentlichen CSV-Export in {product}.",
                "Anfrage zu künftigen Optionen für geplante Berichte in {product} gestellt.",
            ),
        },
    },
    "DATA_SYNC_ACCURACY": {
        "POSITIVE": {
            "en": (
                "Real-time sync in {product} kept all warehouse totals reconciled with accurate numbers.",
                "Data sync accuracy on {product} passed our full audit with zero discrepancies.",
            ),
            "es": (
                "La sincronización en {product} mantuvo números exactos en todos los reportes.",
                "Los datos de {product} coincidieron sin discrepancias con nuestro cierre.",
            ),
            "fr": (
                "La synchronisation des données sur {product} offre des données fiables à 100 %.",
                "Aucun écart de chiffres constaté dans {product} lors de notre audit.",
            ),
            "de": (
                "Die Datensynchronisierung in {product} liefert präzise Daten ohne Abweichungen.",
                "Alle Kennzahlen in {product} stimmten exakt mit unserem Bestand überein.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "{product} dashboards went out of sync with stale metrics and a 12% count mismatch.",
                "Data sync lag in {product} shows yesterday's stale numbers instead of live records.",
            ),
            "es": (
                "{product} quedó desincronizado con datos desactualizados y una clara discrepancia.",
                "Falla la sincronización de {product} y las métricas no coinciden con la base.",
            ),
            "fr": (
                "La synchronisation {product} est désynchronisée avec des données obsolètes et un écart de chiffres.",
                "Les compteurs de {product} restent figés sur des données d'hier.",
            ),
            "de": (
                "{product} ist nicht synchron und zeigt veraltete Daten mit deutlicher Zahlenabweichung.",
                "Fehlerhafte Datensynchronisierung in {product} verfälscht unsere Tagesberichte.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "Scheduled nightly data sync on {product} completed at 02:00 UTC as configured.",
                "Monitoring {product} sync timestamps after schema refresh.",
            ),
            "es": (
                "La sincronización nocturna de {product} finalizó en la ventana programada.",
                "Revisando las marcas de tiempo de sincronización en {product}.",
            ),
            "fr": (
                "La synchronisation nocturne de {product} s'est terminée à l'heure prévue.",
                "Suivi de routine des journaux de synchronisation {product}.",
            ),
            "de": (
                "Die nächtliche Datensynchronisierung von {product} lief planmäßig durch.",
                "Routineprüfung der Zeitstempel nach dem Schema-Update in {product}.",
            ),
        },
    },
    "API_INTEGRATION_RELIABILITY": {
        "POSITIVE": {
            "en": (
                "Reliable API endpoints and well-documented SDK webhooks made {product} integration seamless.",
                "Our REST endpoint sync with {product} handles bursts cleanly without OAuth token drops.",
            ),
            "es": (
                "La API estable y los webhooks claros facilitaron toda la integración con {product}.",
                "El manejo de token OAuth en {product} funciona de forma impecable.",
            ),
            "fr": (
                "L'API fiable et les webhooks bien documentés simplifient l'intégration {product}.",
                "La gestion des jetons OAuth sur {product} est fluide et stable.",
            ),
            "de": (
                "Eine zuverlässige API und saubere Webhooks machten die {product}-Integration reibungslos.",
                "Die REST-Schnittstelle und OAuth-Token-Erneuerung in {product} laufen stabil.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "Webhook delivery failures and tight API rate limit errors broke our {product} integration.",
                "Expired OAuth token refresh loops in the {product} SDK dropped nightly sync jobs.",
            ),
            "es": (
                "Errores de límite de API y fallos de webhook interrumpieron la integración con {product}.",
                "El token OAuth de {product} expira sin renovación automática.",
            ),
            "fr": (
                "Des erreurs de limite d'API et des pertes de webhook bloquent l'intégration {product}.",
                "Le renouvellement du jeton OAuth échoue sur le connecteur {product}.",
            ),
            "de": (
                "Webhook-Ausfälle und ein zu enges API-Limit unterbrechen unsere {product}-Integration.",
                "Fehler bei der OAuth-Token-Aktualisierung in {product} stoppen automatische Läufe.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "Testing {product} webhook payload signatures in our staging sandbox before cutover.",
                "Reviewing REST endpoint pagination headers in the {product} developer docs.",
            ),
            "es": (
                "Probando firmas de webhook de {product} en el entorno de pruebas.",
                "Revisando la documentación del límite de API de {product}.",
            ),
            "fr": (
                "Test des signatures webhook {product} dans notre environnement de préproduction.",
                "Consultation des en-têtes de pagination de l'API {product}.",
            ),
            "de": (
                "Wir testen derzeit die {product}-Webhook-Signaturen in der Staging-Umgebung.",
                "Prüfung der API-Dokumentation zu Rate-Limits für {product}.",
            ),
        },
    },
    "SECURITY_ACCESS_CONTROLS": {
        "POSITIVE": {
            "en": (
                "Granular RBAC permissions, SAML SSO, and tamper-evident audit logs in {product} passed security review.",
                "Encryption controls and MFA enforcement in {product} meet our enterprise compliance bar.",
            ),
            "es": (
                "Los permisos RBAC, SSO y registro de auditoría en {product} superaron la revisión de seguridad.",
                "El cifrado y cumplimiento en {product} cubren nuestros requisitos corporativos.",
            ),
            "fr": (
                "Les permissions RBAC, le SSO et le journal d'audit de {product} répondent aux exigences de conformité.",
                "Le chiffrement et le contrôle d'accès de {product} sont robustes.",
            ),
            "de": (
                "Granulare Berechtigungen, SSO und das Audit-Protokoll in {product} erfüllten unsere Compliance-Prüfung.",
                "Verschlüsselung und Zugriffskontrolle in {product} entsprechen unserem Sicherheitsstandard.",
            ),
        },
        "NEGATIVE": {
            "en": (
                "SSO login loop and overly broad default role access permissions in {product} raise compliance concerns.",
                "Audit log exports in {product} omit permission changes, blocking our security sign-off.",
            ),
            "es": (
                "Errores de inicio con SSO y permisos demasiado amplios en {product} generan riesgo de cumplimiento.",
                "El registro de auditoría de {product} no detalla cambios de acceso.",
            ),
            "fr": (
                "Des erreurs SSO et des permissions par défaut trop larges sur {product} posent un souci de conformité.",
                "Le journal d'audit {product} n'enregistre pas toutes les modifications de rôle.",
            ),
            "de": (
                "SSO-Anmeldefehler und zu weit gefasste Standard-Berechtigungen in {product} gefährden die Compliance.",
                "Im Audit-Protokoll von {product} fehlen Einträge zu geänderten Zugriffsrechten.",
            ),
        },
        "NEUTRAL": {
            "en": (
                "Configuring SAML SSO metadata and MFA enforcement rules for {product} workspace admins.",
                "Reviewing quarterly RBAC role access matrix in {product}.",
            ),
            "es": (
                "Configurando metadatos SSO y permisos de grupo para administradores en {product}.",
                "Revisión trimestral de control de acceso en {product}.",
            ),
            "fr": (
                "Configuration des métadonnées SSO et des rôles d'accès dans {product}.",
                "Revue trimestrielle des permissions RBAC sur {product}.",
            ),
            "de": (
                "Einrichtung der SSO-Metadaten und Zugriffskontrolle für {product}-Administratoren.",
                "Vierteljährliche Prüfung der Rollenberechtigungen in {product}.",
            ),
        },
    },
}

SARCASTIC_NEGATIVE_TEMPLATES: dict[str, dict[str, tuple[str, ...]]] = {
    "APP_CRASH_STABILITY": {
        "en": (
            "Oh fantastic, {product} crashed right before our executive demo — truly love losing an hour of work.",
            "Brilliant update: {product} froze twice in ten minutes, peak engineering right there.",
        ),
        "es": (
            "Qué maravilla, {product} se cierra justo antes de la reunión directiva, un lujo total.",
        ),
        "fr": (
            "Génial, {product} a encore planté en pleine présentation, un vrai bonheur.",
        ),
        "de": (
            "Wunderbar, {product} ist schon wieder vor der Abgabe abgestürzt, genau mein Humor.",
        ),
    },
    "SLOW_PERFORMANCE_LATENCY": {
        "en": (
            "Love watching the {product} loading spinner for four minutes straight, super productive morning.",
            "Amazing speed on {product} — gives me plenty of time to brew coffee while a filter loads.",
        ),
        "es": (
            "Me encanta mirar el indicador de carga lento de {product} durante minutos, súper productivo.",
        ),
        "fr": (
            "Formidable cette latence sur {product}, j'ai le temps de prendre un café à chaque clic.",
        ),
        "de": (
            "Herrlich, wie langsam {product} heute lädt — perfektes Geduldstraining am Morgen.",
        ),
    },
    "BILLING_OVERCHARGE": {
        "en": (
            "Nothing brightens my day like getting double billed on {product} and chasing a refund.",
            "So thoughtful of {product} to charge us twice for the exact same invoice.",
        ),
        "es": (
            "Qué detalle tan amable de {product} al enviarnos un cobro duplicado este mes.",
        ),
        "fr": (
            "Quelle belle surprise de voir un double prélèvement sur notre facture {product}.",
        ),
        "de": (
            "Wie aufmerksam, gleich eine Doppelbelastung auf der {product}-Rechnung zu bekommen.",
        ),
    },
    "SUPPORT_SLOW_RESPONSE": {
        "en": (
            "Zero replies after four days on an urgent {product} ticket — world-class urgency.",
            "Love how our {product} outage ticket sits untouched all week, really reassuring.",
        ),
        "es": (
            "Cuatro días sin respuesta en un ticket urgente de {product}, rapidez de otro nivel.",
        ),
        "fr": (
            "Quatre jours sans réponse pour un ticket critique {product}, quelle réactivité.",
        ),
        "de": (
            "Vier Tage keine Antwort auf ein dringendes {product}-Ticket, erstklassiges Tempo.",
        ),
    },
}

AMBIGUOUS_HEDGED_TEMPLATES: dict[str, tuple[str, ...]] = {
    "en": (
        "Hard to tell yet whether {product} is an upgrade; some pieces feel fine while a few steps remain clunky.",
        "Mixed feelings on {product} so far — it mostly runs okay, though we are still evaluating long-term fit.",
        "Not fully sure about {product} yet; basic workflows work alright, yet certain edges feel unfinished.",
    ),
    "es": (
        "Todavía es pronto para juzgar {product}; en general cumple, aunque hay partes algo confusas.",
        "Opinión dividida sobre {product}: lo básico funciona aceptable pero falta pulir detalles.",
    ),
    "fr": (
        "Difficile de se prononcer sur {product} pour le moment ; l'essentiel fonctionne mais certains points restent flous.",
        "Avis partagé sur {product} : correct dans l'ensemble sans être totalement convaincant.",
    ),
    "de": (
        "Schwer zu sagen bei {product}; im Kern läuft es ordentlich, manches wirkt jedoch unausgereift.",
        "Geteilter Eindruck zu {product}: für Grundaufgaben okay, aber noch mit Luft nach oben.",
    ),
}

CONTRAST_CONNECTORS: dict[str, tuple[str, ...]] = {
    "en": (" However, ", " On the other hand, ", " Although, "),
    "es": (" Sin embargo, ", " Aunque por otro lado, "),
    "fr": (" Cependant, ", " Toutefois, "),
    "de": (" Allerdings ", " Jedoch "),
}

CHANNEL_PREFIXES: dict[str, dict[str, tuple[str, ...]]] = {
    "SURVEY": {
        "en": ("Quarterly pulse check: ", "Feedback from our team: ", ""),
        "es": ("Encuesta trimestral: ", "Opinión del equipo: ", ""),
        "fr": ("Retour d'enquête : ", "Avis de l'équipe : ", ""),
        "de": ("Quartalsumfrage: ", "Team-Rückmeldung: ", ""),
    },
    "REVIEW": {
        "en": ("Verified user review: ", "After 3 months of daily use: ", ""),
        "es": ("Reseña de uso diario: ", "Tras varios meses de uso: ", ""),
        "fr": ("Avis après usage quotidien : ", "Retour produit : ", ""),
        "de": ("Praxiserfahrung: ", "Bewertung nach längerer Nutzung: ", ""),
    },
    "SUPPORT": {
        "en": ("Hi Support — ", "Urgent note from ops: ", "Following up on ticket: "),
        "es": ("Hola Soporte — ", "Nota de operaciones: ", "Seguimiento de caso: "),
        "fr": ("Bonjour le support — ", "Note opérationnelle : ", "Suivi du dossier : "),
        "de": ("Hallo Support — ", "Hinweis aus dem Betrieb: ", "Rückfrage zum Ticket: "),
    },
}

SUPPORT_AGENT_REPLIES: dict[str, tuple[str, ...]] = {
    "en": (
        "Thank you for flagging this on {product}. We reproduced the symptom and escalated diagnostics to engineering.",
        "We reviewed your {product} workspace logs and applied a configuration update; please confirm if resolved.",
        "I have updated your {product} case priority and shared the timeline with our billing/platform lead.",
    ),
    "es": (
        "Gracias por reportarlo en {product}. Ya revisamos los registros y escalamos el diagnóstico.",
        "Aplicamos un ajuste de configuración en su cuenta de {product}; por favor confirme si quedó resuelto.",
    ),
    "fr": (
        "Merci pour ce signalement sur {product}. Nous avons analysé les journaux et transmis au niveau supérieur.",
        "Un correctif de configuration vient d'être appliqué sur {product} ; merci de confirmer le bon fonctionnement.",
    ),
    "de": (
        "Vielen Dank für den Hinweis zu {product}. Wir haben die Protokolle geprüft und die Analyse eskaliert.",
        "Wir haben eine Konfigurationsanpassung für {product} eingespielt; bitte prüfen Sie das Verhalten.",
    ),
}
