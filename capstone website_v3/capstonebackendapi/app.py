from re import S
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

solar_data_selected = None
time_data_selected = None

def load_and_filter_data():
    """Loads and filters data for a 48-hour period into solar_data/time_data, and the last 24 hours into cached_data."""
    global cached_data
    global solar_data
    global time_data

    while True:
        try:
            now = datetime.now()
            one_year_ago = now - timedelta(days=365)
            start_time_48h = one_year_ago - timedelta(hours=48)  # Start of the 48-hour window
            start_time_24h = one_year_ago - timedelta(hours=24)  # Start of the 24-hour window
            end_time = one_year_ago                             # End of both windows (one year ago)

            # Read in data and condition timestamps
            df = pd.read_excel("AMG_Solar_2022_2023_2024.xlsx", sheet_name="2024", header=2)
            df['Date and Time'] = pd.to_datetime(df['Date and Time'])

            # Filter data for the full 48-hour window (for solar_data and time_data)
            df_filtered_48h = df[(df['Date and Time'] >= start_time_48h) & (df['Date and Time'] <= end_time)]
            df_filtered_48h = df_filtered_48h[['Date and Time', 'Value (KW)']]
            df_filtered_48h['Value (KW)'] = -df_filtered_48h['Value (KW)']

            # Assign the 48-hour data to solar_data and time_data
            df_solar = df_filtered_48h['Value (KW)']
            solar_data = df_solar.to_numpy()
            df_time = df_filtered_48h['Date and Time']
            time_data = df_time.to_numpy()

            # Filter data for the last 24-hour window (for cached_data)
            df_filtered_24h = df[(df['Date and Time'] >= start_time_24h) & (df['Date and Time'] <= end_time)]
            df_filtered_24h = df_filtered_24h[['Date and Time', 'Value (KW)']]
            df_filtered_24h['Value (KW)'] = -df_filtered_24h['Value (KW)']

            # Convert the 24-hour DataFrame to JSON for cached_data
            cached_data = df_filtered_24h.to_dict(orient="records")
            print(f"48-hour data updated for {start_time_48h} to {end_time}")
            print(f"24-hour cached data updated for {start_time_24h} to {end_time}")

        except Exception as e:
            print(f"Error updating data: {e}")
        time.sleep(60)  # Wait for 1 minute before updating again

# Continually run the method to update data each minute
threading.Thread(target=load_and_filter_data, daemon=True).start()


#raw solar data
@app.route('/data', methods=['GET'])
def get_solar():
    """Returns the cached data for the last 24 hours from one year ago."""
    return jsonify(cached_data)



@app.route('/selecteddate', methods=['GET'])
def get_selected_date_data():
    global solar_data_selected, time_data_selected

    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not start_date or not end_date:
        return jsonify({"error": "Start and end dates are required"}), 400

    try:
        # Parse the selected date range
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include the end date

        # Extend the start time by 24 hours for solar_data_selected and time_data_selected
        extended_start_datetime = start_datetime - timedelta(hours=24)

        # Load and preprocess the Excel data
        df = pd.read_excel("AMG_Solar_2022_2023_2024.xlsx", sheet_name="2024", header=2)
        df['Date and Time'] = pd.to_datetime(df['Date and Time'])

        # Filter for the extended 48-hour window (for solar_data_selected and time_data_selected)
        df_filtered_extended = df[(df['Date and Time'] >= extended_start_datetime) & (df['Date and Time'] < end_datetime)]
        df_filtered_extended = df_filtered_extended[['Date and Time', 'Value (KW)']]
        df_filtered_extended['Value (KW)'] = -df_filtered_extended['Value (KW)']

        # Assign the 48-hour data to solar_data_selected and time_data_selected
        df_solar_select = df_filtered_extended['Value (KW)']
        solar_data_selected = df_solar_select.to_numpy()
        df_time_select = df_filtered_extended['Date and Time']
        time_data_selected = df_time_select.to_numpy()

        # Filter for the original 24-hour window (for API response)
        df_filtered_api = df[(df['Date and Time'] >= start_datetime) & (df['Date and Time'] < end_datetime)]
        df_filtered_api = df_filtered_api[['Date and Time', 'Value (KW)']]
        df_filtered_api['Value (KW)'] = -df_filtered_api['Value (KW)']

        # Return only the selected 24-hour range to the API
        return jsonify(df_filtered_api.to_dict(orient="records"))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

@app.route('/30_30', methods=['GET'])
def Persistence_30_30():
    global time_data, solar_data
    if solar_data is not None and time_data is not None:
        data = solar_data[1440:]
        prediction = np.zeros(60)
        for hour in range((int)(len(data)/60 - 1)):
            refhalfhour = data[(hour)*60:(hour+1)*60-30]
            predictvalue = np.mean(refhalfhour)
            prediction = np.append(prediction, np.ones(60)*predictvalue)
        
        # Trim prediction to match the length of time_data
        prediction = prediction[:len(time_data[1440:])]
        
        # Create a list of dictionaries with timestamp and prediction value
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/30_30selected', methods=['GET'])
def Persistence_30_30_selected():
    global time_data_selected, solar_data_selected
    if solar_data_selected is not None and time_data_selected is not None:
        data = solar_data_selected[1440:]
        prediction = np.zeros(60)
        for hour in range((int)(len(data)/60 - 1)):
            refhalfhour = data[(hour)*60:(hour+1)*60-30]
            predictvalue = np.mean(refhalfhour)
            prediction = np.append(prediction, np.ones(60)*predictvalue)
        
        # Trim prediction to match the length of time_data
        prediction = prediction[:len(time_data_selected[1440:])]
        
        # Create a list of dictionaries with timestamp and prediction value
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500


#///////////////////////////////////////////////////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////////////////////////
#worth noting that a second copy of this should probably be made to pull from selection data
#this functionality is not yet had, will remove this comment when it is.

@app.route('/30_60', methods=['GET'])
def Persistence_30_60():
    global time_data, solar_data
    if solar_data is not None and time_data is not None:  # Check both solar_data and time_data
        data = solar_data[1440:]  # Use only the last 24 hours (assuming 2880 total minutes)
        prediction = np.zeros(60)  # Initial 60 zeros for the first hour
        for hour in range((int)(len(data) / 60)):
            refmin = data[(hour) * 60 + 29:(hour) * 60 + 30]  # 30th minute of the hour
            predictvalue = np.mean(refmin)
            if hour == (int)(len(data) / 60 - 1):  # Last partial hour
                remaining_length = len(data) - len(prediction)
                prediction = np.append(prediction, np.ones(remaining_length) * predictvalue)
            else:
                prediction = np.append(prediction, np.ones(60) * predictvalue)

        # Trim prediction to match the length of time_data[1440:]
        prediction = prediction[:len(time_data[1440:])]

        # Create a list of dictionaries with timestamp and prediction value
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], prediction)]

        return jsonify(result)  # Return as JSON

    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/30_60selected', methods=['GET'])
def Persistence_30_60_selected():
    global time_data_selected, solar_data_selected
    if solar_data_selected is not None and time_data_selected is not None:  # Check both solar_data and time_data
        data = solar_data_selected[1440:]  # Use only the last 24 hours (assuming 2880 total minutes)
        prediction = np.zeros(60)  # Initial 60 zeros for the first hour
        for hour in range((int)(len(data) / 60)):
            refmin = data[(hour) * 60 + 29:(hour) * 60 + 30]  # 30th minute of the hour
            predictvalue = np.mean(refmin)
            if hour == (int)(len(data) / 60 - 1):  # Last partial hour
                remaining_length = len(data) - len(prediction)
                prediction = np.append(prediction, np.ones(remaining_length) * predictvalue)
            else:
                prediction = np.append(prediction, np.ones(60) * predictvalue)

        # Trim prediction to match the length of time_data[1440:]
        prediction = prediction[:len(time_data_selected[1440:])]

        # Create a list of dictionaries with timestamp and prediction value
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], prediction)]

        return jsonify(result)  # Return as JSON

    else:
        return jsonify({"error": "Data not available yet"}), 500
    
#///////////////////////////////////////////////////////////////////////////////////////////
@app.route('/trend_model', methods=['GET'])
def trend_model():
    global time_data, solar_data
    if solar_data is not None and time_data is not None:
        data = solar_data[1440:]
        predictions = []
        for hour in range(len(data) // 60 - 1):  # Loop over the data
            target_time = time_data[hour]
            
            start_idx = hour * 60 - 60
            end_idx = hour * 60 - 30
            current_idx = hour * 60

            idx_24hr_before = current_idx - (24 * 60) + 1  # 24 hours before
            idx_30min_before = current_idx - 30  # 30 minutes before

            # Check if the indices are within the data range and compute the average
            if idx_24hr_before < idx_30min_before:
                total_avg = (data[idx_24hr_before] + data[idx_30min_before]) / 2
            else:
                total_avg = 0

            if start_idx >= 0 and end_idx >= 0:
                past_window = data[start_idx:end_idx]
            else:
                past_window = []
            
            if len(past_window) >= 2:
                recent_slope = (past_window[-1] - past_window[0]) / len(past_window)
            else:
                recent_slope = 0  # No valid slope if there's insufficient data

            max_solar_limit = 500
            max_correction = 35
            correction = np.clip(recent_slope * 30, -max_correction, max_correction)

            # Calculate forecasted value
            forecasted_value = np.clip(total_avg + correction, 0, max_solar_limit)
            predictions.extend([forecasted_value] * 60)
        
        # Ensure predictions match the length of time_data
        predictions = predictions[:len(time_data[1440:])]
        
        result = [{"Date and Time": str(t), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], predictions)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500


    
@app.route('/trend_selected', methods=['GET'])
def trend_model_selected():
    global time_data_selected, solar_data_selected
    if solar_data_selected is not None and time_data_selected is not None:  # Check both solar_data and time_data
        data = solar_data_selected[1440:]  # Use only the last 24 hours (assuming 2880 total minutes)
        predictions = []
        for hour in range(len(data) // 60 - 1):  # Loop over the data
            target_time = time_data[hour]
            # Find the indices of the last 60 minutes of data (1 hour back)
            start_idx = hour * 60 - 60 
            end_idx = hour * 60 - 30 
            current_idx = hour * 60 
            
            # Indices for the required snapshots
            idx_24hr_before = current_idx - (24 * 60)  # 24 hours before
            idx_30min_before = current_idx - 30  # 30 minutes before
            
            # Check if the indices are within the data range and compute the average
            if idx_24hr_before < idx_30min_before:
                total_avg = (data[idx_24hr_before] + data[idx_30min_before]) / 2
            else:
                total_avg = 0

            if start_idx >= 0 and end_idx >= 0:
                past_window =data[start_idx:end_idx]
            else:
                past_window = []

            if len(past_window) >= 2:
                recent_slope = (past_window[-1] - past_window[0]) / len(past_window)
            else:
                recent_slope = 0  # No valid slope if there's insufficient data

            max_solar_limit = 500
            max_correction = 35
            correction = np.clip(recent_slope * 30, -max_correction, max_correction)

            forecasted_value = np.clip(total_avg + correction, 0, max_solar_limit)
            predictions.extend([forecasted_value] * 60)
        
        predictions = predictions[:len(time_data[1440:])]
        result = [{"Date and Time": str(t), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], predictions)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

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
