import pandas as pd
import polyline
from rdp import rdp
import time 
import openrouteservice as ors

def get_path_steepness(client,route):
    time.sleep(1)
    try:
        route_coordinates = polyline.decode(route['route_geometry'])
        rdp_route_coordinates = rdp(route_coordinates, epsilon=0.0001)
        rdp_route_coordinates = [[i[1],i[0]] for i in rdp_route_coordinates]
        response = client.directions(coordinates = rdp_route_coordinates, profile = 'cycling-regular', format = 'geojson', validate = False, instructions = False, elevation = True, extra_info = ['steepness'])
        steepness = response['features'][0]['properties']['extras']['steepness']["summary"]
        total_length = sum([i['distance'] for i in steepness])
        normalized_weighted_steepness = sum([i['distance']*i['value'] for i in steepness])/total_length
        return normalized_weighted_steepness
    except Exception as e:
        return None

def get_path_suitability(client,route):
    time.sleep(1)
    try:
        route_coordinates = polyline.decode(route['route_geometry'])
        rdp_route_coordinates = rdp(route_coordinates, epsilon=0.0001)
        rdp_route_coordinates = [[i[1],i[0]] for i in rdp_route_coordinates]
        response = client.directions(coordinates = rdp_route_coordinates, profile = 'cycling-regular', format = 'geojson', validate = False, instructions = False, elevation = True, extra_info = ['suitability'])
        suitability = response['features'][0]['properties']['extras']['suitability']["summary"]
        total_length = sum([i['distance'] for i in suitability])
        normalized_weighted_steepness = sum([i['distance']*i['value'] for i in suitability])/total_length
        return normalized_weighted_steepness
    except Exception as e:
        return None