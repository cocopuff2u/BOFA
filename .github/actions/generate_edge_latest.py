import os
import requests
import plistlib
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import re
import json
import yaml
from collections import defaultdict
import pytz

# Define the Eastern Time Zone
eastern = pytz.timezone('US/Eastern')

def fetch_edge_latest(channel, url):
    response = requests.get(url)
    response.raise_for_status()
    
    xml_content = response.text
    
    output_dir = "latest_edge_files"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Directory '{output_dir}' created or already exists.")
    
    output_file = os.path.join(output_dir, f"edge_{channel}_version.xml")
    with open(output_file, "w") as file:
        file.write(xml_content)
    print(f"File '{output_file}' written successfully.")
    return output_file

def extract_info_from_xml(file_path):
    try:
        with open(file_path, 'rb') as file:
            plist_data = plistlib.load(file)
        
        # Debug prints to check the structure of the plist
        print(f"Parsing plist file: {file_path}")
        print(plist_data)
        
        date = plist_data[0].get('Date', 'N/A')
        location = plist_data[0].get('Location', 'N/A')
        title = plist_data[0].get('Title', 'N/A')
        
        # Format the title to only include numbers and special characters
        version = re.sub(r'[^0-9.]+', '', title)
        
        # Format the date to a user-readable format
        if date != 'N/A':
            date = date.astimezone(eastern).strftime('%B %d, %Y %I:%M %p %Z')
        
        return {
            "channel": os.path.basename(file_path).split('_')[1],
            "date": date,
            "location": location,
            "version": version
        }
    except Exception as e:
        print(f"Error parsing file {file_path}: {e}")
        return {
            "channel": os.path.basename(file_path).split('_')[1],
            "date": 'N/A',
            "location": 'N/A',
            "version": 'N/A'
        }

def create_summary_xml(info_list, insider_info_list, output_file):
    root = ET.Element("EdgeLatestVersions")
    
    # Add last_updated element
    last_updated = ET.SubElement(root, "last_updated")
    last_updated.text = datetime.now(eastern).strftime('%B %d, %Y %I:%M %p %Z')
    
    for info in info_list:
        entry = ET.SubElement(root, "Version")
        ET.SubElement(entry, "Channel").text = info["channel"]
        ET.SubElement(entry, "Date").text = info["date"]
        ET.SubElement(entry, "Location").text = info["location"]
        ET.SubElement(entry, "Version").text = info["version"]
    
    for info in insider_info_list:
        entry = ET.SubElement(root, "Version")
        ET.SubElement(entry, "Channel").text = f"insider_{info['channel']}"
        ET.SubElement(entry, "Date").text = info["date"]
        ET.SubElement(entry, "Location").text = info["location"]
        ET.SubElement(entry, "Version").text = info["version"]
    
    tree = ET.ElementTree(root)
    xml_str = ET.tostring(root, encoding='utf-8')
    pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
    
    with open(output_file, "w") as file:
        file.write(pretty_xml_str)
    print(f"Summary file '{output_file}' written successfully.")

def update_last_updated_in_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Find or create last_updated element
    last_updated = root.find("last_updated")
    if last_updated is None:
        last_updated = ET.Element("last_updated")
        root.insert(0, last_updated)
    
    last_updated.text = datetime.now(eastern).strftime('%B %d, %Y %I:%M %p %Z')
    
    tree = ET.ElementTree(root)
    xml_str = ET.tostring(root, encoding='utf-8')
    pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
    
    # Remove extra newlines and spaces
    pretty_xml_str = "\n".join([line for line in pretty_xml_str.split("\n") if line.strip()])
    
    with open(file_path, "w") as file:
        file.write(pretty_xml_str)
    print(f"Updated file '{file_path}' with last_updated.")

def fetch_edge_insider_canary_version(url):
    response = requests.get(url)
    response.raise_for_status()
    
    releases = response.json()
    macos_releases = [release for release in releases[0]["Releases"] if release["Platform"] == "MacOS"]
    
    if not macos_releases:
        print("No MacOS releases found.")
        return None
    
    latest_release = max(macos_releases, key=lambda x: x["PublishedTime"])
    
    artifact = next((artifact for artifact in latest_release["Artifacts"] if artifact["ArtifactName"] == "pkg"), None)
    location = artifact["Location"] if artifact else "N/A"
    
    return {
        "channel": "canary",
        "date": datetime.strptime(latest_release["PublishedTime"], '%Y-%m-%dT%H:%M:%S').astimezone(eastern).strftime('%B %d, %Y %I:%M %p %Z'),
        "location": location,
        "version": latest_release["ProductVersion"]
    }

def create_canary_xml(info, output_file):
    root = ET.Element("EdgeCanaryVersion")
    
    # Add last_updated element
    last_updated = ET.SubElement(root, "last_updated")
    last_updated.text = datetime.now(eastern).strftime('%B %d, %Y %I:%M %p %Z')
    
    entry = ET.SubElement(root, "Version")
    ET.SubElement(entry, "Channel").text = info["channel"]
    ET.SubElement(entry, "Date").text = info["date"]
    ET.SubElement(entry, "Location").text = info["location"]
    ET.SubElement(entry, "Version").text = info["version"]
    
    tree = ET.ElementTree(root)
    xml_str = ET.tostring(root, encoding='utf-8')
    pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
    
    with open(output_file, "w") as file:
        file.write(pretty_xml_str)
    print(f"Canary file '{output_file}' written successfully.")

def fetch_edge_insider_version(url, channel):
    response = requests.get(url)
    response.raise_for_status()
    
    releases = response.json()
    macos_releases = [release for release in releases[0]["Releases"] if release["Platform"] == "MacOS"]
    
    if not macos_releases:
        print(f"No MacOS releases found for {channel}.")
        return None
    
    latest_release = max(macos_releases, key=lambda x: x["PublishedTime"])
    
    artifact = next((artifact for artifact in latest_release["Artifacts"] if artifact["ArtifactName"] == "pkg"), None)
    location = artifact["Location"] if artifact else "N/A"
    
    return {
        "channel": channel,
        "date": datetime.strptime(latest_release["PublishedTime"], '%Y-%m-%dT%H:%M:%S').astimezone(eastern).strftime('%B %d, %Y %I:%M %p %Z'),
        "location": location,
        "version": latest_release["ProductVersion"]
    }

def create_insider_versions_xml(info_list, output_file):
    root = ET.Element("EdgeInsiderVersions")
    
    # Add last_updated element
    last_updated = ET.SubElement(root, "last_updated")
    last_updated.text = datetime.now(eastern).strftime('%B %d, %Y %I:%M %p %Z')
    
    for info in info_list:
        entry = ET.SubElement(root, "Version")
        ET.SubElement(entry, "Channel").text = info["channel"]
        ET.SubElement(entry, "Date").text = info["date"]
        ET.SubElement(entry, "Location").text = info["location"]
        ET.SubElement(entry, "Version").text = info["version"]
    
    tree = ET.ElementTree(root)
    xml_str = ET.tostring(root, encoding='utf-8')
    pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
    
    with open(output_file, "w") as file:
        file.write(pretty_xml_str)
    print(f"Insider versions file '{output_file}' written successfully.")

def convert_xml_to_json(xml_file, json_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    def etree_to_dict(t):
        d = {t.tag: {} if t.attrib else None}
        children = list(t)
        if children:
            dd = defaultdict(list)
            for dc in map(etree_to_dict, children):
                for k, v in dc.items():
                    dd[k].append(v)
            d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
        if t.attrib:
            d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
        if t.text:
            text = t.text.strip()
            if children or t.attrib:
                if text:
                    d[t.tag]['#text'] = text
            else:
                d[t.tag] = text
        return d
    
    data_dict = etree_to_dict(root)
    with open(json_file, "w") as file:
        json.dump(data_dict, file, indent=4)
    print(f"JSON file '{json_file}' written successfully.")

def convert_xml_to_yaml(xml_file, yaml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    def etree_to_dict(t):
        d = {t.tag: {} if t.attrib else None}
        children = list(t)
        if children:
            dd = defaultdict(list)
            for dc in map(etree_to_dict, children):
                for k, v in dc.items():
                    dd[k].append(v)
            d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
        if t.attrib:
            d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
        if t.text:
            text = t.text.strip()
            if children or t.attrib:
                if text:
                    d[t.tag]['#text'] = text
            else:
                d[t.tag] = text
        return d
    
    data_dict = etree_to_dict(root)
    
    # Create a new dictionary with the desired order
    if "EdgeLatestVersions" in data_dict:
        edge_versions = data_dict["EdgeLatestVersions"]
        ordered_dict = {
            "EdgeLatestVersions": {
                "last_updated": edge_versions.get("last_updated", ""),
                "Version": edge_versions.get("Version", [])
            }
        }
        data_dict = ordered_dict
    
    with open(yaml_file, "w") as file:
        yaml.dump(data_dict, file, default_flow_style=False, sort_keys=False)
    print(f"YAML file '{yaml_file}' written successfully.")

def convert_plist_to_json(xml_file, json_file):
    try:
        with open(xml_file, 'rb') as file:
            plist_data = plistlib.load(file)
        
        # Add last_updated field
        output_data = {
            "last_updated": datetime.now(eastern).strftime('%B %d, %Y %I:%M %p %Z'),
            "plist_data": plist_data
        }
        
        with open(json_file, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"JSON file '{json_file}' written successfully.")
    except Exception as e:
        print(f"Error converting plist to JSON: {e}")

def convert_plist_to_yaml(xml_file, yaml_file):
    try:
        with open(xml_file, 'rb') as file:
            plist_data = plistlib.load(file)
        
        # Add last_updated field
        output_data = {
            "last_updated": datetime.now(eastern).strftime('%B %d, %Y %I:%M %p %Z'),
            "plist_data": plist_data
        }
        
        with open(yaml_file, 'w') as f:
            yaml.dump(output_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"YAML file '{yaml_file}' written successfully.")
    except Exception as e:
        print(f"Error converting plist to YAML: {e}")

if __name__ == "__main__":
    # Remove the old channels dictionary and use insider_channels as channels
    channels = {
        "current": "https://edgeupdates.microsoft.com/api/products/stable",
        "canary": "https://edgeupdates.microsoft.com/api/products/canary",
        "dev": "https://edgeupdates.microsoft.com/api/products/dev",
        "beta": "https://edgeupdates.microsoft.com/api/products/beta"
    }
    
    info_list = []
    for channel, url in channels.items():
        info = fetch_edge_insider_version(url, channel)
        if info:
            info_list.append(info)
    
    output_file = os.path.join("latest_edge_files", "edge_latest_versions.xml")
    create_insider_versions_xml(info_list, output_file)
    update_last_updated_in_xml(output_file)
    
    # Convert XML to JSON and YAML
    convert_xml_to_json(output_file, os.path.join("latest_edge_files", "edge_latest_versions.json"))
    convert_xml_to_yaml(output_file, os.path.join("latest_edge_files", "edge_latest_versions.yaml"))
