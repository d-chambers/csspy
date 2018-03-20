"""
Core module for reading CSS 3.0 event format
"""
import operator
from functools import lru_cache, reduce
from pathlib import Path
from typing import Union, Optional, Dict

import numpy as np
import obspy
import obspy.core.event as oe
import pandas as pd
from obspy import UTCDateTime as UTC

import csspy.specs as specs
from csspy.util import _get_seed_str, rid, get_object, timestamp

SPEC_COLUMNS = ('name', 'field', 'db_type', 'file_type', 'start', 'stop')


# ---------------------- Dataframe functions


@lru_cache()
def _get_read_fwf_kwargs(spec):
    """ return kwargs for passing to read_fwf """
    spec_tuple = getattr(specs, spec)
    df = pd.DataFrame(list(spec_tuple), columns=SPEC_COLUMNS)
    # account for python's 0 indexing
    df['start'] -= 1
    cspec = [tuple(x) for x in df[['start', 'stop']].to_records(index=False)]
    names = df.name.values
    return dict(names=names, colspecs=cspec, header=None)


def file_to_df(path: Union[str, Path], file_type: Optional[str] = None
               ) -> pd.DataFrame:
    """
    Read a file's contents into a dataframe.

    Parameters
    ----------
    path
        Str to a file or Path object pointing to the file to read, or str
    file_type

    Returns
    -------

    """
    path = Path(path)
    # try to determine file type from extention
    if file_type is None:
        if '.' not in path.name:
            raise ValueError(f'could not determine file type for {path}')
        file_type = path.name.split('.')[-1]
    # get the spec for this file and return dataframe
    kwargs = _get_read_fwf_kwargs(file_type)
    df = pd.read_fwf(path, **kwargs)
    return df


def _in_rage(df, column, min_value, max_value, func=None):
    """ return a boolean dataframe if condition is true """
    if min_value is None and max_value is None:
        return pd.Series(np.ones(len(df)), index=df.index).astype(bool)
    min_value = min_value or -np.inf
    max_value = max_value or np.inf
    ser = df[column] if func is None else func(df)
    return (ser > min_value) & (ser < max_value)


def _select_on_events(event_ids, df_dict):
    """ given a sequence of event_ids, filter df_dict """

    event = df_dict['event'][df_dict['event']['evid'].isin(event_ids)]
    origin = df_dict['origin'][df_dict['origin']['evid'].isin(event_ids)]
    origerr = df_dict['origerr'][df_dict['origerr']['orid'].isin(origin.orid)]
    assoc = df_dict['assoc'][df_dict['assoc']['orid'].isin(origin.orid)]
    arrival = df_dict['arrival'][df_dict['arrival']['arid'].isin(assoc.arid)]

    stamag = df_dict['stamag'][df_dict['stamag']['orid'].isin(origin.orid)]
    netmag = df_dict['netmag'][df_dict['netmag']['orid'].isin(origin.orid)]

    loc = locals()
    return {key: loc[key] for key in df_dict}


def filter_df_dict(df_dict, starttime=None, endtime=None, minlatitude=None,
                   maxlatitude=None, minlongitude=None, maxlongitude=None,
                   mindepth=None, maxdepth=None,
                   minmagnitude=None, maxmagnitude=None, magnitudetype=None,
                   eventid=None, limit=None, updatedafter=None):
    """
    Apply filters to the dict of dfs.
    """
    # get a dataframe with all info for filtering
    eve = df_dict['event']
    df = eve.merge(df_dict['origin'], left_on='prefor', right_on='orid',
                   how='left')
    df[df == 999.0] = np.NaN  # Nan out invalid values
    mag_type = magnitudetype or 'ml'

    # apply filters through reductions
    reduce_list = [
        (df, 'lat', minlatitude, maxlatitude),
        (df, 'lon', minlongitude, maxlongitude),
        (df, 'time', timestamp(starttime), timestamp(endtime)),
        (df, 'depth', mindepth, maxdepth, lambda x: x['depth'] * 1000),
        (df, 'lddate', timestamp(updatedafter), None),
        (df, mag_type, minmagnitude, maxmagnitude),
    ]
    conditions = [_in_rage(*x) for x in reduce_list]
    df = df[reduce(operator.and_, conditions)]
    # misc filters
    if eventid is not None:
        if hasattr(eventid, '__len__') and not isinstance(eventid, str):
            df = df[df.evid_x.isin(eventid)]
        else:
            df = df[df.evid_x == eventid]
    if limit:
        df = df.iloc[:limit]
    return _select_on_events(df.evid_x, df_dict)


def dir_to_df(path: Union[Path, str], **kwargs) -> Dict[str, pd.DataFrame]:
    """
    Convert a directory of css 3.0 files to a dictionary of dataframes.

    Parameters
    ----------
    path
        The path to the directory.
    kwargs
        Any filter parameters to apply, see csspy.core.filter_df_dict.

    """
    path = Path(path)
    assert path.is_dir(), f'{path} is not a directory'
    out = {}
    # iter each contained file, return dict of DFs
    for file in path.rglob('*'):
        if '.' in file.name:
            ext = file.name.split('.')[-1]
            out[ext] = file_to_df(file)
    if kwargs:
        out = filter_df_dict(out, **kwargs)
    return out


# --------------------------- catalog functions


def _create_event(ser):
    """ create an event from a row from the event dataframe """
    event = oe.Event(
        resource_id=rid(ser.evid),
        creation=oe.CreationInfo(agency_id=ser.auth, creation_time=UTC(ser.lddate)),
        preferred_origin_id=str(ser.prefor),
    )
    return event


def _create_origin(ser):
    """ create an origin and attach to event """
    event = get_object(ser.evid)

    origin = oe.Origin(
        resource_id=rid(ser.orid),
        time=UTC(ser.time),
        latitude=ser.lat,
        longitude=ser.lon,
        depth=ser.depth * 1000,  # convert to m
    )
    # temporarily attach event reference to origin
    origin.__dict__['event'] = event

    event.origins.append(origin)


def _create_origin_quality(ser):
    """ create origing quality/error and attach to origin """
    origin = get_object(ser.orid)

    ser = ser[ser > 0]  # remove unfilled values

    # create origin quality object
    oq = oe.OriginQuality(
        standard_error=ser.get('sdobs'),
    )

    origin.quality = oq


def _create_pick(ser):
    """ create picks """
    ser = ser[(ser != -1) & ~(ser.isnull())]

    co = oe.CreationInfo(
        agencey_idr=ser.get('auth'),
        creation_time=UTC(ser.get('lddate')),
    )

    seed_str = _get_seed_str(ser)

    wid = oe.WaveformStreamID(seed_string=seed_str)

    pick = oe.Pick(
        time=UTC(ser.time),
        resource_id=rid(ser.arid),
        creation_info=co,
        waveform_id=wid,
    )
    return pick


def _create_arrival(ser):
    origin = get_object(ser.orid)

    arrival = oe.Arrival(
        pick_id=rid(ser.arid),
        time_residual=ser.timeres,
        time_weight=ser.wgt,
        azimuth=ser.esaz,
        phase=ser.phase,
        distance=ser.delta,
    )

    origin.arrivals.append(arrival)


def _create_magnitude(ser):
    """ create magnitude objects """
    event = get_object(ser.evid)

    creation_info = oe.CreationInfo(
        creation_time=timestamp(ser.lddate),
        agency_id=ser.auth,
    )

    errors = oe.QuantityError(
        uncertainty=ser.uncertainty,
    )

    magnitude = oe.Magnitude(
        origin_id=str(ser.orid),
        mag=ser.magnitude,
        magnitude_type=ser.magtype,
        station_count=ser.nsta,
        creation_info=creation_info,
        mag_errors=errors,
    )
    event.magnitudes.append(magnitude)


# def _create_stationmag(ser):
#     """ create station magnitudes """
#
#     creation_info = oe.CreationInfo(
#         creation_time=timestamp(ser.lddate),
#         agency_id=ser.auth,
#     )
#
#     stamag = oe.StationMagnitude(
#
#     )

def attach_picks(event):
    pick_ids = set()
    for origin in event.origins:
        for arrival in origin.arrivals:
            pick_ids.add(arrival.pick_id)
    picks = sorted([get_object(x.id) for x in pick_ids],
                   key=lambda x: x.time)
    event.picks = picks


def css_to_catalog(method: Union[dict, str, Path], **kwargs) -> obspy.Catalog:
    """
    Convert a CSS 3.0 directory or dict of dataframes to a catalog.

    Parameters
    ----------
    method
        A path to a css 3.0 directory or a dict of dataframes create with
        dir_to_df.

    Returns
    -------
    obspy.Catalog
    """
    if isinstance(method, dict):
        df_dict = method
    else:
        df_dict = dir_to_df(method)
    if kwargs:
        df_dict = filter_df_dict(df_dict, **kwargs)
    # get events
    events = df_dict['event'].apply(_create_event, axis=1)
    df_dict['origin'].apply(_create_origin, axis=1)
    df_dict['origerr'].apply(_create_origin_quality, axis=1)
    _ = df_dict['arrival'].apply(_create_pick, axis=1)
    df_dict['assoc'].apply(_create_arrival, axis=1)
    df_dict['netmag'].apply(_create_magnitude, axis=1)
    # df_dict['stamag'].apply(_create_stationmag, axis=1)
    # attach pick to catalog
    for event in events:
        attach_picks(event)
    return oe.Catalog(events=list(events.values))
