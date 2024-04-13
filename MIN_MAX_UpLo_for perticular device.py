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
from tqdm import tqdm  # Import tqdm library
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

    
    tree.write('clean.xml')
    print("XML file cleaned successfully!")
except ET.ParseError as e:
    print("Error parsing XML:", e)

#========================================================================================#




tree = ET.parse('clean.xml')
root = tree.getroot()

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


api_endpoint_upper_warning = f'https://{server_address}/api/getobjectproperty.htm?subtype=channel&subid=-1&name=limitmaxwarning&show=nohtmlencode&username=Ashwin.Gedekar&passhash=440909494'
api_endpoint_upper_error = f'https://{server_address}/api/getobjectproperty.htm?subtype=channel&subid=-1&name=limitmaxerror&show=nohtmlencode&username=Ashwin.Gedekar&passhash=440909494'
api_endpoint_lower_warning = f'https://{server_address}/api/getobjectproperty.htm?subtype=channel&subid=-1&name=limitminwarning&show=nohtmlencode&username=Ashwin.Gedekar&passhash=440909494'
api_endpoint_lower_error = f'https://{server_address}/api/getobjectproperty.htm?subtype=channel&subid=-1&name=limitminerror&show=nohtmlencode&username=Ashwin.Gedekar&passhash=440909494'


progress_bar = tqdm(total=len(id_values), desc="Fetching limits for each ID")


upper_warning_limits = {}
upper_error_limits = {}
lower_warning_limits = {}
lower_error_limits = {}


sensor_device_names = {}
DeviceIDs = {}
parent_device_names = {}
for id_value in id_values:
    device_name_endpoint = f'https://{server_address}/api/getsensordetails.json?id={id_value}&username=Ashwin.Gedekar&passhash=440909494'
    device_name_response = requests.get(device_name_endpoint)
    if device_name_response.status_code == 200:
        device_name_json = device_name_response.json()
        parent_device_name = device_name_json["sensordata"]["parentdevicename"]
        sensor_device_name = device_name_json["sensordata"]["name"]
        DeviceID = device_name_json["sensordata"]["parentdeviceid"]
        
        sensor_device_names[id_value] = sensor_device_name
        DeviceIDs[id_value] = DeviceID
        parent_device_names[id_value] = parent_device_name

    progress_bar.update(1)

progress_bar.close()


progress_bar = tqdm(total=len(id_values), desc="Fetching limits for each ID")

for id_value in id_values:
    id_data = {}
    response_upper_warning = requests.get(f"{api_endpoint_upper_warning}&id={id_value}")
    response_upper_error = requests.get(f"{api_endpoint_upper_error}&id={id_value}")
    response_lower_warning = requests.get(f"{api_endpoint_lower_warning}&id={id_value}")
    response_lower_error = requests.get(f"{api_endpoint_lower_error}&id={id_value}")

    id_data["Sensor Name"] = sensor_device_names.get(id_value, "Sensor name not available")
    id_data["Device ID"] = DeviceIDs.get(id_value, "Device ID not available")
    id_data["Device Name"] = parent_device_names.get(id_value, "Device name not available")
    
    # Traffic total 
    if response_upper_warning.status_code == 200:
        match_upper_warning = re.search(r'<result>(\d+)</result>', response_upper_warning.text)
        if match_upper_warning:
            upper_warning_limits[id_value] = int(match_upper_warning.group(1)) * 8 / 1000000  # Convert bytes to megabits
    


    if response_upper_error.status_code == 200:
       match_upper_error = re.search(r'<result>(\d+)</result>', response_upper_error.text)
       if match_upper_error:
          upper_error_limits[id_value] = int(match_upper_error.group(1)) * 8 / 1000000  # Convert bytes to megabits
    

    if response_lower_warning.status_code == 200:
        match_lower_warning = re.search(r'<result>(\d+)</result>', response_lower_warning.text)
        if match_lower_warning:
            lower_warning_limits[id_value] = int(match_lower_warning.group(1)) * 8 / 1000000  # Convert bytes to megabits

    if response_lower_error.status_code == 200:
        match_lower_error = re.search(r'<result>(\d+)</result>', response_lower_error.text)
        if match_lower_error:
            lower_error_limits[id_value] = int(match_lower_error.group(1)) * 8 / 1000000  # Convert bytes to megabits
    
   
    progress_bar.update(1)

progress_bar.close()


data_list = []


for id_value in tqdm(id_values, desc="Processing IDs"):  
    
    api_endpoint = f'https://{server_address}/api/historicdata.csv?id={id_value}&avg={flags.get("avg")}&sdate={flags.get("sdate")}&edate={flags.get("edate")}&username={server_parameters.get("username")}&passhash={server_parameters.get("passhash")}'

   
    response = requests.get(api_endpoint)


    if response.status_code == 200:
        id_data = {
            "ID": id_value,
            "Sensor Name": sensor_device_names.get(id_value, "Sensor name not available"),
            "Device ID": DeviceIDs.get(id_value, "Device ID not available"),
            "Device Name": parent_device_names.get(id_value, "Device name not available"),
            "TRAFFIC TOTAL UPPER ERROR LIMIT": upper_error_limits.get(id_value, "not_set"),
            "TRAFFIC TOTAL LOWER ERROR LIMIT": lower_error_limits.get(id_value, "not_set"),
            "TRAFFIC TOTAL UPPER WARNING LIMIT": upper_warning_limits.get(id_value, "not_set"),
            "TRAFFIC TOTAL LOWER WARNING LIMIT": lower_warning_limits.get(id_value, "not_set")
        }

        try:
           
            df = pd.read_csv(StringIO(response.text), na_values=['NaN', 'N/A', ''])

           
            df.columns = df.columns.str.strip()

            
            selected_columns = ["Date Time", "Traffic Total (Speed)", "Traffic Total (Speed)(RAW)"]
            selected_data = df[selected_columns]

       
            selected_data.loc[:, selected_columns[2:]] = selected_data[selected_columns[2:]].apply(pd.to_numeric, errors='coerce')

           
            selected_data = selected_data.dropna(subset=["Traffic Total (Speed)(RAW)"])

           
            if not selected_data.empty:
                selected_data["Traffic Total (Speed)"] = selected_data["Traffic Total (Speed)"].fillna("< 0.01")

                if flags.get("max") == '1':
                    
                    max_raw_speed_row = selected_data.loc[selected_data["Traffic Total (Speed)(RAW)"].idxmax()]
                    id_data["MAX SPEED"] = max_raw_speed_row['Traffic Total (Speed)']
                    id_data["MAX SPEED RAW"] = max_raw_speed_row['Traffic Total (Speed)(RAW)']
                    id_data["MAX SPEED DATE TIME"] = max_raw_speed_row['Date Time']

                    
                    if flags.get("thr") == '1' and id_value in upper_error_limits and id_value in upper_warning_limits:
                        upper_error_limit = upper_error_limits[id_value]
                        upper_warning_limit = upper_warning_limits[id_value]

                        id_data["THRESHOLD MESSAGE (MAX)"] = f"set"
                         
                       
                    else:
                        id_data["THRESHOLD MESSAGE (MAX)"] = f"not_set"

                
                min_raw_speed_row = selected_data.loc[selected_data["Traffic Total (Speed)(RAW)"].idxmin()]
                id_data["MIN SPEED"] = min_raw_speed_row['Traffic Total (Speed)']
                id_data["MIN SPEED RAW"] = min_raw_speed_row['Traffic Total (Speed)(RAW)']
                id_data["MIN SPEED DATE TIME"] = min_raw_speed_row['Date Time']

                
                if flags.get("thr") == '1' and id_value in lower_error_limits and id_value in lower_warning_limits:
                    min_speed_value = float(min_raw_speed_row['Traffic Total (Speed)'].split()[0])

                    lower_error_limit = lower_error_limits[id_value]
                    lower_warning_limit = lower_warning_limits[id_value]
                    id_data["THRESHOLD MESSAGE (MIN)"] = f"set"

                    
                else:
                    id_data["THRESHOLD MESSAGE (MIN)"] = f"not_set"

            else:
                id_data["THRESHOLD MESSAGE (MIN)"] = f"No non-NaN values found in 'Traffic Total (Speed)(RAW)' for ID {id_value}"

        except Exception as e:
            id_data["THRESHOLD MESSAGE (MIN)"] = f"Error processing CSV data for ID {id_value}: {e}"

        data_list.append(id_data)


df_output = pd.DataFrame(data_list)

for data_dict in data_list:
    print(f"ID {data_dict['ID']}:")
    print('-' * (len(f"ID {data_dict['ID']}:")))
    print(f"Sensor Name: {data_dict['Sensor Name']}")
    print(f"Device ID: {data_dict['Device ID']}")
    print(f"Device Name: {data_dict['Device Name']}")
    print(f"TRAFFIC TOTAL UPPER ERROR LIMIT: {data_dict.get('TRAFFIC TOTAL UPPER ERROR LIMIT', 'not_set')}")
    print(f"TRAFFIC TOTAL LOWER ERROR LIMIT: {data_dict.get('TRAFFIC TOTAL LOWER ERROR LIMIT', 'not_set')}")
    print(f"TRAFFIC TOTAL UPPER WARNING LIMIT: {data_dict.get('TRAFFIC TOTAL UPPER WARNING LIMIT', 'not_set')}")
    print(f"TRAFFIC TOTAL LOWER WARNING LIMIT: {data_dict.get('TRAFFIC TOTAL LOWER WARNING LIMIT', 'not_set')}")
    print("#" * 55)


output_directory = "output"
os.makedirs(output_directory, exist_ok=True)


current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


output_file_path = os.path.join(output_directory, f"output_{current_datetime}.csv")


df_output.to_csv(output_file_path, index=False)


print(f"\nOutput has been saved to {output_file_path}")


  

