#!/usr/bin/env python

import networkx as nx

from re import compile, sub
from sqlalchemy.orm import join, contains_eager
from sys import maxunicode

from simulacra.database import Base, db_session
from simulacra.models import Project, Tag

def sanitize(s):
    # BEGIN http://stackoverflow.com/questions/1707890/fast-way-to-filter-illegal-xml-unicode-chars-in-python
    _illegal_unichrs = [(0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F), (0x7F, 0x84), (0x86, 0x9F), (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF)] 
    if maxunicode >= 0x10000:  # not narrow build 
        _illegal_unichrs.extend([(0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF),
                                 (0x3FFFE, 0x3FFFF), (0x4FFFE, 0x4FFFF),
                                 (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
                                 (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF),
                                 (0x9FFFE, 0x9FFFF), (0xAFFFE, 0xAFFFF),
                                 (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
                                 (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF),
                                 (0xFFFFE, 0xFFFFF), (0x10FFFE, 0x10FFFF)]) 

    _illegal_ranges = ["%s-%s" % (unichr(low), unichr(high)) 
                       for (low, high) in _illegal_unichrs] 
    _illegal_xml_chars_RE = compile(u'[%s]' % u''.join(_illegal_ranges))
    # END http://stackoverflow.com/questions/1707890/fast-way-to-filter-illegal-xml-unicode-chars-in-python
    return sub(_illegal_xml_chars_RE, ' ', s)

def graph_add_node_t(t, g):
    tl = 'tag-' + sanitize(t.tag).lower()
    if g.has_node(tl):
        g.node[tl]['weight'] += 1
    else:
        g.add_node(tl)
        g.node[tl]['type'] = 'tag'
        g.node[tl]['label'] = sanitize(t.tag).lower()
        g.node[tl]['weight'] = 1

def graph_add_node_p(p, g):
    pl = 'project-' + str(p.id)
    if g.has_node(pl):
        return # don't increase the weight
    else:
        g.add_node(pl)
        g.node[pl]['type'] = 'project'
        g.node[pl]['label'] = sanitize(p.title).lower()
        g.node[pl]['weight'] = 1

def graph_add_edge(t, p, g):
    tl = 'tag-' + sanitize(t.tag).lower()
    pl = 'project-' + str(p.id)
    if g.has_edge(tl, pl):
        g[tl][pl]['weight'] += 1
    else:
        g.add_edge(tl, pl)
        g[tl][pl]['weight'] = 1

graph = nx.Graph()

for t in db_session.query(Tag).all():
    #print('tag {}'.format(t.tag))
    for p in t.projects:
        graph_add_node_t(t, graph)
        graph_add_node_p(p, graph)
        graph_add_edge(t, p, graph)

nx.write_gexf(graph, 'project_tag_20141203.gexf')  
