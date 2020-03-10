from operator import mul
from typing import Iterable
import functools as ft


def calc_magic_resistance(
    strength: int=0,
    *,
    bonuses: Iterable=(0,),
    reductions: Iterable=(0,)
) -> float:
    """
    Calculate a Hero's Magic Resistence.

    Formula:

      MR = 1 - (  (1 * natural resistance)
                * (1 - strength * 0.08%)
                * (1 * rbonus0) * (1 * rbonus1) ... (1 * rbonusN)
                * (1 + rreduc0) * (1 + rreduc1) ... (1 + rreducN)
               )

    All sources of magic resistance stack multiplicatively. This means a
    unit's magic resistance value changes less the higher its magic
    resistance is, and more the lower it is.

    Further Reading:
      https://dota2.gamepedia.com/Magic_resistance
    """
    natural    = 1 - 0.25
    from_str   = 1 - strength * 0.0008
    bonuses    = ft.reduce(mul, [(1 - b) for b in bonuses])
    reductions = ft.reduce(mul, [(1 + r) for r in reductions])
    return (1 - (natural * from_str * bonuses * reductions)) * 100
