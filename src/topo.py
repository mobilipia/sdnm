import sys
import ast
import math
import urllib
import logging
import networkx as nx
from networkx import graphviz_layout
import matplotlib.pylab as plt

sys.path.append("./lib")
from link import Link
from node import Node

class Topology():
    def __init__(self, ip='127.0.0.1', port='8080'):
        self.nodes = []
        self.new_nodes = []
        self.links = []
        self.new_links = []
        # Params
        self.ip = ip
        self.port = port

        # Attributes
        self.selected = ''

    def DeleteNode(self, mac):
        for node in self.nodes:
            if node.mac == mac:
                self.nodes.remove(node)
                logging.info(str(node.mac) + ': was Deleted.')

    def DeleteLink(self, link):
        for l in self.links:
            if l == link:
                self.links.remove(l)
                logging.info('Link from src ' + str(link.src) + ': was Deleted.')

    def SelectNode(self, mac):
        for n in self.nodes:
            if n.mac == mac:
                self.selected = mac
                n.select = True
            else:
                n.select = False         

    def GetNodes(self):
        return self.nodes
    
    def GetNode(self, mac):
        for n in self.nodes:
            if n.mac == mac:
                return n

    def GetNewNodes(self, srv_nodes):
        '''
        Returns a list of new Nodes
        '''
        result = []
        for node in srv_nodes:
            node_ex = False
            for n in self.nodes:
                if node == n.mac:
                    node_ex = True
                    n.dead = False
            if not node_ex:
                result.append( Node(x=0, y=0, w=40, h=40, mac=node) )
                
        return result
    
    def MarkDeadNodes(self, srv_nodes):
        for i in range(len(self.nodes)):
            if self.nodes[i].mac not in srv_nodes:
                #del(self.nodes[i])
                self.nodes[i].dead = True

    def MarkDeadLinks(self, srv_links):
        if srv_links != None:
            for i in range(len(self.links)):
                if self.links[i].LinkAsDict() not in srv_links:
                    #del(self.links[i])
                    self.links[i].dead = True
    
    def GetLinks(self):
        return self.links

    def GetPortLinks(self, n1, n2):
        """Get all port pairs connecting two nodes
        Args:
        n1: node one
        n2: node two
        
        Returns:
        a tuple of arrays containing src_ports and dst_ports
        """
        n1_ports = []
        n2_ports = []

        for l in self.links:
            if l.srcmac == n1.mac:
                n1_ports.append(l.srcmac)
                n2_ports.append(l.dstmac)
            elif l.srcmac == n2.mac:
                n1_ports.append(l.dstmac)
                n2_ports.append(l.srcmac)

        return (n1_ports, n2_ports)

    def SrcAndDstNodes(self, link):
        """Find which node is closest to (0, 0)
        Returns:
        A mac tuple ordered by distance to point (0,0)
        """
        na = self.GetNode(link.srcmac).DistanceToPoint( (0,0) )
        nb = self.GetNode(link.dstmac).DistanceToPoint( (0,0) )
        if na <= nb:
            return (link.srcmac, link.dstmac)
        else:
            return (link.dstmac, link.srcmac)

    def RemoveDuplicateLinks(self, srv_links):
        """Remove duplicate links
        """
        result = []
        for link in srv_links:
            inv_link = {'src-switch': link['dst-switch'],
                        'dst-switch': link['src-switch'],
                        'src-port': link['dst-port'],
                        'dst-port': link['src-port']}
            if link not in result:
                if inv_link not in result:
                            result.append(link)
        return result
    
    def GetNewLinks(self, srv_links):
        srv_links = self.RemoveDuplicateLinks(srv_links)
        result = []
        for link in srv_links:
            link_ex = False
            for l in self.links:
                # May need to change -> 'if link == l.LinkAsDict()'
                if link == l:
                    link_ex = True
                    l.dead = False
            if not link_ex:
                result.append( Link(link['src-switch'], link['src-port'],
                                    link['dst-switch'], link['dst-port']) )
                
        return result

    def Update(self):
        srv_nodes = self.UpdateNodes()
        srv_links = self.UpdateLinks()

        self.new_nodes = self.GetNewNodes(srv_nodes)
        self.MarkDeadNodes(srv_nodes)
        self.new_links = self.GetNewLinks(srv_links)
        self.MarkDeadLinks(srv_links)
        self.nodes += self.new_nodes
        self.links += self.new_links

        # Get node positions for new nodes.
        node_pos = self.UpdateGraph()

        for node in self.nodes:
            if (node.x,node.y) == (0,0):
                node.desc = self.UpdateSwitchDesc(node.mac)
                pos = node_pos[node.mac]
                node.x = pos[0]
                node.y = pos[1]

        for link in self.links:
            s = self.GetNode(link.srcmac)
            d = self.GetNode(link.dstmac)
            link.Move((s.x, s.y), link.srcmac)
            link.Move((d.x, d.y), link.dstmac)

        self.new_nodes = []
        self.new_links = []

    def UpdateNodes(self):
        '''
        Retrieve node data from restAPI
        {mac: [mac1, ... , macn]}
        '''
        try:
            address = self.ip + ':' + self.port
            fd = urllib.urlopen('http://' + address + '/wm/topology/switchclusters/json')
            cq_result = fd.read()
            fd.close()
        except IOError:
            print("[INFO] Can't connect to floodlight http server")
            cq_result = ""
        finally:
            if cq_result == "":
                return {}
            else:
                result = []
                t = ast.literal_eval(cq_result)
                for n in t:
                    for mac in t[n]:
                        result.append(mac)
                return result

    def UpdateSwitchDesc(self, dpid):
        """Get switch desc from restAPI
        {mac: [{"manufacturerDescription":<s_manName>, "hardwareDescription":<s_hwDesc>,
        "softwareDescription":<s_version>,"serialNumber":<s_>,"datapathDescription":<s_>}] }
        """
        try:
            address = self.ip + ':' + self.port
            fd = urllib.urlopen('http://' + address + '/wm/core/switch/' + dpid + '/desc/json')
            cq_result = fd.read()
            fd.close()
        except IOError:
            print("[INFO] Can't connect to floodlight http server")
            cq_result = ""
        finally:
            if cq_result == "":
                return {}
            else:
                result = []
                t = ast.literal_eval(cq_result)
                if t[dpid] != "null":
                    return t[dpid][0]
                else:
                    return None

    def UpdateLinks(self):
        '''
        Retrieve link data from restAPI
        {src-switch: mac, dst-switch: mac, src-port: int, dst-port: int}
        '''
        try:
            address = self.ip + ':' + self.port
            fd = urllib.urlopen('http://' + address + '/wm/topology/links/json')
            lq_result = fd.read()
            fd.close()
        except IOError:
            print("[INFO] Can't connect to floodlight http server")
            lq_result = ""
        finally:
            if lq_result == "":
                return []
            else:
                return ast.literal_eval(lq_result)


    def UpdateGraph(self):
        g = nx.Graph()
        for node in self.nodes:
            g.add_node(node.mac)
            for l in self.links:
                if node.mac == l.srcmac:
                    g.add_edge(l.srcmac, l.dstmac)
        # Get node positions
        return nx.graphviz_layout(g, prog='neato')
