# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from zipfile import ZipFile
from cleaning import *
from spoofing_detection import *
from visualizations import *

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
    # Create a ZipFile object
    with ZipFile('cleaned_data.zip', 'w') as zipf:
        # Add multiple files to the zip
        zipf.write('cleaned_data.csv')
        zipf.write('spoof_status.csv')

    # Delete CSV files after creating zip
    os.remove('cleaned_data.csv')
    os.remove('spoof_status.csv')

    # Send zip file
    return send_file('cleaned_data.zip', mimetype='zip', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
