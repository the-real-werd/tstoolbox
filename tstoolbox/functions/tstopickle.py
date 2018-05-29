#!/usr/bin/env python
"""Collection of functions for the manipulation of time series."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import warnings

import mando
from mando.rst_text_formatter import RSTHelpFormatter

from .. import tsutils

warnings.filterwarnings('ignore')


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def tstopickle(filename,
               input_ts='-',
               columns=None,
               start_date=None,
               end_date=None,
               round_index=None,
               dropna='no'):
    """Pickle the data into a Python pickled file.

    Can be brought back into Python with 'pickle.load' or 'numpy.load'.
    See also 'tstoolbox read'.

    Parameters
    ----------
    filename : str
         The filename to store the pickled data.
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {round_index}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)
    tsd.to_pickle(filename)