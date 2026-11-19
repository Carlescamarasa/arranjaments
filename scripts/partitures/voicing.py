"""Disposició de les notes d'un acord per a l'acompanyament: dos mòduls amb la mateixa interfície.

Clàssic (Zamacois, ids VE, DU, EN): acords en posició propera, sense creuaments, amb les notes comunes mantingudes
(per proximitat), la fonamental duplicada pel baix i la 7a que baixa per grau.

Jazz (Levine VC01 a VC08, Herrera VOI-05): esquelet de 3a i 7a (la 5a s'omet), en les dues posicions possibles (7a
a dalt o 3a a dalt) i triant la que es mou menys; la 7a d'un acord baixa mig to i fa de 3a del següent (VC02).

Les funcions treballen amb números MIDI en so real i no depenen de l'arranjador (només necessiten un objecte amb
`pcs` i `te_septima`, com `Acord`).
"""
from __future__ import annotations

# Estils que usen cada mòdul. Els altres (pop, rock) tenen el seu propi cas a `triar_pcs`.
ESTILS_JAZZ = ("swing", "ragtime")
ESTILS_CLASSICS = ("classic", "coral", "marxa", "vals")

# Paràmetres ajustables (els marcats [inferència] no surten literalment del llibre).
SALT_MAX_CLASSIC = 9          # obertura màxima d'un acord en posició propera, en semitons (tres notes: fins a 6/4)
SALT_MAX_JAZZ = 9             # esquelet de dues o tres notes
LIMIT_GREU_FANG = 48          # per sota de Do3 (MIDI 48) no es posen segones ni sèptimes juntes (Levine VC06, Z5-14)
DISTANCIA_MINIMA_BAIX = 3     # [inferència] entre el baix i la nota més greu de l'acord, almenys una tercera
MIG_REGISTRE_JAZZ = 66        # [inferència] centre de la mà dreta per a l'esquelet quan no hi ha acord anterior
PENALITZA_XOC_MELODIA = 15       # semitò a prop de la melodia
PENALITZA_DOBLA_MELODIA = 40     # la mateixa nota que la melodia
PENALITZA_SOBRE_MELODIA = 6
PENALITZA_FANG = 30
PENALITZA_SETENA_SENSE_BAIXAR = 8
PENALITZA_BAIX_PROPER = 10


def nom_grup(estil: str) -> str:
    """«jazz» per a swing i ragtime, «classic» per a la resta."""
    return "jazz" if estil in ESTILS_JAZZ else "classic"


# --------------------------------------------------------------------------- quines classes d'altura es toquen

def triar_pcs(acord, n: int, estil: str, nivell: str, final_dominant: bool = False) -> list[int]:
    """Classes d'altura que cal tocar, de baix a dalt, segons el nombre de notes `n` que admet l'instrument.

    Elemental: tríades i, en estils no jazz, sense 7a (Herrera NIV-01). Swing i ragtime: 3a i 7a sempre que hi ha 7a
    (VC01), sense la 5a (VOI-05). Pop: la 7a només en avançat. Rock: quinta buida, arrel i 5a (Herrera REH-04).
    `final_dominant`: acord final d'un V-I, amb la fonamental triplicada i sense 5a (Zamacois DU08).
    """
    pcs = list(acord.pcs)
    arrel = pcs[0]
    tercera = pcs[1] if len(pcs) > 1 else arrel
    quinta = pcs[2] if len(pcs) > 2 else arrel
    setena = pcs[3] if len(pcs) > 3 else None
    jazz = estil in ESTILS_JAZZ
    if estil == "rock":
        return [arrel] if n <= 1 else [arrel, quinta] if n == 2 else [arrel, quinta, arrel]
    if setena is not None:
        if jazz:
            pass
        elif estil == "pop":
            setena = setena if nivell == "avançat" else None
        else:
            setena = setena if nivell != "elemental" else None
    if n <= 1:
        return [tercera]
    if jazz:
        if setena is not None:
            return [tercera, setena]
        return [tercera, quinta] if n == 2 else [tercera, quinta, arrel]
    if n == 2:
        return [tercera, setena] if setena is not None else [tercera, quinta]
    if final_dominant and setena is None:
        return [arrel, tercera, arrel]
    if setena is not None:
        return [tercera, setena, arrel]
    return [tercera, quinta, arrel]


# --------------------------------------------------------------------------- col·locació en el registre

def candidats(pcs: list[int], lo: int, hi: int, salt_max: int = SALT_MAX_CLASSIC) -> list[list[int]]:
    """Totes les disposicions properes (cada classe de `pcs` una vegada, o dues si hi és repetida) amb totes les
    notes dins de [lo, hi] i una obertura total de `salt_max` semitons com a molt."""
    res = []
    vist = set()
    for base in range(lo, hi + 1):
        if base % 12 not in pcs:
            continue
        resta = list(pcs)
        resta.remove(base % 12)
        resta.sort(key=lambda pc: (pc - base) % 12 or 12)
        nots = [base]
        for pc in resta:
            x = nots[-1] + 1
            while x % 12 != pc:
                x += 1
            nots.append(x)
        if nots[-1] > hi or nots[-1] - nots[0] > salt_max:
            continue
        if tuple(nots) not in vist:
            vist.add(tuple(nots))
            res.append(nots)
    return res


def _fang(nots: list[int]) -> bool:
    """Segones o sèptimes (i novenes) entre notes veïnes per sota de Do3: so fangós (VC06, Z5-14)."""
    for a, b in zip(nots, nots[1:]):
        if a < LIMIT_GREU_FANG and (b - a) % 12 in (1, 2, 10, 11):
            return True
    return False


def _cost(nots: list[int], prev: list[int] | None, melodia: int | None, baix: int | None,
          prev_acord, acord, prev_pcs_setena: int | None) -> float:
    cost = 0.0
    if prev is None:
        cost += abs(sum(nots) / len(nots) - MIG_REGISTRE_JAZZ) * 0.01
    else:
        cost += sum(abs(a - b) for a, b in zip(nots, prev)) + abs(len(nots) - len(prev)) * 3
    if _fang(nots):
        cost += PENALITZA_FANG
    if melodia is not None:
        for x in nots:
            if x == melodia:
                cost += PENALITZA_DOBLA_MELODIA
            elif abs(x - melodia) <= 1:
                cost += PENALITZA_XOC_MELODIA
            elif x > melodia:
                cost += PENALITZA_SOBRE_MELODIA
    if baix is not None and min(nots) - baix < DISTANCIA_MINIMA_BAIX:
        cost += PENALITZA_BAIX_PROPER
    # la 7a de l'acord anterior ha de baixar per grau (VC02, Zamacois Z4-05)
    if prev is not None and prev_pcs_setena is not None and prev_acord is not None and prev_acord is not acord:
        for x in prev:
            if x % 12 == prev_pcs_setena:
                if not any(0 < x - y <= 2 for y in nots):
                    cost += PENALITZA_SETENA_SENSE_BAIXAR
    return cost


def disposicio(acord, n: int, lo: int, hi: int, prev: list[int] | None, estil: str = "classic",
               nivell: str = "mitja", melodia: int | None = None, baix: int | None = None,
               prev_acord=None, final_dominant: bool = False) -> list[int]:
    """Notes (MIDI, de baix a dalt) de l'acord per a la mà dreta o les baquetes, entre `lo` i `hi`.

    `prev`: disposició de l'acord anterior (per mantindre notes comunes i moure's poc). `melodia`: nota sonant de la
    melodia en aquest instant (l'acompanyament no la dobla ni hi xoca). `baix`: nota del baix en aquest instant.
    """
    pcs = triar_pcs(acord, n, estil, nivell, final_dominant)
    jazz = estil in ESTILS_JAZZ
    salt = SALT_MAX_JAZZ if jazz else (12 if (final_dominant or estil == "rock") else SALT_MAX_CLASSIC)
    opcions = candidats(pcs, lo, hi, salt)
    while not opcions and len(pcs) > 1:
        # no cap dins de l'abast: es treu el doblament i després l'última nota, fins que càpiga
        unics = [pc for i, pc in enumerate(pcs) if pc not in pcs[:i]]
        pcs = unics if len(unics) < len(pcs) else pcs[:-1]
        opcions = candidats(pcs, lo, hi, salt)
    if not opcions:
        return [lo + ((pcs[0] - lo) % 12)]
    setena_prev = None
    if prev_acord is not None and getattr(prev_acord, "te_septima", False):
        setena_prev = prev_acord.pcs[3]
    return min(opcions, key=lambda v: (_cost(v, prev, melodia, baix, prev_acord, acord, setena_prev), v))


def compacte(acord, lo: int, hi: int, n: int = 3, prev: list[int] | None = None) -> list[int]:
    """Interfície d'acord compacte (Zamacois Z4-01): l'acord complet en posició propera dins del registre."""
    return disposicio(acord, n, lo, hi, prev, "classic", "mitja")
