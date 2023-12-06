import requests
import os
import sys
import json
import time
import datetime
import sqlite3
import logging

# Configure the logging module
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create a logger
logger = logging.getLogger('collect_logger')


# function to collect data from cve.mitre.org
def cve_init():
    # Get the directory of the currently executing script (sub_script.py)
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Define the relative path to the data file
    cve_db_file = os.path.join(current_directory, '../data/cve_database.db')
    with sqlite3.connect(cve_db_file) as conn:
        # Create database cursor
        cursor = conn.cursor()

        # Define the table schema
        cursor.execute('''CREATE TABLE IF NOT EXISTS cves 
                        (INTEGER PRIMARY KEY, cve_id TEXT, json_blob TEXT)''')

        logger.info("\n############################################################################")
        logger.info("Starting data extraction of CVE data from National Vulnerability Database")
        logger.info("############################################################################\n")

        start_index = 0

        # Check if the meta table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='cve_meta'")
        table_exists = cursor.fetchone()
        if table_exists:
            logger.info("Reading cve_meta table data...")
            cursor.execute(f"SELECT init_finished FROM cve_meta")
            row = cursor.fetchone()
            init_finished = row[0]
            if init_finished == 1:
                logger.info("\n###############################################")
                logger.info("CVE initializtion already complete exiting now")
                logger.info("###############################################\n")
                return
            cursor.execute(f"SELECT offset FROM cve_meta")
            row = cursor.fetchone()
            start_index = row[0]
        else: 
            logger.info("Table cve_meta does not exist. Creating table...")
            # Create cve_meta table
            cursor.execute('''CREATE TABLE IF NOT EXISTS cve_meta 
                            (id INTEGER PRIMARY KEY, offset INTEGER, last_modified TEXT, init_finished INTEGER DEFAULT 0)''')
            current_time = format_datetime_string(str(datetime.datetime.now()))
            cursor.execute("INSERT INTO cve_meta (id, offset, last_modified) VALUES (?, ?, ?)", (12345, 0, current_time))
            conn.commit()
            
        logger.info(f"Reading in cve data starting with index {start_index}...")


        # Old code for writing data to json file
    
        # data_file_path = '../data/cves.json'
        # full_data_file_path = os.path.abspath(data_file_path)
        # if os.path.exists(data_file_path):
        #     with open(data_file_path, "r") as json_file:
        #         cves = json.load(json_file)
        # else:
        #     datetime_string = formate_datetime_string(str(datetime.datetime.now()))
        #     cves = { "offset": 0, "lastModified": datetime_string }

        # start_index = cves["offset"] 
        # check if there was already data in the file
        # if start_index > 0:
        #     logger.info(f"Data file already exists...\nLoading data from {full_data_file_path}\nNumber of records: {start_index}")
        # else:
        #     logger.info("Data file does not yet exist for CVEs...\nReading CVE data from first index...")
            

        # get the data from the website
        cve_api_url = "https://services.nvd.nist.gov/rest/json/cves/2.0?startIndex=" 
        logger.info(f"{cve_api_url}{start_index}&resultsPerPage=2000")
        response = requests.get(f"{cve_api_url}{start_index}&resultsPerPage=2000")
        init_finished = False 
        original_offset = start_index

        while (response.status_code == 200 or response.status_code == 403 or response.status_code == 503) and init_finished == False:
            early_exit = False
            if response.status_code == 403 or response.status_code == 503:
                for i in range(4):
                    if i == 3:
                        logger.info("Unable to recieve response from API, saving results and exiting...")
                        early_exit = True

                    logger.info(f"Retry #{i + 1}: Waiting for 10 seconds, due to API throttling...")
                    time.sleep(10)
                    response = requests.get(f"{cve_api_url}{start_index}&resultsPerPage=2000")
                    if response.status_code == 200:
                        logger.info("Retry Successful! Continuing processing...")
                        break

            if early_exit:
                break
            
            begining_index = start_index
            json_data = response.json()

            # Check if we are done after this loop
            vul_count = len(json_data["vulnerabilities"])
            if vul_count < 2000:
                init_finished = True

            for cve in json_data["vulnerabilities"]:
                start_index += 1
                # cves[cve['cve']['id']] = cve['cve']
                cve_id = str(cve['cve']['id'])
                json_blob = str(json.dumps(cve['cve']))
                cursor.execute("INSERT INTO cves (cve_id, json_blob) VALUES (?, ?)", (cve_id, json_blob))

            conn.commit()
            current_time = format_datetime_string(str(datetime.datetime.now()))
            cursor.execute("UPDATE cve_meta SET offset=?, last_modified=? WHERE id=12345", (start_index, current_time))
            logger.info(f"Completed batch with startIndex={begining_index}")
            # with open(full_data_file_path, "w") as json_file:
            #     cves["offset"] = start_index
            #     json.dump(cves, json_file, indent=4)
            #     logger.info(f"Completed batch with startIndex={begining_index}")

            # Wait 5 seconds to avoid throttling
            time.sleep(5)

            response = requests.get(f"{cve_api_url}{start_index}&resultsPerPage=2000")

        
        if init_finished == True:
            cursor.execute("UPDATE cve_meta SET init_finished=1 WHERE id=12345")

        total_records = start_index 
        records_added = total_records - original_offset

        logger.info("\n############################")
        logger.info("Data extraction completed")
        logger.info("############################\n")
        logger.info(f"Database Table: cves")
        logger.info(f"Database Meta-Table: cves_meta")
        logger.info(f"Total Records: {total_records}")
        logger.info(f"Records Added: {records_added}")
        logger.info(f"Database initialization finished: {init_finished}\n")

def cve_update():
    logger.info("Not added yet...")

# This funnction is used to determine if the cve table initialization is complete (1), not complete (0), or not started yet (3)
def check_cve_status():
    # Get the directory of the currently executing script (sub_script.py)
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Define the relative path to the data file
    cve_db_file = os.path.join(current_directory, '../data/cve_database.db')
    with sqlite3.connect(cve_db_file) as conn:
        # Create database cursor
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='cve_meta'")
        table_exists = cursor.fetchone()
        if table_exists:
            cursor.execute(f"SELECT init_finished FROM cve_meta")
            row = cursor.fetchone()
            init_finished = row[0]
            return init_finished
        else:
            return 3


    

def format_datetime_string(datetime_string):
    # Split the string into date and time components
    date_part, time_part = datetime_string.split(" ")

    # Split the time component into seconds and milliseconds
    seconds_part, milliseconds_part = time_part.split(".")

    # Keep only the first 3 decimal places (milliseconds)
    milliseconds_part = milliseconds_part[:3]

    # Concatenate the parts with "T" and the rounded milliseconds
    formatted_datetime = f"{date_part}T{seconds_part}.{milliseconds_part}"

    return formatted_datetime




if __name__ == "__main__":
    if len(sys.argv) > 1:
        data_source = sys.argv[1]
        if data_source == "cve_init":
            cve_init()
        elif data_source == "cve_update":
            cve_update()
        else:
            logger.info("ERROR: invalid data source. Please choose from one of the following: cve_init, cve_update")

    else:
        logger.info("Please provide a data source to update(example:python collect.py cve).")

