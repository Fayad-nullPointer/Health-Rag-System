from typing import Optional


# Country name --> (hotline number, hotline name, url)
CRISIS_HOTLINES: dict[str, tuple[str, str, str]] = {
    # Middle East & North Africa
    "Egypt"               : ("08008880700",  "Egypt Crisis Line",          "https://www.befrienders.org"),
    "Saudi Arabia"        : ("920033360",    "KSA Mental Health Line",     "https://www.befrienders.org"),
    "United Arab Emirates": ("800HOPE",      "UAE Hope Line",              "https://www.befrienders.org"),
    "Jordan"              : ("110",          "Jordan Lifeline",            "https://www.befrienders.org"),
    "Lebanon"             : ("1564",         "Embrace Lebanon",            "https://embracelebanon.org"),
    "Morocco"             : ("0801004747",   "Morocco Crisis Line",        "https://www.befrienders.org"),
    "Tunisia"             : ("71108108",     "Tunisia Mental Health",      "https://www.befrienders.org"),
    "Kuwait"              : ("94006283",     "Kuwait Crisis Support",      "https://www.befrienders.org"),
    "Iraq"                : ("103",          "Iraq Emergency",             "https://www.befrienders.org"),
    "Libya"               : ("+218914590805","Libya Crisis Support",       "https://www.befrienders.org"),


    # English-speaking countries
    "United States"       : ("988",          "988 Suicide & Crisis Lifeline", "https://988lifeline.org"),
    "United Kingdom"      : ("116 123",      "Samaritans",                 "https://www.samaritans.org"),
    "Canada"              : ("1-833-456-4566","Canada Suicide Prevention", "https://www.crisisservicescanada.ca"),
    "Australia"           : ("13 11 14",     "Lifeline Australia",         "https://www.lifeline.org.au"),
    "Ireland"             : ("116 123",      "Samaritans Ireland",         "https://www.samaritans.org"),
    "New Zealand"         : ("0800 543 354", "Lifeline New Zealand",       "https://www.lifeline.org.nz"),
    "South Africa"        : ("0800 567 567", "SADAG",                      "https://www.sadag.org"),



    # Europe
    "Germany"             : ("0800 111 0 111","Telefonseelsorge",          "https://www.telefonseelsorge.de"),
    "France"              : ("3114",          "Numéro National Prévention", "https://www.3114.fr"),
    "Spain"               : ("024",           "Teléfono de la Esperanza",  "https://telefonodelaesperanza.org"),
    "Italy"               : ("02 2327 2327",  "Telefono Amico",            "https://www.telefonoamico.it"),
    "Netherlands"         : ("0900 0113",     "113 Zelfmoordpreventie",    "https://www.113.nl"),
    "Belgium"             : ("0800 32 123",   "Centre de Prévention",      "https://www.preventionsuicide.be"),
    "Sweden"              : ("90101",         "Mind Självmordslinjen",     "https://mind.se"),
    "Norway"              : ("116 123",       "Mental Helse",              "https://mentalhelse.no"),
    "Denmark"             : ("70 201 201",    "Livslinien",                "https://livslinien.dk"),
    "Finland"             : ("09 2525 0111",  "MIELI Mental Health",       "https://mieli.fi"),
    "Poland"              : ("116 123",       "Telefon Zaufania",          "https://116123.pl"),
    "Russia"              : ("8-800-2000-122","Russian Crisis Line",       "https://www.befrienders.org"),
    "Turkey"              : ("182",           "Turkey Crisis Line",        "https://www.befrienders.org"),



    # Asia
    "India"               : ("iCall: 9152987821", "iCall India",           "https://icallhelpline.org"),
    "Japan"               : ("0120-783-556", "Inochi no Denwa",            "https://www.inochinodenwa.org"),
    "China"               : ("400-161-9995", "Beijing Suicide Research",   "https://www.befrienders.org"),
    "South Korea"         : ("1393",          "Korea Suicide Prevention",  "https://www.befrienders.org"),
    "Pakistan"            : ("0317-4288665",  "Umang Pakistan",            "https://umang.com.pk"),
    "Bangladesh"          : ("16789",         "Kaan Pete Roi",             "https://www.befrienders.org"),
    "Sri Lanka"           : ("1926",          "Sumithrayo",                "https://www.befrienders.org"),
    "Indonesia"           : ("119 ext 8",     "Into The Light Indonesia",  "https://www.befrienders.org"),
    "Philippines"         : ("1553",          "Hopeline Philippines",      "https://hopeline.com.ph"),
    "Malaysia"            : ("015-599 9948",  "Befrienders KL",            "https://www.befrienders.org.my"),
    "Singapore"           : ("1800-221-4444", "SOS Singapore",             "https://www.sos.org.sg"),
    "Thailand"            : ("02-713-6793",   "Samaritans of Thailand",    "https://www.befrienders.org"),



    # Latin America
    "Brazil"              : ("188",           "CVV Brazil",                "https://www.cvv.org.br"),
    "Mexico"              : ("800-290-0024",  "SAPTEL Mexico",             "https://www.saptel.org.mx"),
    "Argentina"           : ("135",           "Centro de Asistencia",      "https://www.befrienders.org"),
    "Colombia"            : ("106",           "Línea 106",                 "https://www.befrienders.org"),
    "Chile"               : ("600-360-7777",  "Teléfono de la Esperanza",  "https://www.befrienders.org"),
}

# Fallback for any country not in the map
INTERNATIONAL_FALLBACK = (
    "befrienders.org",
    "Befrienders Worldwide",
    "https://www.befrienders.org"
)

CRISIS_TEXT_LINE = "Text HOME to 741741 (Crisis Text Line available in US, UK, Canada, Ireland)"


def get_hotline(country: str) -> dict:
    """
    Returns the crisis hotline info for a given country name.
    Falls back to Befrienders Worldwide if the country is not in the map.
    """
    country  = country.strip().title()
    match    = CRISIS_HOTLINES.get(country, INTERNATIONAL_FALLBACK)
    number, name, url = match

    return {
        "country"       : country,
        "hotline_number": number,
        "hotline_name"  : name,
        "hotline_url"   : url,
        "crisis_text"   : CRISIS_TEXT_LINE
    }



def format_crisis_banner(country: str) -> str:
    """
    Returns a plain-text crisis banner string for use in chat responses.
    """
    info = get_hotline(country)
    return (
        f"{info['hotline_name']}: {info['hotline_number']}  |  "
        f"{info['hotline_url']}"
    )



def list_supported_countries() -> list[str]:
    return sorted(CRISIS_HOTLINES.keys())