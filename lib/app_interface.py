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


import argparse as ap


def export_parser():
    parser = ap.ArgumentParser(prog='ShapefileApp.py', description="""
Export Hydra Platform networks to a set of ArgGIS shapefiles.

Written by Philipp Meier <philipp.meier@eawag.ch>

(c) Copyright 2015, 2016
Eawag: Swiss Federal Institute of Aquatic Science and Technology
""", formatter_class=ap.RawDescriptionHelpFormatter)

    parser.add_argument('-o', '--output',
                        help="""Folder to which the shapefiles are saved. If
                        the folder does not exist, it will be created.
                        """)
    parser.add_argument('-n', '--network-id',
                        help="""HydraPlatform network ID.""")
    parser.add_argument('-s', '--scenario-id',
                        help="""HydraPlatform scenario ID.""")
    parser.add_argument('-url', '--url',
                        help="""URL of HydraPlatform server (defaults to value
                        specified in the config file.""")
    parser.add_argument('-u', '--user',
                        help="Username to log in to Hydra Platform server.")
    parser.add_argument('-p', '--password',
                        help="Password to log in to Hydra Platform server.")
    parser.add_argument('-t', '--print-tree', action='store_true',
                        help="""Print the project-network-scenario tree of the
                        HydraPlatform database,
                        """)
    parser.add_argument('-x', '--overwrite', action='store_true',
                        help="Overwrite existing shapefiles on export.")

    return parser


def import_parser():
    parser = ap.ArgumentParser(prog='ShapefileApp.py', description="""
Import a set of ArgGIS shapefiles into Hydra Platform.

Written by Philipp Meier <philipp.meier@eawag.ch>

(c) Copyright 2015, 2016
Eawag: Swiss Federal Institute of Aquatic Science and Technology
""", formatter_class=ap.RawDescriptionHelpFormatter)

    parser.add_argument('-in', '--input-nodes', nargs='+',
                        help="Input shapefile containing nodes.")
    parser.add_argument('-il', '--input-links', nargs='+',
                        help="Input shapefile containing links.")
    parser.add_argument('-url', '--url',
                        help="""URL of HydraPlatform server (defaults to value
                        specified in the config file.""")
    parser.add_argument('-u', '--user',
                        help="Username to log in to Hydra Platform server.")
    parser.add_argument('-p', '--password',
                        help="Password to log in to Hydra Platform server.")
    parser.add_argument('-t', '--print-tree', action='store_true',
                        help="""Print the project-network-scenario tree of the
                        HydraPlatform database,
                        """)

    return parser
