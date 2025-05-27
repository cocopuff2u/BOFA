import xml.etree.ElementTree as ET
import os
from datetime import datetime
from pytz import timezone

def read_xml_value(file_path, xpath):
    """Generic function to read any value from XML using xpath"""
    if not os.path.exists(file_path):
        return "N/A"
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # For Edge specific handling
        if 'edge' in file_path.lower():
            # Updated channel map to match new XML format
            channel_map = {
                'stable': 'current',
                'dev': 'dev',
                'beta': 'beta',
                'canary': 'canary'
            }
            base_channel = xpath.split('/')[0]
            xml_channel = channel_map.get(base_channel)
            if xml_channel:
                version_element = root.find(f".//Version[Channel='{xml_channel}']")
                if version_element is not None:
                    return version_element.find('Location' if 'download' in xpath else 'Version').text
            return "N/A"
            
        # For Firefox, look inside package element
        elif 'firefox' in file_path.lower():
            element = root.find(f'.//package/{xpath}')
        else:
            element = root.find(xpath)
            
        return element.text if element is not None else "N/A"
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return f"Error: {str(e)}"

def read_xml_version(file_path):
    if not os.path.exists(file_path):
        return "N/A"
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # For Edge, get the first version
        if 'edge' in file_path.lower():
            version_element = root.find('.//Version[Channel="current"]/Version')
            return version_element.text if version_element is not None else "N/A"
        
        # For Firefox, get the first version
        elif 'firefox' in file_path.lower():
            version_element = root.find('.//latest_version')
            return version_element.text if version_element is not None else "N/A"
        
        # For Chrome, get the first version
        elif 'chrome' in file_path.lower():
            version_element = root.find('.//version')
            return version_element.text if version_element is not None else "N/A"
        
        # For Safari, get the version from Sonoma (latest macOS)
        elif 'safari' in file_path.lower():
            try:
                sonoma_version = root.find('./Sonoma/version')
                if sonoma_version is not None and sonoma_version.text:
                    return sonoma_version.text
                print(f"Warning: Could not find Safari version in {file_path}")
                return "N/A"
            except Exception as e:
                print(f"Error reading Safari version: {str(e)}")
                return "N/A"
        
        return "N/A"
    except Exception as e:
        print(f"Error reading version from {file_path}: {str(e)}")
        return f"Error: {str(e)}"

def get_browser_lines(file_path):
    """Get all version lines for a browser"""
    if not os.path.exists(file_path):
        return []
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        lines = []
        
        # Different number of lines for each browser
        max_lines = {
            'safari': 4,
            'firefox': 6,
            'edge': 6,
            'chrome': 4
        }
        
        browser_type = next((b for b in max_lines.keys() if b in file_path), None)
        if (browser_type):
            for i in range(1, max_lines[browser_type] + 1):
                line = root.find(f'.//line{i}/version')
                lines.append(line.text if line is not None else "N/A")
        
        return lines
    except Exception as e:
        return [f"Error: {str(e)}"]

def get_safari_detail(xml_path, os_version, detail_type):
    """Get Safari version/URL details by OS version"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        element = root.find(f'.//{os_version}/{detail_type}')
        return element.text if element is not None else "N/A"
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_chrome_details(xml_path, version_path, download_path):
    version = read_xml_value(xml_path, version_path)
    download = read_xml_value(xml_path, download_path)
    return version, download

def fetch_firefox_details(xml_path, version_path, download_path):
    version = read_xml_value(xml_path, version_path)
    download = read_xml_value(xml_path, download_path)
    return version, download

def fetch_edge_details(xml_path, version_path, download_path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # Use new channel mapping
        channel_map = {
            'stable': 'current',
            'dev': 'dev',
            'beta': 'beta',
            'canary': 'canary'
        }
        channel = channel_map.get(version_path, version_path)
        version_element = root.find(f".//Version[Channel='{channel}']")
        if version_element is not None:
            version = version_element.find('Version').text
            download = version_element.find('Location').text
            return version, download
        return "N/A", "N/A"
    except Exception as e:
        return f"Error: {str(e)}", f"Error: {str(e)}"

def fetch_safari_details(xml_path, os_version, detail_type):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        version = root.find(f'.//{os_version}/version').text
        download = root.find(f'.//{os_version}/URL').text
        return version, download
    except Exception as e:
        return f"Error: {str(e)}", f"Error: {str(e)}"

BROWSER_CONFIGS = {
    'Chrome': {
        'fetch_details': fetch_chrome_details,
        'channels': [
            {'name': '', 'display': 'Chrome', 'version_path': 'stable/version', 'download_path': 'stable/latest_download', 'bundle_id': 'com.google.Chrome', 'image': 'chrome.png', 'release_notes': 'https://chromereleases.googleblog.com/'},
            {'name': 'Beta', 'display': 'Chrome', 'version_path': 'beta/version', 'download_path': 'beta/beta_download', 'bundle_id': 'com.google.Chrome.beta', 'image': 'chrome_beta.png', 'release_notes': 'https://chromereleases.googleblog.com/search/label/Beta%20updates'},
            {'name': 'Dev', 'display': 'Chrome', 'version_path': 'dev/version', 'download_path': 'dev/dev_download', 'bundle_id': 'com.google.Chrome.dev', 'image': 'chrome_dev.png', 'release_notes': 'https://chromereleases.googleblog.com/search/label/Dev%20updates'},
            {'name': 'Canary', 'display': 'Chrome', 'version_path': 'canary/version', 'download_path': 'canary/canary_download', 'bundle_id': 'com.google.Chrome.canary', 'image': 'chrome_canary.png'}
        ]
    },
    'Firefox': {
        'fetch_details': fetch_firefox_details,
        'channels': [
            {'name': '', 'display': 'Firefox', 'version_path': 'latest_version', 'download_path': 'latest_download', 'bundle_id': 'org.mozilla.firefox', 'image': 'firefox.png', 'release_notes': 'https://www.mozilla.org/en-US/firefox/notes/'},
            {'name': 'Beta', 'display': 'Firefox', 'version_path': 'latest_devel_version', 'download_path': 'latest_beta_download', 'bundle_id': 'org.mozilla.firefoxbeta', 'image': 'firefox.png', 'release_notes': 'https://www.mozilla.org/en-US/firefox/beta/notes/'},
            {'name': 'Developer', 'display': 'Firefox', 'version_path': 'devedition_version', 'download_path': 'devedition_download', 'bundle_id': 'org.mozilla.firefoxdev', 'image': 'firefox_developer.png', 'release_notes': 'https://www.mozilla.org/en-US/firefox/developer/notes/'},
            {'name': 'ESR', 'display': 'Firefox', 'version_path': 'esr_version', 'download_path': 'esr_download', 'bundle_id': 'org.mozilla.firefoxesr', 'image': 'firefox.png','release_notes': 'https://www.mozilla.org/en-US/firefox/organizations/notes/'},
            {'name': 'ESR 115', 'display': 'Firefox', 'version_path': 'esr115_version', 'download_path': 'esr115_download', 'bundle_id': 'org.mozilla.firefoxesr', 'image': 'firefox.png'},
            {'name': 'Nightly', 'display': 'Firefox', 'version_path': 'nightly_version', 'download_path': 'nightly_download', 'bundle_id': 'org.mozilla.nightly', 'image': 'firefox_nightly.png', 'release_notes': 'https://www.mozilla.org/en-US/firefox/nightly/notes/'}
        ]
    },
    'Edge': {
        'fetch_details': fetch_edge_details,
        'channels': [
            {'name': '', 'display': 'Edge', 'version_path': 'stable', 'download_path': 'stable', 'bundle_id': 'com.microsoft.edgemac', 'image': 'edge.png', 'release_notes': 'https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-stable-channel'},
            {'name': 'Beta', 'display': 'Edge', 'version_path': 'beta', 'download_path': 'beta', 'bundle_id': 'com.microsoft.edgemac.beta', 'image': 'edge_beta.png', 'release_notes': 'https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-beta-channel'},
            {'name': 'Developer', 'display': 'Edge', 'version_path': 'dev', 'download_path': 'dev', 'bundle_id': 'com.microsoft.edgemac.dev', 'image': 'edge_dev.png'},
            {'name': 'Canary', 'display': 'Edge', 'version_path': 'canary', 'download_path': 'canary', 'bundle_id': 'com.microsoft.edgemac.canary', 'image': 'edge_canary.png'}
        ]
    },
    'Safari': {
        'fetch_details': fetch_safari_details,
        'channels': [
            {'name': 'Sequoia/Sonoma', 'display': 'Safari', 'version_path': 'Sonoma', 'download_path': 'Sonoma', 'bundle_id': 'com.apple.Safari', 'image': 'safari.png', 'release_notes': 'https://developer.apple.com/documentation/safari-release-notes'},
            {'name': 'Ventura', 'display': 'Safari', 'version_path': 'Ventura', 'download_path': 'Ventura', 'bundle_id': 'com.apple.Safari', 'image': 'safari.png'},
            {'name': 'Monterey', 'display': 'Safari', 'version_path': 'Monterey', 'download_path': 'Monterey', 'bundle_id': 'com.apple.Safari', 'image': 'safari.png'},
            {'name': 'BigSur', 'display': 'Safari', 'version_path': 'BigSur', 'download_path': 'BigSur', 'bundle_id': 'com.apple.Safari', 'image': 'safari.png'}
        ]
    }
}

def get_last_updated_from_xml(xml_path, browser, channel=None):
    """Extract last updated date for the main stable channel/version for each browser, formatted as 'Month day, Year'."""
    if not os.path.exists(xml_path):
        return "N/A"
    def format_date(date_str):
        # Try to parse common formats and return 'Month day, Year'
        for fmt in [
            "%B %d, %Y %I:%M %p %Z",  # e.g., May 27, 2025 10:02 AM EDT
            "%B %d, %Y %I:%M %p",     # e.g., May 27, 2025 10:02 AM
            "%B %d, %Y",              # e.g., May 27, 2025
            "%Y-%m-%d",               # e.g., 2025-05-27
            "%Y-%m-%d %H:%M",         # e.g., 2025-05-27 10:02
        ]:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime("%B %d, %Y")
            except Exception:
                continue
        return date_str  # fallback: return as-is

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        if browser == 'Chrome':
            elem = root.find(f'.//{channel}/release_time')
            if elem is not None and elem.text:
                return format_date(elem.text)
        elif browser == 'Firefox':
            elem = root.find('.//package/currentVersionReleaseDate')
            if elem is not None and elem.text:
                return format_date(elem.text)
        elif browser == 'Edge':
            for version in root.findall('.//Version'):
                channel_elem = version.find('Channel')
                if channel_elem is not None and channel_elem.text == 'current':
                    date_elem = version.find('Date')
                    if date_elem is not None and date_elem.text:
                        return format_date(date_elem.text)
        elif browser == 'Safari':
            elem = root.find(f'.//{channel}/PostDate')
            if elem is not None and elem.text:
                return format_date(elem.text)
        elem = root.find('.//last_updated')
        if elem is not None and elem.text:
            return format_date(elem.text)
        mtime = os.path.getmtime(xml_path)
        return datetime.fromtimestamp(mtime).strftime("%B %d, %Y")
    except Exception as e:
        return "N/A"

def generate_browser_table(base_path):
    table_content = """| **Browser** | **CFBundle Version** | **CFBundle Identifier** | **Download** |
|------------|-------------------|---------------------|------------|
"""
    for browser, config in BROWSER_CONFIGS.items():
        xml_path = os.path.join(base_path, f'latest_{browser.lower()}_files/{browser.lower()}_latest_versions.xml')
        for channel in config['channels']:
            # Fetch version and download as before
            if browser == 'Safari':
                version, download = config['fetch_details'](xml_path, channel['version_path'], 'URL')
                # Only show release date for "Sequoia/Sonoma" (current)
                show_release = channel['version_path'] == 'Sonoma'
                last_updated = get_last_updated_from_xml(xml_path, browser, channel['version_path']) if show_release else None
            elif browser == 'Chrome':
                version, download = config['fetch_details'](xml_path, channel['version_path'], channel['download_path'])
                # Only show release date for "stable"
                show_release = channel['version_path'].split('/')[0] == 'stable'
                last_updated = get_last_updated_from_xml(xml_path, browser, channel['version_path'].split('/')[0]) if show_release else None
            elif browser == 'Edge':
                version, download = config['fetch_details'](xml_path, channel['version_path'], channel['download_path'])
                # Only show release date for "stable"
                show_release = channel['version_path'] == 'stable'
                last_updated = get_last_updated_from_xml(xml_path, browser) if show_release else None
            elif browser == 'Firefox':
                version, download = config['fetch_details'](xml_path, channel['version_path'], channel['download_path'])
                # Only show release date for "latest_version"
                show_release = channel['version_path'] == 'latest_version'
                last_updated = get_last_updated_from_xml(xml_path, browser) if show_release else None
            else:
                version, download = "N/A", "N/A"
                last_updated = None
                show_release = False

            channel_name = f"<sup>{channel['name']}</sup>" if channel['name'] else ""
            release_notes = f"<br><a href=\"{channel.get('release_notes', config.get('release_notes', '#'))}\" style=\"text-decoration: none;\"><small>_Release Notes_</small></a>" if 'release_notes' in channel or 'release_notes' in config else ""
            # Add Last Updated below Release Notes only for current/stable
            last_updated_html = f"<br><br><b>Last Updated:<br>{last_updated}</b>" if show_release and last_updated else ""
            table_content += (
                f"| **{channel['display']}** {channel_name} {release_notes}{last_updated_html} | "
                f"`{version}` | "
                f"`{channel['bundle_id']}` | "
                f"<a href=\"{download}\"><img src=\".github/images/{channel['image']}\" "
                f"alt=\"Download {channel['display']}\" width=\"80\"></a> |\n"
            )
    return table_content

def generate_settings_section():
    return """
## Browser Settings Management

View your current browser policies and explore available policy options:

### <img src=".github/images/chrome.png" alt="Chrome" width="20"> Chrome
1. **View Current Policies**: Enter `chrome://policy` in your address bar to see active policies
2. **Available Options**: [Chrome Enterprise Policy Documentation](https://chromeenterprise.google/policies/)

### <img src=".github/images/firefox.png" alt="Firefox" width="20"> Firefox
1. **View Current Policies**: Enter `about:policies` in your address bar to see active policies
2. **Available Options**: [Firefox Policy Documentation](https://mozilla.github.io/policy-templates/)

### <img src=".github/images/edge.png" alt="Edge" width="20"> Edge
1. **View Current Policies**: Enter `edge://policy` in your address bar to see active policies
2. **Available Options**: [Edge Policy Documentation](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-policies)

### <img src=".github/images/safari.png" alt="Safari" width="20"> Safari
1. **View Current Policies**: Open System Settings > Profiles & Device Management
2. **Available Options**: [Safari Configuration Profile Reference](https://support.apple.com/guide/deployment/welcome/web)

"""

def generate_readme():
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    xml_files = {
        'Chrome': os.path.join(base_path, 'latest_chrome_files/chrome_latest_versions.xml'),
        'Firefox': os.path.join(base_path, 'latest_firefox_files/firefox_latest_versions.xml'),
        'Edge': os.path.join(base_path, 'latest_edge_files/edge_latest_versions.xml'),
        'Safari': os.path.join(base_path, 'latest_safari_files/safari_latest_versions.xml')
    }
    eastern = timezone('US/Eastern')
    current_time = datetime.now(eastern).strftime("%B %d, %Y %I:%M %p %Z")
    global_last_updated = current_time

    # Fetch versions and download URLs with new Edge mapping
    chrome_version, chrome_download = fetch_chrome_details(xml_files['Chrome'], 'stable/version', 'stable/latest_download')
    firefox_version, firefox_download = fetch_firefox_details(xml_files['Firefox'], 'latest_version', 'latest_download')
    edge_version, edge_download = fetch_edge_details(xml_files['Edge'], 'stable', 'stable')
    safari_version, safari_download = fetch_safari_details(xml_files['Safari'], 'Sonoma', 'URL')

    # Fetch last updated dates from XMLs (browser-specific, channel-specific)
    chrome_last_updated = get_last_updated_from_xml(xml_files['Chrome'], 'Chrome', 'stable')
    firefox_last_updated = get_last_updated_from_xml(xml_files['Firefox'], 'Firefox')
    edge_last_updated = get_last_updated_from_xml(xml_files['Edge'], 'Edge')
    safari_last_updated = get_last_updated_from_xml(xml_files['Safari'], 'Safari', 'Sonoma')

    readme_content = f"""# **BOFA**
**B**rowser **O**verview **F**eed for **A**pple

<a href="https://bofa.cocolabs.dev"><img src=".github/images/bofa_logo.png" alt="MOFA Image" width="200"></a>

Welcome to the **BOFA** repository! This resource tracks the latest versions of major web browsers for macOS. Feeds are automatically updated every hour from XML and JSON links directly from vendors.

We welcome community contributions—fork the repository, ask questions, or share insights to help keep this resource accurate and useful for everyone. Check out the user-friendly website version below for an easier browsing experience!

<div align="center">

### [bofa.cocolabs.dev](https://bofa.cocolabs.dev)

## Latest Stable Browser Versions

<table>
  <tr>
    <td align="center"><a href="{chrome_download}"><img src=".github/images/chrome.png" alt="Chrome" width="80"></a><br><b>Chrome</b><br>{chrome_version}<br><br><small>Last Update:<br>{chrome_last_updated}</small><br><a href="https://chromereleases.googleblog.com/" style="text-decoration: none;"><small>Release Notes</small></a></td>
    <td align="center"><a href="{firefox_download}"><img src=".github/images/firefox.png" alt="Firefox" width="80"></a><br><b>Firefox</b><br>{firefox_version}<br><br><small>Last Update:<br>{firefox_last_updated}</small><br><a href="https://www.mozilla.org/en-US/firefox/notes/" style="text-decoration: none;"><small>Release Notes</small></a></td>
    <td align="center"><a href="{edge_download}"><img src=".github/images/edge.png" alt="Edge" width="80"></a><br><b>Edge</b><br>{edge_version}<br><br><small>Last Update:<br>{edge_last_updated}</small><br><a href="https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-stable-channel" style="text-decoration: none;"><small>Release Notes</small></a></td>
    <td align="center"><a href="{safari_download}"><img src=".github/images/safari.png" alt="Safari" width="80"></a><br><b>Safari</b><br>{safari_version}<br><br><small>Last Update:<br>{safari_last_updated}</small><br><a href="https://developer.apple.com/documentation/safari-release-notes" style="text-decoration: none;"><small>Release Notes</small></a></td>
  </tr>
</table>

</div>
"""

    readme_content += f"""
## Browser Packages

<sup>All links below direct to the official browser vendor. The links provided will always download the latest available version as of the last scan update.</sup>  

<sup>**Chrome**: [**_Raw XML_**](latest_chrome_files/chrome_latest_versions.xml) [**_Raw YAML_**](latest_chrome_files/chrome_latest_versions.yaml) [**_Raw JSON_**](latest_chrome_files/chrome_latest_versions.json) | **Firefox**: [**_Raw XML_**](latest_firefox_files/firefox_latest_versions.xml) [**_Raw YAML_**](latest_firefox_files/firefox_latest_versions.yaml) [**_Raw JSON_**](latest_firefox_files/firefox_latest_versions.json)</sup>

<sup>**Edge**: [**_Raw XML_**](latest_edge_files/edge_latest_versions.xml) [**_Raw YAML_**](latest_edge_files/edge_latest_versions.yaml) [**_Raw JSON_**](latest_edge_files/edge_latest_versions.json) | **Safari**: [**_Raw XML_**](latest_safari_files/safari_latest_versions.xml) [**_Raw YAML_**](latest_safari_files/safari_latest_versions.yaml) [**_Raw JSON_**](latest_safari_files/safari_latest_versions.json)</sup>

<sup>_Last Updated: <code style="color : mediumseagreen">{global_last_updated}</code> (Automatically Updated every hour)_</sup>

"""

    readme_content += generate_browser_table(base_path)
    readme_content += generate_settings_section()

    readme_path = os.path.join(base_path, 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

if __name__ == "__main__":
    generate_readme()
