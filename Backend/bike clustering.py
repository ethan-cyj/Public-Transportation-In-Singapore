from sklearn.cluster import KMeans
import numpy as np
import folium
import pandas as pd
bike_parking = pd.read_csv("unique_bicycle_parking_data.csv")
print(bike_parking)

bike_park_coords = np.array(bike_parking[['Latitude', 'Longitude']])

n_clusters = 55*5

# Perform K-means clustering
bikepark_kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(bike_park_coords)
bikepark_centroids = bikepark_kmeans.cluster_centers_

# Initialize the map centered around Singapore
# The center is an approximate central point (you may adjust it based on your data)
sg_map = folium.Map(location=[1.3521, 103.8198], zoom_start=12)

# Plot HDB cluster centroids in blue
for coord in bikepark_centroids:
    folium.CircleMarker(
        location=[coord[0], coord[1]],
        radius=5,
        color='blue',
        fill=True,
        fill_color='blue',
        fill_opacity=0.6
    ).add_to(sg_map)

# Display the map
sg_map.save('cluster_centroids_map.html')