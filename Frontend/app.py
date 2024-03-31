from shiny import App, Inputs, Outputs, Session, reactive, render, ui
import shinyswatch
from shinywidgets import output_widget, render_widget
#import shinyswatch
from htmltools import HTMLDependency
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import os
import geopandas as gpd
from shapely import Point 
import json 
from bs4 import BeautifulSoup
from pathlib import Path

app_ui = ui.page_navbar(
    shinyswatch.theme.minty(),
    ui.nav_panel("Sub-Problem 1: Cycling infrastructure suitability index","a"),
    ui.nav_panel("Sub-Problem 2: Last Mile Acessibility Index",
                 ui.h2("Rankings by Planning Area"),
                 ui.input_select("metrics", "Select metric for comparison", 
                                 choices=["suitability", "time savings", "weighted score"],
                                 selected = "suitability"),
                ui.layout_columns(
                    ui.card(
                        output_widget("chloropeth_map")
                    ),
                    ui.card(
                    )
                )   
    ),
    ui.nav_panel("Sub-Problem 3: Isochrone Analysis",
                 "c"
    ),
    title = "DSE3101 Cycle",
    bg= "#20c997"
    )

def server(input, output, session):

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

    current_directory = os.getcwd()
    data_directory = os.path.join(current_directory, 'data')

    basemap = gpd.read_file(os.path.join(data_directory, 'MasterPlan2019PlanningAreaBoundaryNoSea.geojson'))
    basemap['Planning_Area'] = basemap["Description"].apply(lambda x:extract_td_contents(x)[0])
    basemap['geometry'] = basemap['geometry'].to_crs("4326")

    mrt_stations_df = pd.read_csv(os.path.join(data_directory, 'Cluster_data','mrt_station_final.csv'),usecols = [1,2,3])
    mrt_stations_df.sort_values(by='MRT.Name', inplace=True)
    ranking = pd.read_csv(os.path.join(data_directory,'Cluster_data','mrt_ranking.csv'))

    mrt_stations_df_combined = pd.merge(mrt_stations_df, ranking, left_on='MRT.Name', right_on='MRT.Name', how='left')
    for index, row in mrt_stations_df_combined.iterrows():
        point_coordinate = Point(row['Longitude'], row['Latitude'])
        Planning_Area = basemap[basemap.geometry.contains(point_coordinate)]['Planning_Area'].reset_index(drop=True)
        mrt_stations_df_combined.loc[index, 'Planning_Area'] = Planning_Area.values[0]

    mrt_stations_df_combined = mrt_stations_df_combined.rename(columns = {'MRT.Name':'MRT Name',
                                                                        'time_difference':'time savings',
                                                                        'Weighted_Score':'weighted score'})
    
    path_metrics = pd.read_csv(os.path.join(data_directory, 'path_metrics.csv'))
    path_metrics = path_metrics.astype(str)

    @output 
    @render_widget
    def chloropeth_map():
        df = mrt_stations_df_combined.groupby('Planning_Area').agg({input.metrics():'mean'}).reset_index()
        basemap_modified = pd.merge(basemap, df, left_on='Planning_Area', right_on='Planning_Area', how='left')
        fig = go.Figure()
        fig.add_trace(go.Choroplethmapbox(geojson=json.loads(basemap_modified.geometry.to_json()), 
                                   locations=basemap_modified.index,
                                   z=basemap_modified[input.metrics()],
                                   colorscale='RdYlGn',
                                   hoverinfo = 'text',
                                   text = ("Planning Area: " + basemap_modified['Planning_Area'] + '<br>' + 
                                           "Average " + input.metrics() + " of paths within the area: " + basemap_modified[input.metrics()].astype(str) )))
        
        fig.add_trace(go.Scattergeo(geojson=json.loads(basemap_modified.geometry.to_json()),
                                    locations = basemap_modified.index,
                                    featureidkey= 'properties.index',
                                    text = basemap_modified['Planning_Area'],
                                    mode = 'text',))

        fig.update_layout(
            margin={'l':0,'t':0,'b':0,'r':0},
            mapbox={
                'style': "open-street-map",
                'center': {'lat': 1.36, 'lon': 103.85},
                'zoom': 10
            }
        )
        return fig
    
    @output
    @render.data_frame
    def path_metric():
        return render.DataTable(path_metrics,width = "50%",height = "300px")

app = App(app_ui, server)

if __name__ == "__main__":
    app.run()


