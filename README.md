# CycleNation: Public Transportation In Singapore

Welcome to our DSE3101 project! We are The Justins, a team of eager and curious data science undergraduates.

## Project Overview

With a greater emphasis on a car-lite society, this project aims to answer the following problem statement:

How can we quantify bicycle accessibility by district, and therefore identify and provide recommendations for revamping cycling infrastructure by district?

The project comprises of three sub-problems to deal with the problem:

**Sub-Problem 1 (SP1)**: Cycling Infrastructure Quality Index. 

In creating this index, we will utilise many infrastructural factors to compute an overall ranking for each subzone. This will help to identify which areas in Singapore are lacking in cycling infrastructures.

**Sub-Problem 2 (SP2))**: Last-Mile Connectivity Assessment. 

For this assessment, we will analyse the average distance from residential centroids to the nearest MRT stations within each district via cycling lanes and footpaths. This is to decide which areas in Singapore may benefit from the development of additional cycling lanes or improved pedestrian pathways.

**Sub-Problem 3 (SP3)**: Multimodal Transport Alternatives Analysis. 

In this analysis, we will compare the coverage and effectiveness of alternatives such as bus routes and pedestrian paths from MRT/ LRT stations given a particular time limit.

## Frontend

## Backend

residential_data.ipynb

- generate residential clusters via K-means clustering

mrtstations.py

* consolidate MRT station coordinates
* We combine from data.gov.sg as well as OneMap API, in order to validate that our data is up to date

#### SP2

Pairing of MRT and Residential Clusters

* uses OneMap, ORS and OTP APIs to get data required for SP2 visualisation
* Data cleaning performed
* Pairing is performed for both n(5) pairing method and individual pairing method.

MRT Rankings

* Here we formulated our SP2 weighted score function

#### SP3

SP3_generate_isochrones.ipynb

Here we write API calling function for OTP's Isochrone API.

We iteratively call and save the following Isochrones from 10min-60min, across 5min intervals

* Cycling
* Bus + Walk
* MRT + Walk
* Public Transport + Walk

note: SP3/app.py contains our draft implementation of subproblem 3

## Data

All our data is taken from the scraped via:

- API:
  - OneMap: https://www.onemap.gov.sg/apidocs/apidocs/
  - LTA Datamall: https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html
  - OpenRouteService: https://openrouteservice.org/dev/#/api-docs/
  - OpenTripPlanner: https://docs.opentripplanner.org/en/v2.5.0/
- Downloaded from Web:
  - Residential, MRT station coordinates: data.gov.sg
  - Open Street Map data: GeoFabrik: https://download.geofabrik.de/asia/malaysia-singapore-brunei.html
  - LTA's General Transit Feed Specification (GTFS): Transitland: https://www.transit.land/feeds/f-w21z-lta

## Set Up

#### OTP

- https://docs.opentripplanner.org/en/v2.5.0/Basic-Tutorial/

## Acknowledgements
