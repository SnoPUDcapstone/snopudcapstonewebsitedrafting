# TODO
#fix proportional and averaged
#make analitics

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


per_30_30 = None
per_30_60 = None
trend_dat = None
proportional_dat = None
avg_dat = None
per_70_60 = None

def load_and_filter_data():
    """Loads and filters data for a 48-hour period into solar_data/time_data, and the last 24 hours into cached_data."""
    global cached_data
    global solar_data
    global time_data

    while True:
        try:
            now = datetime.now()
            one_year_ago = now - timedelta(days=365)
            start_time_48h = one_year_ago - timedelta(hours=49)  # Start of the 48-hour window
            start_time_24h = one_year_ago - timedelta(hours=25)  # Start of the 24-hour window
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

def initialize_data():
    """Initializes all prediction data once at startup."""
    global solar_data, time_data, per_30_30, per_30_60, trend_dat, proportional_dat, avg_dat, per_70_60
    
    # Wait until solar_data and time_data are populated by the background thread
    while solar_data is None or time_data is None:
        print("Waiting for initial data load...")
        time.sleep(1)

    # Initialize Persistence_30_30
    data = solar_data[1440:]
    prediction_30_30 = np.zeros(60)
    for hour in range(int(len(data) / 60 - 1)):
        refhalfhour = data[hour * 60:(hour + 1) * 60 - 30]
        predictvalue = np.mean(refhalfhour)
        prediction_30_30 = np.append(prediction_30_30, np.ones(60) * predictvalue)
    per_30_30 = prediction_30_30[:len(time_data[1440:])]

    # Initialize Persistence_30_60
    prediction_30_60 = np.zeros(60)
    for hour in range(int(len(data) / 60)):
        refmin = data[hour * 60 + 29:hour * 60 + 30]
        predictvalue = np.mean(refmin)
        if hour == int(len(data) / 60 - 1):
            remaining_length = len(data) - len(prediction_30_60)
            prediction_30_60 = np.append(prediction_30_60, np.ones(remaining_length) * predictvalue)
        else:
            prediction_30_60 = np.append(prediction_30_60, np.ones(60) * predictvalue)
    per_30_60 = prediction_30_60[:len(time_data[1440:])]

    # Initialize trend_model
    data = solar_data[1440:]
    predictions = []
    for hour in range(len(data) // 60):  # Loop over the data
        start_idx = hour * 60 - 31
        end_idx = hour * 60 - 30
        curr_hour = hour * 60

        curr_hour = datetime.fromtimestamp(curr_hour)  # Convert to datetime
        month = curr_hour.month
            
        # Set max_correction based on the month
        if month in [6, 7, 8]:  # June, July, August
            max_correction = 50
            max_solar_limit = 450
        else:
            max_correction = 25
            max_solar_limit = 500

        # Check if the indices are within the data range and compute the average
        if start_idx < end_idx:
            total_avg = (data[start_idx] + data[end_idx]) / 2
        else:
            total_avg = 0

        if start_idx >= 0 and end_idx >= 0:
            past_window = data[start_idx:end_idx]
        else:
            past_window = []
            
        if len(past_window) >= 1:
            recent_slope = (data[end_idx] - data[start_idx]) / (end_idx - start_idx)
        else:
            recent_slope = 0  # No valid slope if there's insufficient data

        correction = np.clip(recent_slope * 30, -max_correction, max_correction)

        # Calculate forecasted value
        forecasted_value = np.clip(total_avg + correction, 0, max_solar_limit)
        predictions.extend([forecasted_value] * 60)
        
    # Ensure predictions match the length of time_data
    trend_dat = predictions[:len(time_data[1440:])]

    # Initialize Proportional
    df = pd.DataFrame({'Date & Time': time_data, 'Solar [kW]': solar_data})
    df['Date & Time'] = pd.to_datetime(df['Date & Time'])
    df = df.sort_values(by='Date & Time').reset_index(drop=True)
    ratio = df['Solar [kW]'].shift(31) / df['Solar [kW]'].shift(1471)
    df['proportional'] = np.where(
        (ratio < 0.7) | (ratio > 1.3),
        (df['Solar [kW]'].shift(31) * 0.6 + df['Solar [kW]'].shift(1411) * 0.4),
        ratio * df['Solar [kW]'].shift(1411)
    )
    for i in range(len(df)):
        if i % 60 == 0:
            persistence_value = df.loc[i, 'proportional']
        df.loc[i, 'proportional_1d_30m'] = persistence_value
    df['proportional_1d_30m'].fillna(0, inplace=True)
    proportional_dat = df['proportional_1d_30m'].to_numpy()[1440:]

    # Initialize Persistence_Averaged
    data = solar_data
    prediction = np.zeros(1440)
    for hour in range((int)(len(data)/60 - 23)):
        refmin = data[(hour)*60+29:(hour)*60+30] #30th minute of the hour
        refhour = data[(hour)*60:(hour+1)*60] #Same hour from yesterday
        predictvalue = .4 * np.mean(refmin) + .6*np.mean(refhour)
        if (hour == (int)(len(data)/60 - 24)):
            remaining_length = len(data) - len(prediction)
            prediction = np.append(prediction, np.ones(remaining_length)*predictvalue)
        else:
            prediction = np.append(prediction, np.ones(60)*predictvalue)

    # Trim prediction to match the length of time_data[1440:]
    prediction = prediction[1440:]

    avg_dat = prediction

    #initialise 70_60

    data = solar_data[1440:]  # Last 24 hours
    time_subset = time_data[1440:]  # Corresponding timestamps

    prediction = np.zeros(60)  # Initial 60 zeros for the first hour
        
    for hour in range(len(data) // 60):
        ref_idx = hour * 60 - 71 # 70 minutes before the forecasting hour
            
        if ref_idx >= 0:  # Ensure valid indexing
            predict_value = np.mean(data[ref_idx:ref_idx+1])  # Average of the single value at index ref_idx
        else:
            predict_value = 0  # Default to 0 if not enough data
            
        if hour == (len(data) // 60 - 1):  # Last partial hour
            remaining_length = len(data) - len(prediction)
            prediction = np.append(prediction, np.ones(remaining_length) * predict_value)
        else:
            prediction = np.append(prediction, np.ones(60) * predict_value)

    prediction = prediction[:len(time_subset)]  # Ensure lengths match
    per_70_60 = prediction


    print("All data initialized successfully")

print("Starting initialization...")
initialize_data()

#raw solar data
@app.route('/data', methods=['GET'])
def get_solar():
    """Returns the cached data for the last 24 hours from one year ago."""
    return jsonify(cached_data)


#date selection and intitialisation of relevant data sets
per_30_30_selected = None
per_30_60_selected = None
trend_selected_dat = None
proportional_selected_dat = None
avg_selected_dat = None
per_70_60_selected = None

@app.route('/selecteddate', methods=['GET'])
def get_selected_date_data():
    global solar_data_selected, time_data_selected, per_30_30_selected, per_30_60_selected, trend_selected_dat, proportional_selected_dat, avg_selected_dat, per_70_60_selected

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

        #///////////////////////////////////////////////////////////
        #initialisation
        data = solar_data_selected[1440:]
        prediction = np.zeros(60)
        for hour in range((int)(len(data)/60 - 1)):
            refhalfhour = data[(hour)*60:(hour+1)*60-30]
            predictvalue = np.mean(refhalfhour)
            prediction = np.append(prediction, np.ones(60)*predictvalue)
        
        # Trim prediction to match the length of time_data
        prediction = prediction[:len(time_data_selected[1440:])]
        
        per_30_30_selected = prediction

        #////
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
        per_30_60_selected = prediction
        #//////
        data = solar_data_selected[1440:]  # Use only the last 24 hours (assuming 2880 total minutes)
        predictions = []
        for hour in range(len(data) // 60):  # Loop over the data
            # target_time = time_data_selected[hour]
            # Find the indices of the last 60 minutes of data (1 hour back)
            start_idx = hour * 60 - 31 
            end_idx = hour * 60 - 30 
            curr_hour = hour * 60

            curr_hour = datetime.fromtimestamp(curr_hour)  # Convert to datetime
            month = curr_hour.month
            
            # Set max_correction based on the month
            if month in [6, 7, 8]:  # June, July, August
                max_correction = 50
                max_solar_limit = 450
            else:
                max_correction = 25
                max_solar_limit = 500

            if start_idx < end_idx:
                total_avg = (data[start_idx] + data[end_idx]) / 2

            if start_idx >= 0 and end_idx >= 0:
                past_window =data[start_idx:end_idx]
            else:
                past_window = []

            if len(past_window) >= 2:
                recent_slope = (data[end_idx] - data[start_idx]) / (end_idx - start_idx)
            else:
                recent_slope = 0  # No valid slope if there's insufficient data

            correction = np.clip(recent_slope * 30, -max_correction, max_correction)

            forecasted_value = np.clip(total_avg + correction, 0, max_solar_limit)
            predictions.extend([forecasted_value] * 60)
        
        predictions = predictions[:len(time_data_selected[1440:])]

        trend_selected_dat = predictions
        #///////////

        df_selected = pd.DataFrame({'Date & Time': time_data_selected, 'Solar [kW]': solar_data_selected})

        # Ensure proper datetime format and sorting
        df_selected['Date & Time'] = pd.to_datetime(df_selected['Date & Time'])
        df_selected = df_selected.sort_values(by='Date & Time').reset_index(drop=True)

        # Compute ratio
        ratio = df_selected['Solar [kW]'].shift(31) / df_selected['Solar [kW]'].shift(1471)

        # Apply proportional forecasting algorithm
        df_selected['proportional_1d_30m'] = np.where(
            (ratio < 0.7) | (ratio > 1.3),  # Condition: ratio < 30% or > 130%
            (df_selected['Solar [kW]'].shift(31) * 0.6 + df_selected['Solar [kW]'].shift(1411) * 0.4),  # If true
            ratio * df_selected['Solar [kW]'].shift(1411)  # If false
        )

        # Maintain persistence for 60-minute blocks
        for i in range(len(df_selected)):
            if i % 60 == 0:  # Update persistence value at the start of each hour
                persistence_value = df_selected.loc[i, 'proportional_1d_30m']
            df_selected.loc[i, 'proportional_1d_30m'] = persistence_value

        # Fill NaN values with 0
        df_selected['proportional_1d_30m'].fillna(0, inplace=True)

        # Extract only the last 1440 minutes (24 hours)
        df_filtered = df_selected.iloc[1440:]

        #change to numpy for output
        timeproportionalselected = df_filtered['Date & Time'].to_numpy()
        solarproportionalselected = df_filtered['proportional_1d_30m'].to_numpy()

        proportional_selected_dat = solarproportionalselected

        #////
        data = solar_data_selected
        prediction = np.zeros(1440)
        for hour in range((int)(len(data)/60 - 23)):
            refmin = data[(hour)*60+29:(hour)*60+30] #30th minute of the hour
            refhour = data[(hour)*60:(hour+1)*60] #Same hour from yesterday
            predictvalue = .4 * np.mean(refmin) + .6*np.mean(refhour)
            if (hour == (int)(len(data)/60 - 24)):
                remaining_length = len(data) - len(prediction)
                prediction = np.append(prediction, np.ones(remaining_length)*predictvalue)
            else:
                prediction = np.append(prediction, np.ones(60)*predictvalue)

        # Trim prediction to match the length of time_data[1440:]
        prediction = prediction[1440:]
        avg_selected_dat = prediction
        #/////
        data = solar_data_selected[1440:]  # Last 24 hours
        time_subset = time_data_selected[1440:]  # Corresponding timestamps

        prediction = np.zeros(60)  # Initial 60 zeros for the first hour
        
        for hour in range(len(data) // 60):
            ref_idx = hour * 60 - 71 # 70 minutes before the forecasting hour
            
            if ref_idx >= 0:  # Ensure valid indexing
                predict_value = np.mean(data[ref_idx:ref_idx+1])  # Average of the single value at index ref_idx
            else:
                predict_value = 0  # Default to 0 if not enough data
            
            if hour == (len(data) // 60 - 1):  # Last partial hour
                remaining_length = len(data) - len(prediction)
                prediction = np.append(prediction, np.ones(remaining_length) * predict_value)
            else:
                prediction = np.append(prediction, np.ones(60) * predict_value)

        prediction = prediction[:len(time_subset)]  # Ensure lengths match
        per_70_60_selected = prediction

        #/////////////////////////////////////////////////////////

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
    global time_data, solar_data, per_30_30
    if solar_data is not None and time_data is not None:
        data = solar_data[1440:]
        prediction = np.zeros(60)
        for hour in range((int)(len(data)/60 - 1)):
            refhalfhour = data[(hour)*60:(hour+1)*60-30]
            predictvalue = np.mean(refhalfhour)
            prediction = np.append(prediction, np.ones(60)*predictvalue)
        
        # Trim prediction to match the length of time_data
        prediction = prediction[:len(time_data[1440:])]
        
        per_30_30 = prediction

        # Create a list of dictionaries with timestamp and prediction value
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/30_30selected', methods=['GET'])
def Persistence_30_30_selected():
    global time_data_selected, solar_data_selected, per_30_30_selected
    if solar_data_selected is not None and time_data_selected is not None:
        data = solar_data_selected[1440:]
        prediction = np.zeros(60)
        for hour in range((int)(len(data)/60 - 1)):
            refhalfhour = data[(hour)*60:(hour+1)*60-30]
            predictvalue = np.mean(refhalfhour)
            prediction = np.append(prediction, np.ones(60)*predictvalue)
        
        # Trim prediction to match the length of time_data
        prediction = prediction[:len(time_data_selected[1440:])]
        
        per_30_30_selected = prediction
        # Create a list of dictionaries with timestamp and prediction value
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500


@app.route('/30_30/batt', methods=['GET'])
def batt_use_30_30():
    global time_data, solar_data, per_30_30
    if solar_data is not None and time_data is not None and per_30_30 is not None:

        prediction = solar_data[1440:] - per_30_30
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500


@app.route('/30_30selected/batt', methods=['GET'])
def batt_use_30_30_selected():
    global time_data_selected, solar_data_selected, per_30_30_selected
    if solar_data_selected is not None and time_data_selected is not None and per_30_30_selected is not None:

        prediction = solar_data_selected[1440:] - per_30_30_selected
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/30_30/soc', methods=['GET'])
def soc_30_30():
    global time_data, solar_data, per_30_30
    if solar_data is not None and time_data is not None and per_30_30 is not None:

        soc = np.zeros(1440)
        soc[0] = 700
        batteryout = solar_data[1440:] - per_30_30

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/30_30selected/soc', methods=['GET'])
def soc_30_30_selected():
    global time_data_selected, solar_data_selected, per_30_30_selected
    if solar_data_selected is not None and time_data_selected is not None and per_30_30_selected is not None:

        soc = np.zeros(len(solar_data_selected) - 1440)
        soc[0] = 700
        batteryout = solar_data_selected[1440:] - per_30_30_selected

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500
#///////////////////////////////////////////////////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////////////////////////
#worth noting that a second copy of this should probably be made to pull from selection data
#this functionality is not yet had, will remove this comment when it is.

@app.route('/30_60', methods=['GET'])
def Persistence_30_60():
    global time_data, solar_data, per_30_60
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
        per_30_60 = prediction
        # Create a list of dictionaries with timestamp and prediction value
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], prediction)]

        return jsonify(result)  # Return as JSON

    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/30_60selected', methods=['GET'])
def Persistence_30_60_selected():
    global time_data_selected, solar_data_selected, per_30_60_selected
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
        per_30_60_selected = prediction

        # Create a list of dictionaries with timestamp and prediction value
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], prediction)]

        return jsonify(result)  # Return as JSON

    else:
        return jsonify({"error": "Data not available yet"}), 500
    
@app.route('/30_60/batt', methods=['GET'])
def batt_use_30_60():
    global time_data, solar_data, per_30_60
    if solar_data is not None and time_data is not None and per_30_60 is not None:

        prediction = solar_data[1440:] - per_30_60
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/30_60selected/batt', methods=['GET'])
def batt_use_30_60_selected():
    global time_data_selected, solar_data_selected, per_30_60_selected
    if solar_data_selected is not None and time_data_selected is not None and per_30_60_selected is not None:

        prediction = solar_data_selected[1440:] - per_30_60_selected
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/30_60/soc', methods=['GET'])
def soc_30_60():
    global time_data, solar_data, per_30_60
    if solar_data is not None and time_data is not None and per_30_60 is not None:

        soc = np.zeros(1440)
        soc[0] = 700
        batteryout = solar_data[1440:] - per_30_60

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/30_60selected/soc', methods=['GET'])
def soc_30_60_selected():
    global time_data_selected, solar_data_selected, per_30_60_selected
    if solar_data_selected is not None and time_data_selected is not None and per_30_60_selected is not None:

        soc = np.zeros(len(solar_data_selected) - 1440)
        soc[0] = 700
        batteryout = solar_data_selected[1440:] - per_30_60_selected

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500
#///////////////////////////////////////////////////////////////////////////////////////////


#///////////////////////////////////////////////////////////////////////////////////////////

@app.route('/trend_model', methods=['GET'])
def trend_model():
    global time_data, solar_data, trend_dat
    if solar_data is not None and time_data is not None:
        data = solar_data[1440:]
        predictions = []
        for hour in range(len(data) // 60):  # Loop over the data
            start_idx = hour * 60 - 31
            end_idx = hour * 60 - 30
            curr_hour = hour * 60

            curr_hour = datetime.fromtimestamp(curr_hour)  # Convert to datetime
            month = curr_hour.month
            
            # Set max_correction based on the month
            if month in [6, 7, 8]:  # June, July, August
                max_correction = 50
                max_solar_limit = 450
            else:
                max_correction = 30
                max_solar_limit = 500

            # Check if the indices are within the data range and compute the average
            if start_idx < end_idx:
                total_avg = (data[start_idx] + data[end_idx]) / 2
            else:
                total_avg = 0

            if start_idx >= 0 and end_idx >= 0:
                past_window = data[start_idx:end_idx]
            else:
                past_window = []
            
            if len(past_window) >= 1:
                recent_slope = (data[end_idx] - data[start_idx]) / (end_idx - start_idx)
            else:
                recent_slope = 0  # No valid slope if there's insufficient data

            correction = np.clip(recent_slope * 30, -max_correction, max_correction)

            # Calculate forecasted value
            forecasted_value = np.clip(total_avg + correction, 0, max_solar_limit)
            predictions.extend([forecasted_value] * 60)
        
        # Ensure predictions match the length of time_data
        predictions = predictions[:len(time_data[1440:])]
        
        trend_dat = predictions

        result = [{"Date and Time": str(t), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], predictions)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500
    
@app.route('/trend_selected', methods=['GET'])
def trend_model_selected():
    global time_data_selected, solar_data_selected, trend_selected_dat
    if solar_data_selected is not None and time_data_selected is not None:  # Check both solar_data and time_data

        df_trend_sel = pd.DataFrame({'Date & Time': time_data_selected, 'Solar [kW]': solar_data_selected})

        # Ensure the 'Date & Time' column is sorted and in datetime format
        df_trend_sel['Date & Time'] = pd.to_datetime(df_trend_sel['Date & Time'])
        df_trend_sel = df_trend_sel.sort_values(by='Date & Time').reset_index(drop=True)
        df_trend_sel['Month'] = df_trend_sel['Date & Time'].dt.month
        trend_forecast = np.zeros(len(df_trend_sel))

        for hour in range((len(df_trend_sel) // 60) - 1):
            curr_hour = hour * 60  # Correct starting index

            past_start_idx = curr_hour - 31
            past_end_idx = curr_hour - 30

            if past_start_idx < 0 or past_end_idx < 0:
                continue

            past_avg = df_trend_sel.loc[past_start_idx:past_end_idx, 'Solar [kW]'].mean()
            trend_window = df_trend_sel.loc[past_start_idx:past_end_idx]

            if len(trend_window) < 2:
                recent_slope = 0
            else:
                time_diff = (trend_window['Date & Time'].diff().dt.total_seconds() / 60).dropna()
                power_diff = trend_window['Solar [kW]'].diff().dropna()
                rate_of_change = power_diff / time_diff
                recent_slope = rate_of_change.mean()

            # Set month-based correction
            current_month = df_trend_sel.loc[curr_hour, 'Month']
            max_solar_limit = 445 if current_month in [6, 7, 8] else 500
            max_correction = 50 if current_month in [6, 7, 8] else 30

            correction = np.clip(recent_slope * 30, -max_correction, max_correction)

            # Assign forecasted value
            trend_forecast[curr_hour:curr_hour+60] = np.clip(past_avg + correction, 0, max_solar_limit)

        # Store results
        df_trend_sel['Trend_Forecast'] = trend_forecast
        df_trend_filtered = df_trend_sel.iloc[1440:]  # Keep last 24 hours

        # Convert to numpy for output
        timetrendselected = df_trend_filtered['Date & Time'].to_numpy()
        solartrendselected = df_trend_filtered['Trend_Forecast'].to_numpy()

        trend_selected_dat = solartrendselected

        result = [{"Date and Time": str(t), "Value (KW)": float(p)} 
                  for t, p in zip(timetrendselected, solartrendselected)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/trend_model/batt', methods=['GET'])
def batt_use_trend():
    global time_data, solar_data, trend_dat
    if solar_data is not None and time_data is not None and trend_dat is not None:

        prediction = solar_data[1440:] - trend_dat
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/trend_selected/batt', methods=['GET'])
def batt_use_trend_selected():
    global time_data_selected, solar_data_selected, trend_selected_dat
    if solar_data_selected is not None and time_data_selected is not None and trend_selected_dat is not None:

        prediction = solar_data_selected[1440:] - trend_selected_dat
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/trend_model/soc', methods=['GET'])
def soc_trend():
    global time_data, solar_data, trend_dat
    if solar_data is not None and time_data is not None and trend_dat is not None:

        soc = np.zeros(1440)
        soc[0] = 700
        batteryout = solar_data[1440:] - trend_dat

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/trend_selected/soc', methods=['GET'])
def soc_trend_selected():
    global time_data_selected, solar_data_selected, trend_selected_dat
    if solar_data_selected is not None and time_data_selected is not None and trend_selected_dat is not None:

        soc = np.zeros(len(solar_data_selected) - 1440)
        soc[0] = 700
        batteryout = solar_data_selected[1440:] - trend_selected_dat

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500
#/////////////////////////////////////////////////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////////////////////////////

@app.route('/proportional', methods=['GET'])
def Proportional():
    global time_data, solar_data, proportional_dat
    
    if solar_data is not None and time_data is not None:
        # Convert time_data to Pandas DataFrame
        df = pd.DataFrame({'Date & Time': time_data, 'Solar [kW]': solar_data})

        # Ensure the 'Date & Time' column is sorted and in datetime format
        df['Date & Time'] = pd.to_datetime(df['Date & Time'])
        df = df.sort_values(by='Date & Time').reset_index(drop=True)

        # Compute ratio
        ratio = df['Solar [kW]'].shift(31) / df['Solar [kW]'].shift(1471)

        # Apply proportional algorithm
        df['proportional'] = np.where(
            (ratio < 0.7) | (ratio > 1.3),  # Condition: ratio < 30% or > 130%
            (df['Solar [kW]'].shift(31) * 0.6 + df['Solar [kW]'].shift(1411) * 0.4),  # If true
            ratio * df['Solar [kW]'].shift(1411)  # If false
        )

        # Loop to maintain persistence for a 60-minute block
        for i in range(len(df)):
            if i % 60 == 0:  # Only update at the start of an hour
                persistence_value = df.loc[i, 'proportional']
            df.loc[i, 'proportional_1d_30m'] = persistence_value

        # Fill NaN values with 0
        df['proportional_1d_30m'].fillna(0, inplace=True)

        # Extract only the last 1440 minutes (24 hours)
        df_filtered = df.iloc[1440:]
        
        #change to numpy for ouput
        timepropotional  = df_filtered['Date & Time'].to_numpy()
        solarproportional = df_filtered['proportional_1d_30m'].to_numpy()

        proportional_dat = solarproportional
        # Format results as JSON
        result = [
            {"Date and Time": t.astype(str), "Value (KW)": float(p)}
            for t, p in zip(timepropotional, solarproportional)
        ]

        return jsonify(result)  # Return as JSON

    else:
        return jsonify({"error": "Data not available yet"}), 500


@app.route('/proportional_selected', methods=['GET'])
def proportional_selected():
    global time_data_selected, solar_data_selected, proportional_selected_dat

    if solar_data_selected is not None and time_data_selected is not None:
        # Convert to DataFrame
        df_selected = pd.DataFrame({'Date & Time': time_data_selected, 'Solar [kW]': solar_data_selected})

        # Ensure proper datetime format and sorting
        df_selected['Date & Time'] = pd.to_datetime(df_selected['Date & Time'])
        df_selected = df_selected.sort_values(by='Date & Time').reset_index(drop=True)

        # Compute ratio
        ratio = df_selected['Solar [kW]'].shift(31) / df_selected['Solar [kW]'].shift(1471)

        # Apply proportional forecasting algorithm
        df_selected['proportional_1d_30m'] = np.where(
            (ratio < 0.7) | (ratio > 1.3),  # Condition: ratio < 30% or > 130%
            (df_selected['Solar [kW]'].shift(31) * 0.6 + df_selected['Solar [kW]'].shift(1411) * 0.4),  # If true
            ratio * df_selected['Solar [kW]'].shift(1411)  # If false
        )

        # Maintain persistence for 60-minute blocks
        for i in range(len(df_selected)):
            if i % 60 == 0:  # Update persistence value at the start of each hour
                persistence_value = df_selected.loc[i, 'proportional_1d_30m']
            df_selected.loc[i, 'proportional_1d_30m'] = persistence_value

        # Fill NaN values with 0
        df_selected['proportional_1d_30m'].fillna(0, inplace=True)

        # Extract only the last 1440 minutes (24 hours)
        df_filtered = df_selected.iloc[1440:]

        #change to numpy for output
        timeproportionalselected = df_filtered['Date & Time'].to_numpy()
        solarproportionalselected = df_filtered['proportional_1d_30m'].to_numpy()

        proportional_selected_dat = solarproportionalselected

        # Format results as JSON
        result = [
            {"Date and Time": t.astype(str), "Value (KW)": float(p)}
            for t, p in zip(timeproportionalselected, solarproportionalselected)
        ]

        return jsonify(result)  # Return as JSON

    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/proportional/batt', methods=['GET'])
def batt_use_proportional():
    global time_data, solar_data, proportional_dat
    if solar_data is not None and time_data is not None and proportional_dat is not None:

        prediction = solar_data[1440:] - proportional_dat
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/proportional_selected/batt', methods=['GET'])
def batt_proportional_selected():
    global time_data_selected, solar_data_selected, proportional_selected_dat
    if solar_data_selected is not None and time_data_selected is not None and proportional_selected_dat is not None:

        prediction = solar_data_selected[1440:] - proportional_selected_dat
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/proportional/soc', methods=['GET'])
def soc_proportional():
    global time_data, solar_data, proportional_dat
    if solar_data is not None and time_data is not None and proportional_dat is not None:

        soc = np.zeros(1440)
        soc[0] = 700
        batteryout = solar_data[1440:] - proportional_dat

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/proportional_selected/soc', methods=['GET'])
def soc_proportional_selected():
    global time_data_selected, solar_data_selected, proportional_selected_dat
    if solar_data_selected is not None and time_data_selected is not None and proportional_selected_dat is not None:

        soc = np.zeros(len(solar_data_selected) - 1440)
        soc[0] = 700
        batteryout = solar_data_selected[1440:] - proportional_selected_dat

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500
#///////////////////////////////////////////////////////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////////////////////////////
#worth noting that a second copy of this should probably be made to pull from selection data
#this functionality is not yet had, will remove this comment when it is.

@app.route('/averaged', methods=['GET'])
def Persistence_Averaged():
    global time_data, solar_data, avg_dat
    if solar_data is not None and time_data is not None:  # Check both solar_data and time_data
        data = solar_data
        prediction = np.zeros(1440)
        for hour in range((int)(len(data)/60 - 23)):
            refmin = data[(hour)*60+29:(hour)*60+30] #30th minute of the hour
            refhour = data[(hour)*60:(hour+1)*60] #Same hour from yesterday
            predictvalue = .4 * np.mean(refmin) + .6*np.mean(refhour)
            if (hour == (int)(len(data)/60 - 24)):
                remaining_length = len(data) - len(prediction)
                prediction = np.append(prediction, np.ones(remaining_length)*predictvalue)
            else:
                prediction = np.append(prediction, np.ones(60)*predictvalue)

        # Trim prediction to match the length of time_data[1440:]
        prediction = prediction[1440:]

        avg_dat = prediction
        # Create a list of dictionaries with timestamp and prediction value
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], prediction)]

        return jsonify(result)  # Return as JSON

    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/averagedselected', methods=['GET'])
def Persistence_Averaged_selected():
    global time_data_selected, solar_data_selected, avg_selected_dat
    if solar_data_selected is not None and time_data_selected is not None:  # Check both solar_data and time_data
        data = solar_data_selected
        prediction = np.zeros(1440)
        for hour in range((int)(len(data)/60 - 23)):
            refmin = data[(hour)*60+29:(hour)*60+30] #30th minute of the hour
            refhour = data[(hour)*60:(hour+1)*60] #Same hour from yesterday
            predictvalue = .4 * np.mean(refmin) + .6*np.mean(refhour)
            if (hour == (int)(len(data)/60 - 24)):
                remaining_length = len(data) - len(prediction)
                prediction = np.append(prediction, np.ones(remaining_length)*predictvalue)
            else:
                prediction = np.append(prediction, np.ones(60)*predictvalue)

        # Trim prediction to match the length of time_data[1440:]
        prediction = prediction[1440:]
        avg_selected_dat = prediction
        # Create a list of dictionaries with timestamp and prediction value
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], prediction)]

        return jsonify(result)  # Return as JSON

    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/averaged/batt', methods=['GET'])
def batt_use_averaged():
    global time_data, solar_data, avg_dat
    if solar_data is not None and time_data is not None and avg_dat is not None:

        prediction = solar_data[1440:] - avg_dat
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/averagedselected/batt', methods=['GET'])
def batt_averaged_selected():
    global time_data_selected, solar_data_selected, avg_selected_dat
    if solar_data_selected is not None and time_data_selected is not None and avg_selected_dat is not None:

        prediction = solar_data_selected[1440:] - avg_selected_dat
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/averaged/soc', methods=['GET'])
def soc_averaged():
    global time_data, solar_data, avg_dat
    if solar_data is not None and time_data is not None and avg_dat is not None:

        soc = np.zeros(1440)
        soc[0] = 700
        batteryout = solar_data[1440:] - avg_dat

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/averagedselected/soc', methods=['GET'])
def soc_averaged_selected():
    global time_data_selected, solar_data_selected, avg_selected_dat
    if solar_data_selected is not None and time_data_selected is not None and avg_selected_dat is not None:

        soc = np.zeros(len(solar_data_selected) - 1440)
        soc[0] = 700
        batteryout = solar_data_selected[1440:] - avg_selected_dat

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500
#///////////////////////////////////////////////////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////////////////////////

@app.route('/70_60', methods = ['GET'])
def Persistence_70_60():
    global time_data, solar_data, per_70_60
    if solar_data is not None and time_data is not None:
        data = solar_data[1440:]  # Last 24 hours
        time_subset = time_data[1440:]  # Corresponding timestamps

        prediction = np.zeros(60)  # Initial 60 zeros for the first hour
        
        for hour in range(len(data) // 60):
            ref_idx = hour * 60 - 71 # 70 minutes before the forecasting hour
            
            if ref_idx >= 0:  # Ensure valid indexing
                predict_value = np.mean(data[ref_idx:ref_idx+1])  # Average of the single value at index ref_idx
            else:
                predict_value = 0  # Default to 0 if not enough data
            
            if hour == (len(data) // 60 - 1):  # Last partial hour
                remaining_length = len(data) - len(prediction)
                prediction = np.append(prediction, np.ones(remaining_length) * predict_value)
            else:
                prediction = np.append(prediction, np.ones(60) * predict_value)

        prediction = prediction[:len(time_subset)]  # Ensure lengths match
        per_70_60 = prediction

        result = [{"Date and Time": str(t), "Value (KW)": float(p)} 
                  for t, p in zip(time_subset, prediction)]
        return jsonify(result)

    else:
        return jsonify({"error": "Data not available yet"}), 500

    
@app.route('/70_60selected', methods = ['GET'])
def Persistence_70_60_selected():
    global time_data_selected, solar_data_selected, per_70_60_selected
    if solar_data_selected is not None and time_data_selected is not None:
        data = solar_data_selected[1440:]  # Last 24 hours
        time_subset = time_data_selected[1440:]  # Corresponding timestamps

        prediction = np.zeros(60)  # Initial 60 zeros for the first hour
        
        for hour in range(len(data) // 60):
            ref_idx = hour * 60 - 71 # 70 minutes before the forecasting hour
            
            if ref_idx >= 0:  # Ensure valid indexing
                predict_value = np.mean(data[ref_idx:ref_idx+1])  # Average of the single value at index ref_idx
            else:
                predict_value = 0  # Default to 0 if not enough data
            
            if hour == (len(data) // 60 - 1):  # Last partial hour
                remaining_length = len(data) - len(prediction)
                prediction = np.append(prediction, np.ones(remaining_length) * predict_value)
            else:
                prediction = np.append(prediction, np.ones(60) * predict_value)

        prediction = prediction[:len(time_subset)]  # Ensure lengths match
        per_70_60_selected = prediction

        result = [{"Date and Time": str(t), "Value (KW)": float(p)} 
                  for t, p in zip(time_subset, prediction)]
        return jsonify(result)

    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/70_60/batt', methods=['GET'])
def batt_use_70_60():
    global per_70_60, time_data, solar_data
    if solar_data is not None and time_data is not None and per_70_60 is not None:

        prediction = solar_data[1440:] - per_70_60

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/70_60selected/batt', methods=['GET'])
def batt_70_60_selected():
    global time_data_selected, solar_data_selected, per_70_60_selected
    if solar_data_selected is not None and time_data_selected is not None and per_70_60_selected is not None:

        prediction = solar_data_selected[1440:] - per_70_60_selected
        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], prediction)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/70_60/soc', methods=['GET'])
def soc_70_60():
    global time_data, solar_data, per_70_60
    if solar_data is not None and time_data is not None and per_70_60 is not None:

        soc = np.zeros(1440)
        soc[0] = 700
        batteryout = solar_data[1440:] - per_70_60

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500

@app.route('/70_60selected/soc', methods=['GET'])
def soc_70_60_selected():
    global time_data_selected, solar_data_selected, per_70_60_selected
    if solar_data_selected is not None and time_data_selected is not None and per_70_60_selected is not None:

        soc = np.zeros(len(solar_data_selected) - 1440)
        soc[0] = 700
        batteryout = solar_data_selected[1440:] - per_70_60_selected

        for i in range(len(soc)):
            if i == 0:
                continue
            if (soc[i-1] + (batteryout[i]/60)) <= 1400: 
                soc[i] = soc[i-1] + (batteryout[i]/60)
            else: soc[i] = soc[i-1]

        result = [{"Date and Time": t.astype(str), "Value (KW)": float(p)} 
                  for t, p in zip(time_data_selected[1440:], soc)]
        
        return jsonify(result)
    else:
        return jsonify({"error": "Data not available yet"}), 500
#///////////////////////////////////////////////////////////////////////////////////////////

#this is a test dataset for metrics, implement in future @app.route('/metrics')
@app.route('/metrics')
def get_metrics():
    global solar_data, per_30_30, per_30_60, per_70_60, trend_dat, avg_dat, proportional_dat 
    global solar_data_selected, per_30_30_selected, per_30_60_selected, per_70_60_selected, trend_selected_dat, proportional_selected_dat, avg_selected_dat

    start = request.args.get('start')
    end = request.args.get('end')
    data_type = request.args.get('type', 'option1')

    metrics = None

    # Example static metrics (replace with your actual calculations)
    if (start and end):
        solarkwh = sum(solar_data_selected[1440:])/60
        per3030kwh = sum(per_30_30_selected)/60
        per3060kwh = sum(per_30_60_selected)/60
        per7060kwh = sum(per_70_60_selected)/60
        trendkwh = sum(trend_selected_dat)/60
        proportionalkwh = sum(proportional_selected_dat)/60
        averagedkwh = sum(avg_selected_dat)/60

        per3030cycles = (np.abs(((solar_data_selected[1440:]-per_30_30_selected)/60)).sum())/1400
        per3060cycles = (np.abs(((solar_data_selected[1440:]-per_30_60_selected)/60)).sum())/1400
        per7060cycles = (np.abs(((solar_data_selected[1440:]-per_70_60_selected)/60)).sum())/1400
        trendcycles = (np.abs(((solar_data_selected[1440:]-trend_selected_dat)/60)).sum())/1400
        proportionalcycles = (np.abs(((solar_data_selected[1440:]-proportional_selected_dat)/60)).sum())/1400
        averagedcycles = (np.abs(((solar_data_selected[1440:]-avg_selected_dat)/60)).sum())/1400

        metrics = {
            'solar': round(solarkwh, 2),
            'dataset1': {'rmse': 1.2, 'mae': 0.8, 'mse': 1.44, 'cycles': round(per3030cycles, 2), 'energy': round(per3030kwh, 2)},
            'dataset2': {'rmse': 1.5, 'mae': 0.9, 'mse': 2.25, 'cycles': round(per3060cycles, 2), 'energy': round(per3060kwh, 2)},
            'dataset3': {'rmse': 1.1, 'mae': 0.7, 'mse': 1.21, 'cycles': round(per7060cycles, 2), 'energy': round(per7060kwh, 2)},
            'dataset4': {'rmse': 1.3, 'mae': 0.85, 'mse': 1.69, 'cycles': round(trendcycles, 2), 'energy': round(trendkwh, 2)},
            'dataset5': {'rmse': 1.4, 'mae': 0.95, 'mse': 1.96, 'cycles': round(proportionalcycles, 2), 'energy': round(proportionalkwh, 2)},
            'dataset6': {'rmse': 1.0, 'mae': 0.6, 'mse': 1.0, 'cycles': round(averagedcycles, 2), 'energy': round(averagedkwh, 2)}
        }
    else:

        solarkwh = sum(solar_data[1440:])/60
        per3030kwh = sum(per_30_30)/60
        per3060kwh = sum(per_30_60)/60
        per7060kwh = sum(per_70_60)/60
        trendkwh = sum(trend_dat)/60
        proportionalkwh = sum(proportional_dat)/60
        averagedkwh = sum(avg_dat)/60

        per3030cycles = (np.abs(((solar_data[1440:]-per_30_30)/60)).sum())/1400
        per3060cycles = (np.abs(((solar_data[1440:]-per_30_60)/60)).sum())/1400
        per7060cycles = (np.abs(((solar_data[1440:]-per_70_60)/60)).sum())/1400
        trendcycles = (np.abs(((solar_data[1440:]-trend_dat)/60)).sum())/1400
        proportionalcycles = (np.abs(((solar_data[1440:]-proportional_dat)/60)).sum())/1400
        averagedcycles = (np.abs(((solar_data[1440:]-avg_dat)/60)).sum())/1400

        metrics = {
            'solar': round(solarkwh, 2),
            'dataset1': {'rmse': 1.2, 'mae': 0.8, 'mse': 1.44, 'cycles': round(per3030cycles, 2), 'energy': round(per3030kwh, 2)},
            'dataset2': {'rmse': 1.5, 'mae': 0.9, 'mse': 2.25, 'cycles': round(per3060cycles, 2), 'energy': round(per3060kwh, 2)},
            'dataset3': {'rmse': 1.1, 'mae': 0.7, 'mse': 1.21, 'cycles': round(per7060cycles, 2), 'energy': round(per7060kwh, 2)},
            'dataset4': {'rmse': 1.3, 'mae': 0.85, 'mse': 1.69, 'cycles': round(trendcycles, 2), 'energy': round(trendkwh, 2)},
            'dataset5': {'rmse': 1.4, 'mae': 0.95, 'mse': 1.96, 'cycles': round(proportionalcycles, 2), 'energy': round(proportionalkwh, 2)},
            'dataset6': {'rmse': 1.0, 'mae': 0.6, 'mse': 1.0, 'cycles': round(averagedcycles, 2), 'energy': round(averagedkwh, 2)}
        }
    return jsonify(metrics)


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

