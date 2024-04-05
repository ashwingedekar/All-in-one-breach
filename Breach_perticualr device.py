import requests
import xml.etree.ElementTree as ET
import re
import csv
import xml.etree.ElementTree as ET
import os
import requests
import pandas as pd
from io import StringIO
import warnings
from datetime import datetime
import re
from tqdm import tqdm  
import io


with open("server_address.txt", "r") as file:
    server_parameters = dict(line.strip().split("=") for line in file)

server_address = server_parameters.get("server")
username = server_parameters.get("username")
passhash = server_parameters.get("passhash")

devid = server_parameters.get("devid")


api_endpoint = f'https://{server_address}/api/table.xml?content=sensortree&id={devid}&username={username}&passhash={passhash}'



response = requests.get(api_endpoint)


if response.status_code == 200:
    print("Request successful!")
    print("Response:")
    print(response.text)
    
    file_path = "output.xml"
    if isinstance(response.text, str):
        with open(file_path, "w") as file:
            file.write(response.text)
        print(f"XML data saved to {file_path}")
    
    
    
else:
    print(f"Error: {response.status_code} - {response.text}")


#======================================================================================#

def remove_characters(text):
    
    cleaned_text = re.sub(r'\(�C\)|�C', '', text)
    return cleaned_text


encodings_to_try = ['utf-8', 'latin-1']  

for encoding in encodings_to_try:
    try:
        with open('output.xml', 'r', encoding=encoding) as file:
            xml_content = file.read()
        break  
    except UnicodeDecodeError:
        continue  


cleaned_xml_content = remove_characters(xml_content)

try:
    root = ET.fromstring(cleaned_xml_content)
    tree = ET.ElementTree(root)

    # Save the modified XML back to a file
    tree.write('clean.xml')
    print("XML file cleaned successfully!")
except ET.ParseError as e:
    print("Error parsing XML:", e)

#========================================================================================#



# Parse the XML file
tree = ET.parse('clean.xml')
root = tree.getroot()

# Defis
sensor_ids = []


for sensor in root.iter('sensor'):
  
    sensortype = sensor.find('sensortype')
    if sensortype is not None and sensortype.text == 'SNMP Traffic':
       
        sensor_id = sensor.find('id')
        if sensor_id is not None:
            sensor_ids.append(sensor_id.text)

output_file = 'output.txt'

with open(output_file, 'w') as file:
    for i, sensor_id in enumerate(sensor_ids, start=1):
        file.write(f"id{i}={sensor_id}\n")

print("Sensor IDs for SNMP Traffic sensors have been saved to:", output_file)

#========================================================================================#

warnings.filterwarnings("ignore", category=DeprecationWarning)

with open("server_address.txt", "r") as file:
    server_parameters = dict(line.strip().split("=") for line in file)

server_address = server_parameters.get("server")

flags = {}
id_prefix = 'id'
id_values = []

with open("min_max_flags.txt", "r") as file:
    for line in file:
        line = line.strip()
        if "=" in line:
            key, value = line.split("=")
            if key.startswith(id_prefix):
                id_values.append(value)
            else:
                flags[key] = value

with open("output.txt", "r") as file:
    for line in file:
        line = line.strip()
        if "=" in line:
            key, value = line.split("=")
            if key.startswith(id_prefix):
                id_values.append(value)

upper_warning_limits = {}
output_data = []

for id_value in tqdm(id_values, desc="Getting upper warning for Each IDs"):  
    try:
        api_endpoint_upper_warning = f'https://{server_address}/api/getobjectproperty.htm?subtype=channel&id={id_value}&subid=-1&name=limitmaxwarning&show=nohtmlencode&username={server_parameters.get("username")}&passhash={server_parameters.get("passhash")}'
        response_upper_warning = requests.get(api_endpoint_upper_warning)
        if response_upper_warning.status_code != 200:
            print(f"Check parameters for: {id_value}")
            continue
            
        match_upper_warning = re.search(r'<result>(\d+)</result>', response_upper_warning.text)
        if match_upper_warning is not None:  
            upper_warning_limits[id_value] = float(match_upper_warning.group(1)) * 8 / 1000000  
        else:
            print(f"Warning: Upper warning limit value not set for ID: {id_value}. Skipping.")
            continue
    except Exception as e:
        print(f"Error getting upper warning limit for ID {id_value}: {e}")
        continue

print(upper_warning_limits)

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

output_df = pd.DataFrame(output_data)

output_directory = "output"
os.makedirs(output_directory, exist_ok=True)


current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


output_file_path = os.path.join(output_directory, f"output_{current_datetime}.csv")


output_df.to_csv(output_file_path, index=False)


print(f"\nOutput has been saved to {output_file_path}")



