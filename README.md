# csspy

csspy is a simple package for reading centers for seismic studies event
format (v 3.0). csspy is not real polished, nor do I plan to aggressively
maintain it, but you may find it useful for extracting event information from
the ANF catalog (http://anf.ucsd.edu/tools/events/) as dataframes or obspy
Catalog objects. 

## Installation

csppy requires python 3.6. You can install csspy using pip + git

```bash
$ pip install git+https://github.com/d-chambers/csspy
```

## Quickstart

Supposing you have downloaded and extracted the ANF catalog from 2007_08.
You should now have a file called "events_usarray_2007_08" in your current
directory. As an example we will extract the events associated with the 
[Crandall Canyon mine collapse](https://en.wikipedia.org/wiki/Crandall_Canyon_Mine)

```python
from pathlib import Path

import obspy

import csspy


# get a path object pointing to the catalog directory
path = Path("events_usarray_2007_08")

# load data into a dict of dataframes (if you are wanting css 3.0 format)
df_dict = csspy.dir_to_df(path)

# filter by day and location
t1 = obspy.UTCDateTime('2007-08-06')
t2 = obspy.UTCDateTime('2007-08-08')
latmin = 39.4
latmax = 39.53
lonmin = -111.29
lonmax = -111.07

df_dict = csspy.dir_to_df(path, starttime=t1, endtime=t2, 
                          minlatitude=latmin, maxlatitude=latmax,
                          minlongitude=lonmin, maxlongitude=lonmax)

# convert to an obspy catalog (still a bit rough)
cat = csspy.css_to_catalog(df_dict) 

# now you can fill any missing network codes or location codes
network = 'TA'
location = '--'

cat = csspy.set_seed_defaults(cat, network=network, location=location)

print(cat)

cat.plot(projection='local')

```
