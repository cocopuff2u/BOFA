import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re
import subprocess
import os
import json
import yaml
import pytz

# Fetch the JSON data
url = "https://product-details.mozilla.org/1.0/firefox_versions.json"
response = requests.get(url)
data = response.json()

# Fetch the second JSON data
url_releases = "https://product-details.mozilla.org/1.0/firefox.json"
response_releases = requests.get(url_releases)
data_releases = response_releases.json()

# Fetch the third JSON data
url_devedition = "https://product-details.mozilla.org/1.0/devedition.json"
response_devedition = requests.get(url_devedition)
data_devedition = response_devedition.json()

# Fetch the fourth JSON data
url_major_releases = "https://product-details.mozilla.org/1.0/firefox_history_major_releases.json"
response_major_releases = requests.get(url_major_releases)
data_major_releases = response_major_releases.json()

# Fetch the fifth JSON data
url_stability_releases = "https://product-details.mozilla.org/1.0/firefox_history_stability_releases.json"
response_stability_releases = requests.get(url_stability_releases)
data_stability_releases = response_stability_releases.json()

# Helper function to fetch the latest download link using curl
def fetch_download_url(url):
    try:
        return subprocess.check_output(
            ["curl", url, "-s", "-L", "-I", "-o", "/dev/null", "-w", "%{url_effective}"]
        ).decode("utf-8").strip()
    except subprocess.CalledProcessError:
        return "N/A"

# Fetch the latest download link for Firefox
firefox_download_url = fetch_download_url("https://download.mozilla.org/?product=firefox-pkg-latest-ssl&os=osx")

# Fetch the latest download link for ESR Edition
firefox_esr_download_url = fetch_download_url("https://download.mozilla.org/?product=firefox-esr-pkg-latest-ssl&os=osx")

# Fetch the latest download link for ESR115 Edition
firefox_esr115_download_url = fetch_download_url("https://download.mozilla.org/?product=firefox-esr115-pkg-latest-ssl&os=osx")

# Fetch the latest download link for Nightly Edition
firefox_beta_download_url = fetch_download_url("https://download.mozilla.org/?product=firefox-beta-pkg-latest-ssl&os=osx")

# Fetch the latest download link for Nightly Edition
firefox_nightly_download_url = fetch_download_url("https://download.mozilla.org/?product=firefox-nightly-pkg-latest-ssl&os=osx")

# Fetch the latest download link for Developer Edition
firefox_devedition_download_url = fetch_download_url("https://download.mozilla.org/?product=firefox-devedition-latest-ssl&os=osx")

# Create the root element for the first XML
root = ET.Element("latest")

# Define the Eastern Time Zone
eastern = pytz.timezone('US/Eastern')

# Add static information to the first XML
last_updated = ET.SubElement(root, "last_updated")
last_updated.text = datetime.now(eastern).strftime("%B %d, %Y %I:%M %p %Z")

# Helper function to get data or return "N/A" if blank
def get_data_or_na(key):
    return data.get(key, "N/A") or "N/A"

# Add dynamic information from the first JSON
package1 = ET.SubElement(root, "package")
ET.SubElement(package1, "name").text = "Firefox"
ET.SubElement(package1, "application_name").text = "Mozilla Firefox"
ET.SubElement(package1, "bundleId").text = "org.mozilla.firefox"
ET.SubElement(package1, "latest_version").text = get_data_or_na("LATEST_FIREFOX_VERSION")
ET.SubElement(package1, "latest_older_version").text = get_data_or_na("LATEST_FIREFOX_OLDER_VERSION")
ET.SubElement(package1, "currentVersionReleaseDate").text = get_data_or_na("LAST_RELEASE_DATE")
ET.SubElement(package1, "latest_download").text = firefox_download_url
ET.SubElement(package1, "latest_devel_version").text = get_data_or_na("LATEST_FIREFOX_DEVEL_VERSION")
ET.SubElement(package1, "latest_released_devel_version").text = get_data_or_na("LATEST_FIREFOX_RELEASED_DEVEL_VERSION")
ET.SubElement(package1, "latest_beta_download").text = firefox_beta_download_url
ET.SubElement(package1, "esr_version").text = get_data_or_na("FIREFOX_ESR")
ET.SubElement(package1, "esr_next_version").text = get_data_or_na("FIREFOX_ESR_NEXT")
ET.SubElement(package1, "esr_download").text = firefox_esr_download_url
ET.SubElement(package1, "esr115_version").text = get_data_or_na("FIREFOX_ESR115")
ET.SubElement(package1, "esr115_download").text = firefox_esr115_download_url
ET.SubElement(package1, "devedition_version").text = get_data_or_na("FIREFOX_DEVEDITION")
ET.SubElement(package1, "devedition_download").text = firefox_devedition_download_url
ET.SubElement(package1, "nightly_version").text = get_data_or_na("FIREFOX_NIGHTLY")
ET.SubElement(package1, "nightly_download").text = firefox_nightly_download_url

# Add all relevant dates from the first JSON
ET.SubElement(package1, "last_merge_date").text = get_data_or_na("LAST_MERGE_DATE")
ET.SubElement(package1, "last_release_date").text = get_data_or_na("LAST_RELEASE_DATE")
ET.SubElement(package1, "last_softfreeze_date").text = get_data_or_na("LAST_SOFTFREEZE_DATE")
ET.SubElement(package1, "last_stringfreeze_date").text = get_data_or_na("LAST_STRINGFREEZE_DATE")
ET.SubElement(package1, "next_merge_date").text = get_data_or_na("NEXT_MERGE_DATE")
ET.SubElement(package1, "next_release_date").text = get_data_or_na("NEXT_RELEASE_DATE")
ET.SubElement(package1, "next_softfreeze_date").text = get_data_or_na("NEXT_SOFTFREEZE_DATE")
ET.SubElement(package1, "next_stringfreeze_date").text = get_data_or_na("NEXT_STRINGFREEZE_DATE")

# Convert the tree to a string and pretty-print it
def pretty_print_xml(element, level=0):
    indent = "  "
    if len(element):
        element.text = "\n" + indent * (level + 1)
        for child in element:
            pretty_print_xml(child, level + 1)
        child.tail = "\n" + indent * level
    if level and (not element.tail or not element.tail.strip()):
        element.tail = "\n" + indent * level

pretty_print_xml(root)
xml_data = ET.tostring(root, encoding='utf8', method='xml').decode()

# Create the output directory if it doesn't exist
output_dir = os.path.join(os.getcwd(), 'latest_firefox_files')
os.makedirs(output_dir, exist_ok=True)

# Save the first XML to a local file (overwrite if exists)
with open(os.path.join(output_dir, "firefox_latest_versions.xml"), "w") as f:
    f.write(xml_data)

print("First XML file (firefox_latest_versions.xml) created successfully in latest_firefox_files.")

# Create the root element for the second XML
root_releases = ET.Element("releases")

# Add static information to the second XML
last_updated_releases = ET.SubElement(root_releases, "last_updated")
last_updated_releases.text = datetime.now(eastern).strftime("%B %d, %Y %I:%M %p %Z")

# Add dynamic information from the second JSON
releases_list = []
for release_key, release_info in data_releases["releases"].items():
    releases_list.append({
        "key": release_key,
        "build_number": str(release_info.get("build_number", "N/A")),
        "category": release_info.get("category", "N/A"),
        "date": release_info.get("date", "N/A"),
        "description": release_info.get("description", "N/A"),
        "is_security_driven": str(release_info.get("is_security_driven", "N/A")),
        "product": release_info.get("product", "N/A"),
        "version": release_info.get("version", "N/A")
    })

# Sort releases by date
releases_list.sort(key=lambda x: x["date"])

for release in releases_list:
    release_element = ET.SubElement(root_releases, "release")
    ET.SubElement(release_element, "key").text = release["key"]
    ET.SubElement(release_element, "build_number").text = release["build_number"]
    ET.SubElement(release_element, "category").text = release["category"]
    ET.SubElement(release_element, "date").text = release["date"]
    ET.SubElement(release_element, "description").text = release["description"]
    ET.SubElement(release_element, "is_security_driven").text = release["is_security_driven"]
    ET.SubElement(release_element, "product").text = release["product"]
    ET.SubElement(release_element, "version").text = release["version"]

# Pretty-print the second XML
pretty_print_xml(root_releases)
xml_data_releases = ET.tostring(root_releases, encoding='utf8', method='xml').decode()

# Save the second XML to a local file (overwrite if exists)
with open(os.path.join(output_dir, "firefox_release_history.xml"), "w") as f:
    f.write(xml_data_releases)

print("Second XML file (firefox_release_history.xml) created successfully in latest_firefox_files.")

# Create the root element for the third XML
root_devedition = ET.Element("firefox_devedition_releases")

# Add static information to the third XML
last_updated_devedition = ET.SubElement(root_devedition, "last_updated")
last_updated_devedition.text = datetime.now(eastern).strftime("%B %d, %Y %I:%M %p %Z")

# Add dynamic information from the third JSON
devedition_list = []
for release_key, release_info in data_devedition["releases"].items():
    devedition_list.append({
        "key": release_key,
        "build_number": str(release_info.get("build_number", "N/A")),
        "category": release_info.get("category", "N/A"),
        "date": release_info.get("date", "N/A"),
        "description": release_info.get("description", "N/A"),
        "is_security_driven": str(release_info.get("is_security_driven", "N/A")),
        "product": release_info.get("product", "N/A"),
        "version": release_info.get("version", "N/A")
    })

# Sort devedition releases by date
devedition_list.sort(key=lambda x: x["date"])

for release in devedition_list:
    release_element = ET.SubElement(root_devedition, "release")
    ET.SubElement(release_element, "key").text = release["key"]
    ET.SubElement(release_element, "build_number").text = release["build_number"]
    ET.SubElement(release_element, "category").text = release["category"]
    ET.SubElement(release_element, "date").text = release["date"]
    ET.SubElement(release_element, "description").text = release["description"]
    ET.SubElement(release_element, "is_security_driven").text = release["is_security_driven"]
    ET.SubElement(release_element, "product").text = release["product"]
    ET.SubElement(release_element, "version").text = release["version"]

# Pretty-print the third XML
pretty_print_xml(root_devedition)
xml_data_devedition = ET.tostring(root_devedition, encoding='utf8', method='xml').decode()

# Save the third XML to a local file (overwrite if exists)
with open(os.path.join(output_dir, "firefox_devedition_history.xml"), "w") as f:
    f.write(xml_data_devedition)

print("Third XML file (firefox_devedition_history.xml) created successfully in latest_firefox_files.")

# Create the root element for the combined XML
root_combined_releases = ET.Element("combined_releases")

# Add static information to the combined XML
last_updated_combined_releases = ET.SubElement(root_combined_releases, "last_updated")
last_updated_combined_releases.text = datetime.now(eastern).strftime("%B %d, %Y %I:%M %p %Z")

# Collect all releases from both JSONs
combined_releases = []

# Add dynamic information from the fourth JSON (major releases)
for version, date in data_major_releases.items():
    combined_releases.append({"type": "major", "version": version, "date": date})

# Add dynamic information from the fifth JSON (stability releases)
for version, date in data_stability_releases.items():
    combined_releases.append({"type": "stability", "version": version, "date": date})

# Sort the combined releases by date
combined_releases.sort(key=lambda x: x["date"])

# Add sorted releases to the combined XML
for release in combined_releases:
    release_element = ET.SubElement(root_combined_releases, "release")
    ET.SubElement(release_element, "type").text = release["type"]
    ET.SubElement(release_element, "version").text = release["version"]
    ET.SubElement(release_element, "date").text = release["date"]

# Pretty-print the combined XML
pretty_print_xml(root_combined_releases)
xml_data_combined_releases = ET.tostring(root_combined_releases, encoding='utf8', method='xml').decode()

# Save the combined XML to a local file (overwrite if exists)
with open(os.path.join(output_dir, "firefox_combined_history.xml"), "w") as f:
    f.write(xml_data_combined_releases)

print("Combined XML file (firefox_combined_history.xml) created successfully in latest_firefox_files.")

# Function to convert XML to dictionary
def xml_to_dict(element):
    if len(element) == 0:
        return element.text
    result = {}
    for child in element:
        child_dict = xml_to_dict(child)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(child_dict)
        else:
            result[child.tag] = child_dict
    return result

# Convert XML data to dictionary
data_dict = xml_to_dict(root)
data_releases_dict = xml_to_dict(root_releases)
data_devedition_dict = xml_to_dict(root_devedition)
data_combined_releases_dict = xml_to_dict(root_combined_releases)

# Convert dictionary to JSON
json_data = json.dumps(data_dict, indent=2)
json_data_releases = json.dumps(data_releases_dict, indent=2)
json_data_devedition = json.dumps(data_devedition_dict, indent=2)
json_data_combined_releases = json.dumps(data_combined_releases_dict, indent=2)

# Convert dictionary to YAML
yaml_data = yaml.dump(data_dict, sort_keys=False)
yaml_data_releases = yaml.dump(data_releases_dict, sort_keys=False)
yaml_data_devedition = yaml.dump(data_devedition_dict, sort_keys=False)
yaml_data_combined_releases = yaml.dump(data_combined_releases_dict, sort_keys=False)

# Save JSON and YAML files (overwrite if exists)
with open(os.path.join(output_dir, "firefox_latest_versions.json"), "w") as f:
    f.write(json_data)
with open(os.path.join(output_dir, "firefox_latest_versions.yaml"), "w") as f:
    f.write(yaml_data)

with open(os.path.join(output_dir, "firefox_release_history.json"), "w") as f:
    f.write(json_data_releases)
with open(os.path.join(output_dir, "firefox_release_history.yaml"), "w") as f:
    f.write(yaml_data_releases)

with open(os.path.join(output_dir, "firefox_devedition_history.json"), "w") as f:
    f.write(json_data_devedition)
with open(os.path.join(output_dir, "firefox_devedition_history.yaml"), "w") as f:
    f.write(yaml_data_devedition)

with open(os.path.join(output_dir, "firefox_combined_releases_history.json"), "w") as f:
    f.write(json_data_combined_releases)
with open(os.path.join(output_dir, "firefox_combined_history.yaml"), "w") as f:
    f.write(yaml_data_combined_releases)

print("JSON and YAML files created successfully in latest_firefox_files.")
