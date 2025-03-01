from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)
CORS(app)
wsgi_app = app.wsgi_app

# Global variable to store filtered data
cached_data = []
solar_data = None
time_data = None

def load_and_filter_data():
    """Loads and filters data for the 24-hour period from exactly one year ago."""
    global cached_data
    global solar_data
    global time_data

    while True:
        try:

            now = datetime.now()
            one_year_ago = now - timedelta(days=365)
            start_time = one_year_ago - timedelta(hours=24)
            end_time = one_year_ago

            #read in data and condition timestamps/////////////////////////////////////////////////////////////
            df = pd.read_excel("AMG_Solar_2022_2023_2024.xlsx", sheet_name="2024", header=2)  # Load Excel file
            df['Date and Time'] = pd.to_datetime(df['Date and Time']) #NOTE: We may want to make sure that the data in column C is 'OK' and not 'UNRELIABLE'. Maybe add a filter to multiply unreliable data by 0.
            #//////////////////////////////////////////////////////////////////////////////////////////////////

                # Filter data for the exact 24-hour window
            df_filtered = df[(df['Date and Time'] >= start_time) & (df['Date and Time'] <= end_time)]
            df_filtered = df_filtered[['Date and Time', 'Value (KW)']]
            df_filtered['Value (KW)'] = -df_filtered['Value (KW)']
            
            df_solar = df_filtered['Value (KW)']
            solar_data = df_solar.to_numpy()
            df_time = df_filtered['Date and Time']
            time_data = df_time.to_numpy()
            #///////////////////////////////////////////////////////////////////////////////////////////
            ##if you need to expose further data sets do so here in the way I did in the section above
            ##use variable one year ago as the reference point for the end of the data set currently analyzed

            #///////////////////////////////////////////////////////////////////////////////////////////
            # Convert DataFrame to JSON
            cached_data = df_filtered.to_dict(orient="records")
            print(f"Data updated for {start_time} to {end_time}")  # Log the update

        except Exception as e:
            print(f"Error updating data: {e}")
        time.sleep(60)  # Wait for 1 minute before updating again

#continually run above method to update data each min
threading.Thread(target=load_and_filter_data, daemon=True).start()

#raw solar data
@app.route('/data', methods=['GET'])
def get_solar():
    """Returns the cached data for the last 24 hours from one year ago."""
    return jsonify(cached_data)

#///////////////////////////////////////////////////////////////////////////////////////////
#new method guide
#general format is as follows
#route line, this is the page the api is accessable from
#function definition, this is where you will do your calculations// as follows
#
#@app.route('/your_name_here'), methods=['GET'])
#def your_function_name():
#   if INPUTS is not None:                      //This is needed as data initially is not populated from csv file
#           
#        Your calculations
#
#        return jsonify(OUTPUT_NUMPY_ARRAY.tolist())  # Convert NumPy array back to list for JSON
#   else:
#       return jsonify({"error": "Data not available yet"}), 500
#
#
# you can also provide arguments to your functions as such
#     start_time = request.args.get('start_time')
#     end_time = request.args.get('end_time')
#
#and a call to the api would look like this message in the terminal
#GET /data?start_time=2024-02-25%2022:00&end_time=2024-02-26%2022:00
#
#worth noting that currently there is no method to dynamically fetch specific days, this can be implemented if needed though
#///////////////////////////////////////////////////////////////////////////////////////////
#your code Here:                                                                                                              

#good method --
#key points: for dev ease put the name of the method in /your_name_here
#draw data from solar_data as thats the live numpy array i pulled from data
#worth noting that a second copy of this should probably be made to pull from selection data
#this functionality is not yet had, will remove this comment when it is.

@app.route('/30_30'), methods=['GET']) 
def Persistence_30_30():
  if solar_data is not None:                      #This is needed as data initially is not populated from csv file
          
    data = solar_data
    prediction = np.zeros(60) 
    for hour in range((int)(len(data)/60)): #note that all my functions assume the data starts at the first minute of an hour.
        refhalfhour = data[(hour)*60:(hour+1)*60-30]
        predictvalue = np.mean(refhalfhour)
        if (hour == (int)(len(data)/60 - 1)): #Ensures that the prediction continues to the current hour even if the hour is not over
            prediction = np.append(prediction, np.ones(len(data)-len(prediction))*predictvalue)
        else:
            prediction = np.append(prediction, np.ones(60)*predictvalue)
        

    return jsonify(prediction.tolist())  # Convert NumPy array back to list for JSON
 else:
    return jsonify({"error": "Data not available yet"}), 500

#///////////////////////////////////////////////////////////////////////////////////////////

#///////////////////////////////////////////////////////////////////////////////////////////
#worth noting that a second copy of this should probably be made to pull from selection data
#this functionality is not yet had, will remove this comment when it is.

@app.route('/30_60'), methods=['GET']) 
def Persistence_30_60():
  if solar_data is not None:                      #This is needed as data initially is not populated from csv file
          
    data = solar_data
    prediction = np.zeros(60)
    for hour in range((int)(len(data)/60)):
        refmin = data[(hour)*60+29:(hour)*60+30]
        predictvalue = np.mean(refmin)
        if (hour == (int)(len(data)/60 - 1)):
            prediction = np.append(prediction, np.ones(len(data)-len(prediction))*predictvalue)
        else:
            prediction = np.append(prediction, np.ones(60)*predictvalue)
        

    return jsonify(prediction.tolist())  # Convert NumPy array back to list for JSON
 else:
    return jsonify({"error": "Data not available yet"}), 500

#///////////////////////////////////////////////////////////////////////////////////////////

#///////////////////////////////////////////////////////////////////////////////////////////
#worth noting that a second copy of this should probably be made to pull from selection data
#this functionality is not yet had, will remove this comment when it is.

@app.route('/day_before'), methods=['GET']) 
def Persistence_day_before():
  if solar_data is not None:                      #This is needed as data initially is not populated from csv file
          
    data = solar_data
    prediction = np.zeros(1440)
    for hour in range((int)(len(data)/60 - 23)):
        refhour = data[(hour)*60:(hour+1)*60]
        predictvalue = np.mean(refhour)
        if (hour == (int)(len(data)/60 - 24)):
            prediction = np.append(prediction, np.ones(len(data)-len(prediction))*predictvalue)
        else:
            prediction = np.append(prediction, np.ones(60)*predictvalue)
        

    return jsonify(prediction.tolist())  # Convert NumPy array back to list for JSON
 else:
    return jsonify({"error": "Data not available yet"}), 500

#///////////////////////////////////////////////////////////////////////////////////////////


@app.route('/selecteddate', methods=['GET'])
def get_selected_date_data():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not start_date or not end_date:
        return jsonify({"error": "Start and end dates are required"}), 400

    try:
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d') # I am not sure exactly how this function works, but it may be a good idea to load up data for a day before the chosen date since a lot of our methods
                                                                   # require data from the previous day, and it would look like we aren't predicting anything for the first day. If we start predicting the day before and just
                                                                   # don't display the data or prediction from that day we could avoid the problem.
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include the end date

        df = pd.read_excel("AMG_Solar_2022_2023_2024.xlsx", sheet_name="2024", header=2)
        df['Date and Time'] = pd.to_datetime(df['Date and Time'])
        
        df_filtered = df[(df['Date and Time'] >= start_datetime) & (df['Date and Time'] < end_datetime)]
        df_filtered = df_filtered[['Date and Time', 'Value (KW)']]
        df_filtered['Value (KW)'] = -df_filtered['Value (KW)']
        
        return jsonify(df_filtered.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/')
def hello():
    return "API is running! Access past 24-hour data at /data"

if __name__ == '__main__':
    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(host=HOST, port=PORT, debug=False)
