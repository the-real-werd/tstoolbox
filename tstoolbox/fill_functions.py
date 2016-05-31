#!/sjr/beodata/local/python_linux/bin/python
'''A collection of filling routines.
'''

from __future__ import print_function
from __future__ import absolute_import

import pandas as pd
import mando
from mando.rst_text_formatter import RSTHelpFormatter

from . import tsutils


@mando.command(formatter_class=RSTHelpFormatter)
def fill(method='ffill',
         interval='guess',
         print_input=False,
         input_ts='-',
         start_date=None,
         end_date=None,
         columns=None):
    '''Fills missing values (NaN) with different methods.

    Missing values can occur because of NaN, or because the time series
    is sparse.  The 'interval' option can insert NaNs to create a dense
    time series.

    :param method: String contained in single quotes or a number that
        defines the method to use for filling.

        +-----------+---------------------------+
        | ffill     | assigns NaN values to     |
        |           | the last good value       |
        +-----------+---------------------------+
        | bfill     | assigns NaN values to     |
        |           | the next good value       |
        +-----------+---------------------------+
        | 2.3       | any number: fills all NaN |
        |           | with this number          |
        +-----------+---------------------------+
        | linear    | will linearly interpolate |
        |           | missing values            |
        +-----------+---------------------------+
        | spline    | spline interpolation      |
        +-----------+---------------------------+
        | nearest   | nearest good value        |
        +-----------+---------------------------+
        | zero      |                           |
        +-----------+---------------------------+
        | slinear   |                           |
        +-----------+---------------------------+
        | quadratic |                           |
        +-----------+---------------------------+
        | cubic     |                           |
        +-----------+---------------------------+
        | mean      | fill with mean            |
        +-----------+---------------------------+
        | median    | fill with median          |
        +-----------+---------------------------+
        | max       | fill with maximum         |
        +-----------+---------------------------+
        | min       | fill with minimum         |
        +-----------+---------------------------+

        If a number will fill with that number.
    :param interval: Will try to insert missing intervals.  Can give any
        of the pandas offset aliases, 'guess' (to try and figure the
        interval), or None to not insert missing intervals.
    :param -p, --print_input: If set to 'True' will include the input
        columns in the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value'
        format or '-' for stdin.
    :param -s, --start_date <str>:  The start_date of the series in
        ISOdatetime format, or 'None' for beginning.
    :param -e, --end_date <str>:  The end_date of the series in
        ISOdatetime format, or 'None' for end.
    :param columns:  Columns to pick out of input.  Can use column names
        or column numbers.  If using numbers, column number 0 is the
        first column.  To pick multiple columns; separate by commas with
        no spaces.  As used in 'pick' command.
    '''
    tsd = tsutils.common_kwds(tsutils.read_iso_ts(input_ts, dense=False),
                              start_date=start_date,
                              end_date=end_date,
                              pick=columns)
    if print_input is True:
        ntsd = tsd.copy()
    else:
        ntsd = tsd
    ntsd = tsutils.asbestfreq(ntsd)
    offset = ntsd.index[1] - ntsd.index[0]
    predf = pd.DataFrame(dict(zip(tsd.columns, tsd.mean().values)),
                         index=[tsd.index[0] - offset])
    postf = pd.DataFrame(dict(zip(tsd.columns, tsd.mean().values)),
                         index=[tsd.index[-1] + offset])
    ntsd = pd.concat([predf, ntsd, postf])
    if method in ['ffill', 'bfill']:
        ntsd = ntsd.fillna(method=method)
    elif method in ['linear']:
        ntsd = ntsd.apply(pd.Series.interpolate, method='values')
    elif method in ['nearest', 'zero', 'slinear', 'quadratic', 'cubic']:
        from scipy.interpolate import interp1d
        for c in ntsd.columns:
            df2 = ntsd[c].dropna()
            f = interp1d(df2.index.values.astype('d'), df2.values, kind=method)
            slices = pd.isnull(ntsd[c])
            ntsd[c][slices] = f(ntsd[c][slices].index.values.astype('d'))
    elif method in ['mean']:
        ntsd = ntsd.fillna(ntsd.mean())
    elif method in ['median']:
        ntsd = ntsd.fillna(ntsd.median())
    elif method in ['max']:
        ntsd = ntsd.fillna(ntsd.max())
    elif method in ['min']:
        ntsd = ntsd.fillna(ntsd.min())
    else:
        try:
            ntsd = ntsd.fillna(value=float(method))
        except ValueError:
            raise ValueError('''
*
*   The allowable values for 'method' are 'ffill', 'bfill', 'linear',
*   'nearest', 'zero', 'slinear', 'quadratic', 'cubic', 'mean', 'median',
*   'max', 'min' or a number.  Instead you have {0}.
*
'''.format(method))
    ntsd = ntsd.iloc[1:-1]
    tsd.index.name = 'Datetime'
    ntsd.index.name = 'Datetime'
    return tsutils.print_input(print_input, tsd, ntsd, '_fill')


#@mando.command(formatter_class=RSTHelpFormatter)
def fill_by_correlation(method='move2',
                        maximum_lag=0,
                        interval='guess',
                        transform='log10',
                        choose_best='dtw',
                        print_input=False,
                        input_ts='-'):
    '''Fills missing values (NaN) with different methods.

    Missing values can occur because of NaN, or because the time series
    is sparse.  The 'interval' option can insert NaNs to create a dense
    time series.

    :param method: String contained in single quotes or a number that
        defines the method to use for filling.  'move2': maintenance of
        variance extension - 2
    :param interval: Will try to insert missing intervals.  Can give any
        of the pandas offset aliases, 'guess' (to try and figure the
        interval), or None to not insert missing intervals.
    :param -p, --print_input: If set to 'True' will include the input
        columns in the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value'
        format or '-' for stdin.
    '''
    tsd = tsutils.read_iso_ts(input_ts)
    if print_input is True:
        ntsd = tsd.copy()
    else:
        ntsd = tsd
    ntsd = tsutils.asbestfreq(ntsd)

    if transform == 'log10':
        ntsd = pd.np.log10(ntsd)

    firstcol = pd.DataFrame(ntsd.iloc[:, 0])
    basets = pd.DataFrame(ntsd.iloc[:, 1:])
    if choose_best is True:
        firstcol = pd.DataFrame(ntsd.iloc[:, 0])
        allothers = pd.DataFrame(ntsd.iloc[:, 1:])
        collect = []
        for index in list(range(maximum_lag + 1)):
            shifty = allothers.shift(index)
            testdf = firstcol.join(shifty)
            lagres = testdf.dropna().corr().iloc[1:, 0]
            collect.append(pd.np.abs(lagres.values))
        collect = pd.np.array(collect)
        bestlag, bestts = pd.np.unravel_index(collect.argmax(), collect.shape)
        basets = pd.DataFrame(ntsd.iloc[:, bestts + 1].shift(bestlag))

    single_source_ts = ['move1', 'move2', 'move3']
    if method.lower() in single_source_ts:
        if len(basets.columns) != 1:
            raise ValueError('''
*
*   For methods in {0}
*   You can only have a single source column.  You can pass in onlu 2
*   time-series or use the flag 'choose_best' along with 'maximum_lag'.
*   Instead there are {1} source time series.
*
'''.format(single_source_ts, len(basets.columns)))

    if method == 'move1':
        ntsd = firstcol.join(basets)
        dna = ntsd.dropna()
        means = pd.np.mean(dna)
        stdevs = pd.np.std(dna)
        print(means[1] + stdevs[1]/stdevs[0]*means[0])
        print(means, stdevs)

