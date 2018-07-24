#!/usr/bin/env python
"""Collection of functions for the manipulation of time series."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import mando
from mando.rst_text_formatter import RSTHelpFormatter

from .. import tsutils


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def converttz(fromtz,
              totz,
              input_ts='-',
              columns=None,
              start_date=None,
              end_date=None,
              round_index=None,
              dropna='no',
              clean=False,
              skiprows=None):
    """Convert the time zone of the index.

    Parameters
    ----------
    fromtz : str
        The time zone of the original time-series.
    totz : str
        The time zone of the converted time-series.
    {input_ts}
    {start_date}
    {end_date}
    {columns}
    {dropna}
    {clean}
    {skiprows}
    {round_index}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts,
                                                  skiprows=skiprows),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna,
                              clean=clean)
    tsd = tsd.tz_localize(fromtz).tz_convert(totz)
    return tsutils.printiso(tsd,
                            showindex='always')
