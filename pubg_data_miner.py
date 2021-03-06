import requests
import json
import os
import time

import smtplib
import ssl

SEND_EMAIL_ENABLED = True

PLATFORM = "steam"
PLAYER_NAMES = "YOUR_USERNAME"
API_KEY = "YOUR_API_KEY"
PLAYER_REQUEST_URL = "https://api.pubg.com/shards/" + PLATFORM + "/players?filter[playerNames]=" + PLAYER_NAMES
API_REQUEST_HEADERS = {
    "Authorization": ("Bearer " + API_KEY),
    "Accept": "application/vnd.api+json"
}

MATCHES_FILE = "matches.txt"

def main():
    start_time = time.time()

    port = 587  # For starttls
    smtp_server = "smtp.gmail.com"
    sender_email = "SENDER_EMAIL"
    receiver_email = "RECEIVER_EMAIL"
    password = "SENDER_PASSWORD"
    match_count = 0
    message = "Subject: PUBG DATA MINER REPORT\n\n"
    print("Loading player info for " + PLAYER_NAMES)
    player_response = requests.get(PLAYER_REQUEST_URL, headers=API_REQUEST_HEADERS).json()["data"]

    # extract all match ids that are potentially new
    potentially_new_match_ids = set()
    for player in player_response:
        for match in player["relationships"]['matches']["data"]:
            potentially_new_match_ids.add(match["id"])

    #load all the match ids I already have telemetry for
    previous_match_file = open(MATCHES_FILE, "r+")
    previous_match_ids = set(previous_match_file.read().splitlines())

    #here are the ones we don't have data for
    potentially_new_match_ids.difference_update(previous_match_ids)
    print("Need data for " + str(len(potentially_new_match_ids)) + " new matches")

    #let's get all the telemetry urls
    telemetry_asset_ids = set()
    for match_id in potentially_new_match_ids:
        print("FETCHING: match " + match_id)
        match_request_url="https://api.pubg.com/shards/" + PLATFORM + "/matches/" + match_id
        match_response = requests.get(match_request_url, headers=API_REQUEST_HEADERS).json()
        print("RECEIVED: match " + match_id)
        match_attributes = match_response["data"]["attributes"]

        for asset in match_response["data"]["relationships"]["assets"]["data"]:
            telemetry_asset_ids.add(asset["id"])

        for item in match_response["included"]:
            if item["id"] in telemetry_asset_ids:
                print("FETCHING: telemetry " + item["attributes"]["URL"])
                #lets grab the telemetry data now
                telemetry = requests.get(item["attributes"]["URL"]).json()
                if not os.path.exists(match_attributes["mapName"]):
                    os.makedirs(match_attributes["mapName"])
                if not os.path.exists(os.path.join(match_attributes["mapName"], match_attributes["gameMode"])):
                    os.makedirs(os.path.join(match_attributes["mapName"], match_attributes["gameMode"]))
                telemetry_file = open(os.path.join(match_attributes["mapName"], match_attributes["gameMode"], item["id"]), 'w')
                print("WRITING: telemetry " + item["id"])
                telemetry_file.write(json.dumps(telemetry, ensure_ascii=False))
                match_count = match_count + 1
                message += (match_id + "\n")
                previous_match_file.write(match_id + "\n")
    message += ("\n\nTotal of " + str(match_count) + " matches downloaded in " + str(time.time() - start_time))

    if SEND_EMAIL_ENABLED:
        context = ssl.create_default_context()
        try:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls(context=context)

            print("logging in to email server")
            server.login(sender_email, password)
            print("login successful, sending email")
            server.sendmail(sender_email, receiver_email, message)
        except Exception as e:
            print(e)
        finally:
            server.quit()


if __name__ == "__main__": main()
