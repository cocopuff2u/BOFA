import xml.etree.ElementTree as ET
import os
from datetime import datetime
from pytz import timezone

def parse_xml_file(file_path):
    """Parse XML file robustly, handling encoding and BOM issues."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    try:
        # Try normal parse first
        return ET.parse(file_path)
    except ET.ParseError:
        # Try reading as utf-8-sig to remove BOM if present
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        return ET.ElementTree(ET.fromstring(content))

def read_xml_value(file_path, xpath):
    """Generic function to read any value from XML using xpath"""
    if not os.path.exists(file_path):
        return "N/A"
    try:
        tree = parse_xml_file(file_path)
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
        tree = parse_xml_file(file_path)
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
        tree = parse_xml_file(file_path)
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
        tree = parse_xml_file(xml_path)
        root = tree.getroot()
        element = root.find(f'.//{os_version}/{detail_type}')
        return element.text if element is not None else "N/A"
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_chrome_details(xml_path, version_path, download_path):
    # Adjust to use 'download_link' instead of 'latest_download'
    version = read_xml_value(xml_path, version_path)
    # Map download_path to the new tag
    # download_path is like 'stable/latest_download' or 'beta/beta_download'
    # We want to use the same parent as version_path, but always 'download_link'
    parent = version_path.split('/')[0]
    download = read_xml_value(xml_path, f"{parent}/download_link")
    return version, download

def fetch_firefox_details(xml_path, version_path, download_path):
    # version_path and download_path are now the channel names: 'stable', 'beta', 'dev', 'esr', 'nightly'
    if not os.path.exists(xml_path):
        return "N/A", "N/A"
    try:
        tree = parse_xml_file(xml_path)
        root = tree.getroot()
        channel_elem = root.find(f'.//{version_path}')
        if channel_elem is not None:
            version_elem = channel_elem.find('version')
            download_elem = channel_elem.find('download')
            version = version_elem.text if version_elem is not None else "N/A"
            download = download_elem.text if download_elem is not None else "N/A"
            return version, download
        return "N/A", "N/A"
    except Exception as e:
        return f"Error: {str(e)}", f"Error: {str(e)}"

def fetch_edge_details(xml_path, version_path, download_path):
    try:
        tree = parse_xml_file(xml_path)
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
        tree = parse_xml_file(xml_path)
        root = tree.getroot()
        version = root.find(f'.//{os_version}/version').text
        download = root.find(f'.//{os_version}/URL').text
        return version, download
    except Exception as e:
        return f"Error: {str(e)}", f"Error: {str(e)}"

# --- NEW functions for Safari (releases + tech previews) ---
def fetch_safari_release(xml_path, *args, **kwargs):
    """Return the latest <release> entry's full_version and a link (release_notes or fallback)."""
    if not os.path.exists(xml_path):
        return "N/A", "#"
    try:
        tree = parse_xml_file(xml_path)
        root = tree.getroot()
        release = root.find('release')  # first release is the latest in the file format
        if release is None:
            return "N/A", "#"
        # prefer explicit checks to avoid DeprecationWarning for element truth testing
        full_elem = release.find('full_version')
        major_elem = release.find('major_version')
        version = (
            full_elem.text if (full_elem is not None and full_elem.text)
            else (major_elem.text if (major_elem is not None and major_elem.text) else "N/A")
        )
        notes_elem = release.find('release_notes')
        notes = notes_elem.text if (notes_elem is not None and notes_elem.text) else "#"
        # If notes is a doc:// link, keep it; otherwise use it as-is.
        return version, notes
    except Exception as e:
        return f"Error: {str(e)}", "#"

def fetch_safari_tech_previews(xml_path):
    """Return a list of tech preview dicts: [{'macos','version','PostDate','URL','ReleaseNotes'}, ...]"""
    previews = []
    if not os.path.exists(xml_path):
        return previews
    try:
        tree = parse_xml_file(xml_path)
        root = tree.getroot()
        for tp in root.findall('Safari_Technology_Preview'):
            previews.append({
                'macos': tp.findtext('macos', default='N/A'),
                'version': tp.findtext('version', default='N/A'),
                'post_date': tp.findtext('PostDate', default='N/A'),
                'url': tp.findtext('URL', default='#'),
                'release_notes': tp.findtext('ReleaseNotes', default='#')
            })
    except Exception:
        pass
    return previews

def generate_safari_tech_table(base_path, xml_path):
    """Generate a markdown table for Safari Technology Previews that matches other browser rows."""
    previews = fetch_safari_tech_previews(xml_path)
    if not previews:
        return ""

    table = "| **Browser** | **Version** | **CFBundle Identifier** | **Download** |\n"
    table += "|------------|-------------------|---------------------|------------|\n"
    for p in previews:
        display = f"Safari Technology Preview <sup>({p['macos']})</sup>"
        version = p['version']
        bundle_id = "com.apple.SafariTechnologyPreview"
        # Use a technology-specific image if available
        image = "safari_technology.png"
        download = p['url'] if p['url'] and p['url'] != 'N/A' else p['release_notes']
        last_updated_html = f"<br><br><b>Post Date:</b><br><em><code>{p['post_date']}</code></em>"
        # center the image/link inside the table cell
        image_html = f'<div align="center"><a href="{download}"><img src=".github/images/{image}" alt="Download {display}" width="80"></a></div>'
        table += (
            f"| **{display}** {last_updated_html} | "
            f"`{version}` | "
            f"`{bundle_id}` | "
            f"{image_html} |\n"
        )
    table += "\n"
    return table

# --- NEW: fetch_all_safari_releases + generator (table matches other browsers) ---
def fetch_all_safari_releases(xml_path):
    """Return list of all <release> dicts from the Safari XML (preserves file order)."""
    releases = []
    if not os.path.exists(xml_path):
        return releases
    try:
        tree = parse_xml_file(xml_path)
        root = tree.getroot()
        for rel in root.findall('release'):
            releases.append({
                'major_version': rel.findtext('major_version', default='N/A'),
                'full_version': rel.findtext('full_version', default='N/A'),
                'released': rel.findtext('released', default='N/A'),
                # Prefer an explicit release_notes_url child when present; otherwise use release_notes text
                'release_notes': rel.findtext('release_notes', default='#'),
                'release_notes_url': rel.findtext('release_notes_url', default=None)
            })
    except Exception:
        pass
    return releases

def generate_safari_releases_table(base_path, xml_path):
    """Render a dedicated markdown table listing all Safari <release> entries using the same layout as other browsers."""
    releases = fetch_all_safari_releases(xml_path)
    if not releases:
        return ""
    # header + separator so Markdown renders this as a proper table
    table = "| **Browser** | **Version** | **CFBundle Identifier** | **Release Notes** |\n"
    table += "|------------|-------------------|---------------------|------------|\n"
    for r in releases:
        full_version = r['full_version']
        # If version contains 'beta', mark as beta (but do NOT make the beta label bold)
        is_beta = 'beta' in (full_version or "").lower()
        display_base = "Safari"
        # non-bold for beta: show as plain text with a superscript; stable stays bold
        if is_beta:
            display_cell = f"{display_base} <sup>Beta</sup>"
        else:
            display_cell = f"**{display_base}**"
        version = full_version
        bundle_id = "com.apple.Safari" if is_beta else "com.apple.Safari"
        # Use the same Safari logo for both stable and beta
        image = "safari.png"

        # Prefer explicit URL node, otherwise fall back to release_notes text
        notes_url = r.get('release_notes_url') or r.get('release_notes') or '#'
        # Normalize relative developer links to a full URL
        if isinstance(notes_url, str) and notes_url and not notes_url.startswith('http'):
            if notes_url.startswith('/'):
                notes_url = 'https://developer.apple.com' + notes_url
            else:
                if notes_url.startswith('doc://') or notes_url == '#':
                    notes_url = '#'

        # Render a Safari-logo icon linking to the release notes (fallback to text if no URL)
        if notes_url and notes_url != '#':
            # center the image/link inside the table cell
            note_link_html = f'<div align="center"><a href="{notes_url}"><img src=".github/images/{image}" alt="Safari Release Notes" width="80"></a>'
        else:
            note_link_html = '<small>N/A</small>'

        last_updated_html = f"<br><br><b>Released:</b><br><em><code>{r['released']}</code></em>"
        table += (
            f"| {display_cell} {last_updated_html} | "
            f"`{version}` | "
            f"`{bundle_id}` | "
            f"{note_link_html} |\n"
        )
    table += "\n"
    return table
# --- END NEW functions ---

BROWSER_CONFIGS = {
    'Chrome': {
        'fetch_details': fetch_chrome_details,
        'channels': [
            {'name': '', 'display': 'Chrome', 'version_path': 'stable/version', 'download_path': 'stable/download_link', 'bundle_id': 'com.google.Chrome', 'image': 'chrome.png', 'release_notes': 'https://chromereleases.googleblog.com/'},
            {'name': 'Extended Stable', 'display': 'Chrome', 'version_path': 'extended/version', 'download_path': 'extended/download_link', 'bundle_id': 'com.google.Chrome', 'image': 'chrome.png', 'release_notes_comment': '<br>_<sup>Requires `TargetChannel` policy; link is for Stable.</sup>_'},
            {'name': 'Beta', 'display': 'Chrome', 'version_path': 'beta/version', 'download_path': 'beta/download_link', 'bundle_id': 'com.google.Chrome.beta', 'image': 'chrome_beta.png', 'release_notes': 'https://chromereleases.googleblog.com/search/label/Beta%20updates'},
            {'name': 'Dev', 'display': 'Chrome', 'version_path': 'dev/version', 'download_path': 'dev/download_link', 'bundle_id': 'com.google.Chrome.dev', 'image': 'chrome_dev.png', 'release_notes': 'https://chromereleases.googleblog.com/search/label/Dev%20updates'},
            {'name': 'Canary', 'display': 'Chrome', 'version_path': 'canary/version', 'download_path': 'canary/download_link', 'bundle_id': 'com.google.Chrome.canary', 'image': 'chrome_canary.png'},
            {'name': 'Canary ASAN', 'display': 'Chrome', 'version_path': 'canary_asan/version', 'download_path': 'canary_asan/download_link', 'bundle_id': 'com.google.Chrome.canary', 'image': 'chrome_canary.png'}
        ]
    },
    'Firefox': {
        'fetch_details': fetch_firefox_details,
        'channels': [
            {'name': '', 'display': 'Firefox', 'version_path': 'stable', 'download_path': 'stable', 'bundle_id': 'org.mozilla.firefox', 'image': 'firefox.png', 'release_notes': 'https://www.mozilla.org/en-US/firefox/notes/'},
            {'name': 'Beta', 'display': 'Firefox', 'version_path': 'beta', 'download_path': 'beta', 'bundle_id': 'org.mozilla.firefoxbeta', 'image': 'firefox.png', 'release_notes': 'https://www.mozilla.org/en-US/firefox/beta/notes/'},
            {'name': 'Developer', 'display': 'Firefox', 'version_path': 'dev', 'download_path': 'dev', 'bundle_id': 'org.mozilla.firefoxdev', 'image': 'firefox_developer.png', 'release_notes': 'https://www.mozilla.org/en-US/firefox/developer/notes/'},
            {'name': 'ESR', 'display': 'Firefox', 'version_path': 'esr', 'download_path': 'esr', 'bundle_id': 'org.mozilla.firefoxesr', 'image': 'firefox.png','release_notes': 'https://www.mozilla.org/en-US/firefox/organizations/notes/'},
            {'name': 'Nightly', 'display': 'Firefox', 'version_path': 'nightly', 'download_path': 'nightly', 'bundle_id': 'org.mozilla.nightly', 'image': 'firefox_nightly.png', 'release_notes': 'https://www.mozilla.org/en-US/firefox/nightly/notes/'}
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
        # Use the new release-level fetcher and a single "release" channel
        'fetch_details': fetch_safari_release,
        'channels': [
            {'name': '', 'display': 'Safari', 'version_path': 'release', 'download_path': 'release', 'bundle_id': 'com.apple.Safari', 'image': 'safari.png', 'release_notes': 'https://developer.apple.com/documentation/safari-release-notes'}
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
        tree = parse_xml_file(xml_path)
        root = tree.getroot()
        if browser == 'Chrome':
            # Use channel-specific release_time if available
            if channel:
                elem = root.find(f'.//{channel}/release_time')
                if elem is not None and elem.text:
                    return format_date(elem.text)
        elif browser == 'Firefox':
            # New Firefox XML: channel is one of 'stable', 'beta', 'dev', 'esr', 'nightly'
            if channel:
                channel_elem = root.find(f'.//{channel}')
                if channel_elem is not None:
                    release_elem = channel_elem.find('release_time')
                    if release_elem is not None and release_elem.text:
                        return format_date(release_elem.text)
            # fallback to <last_updated>
            elem = root.find('.//last_updated')
            if elem is not None and elem.text:
                return format_date(elem.text)
        elif browser == 'Edge':
            # Match Date for the requested channel (stable->current)
            channel_map = {'stable': 'current', 'beta': 'beta', 'dev': 'dev', 'canary': 'canary'}
            wanted = channel_map.get(channel, channel) if channel else 'current'
            for version in root.findall('.//Version'):
                ch = version.find('Channel')
                if ch is not None and ch.text == wanted:
                    date_elem = version.find('Date')
                    if date_elem is not None and date_elem.text:
                        return format_date(date_elem.text)
        elif browser == 'Safari':
            # New Safari XML uses <release> elements with <released>;
            # Technology previews use <Safari_Technology_Preview> with <PostDate>.
            if channel:
                # try both PostDate (tech previews) and released (release entries)
                elem = root.find(f'.//{channel}/PostDate') or root.find(f'.//{channel}/released')
                if elem is not None and elem.text:
                    return format_date(elem.text)
            # fallback: if there are <release> entries use the first <release>/<released>
            release_released = root.find('.//release/released')
            if release_released is not None and release_released.text:
                return format_date(release_released.text)
        # Global fallbacks
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
        # Skip Safari in the main browser table (we render a dedicated Safari releases section)
        if browser == 'Safari':
            continue

        xml_path = os.path.join(base_path, f'latest_{browser.lower()}_files/{browser.lower()}_latest_versions.xml')
        for channel in config['channels']:
            # Fetch version and download
            if browser == 'Safari':
                version, download = config['fetch_details'](xml_path, channel['version_path'], 'URL')
                last_updated = get_last_updated_from_xml(xml_path, browser, channel['version_path'])
            elif browser == 'Chrome':
                version, download = config['fetch_details'](xml_path, channel['version_path'], channel['download_path'])
                # For Extended Stable, use the same download as Stable
                if channel.get('name') == 'Extended Stable':
                    _, stable_download = config['fetch_details'](xml_path, 'stable/version', 'stable/download_link')
                    download = stable_download
                last_updated = get_last_updated_from_xml(xml_path, browser, channel['version_path'].split('/')[0])
            elif browser == 'Edge':
                version, download = config['fetch_details'](xml_path, channel['version_path'], channel['download_path'])
                last_updated = get_last_updated_from_xml(xml_path, browser, channel['version_path'])
            elif browser == 'Firefox':
                version, download = config['fetch_details'](xml_path, channel['version_path'], channel['download_path'])
                last_updated = get_last_updated_from_xml(xml_path, browser, channel['version_path'])
            else:
                version, download = "N/A", "N/A"
                last_updated = None

            channel_name = f"<sup>{channel['name']}</sup>" if channel['name'] else ""
            # For Extended Stable, show comment instead of release notes
            if 'release_notes_comment' in channel:
                release_notes = f"<br><small>{channel['release_notes_comment']}</small>"
            else:
                release_notes = f"<br><a href=\"{channel.get('release_notes', config.get('release_notes', '#'))}\" style=\"text-decoration: none;\"><small>_Release Notes_</small></a>" if 'release_notes' in channel or 'release_notes' in config else ""
            last_updated_html = f"<br><br><b>Last Updated:</b><br><em><code>{last_updated}</code></em>" if last_updated else ""
            table_content += (
                f"| **{channel['display']}** {channel_name} {release_notes}{last_updated_html} | "
                f"`{version}` | "
                f"`{channel['bundle_id']}` | "
                f"<a href=\"{download}\"><img src=\".github/images/{channel['image']}\" "
                f"alt=\"Download {channel['display']}\" width=\"80\"></a> |\n"
            )
    # Ensure the table is followed by blank lines so subsequent sections/tables render separately
    return table_content + "\n\n"

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
    chrome_version, chrome_download = fetch_chrome_details(xml_files['Chrome'], 'stable/version', 'stable/download_link')
    firefox_version, firefox_download = fetch_firefox_details(xml_files['Firefox'], 'stable', 'stable')
    edge_version, edge_download = fetch_edge_details(xml_files['Edge'], 'stable', 'stable')
    # Use the new release-based Safari fetcher (main browser tile)
    safari_version, safari_download = fetch_safari_release(xml_files['Safari'])

    # Fetch last updated dates from XMLs (browser-specific, channel-specific)
    chrome_last_updated = get_last_updated_from_xml(xml_files['Chrome'], 'Chrome', 'stable')
    firefox_last_updated = get_last_updated_from_xml(xml_files['Firefox'], 'Firefox', 'stable')
    edge_last_updated = get_last_updated_from_xml(xml_files['Edge'], 'Edge')
    safari_last_updated = get_last_updated_from_xml(xml_files['Safari'], 'Safari')

    readme_content = f"""# **BOFA**
**B**rowser **O**verview **F**eed for **A**pple

<a href="https://bofa.cocolabs.dev"><img src=".github/images/bofa_logo.png" alt="MOFA Image" width="200"></a>

Welcome to the **BOFA** repository! This resource tracks the latest versions of major web browsers for macOS. Feeds are automatically updated every hour from XML and JSON links directly from vendors.

We welcome community contributions—fork the repository, ask questions, or share insights to help keep this resource accurate and useful for everyone. Check out the user-friendly website version below for an easier browsing experience!

<div align="center">

<table>
  <tr>
    <th>🌟 Explore the BOFA Website 🌟</th>
    <th>⭐ Support the Project – Give it a Star! ⭐</th>
  </tr>
  <tr>
    <td align="center">🌐 <strong>Visit:</strong> <a href="https://bofa.cocolabs.dev">bofa.cocolabs.dev</a> 🌐</td>
    <td align="center">
      <a href="https://github.com/cocopuff2u/bofa">
        <img src="https://img.shields.io/github/stars/cocopuff2u/bofa" alt="GitHub Repo Stars">
      </a>
    </td>
  </tr>
</table>


## Latest Stable Browser Versions

<table>
  <tr>
    <td align="center"><a href="{chrome_download}"><img src=".github/images/chrome.png" alt="Chrome" width="80"></a><br><b>Chrome</b><br><em><code>{chrome_version}</code></em><br><br><small>Last Update:<br><em><code>{chrome_last_updated}</code></em></small><br><a href="https://chromereleases.googleblog.com/" style="text-decoration: none;"><small>Release Notes</small></a></td>
    <td align="center"><a href="{firefox_download}"><img src=".github/images/firefox.png" alt="Firefox" width="80"></a><br><b>Firefox</b><br><em><code>{firefox_version}</code></em><br><br><small>Last Update:<br><em><code>{firefox_last_updated}</code></em></small><br><a href="https://www.mozilla.org/en-US/firefox/notes/" style="text-decoration: none;"><small>Release Notes</small></a></td>
    <td align="center"><a href="{edge_download}"><img src=".github/images/edge.png" alt="Edge" width="80"></a><br><b>Edge</b><br><em><code>{edge_version}</code></em><br><br><small>Last Update:<br><em><code>{edge_last_updated}</code></em></small><br><a href="https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-stable-channel" style="text-decoration: none;"><small>Release Notes</small></a></td>
    <td align="center"><a href="{safari_download}"><img src=".github/images/safari.png" alt="Safari" width="80"></a><br><b>Safari</b><br><em><code>{safari_version}</code></em><br><br><small>Last Update:<br><em><code>{safari_last_updated}</code></em></small><br><a href="https://developer.apple.com/documentation/safari-release-notes" style="text-decoration: none;"><small>Release Notes</small></a></td>
  </tr>
</table>

"""

    readme_content += f"""
## Browser Packages

<sup>All links below direct to the official browser vendor. The links provided will always download the latest available version as of the last scan update.</sup>  

<sup>**Chrome**: [**_Raw XML_**](latest_chrome_files/chrome_latest_versions.xml) [**_Raw YAML_**](latest_chrome_files/chrome_latest_versions.yaml) [**_Raw JSON_**](latest_chrome_files/chrome_latest_versions.json) | **Firefox**: [**_Raw XML_**](latest_firefox_files/firefox_latest_versions.xml) [**_Raw YAML_**](latest_firefox_files/firefox_latest_versions.yaml) [**_Raw JSON_**](latest_firefox_files/firefox_latest_versions.json)</sup>

<sup>**Edge**: [**_Raw XML_**](latest_edge_files/edge_latest_versions.xml) [**_Raw YAML_**](latest_edge_files/edge_latest_versions.yaml) [**_Raw JSON_**](latest_edge_files/edge_latest_versions.json) | **Safari**: [**_Raw XML_**](latest_safari_files/safari_latest_versions.xml) [**_Raw YAML_**](latest_safari_files/safari_latest_versions.yaml) [**_Raw JSON_**](latest_safari_files/safari_latest_versions.json)</sup>

<sup>_Last Updated: <code style="color : mediumseagreen">{global_last_updated}</code> (Automatically Updated every hour)_</sup>

</div>

"""

    readme_content += generate_browser_table(base_path)
    # Add a dedicated Safari releases table (all <release> entries)
    readme_content += generate_safari_releases_table(base_path, xml_files['Safari'])
    # Append the new Safari Technology Preview table (if any)
    readme_content += generate_safari_tech_table(base_path, xml_files['Safari'])
    readme_content += generate_settings_section()

    readme_path = os.path.join(base_path, 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

if __name__ == "__main__":
    generate_readme()
