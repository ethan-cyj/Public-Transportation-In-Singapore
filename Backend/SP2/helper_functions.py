import pandas as pd
import polyline
from rdp import rdp
import time 
import openrouteservice as ors
import numpy as np
from pyonemap import OneMap
import json 
import requests
from bs4 import BeautifulSoup


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
    
def get_path_steepness_and_suitability(client,route):
    time.sleep(1)
    try:
        route_coordinates = polyline.decode(route['route_geometry'])
        rdp_route_coordinates = rdp(route_coordinates, epsilon=0.0001)
        rdp_route_coordinates = [[i[1],i[0]] for i in rdp_route_coordinates]
        response = client.directions(coordinates = rdp_route_coordinates, profile = 'cycling-regular', format = 'geojson', validate = False, instructions = False, elevation = True, extra_info = ['steepness','suitability'])

        steepness = response['features'][0]['properties']['extras']['steepness']['summary']
        total_length_steepness = sum([i['distance'] for i in steepness])
        normalized_weighted_steepness = sum([i['distance']*i['value'] for i in steepness])/total_length_steepness

        suitability = response['features'][0]['properties']['extras']['suitability']['summary']
        total_length_suitability = sum([i['distance'] for i in suitability])
        normalized_weighted_suitability = sum([i['distance']*i['value'] for i in suitability])/total_length_suitability

        return normalized_weighted_steepness,normalized_weighted_suitability
    except Exception as e:
        return None,None
    
#Defining a function that calculates the Euclidean Distance between two points using Haversine Method?
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arcsin(np.sqrt(a))

    distance = R * c
    return distance

def get_cycle_route(onemap,coordinate_pair):
    time.sleep(0.5)
    try:
        return onemap.routing.route(start_lat=coordinate_pair.lat_x, 
                                    start_lon=coordinate_pair.lon_x, 
                                    end_lat=coordinate_pair.lat_y, 
                                    end_lon=coordinate_pair.lon_y, 
                                    routeType="cycle")
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_distance(route):
    try:
        return route['route_summary']['total_distance']/1000 #convert m to km
    except (KeyError, IndexError,TypeError) as e:
        print(f"Error: {e}")
        return None
    
def get_time(route):
    try:
        return route['route_summary']['total_time']/60 #convert second to minutes
    except (KeyError, IndexError,TypeError) as e:
        print(f"Error: {e}")
        return None
    
def get_centroid_name(onemap,row):
    geocode = onemap.reverseGeocode.revGeoCode(row['Latitude_x'], row['Longitude_x'])
    if geocode['GeocodeInfo'][0]['BUILDINGNAME'] != "NIL" and geocode['GeocodeInfo'][0]['BUILDINGNAME'] != "MULTI STOREY CAR PARK":
            return geocode['GeocodeInfo'][0]['BUILDINGNAME']
    else:
        if geocode['GeocodeInfo'][0]['BLOCK'] != "NIL":
            return geocode['GeocodeInfo'][0]['BLOCK'] + " " + geocode['GeocodeInfo'][0]['ROAD']
        else:
            return geocode['GeocodeInfo'][0]['ROAD']
        

def fetch_itinerary(from_lat, from_lon, to_lat, to_lon):
    # Define the GraphQL endpoint
    endpoint = 'http://localhost:8080/otp/gtfs/v1'
    
    # Construct the GraphQL query
    query = """
    query EgQuery($time: String, $date: String, $from: InputCoordinates, $to: InputCoordinates, $numItineraries: Int, $walkReluctance: Float) {
      plan(
        time: $time
        date: $date
        from: $from
        to: $to
        transportModes: [
            {
                mode: WALK
            },
            {
                mode: TRANSIT
            },
        ]
        numItineraries: $numItineraries
        walkReluctance: $walkReluctance
      ) {
        itineraries {
          legs {
                mode
                startTime
                endTime
                from {
                    name
                    lat
                    lon
                    departureTime
                    arrivalTime
                }
                to {
                    name
                    lat
                    lon
                    departureTime
                    arrivalTime
                }
                route {
                    gtfsId
                    longName
                    shortName
                }
                legGeometry {
                    points
                }
            }
          duration
        }
      }
    }
    """

    # Define the variables for your query
    variables = {
        'time': '18:00:00',
        'date': '2023-06-01',
        'from': {'lat': from_lat, 'lon': from_lon},
        'to': {'lat': to_lat, 'lon': to_lon},
        'numItineraries': 1,
        'walkReluctance': 3.5
    }

    # Set up the headers
    headers = {
        'Content-Type': 'application/json'
    }

    # Send the request to the GraphQL API
    response = requests.post(endpoint, headers=headers, json={'query': query, 'variables': variables})

    # Check if the request was successful
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"GraphQL query failed to run with a {response.status_code}")


def apply_fetch_itinerary(row):
    try:
        response = fetch_itinerary(
            from_lat=row['Latitude_x'], 
            from_lon=row['Longitude_x'], 
            to_lat=row['Latitude_y'], 
            to_lon=row['Longitude_y']
        )
        bus_route = []
        # Extract relevant information from response
        if response and 'data' in response and 'plan' in response['data'] and 'itineraries' in response['data']['plan']:
            itinerary = response['data']['plan']['itineraries'][0]  # Taking the first itinerary
            duration = itinerary['duration'] if 'duration' in itinerary else None
            for leg in itinerary['legs']:
                # if leg['mode'] == 'BUS':
                    # Append bus route information for each bus leg
                from_stop = leg['from']['name']
                to_stop = leg['to']['name']
                bus_route.append(f"{from_stop} to {to_stop}")
                #bus_route.append(leg['route']['shortName'])
                #bus_route.append(f"{leg['legGeometry']['points']}")
            # Further extraction can be done based on the structure of your response
            return bus_route, duration/60  # Convert seconds to minutes
        else:
            return None, None
    except Exception as e:
        print(f"Error fetching itinerary: {e}")
        return None, None
    

def extract_td_contents(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    rows = table.find_all('tr')

    td_contents = []
    for row in rows:
        cells = row.find_all('td')
        for cell in cells:
            td_contents.append(cell.text.strip())

    return td_contents