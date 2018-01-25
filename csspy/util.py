"""
Utility functions for csspy
"""

from functools import wraps

from obspy import UTCDateTime as UTC
from obspy.core import event as oe


RID_CACHE = {}
INSTANCE_CACHE = {}


def _get_seed_str(ser):
    """ get a seed string from an arrival row """
    channel = ser.get('chan', '')
    split = channel.replace('-', '_').split('_')
    if len(split) == 2:
        channel, location = split
    else:
        channel, location = channel, ''
    station = ser.get('sta', '')
    network = ser.get('network', '')
    return '.'.join([network, station, location, channel])


def str_of_int_input(func):
    """ decorator to ensure string input to function """

    @wraps(func)
    def wrap(one_arg):
        if isinstance(one_arg, float):
            one_arg = int(one_arg)
        if not isinstance(one_arg, str):
            one_arg = str(one_arg)
        return func(one_arg)

    return wrap


@str_of_int_input
def rid(some_id):
    if some_id not in RID_CACHE:
        RID_CACHE[some_id] = oe.ResourceIdentifier(some_id)
    return RID_CACHE[some_id]


@str_of_int_input
def get_object(some_id):
    return RID_CACHE[some_id].get_referred_object()


def timestamp(obj):
    return UTC(obj).timestamp if obj is not None else None


def get_instances(obj, cls, ids=None):
    """ recurse obj and return a list of instances contained """
    out = []
    ids = ids or set()

    if id(obj) in ids:
        return []

    if (id(obj), cls) in INSTANCE_CACHE:
        return INSTANCE_CACHE[(id(obj), cls)]

    ids.add(id(obj))

    if isinstance(obj, cls):
        out.append(obj)
    if hasattr(obj, '__dict__'):
        for item, val in obj.__dict__.items():
            out += get_instances(val, cls, ids)
    if isinstance(obj, (list, tuple)):
        for val in obj:
            out += get_instances(val, cls, ids)

    INSTANCE_CACHE[(id(obj), cls)] = out

    return out


def set_seed_defaults(catalog, network=None, station=None, location=None,
                      channel=None):
    """
    Fill all blank waveform_id values with those provided (if provided).
    """
    newcodes = {'network_code': network, 'station_code': station,
                'location_code': location, 'channel_code': channel}
    catalog = catalog.copy()  # dont mutate original catalog

    for wid in get_instances(catalog, oe.WaveformStreamID):
        updates = {nc: wid.__dict__[nc] or newcodes[nc] for nc in newcodes
                   if (wid.__dict__ or nc[wid])}
        if updates:
            wid.__dict__.update(updates)

    return catalog
