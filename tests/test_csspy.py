"""
Test for converting a directory of css 3.0 files to a dict of dataframes
"""

import obspy
import obspy.core.event as oe
import pandas as pd
import pytest

import csspy
from csspy.core import filter_df_dict as df_filt
from csspy.util import get_instances


# ----------------- fixtures


@pytest.fixture(scope='session')
def directory_df_dict():
    """ return a dict of all files in test directory converted to dfs """
    return csspy.dir_to_df(pytest.anf_dir)


@pytest.fixture(scope='session')
def catalog():
    t1 = obspy.UTCDateTime('2007-08-06')
    t2 = obspy.UTCDateTime('2007-08-07')
    return csspy.css_to_catalog(pytest.anf_dir, starttime=t1, endtime=t2)


# ------------------ tests


class TestDirToDataFrames:

    # tests
    def test_dict_outputs(self, directory_df_dict):
        """ ensure passing a directory produces a dict of dataframes for each
        table type """
        assert isinstance(directory_df_dict, dict)

        for name, df in directory_df_dict.items():
            assert isinstance(df, pd.DataFrame)
            assert not df.empty


class TestFilterDataFrames:
    """ tests for filtering """

    # test
    def test_limit(self, directory_df_dict):
        """ ensure event number can be limited """
        limit = 10
        filt = df_filt(directory_df_dict, limit=limit)
        assert len(filt['event']) == limit

    def test_id_number(self, directory_df_dict):
        """ ensure events can be filtered on ids """
        df = directory_df_dict['event']
        eventid = df.evid.iloc[0]
        df2 = df_filt(directory_df_dict, eventid=eventid)['event']
        assert len(df2) == 1
        assert df2.iloc[0]['evid'] == eventid

    def test_id_sequence(self, directory_df_dict):
        """ ensure events can be filtered on sequence of ids """
        df = directory_df_dict['event']
        eventids = df.evid.values[:15]
        df2 = df_filt(directory_df_dict, eventid=eventids)['event']
        assert len(df2) == len(eventids)
        assert set(df2.evid) == set(eventids)


class TestCatalog:
    """ tests for reading css directories into catalogs """

    # tests
    def test_catalog_type(self, catalog):
        """ ensure a catalog was returned """
        assert isinstance(catalog, obspy.Catalog)

    def test_each_event_has_origin(self, catalog):
        """ ensure each event has an origin """
        for eve in catalog:
            assert len(eve.origins)

    def test_has_origins(self, catalog):
        """ ensure origins are there """
        origins = get_instances(catalog, oe.Origin)
        assert len(origins) >= len(catalog)

        assert all([eve.origins for eve in catalog])

        for origin in origins:
            assert len(origin.arrivals)
            assert origin.latitude
            assert origin.longitude

    def test_has_picks(self, catalog):
        """ ensure the catalog has picks and that they are valid """
        picks = get_instances(catalog, oe.Pick)
        for pick in picks:
            assert pick.time
            assert pick.waveform_id

    def test_waveform_ids(self, catalog):
        """ ensure waveform ids at least have station codes """
        wids = get_instances(catalog, oe.WaveformStreamID)
        for wid in wids:
            assert len(wid.channel_code) == 3


class TestFillDefaults:
    """ tests for filling default values of catalog """

    # fixtures
    @pytest.fixture(scope='class')
    def filled_catalog(self, catalog):
        csspy.set_seed_defaults(catalog, network='TA', location='00')

    # tests
    def test_wids(self, filled_catalog):
        """ ensure there are no None values in wids now """
        wids = get_instances(filled_catalog, oe.WaveformStreamID)
        for wid in wids:
            assert getattr(wid, 'network_code') is not None
            assert getattr(wid, 'station_code') is not None
            assert getattr(wid, 'location_code') is not None


class TestQuickStart:
    """ test the code in the quickstart section of readme """

    # fixtures
    @pytest.fixture(scope='class')
    def filtered_df(self, directory_df_dict):
        """ return the dataframe dict filtered to Crandall """

        t1 = obspy.UTCDateTime('2007-08-06')
        t2 = obspy.UTCDateTime('2007-08-08')
        latmin = 39.4
        latmax = 39.53
        lonmin = -111.29
        lonmax = -111.07
        df_dict = df_filt(directory_df_dict, starttime=t1, endtime=t2,
                          minlatitude=latmin, maxlatitude=latmax,
                          minlongitude=lonmin, maxlongitude=lonmax)
        return df_dict

    @pytest.fixture(scope='class')
    def catalog(self, filtered_df):
        """ convert to an obspy catalog """
        return csspy.css_to_catalog(filtered_df)

    @pytest.fixture(scope='class')
    def filled_catalog(self, catalog):
        """ fill the catalogs waveform_ids with default location/station """
        return csspy.set_seed_defaults(catalog, network='TA', location='00')

    # tests
    def test_string(self, catalog):
        """ ensure the catalog can be rep. as a string """
        try:
            str(catalog)
        except Exception:
            pytest.fail('catalog cannot be displayed')

    def test_fill_sid_values(self, filled_catalog):
        """ ensure values in wids were filled """
        for wid in get_instances(filled_catalog, oe.WaveformStreamID):
            assert wid.channel_code is not None
            assert wid.network_code == 'TA'
