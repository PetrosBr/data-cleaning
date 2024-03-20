import folium
import os
import pandas as pd

import folium
import os
import pandas as pd

def plot_on_a_map(data, spoof_data, outliers_dir, mmsi_col_name='MMSI', time_col_name='t', 
                  attr_col_line='hasProblem', long_col_name='x', lat_col_name='y', 
                  output_file='map_visualization.html'):
    """
    Plots data on a map, highlighting specific spoofed data points.
    """
    m = folium.Map(location=[0, 0], zoom_start=2, tiles='OpenStreetMap')

    # Plot each point for trajectories instead of using polyline
    for _, row in data.iterrows():
        # Base color for the point
        folium.CircleMarker(location=[row[lat_col_name], row[long_col_name]], 
                            radius=2, # Adjust the size of the dot as needed
                            color='blue', fill=True).add_to(m)

    # Highlight specific spoofed points
    for _, row in spoof_data.iterrows():
        if row[attr_col_line]:  # Check if the row indicates spoofing
            mmsi = row[mmsi_col_name]
            outlier_file = f"{outliers_dir}/{mmsi}_outlier.csv"
            if os.path.exists(outlier_file):
                df_outliers = pd.read_csv(outlier_file)
                for _, outlier in df_outliers.iterrows():
                    folium.CircleMarker(location=[outlier[lat_col_name], outlier[long_col_name]],
                                        radius=5, color='red', fill=True,
                                        popup=f"MMSI: {mmsi}\n{'Location' if row['hasLocationSpoofing'] else 'Identity'} Spoofing").add_to(m)

    m.save(output_file)





def plot_mmsi_map(data, mmsi, outliers_dir, long_col_name='x', lat_col_name='y', output_file_prefix='mmsi_visualization'):
    """
    Generates a map for a single MMSI, plotting normal trajectory points in blue and spoofed points in red.
    """
    m = folium.Map(location=[0, 0], zoom_start=2, tiles='OpenStreetMap')
    group = data[data['MMSI'] == mmsi]
    
    # Plot normal trajectory points in blue
    for _, row in group.iterrows():
        folium.CircleMarker(location=[row[lat_col_name], row[long_col_name]],
                            radius=2, color='blue', fill=True).add_to(m)
    
    # Plot spoofed data points in red
    outlier_file = f"{outliers_dir}/{mmsi}_outlier.csv"
    if os.path.exists(outlier_file):
        df_outliers = pd.read_csv(outlier_file)
        for _, outlier in df_outliers.iterrows():
            folium.CircleMarker(location=[outlier[lat_col_name], outlier[long_col_name]],
                                radius=5, color='red', fill=True,
                                popup=f"MMSI: {mmsi} Spoofing").add_to(m)

    output_file = f"{output_file_prefix}_{mmsi}.html"
    m.save(output_file)
