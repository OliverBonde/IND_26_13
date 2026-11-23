"""Display labels for BR18 Table 3.1. Rule IDs stay unchanged for calculations.

Source: https://www.bygningsreglementet.dk/tekniske-bestemmelser/17/
vejledninger/undervisningsbygninger/lydisolation-for-undervisningsbygninger/

These labels describe airborne-sound-insulation rows only; they do not
replace the supplementary guidance or constitute calculation logic.
"""

# Displayed Danish descriptions correspond to the lines of Table 3.1.
RULES_DA = {
    "T3.1_ALMINDELIG_HORISONTAL": "Mellem undervisningsrum samt mellem undervisningsrum og fællesrum, horisontalt",
    "T3.1_ALMINDELIG_VERTIKAL": "Mellem undervisningsrum samt mellem undervisningsrum og fællesrum, vertikalt",
    "T3.1_UND_UND_DOR": "Mellem undervisningsrum med dørforbindelse (samlet lydisolation for væg med dør, folde- og mobilvægge, glaspartier mv.)",
    "T3.1_UND_FAELLES_DOR": "Mellem undervisningsrum og fællesrum med dørforbindelse (samlet lydisolation for væg med dør, folde- og mobilvægge, glaspartier mv.)",
    "T3.1_FLEKSIBEL": "For fleksible rumadskillelser i åbne undervisningsområder 1)",
    "T3.1_SLOEJD": "Mellem undervisningsrum til sløjd og andre undervisningsrum eller fællesrum",
    "T3.1_SLOEJD_FAELLES_DOR": "Mellem undervisningsrum til sløjd og fællesrum med dørforbindelse (samlet lydisolation for væg med dør, folde- og mobilvægge, glaspartier mv.)",
    "T3.1_MUSIK": "Mellem undervisningsrum til sang og musik samt mellem undervisningsrum til sang og musik og andre undervisningsrum eller fællesrum",
    "T3.1_MUSIK_DOR": "Mellem undervisningsrum til sang og musik med dørforbindelse (samlet lydisolation for væg med dør)",
    "T3.1_MUSIK_FAELLES_DOR": "Mellem undervisningsrum til sang og musik og fællesrum med dørforbindelse (samlet lydisolation for væg med dør)",
    "T3.1_EKSTERN_STOEJ": "Mellem undervisningsrum og tilgrænsende rum i erhvervsenheder eller i andre undervisnings- eller daginstitutioner",
}
RULES_EN = {
    "T3.1_ALMINDELIG_HORISONTAL": "Between teaching rooms and between teaching rooms and common areas, horizontally",
    "T3.1_ALMINDELIG_VERTIKAL": "Between teaching rooms and between teaching rooms and common areas, vertically",
    "T3.1_UND_UND_DOR": "Between teaching rooms with a door connection (overall sound insulation of wall with door, folding and movable partitions, glazing, etc.)",
    "T3.1_UND_FAELLES_DOR": "Between teaching rooms and common areas with a door connection (overall sound insulation of wall with door, folding and movable partitions, glazing, etc.)",
    "T3.1_FLEKSIBEL": "For flexible partitions within open-plan teaching areas 1)",
    "T3.1_SLOEJD": "Between woodworking teaching rooms and other teaching rooms or common areas",
    "T3.1_SLOEJD_FAELLES_DOR": "Between woodworking teaching rooms and common areas with a door connection (overall sound insulation of wall with door, folding and movable partitions, glazing, etc.)",
    "T3.1_MUSIK": "Between music and singing teaching rooms and between music/singing teaching rooms and other teaching rooms or common areas",
    "T3.1_MUSIK_DOR": "Between music and singing teaching rooms with a door connection (overall sound insulation of wall with door)",
    "T3.1_MUSIK_FAELLES_DOR": "Between music and singing teaching rooms and common areas with a door connection (overall sound insulation of wall with door)",
    "T3.1_EKSTERN_STOEJ": "Between teaching rooms and adjoining rooms in commercial units or other educational institutions or daycare facilities",
}


def rule_description(rule_id, language="English"):
    """Return an appropriate table-row description, or an em dash if not covered."""
    return (RULES_DA if language == "Dansk" else RULES_EN).get(rule_id, "—")
