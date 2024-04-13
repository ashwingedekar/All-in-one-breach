for id_value in tqdm(id_values, desc="Processing IDs"):
    try:   
        api_endpoint = f'https://{server_address}/api/historicdata.csv?id={id_value}&avg={flags.get("avg")}&sdate={flags.get("sdate")}&edate={flags.get("edate")}&username={server_parameters.get("username")}&passhash={server_parameters.get("passhash")}'
        response = requests.get(api_endpoint)
        df = pd.read_csv(io.StringIO(response.text))
        df['Traffic Total (Speed)'] = df['Traffic Total (Speed)'].astype(str).str.replace(',', '').str.extract(r'(\d+\.*\d*)').astype(float)
        selected_data = df["Traffic Total (Speed)"]
    except KeyError:
        print(f"Traffic Total (Speed) column not found for ID: {id_value}")
        continue  
    if id_value not in upper_warning_limits:
        print(f"Upper warning limit not set for ID: {id_value}")
        continue
    
    filtered_data = selected_data[selected_data > upper_warning_limits.get(id_value)]

    if not filtered_data.empty:
        device_name_endpoint = f'https://{server_address}/api/getsensordetails.json?id={id_value}&username={server_parameters.get("username")}&passhash={server_parameters.get("passhash")}'
        device_name_response = requests.get(device_name_endpoint)
        if device_name_response.status_code == 200:
            device_name_json = device_name_response.json()
            parent_device_name = device_name_json["sensordata"]["parentdevicename"]
            sensor_device_name = device_name_json["sensordata"]["name"]
            DeviceID = device_name_json["sensordata"]["parentdeviceid"]
        else:
            parent_device_name = "N/A"
            sensor_device_name = "N/A"

        output_data.extend([{
            "Device Name": parent_device_name,
            "Device ID": DeviceID,
            "Sensor Name": sensor_device_name,
            "Sensor ID": id_value,
            "Date": row['Date Time'],
            "Traffic Total": row["Traffic Total (Speed)"]
        } for index, row in df.iterrows() if row['Traffic Total (Speed)'] > upper_warning_limits.get(id_value)])
    else:
        max_traffic = selected_data.max()
        output_data.append({
            "Device Name": parent_device_name,
            "Device ID": DeviceID,
            "Sensor Name": sensor_device_name,
            "Sensor ID": id_value,
            "Date": df.loc[df['Traffic Total (Speed)'].idxmax(), 'Date Time'],
            "Traffic Total": max_traffic
        })

output_df = pd.DataFrame(output_data)
