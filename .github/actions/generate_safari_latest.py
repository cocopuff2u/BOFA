import requests
import gzip
import plistlib
from datetime import datetime
import pytz
import io
from bs4 import BeautifulSoup
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
import yaml
from collections import defaultdict

def get_session():
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }
    session.headers.update(headers)
    return session

def extract_version_from_url(url):
    # Extract version from URL (e.g., Safari16.6.1BigSurAuto.pkg -> 16.6.1)
    try:
        filename = url.split('/')[-1]
        version = filename.replace('Safari', '').split('Auto')[0]
        version = ''.join(c for c in version if c.isdigit() or c == '.')
        return version
    except:
        return "Unknown"

def extract_os_from_url(url):
    # Extract OS name from URL (e.g., Safari18.3VenturaAuto.pkg -> Ventura)
    try:
        filename = url.split('/')[-1]
        version_and_os = filename.replace('Safari', '').split('Auto')[0]
        # Remove any digits and dots from the start
        os_name = ''.join(c for c in version_and_os if not (c.isdigit() or c == '.'))
        return os_name
    except:
        return "Unknown"

def bytes_to_mb(bytes_size):
    return f"{bytes_size / (1024 * 1024):.2f} MB"

def get_latest_safari_version(catalog_url):
    try:
        session = get_session()
        response = session.get(catalog_url)
        response.raise_for_status()
        
        # Check if the content is gzipped
        if response.headers.get('Content-Encoding') == 'gzip':
            plist_content = gzip.decompress(response.content)
        else:
            plist_content = response.content
        
        catalog = plistlib.loads(plist_content)
        
        # Create root XML element
        root = ET.Element('safari_versions')
        
        # Add last_updated element
        last_updated = ET.SubElement(root, 'last_updated')
        eastern = pytz.timezone('US/Eastern')
        current_time = datetime.now(eastern).strftime('%B %d, %Y %I:%M %p %Z')
        last_updated.text = current_time
        
        for product_id, product_info in catalog['Products'].items():
            if 'ExtendedMetaInfo' in product_info:
                meta_info = product_info['ExtendedMetaInfo']
                if meta_info.get('ProductType') == 'Safari':
                    if 'Packages' in product_info:
                        for package in product_info['Packages']:
                            if 'URL' in package and 'Size' in package:
                                os_name = extract_os_from_url(package['URL'])
                                if not os_name or os_name == "Unknown":
                                    continue
                                
                                packages = ET.SubElement(root, os_name)
                                
                                # Extract and add version
                                version = ET.SubElement(packages, 'version')
                                version.text = extract_version_from_url(package['URL'])
                                
                                # Add URL
                                url_elem = ET.SubElement(packages, 'URL')
                                url_elem.text = package['URL']
                                
                                # Convert and add Size
                                size_elem = ET.SubElement(packages, 'Size')
                                size_elem.text = bytes_to_mb(package['Size'])
                                
                                # Format and add PostDate
                                if 'PostDate' in product_info:
                                    post_date = ET.SubElement(packages, 'PostDate')
                                    post_date.text = product_info['PostDate'].strftime('%B %d, %Y %I:%M %p')
        
        # Convert to pretty XML string
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        return xml_str
    
    except Exception as e:
        print(f"Error: {e}")
        return None

def scrape_safari_versions(url):
    try:
        session = get_session()
        response = session.get(url)
        response.raise_for_status()
        
        # Try to get any potential JSON data first
        if 'application/json' in response.headers.get('Content-Type', ''):
            data = response.json()
            # Process JSON data if available
            return data
            
        soup = BeautifulSoup(response.text, 'html.parser')
        versions = []
        for release in soup.find_all('div', class_='article-content'):
            try:
                date = release.find('time').text.strip()
                version = release.find('h2').text.strip()
                notes = release.find('div', class_='content').text.strip()
                versions.append({
                    'date': date,
                    'version': version,
                    'notes': notes
                })
            except AttributeError:
                continue
        return versions
    except Exception as e:
        print(f"Error: {e}")
        return []

def scrape_entire_site(url):
    try:
        session = get_session()
        response = session.get(url)
        response.raise_for_status()
        
        # Try to detect if we got a JavaScript redirect
        if 'javascript' in response.text.lower():
            print("Warning: Page requires JavaScript execution")
            
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text()
    except Exception as e:
        print(f"Error: {e}")
        return ""

def export_to_text(content, filepath):
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(content)

def xml_to_json(xml_str):
    try:
        root = ET.fromstring(xml_str)
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
        return json.dumps(etree_to_dict(root), indent=4)
    except Exception as e:
        print(f"Error converting XML to JSON: {e}")
        return None

def xml_to_yaml(xml_str):
    try:
        root = ET.fromstring(xml_str)
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
        
        # Ensure last_updated is at the top
        safari_versions = data_dict.get('safari_versions', {})
        if 'last_updated' in safari_versions:
            last_updated = safari_versions.pop('last_updated')
            safari_versions = {'last_updated': last_updated, **safari_versions}
            data_dict['safari_versions'] = safari_versions
        
        return yaml.dump(data_dict, default_flow_style=False, sort_keys=False)
    except Exception as e:
        print(f"Error converting XML to YAML: {e}")
        return None

def export_to_file(content, filepath):
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(content)

# Example usage
catalog_url = 'https://swscan.apple.com/content/catalogs/others/index-15-14-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog.gz'
safari_xml = get_latest_safari_version(catalog_url)

if safari_xml:
    export_to_file(safari_xml, 'latest_safari_files/safari_latest_versions.xml')
    safari_json = xml_to_json(safari_xml)
    if safari_json:
        export_to_file(safari_json, 'latest_safari_files/safari_latest_versions.json')
    safari_yaml = xml_to_yaml(safari_xml)
    if safari_yaml:
        export_to_file(safari_yaml, 'latest_safari_files/safari_latest_versions.yaml')
