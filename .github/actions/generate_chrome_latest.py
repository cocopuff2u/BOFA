import subprocess
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
from datetime import datetime
import os
import yaml
from pytz import timezone

def fetch_chrome_versions(channel):
    """
    Fetch Chrome version history for a given channel using the Google Version History API.
    """
    print(f"Fetching Chrome version history for channel: {channel}")
    url = f"https://versionhistory.googleapis.com/v1/chrome/platforms/mac/channels/{channel}/versions"
    result = subprocess.run(["curl", url], capture_output=True, text=True)
    return result.stdout

def fetch_mac_version(channel):
    """
    Fetch the latest Mac Chrome version for a given channel.
    Returns a dict with version, formatted release time, and timestamp.
    """
    print(f"Fetching latest Mac version for channel: {channel}")
    url = f"https://versionhistory.googleapis.com/v1/chrome/platforms/mac/channels/{channel.lower()}/versions/all/releases?filter=endtime=none"
    result = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
    if not result.stdout:
        return {"version": "N/A", "time": "N/A", "timestamp": "N/A"}
    try:
        data = json.loads(result.stdout)
        releases = data.get("releases", [])
        if not releases:
            return {"version": "N/A", "time": "N/A", "timestamp": "N/A"}
        # Find the release with the highest fraction, or the most recent startTime
        latest_release = max(
            releases,
            key=lambda r: (
                r.get("fraction", 0),
                r.get("serving", {}).get("startTime", "")
            )
        )
        version = latest_release.get("version", "N/A")
        start_time_str = latest_release.get("serving", {}).get("startTime", None)
        if start_time_str:
            dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            dt = timezone('US/Eastern').localize(dt)
            release_time = dt.strftime("%B %d, %Y %I:%M %p %Z")
            timestamp = int(dt.timestamp() * 1000)
        else:
            release_time = "N/A"
            timestamp = "N/A"
        return {"version": version, "time": release_time, "timestamp": timestamp}
    except Exception as e:
        print(f"Error fetching mac version for channel {channel}: {e}")
        return {"version": "N/A", "time": "N/A", "timestamp": "N/A"}

def convert_to_xml(json_data):
    """
    Convert Chrome version data from JSON to XML format.
    """
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
    """
    Convert Chrome version data from JSON to YAML format.
    """
    last_updated = {"last_updated": datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")}
    json_data.update(last_updated)
    if "nextPageToken" in json_data and not json_data["nextPageToken"]:
        del json_data["nextPageToken"]
    return yaml.dump(json_data, default_flow_style=False)

def convert_to_json(json_data):
    """
    Convert Chrome version data to JSON string with last_updated.
    """
    last_updated = {"last_updated": datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")}
    json_data = {**last_updated, **json_data}
    if "nextPageToken" in json_data and not json_data["nextPageToken"]:
        del json_data["nextPageToken"]
    return json.dumps(json_data, indent=2)

def convert_mac_versions_to_xml(stable, extended, beta, dev, canary, canary_asan):
    """
    Convert Mac Chrome channel versions to XML format.
    """
    root = ET.Element("mac_versions")
    last_updated = ET.SubElement(root, "last_updated")
    last_updated.text = datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")

    stable_element = ET.SubElement(root, "stable")
    version_element = ET.SubElement(stable_element, "version")
    version_element.text = stable["version"]
    time_element = ET.SubElement(stable_element, "release_time")
    time_element.text = stable["time"]
    download_url = ET.SubElement(stable_element, "download_link")
    download_url.text = "https://dl.google.com/chrome/mac/stable/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"

    extended_element = ET.SubElement(root, "extended")
    version_element = ET.SubElement(extended_element, "version")
    version_element.text = extended["version"]
    time_element = ET.SubElement(extended_element, "release_time")
    time_element.text = extended["time"]
    download_url = ET.SubElement(extended_element, "download_link")
    download_url.text = "https://dl.google.com/chrome/mac/stable/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"

    beta_element = ET.SubElement(root, "beta")
    version_element = ET.SubElement(beta_element, "version")
    version_element.text = beta["version"]
    time_element = ET.SubElement(beta_element, "release_time")
    time_element.text = beta["time"]
    download_url = ET.SubElement(beta_element, "download_link")
    download_url.text = "https://dl.google.com/chrome/mac/beta/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"

    dev_element = ET.SubElement(root, "dev")
    version_element = ET.SubElement(dev_element, "version")
    version_element.text = dev["version"]
    time_element = ET.SubElement(dev_element, "release_time")
    time_element.text = dev["time"]
    download_url = ET.SubElement(dev_element, "download_link")
    download_url.text = "https://dl.google.com/chrome/mac/universal/dev/googlechromedev.dmg"

    canary_element = ET.SubElement(root, "canary")
    version_element = ET.SubElement(canary_element, "version")
    version_element.text = canary["version"]
    time_element = ET.SubElement(canary_element, "release_time")
    time_element.text = canary["time"]
    download_url = ET.SubElement(canary_element, "download_link")
    download_url.text = "https://dl.google.com/chrome/mac/universal/canary/googlechromecanary.dmg"

    canary_asan_element = ET.SubElement(root, "canary_asan")
    version_element = ET.SubElement(canary_asan_element, "version")
    version_element.text = canary_asan["version"]
    time_element = ET.SubElement(canary_asan_element, "release_time")
    time_element.text = canary_asan["time"]
    download_url = ET.SubElement(canary_asan_element, "download_link")
    download_url.text = "https://dl.google.com/chrome/mac/universal/canary-asan/googlechromecanaryasan.dmg"

    return minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

def convert_mac_versions_to_yaml(stable, extended, beta, dev, canary, canary_asan):
    """
    Convert Mac Chrome channel versions to YAML format.
    """
    last_updated = {"last_updated": datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")}
    mac_versions = {
        "stable": {
            "version": stable["version"],
            "time": stable["time"],
            "download_link": "https://dl.google.com/chrome/mac/stable/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "extended": {
            "version": extended["version"],
            "time": extended["time"],
            "download_link": "https://dl.google.com/chrome/mac/stable/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "beta": {
            "version": beta["version"],
            "time": beta["time"],
            "download_link": "https://dl.google.com/chrome/mac/beta/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "dev": {
            "version": dev["version"],
            "time": dev["time"],
            "download_link": "https://dl.google.com/chrome/mac/universal/dev/googlechromedev.dmg"
        },
        "canary": {
            "version": canary["version"],
            "time": canary["time"],
            "download_link": "https://dl.google.com/chrome/mac/universal/canary/googlechromecanary.dmg"
        },
        "canary_asan": {
            "version": canary_asan["version"],
            "time": canary_asan["time"],
            "download_link": "https://dl.google.com/chrome/mac/universal/canary/googlechromecanary.dmg"
        }
    }
    mac_versions = {**last_updated, **mac_versions}
    return yaml.dump(mac_versions, default_flow_style=False)

def convert_mac_versions_to_json(stable, extended, beta, dev, canary, canary_asan):
    """
    Convert Mac Chrome channel versions to JSON format.
    """
    mac_versions = {
        "stable": {
            "version": stable["version"],
            "time": stable["time"],
            "download_link": "https://dl.google.com/chrome/mac/stable/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "extended": {
            "version": extended["version"],
            "time": extended["time"],
            "download_link": "https://dl.google.com/chrome/mac/stable/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "beta": {
            "version": beta["version"],
            "time": beta["time"],
            "download_link": "https://dl.google.com/chrome/mac/beta/accept_tos%3Dhttps%253A%252F%252Fwww.google.com%252Fintl%252Fen_ph%252Fchrome%252Fterms%252F%26_and_accept_tos%3Dhttps%253A%252F%252Fpolicies.google.com%252Fterms/googlechrome.pkg"
        },
        "dev": {
            "version": dev["version"],
            "time": dev["time"],
            "download_link": "https://dl.google.com/chrome/mac/universal/dev/googlechromedev.dmg"
        },
        "canary": {
            "version": canary["version"],
            "time": canary["time"],
            "download_link": "https://dl.google.com/chrome/mac/universal/canary/googlechromecanary.dmg"
        },
        "canary_asan": {
            "version": canary_asan["version"],
            "time": canary_asan["time"],
            "download_link": "https://dl.google.com/chrome/mac/universal/canary/googlechromecanary.dmg"
        }
    }
    last_updated = {"last_updated": datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")}
    mac_versions = {**last_updated, **mac_versions}
    return json.dumps(mac_versions, indent=2)

def fetch_chrome_history(channel):
    """
    Fetch Chrome release history for a given channel.
    Returns a list of dicts with version, release date, end date, fraction, and fraction group.
    """
    url = f"https://versionhistory.googleapis.com/v1/chrome/platforms/mac/channels/{channel}/versions/all/releases"
    result = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
    if not result.stdout:
        return []
    try:
        data = json.loads(result.stdout)
        releases = data.get("releases", [])
        history = []
        for release in releases:
            version = release.get("version")
            start_time = format_time(release.get("serving", {}).get("startTime"))
            end_time = format_time(release.get("serving", {}).get("endTime"))
            fraction_val = release.get("fraction", 0)
            # Format fraction as a percentage string, up to two decimals
            fraction_pct = fraction_val * 100
            if fraction_pct == int(fraction_pct):
                fraction = f"{int(fraction_pct)}%"
            else:
                fraction = f"{fraction_pct:.2f}".rstrip('0').rstrip('.') + "%"
            fraction_group = release.get("fractionGroup", "N/A")
            history.append({
                "version": version,
                "release_date": start_time,
                "end_date": end_time,
                "fraction": fraction,
                "fraction_group": fraction_group
            })
        return history
    except Exception as e:
        print(f"Error processing history: {e}")
        return []

def format_time(iso_time):
    """
    Convert ISO time string to formatted date string.
    """
    if not iso_time:
        return "N/A"
    try:
        dt = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        return dt.strftime("%B %d, %Y %I:%M %p")
    except ValueError:
        return "Invalid Time"

def convert_history_to_json(history):
    """
    Convert Chrome release history to JSON string.
    """
    return json.dumps({"releases": history}, indent=2)

def convert_history_to_yaml(history):
    """
    Convert Chrome release history to YAML string.
    """
    return yaml.dump({"releases": history}, default_flow_style=False)

def convert_history_to_xml(history):
    """
    Convert Chrome release history to XML format.
    """
    root = ET.Element("releases")
    last_updated = ET.SubElement(root, "last_updated")
    last_updated.text = datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")
    for entry in history:
        release_element = ET.SubElement(root, "release")
        version_element = ET.SubElement(release_element, "version")
        version_element.text = entry["version"]
        start_time_element = ET.SubElement(release_element, "release_date")
        start_time_element.text = entry["release_date"]
        end_time_element = ET.SubElement(release_element, "end_date")
        end_time_element.text = entry["end_date"]
        fraction_element = ET.SubElement(release_element, "fraction")
        fraction_element.text = entry["fraction"]
        fraction_group_element = ET.SubElement(release_element, "fraction_group")
        fraction_group_element.text = str(entry["fraction_group"])
    return minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

def main():
    """
    Main function to fetch, convert, and save Chrome version and history data for all channels.
    """
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
        {"name": "canary_asan", "channelType": "CANARY_ASAN"}
    ]
    
    # Fetch and save version history for each channel in XML, YAML, and JSON
    for channel in channels:
        print(f"Processing channel: {channel['channelType']}")
        try:
            json_data = json.loads(fetch_chrome_versions(channel["name"]))
        except Exception as e:
            print(f"Error fetching versions for {channel['name']}: {e}")
            continue
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
    mac_channels = ["Stable", "Extended", "Beta", "Dev", "Canary", "Canary_ASAN"]
    print("Fetching Mac channel versions...")
    mac_versions = {}
    for channel in mac_channels:
        mac_versions[channel.lower()] = fetch_mac_version(channel)
    mac_versions_xml = convert_mac_versions_to_xml(
        mac_versions["stable"], mac_versions["extended"], mac_versions["beta"], mac_versions["dev"], mac_versions["canary"], mac_versions["canary_asan"]
    )
    mac_versions_yaml = convert_mac_versions_to_yaml(
        mac_versions["stable"], mac_versions["extended"], mac_versions["beta"], mac_versions["dev"], mac_versions["canary"], mac_versions["canary_asan"]
    )
    mac_versions_json = convert_mac_versions_to_json(
        mac_versions["stable"], mac_versions["extended"], mac_versions["beta"], mac_versions["dev"], mac_versions["canary"], mac_versions["canary_asan"]
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

    # Fetch and save Chrome release history for all channels
    print("Fetching Chrome history for all channels...")
    channels = ["stable", "extended", "beta", "dev", "canary", "canary_asan"]
    for channel in channels:
        print(f"Processing channel: {channel}")
        history = fetch_chrome_history(channel)
        history_json = convert_history_to_json(history)
        history_yaml = convert_history_to_yaml(history)
        history_xml = convert_history_to_xml(history)

        json_filename = os.path.join(output_dir, f"chrome_{channel}_history.json")
        yaml_filename = os.path.join(output_dir, f"chrome_{channel}_history.yaml")
        xml_filename = os.path.join(output_dir, f"chrome_{channel}_history.xml")

        with open(json_filename, "w") as json_file:
            json_file.write(history_json)
        print(f"Wrote JSON: {json_filename}")
        with open(yaml_filename, "w") as yaml_file:
            yaml_file.write(history_yaml)
        print(f"Wrote YAML: {yaml_filename}")
        with open(xml_filename, "w") as xml_file:
            xml_file.write(history_xml)
        print(f"Wrote XML: {xml_filename}")

    # Convert all *_history.json files to YAML in the output directory
    for filename in os.listdir(output_dir):
        if filename.endswith("_history.json"):
            json_path = os.path.join(output_dir, filename)
            yaml_path = os.path.join(output_dir, filename.replace(".json", ".yaml"))
            try:
                with open(json_path, "r") as f:
                    data = json.load(f)
                with open(yaml_path, "w") as f:
                    yaml.dump(data, f, sort_keys=False, allow_unicode=True)
            except Exception as e:
                print(f"Error converting {json_path} to YAML: {e}")

    # Ensure all *_history.json and *_history.yaml files have last_updated at the top level
    now_str = datetime.now(timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p %Z")
    for filename in os.listdir(output_dir):
        if filename.endswith("_history.json"):
            json_path = os.path.join(output_dir, filename)
            try:
                with open(json_path, "r") as f:
                    data = json.load(f)
                if "last_updated" not in data:
                    data = {"last_updated": now_str, **data}
                    with open(json_path, "w") as f:
                        json.dump(data, f, indent=2)
            except Exception as e:
                print(f"Error updating last_updated in {json_path}: {e}")
        if filename.endswith("_history.yaml"):
            yaml_path = os.path.join(output_dir, filename)
            try:
                with open(yaml_path, "r") as f:
                    data = yaml.safe_load(f)
                if data is not None and "last_updated" not in data:
                    data = {"last_updated": now_str, **data}
                    with open(yaml_path, "w") as f:
                        yaml.dump(data, f, sort_keys=False, allow_unicode=True)
            except Exception as e:
                print(f"Error updating last_updated in {yaml_path}: {e}")

if __name__ == "__main__":
    main()
