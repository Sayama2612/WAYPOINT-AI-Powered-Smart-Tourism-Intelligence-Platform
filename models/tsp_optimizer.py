import math
import random
from typing import List, Dict
import numpy as np


def haversine_km(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    aa = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(aa), math.sqrt(1-aa))


def build_cost_matrix(points, crowd_scores=None, weather_scores=None, alpha=0.5, beta=0.3):
    n = len(points)
    mat = np.zeros((n,n))
    for i in range(n):
        for j in range(n):
            if i==j:
                mat[i,j] = 0.0
            else:
                d = haversine_km(points[i], points[j])
                penalty = 1.0
                if crowd_scores is not None:
                    penalty += alpha * (crowd_scores[j]/100.0)
                if weather_scores is not None:
                    penalty += beta * (weather_scores[j]/100.0)
                mat[i,j] = d * penalty
    return mat


def route_cost(route: List[int], cost_mat):
    c = 0.0
    for i in range(len(route)-1):
        c += cost_mat[route[i], route[i+1]]
    return c


def two_opt(route: List[int], cost_mat, max_iter=200):
    best = route.copy()
    best_cost = route_cost(best, cost_mat)
    n = len(route)
    improved = True
    it = 0
    while improved and it < max_iter:
        improved = False
        for i in range(1, n-2):
            for j in range(i+1, n-1):
                new_route = best[:i] + best[i:j+1][::-1] + best[j+1:]
                new_cost = route_cost(new_route, cost_mat)
                if new_cost + 1e-6 < best_cost:
                    best = new_route
                    best_cost = new_cost
                    improved = True
        it += 1
    return best, best_cost


def optimize_route(coords: List[tuple], crowd_scores=None, weather_scores=None, alpha=0.5, beta=0.3):
    n = len(coords)
    if n <= 2:
        return list(range(n)), 0.0
    cost_mat = build_cost_matrix(coords, crowd_scores=crowd_scores, weather_scores=weather_scores, alpha=alpha, beta=beta)
    # start with greedy nearest neighbor
    start = 0
    route = [start]
    unvisited = set(range(n))
    unvisited.remove(start)
    while unvisited:
        last = route[-1]
        next_node = min(unvisited, key=lambda x: cost_mat[last,x])
        route.append(next_node)
        unvisited.remove(next_node)
    route.append(start)  # make it closed for cost computation
    # run 2-opt
    best_route, best_cost = two_opt(route, cost_mat)
    # return open route (omit repeated start at end)
    if best_route and best_route[-1] == best_route[0]:
        best_route = best_route[:-1]
    return best_route, best_cost
