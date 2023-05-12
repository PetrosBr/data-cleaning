# Data Cleaning
This application applies data cleaning methods in AIS datasets. It takes as input an AIS dataset (e.g. in .csv format) and returns a cleansed dataset along with a table of identified spoofing events and a relevant visualization.

## Instructions
Install the application from this repository. Place a .csv file that contains AIS data with the following features: t: timestamp, shipid: MMSI or anonymized ship id, lon: Longitude, lat: latitude, heading, course, speed.

### Run the application

In the directory where the Data Cleaning application is located run:
```
python complete_pipeline.py
```


```