#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    Copyright (c) 2016, Philipp Meier
#
#    This file is part of the Hydra Platform ShapefileApp (HydraShapefileApp).
#
#    HydraShapefileApp is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by the
#    Free Software Foundation, either version 3 of the License, or (at your
#    option) any later version.
#
#    HydraShapefileApp is distributed in the hope that it will be useful, but
#    WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
#    or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
#    for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with HydraShapefileApp.  If not, see <http://www.gnu.org/licenses/>.


import os
import sys
import json
import warnings

if sys.version.startswith('2'):
    import urllib as ul
    import urllib2 as ul2
elif sys.version.startswith('3'):
    import urllib.parse as ul
    import urllib.request as ul2


def wkt_lookup(searchstring):
    baseurl = 'http://prj2epsg.org/search.json?'
    searchstring = ul.urlencode({'terms': searchstring})

    try:
        result = ul2.urlopen(baseurl + searchstring, timeout=10)
        epsg_json = result.read()
        return json.loads(epsg_json.decode('utf-8'))
    except ul2.URLError:
        return None


def prj2epsg(prjfile):
    prjfile = os.path.abspath(os.path.expanduser(prjfile))
    prj = open(prjfile)
    response = wkt_lookup(prj.read())
    prj.close()

    if response is None:
        return None

    if not response[u'exact']:
        warnings.warn('No unique result found.')

    epsg = dict()
    epsg['epsg'] = []
    for code in response[u'codes']:
        try:
            epsg['epsg'].append(int(code[u'code']))
        except ValueError:
            warnings.warn('Invalid EPSG data retrieved.')
    return epsg
