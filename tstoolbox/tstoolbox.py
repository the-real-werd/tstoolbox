#!/usr/bin/env python
"""Collection of functions for the manipulation of time series."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os.path
import sys
import warnings
from builtins import map
from builtins import range
from builtins import str

import mando
from mando.rst_text_formatter import RSTHelpFormatter

import pandas as pd

from . import fill_functions
from . import tsutils

from .functions.plot import plot
from .functions.createts import createts
from .functions.filter import filter
from .functions.read import read
from .functions.date_slice import date_slice
from .functions.describe import describe
from .functions.peak_detection import peak_detection
from .functions.convert import convert
from .functions.equation import equation
from .functions.pick import pick
from .functions.stdtozrxp import stdtozrxp

warnings.filterwarnings('ignore')
fill = fill_functions.fill

_offset_aliases = {
    86400000000000: 'D',
    604800000000000: 'W',
    2419200000000000: 'M',
    2505600000000000: 'M',
    2592000000000000: 'M',
    2678400000000000: 'M',
    31536000000000000: 'A',
    31622400000000000: 'A',
    3600000000000: 'H',
    60000000000: 'M',
    1000000000: 'T',
    1000000: 'L',
    1000: 'U',
}


@mando.command()
def about():
    """Display version number and system information."""
    tsutils.about(__name__)


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


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def accumulate(input_ts='-',
               columns=None,
               start_date=None,
               end_date=None,
               dropna='no',
               statistic='sum',
               round_index=None,
               print_input=False):
    """Calculate accumulating statistics.

    Parameters
    ----------
    statistic : str
        [optional, default is 'sum']
        'sum', 'max', 'min', 'prod'
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {print_input}
    {round_index}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)
    try:
        ntsd = eval('tsd.cum{0}()'.format(statistic))
    except AttributeError:
        raise ValueError("""
*
*   Statistic {0} is not implemented.
*
""".format(statistic))
    return tsutils.print_input(print_input, tsd, ntsd, '_' + statistic)


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def ewm_window(input_ts='-',
               columns=None,
               start_date=None,
               end_date=None,
               dropna='no',
               statistic='',
               alpha_com=None,
               alpha_span=None,
               alpha_halflife=None,
               alpha=None,
               min_periods=0,
               adjust=True,
               ignore_na=False,
               print_input=False,
               ):
    """Provides exponential weighted functions.

    Exactly one of center of mass, span, half-life, and alpha must be provided.
    Allowed values and relationship between the parameters are specified in the
    parameter descriptions above; see the link at the end of this section for
    a detailed explanation.

    When adjust is True (default), weighted averages are calculated using
    weights (1-alpha)**(n-1), (1-alpha)**(n-2), . . . , 1-alpha, 1.

    When adjust is False, weighted averages are calculated recursively as:
        weighted_average[0] = arg[0]; weighted_average[i]
        = (1-alpha)*weighted_average[i-1] + alpha*arg[i].

    When ignore_na is False (default), weights are based on absolute positions.
    For example, the weights of x and y used in calculating the final weighted
    average of [x, None, y] are (1-alpha)**2 and 1 (if adjust is True), and
    (1-alpha)**2 and alpha (if adjust is False).

    When ignore_na is True (reproducing pre-0.15.0 behavior), weights are based
    on relative positions. For example, the weights of x and y used in
    calculating the final weighted average of [x, None, y] are 1-alpha and
    1 (if adjust is True), and 1-alpha and alpha (if adjust is False).

    More details can be found at
    http://pandas.pydata.org/pandas-docs/stable/computation.html#exponentially-weighted-windows

    Parameters
    ----------
    statistic : str
        Statistic applied to each window.

        +------+--------------------+
        | corr | correlation        |
        +------+--------------------+
        | cov  | covariance         |
        +------+--------------------+
        | mean | mean               |
        +------+--------------------+
        | std  | standard deviation |
        +------+--------------------+
        | var  | variance           |
        +------+--------------------+

    alpha_com : float, optional
        Specify decay in terms of center of mass, alpha=1/(1+com), for com>=0

    alpha_span : float, optional
        Specify decay in terms of span, alpha=2/(span+1), for span1

    alpha_halflife : float, optional
        Specify decay in terms of half-life, alpha=1-exp(log(0.5)/halflife),
        for halflife>0

    alpha : float, optional
        Specify smoothing factor alpha directly, 0<alpha<=1

    min_periods : int, default 0
        Minimum number of observations in window required to have a value
        (otherwise result is NA).

    adjust : boolean, default True
        Divide by decaying adjustment factor in beginning periods to account
        for imbalance in relative weightings (viewing EWMA as a moving average)

    ignore_na : boolean, default False
        Ignore missing values when calculating weights.

    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {print_input}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              dropna=dropna)

    ntsd = tsd.ewm(alpha_com=alpha_com,
                   alpha_span=alpha_span,
                   alpha_halflife=alpha_halflife,
                   alpha=alpha,
                   min_periods=min_periods,
                   adjust=adjust,
                   ignore_na=ignore_na,
                   )

    if statistic:
        ntsd = eval('ntsd.{0}()'.format(statistic))

    return tsutils.print_input(print_input,
                               tsd,
                               ntsd,
                               '_ewm_' + statistic)


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def expanding_window(input_ts='-',
                     columns=None,
                     start_date=None,
                     end_date=None,
                     dropna='no',
                     statistic='',
                     min_periods=1,
                     center=False,
                     print_input=False,
                     ):
    """Calculate an expanding window statistic.

    Parameters
    ----------
    statistic : str

        +-----------+----------------------+
        | statistic | Meaning              |
        +===========+======================+
        | corr      | correlation          |
        +-----------+----------------------+
        | count     | count of real values |
        +-----------+----------------------+
        | cov       | covariance           |
        +-----------+----------------------+
        | kurt      | kurtosis             |
        +-----------+----------------------+
        | max       | maximum              |
        +-----------+----------------------+
        | mean      | mean                 |
        +-----------+----------------------+
        | median    | median               |
        +-----------+----------------------+
        | min       | minimum              |
        +-----------+----------------------+
        | skew      | skew                 |
        +-----------+----------------------+
        | std       | standard deviation   |
        +-----------+----------------------+
        | sum       | sum                  |
        +-----------+----------------------+
        | var       | variance             |
        +-----------+----------------------+

    min_periods : int, default 1
        Minimum number of observations in window required to have a value

    center : boolean, default False
        Set the labels at the center of the window.

    {print_input}
    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              dropna=dropna)

    ntsd = tsd.expanding(min_periods=1,
                         center=False)

    if statistic:
        ntsd = eval('ntsd.{0}()'.format(statistic))

    return tsutils.print_input(print_input,
                               tsd,
                               ntsd,
                               '_expanding_' + statistic)


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def rolling_window(window=2,
                   input_ts='-',
                   columns=None,
                   start_date=None,
                   end_date=None,
                   dropna='no',
                   span=None,
                   statistic='',
                   min_periods=None,
                   center=False,
                   win_type=None,
                   on=None,
                   closed=None,
                   print_input=False,
                   freq=None):
    """Calculate a rolling window statistic.

    Parameters
    ----------
    window : int, or offset
        [optional, default = 2]

        Size of the moving window. This is the number of observations used for
        calculating the statistic. Each window will be a fixed size.

        If its an offset then this will be the time period of each window. Each
        window will be a variable sized based on the observations included in
        the time-period. This is only valid for datetimelike indexes.

    min_periods : int, default None

        Minimum number of observations in window required to have a value
        (otherwise result is NA). For a window that is specified by an offset,
        this will default to 1.

    center : boolean, default False

        Set the labels at the center of the window.

    win_type : string, default None

        Provide a window type. If None, all points are evenly weighted. See the
        notes below for further information.

    on : string, optional

        For a DataFrame, column on which to calculate the rolling window,
        rather than the index

    closed : string, default None

        Make the interval closed on the 'right', 'left', 'both' or 'neither'
        endpoints. For offset-based windows, it defaults to 'right'. For fixed
        windows, defaults to 'both'. Remaining cases not implemented for fixed
        windows.

    span : int
        [optional, default = 2]

        DEPRECATED: Changed to 'window' to be consistent with pandas.

    statistic : str
        [optional, default is '']

        +----------+--------------------+
        | corr     | correlation        |
        +----------+--------------------+
        | count    | count of numbers   |
        +----------+--------------------+
        | cov      | covariance         |
        +----------+--------------------+
        | kurt     | kurtosis           |
        +----------+--------------------+
        | max      | maximum            |
        +----------+--------------------+
        | mean     | mean               |
        +----------+--------------------+
        | median   | median             |
        +----------+--------------------+
        | min      | minimum            |
        +----------+--------------------+
        | quantile | quantile           |
        +----------+--------------------+
        | skew     | skew               |
        +----------+--------------------+
        | std      | standard deviation |
        +----------+--------------------+
        | sum      | sum                |
        +----------+--------------------+
        | var      | variance           |
        +----------+--------------------+

    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {print_input}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              dropna=dropna)

    if span is not None:
        window = span

    window_list = [
        'boxcar',
        'triang',
        'blackman',
        'hamming',
        'bartlett',
        'parzen',
        'bohman',
        'blackmanharris',
        'nuttall',
        'barthann',
        'kaiser',
        'gaussian',
        'general_gaussian',
        'slepian',
    ]

    ntsd = tsd.rolling(window,
                       min_periods=min_periods,
                       center=center,
                       win_type=win_type,
                       on=on,
                       closed=closed)

    if statistic:
        ntsd = eval('ntsd.{0}()'.format(statistic))

    return tsutils.print_input(print_input,
                               tsd,
                               ntsd,
                               '_rolling_{0}_{1}'.format(window, statistic))


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def aggregate(input_ts='-',
              columns=None,
              start_date=None,
              end_date=None,
              dropna='no',
              statistic='mean',
              agg_interval='D',
              ninterval=1,
              round_index=None,
              print_input=False):
    """Take a time series and aggregate to specified frequency.

    Parameters
    ----------
    statistic : str
        [optional, defaults to 'mean']

        'mean', 'sum', 'std', 'max', 'min', 'median', 'first', or 'last'
        to calculate the aggregation.  Can also be a comma separated list of
        statistic methods.
    agg_interval : str
        [optional, defaults to 'D']
        The interval to aggregate the time series.  Any of the PANDAS
        offset codes.

        {pandas_offset_codes}

        There are some deprecated aggregation interval names in
        tstoolbox, DON'T USE!

        +---------------+-----+
        | Instead of... | Use |
        +===============+=====+
        | hourly        | H   |
        +---------------+-----+
        | daily         | D   |
        +---------------+-----+
        | monthly       | M   |
        +---------------+-----+
        | yearly        | A   |
        +---------------+-----+

    ninterval : int
        [optional, defaults to 1]

        The number of agg_interval to use for the aggregation.
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {round_index}
    {print_input}

    """
    statslist = ['mean',
                 'sum',
                 'std',
                 'max',
                 'min',
                 'median',
                 'first',
                 'last']
    assert statistic in statslist, """
***
*** The statistic option must be one of:
*** {1}
*** to calculate the aggregation.
*** You gave {0}.
***
""".format(statistic, statslist)

    aggd = {'hourly': 'H',
            'daily': 'D',
            'monthly': 'M',
            'yearly': 'A'}
    agg_interval = aggd.get(agg_interval, agg_interval)

    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)
    methods = statistic.split(',')
    newts = pd.DataFrame()
    for method in methods:
        if method == 'mean':
            tmptsd = tsd.resample('{0:d}{1}'.format(ninterval,
                                                    agg_interval)).mean()
        elif method == 'sum':
            tmptsd = tsd.resample('{0:d}{1}'.format(ninterval,
                                                    agg_interval)).sum()
        elif method == 'std':
            tmptsd = tsd.resample('{0:d}{1}'.format(ninterval,
                                                    agg_interval)).std()
        elif method == 'max':
            tmptsd = tsd.resample('{0:d}{1}'.format(ninterval,
                                                    agg_interval)).max()
        elif method == 'min':
            tmptsd = tsd.resample('{0:d}{1}'.format(ninterval,
                                                    agg_interval)).min()
        elif method == 'median':
            tmptsd = tsd.resample('{0:d}{1}'.format(ninterval,
                                                    agg_interval)).median()
        elif method == 'first':
            tmptsd = tsd.resample('{0:d}{1}'.format(ninterval,
                                                    agg_interval)).first()
        elif method == 'last':
            tmptsd = tsd.resample('{0:d}{1}'.format(ninterval,
                                                    agg_interval)).last()
        tmptsd.rename(columns=lambda x: x + '_' + method, inplace=True)
        newts = newts.join(tmptsd, how='outer')
    return tsutils.print_input(print_input, tsd, newts, '')


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def replace(from_values,
            to_values,
            round_index=None,
            input_ts='-',
            columns=None,
            start_date=None,
            end_date=None,
            dropna='no',
            print_input=False):
    """Return a time-series replacing values with others.

    Parameters
    ----------
    from_values
        All values in this comma separated list are replaced
        with the corresponding value in to_values.  Use the
        string 'None' to represent a missing value.  If
        using 'None' as a from_value it might be easier to
        use the "fill" subcommand instead.
    to_values
        All values in this comma separater list are the
        replacement values corresponding one-to-one to the
        items in from_values.  Use the string 'None' to
        represent a missing value.
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {round_index}
    {print_input}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)

    nfrom_values = []
    for fv in from_values.split(','):
        if fv == 'None':
            nfrom_values.append(None)
            continue
        try:
            nfrom_values.append(int(fv))
        except ValueError:
            nfrom_values.append(float(fv))

    nto_values = []
    for tv in to_values.split(','):
        if tv == 'None':
            nto_values.append(None)
            continue
        try:
            nto_values.append(int(tv))
        except ValueError:
            nto_values.append(float(tv))

    ntsd = tsd.replace(nfrom_values, nto_values)
    if dropna in ['any', 'all']:
        ntsd = ntsd.dropna(axis='index', how=dropna)

    return tsutils.print_input(
        print_input, tsd, ntsd, '_replace')


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def clip(input_ts='-',
         start_date=None,
         end_date=None,
         columns=None,
         dropna='no',
         a_min=None,
         a_max=None,
         round_index=None,
         print_input=False):
    """Return a time-series with values limited to [a_min, a_max].

    Parameters
    ---------
    a_min
        [optional, defaults to None]

        All values lower than this will be set to this value.
        Default is None.
    a_max
        [optional, defaults to None]

        All values higher than this will be set to this value.
        Default is None.
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {print_input}
    {round_index}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)
    for col in tsd.columns:
        if a_min is None:
            try:
                n_min = pd.np.finfo(tsd[col].dtype).min
            except ValueError:
                n_min = pd.np.iinfo(tsd[col].dtype).min
        else:
            n_min = float(a_min)

        if a_max is None:
            try:
                n_max = pd.np.finfo(tsd[col].dtype).max
            except ValueError:
                n_max = pd.np.iinfo(tsd[col].dtype).max
        else:
            n_max = float(a_max)

    return tsutils.print_input(
        print_input, tsd, tsd.clip(n_min, n_max), '_clip')


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def add_trend(start_offset,
              end_offset,
              input_ts='-',
              columns=None,
              start_date=None,
              end_date=None,
              dropna='no',
              round_index=None,
              print_input=False):
    """Add a trend.

    Parameters
    ----------
    start_offset : float
        The starting value for the applied trend.
    end_offset : float
        The ending value for the applied trend.
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {print_input}
    {round_index}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)
    # Need it to be float since will be using pd.np.nan
    ntsd = tsd.copy().astype('float64')

    ntsd.ix[:, :] = pd.np.nan
    ntsd.ix[0, :] = float(start_offset)
    ntsd.ix[-1, :] = float(end_offset)
    ntsd = ntsd.interpolate(method='values')

    ntsd = ntsd + tsd

    ntsd = tsutils.memory_optimize(ntsd)
    return tsutils.print_input(print_input,
                               tsd,
                               ntsd,
                               '_trend')


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def remove_trend(input_ts='-',
                 columns=None,
                 start_date=None,
                 end_date=None,
                 dropna='no',
                 round_index=None,
                 print_input=False):
    """Remove a 'trend'.

    Parameters
    ----------
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {round_index}
    {print_input}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)
    ntsd = tsd.copy()
    for col in tsd.columns:
        index = tsd.index.astype('l')
        index = index - index[0]
        lin = pd.np.polyfit(index, tsd[col], 1)
        ntsd[col] = lin[0] * index + lin[1]
        ntsd[col] = tsd[col] - ntsd[col]
    return tsutils.print_input(
        print_input, tsd, ntsd, '_rem_trend')


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def calculate_fdc(input_ts='-',
                  columns=None,
                  start_date=None,
                  end_date=None,
                  percent_point_function=None,
                  plotting_position='weibull',
                  ascending=True):
    """Return the frequency distribution curve.

    DOES NOT return a time-series.

    Parameters
    ----------
    percent_point_function : str
        [optional, default is None]

        The distribution used to shift the plotting position values.
        Choose from 'norm', 'lognorm', 'weibull', and None.
    plotting_position : str
        [optional, default is 'weibull']

        {plotting_position_table}

    ascending : bool
        Sort order defaults to True.
    {input_ts}
    {columns}
    {start_date}
    {end_date}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns)

    ppf = tsutils._set_ppf(percent_point_function)
    newts = pd.DataFrame()
    for col in tsd:
        tmptsd = tsd[col].dropna()
        xdat = ppf(tsutils._set_plotting_position(tmptsd.count(),
                                                  plotting_position)) * 100
        tmptsd.sort_values(ascending=ascending, inplace=True)
        tmptsd.index = xdat
        newts = newts.join(tmptsd, how='outer')
    newts.index.name = 'Plotting_position'
    newts = newts.groupby(newts.index).first()
    return tsutils.printiso(newts,
                            showindex='always')


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def stack(input_ts='-',
          columns=None,
          start_date=None,
          end_date=None,
          round_index=None,
          dropna='no'):
    """Return the stack of the input table.

    The stack command takes the standard table and
    converts to a three column table.

    From::

      Datetime,TS1,TS2,TS3
      2000-01-01 00:00:00,1.2,1018.2,0.0032
      2000-01-02 00:00:00,1.8,1453.1,0.0002
      2000-01-03 00:00:00,1.9,1683.1,-0.0004

    To::

      Datetime,Columns,Values
      2000-01-01,TS1,1.2
      2000-01-02,TS1,1.8
      2000-01-03,TS1,1.9
      2000-01-01,TS2,1018.2
      2000-01-02,TS2,1453.1
      2000-01-03,TS2,1683.1
      2000-01-01,TS3,0.0032
      2000-01-02,TS3,0.0002
      2000-01-03,TS3,-0.0004

    Parameters
    ----------
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

    newtsd = pd.DataFrame(tsd.stack()).reset_index(1)
    newtsd.columns = ['Columns', 'Values']
    newtsd = newtsd.groupby('Columns').apply(
        lambda d: d.sort_values('Columns')).reset_index('Columns', drop=True)
    return tsutils.printiso(newtsd)


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def unstack(column_names,
            input_ts='-',
            columns=None,
            start_date=None,
            end_date=None,
            round_index=None,
            dropna='no'):
    """Return the unstack of the input table.

    The unstack command takes the stacked table and converts to a
    standard tstoolbox table.

    From::

      Datetime,Columns,Values
      2000-01-01,TS1,1.2
      2000-01-02,TS1,1.8
      2000-01-03,TS1,1.9
      2000-01-01,TS2,1018.2
      2000-01-02,TS2,1453.1
      2000-01-03,TS2,1683.1
      2000-01-01,TS3,0.0032
      2000-01-02,TS3,0.0002
      2000-01-03,TS3,-0.0004

    To::

      Datetime,TS1,TS2,TS3
      2000-01-01,1.2,1018.2,0.0032
      2000-01-02,1.8,1453.1,0.0002
      2000-01-03,1.9,1683.1,-0.0004

    Parameters
    ----------
    column_names
        The column in the table that holds the column names
        of the unstacked data.
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

    try:
        newtsd = tsd.pivot_table(index=tsd.index,
                                 values=tsd.columns.drop(column_names),
                                 columns=column_names,
                                 aggfunc='first')
    except ValueError:
        raise ValueError("""
*
*   Duplicate index (time stamp and '{0}') where found.
*   Found these duplicate indices:
*   {1}
*
""".format(column_names,
           tsd.index.get_duplicates()))

    newtsd.index.name = 'Datetime'

    newtsd.columns = ['_'.join(tuple(map(str, col))).rstrip('_')
                      for col in newtsd.columns.values]

    # Remove weird characters from column names
    newtsd.rename(columns=lambda x: ''.join(
        [i for i in str(x) if i not in '\'" ']))
    return tsutils.printiso(newtsd)


def _dtw(ts_a, ts_b, d=lambda x, y: abs(x - y), window=10000):
    """Return the DTW similarity distance timeseries numpy arrays.

    Arguments
    ---------
    ts_a, ts_b : array of shape [n_samples, n_timepoints]
        Two arrays containing n_samples of timeseries data
        whose DTW distance between each sample of A and B
        will be compared

    d : DistanceMetric object (default = abs(x-y))
        the distance measure used for A_i - B_j in the
        DTW dynamic programming function

    Returns
    -------
    DTW distance between A and B

    """
    # Create cost matrix via broadcasting with large int
    ts_a, ts_b = pd.np.array(ts_a), pd.np.array(ts_b)
    M, N = len(ts_a), len(ts_b)
    cost = sys.maxsize * pd.np.ones((M, N))

    # Initialize the first row and column
    cost[0, 0] = d(ts_a[0], ts_b[0])
    for i in range(1, M):
        cost[i, 0] = cost[i - 1, 0] + d(ts_a[i], ts_b[0])

    for j in range(1, N):
        cost[0, j] = cost[0, j - 1] + d(ts_a[0], ts_b[j])

    # Populate rest of cost matrix within window
    for i in range(1, M):
        for j in range(max(1, i - window),
                       min(N, i + window)):
            choices = cost[i - 1, j - 1], cost[i, j - 1], cost[i - 1, j]
            cost[i, j] = min(choices) + d(ts_a[i], ts_b[j])

    # Return DTW distance given window
    return cost[-1, -1]


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def dtw(input_ts='-',
        columns=None,
        start_date=None,
        end_date=None,
        round_index=None,
        dropna='no',
        window=10000):
    """Dynamic Time Warping.

    Parameters
    ----------
    window : int
         [optional, default is 10000]

         Window length.
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {round_index}
    {dropna}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna='no')

    process = {}
    for i in tsd.columns:
        for j in tsd.columns:
            if (i, j) not in process and (j, i) not in process and i != j:
                process[(i, j)] = _dtw(tsd[i], tsd[j], window=window)

    ntsd = pd.DataFrame(list(process.items()))
    ncols = ntsd.columns
    ncols = ['Variables'] + [str(i) + 'DTW_score' for i in ncols[1:]]
    ntsd.columns = ncols
    return tsutils.printiso(ntsd)


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def pca(input_ts='-',
        columns=None,
        start_date=None,
        end_date=None,
        n_components=None,
        round_index=None):
    """Return the principal components analysis of the time series.

    Does not return a time-series.

    Parameters
    ----------
    n_components : int
        [optional, default is None]

        The number of groups to separate the time series into.
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {round_index}

    """
    from sklearn.decomposition import PCA

    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              round_index=round_index,
                              pick=columns)

    pca = PCA(n_components)
    pca.fit(tsd.dropna(how='any'))
    print(pca.components_)


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def normalization(input_ts='-',
                  columns=None,
                  start_date=None,
                  end_date=None,
                  dropna='no',
                  mode='minmax',
                  min_limit=0,
                  max_limit=1,
                  pct_rank_method='average',
                  print_input=False,
                  round_index=None,
                  float_format='%g'):
    """Return the normalization of the time series.

    Parameters
    ----------
    mode : str
        [optional, default is 'minmax']

        minmax
            min_limit +
            (X-Xmin)/(Xmax-Xmin)*(max_limit-min_limit)

        zscore
            X-mean(X)/stddev(X)

        pct_rank
            rank(X)*100/N
    min_limit : float
        [optional, defaults to 0]

        Defines the minimum limit of the minmax normalization.
    max_limit : float
        [optional, defaults to 1]

        Defines the maximum limit of the minmax normalization.
    pct_rank_method : str
        [optional, defaults to 'average']

        Defines how tied ranks are broken.  Can be 'average', 'min', 'max',
        'first', 'dense'.
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {print_input}
    {float_format}
    {round_index}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)

    # Trying to save some memory
    if print_input:
        otsd = tsd.copy()
    else:
        otsd = pd.DataFrame()

    if mode == 'minmax':
        tsd = (min_limit +
               (tsd - tsd.min()) /
               (tsd.max() - tsd.min()) *
               (max_limit - min_limit))
    elif mode == 'zscore':
        tsd = (tsd - tsd.mean()) / tsd.std()
    elif mode == 'pct_rank':
        tsd = tsd.rank(method=pct_rank_method, pct=True)
    else:
        raise ValueError("""
*
*   The 'mode' options are 'minmax', 'zscore', or 'pct_rank', you gave me
*   {0}.
*
""".format(mode))

    tsd = tsutils.memory_optimize(tsd)
    return tsutils.print_input(print_input,
                               otsd,
                               tsd,
                               '_{0}'.format(mode),
                               float_format=float_format)


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def converttz(fromtz,
              totz,
              input_ts='-',
              columns=None,
              start_date=None,
              end_date=None,
              round_index=None,
              dropna='no'):
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
    {round_index}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)
    tsd = tsd.tz_localize(fromtz).tz_convert(totz)
    return tsutils.printiso(tsd,
                            showindex='always')


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def convert_index_to_julian(epoch='julian',
                            input_ts='-',
                            columns=None,
                            start_date=None,
                            end_date=None,
                            round_index=None,
                            dropna='no'):
    """Convert date/time index to Julian dates from different epochs.

    Parameters
    ----------
    epoch : str
        [optional, defaults to 'julian']

        Can be one of, 'julian', 'reduced', 'modified',
        'truncated', 'dublin', 'cnes', 'ccsds', 'lop', 'lilian', 'rata_die',
        'mars_sol_date', or a date and time.

        If supplying a date and time, most formats are recognized, however
        the closer the format is to ISO 8601 the better.  Also should check and
        make sure date was parsed as expected.  If supplying only a date, the
        epoch starts at midnight the morning of that date.

        +-----------+-------------------+----------------+---------------+
        | epoch     | Epoch             | Calculation    | Notes         |
        +===========+===================+================+===============+
        | julian    | 4713-01-01:12 BCE | JD             |               |
        +-----------+-------------------+----------------+---------------+
        | reduced   | 1858-11-16:12     | JD -           | [ [1]_ ]      |
        |           |                   | 2400000        | [ [2]_ ]      |
        +-----------+-------------------+----------------+---------------+
        | modified  | 1858-11-17:00     | JD -           | SAO 1957      |
        |           |                   | 2400000.5      |               |
        +-----------+-------------------+----------------+---------------+
        | truncated | 1968-05-24:00     | floor (JD -    | NASA 1979     |
        |           |                   | 2440000.5)     |               |
        +-----------+-------------------+----------------+---------------+
        | dublin    | 1899-12-31:12     | JD -           | IAU 1955      |
        |           |                   | 2415020        |               |
        +-----------+-------------------+----------------+---------------+
        | cnes      | 1950-01-01:00     | JD -           | CNES          |
        |           |                   | 2433282.5      | [ [3]_ ]      |
        +-----------+-------------------+----------------+---------------+
        | ccsds     | 1958-01-01:00     | JD -           | CCSDS         |
        |           |                   | 2436204.5      | [ [3]_ ]      |
        +-----------+-------------------+----------------+---------------+
        | lop       | 1992-01-01:00     | JD -           | LOP           |
        |           |                   | 2448622.5      | [ [3]_ ]      |
        +-----------+-------------------+----------------+---------------+
        | lilian    | 1582-10-15[13]    | floor (JD -    | Count of days |
        |           |                   | 2299159.5)     | of the        |
        |           |                   |                | Gregorian     |
        |           |                   |                | calendar      |
        +-----------+-------------------+----------------+---------------+
        | rata_die  | 0001-01-01[13]    | floor (JD -    | Count of days |
        |           | proleptic         | 1721424.5)     | of the        |
        |           | Gregorian         |                | Common        |
        |           | calendar          |                | Era           |
        +-----------+-------------------+----------------+---------------+
        | mars_sol  | 1873-12-29:12     | (JD - 2405522) | Count of      |
        |           |                   | /1.02749       | Martian days  |
        +-----------+-------------------+----------------+---------------+

        .. [1] . Hopkins, Jeffrey L. (2013). Using Commercial Amateur
           Astronomical Spectrographs, p. 257, Springer Science & Business
           Media, ISBN 9783319014425

        .. [2] . Palle, Pere L., Esteban, Cesar. (2014). Asteroseismology, p.
           185, Cambridge University Press, ISBN 9781107470620

        .. [3] . Theveny, Pierre-Michel. (10 September 2001). "Date Format"
           The TPtime Handbook. Media Lab.

    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {round_index}
    {dropna}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)
    allowed = {'julian': lambda x: x,
               'reduced': lambda x: x - 2400000,
               'modified': lambda x: x - 2400000.5,
               'truncated': lambda x: pd.np.floor(x - 2440000.5),
               'dublin': lambda x: x - 2415020,
               'cnes': lambda x: x - 2433282.5,
               'ccsds': lambda x: x - 2436204.5,
               'lop': lambda x: x - 2448622.5,
               'lilian': lambda x: pd.np.floor(x - 2299159.5),
               'rata_die': lambda x: pd.np.floor(x - 1721424.5),
               'mars_sol': lambda x: (x - 2405522) / 1.02749}
    try:
        tsd.index = allowed[epoch](tsd.index.to_julian_date())
    except KeyError:
        tsd.index = (tsd.index.to_julian_date() -
                     pd.to_datetime(tsutils.parsedate(epoch)).to_julian_date())

    tsd.index.name = '{0}_date'.format(epoch)
    tsd.index = tsd.index.format(formatter=lambda x: str('{0:f}'.format(x)))

    return tsutils.printiso(tsd,
                            showindex='always')


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def pct_change(input_ts='-',
               columns=None,
               start_date=None,
               end_date=None,
               dropna='no',
               periods=1,
               fill_method='pad',
               limit=None,
               freq=None,
               print_input=False,
               round_index=None,
               float_format='%g'):
    """Return the percent change between times.

    Parameters
    ----------
    periods : int
        [optional, default is 1]

        The number of intervals to calculate percent change across.
    fill_method : str
        [optional, defaults to 'pad']

        Fill method for NA.  Defaults to 'pad'.
    limit
        [optional, defaults to None]

        Is the minimum number of consecutive NA values where no more filling
        will be made.
    freq : str
        [optional, defaults to None]

        A pandas time offset string to represent the interval.
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {print_input}
    {float_format}
    {round_index}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)

    # Trying to save some memory
    if print_input:
        otsd = tsd.copy()
    else:
        otsd = pd.DataFrame()

    return tsutils.print_input(print_input,
                               otsd,
                               tsd.pct_change(periods=periods,
                                              fill_method=fill_method,
                                              limit=limit,
                                              freq=freq),
                               '_pct_change',
                               float_format=float_format)


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def rank(input_ts='-',
         columns=None,
         start_date=None,
         end_date=None,
         dropna='no',
         axis=0,
         method='average',
         numeric_only=None,
         na_option='keep',
         ascending=True,
         pct=False,
         print_input=False,
         float_format='%g',
         round_index=None):
    """Compute numerical data ranks (1 through n) along axis.

    Equal values are assigned a rank that is the average of the ranks of those
    values

    Parameters
    ----------
    axis
        [optional, default is 0]

        0 or 'index' for rows. 1 or 'columns' for columns.  Index to direct
        ranking.
    method : str
        [optional, default is 'average']

        +-----------------+--------------------------------+
        | method argument | Description                    |
        +=================+================================+
        | average         | average rank of group          |
        +-----------------+--------------------------------+
        | min             | lowest rank in group           |
        +-----------------+--------------------------------+
        | max             | highest rank in group          |
        +-----------------+--------------------------------+
        | first           | ranks assigned in order they   |
        |                 | appear in the array            |
        +-----------------+--------------------------------+
        | dense           | like 'min', but rank always    |
        |                 | increases by 1 between groups  |
        +-----------------+--------------------------------+

    numeric_only
        [optional, default is None]

        Include only float, int, boolean data. Valid only for DataFrame or
        Panel objects.
    na_option : str
        [optional, default is 'keep']

        +--------------------+--------------------------------+
        | na_option argument | Description                    |
        +====================+================================+
        | keep               | leave NA values where they are |
        +--------------------+--------------------------------+
        | top                | smallest rank if ascending     |
        +--------------------+--------------------------------+
        | bottom             | smallest rank if descending    |
        +--------------------+--------------------------------+

    ascending
        [optional, default is True]

        False ranks by high (1) to low (N)
    pct
        [optional, default is False]

        Computes percentage rank of data.
    {input_ts}
    {columns}
    {start_date}
    {end_date}
    {dropna}
    {print_input}
    {float_format}
    {round_index}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna=dropna)

    # Trying to save some memory
    if print_input:
        otsd = tsd.copy()
    else:
        otsd = pd.DataFrame()

    return tsutils.print_input(print_input,
                               otsd,
                               tsd.rank(axis=axis,
                                        method=method,
                                        numeric_only=numeric_only,
                                        na_option=na_option,
                                        ascending=ascending,
                                        pct=pct),
                               '_rank',
                               float_format=float_format)


@mando.command(formatter_class=RSTHelpFormatter, doctype='numpy')
@tsutils.doc(tsutils.docstrings)
def date_offset(years=0,
                months=0,
                weeks=0,
                days=0,
                hours=0,
                minutes=0,
                seconds=0,
                microseconds=0,
                columns=None,
                dropna='no',
                input_ts='-',
                start_date=None,
                end_date=None,
                round_index=None):
    """Apply an offset to a time-series.

    Parameters
    ----------
    years: number
        [optional, default is 0]

        Relative number of years to offset the datetime index,
        may be negative; adding or subtracting a relativedelta with
        relative information performs the corresponding arithmetic
        operation on the original datetime value with the information in
    months: number
        [optional, default is 0]

        Relative number of months to offset the datetime index,
        may be negative; adding or subtracting a relativedelta with
        relative information performs the corresponding arithmetic
        operation on the original datetime value with the information in
    weeks: number
        [optional, default is 0]

        Relative number of weeks to offset the datetime index,
        may be negative; adding or subtracting a relativedelta with
        relative information performs the corresponding arithmetic
        operation on the original datetime value with the information in
    days: number
        [optional, default is 0]

        Relative number of days to offset the datetime index,
        may be negative; adding or subtracting a relativedelta with
        relative information performs the corresponding arithmetic
        operation on the original datetime value with the information in
    hours: number
        [optional, default is 0]

        Relative number of hours to offset the datetime index,
        may be negative; adding or subtracting a relativedelta with
        relative information performs the corresponding arithmetic
        operation on the original datetime value with the information in
    minutes: number
        [optional, default is 0]

        Relative number of minutes to offset the datetime index,
        may be negative; adding or subtracting a relativedelta with
        relative information performs the corresponding arithmetic
        operation on the original datetime value with the information in
    seconds: number
        [optional, default is 0]

        Relative number of seconds to offset the datetime index,
        may be negative; adding or subtracting a relativedelta with
        relative information performs the corresponding arithmetic
        operation on the original datetime value with the information in
    microseconds: number
        [optional, default is 0]

        Relative number of microseconds to offset the datetime index,
        may be negative; adding or subtracting a relativedelta with
        relative information performs the corresponding arithmetic
        operation on the original datetime value with the information in
        the relativedelta.
    {input_ts}
    {start_date}
    {end_date}
    {columns}
    {round_index}
    {dropna}

    """
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns,
                              round_index=round_index,
                              dropna='no')

    relativedelta = pd.tseries.offsets.relativedelta
    ntsd = pd.DataFrame(tsd.values,
                        index=[i +
                               relativedelta(years=years,
                                             months=months,
                                             days=days,
                                             hours=hours,
                                             minutes=minutes,
                                             seconds=seconds,
                                             microseconds=microseconds)
                               for i in tsd.index])
    ntsd.columns = tsd.columns

    return tsutils.printiso(ntsd, showindex='always')


def main():
    """Main function."""
    if not os.path.exists('debug_tstoolbox'):
        sys.tracebacklimit = 0
    mando.main()


if __name__ == '__main__':
    main()
