"""Helper functions."""

from io import StringIO

import pandas as pd


def df_from_raw_csv(raw_data: str) -> pd.DataFrame:
    """Create a pandas dataframe from a raw csv string."""
    iodata = StringIO(raw_data)
    df = pd.read_csv(iodata)
    df["published_at"] = pd.to_datetime(df["published_at"], format="%Y-%m-%d")
    return df
