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


import warnings

from datetime import datetime

from HydraLib.PluginLib import HydraResource
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
                                      {'project_id': project['id'],
                                       'include_data': 'N'})
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
