# Data Cleaning
This application applies data cleaning methods in AIS datasets. It takes as input an AIS dataset (e.g. in .csv format) and returns a cleansed dataset along with a table of identified spoofing events and a relevant visualization.

## Instructions
Download the application from this repository. The input data must contain AIS data with the following features: t: timestamp, shipid: MMSI or anonymized ship id, lon: Longitude, lat: latitude, heading, course, speed. If the AIS dataset contains different column names go to column_mappings.json and change the left column to fill the correct ones from your dataset.

### Run the application

In the directory where the Data Cleaning application is located run the following commands:

Build the docker image
```
docker build -t my-cleaning-app .

```
Run the docker container
```
docker run -p 5000:5000 my-cleaning-app
```
The application expects to receive a CSV file via a POST request to the /cleaning endpoint. It returns a .zip file containing a cleaned_data.csv and a spoof_status.csv

```
curl -X POST -F file=@yourfile.csv http://localhost:5000/cleaning --output cleaned_data.zip

```
