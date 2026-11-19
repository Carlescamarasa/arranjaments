"""Dades de les proves d'harmonia: tots els exemples de les fitxes (una sola font de veritat).

Cada exemple diu quines comprovacions ha de FALLAR (`falla`). Si està buit, l'exemple és correcte
i ha de passar-les totes. Un exemple incorrecte només pot fallar la regla que il·lustra: així
cada error es veu aïllat. Les línies usen el Do central = Do3.
"""

GENERALS = ["escriptura", "paraleles", "directes", "sensible", "sensible_duplicada", "setena"]

EXEMPLES = [
    # ---------------- 1. Quintes i octaves paral·leles ----------------
    dict(tema="quintes-octaves-paraleles", fitxer="exemple-1-correcte", tonalitat="Do major",
         graus="I IV V I", falla=[],
         linia="S: Do4 Do4 Si3 Do4 | A: Mi3 Fa3 Re3 Mi3 | T: Sol2 La2 Sol2 Sol2 | B: Do2 Fa1 Sol1 Do2"),
    dict(tema="quintes-octaves-paraleles", fitxer="exemple-1-incorrecte", tonalitat="Do major",
         graus="I IV", falla=["paraleles"],
         linia="S: Do4 Fa4 | A: Sol3 La3 | T: Mi3 Do3 | B: Do2 Fa2"),
    dict(tema="quintes-octaves-paraleles", fitxer="exemple-2-correcte", tonalitat="Do major",
         graus="IV V", falla=[],
         linia="S: Fa4 Re4 | A: La3 Sol3 | T: Do3 Si2 | B: Fa2 Sol2"),
    dict(tema="quintes-octaves-paraleles", fitxer="exemple-2-incorrecte", tonalitat="Do major",
         graus="IV V", falla=["paraleles"],
         linia="S: Fa4 Re4 | A: La3 Si3 | T: Do3 Re3 | B: Fa2 Sol2"),
    dict(tema="quintes-octaves-paraleles", fitxer="exemple-3-correcte", tonalitat="Do major",
         graus="I VII6 I6", falla=[],
         linia="S: Mi4 Re4 Sol3 | A: Sol3 Fa3 Mi3 | T: Do3 Si2 Do3 | B: Do2 Re2 Mi2"),
    dict(tema="quintes-octaves-paraleles", fitxer="exemple-4-incorrecte", tonalitat="Do major",
         graus="I IV", falla=["directes"],
         linia="S: Mi4 Do4 | A: Sol3 Fa3 | T: Do3 La2 | B: Do2 Fa1"),

    # ---------------- 2. Sensible i setena del V7 ----------------
    dict(tema="sensible-i-setena-v7", fitxer="exemple-1-correcte", tonalitat="Do major",
         graus="V I", falla=[],
         linia="S: Si3 Do4 | A: Re3 Mi3 | T: Sol2 Sol2 | B: Sol1 Do2"),
    dict(tema="sensible-i-setena-v7", fitxer="exemple-1-incorrecte", tonalitat="Do major",
         graus="V I", falla=["sensible"],
         linia="S: Si3 Sol3 | A: Re3 Do3 | T: Sol2 Mi2 | B: Sol1 Do2"),
    dict(tema="sensible-i-setena-v7", fitxer="exemple-2-correcte", tonalitat="Do major",
         graus="V7 I", falla=[],
         linia="S: Re3 Do3 | A: Si2 Sol2 | T: Fa2 Mi2 | B: Sol1 Do2"),
    dict(tema="sensible-i-setena-v7", fitxer="exemple-3-correcte", tonalitat="Do major",
         graus="V7 I", falla=[],
         linia="S: Fa3 Mi3 | A: Si2 Do3 | T: Sol2 Sol2 | B: Sol1 Do2"),
    dict(tema="sensible-i-setena-v7", fitxer="exemple-3-incorrecte", tonalitat="Do major",
         graus="V7 I", falla=["setena"],
         linia="S: Re3 Mi3 | A: Si2 Do3 | T: Fa2 Sol2 | B: Sol1 Do2"),
    dict(tema="sensible-i-setena-v7", fitxer="exemple-4-correcte", tonalitat="Do major",
         graus="V4/3 I6", falla=[],
         linia="S: Sol3 Sol3 | A: Si2 Do3 | T: Fa2 Sol2 | B: Re2 Mi2"),
    dict(tema="sensible-i-setena-v7", fitxer="exemple-5-correcte", tonalitat="Do major",
         graus="V7 VI", falla=[],
         linia="S: Fa3 Mi3 | A: Si2 Do3 | T: Re2 Do2 | B: Sol1 La1"),
    dict(tema="sensible-i-setena-v7", fitxer="exemple-5-incorrecte", tonalitat="Do major",
         graus="V7 VI", falla=["sensible"],
         linia="S: Si3 La3 | A: Re3 Do3 | T: Fa2 Mi2 | B: Sol1 La1"),

    # ---------------- 3. Sisena augmentada ----------------
    dict(tema="sisena-augmentada", fitxer="exemple-1-correcte", tonalitat="la menor",
         graus="6a aug. italiana, V", falla=[], tipus="italiana",
         linia="S: La3 Sol#3 | A: Re#3 Mi3 | T: La2 Si2 | B: Fa1 Mi1"),
    dict(tema="sisena-augmentada", fitxer="exemple-2-correcte", tonalitat="la menor",
         graus="6a aug. francesa, V", falla=[], tipus="francesa",
         linia="S: La3 Sol#3 | A: Re#3 Mi3 | T: Si2 Si2 | B: Fa1 Mi1"),
    dict(tema="sisena-augmentada", fitxer="exemple-3-correcte", tonalitat="la menor",
         graus="6a aug. alemanya, I6/4, V", falla=[], tipus="alemanya",
         linia="S: Re#3 Mi3 Mi3 | A: Do3 Do3 Si2 | T: La2 La2 Sol#2 | B: Fa1 Mi1 Mi1"),
    dict(tema="sisena-augmentada", fitxer="exemple-4-correcte", tonalitat="la menor",
         graus="6a aug. alemanya, V", falla=[], tipus="alemanya",
         linia="S: Re#3 Mi3 | A: Do3 Si2 | T: La2 Sol#2 | B: Fa1 Mi1"),
    dict(tema="sisena-augmentada", fitxer="exemple-4-incorrecte", tonalitat="la menor",
         graus="6a aug. alemanya, V", falla=["paraleles"], tipus="alemanya",
         linia="S: Do4 Si3 | A: Re#3 Mi3 | T: La2 Sol#2 | B: Fa1 Mi1"),
    dict(tema="sisena-augmentada", fitxer="exemple-5-incorrecte", tonalitat="la menor",
         graus="6a aug. italiana, V", falla=["sisena_augmentada"], tipus="italiana",
         linia="S: La3 Si3 | A: Re#3 Si2 | T: La2 Sol#2 | B: Fa1 Mi1"),
]


def comprovacions(ex) -> list[str]:
    extra = ["sisena_augmentada"] if ex["tema"] == "sisena-augmentada" else []
    return GENERALS + extra


# Proves internes de les comprovacions (no surten a cap fitxa). Serveixen per a saber que
# les excepcions no deixen passar el que no toca.
PROVES = [
    dict(nom="5a dism. → 5a justa amb el 2n acord en estat fonamental", tonalitat="Do major",
         falla=["paraleles", "setena"],
         linia="S: Re4 Mi4 | A: Fa3 Sol3 | T: Si2 Do3 | B: Re2 Do2"),
    dict(nom="5a dism. → 5a justa amb el 2n acord en 1a inversió (Zamacois II, §78)", tonalitat="Do major",
         falla=[],
         linia="S: Re4 Do4 | A: Fa3 Sol3 | T: Si2 Do3 | B: Re2 Mi2"),
    dict(nom="les mateixes quintes de l'alemanya, però sense 6a augmentada", tonalitat="la menor",
         falla=["paraleles"],
         linia="S: Re3 Mi3 | A: Do3 Si2 | T: La2 Sol#2 | B: Fa1 Mi1"),
    dict(nom="sensible en veu interior que salta a la 3a de la tònica (baixant una 5a)", tonalitat="Do major",
         falla=["sensible"],
         linia="S: Sol3 Sol3 | A: Re3 Do3 | T: Si2 Mi2 | B: Sol1 Do2"),
    dict(nom="octava directa entre veus interiors saltant les dues", tonalitat="Do major",
         falla=["directes"],
         linia="S: Do4 Mi4 | A: Mi3 Do4 | T: Sol2 Do3 | B: Do2 La1"),
]
