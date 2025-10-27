import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re
import subprocess
import os
import json
import yaml
import pytz

# Fetch Firefox release and devedition JSON data
url_releases = "https://product-details.mozilla.org/1.0/firefox.json"
response_releases = requests.get(url_releases)
data_releases = response_releases.json()

url_devedition = "https://product-details.mozilla.org/1.0/devedition.json"
response_devedition = requests.get(url_devedition)
data_devedition = response_devedition.json()

# Helper to get the final download URL for a Firefox product using curl
def fetch_download_url(url):
    try:
        return subprocess.check_output(
            ["curl", url, "-s", "-L", "-I", "-o", "/dev/null", "-w", "%{url_effective}"]
        ).decode("utf-8").strip()
    except subprocess.CalledProcessError:
        return "N/A"

# Get download URLs for all main Firefox channels
firefox_download_url = fetch_download_url("https://download.mozilla.org/?product=firefox-pkg-latest-ssl&os=osx")
firefox_esr_download_url = fetch_download_url("https://download.mozilla.org/?product=firefox-esr-pkg-latest-ssl&os=osx")
firefox_beta_download_url = fetch_download_url("https://download.mozilla.org/?product=firefox-beta-pkg-latest-ssl&os=osx")
firefox_nightly_download_url = fetch_download_url("https://download.mozilla.org/?product=firefox-nightly-pkg-latest-ssl&os=osx")
firefox_devedition_download_url = fetch_download_url("https://download.mozilla.org/?product=firefox-devedition-latest-ssl&os=osx")

# Build the main XML for latest Firefox versions
root = ET.Element("mac_versions")

# Add last_updated timestamp to the XML
eastern = pytz.timezone('US/Eastern')
last_updated = ET.SubElement(root, "last_updated")
last_updated.text = datetime.now(eastern).strftime("%B %d, %Y %I:%M %p %Z")

# Find the newest stable release (major or stability)
stable_release = None
for release_key, release in data_releases["releases"].items():
    if re.match(r'^firefox-\d+(\.\d+)*$', release_key):
        if release.get("category") in ("major", "stability"):
            if stable_release is None or release.get("date", "") > stable_release.get("date", ""):
                stable_release = release

# Add stable release info to XML
stable = ET.SubElement(root, "stable")
if stable_release:
    ET.SubElement(stable, "version").text = stable_release.get("version", "N/A")
    try:
        dt = datetime.strptime(stable_release.get("date", ""), "%Y-%m-%d")
        dt = eastern.localize(dt)
        ET.SubElement(stable, "release_time").text = dt.strftime("%B %d, %Y %I:%M %p %Z")
    except Exception:
        ET.SubElement(stable, "release_time").text = stable_release.get("date", "N/A")
else:
    ET.SubElement(stable, "version").text = "N/A"
    ET.SubElement(stable, "release_time").text = "N/A"
ET.SubElement(stable, "download").text = firefox_download_url

# Find the newest beta release (dev category)
beta_release = None
for release_key, release in data_releases["releases"].items():
    if re.match(r'^firefox-\d+(\.\d+)*b\d+$', release_key):
        if release.get("category") == "dev":
            if beta_release is None or release.get("date", "") > beta_release.get("date", ""):
                beta_release = release

# Add beta release info to XML
beta = ET.SubElement(root, "beta")
if beta_release:
    ET.SubElement(beta, "version").text = beta_release.get("version", "N/A")
    try:
        dt = datetime.strptime(beta_release.get("date", ""), "%Y-%m-%d")
        dt = eastern.localize(dt)
        ET.SubElement(beta, "release_time").text = dt.strftime("%B %d, %Y %I:%M %p %Z")
    except Exception:
        ET.SubElement(beta, "release_time").text = beta_release.get("date", "N/A")
else:
    ET.SubElement(beta, "version").text = "N/A"
    ET.SubElement(beta, "release_time").text = "N/A"
ET.SubElement(beta, "download").text = firefox_beta_download_url

# Find the newest Developer Edition release
dev_release = None
for release in data_devedition["releases"].values():
    if dev_release is None or release.get("date", "") > dev_release.get("date", ""):
        dev_release = release

# Add Developer Edition info to XML
dev = ET.SubElement(root, "dev")
if dev_release:
    ET.SubElement(dev, "version").text = dev_release.get("version", "N/A")
    try:
        dt = datetime.strptime(dev_release.get("date", ""), "%Y-%m-%d")
        dt = eastern.localize(dt)
        ET.SubElement(dev, "release_time").text = dt.strftime("%B %d, %Y %I:%M %p %Z")
    except Exception:
        ET.SubElement(dev, "release_time").text = dev_release.get("date", "N/A")
else:
    ET.SubElement(dev, "version").text = "N/A"
    ET.SubElement(dev, "release_time").text = "N/A"
ET.SubElement(dev, "download").text = firefox_devedition_download_url

# Find the newest ESR release
esr_release = None
for release_key, release in data_releases["releases"].items():
    if release_key.endswith("esr") and release.get("category") == "esr":
        if esr_release is None or release.get("date", "") > esr_release.get("date", ""):
            esr_release = release

# Add ESR info to XML
esr = ET.SubElement(root, "esr")
if esr_release:
    ET.SubElement(esr, "version").text = esr_release.get("version", "N/A")
    try:
        dt = datetime.strptime(esr_release.get("date", ""), "%Y-%m-%d")
        dt = eastern.localize(dt)
        ET.SubElement(esr, "release_time").text = dt.strftime("%B %d, %Y %I:%M %p %Z")
    except Exception:
        ET.SubElement(esr, "release_time").text = esr_release.get("date", "N/A")
else:
    ET.SubElement(esr, "version").text = "N/A"
    ET.SubElement(esr, "release_time").text = "N/A"
ET.SubElement(esr, "download").text = firefox_esr_download_url

# Add Nightly info to XML
url_versions = "https://product-details.mozilla.org/1.0/firefox_versions.json"
response_versions = requests.get(url_versions)
data_versions = response_versions.json()

nightly = ET.SubElement(root, "nightly")
ET.SubElement(nightly, "version").text = data_versions.get("FIREFOX_NIGHTLY", "N/A")
try:
    dt = datetime.strptime(data_versions.get("LAST_MERGE_DATE", ""), "%Y-%m-%d")
    dt = eastern.localize(dt)
    ET.SubElement(nightly, "release_time").text = dt.strftime("%B %d, %Y %I:%M %p %Z")
except Exception:
    ET.SubElement(nightly, "release_time").text = data_versions.get("LAST_MERGE_DATE", "N/A")
ET.SubElement(nightly, "download").text = firefox_nightly_download_url

# Pretty-print XML for readability
def pretty_print_xml(element, level=0):
    indent = "  "
    if len(element):
        element.text = "\n" + indent * (level + 1)
        for child in element:
            pretty_print_xml(child, level + 1)
        child.tail = "\n" + indent * level
    if level and (not element.tail or not element.tail.strip()):
        element.tail = "\n" + indent * level

# Save the main XML, JSON, and YAML for latest versions
pretty_print_xml(root)
xml_data = ET.tostring(root, encoding='utf8', method='xml').decode()

output_dir = os.path.join(os.getcwd(), 'latest_firefox_files')
os.makedirs(output_dir, exist_ok=True)
with open(os.path.join(output_dir, "firefox_latest_versions.xml"), "w") as f:
    f.write(xml_data)
print("firefox_latest_versions.xml created successfully in latest_firefox_files.")

# Convert XML to dict for JSON/YAML export
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

data_dict = xml_to_dict(root)
json_data = json.dumps(data_dict, indent=2)
yaml_data = yaml.dump(data_dict, sort_keys=False)

with open(os.path.join(output_dir, "firefox_latest_versions.json"), "w") as f:
    f.write(json_data)
with open(os.path.join(output_dir, "firefox_latest_versions.yaml"), "w") as f:
    f.write(yaml_data)
print("firefox_latest_versions.json and firefox_latest_versions.yaml created successfully in latest_firefox_files.")

# Helper to get the current last_updated string
def get_last_updated_str():
    eastern = pytz.timezone('US/Eastern')
    return datetime.now(eastern).strftime("%B %d, %Y %I:%M %p %Z")

def make_pkg_links(version, date=None):
    """
    Returns two links for the given version string.
    If date is prior to 2022-01-01, returns the base ftp.mozilla.org URL for both.
    Otherwise, just construct the URLs (do not check with curl for speed).
    """
    safe_version = str(version)
    # If date is provided and prior to 2022-01-01, return base URL for both
    if date:
        try:
            if date < "2022-01-01":
                return [
                    "https://ftp.mozilla.org/pub/firefox/releases/",
                    "https://ftp.mozilla.org/pub/firefox/releases/"
                ]
        except Exception:
            pass
    base_url = f"https://ftp.mozilla.org/pub/firefox/releases/{safe_version}/mac/en-US/"
    pkg_name = f"Firefox%20{safe_version}.pkg"
    dmg_name = f"Firefox%20{safe_version}.dmg"
    # Do not check with curl, just return the constructed URLs
    pkg_url = base_url + pkg_name
    dmg_url = base_url + dmg_name
    return [pkg_url, dmg_url]

# Write all Firefox release history files (all channels, newest first)
def write_firefox_all_history_files():
    url = "https://product-details.mozilla.org/1.0/firefox.json"
    data = requests.get(url).json()
    releases = []
    for key, info in data.get("releases", {}).items():
        entry = dict(key=key)
        entry.update(info)
        # Add links for each release (use 'version' field)
        version = entry.get("version")
        date = entry.get("date")
        if version:
            links = make_pkg_links(version, date)
            entry["download_pkg"] = links[0]
            entry["download_dmg"] = links[1]
        releases.append(entry)
    releases.sort(key=lambda x: x.get("date", ""), reverse=True)
    root = ET.Element("firefox_all_history")
    last_updated = ET.SubElement(root, "last_updated")
    last_updated.text = get_last_updated_str()
    for rel in releases:
        rel_elem = ET.SubElement(root, "release")
        for k, v in rel.items():
            if k not in ("download_pkg", "download_dmg"):
                ET.SubElement(rel_elem, k).text = str(v)
        # Only add one pkg and one dmg link per release
        if rel.get("download_pkg"):
            ET.SubElement(rel_elem, "download_pkg").text = rel["download_pkg"]
        if rel.get("download_dmg"):
            ET.SubElement(rel_elem, "download_dmg").text = rel["download_dmg"]
    pretty_print_xml(root)
    xml_data = ET.tostring(root, encoding='utf8', method='xml').decode()
    json_obj = {"last_updated": get_last_updated_str(), "releases": releases}
    json_data = json.dumps(json_obj, indent=2)
    yaml_data = yaml.dump(json_obj, sort_keys=False)
    with open(os.path.join(output_dir, "firefox_all_history.xml"), "w") as f:
        f.write(xml_data)
    with open(os.path.join(output_dir, "firefox_all_history.json"), "w") as f:
        f.write(json_data)
    with open(os.path.join(output_dir, "firefox_all_history.yaml"), "w") as f:
        f.write(yaml_data)
    print("firefox_all_history.xml, .json, .yaml created successfully in latest_firefox_files.")

# Write Firefox beta/dev history files (newest first)
def write_firefox_beta_dev_history_files():
    url = "https://product-details.mozilla.org/1.0/firefox_history_development_releases.json"
    data = requests.get(url).json()
    releases = []
    for key, info in data.items():
        # info is a date string
        entry = dict(version=key, date=info)
        links = make_pkg_links(key, info)
        entry["download_pkg"] = links[0]
        entry["download_dmg"] = links[1]
        releases.append(entry)
    releases.sort(key=lambda x: x.get("date", ""), reverse=True)
    root = ET.Element("firefox_beta_dev_history")
    last_updated = ET.SubElement(root, "last_updated")
    last_updated.text = get_last_updated_str()
    for rel in releases:
        rel_elem = ET.SubElement(root, "release")
        for k, v in rel.items():
            if k not in ("download_pkg", "download_dmg"):
                ET.SubElement(rel_elem, k).text = str(v)
        # Only add one pkg and one dmg link per release
        ET.SubElement(rel_elem, "download_pkg").text = rel["download_pkg"]
        ET.SubElement(rel_elem, "download_dmg").text = rel["download_dmg"]
    pretty_print_xml(root)
    xml_data = ET.tostring(root, encoding='utf8', method='xml').decode()
    json_obj = {"last_updated": get_last_updated_str(), "releases": releases}
    json_data = json.dumps(json_obj, indent=2)
    yaml_data = yaml.dump(json_obj, sort_keys=False)
    with open(os.path.join(output_dir, "firefox_beta_dev_history.xml"), "w") as f:
        f.write(xml_data)
    with open(os.path.join(output_dir, "firefox_beta_dev_history.json"), "w") as f:
        f.write(json_data)
    with open(os.path.join(output_dir, "firefox_beta_dev_history.yaml"), "w") as f:
        f.write(yaml_data)
    print("firefox_beta_dev_history.xml, .json, .yaml created successfully in latest_firefox_files.")

# Write all Firefox version info files (structure as-is, with last_updated at the top)
def write_firefox_all_version_info_files():
    url = "https://product-details.mozilla.org/1.0/firefox_versions.json"
    data = requests.get(url).json()
    # XML
    def dict_to_xml(parent, d):
        for k, v in d.items():
            if isinstance(v, dict):
                child = ET.SubElement(parent, k)
                dict_to_xml(child, v)
            else:
                ET.SubElement(parent, k).text = str(v)
    root = ET.Element("firefox_all_version_info")
    last_updated = ET.SubElement(root, "last_updated")
    last_updated.text = get_last_updated_str()
    dict_to_xml(root, data)
    pretty_print_xml(root)
    xml_data = ET.tostring(root, encoding='utf8', method='xml').decode()
    # JSON/YAML with last_updated at the top
    json_obj = {"last_updated": get_last_updated_str()}
    json_obj.update(data)
    json_data = json.dumps(json_obj, indent=2)
    yaml_data = yaml.dump(json_obj, sort_keys=False)
    # Write files
    with open(os.path.join(output_dir, "firefox_all_version_info.xml"), "w") as f:
        f.write(xml_data)
    with open(os.path.join(output_dir, "firefox_all_version_info.json"), "w") as f:
        f.write(json_data)
    with open(os.path.join(output_dir, "firefox_all_version_info.yaml"), "w") as f:
        f.write(yaml_data)
    print("firefox_all_version_info.xml, .json, .yaml created successfully in latest_firefox_files.")

# Run all history/version info writers
write_firefox_all_history_files()
write_firefox_beta_dev_history_files()
write_firefox_all_version_info_files()
