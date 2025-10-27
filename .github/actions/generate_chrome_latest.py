import subprocess
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
from datetime import datetime
import os
import yaml
from pytz import timezone

def fetch_chrome_versions(channel):
    print(f"Fetching Chrome version history for channel: {channel}")
    # Use the correct API endpoint and channel identifier
    url = f"https://versionhistory.googleapis.com/v1/chrome/platforms/mac/channels/{channel}/versions"
    result = subprocess.run(["curl", url], capture_output=True, text=True)
    return result.stdout

def fetch_mac_version(channel):
    print(f"Fetching latest Mac version for channel: {channel}")
    url = f"https://chromiumdash.appspot.com/fetch_releases?platform=Mac&channel={channel}"
    result = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
    if not result.stdout:
        return {"version": "N/A", "time": "N/A", "timestamp": "N/A"}
    try:
        data = json.loads(result.stdout)
        if data:
            version = data[0]["version"]
            timestamp = int(data[0]["time"])
            release_time = datetime.fromtimestamp(timestamp / 1000, timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")
            return {"version": version, "time": release_time, "timestamp": timestamp}
    except json.JSONDecodeError:
        return {"version": "N/A", "time": "N/A", "timestamp": "N/A"}
    return {"version": "N/A", "time": "N/A", "timestamp": "N/A"}

def convert_to_xml(json_data):
    root = ET.Element("versions")
    last_updated = ET.SubElement(root, "last_updated")
    last_updated.text = datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")
    for version in json_data["versions"]:
        version_element = ET.SubElement(root, "version")
        name_element = ET.SubElement(version_element, "name")
        name_element.text = version["name"]
        version_element = ET.SubElement(version_element, "version")
        version_element.text = version["version"]
    return minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

def convert_to_yaml(json_data):
    last_updated = {"last_updated": datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")}
    json_data.update(last_updated)
    if "nextPageToken" in json_data and not json_data["nextPageToken"]:
        del json_data["nextPageToken"]
    return yaml.dump(json_data, default_flow_style=False)

def convert_to_json(json_data):
    last_updated = {"last_updated": datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")}
    json_data = {**last_updated, **json_data}
    if "nextPageToken" in json_data and not json_data["nextPageToken"]:
        del json_data["nextPageToken"]
    return json.dumps(json_data, indent=2)

def convert_mac_versions_to_xml(stable, extended, beta, dev, canary):
    root = ET.Element("mac_versions")
    last_updated = ET.SubElement(root, "last_updated")
    last_updated.text = datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")

    stable_element = ET.SubElement(root, "stable")
    version_element = ET.SubElement(stable_element, "version")
    version_element.text = stable["version"]
    time_element = ET.SubElement(stable_element, "release_time")
    time_element.text = stable["time"]
    download_url = ET.SubElement(stable_element, "latest_download")
    download_url.text = "https://dl.google.com/chrome/mac/stable/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"

    extended_element = ET.SubElement(root, "extended")
    version_element = ET.SubElement(extended_element, "version")
    version_element.text = extended["version"]
    time_element = ET.SubElement(extended_element, "release_time")
    time_element.text = extended["time"]
    download_url = ET.SubElement(extended_element, "extended_download")
    download_url.text = "https://dl.google.com/chrome/mac/stable/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"

    beta_element = ET.SubElement(root, "beta")
    version_element = ET.SubElement(beta_element, "version")
    version_element.text = beta["version"]
    time_element = ET.SubElement(beta_element, "release_time")
    time_element.text = beta["time"]
    download_url = ET.SubElement(beta_element, "beta_download")
    download_url.text = "https://dl.google.com/chrome/mac/beta/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"

    dev_element = ET.SubElement(root, "dev")
    version_element = ET.SubElement(dev_element, "version")
    version_element.text = dev["version"]
    time_element = ET.SubElement(dev_element, "release_time")
    time_element.text = dev["time"]
    download_url = ET.SubElement(dev_element, "dev_download")
    download_url.text = "https://dl.google.com/chrome/mac/universal/dev/googlechromedev.dmg"

    canary_element = ET.SubElement(root, "canary")
    version_element = ET.SubElement(canary_element, "version")
    version_element.text = canary["version"]
    time_element = ET.SubElement(canary_element, "release_time")
    time_element.text = canary["time"]
    download_url = ET.SubElement(canary_element, "canary_download")
    download_url.text = "https://dl.google.com/chrome/mac/universal/canary/googlechromecanary.dmg"

    return minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

def convert_mac_versions_to_yaml(stable, extended, beta, dev, canary):
    last_updated = {"last_updated": datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")}
    mac_versions = {
        "stable": {
            "version": stable["version"],
            "time": stable["time"],
            "latest_download": "https://dl.google.com/chrome/mac/stable/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "extended": {
            "version": extended["version"],
            "time": extended["time"],
            "extended_download": "https://dl.google.com/chrome/mac/extended/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "beta": {
            "version": beta["version"],
            "time": beta["time"],
            "beta_download": "https://dl.google.com/chrome/mac/beta/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "dev": {
            "version": dev["version"],
            "time": dev["time"],
            "dev_download": "https://dl.google.com/chrome/mac/universal/dev/googlechromedev.dmg"
        },
        "canary": {
            "version": canary["version"],
            "time": canary["time"],
            "canary_download": "https://dl.google.com/chrome/mac/universal/canary/googlechromecanary.dmg"
        }
    }
    mac_versions = {**last_updated, **mac_versions}
    return yaml.dump(mac_versions, default_flow_style=False)

def convert_mac_versions_to_json(stable, extended, beta, dev, canary):
    mac_versions = {
        "stable": {
            "version": stable["version"],
            "time": stable["time"],
            "latest_download": "https://dl.google.com/chrome/mac/stable/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "extended": {
            "version": extended["version"],
            "time": extended["time"],
            "extended_download": "https://dl.google.com/chrome/mac/extended/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "beta": {
            "version": beta["version"],
            "time": beta["time"],
            "beta_download": "https://dl.google.com/chrome/mac/beta/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "dev": {
            "version": dev["version"],
            "time": dev["time"],
            "dev_download": "https://dl.google.com/chrome/mac/universal/dev/googlechromedev.dmg"
        },
        "canary": {
            "version": canary["version"],
            "time": canary["time"],
            "canary_download": "https://dl.google.com/chrome/mac/universal/canary/googlechromecanary.dmg"
        }
    }
    last_updated = {"last_updated": datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")}
    mac_versions = {**last_updated, **mac_versions}
    return json.dumps(mac_versions, indent=2)

def print_mac_history_versions(history_json):
    print("Mac Version History:")
    for entry in history_json:
        version = entry.get("version", "N/A")
        milestone = entry.get("milestone", "N/A")
        timestamp = entry.get("time", None)
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000, timezone('US/Eastern'))
            formatted_time = dt.strftime("%B %d, %Y %I:%M %p %Z")
        else:
            formatted_time = "N/A"
        print(f"  Version: {version}, Milestone: {milestone}, Time: {formatted_time} ({timestamp})")

def main():
    # Create the output directory if it doesn't exist
    output_dir = "latest_chrome_files"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")

    channels = [
        {"name": "extended", "channelType": "EXTENDED"},
        {"name": "stable", "channelType": "STABLE"},
        {"name": "beta", "channelType": "BETA"},
        {"name": "dev", "channelType": "DEV"},
        {"name": "canary", "channelType": "CANARY"},
        {"name": "canary_asan", "channelType": "CANARY_ASAN"},
        {"name": "all", "channelType": "ALL"}
    ]
    
    for channel in channels:
        print(f"Processing channel: {channel['channelType']}")
        json_data = json.loads(fetch_chrome_versions(channel["name"]))
        xml_data = convert_to_xml(json_data)
        yaml_data = convert_to_yaml(json_data)
        json_data_str = convert_to_json(json_data)
        
        xml_filename = os.path.join(output_dir, f"chrome_{channel['channelType'].lower()}_history.xml")
        yaml_filename = os.path.join(output_dir, f"chrome_{channel['channelType'].lower()}_history.yaml")
        json_filename = os.path.join(output_dir, f"chrome_{channel['channelType'].lower()}_history.json")
        
        with open(xml_filename, "w") as xml_file:
            xml_file.write(xml_data)
        print(f"Wrote XML: {xml_filename}")
        with open(yaml_filename, "w") as yaml_file:
            yaml_file.write(yaml_data)
        print(f"Wrote YAML: {yaml_filename}")
        with open(json_filename, "w") as json_file:
            json_file.write(json_data_str)
        print(f"Wrote JSON: {json_filename}")
    
    # Fetch and save Mac Stable, Beta, Dev, and Canary versions
    mac_channels = ["Stable", "Extended", "Beta", "Dev", "Canary"]
    print("Fetching Mac channel versions...")
    mac_versions = {channel.lower(): fetch_mac_version(channel) for channel in mac_channels}
    mac_versions_xml = convert_mac_versions_to_xml(
        mac_versions["stable"], mac_versions["extended"], mac_versions["beta"], mac_versions["dev"], mac_versions["canary"]
    )
    mac_versions_yaml = convert_mac_versions_to_yaml(
        mac_versions["stable"], mac_versions["extended"], mac_versions["beta"], mac_versions["dev"], mac_versions["canary"]
    )
    mac_versions_json = convert_mac_versions_to_json(
        mac_versions["stable"], mac_versions["extended"], mac_versions["beta"], mac_versions["dev"], mac_versions["canary"]
    )
    
    xml_filename = os.path.join(output_dir, "chrome_latest_versions.xml")
    yaml_filename = os.path.join(output_dir, "chrome_latest_versions.yaml")
    json_filename = os.path.join(output_dir, "chrome_latest_versions.json")
    
    with open(xml_filename, "w") as xml_file:
        xml_file.write(mac_versions_xml)
    print(f"Wrote Mac XML: {xml_filename}")
    with open(yaml_filename, "w") as yaml_file:
        yaml_file.write(mac_versions_yaml)
    print(f"Wrote Mac YAML: {yaml_filename}")
    with open(json_filename, "w") as json_file:
        json_file.write(mac_versions_json)
    print(f"Wrote Mac JSON: {json_filename}")

if __name__ == "__main__":
    main()
