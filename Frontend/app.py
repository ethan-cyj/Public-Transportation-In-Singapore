from shiny import App, render, ui
from shinyswatch import theme
import pandas as pd
import os
from shinywidgets import output_widget, render_widget
import plotly.graph_objs as go
import geopandas as gpd
from shapely import Point
import json 
from bs4 import BeautifulSoup

current_directory = os.getcwd()
data_directory = os.path.join(current_directory, 'data')
isochrone_directory = os.path.join(current_directory, 'data/Isochrone_data')
file_path1 = os.path.join(isochrone_directory, 'mrt_station_colours.csv')
mrt_df = pd.read_csv(file_path1)
new_color_map = {
    'red': '#cb2721',
    'yellow': '#e69c3d',
    'green': '#159048',
    'blue': '#0b569d',
    'purple': '#7d4687',
    'brown': '#a67440',
    'grey': '#7c8981',
}


mrt_df['Color'] = mrt_df['Color'].map(new_color_map)
bus_isochrones = pd.read_json(os.path.join(isochrone_directory, 'bus_isochrones_new.json'), orient='records', lines=True)
bicycle_isochrones = pd.read_json(os.path.join(isochrone_directory, 'bicycle_isochrones_new.json'), orient='records', lines=True)
mrt_isochrones = pd.read_json(os.path.join(isochrone_directory, 'mrt_isochrones_new.json'), orient='records', lines=True)
public_transport_isochrones = pd.read_json(os.path.join(isochrone_directory, 'public_isochrones_new.json'), orient='records', lines=True)
mrt_names = mrt_df['MRT.Name'].values.tolist()
coords = mrt_df[['Latitude', 'Longitude']].values.tolist()
basemap = gpd.read_file(os.path.join(data_directory, 'MasterPlan2019PlanningAreaBoundaryNoSea.geojson'))
mrt_stations_df = pd.read_csv(os.path.join(data_directory, 'Cluster_data','mrt_station_final.csv'),usecols = [1,2,3])
cluster_ranking = pd.read_csv(os.path.join(data_directory,'Cluster_data','5_cluster_mrt_ranking.csv'))


app_ui = ui.page_navbar(
    theme.minty(),
    ui.nav_panel("Sub-Problem 1: Cycling infrastructure suitability index","a"),
    ui.nav_panel("Sub-Problem 2: Last Mile Acessibility Index",
                 ui.h2("Rankings by Planning Area"),
                 ui.input_select("metrics", "Select Metric for Comparison", 
                                 choices=["Distance","Suitability", "Time Savings", "Weighted Score"],
                                 selected = "Distance"),
                ui.layout_columns(
                    ui.card(
                        output_widget("chloropeth_map")
                    ),
                    ui.card(
#                        ui.output_data_frame("path_metric")
                    )
                )),
    ui.nav_panel("Sub-Problem 3: Isochrone Analysis",
                ui.h2("Distance Travellable from MRT/LRT Stations"),
                ui.page_sidebar(
                ui.sidebar(ui.input_selectize(
                    "transport_means",
                    "Select the Means of Movement (Limit to 2 Options)",
                    ["Bus", "Bicycle", "MRT", "Public Transport"],
                    multiple=True,
                    options = dict(maxItems = 2),
                ),ui.input_selectize(
                    "station",
                    "Select the MRT/LRT station",
                    mrt_names,
                    multiple=True
                ),
                # Set step to 5 for intervals of 5 minutes
                ui.input_slider(
                    "n_min",
                    "Select Maximum Time (in minutes)",
                    min=10, max=60, value=5, step=5
                ), 
                bg="#f8f8f8"
                ),
                ui.output_text_verbatim("txt"),
                output_widget("plot")
                )
                ),
    title = "DSE3101 Cycle",
    bg= "#20c997"
)

def server(input, output, session):
    #SP2 Functions
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

    basemap = gpd.read_file(os.path.join(data_directory, 'MasterPlan2019PlanningAreaBoundaryNoSea.geojson'))
    mrt_stations_df = pd.read_csv(os.path.join(data_directory, 'Cluster_data','mrt_station_final.csv'),usecols = [1,2,3])
    cluster_ranking = pd.read_csv(os.path.join(data_directory,'Cluster_data','5_cluster_mrt_ranking.csv'))
    
    basemap['Planning_Area'] = basemap["Description"].apply(lambda x:extract_td_contents(x)[0])
    basemap['geometry'] = basemap['geometry'].to_crs("4326")

    mrt_stations_df.sort_values(by='MRT.Name', inplace=True)
    
    for index, row in cluster_ranking.iterrows():
        point_coordinate = Point(row['Longitude'], row['Latitude'])
        Planning_Area = basemap[basemap.geometry.contains(point_coordinate)]['Planning_Area'].reset_index(drop=True)
        cluster_ranking.loc[index, 'Planning_Area'] = Planning_Area.values[0]

    cluster_ranking = cluster_ranking.rename(columns = {'MRT.Name':'MRT Name',
                                                        'time_difference':'Time Savings',
                                                        'Weighted_Score':'Weighted Score',
                                                        'suitability':'Suitability',
                                                        'distance':'Distance'})
    
    path_metrics = pd.read_csv(os.path.join(data_directory, 'path_metrics.csv'))
    path_metrics = path_metrics.astype(str)

    @output 
    @render_widget
    def chloropeth_map():
        df = cluster_ranking.groupby('Planning_Area').agg({input.metrics():'mean'}).reset_index()
        basemap_modified = pd.merge(basemap, df, left_on='Planning_Area', right_on='Planning_Area', how='left')
        fig = go.Figure()
        fig.add_trace(go.Choroplethmapbox(geojson=json.loads(basemap_modified.geometry.to_json()), 
                                   locations=basemap_modified.index,
                                   z=basemap_modified[input.metrics()],
                                   colorscale='RdYlGn',
                                   hoverinfo = 'text',
                                   text = ("Planning Area: " + basemap_modified['Planning_Area'] + '<br>' + 
                                           "Average " + input.metrics() + " of Paths Within the Area: " + round(basemap_modified[input.metrics()],2).astype(str) )))

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
        return render.DataTable(path_metrics,width = "100%",height = "300px")

    


    #SP3
    def get_isochrone(name, mode, cutoff):
        variable_name = f"{mode}_isochrones"    
        df = globals()[variable_name] 
        filtered_df = df[(df['MRT.Name'] == name)]
        isochrone = filtered_df[f'isochrone_{cutoff}M'].iloc[0]
        return isochrone

    @render.text
    def txt():
        if len(input.transport_means()) == 2:
            transport_means1 = (input.transport_means())[0]
            transport_means2 = (input.transport_means())[1]
            # Generate the initial text string
            initial_text = f"You are trying to find the maximum distance that can be travelled within {input.n_min()} minutes by {transport_means1} and {transport_means2} from the following stations:"
            
            # Initialize an empty list to store the lines
            lines = [initial_text]
            
            # Iterate over each station in the tuple
            for station in input.station():
                lines.append(f"• {station.strip()}")
        
            # Join the lines with newline characters
            return '\n'.join(lines)
        else:
            # Generate the initial text string
            initial_text = f"You are trying to find the maximum distance that can be travelled within {input.n_min()} minutes by (Transport Means) from the following stations:"
            # Initialize an empty list to store the lines
            lines = [initial_text]
            # Iterate over each station in the tuple
            for transport_means in input.transport_means():
                lines[0] = f"You are trying to find the maximum distance that can be travelled within {input.n_min()} minutes by {input.transport_means()[0]} from the following stations:"
            for station in input.station():
                lines.append(f"• {station.strip()}")
        
            # Join the lines with newline characters
            return '\n'.join(lines)
    @render_widget
    def plot():
        fig = go.Figure()
        
        for _, row in mrt_df.iterrows():
            fig.add_trace(go.Scattermapbox(
                mode="markers",
                lon=[row['Longitude']],
                lat=[row['Latitude']],
                text=[row['MRT.Name']],
                name=row['MRT.Name'],
                marker=dict(size=6, color='grey'),  # Use a neutral color for all stations
                textposition="bottom center",
                hoverinfo='text'
            ))
        transportmeans_items = input.transport_means()
        # Fetch and add isochrones for each selected MRT station
        for mrt_name in input.station():
            for transport_means in input.transport_means():
                transport_ind = transportmeans_items.index(transport_means)
                if transport_ind == 0:
                    thickness = 1
                else:
                    thickness = 5
                if transport_means == "Public Transport":
                    transport_means = "Public_Transport"
                transport_means = transport_means.lower()
                # Extracting color and coordinates for the current MRT station
                station_row = mrt_df[mrt_df['MRT.Name'] == mrt_name].iloc[0]
                color = station_row["Color"]
                lat, lon = station_row['Latitude'], station_row['Longitude']
                
                # Convert cutoff to minutes, e.g. "15M" to 15
                cutoff = int(input.n_min())
                
                # Fetch the isochrone data
                isochrone = get_isochrone(name=mrt_name, mode=transport_means, cutoff=cutoff)
                lon_coords = [coord[0] for coord in isochrone]
                lat_coords = [coord[1] for coord in isochrone]
                    
                # Add isochrone as a trace
                fig.add_trace(go.Scattermapbox(
                    mode="lines",
                    lon=lon_coords,
                    lat=lat_coords,
                    name=f"Isochrone {lat}, {lon}",
                    line=dict(width=thickness, color=color),
                    fill="toself",
                    hoverinfo = "none"
                ))
                # Add MRT station as a marker
                fig.add_trace(go.Scattermapbox(
                    mode="markers",
                    lon=[lon],
                    lat=[lat],
                    text=[mrt_name],
                    name=mrt_name,
                    marker=dict(size=10, color=color),
                    textposition="bottom center",
                    hoverinfo='text'
                ))
                
        # Update the layout to match the provided example
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=12,
            mapbox_center={"lat": coords[0][0], "lon": coords[0][1]},
            showlegend=False,
            width=1300,
            height=600
        )
        if len(input.transport_means()) == 2:
            transportmeans1 = input.transport_means()[0]
            transportmeans2 = input.transport_means()[1]
            legend_items = {transportmeans1: {'color': 'black', 'width': 1}, transportmeans2: {'color': 'black', 'width': 5}}
            legend_box = go.layout.Shape(
                type="rect",
                x0=0.80,
                y0=0.8,
                x1=0.98,
                y1=0.95,
                fillcolor="white",
                opacity=1,
                line=dict(width=1)
            )
            fig.add_shape(legend_box)
            for i, (label, style) in enumerate(legend_items.items()):
                fig.add_shape(type='line', x0=0.82, y0=0.9-0.05*i, x1=0.86, y1=0.9-0.05*i,
                    line=dict(color=style['color'], width=style['width']))
                fig.add_annotation(x=0.87, y=0.9-0.05*i, xanchor='left', yanchor='middle',
                                text=label,
                                showarrow=False, font=dict(size=14, color='black'))
        
        # Show the figure
        return fig
            

app = App(app_ui, server)
if __name__ == "__main__":
    app.run()