# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from zipfile import ZipFile
from cleaning import *
from spoofing_detection import *
from visualizations import *

import os
import json
import shutil
app = Flask(__name__)

# Function to load column mappings
def load_column_mappings():
    config_path = 'column_mappings.json'  # Path to your config file
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            column_mappings = json.load(f)
        return column_mappings
    else:
        return {}  # Return an empty dict if the config file does not exist




app = Flask(__name__)

@app.route('/cleaning', methods=['POST'])

def clean_data():
    # Check if a file was posted
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']

    # If no file is selected
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    file.save(filename)

    column_mappings = load_column_mappings()
    # Load the data from the file
    data = pd.read_csv(filename)
    data.rename(columns=column_mappings, inplace=True)


    # Load the data from the file
    data = pd.read_csv(filename)


    line_data = pd.DataFrame(data)

    # cleaning
    line_data = rm_invalid_movements(rm_empty(line_data))

    # spoofing detection
    mmsi_set = set(line_data['shipid'].unique())
    spoof_data = pd.DataFrame(
        columns=["MMSI", "hasProblem", "hasLocationSpoofing", "hasIdentitySpoofing", "CountOfClusters"])
    count = 0
    for mmsi in mmsi_set:
        df_temp = line_data.copy()
        df_temp = df_temp[df_temp['shipid'] == mmsi]
        df_temp.rename(columns={'lon': 'x', 'lat': 'y', 't': '# Timestamp'}, inplace=True)
        df_temp['# Timestamp'] = pd.to_datetime(df_temp['# Timestamp'])
        hasProblem, hasLocationSpoofing, hasIdentitySpoofing, numberOfClusters = get_cluster_insights(df_temp, 5, mmsi)
        new_row = {'MMSI': mmsi, 'hasProblem': hasProblem, 'hasLocationSpoofing': hasLocationSpoofing,
                   'hasIdentitySpoofing': hasIdentitySpoofing, 'CountOfClusters': numberOfClusters}
        spoof_data.loc[count] = new_row
        count += 1


    vis_data = line_data.rename(columns={'shipid': 'MMSI', 'lon': 'x', 'lat':'y', 't': '# Timestamp'})
    
    outliers_dir = "Clusters"
    #map_output_filename = 'map_visualization.html'
    #plot_on_a_map(vis_data, spoof_data, outliers_dir, output_file=map_output_filename)

    
    problem_mmsis = spoof_data[spoof_data['hasProblem'] == True]['MMSI'].unique()

# Plot individual maps for each MMSI with problems
    for mmsi in problem_mmsis:
        plot_mmsi_map(vis_data, mmsi, outliers_dir, output_file_prefix='mmsi_visualization')

    # area of interest selection
    line_data.rename(columns={v: k for k, v in column_mappings.items()}, inplace=True)
      


    # area of interest selection
    line_data.rename(columns={'shipid': 'MMSI'}, inplace=True)
    constrained_region_df = spoof_data.merge(line_data, on=['MMSI'], how='inner')

    world = geopandas.read_file(geopandas.datasets.get_path('naturalearth_lowres'))
    greece = world[world['name'] == 'Greece']['geometry'].values[0]

    constrained_region_df = areas_of_interest(constrained_region_df, greece, lat_col_name='lat', long_col_name='lon')

    # visualization
    constrained_region_df['t'] = pd.to_datetime(constrained_region_df['t'])

    # TODO: Add a way to return the visualization or save it to a file


    # Save cleaned data to CSV files
    line_data.to_csv('cleaned_data.csv')
    spoof_data.to_csv('spoof_status.csv')


    with ZipFile('cleaned_data.zip', 'w') as zipf:
        # Add multiple files to the zip
        zipf.write('cleaned_data.csv')
        zipf.write('spoof_status.csv')

        #zipf.write(map_output_filename)
        
        # Add individual MMSI maps to the zip file
        for mmsi in problem_mmsis:
            mmsi_map_filename = f"mmsi_visualization_{mmsi}.html"
            zipf.write(mmsi_map_filename)
        
        if os.path.exists("Clusters"):
            for filename in os.listdir("Clusters"):
                if filename.endswith("_outlier.csv"):
                    zipf.write(os.path.join("Clusters", filename))
                    
    for mmsi in problem_mmsis:
        mmsi_map_filename = f"mmsi_visualization_{mmsi}.html"
        os.remove(mmsi_map_filename)


    # Delete CSV files after creating zip
    os.remove('cleaned_data.csv')
    os.remove('spoof_status.csv')

    shutil.rmtree("Clusters")
    #os.remove('map_visualization.html')


    # Send zip file
    return send_file('cleaned_data.zip', mimetype='zip', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
