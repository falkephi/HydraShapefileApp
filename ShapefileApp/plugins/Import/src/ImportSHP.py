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
import json
import warnings

import argparse as ap

from osgeo import ogr
from osgeo import osr
from datetime import datetime

from GIS.epsg_lookup import prj2epsg

from HydraLib.PluginLib import temp_ids

from HydraLib.PluginLib.resources import HydraResource
#from HydraLib.PluginLib import HydraAttribute
from HydraLib.PluginLib import JsonConnection
from HydraLib.PluginLib import HydraPluginError


class HydraNetwork(HydraResource):

    def __init__(self, url=None, username=None, password=None):
        super(HydraNetwork, self).__init__()
        self.conn = JsonConnection(url=url, app_name='ShapefileApp')
        self.url = url
        self.username = username
        self.password = password
        self.session_id = None
        self.project = None
        self.hydra_network = None
        self.hydra_scenario = None
        self.hydra_attributes = None

        self.attrs = dict()
        self.attr_ids = dict()
        self.epsg = None
        self.nodes = dict()
        self.links = []

        self.link_names = dict()
        self.node_names = dict()

        self._node_coord_index = dict()

    def login(self):
        if self.username is not None and self.password is not None:
            self.session_id = self.conn.login(username=self.username,
                                              password=self.password)
        else:
            self.session_id = self.conn.login()

    def load_attributes(self):
        self.hydra_attributes = self.conn.call('get_all_attributes', {})
        for attr in self.hydra_attributes:
            self.attrs[attr.id] = attr
            self.attr_ids[attr.name] = attr.id

    def load_network(self, network_id, scenario_id):
        """Load a network from HydraPlatform.
        """
        if self.project is None:
            self.load_project(network_id=network_id)

        self.hydra_network = self.conn.call('get_network',
                                            {'network_id': network_id,
                                             'include_data': 'Y'})

        self.load_attributes()

        for scenario in self.hydra_network['scenarios']:
            if scenario['id'] == scenario_id:
                self.hydra_scenario = scenario
                break

        res_scen_dict = dict()
        for res_scen in self.hydra_scenario['resourcescenarios']:
            res_scen_dict.update({res_scen['resource_attr_id']: res_scen})

        # Create node index
        node_dict = dict()
        for node in self.hydra_network['nodes']:
            node_dict.update({node['id']: node})

        self.name = self.hydra_network['name']
        self.description = self.hydra_network['description']

        if 'projection' in self.hydra_network.keys():
            try:
                self.epsg = \
                    int(self.hydra_network['projection'].split(':')[1])
            except ValueError:
                warnings.warn('Could not load EPSG code.')

        # Add network attributes
        for res_attr in self.hydra_network['attributes']:
            if res_scen_dict.get(res_attr['id']) is not None:
                res_scen = res_scen_dict[res_attr['id']]
                self.add_attribute(self.attrs[res_attr['attr_id']],
                                   res_attr, res_scen)
            else:
                self.add_attribute(self.attrs[res_attr['attr_id']],
                                   res_attr, None)

        # Add nodes and attributes
        for node in self.hydra_network['nodes']:
            n_node = HydraNode(x=float(node['x']), y=float(node['y']))
            n_node.name = node['name']
            n_node.layout = node['layout']
            n_node.id = node['id']
            n_node.types = node['types']
            for res_attr in node['attributes']:
                if res_scen_dict.get(res_attr['id']) is not None:
                    res_scen = res_scen_dict[res_attr['id']]
                    n_node.add_attribute(self.attrs[res_attr['attr_id']],
                                         res_attr, res_scen)
                else:
                    n_node.add_attribute(self.attrs[res_attr['attr_id']],
                                         res_attr, None)
            self.add_node(n_node)

        # Add segments and attributes
        for link in self.hydra_network['links']:
            n_link = HydraLink(start_node=self.nodes[link['node_1_id']],
                               end_node=self.nodes[link['node_2_id']])
            n_link.name = link['name']
            n_link.layout = link['layout']
            n_link.id = link['id']
            n_link.types = link['types']
            for res_attr in link['attributes']:
                if res_scen_dict.get(res_attr['id']) is not None:
                    res_scen = res_scen_dict[res_attr['id']]
                    n_link.add_attribute(self.attrs[res_attr['attr_id']],
                                         res_attr, res_scen)
                else:
                    n_link.add_attribute(self.attrs[res_attr['attr_id']],
                                         res_attr, None)

            self.add_link(n_link)

    def load_project(self, project_id=None, network_id=None):
        """Load a project by its ID or by a network ID.
        """
        if project_id is not None:
            self.project = self.conn.call('get_project',
                                          {'project_id': project_id})
        elif network_id is not None:
            self.project = self.conn.call('get_network_project',
                                          {'network_id': network_id})

    def create_project(self, name=None):
        self.project = dict()
        if name is not None:
            self.project['name'] = name
        else:
            self.project['name'] = "Shapefile import @ %s" % datetime.now()
        self.project['description'] = ''
        self.project['status'] = 'A'
        self.project = self.conn.call('add_project',
                                      {'project': self.project})

    def add_node(self, node):
        if self.node_names.get(node.name.lower()) is not None:
            add_string = ' (%s)' % self.node_names[node.name.lower()]
            self.node_names[node.name.lower()] += 1
            node.name += add_string
        else:
            self.node_names[node.name.lower()] = 1
        self.nodes[node.id] = node
        self._node_coord_index[(node.x, node.y)] = node.id

    def add_link(self, link):
        if self.link_names.get(link.name.lower()) is not None:
            add_string = ' (%s)' % self.link_names[link.name.lower()]
            self.link_names[link.name.lower()] += 1
            link.name += add_string
        else:
            self.link_names[link.name.lower()] = 1
        self.links.append(link)

    def save_network(self, network_name=None, project_name=None):
        """Save the network to HydraPlatform server.
        """
        if self.project is None:
            self.create_project(name=project_name)
        self.hydra_network = dict()
        self.hydra_scenario = dict()
        self.hydra_scenario['name'] = 'Scenario created by ShapefileApp'
        self.hydra_scenario['description'] = \
            'Standard scenario created by ShapefileApp.'
        self.hydra_scenario['id'] = -1
        self.hydra_scenario['resourcescenarios'] = []

        if network_name is not None:
            self.hydra_network['name'] = network_name
        else:
            self.hydra_network['name'] = \
                "Network imported from shapefile (%s)." % self.name
        self.hydra_network['description'] = \
            "Network imported from %s" % self.name
        if self.epsg is not None:
            self.hydra_network['projection'] = \
                'EPSG:%s' % self.epsg
        self.hydra_network['nodes'] = []
        self.hydra_network['links'] = []
        self.hydra_network['attributes'] = []
        self.hydra_network['scenarios'] = []
        self.hydra_network['project_id'] = self.project['id']

        for node in self.nodes.values():
            hydra_node = self.create_hydra_node(node)
            self.hydra_network['nodes'].append(hydra_node)

        for link in self.links:
            hydra_link = self.create_hydra_link(link)
            self.hydra_network['links'].append(hydra_link)

        self.hydra_network['scenarios'].append(self.hydra_scenario)
        net_summary = self.conn.call('add_network',
                                     {'net': self.hydra_network})

        return net_summary

    def create_hydra_node(self, node):
        """Build a node dict from a HydraNode object.
        """
        hydra_node = dict()
        hydra_node['id'] = node.id
        hydra_node['name'] = node.name
        hydra_node['description'] = ''
        hydra_node['attributes'] = []
        hydra_node['x'] = repr(node.x)
        hydra_node['y'] = repr(node.y)

        #TODO: Add attributes
        return hydra_node

    def create_hydra_link(self, link):
        """Build a link dict from a HydraLink object.
        """
        hydra_link = dict()
        #TODO: Finalise this function

        return hydra_link


class HydraNode(HydraResource):

    def __init__(self, x=0, y=0):
        super(HydraNode, self).__init__()
        self.x = x
        self.y = y
        self.id = None
        self.types = []
        self.layout = None


class HydraSimpleNode(HydraResource):
    """A simple node class for shapefile import.
    """

    def __init__(self, x=0, y=0):
        super(HydraSimpleNode, self).__init__()
        self.x = x
        self.y = y
        self.attributes = dict()
        self.layout = None

    def add_attribute(self, key, val):
        """Overload the function of HydraResource to accept an attribute
        consisting of a key and a value. This way we don't need to construct a
        resource_scenario and a resource_attribute twice.
        """
        self.attributes[key] = val


class HydraLink(HydraResource):

    def __init__(self, start_node=None, end_node=None):
        super(HydraLink, self).__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.id = None
        self.types = []
        self.layout = None


class HydraSimpleLink(HydraResource):
    """A simple link class for shapefile import.
    """

    def __init__(self, start_node=None, end_node=None):
        super(HydraSimpleLink, self).__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.id = None
        self.attributes = dict()
        self.layout = None

    def add_attribute(self, key, val):
        """See HydraSimpleNode.add_attribute()
        """
        self.attributes[key] = val


class HydraNetworkTree(object):

    def __init__(self, url=None, username=None, password=None):
        self.conn = JsonConnection(url)
        if username is not None and password is not None:
            self.session_id = self.conn.login(username=username,
                                              password=password)
        else:
            self.session_id = self.conn.login()

        self.projects = dict()

    def get_tree(self):
        project_list = self.conn.call('get_projects', {})
        for project in project_list:
            networks = self.conn.call('get_networks',
                                      {'project_id': project['id']})
            project['networks'] = networks
            self.projects.update({project['id']: project})

    def print_tree(self, color=True):
        if color:
            pr_col = '\033[1m'
            ne_col = '\033[92m'
            sc_col = '\033[94m'
            endtag = '\033[0m'
        else:
            pr_col = ''
            ne_col = ''
            sc_col = ''
            endtag = ''
        for pid, project in self.projects.iteritems():
            print('%sP %3d %s%s' %
                  (pr_col, pid, project['name'], endtag))
            for network in project['networks']:
                print(u'%sN%s   \u2514\u2500%s%2d %s%s' %
                      (ne_col, endtag, ne_col, network['id'], network['name'],
                       endtag))
                for scenario in network['scenarios']:
                    print(u'%sS%s      \u2514\u2500%s%2d %s%s' %
                          (sc_col, endtag, sc_col, scenario['id'],
                           scenario['name'], endtag))


class ShapefileApp(HydraNetwork):

    def __init__(self, **kwargs):
        super(ShapefileApp, self).__init__(**kwargs)
        self._node_type_index = dict()
        self._link_type_index = dict()
        self.driver = ogr.GetDriverByName('ESRI Shapefile')

        self.temp_node_ids = temp_ids()
        self.temp_link_ids = temp_ids()
        self.temp_res_attr_ids = temp_ids()

    def from_shp(self, linkfiles, nodefiles=None, net_name=None,
                 proj_name=None):
        """Import network data from shapefiles. There needs to be at least one
        shapefile that contains MultiLine objects, defining links. If no node
        file is specified, nodes will be derived from the start and end point
        of individual links.
        """

        self.load_attributes()

        if nodefiles is not None:
            self.shp_import_nodes(nodefiles)
            create_nodes = False
        else:
            create_nodes = True

        self.shp_import_links(linkfiles, create_nodes=create_nodes)

        self.save_network(network_name=net_name, project_name=proj_name)

    def shp_import_nodes(self, nodefiles):
        """Import nodes from all shapefiles in a given list.
        """
        for nodefile in nodefiles:
            nodefile = os.path.abspath(os.path.expanduser(nodefile))
            nodeshp = self.driver.Open(nodefile)
            if nodeshp is None:
                raise HydraPluginError("Shapefile %s not readable!!!" %
                                       nodefile)
            nlayers = nodeshp.GetLayerCount()
            for nl in range(nlayers):
                layer = nodeshp.GetLayer(nl)
                layer_name = layer.GetName()
                #TODO: Project data if files feature different projections
                #if self.epsg is None:
                #    layer_proj = layer.GetSpatialRef()
                #    layer_proj.AutoIdentifyEPSG()
                #    self.epsg = layer_proj.GetAuthorityCode(None)
                #    if self.epsg is None:
                #        prj_file = os.path.splitext(nodefile)[0] + '.prj'
                #        self.epsg = prj2epsg(prj_file)['epsg'][0]

                nfeatures = layer.GetFeatureCount()
                for nf in range(nfeatures):
                    feature = layer.GetFeature(nf)
                    feature_json = feature.ExportToJson()
                    self.add_node_from_json(feature_json)

    def shp_import_links(self, linkfiles, create_nodes=False):
        """Import links from a given list of shapefiles.
        """

        for linkfile in linkfiles:
            linkfile = os.path.abspath(os.path.expanduser(linkfile))
            linkshp = self.driver.Open(linkfile)
            if linkshp is None:
                raise HydraPluginError("Shapefile %s not readable!!!" %
                                       linkfile)
            nlayers = linkshp.GetLayerCount()
            for nl in range(nlayers):
                layer = linkshp.GetLayer(nl)
                layer_name = layer.GetName()
                #TODO: Project data if files feature different projections
                if self.epsg is None:
                    layer_proj = layer.GetSpatialRef()
                    layer_proj.AutoIdentifyEPSG()
                    self.epsg = layer_proj.GetAuthorityCode(None)
                    if self.epsg is None:
                        prj_file = os.path.splitext(linkfile)[0] + '.prj'
                        self.epsg = prj2epsg(prj_file)['epsg'][0]

                nfeatures = layer.GetFeatureCount()
                for nf in range(nfeatures):
                    feature = layer.GetFeature(nf)
                    feature_json = feature.ExportToJson()
                    self.add_link_from_json(feature_json,
                                            create_nodes=create_nodes)

    def add_node_from_json(self, nodejson):
        """Add a new node from a GeoJSON string.
        """
        nodedict = json.loads(nodejson)
        if nodedict['geometry']['type'] != 'Point':
            raise HydraPluginError(
                "Wrong geometry type %s (should be 'Point')" %
                nodedict['geometry']['type'])
        x = nodedict['geometry']['coordinates'][0]
        y = nodedict['geometry']['coordinates'][1]
        node = HydraSimpleNode(x=x, y=y)
        node.id = self.temp_node_ids.next()
        if nodedict.get('properties') is not None:
            for key, val in nodedict['properties'].iteritems():
                if key.lower() == 'name':
                    node.name = val
                else:
                    node.add_attribute(key, val)

        if node.name is None:
            node.name = "Node %s" % abs(node.id)
        self.add_node(node)

    def add_link_from_json(self, linkjson, create_nodes=False):
        """Add a new link and respective nodes from a GeoJSON string.
        """

        linkdict = json.loads(linkjson)
        us_node_coord = tuple(linkdict['geometry']['coordinates'][0])
        ds_node_coord = tuple(linkdict['geometry']['coordinates'][-1])

        if create_nodes:
            if self._node_coord_index.get((us_node_coord[0], us_node_coord[1]))\
                    is not None:
                us_node = self.nodes[self._node_coord_index[(us_node_coord[0],
                                                             us_node_coord[1])]]
            else:
                us_node = HydraSimpleNode(x=us_node_coord[0],
                                          y=us_node_coord[1])
                us_node.id = self.temp_node_ids.next()
                us_node.name = "Node %s" % abs(us_node.id)
                self.add_node(us_node)
            if self._node_coord_index.get((ds_node_coord[0], ds_node_coord[1]))\
                    is not None:
                ds_node = self.nodes[self._node_coord_index[(ds_node_coord[0],
                                                             ds_node_coord[1])]]
            else:
                ds_node = HydraSimpleNode(x=ds_node_coord[0],
                                          y=ds_node_coord[1])
                ds_node.id = self.temp_node_ids.next()
                ds_node.name = "Node %s" % abs(ds_node.id)
                self.add_node(ds_node)
        else:
            round_digits = range(12, 0, -1)
            us_i = 0
            while self._node_coord_index.get(us_node_coord) is None:
                us_node_coord = tuple([round(i, round_digits[us_i])
                                       for i in us_node_coord])
                us_i += 1
            ds_i = 0
            while self._node_coord_index.get(ds_node_coord) is None:
                ds_node_coord = tuple([round(i, round_digits[ds_i])
                                       for i in ds_node_coord])
                ds_i += 1
            us_node = self.nodes[self._node_coord_index[us_node_coord]]
            ds_node = self.nodes[self._node_coord_index[ds_node_coord]]

        link = HydraSimpleLink(start_node=us_node, end_node=ds_node)
        link.id = self.temp_link_ids.next()
        link.layout = dict(geometry=linkdict['geometry'])
        if linkdict.get('properties') is not None:
            for key, val in linkdict['properties'].iteritems():
                if key.lower() == 'name':
                    link.name = val
                else:
                    link.add_attribute(key, val)

        if link.name is None:
            link.name = "Link %s" % abs(link.id)
        self.add_link(link)

    def create_hydra_node(self, node):
        """Override inherited function to build a node dict from a
        HydraSimpleNode object.
        """
        hydra_node = dict()
        hydra_node['id'] = node.id
        hydra_node['name'] = node.name
        hydra_node['description'] = ''
        hydra_node['attributes'] = []
        hydra_node['x'] = repr(node.x)
        hydra_node['y'] = repr(node.y)

        for key, val in node.attributes.iteritems():
            res_attr = self.create_attribute(key, val)
            hydra_node['attributes'].append(res_attr)

        return hydra_node

    def create_hydra_link(self, link):
        """Override inherited function to build a link dict from a
        HydraSimpleNode object.
        """
        hydra_link = dict()
        hydra_link['id'] = link.id
        hydra_link['name'] = link.name
        hydra_link['description'] = ''
        hydra_link['attributes'] = []
        hydra_link['node_1_id'] = link.start_node.id
        hydra_link['node_2_id'] = link.end_node.id
        hydra_link['layout'] = link.layout

        for key, val in link.attributes.iteritems():
            res_attr = self.create_attribute(key, val)
            hydra_link['attributes'].append(res_attr)

        return hydra_link

    def create_attribute(self, key, val):
        """Create a resource attribute and a resource scenario.
        """
        if self.attr_ids.get(key) is None:
            attr = dict(name=key)

            #TODO: This is not really efficient, but it works
            attr = self.conn.call('add_attribute', {'attr': attr})
            self.attr_ids[key] = attr.id
            self.attrs[attr.id] = attr
        else:
            attr = self.attrs[self.attr_ids[key]]

        res_attr = dict(id=self.temp_res_attr_ids.next(),
                        attr_id=attr.id,
                        attr_is_var='N')
        if val is None:
            res_attr['attr_is_var'] = 'Y'
        else:
            dataset = dict(id=None,
                           type=None,
                           unit=None,
                           dimension=None,
                           name='Shapefile data %s' % key,
                           value=None,
                           hidden='N',
                           metadata='{"source": "ShapefileApp"}',
                           )
            if isinstance(val, str) or isinstance(val, unicode):
                dataset['type'] = 'descriptor'
            elif isinstance(val, float) or isinstance(val, int):
                dataset['type'] = 'scalar'

            dataset['value'] = str(val)

            res_scen = dict(attr_id=attr.id,
                            resource_attr_id=res_attr['id'],
                            value=dataset)

            self.hydra_scenario['resourcescenarios'].append(res_scen)

        return res_attr

    def build_node_type_index(self):
        for node in self.nodes.values():
            combined_type = '_'.join([t.name for t in node.types])
            if combined_type == '':
                combined_type = 'Generic node'
            if self._node_type_index.get(combined_type) is None:
                self._node_type_index[combined_type] = [node]
            else:
                self._node_type_index[combined_type].append(node)

    def build_link_type_index(self):
        for link in self.links:
            combined_type = '_'.join([t.name for t in link.types])
            if combined_type == '':
                combined_type = 'Generic link'
            if self._link_type_index.get(combined_type) is None:
                self._link_type_index[combined_type] = [link]
            else:
                self._link_type_index[combined_type].append(link)

    def to_shp(self, outfolder, overwrite=False):
        """Export the network to a shapefile. Up to now the export only
        supports strings and scalars as attribute values.
        """
        #TODO: Create folder if necessary
        outfolder = os.path.abspath(os.path.expanduser(outfolder))

        self.build_node_type_index()
        self.build_link_type_index()

        projection = osr.SpatialReference()
        projection.ImportFromEPSG(int(self.hydra_network.projection.split(':')[1]))

        for nodetype in self._node_type_index.keys():
            outfile = outfolder + os.path.sep +\
                nodetype.replace(" ", "_") + ".shp"
            if overwrite and os.path.exists(outfile):
                self.driver.DeleteDataSource(outfile)
            elif os.path.exists(outfile) and not overwrite:
                raise HydraPluginError("Outputfile exists!")
            basepath, filename = os.path.split(outfile)

            target_file = self.driver.CreateDataSource(outfile)

            target_layer = target_file.CreateLayer(nodetype.encode('ascii',
                                                                   'ignore'),
                                                   projection,
                                                   geom_type=ogr.wkbPoint)

            featureDefn = target_layer.GetLayerDefn()

            # Collect all attributes to add them to the layer
            attrs = dict()
            field_type = dict()

            for node in self._node_type_index[nodetype]:
                for attr in node.attributes:
                    attr = self._filter_data_types(attr)
                    if attrs.get(attr.name) is None:
                        attrs[attr.name] = [self._get_ogr_type(attr)]
                    else:
                        attrs[attr.name].append(self._get_ogr_type(attr))

            for attr in attrs.keys():
                type_set = set(attrs[attr])
                if len(type_set) > 1:
                    raise HydraPluginError(
                        "Ambiguous data type for attribute '%s'." % attr)
                else:
                    field_type[attr] = type_set.pop()

            field = dict()
            name_field = ogr.FieldDefn('name', ogr.OFTString)
            target_layer.CreateField(name_field)
            for attr in field_type.keys():
                field[attr] = ogr.FieldDefn(attr.encode('ascii', 'ignore'),
                                            field_type[attr])
                target_layer.CreateField(field[attr])

            for node in self._node_type_index[nodetype]:
                #node_wkt = "POINT (%s %s)" % (node.x, node.y)
                #node_geom = ogr.CreateGeometryFromWkt(node_wkt)
                node_geom = ogr.Geometry(ogr.wkbPoint)
                node_geom.AddPoint(node.x, node.y)
                #node_dict = dict(type="Point",
                #                 coordinates=[node.x, node.y])
                #node_json = json.dumps(node_dict)
                #node_geom = ogr.CreateGeometryFromJson(node_json)
                node_feature = ogr.Feature(featureDefn)
                node_feature.SetGeometry(node_geom)
                node_feature.SetField('name',
                                      node.name.encode('ascii', 'ignore'))
                for attr in node.attributes:
                    node_feature.SetField( \
                        attr.name.encode('ascii', 'ignore')[:10],
                        attr.value)
                target_layer.CreateFeature(node_feature)
                node_feature.Destroy()

            target_file.Destroy()

        attrs = dict()
        field_type = dict()

        for linktype in self._link_type_index.keys():
            outfile = outfolder + os.path.sep +\
                linktype.replace(" ", "_") + ".shp"
            if overwrite and os.path.exists(outfile):
                self.driver.DeleteDataSource(outfile)
            elif os.path.exists(outfile) and not overwrite:
                raise HydraPluginError("Outputfile exists!")
            basepath, filename = os.path.split(outfile)

            target_file = self.driver.CreateDataSource(outfile)

            target_layer = target_file.CreateLayer(linktype.encode('ascii'),
                projection, geom_type=ogr.wkbMultiLineString)

            featureDefn = target_layer.GetLayerDefn()

            attrs = dict()
            field_type = dict()

            for link in self._link_type_index[linktype]:
                for attr in link.attributes:
                    attr = self._filter_data_types(attr)
                    if attrs.get(attr.name) is None:
                        attrs[attr.name] = [self._get_ogr_type(attr)]
                    else:
                        attrs[attr.name].append(self._get_ogr_type(attr))

            for attr in attrs.keys():
                type_set = set(attrs[attr])
                if len(type_set) > 1:
                    raise HydraPluginError(
                        "Ambiguous data type for attribute '%s'." % attr)
                else:
                    field_type[attr] = type_set.pop()

            field = dict()
            name_field = ogr.FieldDefn('name', ogr.OFTString)
            target_layer.CreateField(name_field)
            for attr in field_type.keys():
                field[attr] = ogr.FieldDefn(attr.encode('ascii', 'ignore'),
                                            field_type[attr])
                target_layer.CreateField(field[attr])

            for link in self._link_type_index[linktype]:
                if 'geometry' in link.layout.keys():
                    geom = json.dumps(link.layout['geometry'])
                    link_geom = ogr.CreateGeometryFromJson(geom)
                else:
                    link_geom = ogr.Geometry(ogr.wkbLineString)
                    link_geom.AddPoint(link.start_node.x, link.start_node.y)
                    link_geom.AddPoint(link.end_node.x, link.end_node.y)
                link_feature = ogr.Feature(featureDefn)
                link_feature.SetGeometry(link_geom)
                link_feature.SetField('name',
                                      link.name.encode('ascii', 'ignore'))
                for attr in link.attributes:
                    link_feature.SetField( \
                        attr.name.encode('ascii', 'ignore')[:10],
                        attr.value)
                target_layer.CreateFeature(link_feature)
                link_feature.Destroy()

            target_file.Destroy()

    def _get_ogr_type(self, attr):
        """Return the field type used for an attribute type."""
        if attr.dataset_type == 'array':
            return ogr.OFTString
        elif attr.dataset_type == 'scalar':
            return ogr.OFTReal
        elif attr.dataset_type == 'descriptor':
            return ogr.OFTString
        elif attr.dataset_type == 'timeseries':
            return ogr.OFTString
        else:
            return ogr.OFTString

    def _filter_data_types(self, attr):
        if attr.dataset_type == 'array':
            attr.value = 'Array'
        elif attr.dataset_type == 'scalar':
            attr.value = float(attr.value)
        elif attr.dataset_type == 'timeseries':
            attr.value = 'Timeseries'

        return attr


def commandline_parser():
    parser = ap.ArgumentParser(prog='ShapefileApp.py', description="""
Import and export HydraPlatform networks from and to ArgGIS shapefiles.

Written by Philipp Meier <philipp.meier@eawag.ch>

(c) Copyright 2015
Eawag: Swiss Federal Institute of Aquatic Science and Technology
""", formatter_class=ap.RawDescriptionHelpFormatter)

    parser.add_argument('-in', '--input-nodes', nargs='+',
                        help="Input shapefile containing nodes.")
    parser.add_argument('-il', '--input-links', nargs='+',
                        help="Input shapefile containing links.")
    parser.add_argument('-url', '--url',
                        help="""URL of HydraPlatform server (defaults to value
                        specified in the config file.""")
    parser.add_argument('-t', '--print-tree', action='store_true',
                        help="""Print the project-network-scenario tree of the
                        HydraPlatform database,
                        """)

    return parser


if __name__ == '__main__':
    parser = commandline_parser()
    args = parser.parse_args()

    if args.print_tree:
        tree = HydraNetworkTree(url=args.url)
        tree.get_tree()
        tree.print_tree()
    else:
        exporter = ShapefileApp(url=args.url)
        exporter.login()

    if args.input_links is not None:
        # Import network from shapefile
        exporter.from_shp(args.input_links, args.input_nodes)
