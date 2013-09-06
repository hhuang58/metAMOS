############################################################################
# Copyright (c) 2011-2013 Saint-Petersburg Academic University
# All Rights Reserved
# See file LICENSE for details.
############################################################################

import logging
class Abstract_Vertex(object):
    def __init__(self, vid):
        self.inn = []
        self.out = []
        self.vid = vid

    def __hash__(self):
        return self.vid


class Abstract_Edge(object):
    def __init__(self, v1, v2, eid):
        self.v1, self.v2 = v1, v2
        v1.out.append(self)
        v2.inn.append(self)
        self.eid = eid

    def __hash__(self):
        return self.eid

    def length(self):
        pass


class Abstract_Graph(object):
    def __init__(self):
        self.vs = {} # key -> Vertex
        self.es = {} # key -> Edges
        self.logger = logging.getLogger('rectangles')
        

    def get_edge(self, eid):
        return self.es.get(eid, None)

    def find_all_loops(self, edge, threshold, L, rs):
        self.logger.info ("find all loops " + str(edge.eid))
        NO_LOOPS = None
        v1 = edge.v2
        lst = [(v1, 0)]
        long_end = None
        visited_vs = set()
        visited_es = set()
        while len(lst) != 0:
            (v, deep) = lst.pop(0)
            if deep > threshold:
                continue
            for e1 in v.out:
                if e1.length() > L:
                    if long_end and long_end.eid != e1.eid:
                        return NO_LOOPS
                    long_end = e1
                else:
                    visited_vs.add(v)
                    lst.append((e1.v2, deep + 1))
        if not long_end:
            return NO_LOOPS
        self.logger.info("found loops")             
        visited_es.add(long_end.eid)
        visited_es.add(edge.eid)
        good_vertex = [edge.v1.vid, edge.v2.vid, long_end.v1.vid, long_end.v2.vid]
        bad_edges = set()
        for v in visited_vs:
            for e in v.out:
                visited_es.add(e.eid)
            for e in v.inn:
                visited_es.add(e.eid)
            for e in v.out:
                v2 = e.v2
            #for v2 in [e.v2 for e in v.out]:
                if v2.vid not in good_vertex and v2 not in visited_vs:
                    bad_edges.add(e)
            for e in v.inn:
                v_begin = e.v1
            #for v_begin in [e.v1 for e in v.inn]:
                if v_begin.vid not in good_vertex and v_begin not in visited_vs:
                    bad_edges.add(e)
        """if len(bad_edges) != 0:
          return NO_LOOPS"""
        if len(bad_edges) != 0 and len(rs.keys()) == 0:
          return NO_LOOPS
        self.logger.info("found visited vs")
        if len(rs.keys()) != 0:
            tips = set()
            for e_bad in bad_edges:
                tip = True
                for e_inn in  e_bad.v1.inn:
                    if e_inn.eid not in visited_es:
                        tip = False
                for e_out in e_bad.v1.out:
                    if e_out.eid != e_bad.eid and e_out.eid not in visited_es:
                        tip = False
                for e_inn in e_bad.v2.inn:
                    if e_inn.eid != e_bad.eid and e_inn.eid not in visited_es:
                        tip = False
                for e_out in e_bad.v2.out:
                    if e_out.eid not in visited_es:
                        tip = False
                if tip:
                    tips.add(e_bad)
                    continue
    
                """for e_good in visited_es:
                    if (self.es[e_good], e_bad) in rs:
                        return NO_LOOPS
                    if (e_bad, self.es[e_good]) in rs:
                        return NO_LOOPS"""
            for tip in tips:
                bad_edges.remove(tip)
            """not_aligned = set(bad_edges)
            for (first,second), r in rs.items():
              if first in not_aligned:
                if second != first :
                  not_aligned.remove(first)
              if second in not_aligned:
                if first != second:
                  not_aligned.remove(second)"""

            if len(bad_edges) !=0:# and len(not_aligned) != len(bad_edges):
                return NO_LOOPS  
        self.logger.info("found tips")
        if len(visited_es) == 2:
            return NO_LOOPS
        for v in visited_vs:
            if not self.is_connected(v, long_end, threshold):
                return NO_LOOPS
        paths = self.get_paths(edge.v1, long_end, edge, int(1.5 * (threshold + 1)), False)
        if len(paths) < 1:
            return NO_LOOPS
        best_path = paths[0]
        best_len = self.path_len(best_path)
        """for path in paths:
            if self.path_len(path) > best_len:
                if path[0] != edge:
                    continue
                long_edges = set()
                false_path = False
                for e in path:
                    if e not in visited_vs:
                        false_path = True
                        break
                    if e.length() > 600 and e.eid in long_edges:
                        false_path = True
                        break
                    if e.length() > 600:
                        long_edges.add(e.eid)
                if false_path:
                    continue
                best_path = self.path_len(path)
                best_path = path"""
        return (edge.eid, long_end.eid, visited_es, best_path, visited_vs, paths)

    def path_len(self, path):
        path_len = 0
        for e in path:
            path_len += e.length()
        return path_len

    def is_connected(self, vertex, edge, threshold):
        return len(self.get_paths(vertex, edge, None, threshold, True)) > 0

    def get_paths(self, vertex, edge, begin_edge, threshold, one_path=False):
        paths = []
        lst = [(vertex, 0, [])]
        while len(lst) != 0:
            (v, deep, path) = lst.pop(0)
            if deep > threshold:
                continue
            for e in v.out:
                if begin_edge and v.vid == vertex.vid and e.eid != begin_edge.eid:
                    continue
                if e.eid == edge.eid:
                    paths.append(path)
                    if one_path:
                        return paths
                new_path = list(path)
                new_path.append(e)
                lst.append((e.v2, deep + 1, new_path))
        return paths


def number_of_pathes(v1, v2, limit):
    limit += 1 # limit inclusive
    ls = [{} for _ in xrange(limit)]
    ls[0][v1] = 1
    for pos in xrange(limit):
        for v, cnt in ls[pos].iteritems:
            if v == v2: return cnt
            for e in v.out:
                pos2 = pos + e.len
                if pos2 < limit:
                    v2 = e.v2
                    ls[pos2][v2] = ls[pos2].get(v2, 0) + cnt
    return 0


def find_paths(v1, v2, e1, len_threshold, deep_threshold):
    return __find_all_paths(v1, v2, e1, [], 0, [], len_threshold, deep_threshold)


def __find_all_paths(v1, v2, e1, path, path_len, paths, len_threshold, deep_threshold):
    for e in v1.out:
        if (len(path) == 0) and e != e1:
            continue
        if e.len > len_threshold:
            return paths
        new_path = list(path)
        new_path.append(e)
        new_path_len = path_len + e.len
        if e.v2 == v2:
            paths.append((new_path, new_path_len))
            return paths
        else:
            if (len(path) > deep_threshold):
                return paths
            __find_all_paths(e.v2, v2, e1, new_path, new_path_len, paths, len_threshold - e.len, deep_threshold)
    return paths


