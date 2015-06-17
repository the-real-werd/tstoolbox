#!/sjr/beodata/local/python_linux/bin/python
'''
tstoolbox is a collection of command line tools for the manipulation of time
series.
'''

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import sys
import os.path
import warnings
from argparse import RawTextHelpFormatter
warnings.filterwarnings('ignore')

import pandas as pd
# The numpy import is needed like this to be able to include numpy functions in
# the 'equation' subcommand.
from numpy import *
import mando

from . import tsutils
from . import fill_functions
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


@mando.command
def filter(filter_type,
           print_input=False,
           cutoff_period=None,
           window_len=5,
           float_format='%g',
           input_ts='-',
           start_date=None,
           end_date=None):
    '''
    Apply different filters to the time-series.

    :param filter_type <str>: 'flat', 'hanning', 'hamming', 'bartlett',
        'blackman', 'fft_highpass' and 'fft_lowpass' for Fast Fourier Transform
        filter in the frequency domain.
    :param window_len <int>: For the windowed types, 'flat', 'hanning',
        'hamming', 'bartlett', 'blackman' specifies the length of the window.
        Defaults to 5.
    :param -p, --print_input: If set to 'True' will include the input
        columns in the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.  Default is stdin.
    :param cutoff_period: The period in input time units that will form the
        cutoff between low frequencies (longer periods) and high frequencies
        (shorter periods).  Filter will be smoothed by `window_len` running
        average.  For 'fft_highpass' and 'fft_lowpass'. Default is None and
        must be supplied if using 'fft_highpass' or 'fft_lowpass'.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
    from tstoolbox import filters

    if len(tsd.values) < window_len:
        raise ValueError('''
*
*   Input vector (length={0}) needs to be bigger than window size ({1}).
*
'''.format(len(tsd.values), window_len))

    # Trying to save some memory
    if print_input:
        otsd = tsd.copy()
    else:
        otsd = pd.DataFrame()

    for col in tsd.columns:
        # fft_lowpass, fft_highpass
        if filter_type == 'fft_lowpass':
            tsd[col].values[:] = filters._transform(
                tsd[col].values, cutoff_period, window_len, lopass=True)
        elif filter_type == 'fft_highpass':
            tsd[col].values[:] = filters._transform(
                tsd[col].values, cutoff_period, window_len)
        elif filter_type in ['flat',
                             'hanning',
                             'hamming',
                             'bartlett',
                             'blackman']:
            if window_len < 3:
                continue
            s = pd.np.pad(tsd[col].values, window_len//2, 'reflect')

            if filter_type == 'flat':  # moving average
                w = pd.np.ones(window_len, 'd')
            else:
                w = eval('pd.np.' + filter_type + '(window_len)')
            tsd[col].values[:] = pd.np.convolve(w / w.sum(), s, mode='valid')
        else:
            raise ValueError('''
*
*   Filter type {0} not implemented.
*
'''.format(filter_type))
    return tsutils.print_input(print_input, otsd, tsd, '_filter',
                               float_format=float_format)


def zero_crossings(y_axis, window=11):
    """
    Algorithm to find zero crossings. Smooths the curve and finds the
    zero-crossings by looking for a sign change.


    keyword arguments:
    y_axis -- A list containing the signal over which to find zero-crossings
    window -- the dimension of the smoothing window; should be an odd integer
        (default: 11)

    return -- the index for each zero-crossing
    """
    # smooth the curve
    length = len(y_axis)
    x_axis = pd.np.asarray(range(length), int)

    ymean = y_axis.mean()
    y_axis = y_axis - ymean

    # discard tail of smoothed signal
    y_axis = _smooth(y_axis, window)[:length]
    zero_crossings = pd.np.where(pd.np.diff(pd.np.sign(y_axis)))[0]
    indices = [x_axis[index] for index in zero_crossings]

    # check if zero-crossings are valid
#    diff = np.diff(indices)
#    if diff.std() / diff.mean() > 0.2:
#        print diff.std() / diff.mean()
#        print np.diff(indices)
#        raise(ValueError,
#            "False zero-crossings found, indicates problem {0} or {1}".format(
#            "with smoothing window", "problem with offset"))
    # check if any zero crossings were found
    if len(zero_crossings) < 1:
        raise ValueError

    return indices
    # used this to test the fft function's sensitivity to spectral leakage
    # return indices + np.asarray(30 * np.random.randn(len(indices)), int)

# Frequency calculation#############################
#    diff = np.diff(indices)
#    time_p_period = diff.mean()
#
#    if diff.std() / time_p_period > 0.1:
#        raise ValueError,
#            "smoothing window too small, false zero-crossing found"
#
#    #return frequency
#    return 1.0 / time_p_period
##############################################################################

    # return tsutils.print_input(print_input, tsd, tmptsd, '_filter')


@mando.command
def read(filenames, start_date=None, end_date=None, dense=False,
         float_format='%g', how='outer'):
    '''
    Collect time series from a list of pickle or csv files then print
    in the tstoolbox standard format.

    :param filenames <str>: List of comma delimited filenames to read time
        series from.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    :param dense: Set `dense` to True to have missing values inserted such that
        there is a single interval.
    :param how <str>: Use PANDAS concept on how to join the separate DataFrames
        read from each file.  Default how='outer' which is the union, 'inner'
        is the intersection,
    '''
    filenames = filenames.split(',')
    result = pd.concat([tsutils.date_slice(
                        tsutils.read_iso_ts(i,
                                            dense=dense,
                                            extended_columns=True),
                        start_date=start_date,
                        end_date=end_date) for i in filenames],
                        join=how,
                        axis=1)

    colnames = ['.'.join(i.split('.')[1:]) for i in result.columns]
    if len(colnames) == len(set(colnames)):
        result.columns = colnames
    else:
        result.columns = [i if result.columns.tolist().count(i) == 1
                          else i + str(index)
                          for index, i in enumerate(result.columns)]

    return tsutils.printiso(result, float_format=float_format)


@mando.command
def date_slice(float_format='%g',
               start_date=None,
               end_date=None,
               input_ts='-'):
    '''
    Prints out data to the screen between start_date and end_date

    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    '''
    return tsutils.printiso(
        tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                           start_date=start_date,
                           end_date=end_date), float_format=float_format)


@mando.command
def describe(input_ts='-', start_date=None, end_date=None):
    '''
    Prints out statistics for the time-series.

    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
    return tsutils.printiso(tsd.describe())


@mando.command
def peak_detection(method='rel',
                   type='peak',
                   window=24,
                   pad_len=5,
                   points=9,
                   lock_frequency=False,
                   float_format='%g',
                   print_input='',
                   input_ts='-',
                   start_date=None,
                   end_date=None):
    '''
    Peak and valley detection.

    :param type <str>: 'peak', 'valley', or 'both' to determine what should be
        returned.  Default is 'peak'.
    :param method <str>: 'rel', 'minmax', 'zero_crossing', 'parabola', 'sine'
        methods are available.  The different algorithms have different
        strengths and weaknesses.  The 'rel' algorithm is the default.
    :param window <int>: There will not usually be multiple peaks within the
        window number of values.  The different `method`s use this variable in
        different ways.
        For 'rel' the window keyword specifies how many points on each side
        to require a `comparator`(n,n+x) = True.
        For 'minmax' the window keyword is the distance to look ahead from a
        peak candidate to determine if it is the actual peak
        '(sample / period) / f' where '4 >= f >= 1.25' might be a good value
        For 'zero_crossing' the window keyword is the dimension of the
        smoothing window; should be an odd integer
    :param points <int>: For 'parabola' and 'sine' methods. How many points
        around the peak should be used during curve fitting, must be odd
        (default: 9)
    :param lock_frequency: For 'sine method only.  Specifies if the
        frequency argument of the model function should be locked to the
        value calculated from the raw peaks or if optimization process may
        tinker with it. (default: False)
    :param -p, --print_input: If set to 'True' will include the input columns
        in the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.  Default is stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    # Couldn't get fft method working correctly.  Left pieces in
    # in case want to figure it out in the future.

    if type not in ['peak', 'valley', 'both']:
        raise ValueError('''
*
*   The `type` argument must be one of 'peak',
*   'valley', or 'both'.  You supplied {0}.
*
'''.format(type))

    if method not in ['rel', 'minmax', 'zero_crossing', 'parabola', 'sine']:
        raise ValueError('''
*
*   The `method` argument must be one of 'rel', 'minmax',
*   'zero_crossing', 'parabola', or 'sine'.  You supplied {0}.
*
'''.format(method))

    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)

    window = int(window)
    kwds = {}
    if method == 'rel':
        from tstoolbox.peakdetect import _argrel as func
        window = window / 2
        if window == 0:
            window = 1
        kwds['window'] = int(window)
    elif method == 'minmax':
        from tstoolbox.peakdetect import _peakdetect as func
        window = int(window / 2)
        if window == 0:
            window = 1
        kwds['window'] = int(window)
    elif method == 'zero_crossing':
        from tstoolbox.peakdetect import _peakdetect_zero_crossing as func
        if not window % 2:
            window = window + 1
        kwds['window'] = int(window)
    elif method == 'parabola':
        from tstoolbox.peakdetect import _peakdetect_parabola as func
        kwds['points'] = int(points)
    elif method == 'sine':
        from tstoolbox.peakdetect import _peakdetect_sine as func
        kwds['points'] = int(points)
        kwds['lock_frequency'] = lock_frequency
    elif method == 'fft':  # currently would never be used.
        from tstoolbox.peakdetect import _peakdetect_fft as func
        kwds['pad_len'] = int(pad_len)

    if type == 'peak':
        tmptsd = tsd.rename(columns=lambda x: str(x) + '_peak', copy=True)
    if type == 'valley':
        tmptsd = tsd.rename(columns=lambda x: str(x) + '_valley', copy=True)
    if type == 'both':
        tmptsd = tsd.rename(columns=lambda x: str(x) + '_peak', copy=True)
        tmptsd = tmptsd.join(
            tsd.rename(columns=lambda x: str(x) + '_valley', copy=True),
            how='outer')

    for c in tmptsd.columns:
        if method in ['fft', 'parabola', 'sine']:
            maxpeak, minpeak = func(
                tmptsd[c].values, range(len(tmptsd[c])), **kwds)
        else:
            maxpeak, minpeak = func(tmptsd[c].values, **kwds)
        if c[-5:] == '_peak':
            datavals = maxpeak
        if c[-7:] == '_valley':
            datavals = minpeak
        maxx, maxy = list(zip(*datavals))
        hold = tmptsd[c][array(maxx).astype('i')]
        tmptsd[c][:] = pd.np.nan
        tmptsd[c][array(maxx).astype('i')] = hold

    tmptsd.index.name = 'Datetime'
    tsd.index.name = 'Datetime'
    return tsutils.print_input(print_input, tsd, tmptsd, None,
                               float_format=float_format)


@mando.command
def convert(
        factor=1.0,
        offset=0.0,
        print_input=False,
        float_format='%g',
        input_ts='-',
        start_date=None,
        end_date=None):
    '''
    Converts values of a time series by applying a factor and offset.  See the
        'equation' subcommand for a generalized form of this command.

    :param factor <float>: Factor to multiply the time series values.
    :param offset <float>: Offset to add to the time series values.
    :param -p, --print_input: If set to 'True' will include the input columns
        in the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
    tmptsd = tsd * factor + offset
    return tsutils.print_input(print_input, tsd, tmptsd, '_convert',
                               float_format='%g')


def _parse_equation(equation):
    '''
    Private function to parse the equation used in the calculations.
    '''
    import re
    # Get rid of spaces
    nequation = equation.replace(' ', '')

    # Does the equation contain any x[t]?
    tsearch = re.search(r'\[.*?t.*?\]', nequation)

    # Does the equation contain any x1, x2, ...etc.?
    nsearch = re.search(r'x[1-9][0-9]*', nequation)

    # This beasty is so users can use 't' in their equations
    # Indices of 'x' are a function of 't' and can possibly be negative or
    # greater than the length of the DataFrame.
    # Correctly (I think) handles negative indices and indices greater
    # than the length by setting to nan
    # AssertionError happens when index negative.
    # IndexError happens when index is greater than the length of the
    # DataFrame.
    # UGLY!

    # testeval is just a list of the 't' expressions in the equation.
    # for example 'x[t]+0.6*max(x[t+1],x[t-1]' would have
    # testeval = ['t', 't+1', 't-1']
    testeval = set()
    # If there is both function of t and column terms x1, x2, ...etc.
    if tsearch and nsearch:
        testeval.update(re.findall(r'x[1-9][0-9]*\[(.*?t.*?)\]',
                                   nequation))
        # replace 'x1[t+1]' with 'x.ix[t+1,1-1]'
        # replace 'x2[t+7]' with 'x.ix[t+7,2-1]'
        # ...etc
        nequation = re.sub(r'x([1-9][0-9]*)\[(.*?t.*?)\]',
                           r'x.ix[\2,\1-1]',
                           nequation)
        # replace 'x1' with 'x.ix[t,1-1]'
        # replace 'x4' with 'x.ix[t,4-1]'
        nequation = re.sub(r'x([1-9][0-9]*)',
                           r'x.ix[t,\1-1]',
                           nequation)
    # If there is only a function of t, i.e. x[t]
    elif tsearch:
        testeval.update(re.findall(r'x\[(.*?t.*?)\]',
                                   nequation))
        nequation = re.sub(r'x\[(.*?t.*?)\]',
                           r'xxix[\1,:]',
                           nequation)
        # Replace 'x' with underlying equation, but not the 'x' in a word,
        # like 'maximum'.
        nequation = re.sub(r'(?<![a-zA-Z])x(?![a-zA-Z\[])',
                           r'xxix[t,:]',
                           nequation)
        nequation = re.sub(r'xxix',
                           r'x.ix',
                           nequation)

    elif nsearch:
        nequation = re.sub(r'x([1-9][0-9]*)',
                           r'x.ix[:,\1-1]',
                           nequation)

    try:
        testeval.remove('t')
    except KeyError:
        pass
    return tsearch, nsearch, testeval, nequation

@mando.command
def equation(
        equation,
        print_input='',
        float_format='%g',
        input_ts='-',
        start_date=None,
        end_date=None):
    '''
    Applies <equation> to the time series data.  The <equation> argument is a
        string contained in single quotes with 'x' used as the variable
        representing the input.  For example, '(1 - x)*sin(x)'.

    :param equation <str>: String contained in single quotes that defines the
        equation.  The input variable place holder is 'x'.  Mathematical
        functions in the 'np' (numpy) name space can be used.  For example,
        'x*4 + 2', 'x**2 + cos(x)', and 'tan(x*pi/180)' are all valid
        <equation> strings.  The variable 't' is special representing the time
        at which 'x' occurs.  This means you can do things like 'x[t] +
        max(x[t-1], x[t+1])*0.6' to add to the current value 0.6 times the
        maximum adjacent value.
    :param -p, --print_input: If set to 'True' will include the input columns
        in the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    x = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                           start_date=start_date,
                           end_date=end_date).astype('f')

    tsearch, nsearch, testeval, nequation = _parse_equation(equation)
    if tsearch and nsearch:
        y = pd.DataFrame(x.ix[:, 0].copy(), index=x.index, columns=['_'])
        for t in range(len(x)):
            try:
                for tst in testeval:
                    if eval(tst) < 0:
                        raise IndexError()
                y.ix[t, 0] = eval(nequation)
            except (AssertionError, IndexError):
                y.ix[t, 0] = pd.np.nan
        y = pd.DataFrame(y, columns=['_'], dtype='float32')
    elif tsearch:
        y = x.copy()
        for t in range(len(x)):
            try:
                for tst in testeval:
                    if eval(tst) < 0:
                        raise IndexError()
                y.ix[t, :] = eval(nequation)
            except (AssertionError, IndexError):
                y.ix[t, :] = pd.np.nan
    elif nsearch:
        y = pd.DataFrame(x.ix[:, 0].copy(), index=x.index, columns=['_'])
        y.ix[:, 0] = eval(nequation)
    else:
        y = eval(equation)
    return tsutils.print_input(print_input, x, y, '_equation',
                               float_format=float_format)


@mando.command
def pick(columns, input_ts='-', start_date=None, end_date=None):
    '''
    Will pick a column or list of columns from input.  Start with 1.

    :param columns: Either an integer to collect a single column or a list of
        integers to collect multiple columns.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)

    columns = columns.split(',')
    ncolumns = []
    for i in columns:
        if i in tsd.columns:
            ncolumns.append(tsd.columns.tolist().index(i))
            continue
        else:
            try:
                target_col = int(i)
            except:
                raise ValueError('''
*
*   The name {0} isn't in the list of column names
*   {1}.
*
'''.format(i, tsd.columns))
            if target_col < 1:
                raise ValueError('''
*
*   The request column index {0} must be greater than 0.
*   First column is index 1.
*
'''.format(i))
            if target_col > len(tsd.columns):
                raise ValueError('''
*
*   The request column index {0} must be less than the
*   number of columns {1}.
*
'''.format(i, len(tsd.columns)))
            ncolumns.append(target_col - 1)

    if len(ncolumns) == 1:
        return tsutils.printiso(pd.DataFrame(tsd[tsd.columns[ncolumns]]))

    newtsd = pd.DataFrame()
    for index, col in enumerate(ncolumns):
        jtsd = pd.DataFrame(tsd[tsd.columns[col]])

        newtsd = newtsd.join(jtsd,
                             lsuffix='_{0}'.format(index), how='outer')
    return tsutils.printiso(newtsd)


@mando.command
def stdtozrxp(
        rexchange=None,
        input_ts='-',
        start_date=None,
        end_date=None):
    '''
    Prints out data to the screen in a WISKI ZRXP format.

    :param rexchange: The REXCHANGE ID to be written into the zrxp header.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
    if len(tsd.columns) > 1:
        raise ValueError('''
*
*   The "stdtozrxp" command can only accept a single
*   'time-series, instead it is seeing {0}.
*
'''.format(len(tsd.columns)))
    if rexchange:
        print('#REXCHANGE{0}|*|'.format(rexchange))
    for i in range(len(tsd)):
        print(('{0.year:04d}{0.month:02d}{0.day:02d}{0.hour:02d}'
               '{0.minute:02d}{0.second:02d}, {1}').format(
                   tsd.index[i], tsd[tsd.columns[0]][i]))


@mando.command
def tstopickle(
        filename,
        input_ts='-',
        start_date=None,
        end_date=None):
    '''
    Pickles the data into a Python pickled file.  Can be brought back into
    Python with 'pickle.load' or 'numpy.load'.  See also 'tstoolbox read'.

    :param filename <str>: The filename to store the pickled data.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
    pd.core.common.save(tsd, filename)


@mando.command
def accumulate(
        statistic='sum',
        print_input=False,
        input_ts='-',
        start_date=None,
        end_date=None):
    '''
    Calculates accumulating statistics.

    :param statistic <str>: 'sum', 'max', 'min', 'prod', defaults to 'sum'.
    :param -p, --print_input: If set to 'True' will include the input columns
        in the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
    if statistic == 'sum':
        ntsd = tsd.cumsum()
    elif statistic == 'max':
        ntsd = tsd.cummax()
    elif statistic == 'min':
        ntsd = tsd.cummin()
    elif statistic == 'prod':
        ntsd = tsd.cumprod()
    else:
        raise ValueError('''
*
*   Statistic {0} is not implemented.
*
'''.format(statistic))
    return tsutils.print_input(print_input, tsd, ntsd, '_' + statistic)


@mando.command
def rolling_window(
        span=2,
        statistic='mean',
        wintype=None,
        center=False,
        print_input=False,
        input_ts='-',
        start_date=None,
        end_date=None):
    '''
    Calculates a rolling window statistic.

    :param span <int>: The number of previous intervals to include in the
        calculation of the statistic. If `span` is equal to 0 will give an
        expanding rolling window.
    :param statistic <str>: One of 'mean', 'corr', 'count', 'cov', 'kurtosis',
        'median', 'skew', 'stdev', 'sum', 'variance', 'expw_mean',
        'expw_stdev', 'expw_variance' 'expw_corr', 'expw_cov' used to calculate
        the statistic, defaults to 'mean'.
    :param wintype <str>: The 'mean' and 'sum' `statistic` calculation can also
        be weighted according to the `wintype` windows.  Some of the following
        windows require additional keywords identified in parenthesis:
        'boxcar', 'triang', 'blackman', 'hamming', 'bartlett', 'parzen',
        'bohman', 'blackmanharris', 'nuttall', 'barthann', 'kaiser' (needs
        beta), 'gaussian' (needs std), 'general_gaussian' (needs power, width)
        'slepian' (needs width).
    :param center: If set to 'True' the calculation will be made for the
        value at the center of the window.  Default is 'False'.
    :param -p, --print_input: If set to 'True' will include the input columns in
        the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
    if span is None:
        span = len(tsd)
    else:
        span = int(span)
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
    if wintype in window_list and statistic in ['mean', 'sum']:
        meantest = statistic == 'mean'
        newts = pd.stats.moments.rolling_window(
            tsd, span, wintype, center=center, mean=meantest)
    elif statistic == 'mean':
        if span == 0:
            newts = pd.stats.moments.expanding_mean(tsd, center=center)
        else:
            newts = pd.stats.moments.rolling_mean(tsd, span, center=center)
    elif statistic == 'corr':
        if span == 0:
            newts = pd.stats.moments.expanding_corr(tsd, center=center)
        else:
            newts = pd.stats.moments.rolling_corr(tsd, span, center=center)
    elif statistic == 'cov':
        if span == 0:
            newts = pd.stats.moments.expanding_cov(tsd, center=center)
        else:
            newts = pd.stats.moments.rolling_cov(tsd, span, center=center)
    elif statistic == 'count':
        if span == 0:
            newts = pd.stats.moments.expanding_count(tsd, center=center)
        else:
            newts = pd.stats.moments.rolling_count(tsd, span, center=center)
    elif statistic == 'kurtosis':
        if span == 0:
            newts = pd.stats.moments.expanding_kurt(tsd, center=center)
        else:
            newts = pd.stats.moments.rolling_kurt(tsd, span, center=center)
    elif statistic == 'median':
        if span == 0:
            newts = pd.stats.moments.expanding_median(tsd, center=center)
        else:
            newts = pd.stats.moments.rolling_median(tsd, span, center=center)
    elif statistic == 'skew':
        if span == 0:
            newts = pd.stats.moments.expanding_skew(tsd, center=center)
        else:
            newts = pd.stats.moments.rolling_skew(tsd, span, center=center)
    elif statistic == 'stdev':
        if span == 0:
            newts = pd.stats.moments.expanding_std(tsd, center=center)
        else:
            newts = pd.stats.moments.rolling_std(tsd, span, center=center)
    elif statistic == 'sum':
        if span == 0:
            newts = pd.stats.moments.expanding_sum(tsd, center=center)
        else:
            newts = pd.stats.moments.rolling_sum(tsd, span, center=center)
    elif statistic == 'variance':
        if span == 0:
            newts = pd.stats.moments.expanding_var(tsd, center=center)
        else:
            newts = pd.stats.moments.rolling_var(tsd, span, center=center)
    elif statistic == 'expw_mean':
        newts = pd.stats.moments.ewma(tsd, span=span, center=center)
    elif statistic == 'expw_stdev':
        newts = pd.stats.moments.ewmstd(tsd, span=span, center=center)
    elif statistic == 'expw_variance':
        newts = pd.stats.moments.ewmvar(tsd, span=span, center=center)
    elif statistic == 'expw_corr':
        newts = pd.stats.moments.ewmcorr(tsd, span=span, center=center)
    elif statistic == 'expw_cov':
        newts = pd.stats.moments.ewmcov(tsd, span=span, center=center)
    else:
        raise ValueError('''
*
*   Statistic '{0}' is not implemented.
*
'''.format(statistic))
    return tsutils.print_input(print_input, tsd, newts, '_' + statistic)


@mando.command
def aggregate(
        statistic='mean',
        agg_interval='daily',
        ninterval=1,
        start_interval=1,
        print_input=False,
        input_ts='-',
        start_date=None,
        end_date=None):
    '''
    Takes a time series and aggregates to specified frequency, outputs to
        'ISO-8601date,value' format.

    :param statistic <str>: 'mean', 'sum', 'std', 'max', 'min', 'median',
        'first', or 'last' to calculate the aggregation, defaults to 'mean'.
        Can also be a comma separated list of statistic methods.
    :param agg_interval <str>: The 'hourly', 'daily', 'monthly', 'yearly'
        aggregation intervals, defaults to 'daily'.
    :param ninterval <int>: The number of agg_interval to use for the
        aggregation.  Defaults to 1.
    :param -p, --print_input: If set to 'True' will include the input columns in
        the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    aggd = {'hourly': 'H',
            'daily': 'D',
            'monthly': 'M',
            'yearly': 'A'
           }
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
    methods = statistic.split(',')
    newts = pd.DataFrame()
    for method in methods:
        tmptsd = tsd.resample('{0:d}{1}'.format(ninterval,
                                                aggd[agg_interval]),
                                                how=method)
        tmptsd.rename(columns=lambda x: x + '_' + method, inplace=True)
        newts = newts.join(tmptsd, how='outer')
    return tsutils.print_input(print_input, tsd, newts, '')


@mando.command
def clip(
        a_min=None,
        a_max=None,
        start_date=None,
        end_date=None,
        print_input=False,
        input_ts='-'):
    '''
    Returns a time-series with values limited to [a_min, a_max]

    :param -p, --print_input: If set to 'True' will include the input columns in
        the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
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


@mando.command
def add_trend(
        start_offset,
        end_offset,
        start_date=None,
        end_date=None,
        print_input=False,
        input_ts='-'):
    '''
    Adds a trend.

    :param start_offset <float>: The starting value for the applied trend.
    :param end_offset <float>: The ending value for the applied trend.
    :param -p, --print_input: If set to 'True' will include the input columns
        in the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
    ntsd = tsd.copy().astype('f')
    ntsd.ix[:, :] = pd.np.nan
    ntsd.ix[0, :] = float(start_offset)
    ntsd.ix[-1, :] = float(end_offset)
    ntsd = ntsd.interpolate(method='values')
    ntsd = ntsd + tsd
    return tsutils.print_input(
        print_input, tsd, ntsd, '_trend')


@mando.command
def remove_trend(
        start_date=None,
        end_date=None,
        print_input=False,
        input_ts='-'):
    '''
    Removes a 'trend'.

    :param -p, --print_input: If set to 'True' will include the input columns
        in the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
    ntsd = tsd.copy()
    for col in tsd.columns:
        index = tsd.index.astype('l')
        index = index - index[0]
        lin = pd.np.polyfit(index, tsd[col], 1)
        ntsd[col] = lin[0]*index + lin[1]
        ntsd[col] = tsd[col] - ntsd[col]
    return tsutils.print_input(
        print_input, tsd, ntsd, '_rem_trend')


@mando.command
def calculate_fdc(
        x_plotting_position='norm',
        input_ts='-',
        start_date=None,
        end_date=None):
    '''
    Returns the frequency distribution curve.  DOES NOT return a time-series.

    :param x_plotting_position <str>: 'norm' or 'lin'.  'norm' defines a x
        plotting position Defaults to 'norm'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)
    if len(tsd.columns) > 1:
        raise ValueError('''
*
*   This function currently only works with one time-series at a time.
*   You gave it {0}.
*
'''.format(len(tsd.columns)))

    cnt = tsd[tsd.columns[0]].count()
    a_tmp = 1. / (cnt + 1)
    b_tmp = 1 - a_tmp
    if x_plotting_position == 'norm':
        from scipy.stats.distributions import norm
        plotpos = norm.ppf(linspace(a_tmp, b_tmp, cnt))
        xlabel = norm.cdf(plotpos)
    if x_plotting_position == 'lin':
        plotpos = linspace(a_tmp, b_tmp, cnt)
        xlabel = plotpos
    ydata = tsd[tsd.columns[0]].dropna()
    ydata.sort(ascending=False)
    print('Exceedance, Value, Exceedance_Label')
    for xdat, ydat, zdat in zip(plotpos, ydata.values, xlabel):
        print('{0}, {1}, {2}'.format(xdat, ydat, zdat))


@mando.command(formatter_class=RawTextHelpFormatter)
def stack(
        input_ts='-',
        start_date=None,
        end_date=None):
    '''
    Returns the stack of the input table.

    The stack command takes the standard table and converts to a three column
    table.

    From:

    Datetime,TS1,TS2,TS3
    2000-01-01 00:00:00,1.2,1018.2,0.0032
    2000-01-02 00:00:00,1.8,1453.1,0.0002
    2000-01-03 00:00:00,1.9,1683.1,-0.0004

    To:

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


    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)

    newtsd = pd.DataFrame(tsd.stack()).reset_index(1)
    newtsd.sort(['level_1'], inplace=True)
    newtsd.columns = ['Columns', 'Values']
    return tsutils.printiso(newtsd)


@mando.command(formatter_class=RawTextHelpFormatter)
def unstack(
        column_names,
        input_ts='-',
        start_date=None,
        end_date=None):
    '''
    Returns the unstack of the input table.

    The unstack command takes the stacked table and converts to a
    standard tstoolbox table.


    From:

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


    To:

    Datetime,TS1,TS2,TS3
    2000-01-01,1.2,1018.2,0.0032
    2000-01-02,1.8,1453.1,0.0002
    2000-01-03,1.9,1683.1,-0.0004

    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param columns_labels: The column in the table that holds the column
        labels.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.read_iso_ts(input_ts)
    tsd.sort(inplace=True)
    tsd = tsutils.date_slice(tsd,
                             start_date=start_date,
                             end_date=end_date)

    index = [tsd.index.values, tsd[column_names].values]
    cols = list(tsd.columns)
    cols.remove(column_names)
    newtsd = pd.DataFrame(tsd[cols].values, index=index)
    newtsd = newtsd.unstack()
    newtsd.index.name = 'Datetime'
    levels = newtsd.columns.levels
    labels = newtsd.columns.labels
    newtsd.columns = levels[1][labels[1]]
    newtsd.rename(columns=lambda x: ''.join([i for i in x if i not in '\'" ']))
    return tsutils.printiso(newtsd)


mark_dict = {
    ".":"point",
    ",":"pixel",
    "o":"circle",
    "v":"triangle_down",
    "^":"triangle_up",
    "<":"triangle_left",
    ">":"triangle_right",
    "1":"tri_down",
    "2":"tri_up",
    "3":"tri_left",
    "4":"tri_right",
    "8":"octagon",
    "s":"square",
    "p":"pentagon",
    "*":"star",
    "h":"hexagon1",
    "H":"hexagon2",
    "+":"plus",
    "D":"diamond",
    "d":"thin_diamond",
    "|":"vline",
    "_":"hline"
    }

colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w']

@mando.command(formatter_class=RawTextHelpFormatter)
def plot(
        ofilename='plot.png',
        type='time',
        xtitle='',
        ytitle='',
        title='',
        figsize=(10, 6.0),
        legend=None,
        legend_names=None,
        subplots=False,
        sharex=True,
        sharey=False,
        style=None,
        logx=False,
        logy=False,
        xaxis='arithmetic',
        yaxis='arithmetic',
        xlim=None,
        ylim=None,
        secondary_y=False,
        mark_right=True,
        scatter_matrix_diagonal='probability_density',
        bootstrap_size=50,
        bootstrap_samples=500,
        norm_xaxis=False,
        norm_yaxis=False,
        xy_match_line='',
        grid=None,
        input_ts='-',
        start_date=None,
        end_date=None,
        label_rotation=None,
        label_skip=1,
        drawstyle='default'):
    '''
    Plots.

    :param ofilename <str>: Output filename for the plot.  Extension defines the
       type, ('.png'). Defaults to 'plot.png'.
    :param type <str>: The plot type.  Can be 'time', 'xy', 'double_mass',
       'boxplot', 'scatter_matrix', 'lag_plot', 'autocorrelation', 'bootstrap',
       or 'probability_density', 'bar', 'barh', 'bar_stacked', 'barh_stacked',
       'histogram', 'norm_xaxis', 'norm_yaxis'.  Defaults to 'time'.
    :param xtitle <str>: Title of x-axis, defaults depend on ``type``.
    :param ytitle <str>: Title of y-axis, defaults depend on ``type``.
    :param title <str>: Title of chart, defaults to ''.
    :param figsize: The (width, height) of plot as inches.  Defaults to
       (10,6.5).
    :param legend: Whether to display the legend. Defaults to True.
    :param legend_names <str>: Legend would normally use the time-series names
       associated with the input data.  The 'legend_names' option allows you to
       override the names in the data set.  You must supply a comma separated
       list of strings for each time-series in the data set.  Defaults to None.
    :param subplots: boolean, default False.  Make separate subplots for each
       time series
    :param sharex: boolean, default True In case subplots=True, share x axis
    :param sharey: boolean, default False In case subplots=True, share y axis
    :param style <str>: comma separated matplotlib style strings matplotlib line
       style per time-series.  Just combine codes in 'ColorLineMarker' order,
       for example 'r--*' is a red dashed line with star marker.

       Colors - Single Character Codes:
       'b'  blue
       'g'  green
       'r'  red
       'c'  cyan
       'm'  magenta
       'y'  yellow
       'k'  black
       'w'  white
       ---------------------
       Grays - Float:
       '0.75'  0.75 gray
       ---------------------
       Colors - HTML Color Names
       'red'
       'burlywood'
       'chartreuse'
       ...etc.
       Color reference:
       http://matplotlib.org/api/colors_api.html

       Lines
       '-'     solid
       '--'    dashed
       '-.'    dash_dot
       ':'     dotted
       'None'  draw nothing
       ' '     draw nothing
       ''      draw nothing
       Line reference:
       http://matplotlib.org/api/artist_api.html

       Markers
       '.'     point
       'o'     circle
       'v'     triangle down
       '^'     triangle up
       '<'     triangle left
       '>'     triangle right
       '1'     tri_down
       '2'     tri_up
       '3'     tri_left
       '4'     tri_right
       '8'     octagon
       's'     square
       'p'     pentagon
       '*'     star
       'h'     hexagon1
       'H'     hexagon2
       '+'     plus
       'x'     x
       'D'     diamond
       'd'     thin diamond
       '|'     vline
       '_'     hline
       'None'     nothing
       ' '     nothing
       ''     nothing
       Marker reference:
       http://matplotlib.org/api/markers_api.html

    :param logx: boolean, default False
       For line plots, use log scaling on x axis
       DEPRECATED: use '--xaxis="log"' instead.
    :param logy: boolean, default False
       For line plots, use log scaling on y axis
       DEPRECATED: use '--yaxis="log"' instead.
    :param xlim: comma separated lower and upper limits (--xlim 1,1000)
       Limits for the x-axis
    :param ylim: comma separated lower and upper limits (--ylim 1,1000)
       Limits for the y-axis
    :param xaxis <str>: defines the type of the xaxis.  One of 'arithmetic',
       'log'. Default is 'arithmetic'.
    :param yaxis <str>: defines the type of the yaxis.  One of 'arithmetic',
       'log'. Default is 'arithmetic'.
    :param secondary_y: boolean or sequence, default False
       Whether to plot on the secondary y-axis If a list/tuple, which
       time-series to plot on secondary y-axis
    :param mark_right: boolean, default True :
       When using a secondary_y axis, should the legend label the axis of the
       various time-series automatically
    :param scatter_matrix_diagonal <str>: If plot type is 'scatter_matrix', this
       specifies the plot along the diagonal.  Defaults to
       'probability_density'.
    :param bootstrap_size: The size of the random subset for 'bootstrap' plot.
       Defaults to 50.
    :param bootstrap_samples: The number of random subsets of
       'bootstrap_size'.  Defaults to 500.
    :param norm_xaxis: Only available with xy plots.
       Whether the x-axis should be labels with the normal
       distribution common with frequency distribution curves.
       Defaults to False.
       DEPRECATED: use '--type="norm_xaxis"' or '--type="norm_yaxis"' instead.
    :param xy_match_line <str>: Will add a match line where x == y.  Default is
       ''.  Set to a line style code.
    :param grid: boolean, default True
       Whether to plot grid lines on the major ticks.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    :param label_rotation <int>: Rotation for major labels for bar plots.
    :param label_skip <int>: Skip for major labels for bar plots.
    :param drawstyle <str>: 'default' connects the points with lines. The steps
        variants produce step-plots. 'steps' is equivalent to 'steps-pre' and
        is maintained for backward-compatibility.
        ACCEPTS: ['default' | 'steps' | 'steps-pre' | 'steps-mid'
        | 'steps-post']
    '''

    # Need to work around some old option defaults with the implemntation of
    # mando
    if legend == '' or legend == 'True' or legend is None:
        legend = True
    else:
        legend = False

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator

    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts, dense=False),
                             start_date=start_date,
                             end_date=end_date)

    def _know_your_limits(xylimits, axis='arithmetic'):
        '''
        This defines the xlim and ylim as lists rather than strings.
        Might prove useful in the future in a more generic spot.
        It normalizes the different representiations.
        '''
        if isinstance(xylimits, str):
            nlim = []
            for lim in xylimits.split(','):
                if lim == '':
                    nlim.append(None)
                elif '.' in lim:
                    nlim.append(float(lim))
                else:
                    nlim.append(int(lim))
        else:  # tuples or lists...
            nlim = xylimits


        if axis == 'normal':
            if nlim is None:
                nlim = [None, None]
            if nlim[0] is None:
                nlim[0] = 0.01
            if nlim[1] is None:
                nlim[1] = 0.99
            if (nlim[0] <= 0 or nlim[0] >= 1 or
                    nlim[1] <= 0 or nlim[1] >= 1):
                raise ValueError('''
*
*   Both limits must be between 0 and 1 for the
*   'normal' axis.  Instead you have {0}
*
'''.format(nlim))

        if nlim is None:
            return nlim

        if nlim[0] is not None and nlim[1] is not None:
            if nlim[0] >= nlim[1]:
                raise ValueError('''
*
*   The second limit must be greater than the first.
*   You gave {0}.
*
'''.format(nlim))

        if axis == 'log':
            if ((nlim[0] is not None and nlim[0] <= 0) or
                    (nlim[1] is not None and nlim[1] <= 0)):
                raise ValueError('''
*
*   If log plot cannot have limits less than or equal to 0.
*   You have {0}.
*
'''.format(nlim))

        return nlim


    # This is to help pretty print the frequency
    try:
        try:
            pltfreq = str(tsd.index.freq, 'utf-8').lower()
        except TypeError:
            pltfreq = str(tsd.index.freq).lower()
        if pltfreq.split(' ')[0][1:] == '1':
            beginstr = 3
        else:
            beginstr = 1
        # short freq string (day) OR (2 day)
        short_freq = '({0})'.format(pltfreq[beginstr:-1])
    except AttributeError:
        short_freq = ''

    if legend_names:
        lnames = legend_names.split(',')
        if len(lnames) != len(set(lnames)):
            raise ValueError('''
*
*   Each name in legend_names must be unique.
*
''')
        if len(tsd.columns) == len(lnames):
            renamedict = dict(zip(tsd.columns, lnames))
        elif type == 'xy' and len(tsd.columns)//2 == len(lnames):
            renamedict = dict(zip(tsd.columns[2::2], lnames[1:]))
            renamedict[tsd.columns[1]] = lnames[0]
        else:
            raise ValueError('''
*
*   For 'legend_names' you must have the same number of comma
*   separated names as columns in the input data.  The input
*   data has {0} where the number of 'legend_names' is {1}.
*
*   If 'xy' type you need to have legend names as x,y1,y2,y3,...
*
'''.format(len(tsd.columns), len(lnames)))
        tsd.rename(columns=renamedict, inplace=True)
    else:
        lnames = tsd.columns

    if style:
        style = style.split(',')

    if logx is True or logy is True or norm_xaxis is True:
        import warnings
        warnings.warn('''
*
*   The --logx, --logy, and --norm_xaxis  options are deprecated.
*   Use '--xaxis="log" or '--yaxis="log"',
*   or '--type="norm_xaxis"' or '--type="norm_yaxis"'.
*
''')

    if xaxis == 'log':
        logx = True
    if yaxis == 'log':
        logy = True

    if type == 'norm_xaxis':
        xaxis = 'normal'
        if xaxis != 'arithmetic':
            import warnings
            warnings.warn('''
*
*   The --type=norm_xaxis cannot also have the xaxis set to {0}.
*   The {0} setting for xaxis is ignored.
*
'''.format(xaxis))

    if type == 'norm_yaxis':
        yaxis = 'normal'
        if yaxis != 'arithmetic':
            import warnings
            warnings.warn('''
*
*   The --type=norm_yaxis cannot also have the yaxis set to {0}.
*   The {0} setting for yaxis is ignored.
*
'''.format(yaxis))

    xlim = _know_your_limits(xlim, axis=xaxis)
    ylim = _know_your_limits(ylim, axis=yaxis)

    plt.figure(figsize=figsize)
    if type == 'time':
        tsd.plot(legend=legend, subplots=subplots, sharex=sharex,
                 sharey=sharey, style=style, logx=logx, logy=logy, xlim=xlim,
                 ylim=ylim, secondary_y=secondary_y, mark_right=mark_right,
                 figsize=figsize, drawstyle=drawstyle)
        plt.xlabel(xtitle or 'Time')
        plt.ylabel(ytitle)
        if legend is True:
            plt.legend(loc='best')
    elif type in ['xy', 'double_mass', 'norm_xaxis', 'norm_yaxis']:
        # PANDAS was not doing the right thing with xy plots
        # if you wanted lines between markers.
        # Fell back to using raw matplotlib.
        # Boy I do not like matplotlib.
        fig, ax = plt.subplots(figsize=figsize)
        if style is None and type == 'xy':
            style = '*' * len(tsd.columns)
            style = ','.join(style).split(',')  # weird but it works
        if type == 'double_mass':
            tsd = tsd.cumsum()
        if type in ['norm_xaxis', 'norm_yaxis']:
            # scipy is not a PANDAS required library
            from scipy.stats.distributions import norm
            ys = tsd.iloc[:, :]
            colcnt = tsd.shape[1]
        else:
            xs = pd.np.array(tsd.iloc[:, 0::2])
            ys = pd.np.array(tsd.iloc[:, 1::2])
            colcnt = tsd.shape[1]//2
        for colindex in range(colcnt):
            lstyle = style[colindex]
            lcolor = 'b'
            marker = ''
            linest = '-'
            if lstyle[0] in colors:
                lcolor = lstyle[0]
                lstyle = lstyle[1:]
                linest = lstyle
            if lstyle[0] in mark_dict:
                marker = lstyle[0]
                linest = lstyle[1:]

            if type in ['norm_xaxis', 'norm_yaxis']:
                oydata = pd.np.array(ys.iloc[:, colindex].dropna())
                oydata = pd.np.sort(oydata)[::-1]
                n = len(oydata)
                oxdata = norm.ppf(pd.np.linspace(1./(n+1), 1-1./(n+1), n))
                norm_axis = ax.xaxis
            else:
                oxdata = xs[:, colindex]
                oydata = ys[:, colindex]
            if type == 'norm_yaxis':
                oxdata, oydata = oydata, oxdata
                norm_axis = ax.yaxis

            if logy is True and logx is False:
                ax.semilogy(oxdata, oydata,
                            linestyle=linest,
                            color=lcolor,
                            marker=marker,
                            label=lnames[colindex]
                           )
            elif logx is True and logy is False:
                ax.semilogx(oxdata, oydata,
                            linestyle=linest,
                            color=lcolor,
                            marker=marker,
                            label=lnames[colindex]
                           )
            elif logx is True and logy is True:
                ax.loglog(oxdata, oydata,
                          linestyle=linest,
                          color=lcolor,
                          marker=marker,
                          label=lnames[colindex]
                         )
            else:
                ax.plot(oxdata, oydata,
                        linestyle=linest,
                        color=lcolor,
                        marker=marker,
                        label=lnames[colindex],
                        drawstyle=drawstyle
                       )
        if type in ['norm_xaxis', 'norm_yaxis']:
            xtmaj = pd.np.array([0.01, 0.1, 0.5, 0.9, 0.99])
            xtmaj_str = ['1', '10', '50', '90', '99']
            xtmin = pd.np.concatenate([pd.np.linspace(0.001, 0.01, 10),
                                       pd.np.linspace(0.01, 0.1, 10),
                                       pd.np.linspace(0.1, 0.9, 9),
                                       pd.np.linspace(0.9, 0.99, 10),
                                       pd.np.linspace(0.99, 0.999, 10),
                                      ])
            xtmaj = norm.ppf(xtmaj)
            xtmin = norm.ppf(xtmin)
            norm_axis.set_major_locator(FixedLocator(xtmaj))
            norm_axis.set_minor_locator(FixedLocator(xtmin))
            if type == 'norm_xaxis':
                ax.set_xticklabels(xtmaj_str)
                ax.set_xlim(norm.ppf([0.01, 0.99]))
                ax.set_ylim(ylim)
            if type == 'norm_yaxis':
                ax.set_yticklabels(xtmaj_str)
                ax.set_ylim(norm.ppf(ylim))
                ax.set_xlim(xlim)
        if xy_match_line:
            if isinstance(xy_match_line, str):
                xymsty = xy_match_line
            else:
                xymsty = 'g--'
            nxlim = ax.get_xlim()
            nylim = ax.get_ylim()
            maxt = max(nxlim[1], nylim[1])
            mint = min(nxlim[0], nylim[0])
            ax.plot([mint, maxt], [mint, maxt], xymsty, zorder=1)
            ax.set_ylim(nylim)
            ax.set_xlim(nxlim)
        ax.set_xlabel(xtitle or tsd.columns[0])
        ax.set_ylabel(ytitle or tsd.columns[1])
        if legend is True:
            ax.legend(loc='best')
        if type not in ['norm_xaxis', 'norm_yaxis']:
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
    elif type == 'probability_density':
        tsd.plot(kind='kde', legend=legend, subplots=subplots, sharex=sharex,
                 sharey=sharey, style=style, logx=logx, logy=logy, xlim=xlim,
                 ylim=ylim, secondary_y=secondary_y,
                 figsize=figsize)
        plt.xlabel(xtitle)
        plt.ylabel(ytitle or 'Density')
        if legend is True:
            plt.legend(loc='best')
    elif type == 'boxplot':
        tsd.boxplot()
    elif type == 'scatter_matrix':
        from pandas.tools.plotting import scatter_matrix
        if scatter_matrix_diagonal == 'probablity_density':
            scatter_matrix_diagonal = 'kde'
        scatter_matrix(tsd, diagonal=scatter_matrix_diagonal,
                       figsize=figsize)
    elif type == 'lag_plot':
        from pandas.tools.plotting import lag_plot
        lag_plot(tsd,
                 figsize=figsize)
        plt.xlabel(xtitle or 'y(t)')
        plt.ylabel(ytitle or 'y(t+{0})'.format(short_freq or 1))
    elif type == 'autocorrelation':
        from pandas.tools.plotting import autocorrelation_plot
        autocorrelation_plot(tsd,
                             figsize=figsize)
        plt.xlabel(xtitle or 'Time Lag {0}'.format(short_freq))
        plt.ylabel(ytitle)
    elif type == 'bootstrap':
        if len(tsd.columns) > 1:
            raise ValueError('''
*
*   The 'bootstrap' plot can only work with 1 time-series in the DataFrame.
*   The DataFrame that you supplied has {0} time-series.
*
'''.format(len(tsd.columns)))
        from pandas.tools.plotting import bootstrap_plot
        bootstrap_plot(tsd, size=bootstrap_size, samples=bootstrap_samples,
                       color='gray',
                       figsize=figsize)
    elif (type == 'bar' or
          type == 'bar_stacked' or
          type == 'barh' or
          type == 'barh_stacked'
         ):
        stacked = False
        if type[-7:] == 'stacked':
            stacked = True
        kind = 'bar'
        if type[:4] == 'barh':
            kind = 'barh'
        ax = tsd.plot(kind=kind, legend=legend, stacked=stacked,
                      style=style, logx=logx, logy=logy, xlim=xlim,
                      ylim=ylim,
                      figsize=figsize)
        freq = tsutils.asbestfreq(tsd)[1]
        if freq is not None:
            if freq[0] == 'A':
                endchar = 4
            elif freq[0] == 'M':
                endchar = 7
            elif freq[0] == 'D':
                endchar = 10
            elif freq[0] == 'H':
                endchar = 13
            else:
                endchar = None
            nticklabels = []
            if kind == 'bar':
                taxis = ax.xaxis
            else:
                taxis = ax.yaxis
            for index, i in enumerate(taxis.get_majorticklabels()):
                if index % label_skip:
                    nticklabels.append(' ')
                else:
                    nticklabels.append(i.get_text()[:endchar])
            taxis.set_ticklabels(nticklabels)
            plt.setp(taxis.get_majorticklabels(), rotation=label_rotation)
        plt.xlabel(xtitle)
        plt.ylabel(ytitle)
        if legend is True:
            plt.legend(loc='best')
    elif type == 'histogram':
        tsd.hist(figsize=figsize)
        plt.xlabel(xtitle)
        plt.ylabel(ytitle)
        if legend is True:
            plt.legend(loc='best')
    else:
        raise ValueError('''
*
*   Plot 'type' {0} is not supported.
*
'''.format(type))

    if grid is None:
        grid = True
    else:
        grid = False
    plt.grid(grid)
    plt.title(title)
    plt.savefig(ofilename)


def _dtw(ts_a, ts_b, d=lambda x, y: abs(x-y), window=10000):
    """Returns the DTW similarity distance between two 2-D
    timeseries numpy arrays.

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
        cost[i, 0] = cost[i-1, 0] + d(ts_a[i], ts_b[0])

    for j in range(1, N):
        cost[0, j] = cost[0, j-1] + d(ts_a[0], ts_b[j])

    # Populate rest of cost matrix within window
    for i in range(1, M):
        for j in range(max(1, i - window),
                       min(N, i + window)):
            choices = cost[i - 1, j - 1], cost[i, j-1], cost[i-1, j]
            cost[i, j] = min(choices) + d(ts_a[i], ts_b[j])

    # Return DTW distance given window
    return cost[-1, -1]

@mando.command
def dtw(window=10000,
        input_ts='-',
        start_date=None,
        end_date=None):
    '''Dynamic Time Warping'''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts, dense=True),
                             start_date=start_date,
                             end_date=end_date)

    process = {}
    for i in tsd.columns:
        for j in tsd.columns:
            if (i, j) not in process and (j, i) not in process and i != j:
                process[(i, j)] = _dtw(tsd[i], tsd[j], window=window)

    print(process.keys())

    ntsd = pd.DataFrame(process.values(), process.keys())
    return tsutils.printiso(ntsd)

@mando.command
def pca(n_components=None,
        input_ts='-',
        start_date=None,
        end_date=None):
    '''
    Returns the principal components analysis of the time series.  Does not
    return a time-series.

    :param n_components <int>: The number of groups to separate the time series
        into.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    from sklearn.decomposition import PCA

    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)

    pca = PCA(n_components)
    pca.fit(tsd.dropna(how='any'))
    print(pca.components_)


@mando.command
def normalization(mode='minmax',
                  min_limit=0,
                  max_limit=1,
                  pct_rank_method='average',
                  print_input=False,
                  float_format='%g',
                  input_ts='-',
                  start_date=None,
                  end_date=None):
    '''
    Returns the normalization of the time series.

    :param mode <str>: 'minmax' or 'zscore'.  Default is 'minmax'
        'minmax' is min_limit + (X-Xmin)/(Xmax-Xmin)*(max_limit - min_limit)
        'zscore' is X-mean(X)/stddev(X)
        'pct_rank' is rank(X)*100/N
    :param min_limit <float>: Defaults to 0.  Defines the minimum limit of
        the minmax normalization.
    :param max_limit <float>: Defaults to 1.  Defines the maximum limit of
        the minmax normalization.
    :param pct_rank_method <str>: Defaults to 'average'.  Defines how tied
        ranks are broken.  Can be 'average', 'min', 'max', 'first', 'dense'.
    :param -p, --print_input: If set to 'True' will include the input
        columns in the output table.  Default is 'False'.
    :param -i, --input_ts <str>: Filename with data in 'ISOdate,value' format
        or '-' for stdin.
    :param -s, --start_date <str>: The start_date of the series in ISOdatetime
        format, or 'None' for beginning.
    :param -e, --end_date <str>: The end_date of the series in ISOdatetime
        format, or 'None' for end.
    '''
    tsd = tsutils.date_slice(tsutils.read_iso_ts(input_ts),
                             start_date=start_date,
                             end_date=end_date)

    # Trying to save some memory
    if print_input:
        otsd = tsd.copy()
    else:
        otsd = pd.DataFrame()

    if mode == 'minmax':
        tsd = (min_limit +
               (tsd - tsd.min())/
               (tsd.max() - tsd.min())*
               (max_limit - min_limit))
    elif mode == 'zscore':
        tsd = (tsd - tsd.mean())/tsd.std()
    elif mode == 'pct_rank':
        tsd = tsd.rank(method=pct_rank_method, pct=True)
    else:
        raise ValueError('''
*
*   The 'mode' options are 'minmax', 'zscore', or 'pct_rank', you gave me
*   {0}.
*
'''.format(mode))

    return tsutils.print_input(print_input, otsd, tsd, '_{0}'.format(mode),
                               float_format=float_format)


def main():
    ''' Main '''
    if not os.path.exists('debug_tstoolbox'):
        sys.tracebacklimit = 0
    mando.main()
