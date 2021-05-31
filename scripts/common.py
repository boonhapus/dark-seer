from typing import List, Dict, Any
import pathlib
import csv


def to_csv(
    data: List[Dict[str, Any]],
    fp: pathlib.Path,
    *,
    mode: str='w',
    header: bool=True,
    sep: str='|'
):
    """
    Write data to CSV.

    Data must be in record format.. [{column -> value}, ..., {column -> value}]
    """
    with fp.open(mode=mode, encoding='utf-8', newline='') as c:
        writer = csv.DictWriter(c, data[0].keys(), delimiter=sep)

        if header:
            writer.writeheader()

        writer.writerows(data)


def chunks(iter_, *, n: int) -> iter:
    """
    Yield successive n-sized chunks from lst.
    """
    for i in range(0, len(iter_), n):
        yield iter_[i:i + n]
