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

sys.path.append(os.path.sep.join(['..', '..', '..', 'lib']))

from hydra_network import HydraNetworkTree
from shapefile_lib import ShapefileApp

from app_interface import import_parser


if __name__ == '__main__':
    parser = import_parser()
    args = parser.parse_args()

    if args.print_tree:
        tree = HydraNetworkTree(url=args.url, username=args.user,
                                password=args.password)
        tree.get_tree()
        tree.print_tree()
    else:
        importer = ShapefileApp(url=args.url, username=args.user,
                                password=args.password)
        importer.login()

    if args.input_links is not None:
        # Import network from shapefile
        importer.from_shp(args.input_links, args.input_nodes)
