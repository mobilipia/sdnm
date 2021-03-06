import subprocess
import string
import ast
import networkx as nx
import matplotlib.pylab as plt

link_data = []
cluster_data = dict()

def retrieve_links():
    # Get link_data from REST API.
    lq = subprocess.Popen('curl http://127.0.0.1:8080/wm/topology/links/json', shell=True,stdout=subprocess.PIPE)
    lq_result = lq.communicate()[0]

    #print(lq_result)
    if lq_result == "":
        return []
    else:
        return ast.literal_eval(lq_result)

# FIX ME: Only grabing first cluster
def retrieve_clusters():
    ''' Get cluster_data from REST API. '''
    cq = subprocess.Popen('curl http://127.0.0.1:8080/wm/topology/switchclusters/json', shell=True, stdout=subprocess.PIPE)
    cq_result = cq.communicate()[0]

    #print(cq_result)
    if cq_result == "":
        return {}
    else:
        return ast.literal_eval(cq_result)

def get_graph(clusters, links):
    g = nx.Graph()
    for node in clusters:
        g.add_node(node)
        for l in links:
            if node == l['src-switch']:
                g.add_edge(l['src-switch'], l['dst-switch'])
    return g

def draw_topology(clusters, links):
    g = nx.Graph()

    for k, v in clusters.iteritems():
        for node in v:
            g.add_node(node)
            for l in links:
                if node == l['src-switch']:
                    g.add_edge(l['src-switch'],l['dst-switch'])
    
    # Magic... Draws empty img is nodes are == 0. No idea why
    #  this fix works. Rather use an exception when loading them
    #  img in NetworkGraph, but loading non-existing img doesn't
    #  raise one... Why you no raise exception?! --\_(o_O)_/--
    #print(g.number_of_nodes())
    if g.number_of_nodes() > 0:
        nx.draw(g)    
        plt.savefig('path.png')
    else:
        plt.savefig('path.png')
            
if __name__ == '__main__':
    # Get important link data
    link_data = retrieve_links()
    cluster_data = retrieve_clusters()

    draw_topology(cluster_data, link_data)
