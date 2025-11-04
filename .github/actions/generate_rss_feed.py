import xml.etree.ElementTree as ET
from datetime import datetime
import os

# Get the root directory of the project (assuming the script is inside a subfolder like '/update_readme_scripts/')
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repo_root = os.path.dirname(project_root)  # go up from .github to repo root

# Define the correct paths based on the project root
# latest_xml_path = os.path.join(repo_root, 'latest_raw_files', 'macos_standalone_latest.xml')
# Replace single-feed path with a directory + per-package filenames
# FEEDS_DIR = os.path.join(repo_root, 'latest_raw_files', 'macos_standalone_rss')
# FEED_BASE_URL = "https://BOFA.cocolabs.dev/rss_feeds"

# Print the paths to verify if they are correct
# print(f"Latest XML Path: {latest_xml_path}")
# print(f"RSS Feeds Directory: {FEEDS_DIR}")

def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for subelem in elem:
            indent(subelem, level + 1)
        if not subelem.tail or not subelem.tail.strip():
            subelem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

# Constants for URLs
SITE_URL = "https://bofa.cocolabs.dev/"

# Remove the static PACKAGES list and replace with dynamic parsing
# --- Begin new code for browser XML parsing ---

# Paths to browser XML files
chrome_xml_path = os.path.join(repo_root, 'latest_chrome_files', 'chrome_latest_versions.xml')
edge_xml_path = os.path.join(repo_root, 'latest_edge_files', 'edge_latest_versions.xml')
firefox_xml_path = os.path.join(repo_root, 'latest_firefox_files', 'firefox_latest_versions.xml')

def parse_chrome_packages():
    pkgs = []
    if not os.path.exists(chrome_xml_path):
        return pkgs
    tree = ET.parse(chrome_xml_path)
    root = tree.getroot()
    for channel in ['stable']:
        node = root.find(channel)
        if node is not None:
            version = node.find('version').text if node.find('version') is not None else ''
            download = node.find('download_link').text if node.find('download_link') is not None else ''
            release_time = node.find('release_time').text if node.find('release_time') is not None else ''
            pkgs.append({
                "name": "Chrome",
                "feed_filename": "chrome_rss.xml",
                "channel_title": "BOFA - Chrome RSS Feed",
                "channel_description": "Google Chrome for Mac",
                "release_notes_url": "https://chromereleases.googleblog.com/",
                "item_title": "New Chrome Release",
                "image_url": "https://bofa.cocolabs.dev/images/bofa_logo.png",
                "short_version": version,
                "update_download": download,
                "last_updated": release_time,
            })
    return pkgs

def parse_edge_packages():
    pkgs = []
    if not os.path.exists(edge_xml_path):
        return pkgs
    tree = ET.parse(edge_xml_path)
    root = tree.getroot()
    for version in root.findall('Version'):
        channel = version.find('Channel').text if version.find('Channel') is not None else ''
        if channel != 'current':
            continue  # Only process the 'current' channel
        ver = version.find('Version').text if version.find('Version') is not None else ''
        download = version.find('Location').text if version.find('Location') is not None else ''
        date = version.find('Date').text if version.find('Date') is not None else ''
        pkgs.append({
            "name": "Edge",
            "feed_filename": "edge_rss.xml",
            "channel_title": "BOFA - Edge RSS Feed",
            "channel_description": "Microsoft Edge for Mac",
            "release_notes_url": "https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-stable-channel",
            "item_title": "New Edge Release",
            "image_url": "https://bofa.cocolabs.dev/images/bofa_logo.png",
            "short_version": ver,
            "update_download": download,
            "last_updated": date,
        })
    return pkgs

def parse_firefox_packages():
    pkgs = []
    if not os.path.exists(firefox_xml_path):
        return pkgs
    tree = ET.parse(firefox_xml_path)
    root = tree.getroot()
    # Get the root-level <last_updated> for the feed's lastBuildDate if needed
    root_last_updated = root.find('last_updated').text if root.find('last_updated') is not None else ''
    for channel in ['stable']:
        node = root.find(channel)
        if node is not None:
            version = node.find('version').text if node.find('version') is not None else ''
            download = node.find('download').text if node.find('download') is not None else ''
            release_time = node.find('release_time').text if node.find('release_time') is not None else ''
            # Use <release_time> for last_updated (pubDate)
            pkgs.append({
                "name": "Firefox",
                "feed_filename": "firefox_rss.xml",
                "channel_title": "BOFA - Firefox RSS Feed",
                "channel_description": "Mozilla Firefox for Mac",
                "release_notes_url": "https://www.mozilla.org/en-US/firefox/notes/",
                "item_title": "New Firefox Release",
                "image_url": "https://bofa.cocolabs.dev/images/bofa_logo.png",
                "short_version": version,
                "update_download": download,
                "last_updated": release_time,
            })
    return pkgs

# Combine all browser packages
PACKAGES = parse_chrome_packages() + parse_edge_packages() + parse_firefox_packages()

# --- End new code for browser XML parsing ---

# Helper: get all textual content from an element (text + children text/tails)
def _get_all_text(el: ET.Element) -> str:
    parts = []
    if el.text:
        parts.append(el.text)
    for child in el:
        if child.text:
            parts.append(child.text)
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)

# Build the <description> as escaped HTML text (no child elements, no CDATA)
def _set_description_with_link(desc_el: ET.Element, version: str, release_notes_url: str) -> None:
    desc_el.clear()
    desc_el.text = (
        "<br>"
        f"Version: {version}"
        "<br>"
        f"Release Notes: <a href=\"{release_notes_url}\">Release Notes</a>"
    )

# Register atom namespace for proper find/create
ET.register_namespace('atom', 'http://www.w3.org/2005/Atom')
ATOM_NS = {'atom': 'http://www.w3.org/2005/Atom'}

def _ensure_feed_exists(feed_path: str) -> None:
    if not os.path.exists(feed_path) or os.path.getsize(feed_path) == 0:
        rss = ET.Element('rss', {'version': '2.0', 'xmlns:atom': 'http://www.w3.org/2005/Atom'})
        ET.SubElement(rss, 'channel')
        tree = ET.ElementTree(rss)
        indent(rss)
        os.makedirs(os.path.dirname(feed_path), exist_ok=True)
        tree.write(feed_path, encoding='UTF-8', xml_declaration=True)

def _find_package_node(root: ET.Element, package_name: str):
    for package in root.findall('package'):
        name_el = package.find('name')
        if name_el is not None and name_el.text == package_name:
            return package
    return None

def _update_rss_for_package(pkg_conf: dict) -> None:
    # Use the new fields directly from pkg_conf
    short_version = (pkg_conf.get('short_version') or "").strip()
    update_download = (pkg_conf.get('update_download') or "").strip()
    last_updated = (pkg_conf.get('last_updated') or "").strip()

    # Compute per-package feed paths/urls
    feed_filename = pkg_conf['feed_filename']
    # feed_path = os.path.join(FEEDS_DIR, feed_filename)
    # feed_url = f"{FEED_BASE_URL}/{feed_filename}"

    # Only write to browser-specific folders
    browser_folder = None
    if feed_filename.startswith("chrome_"):
        browser_folder = os.path.join(repo_root, "latest_chrome_files")
    elif feed_filename.startswith("edge_"):
        browser_folder = os.path.join(repo_root, "latest_edge_files")
    elif feed_filename.startswith("firefox_"):
        browser_folder = os.path.join(repo_root, "latest_firefox_files")
    if not browser_folder:
        print(f"{pkg_conf['name']}: Unknown browser type for feed file {feed_filename}; skipping.")
        return
    feed_path = os.path.join(browser_folder, feed_filename)
    feed_url = ""  # Not used anymore

    # Prepare dates
    try:
        import re
        dt_str = last_updated
        # Remove trailing timezone abbreviation (e.g., " EST" or " EDT")
        dt_str_clean = re.sub(r' [A-Z]{2,4}$', '', dt_str)
        dt_obj = datetime.strptime(dt_str_clean, "%B %d, %Y %I:%M %p")
        last_build_date_text = dt_obj.strftime("%a, %d %b %Y %H:%M:%S +0000")
    except Exception:
        try:
            # Try parsing as date only (fallback for edge cases)
            dt_obj = datetime.strptime(last_updated, "%B %d, %Y")
            last_build_date_text = dt_obj.strftime("%a, %d %b %Y 00:00:00 +0000")
        except Exception:
            last_build_date_text = datetime.utcnow().strftime("%a, %d %b %Y 00:00:00 +0000")

    # Ensure feed file exists
    _ensure_feed_exists(feed_path)

    # Parse the RSS feed
    rss_tree = ET.parse(feed_path)
    rss_root = rss_tree.getroot()
    channel = rss_root.find('channel')

    # Initialize channel-level elements if they do not exist
    title = channel.find('title')
    link = channel.find('link')
    description = channel.find('description')
    docs = channel.find('docs')

    if title is None:
        title = ET.SubElement(channel, 'title')
    title.text = pkg_conf['channel_title']

    if link is None:
        link = ET.SubElement(channel, 'link')
    # Always ensure canonical channel link points to the site (not the feed URL)
    link.text = SITE_URL

    if description is None:
        description = ET.SubElement(channel, 'description')
    description.text = pkg_conf['channel_description']

    if docs is None:
        docs = ET.SubElement(channel, 'docs')
    docs.text = "http://www.rssboard.org/rss-specification"

    # Add/update atom:link rel="self" for the feed URL
    atom_link = channel.find('atom:link', ATOM_NS)
    if atom_link is None:
        atom_link = ET.SubElement(channel, '{http://www.w3.org/2005/Atom}link', {
            'href': feed_url,
            'rel': 'self',
            'type': 'application/rss+xml'
        })
    else:
        atom_link.set('href', feed_url)
        atom_link.set('rel', 'self')
        atom_link.set('type', 'application/rss+xml')

    # Add/ensure language, ttl, and lastBuildDate
    language = channel.find('language')
    if language is None:
        language = ET.SubElement(channel, 'language')
    language.text = 'en-US'

    ttl = channel.find('ttl')
    if ttl is None:
        ttl = ET.SubElement(channel, 'ttl')
    ttl.text = '60'

    last_build_date = channel.find('lastBuildDate')
    if last_build_date is None:
        last_build_date = ET.SubElement(channel, 'lastBuildDate')
    last_build_date.text = last_build_date_text

    # Add the <image> element above the <item> elements
    image = channel.find('image')
    if image is None:
        image = ET.Element('image')
        url = ET.SubElement(image, 'url')
        url.text = pkg_conf['image_url']
        img_title = ET.SubElement(image, 'title')
        img_title.text = pkg_conf['channel_title']
        img_link = ET.SubElement(image, 'link')
        img_link.text = SITE_URL
        first_item_index = next((i for i, elem in enumerate(channel) if elem.tag == 'item'), len(channel))
        channel.insert(first_item_index, image)
    else:
        # Ensure image link points to the site URL
        img_link = image.find('link')
        if img_link is None:
            img_link = ET.SubElement(image, 'link')
        img_link.text = SITE_URL

    # Remove duplicate non-atom channel <link> elements (keep the first one as canonical)
    links = channel.findall('link')
    if links:
        links[0].text = SITE_URL
        for extra in links[1:]:
            channel.remove(extra)
    else:
        ET.SubElement(channel, 'link').text = SITE_URL

    # Check if the package version already exists in the RSS feed
    existing_version = False
    for item in channel.findall('item'):
        title_el = item.find('title')
        desc_el = item.find('description')
        if not (title_el is None or desc_el is None):
            desc_text = _get_all_text(desc_el)
            if (short_version in (title_el.text or "")) or (short_version in desc_text):
                _set_description_with_link(desc_el, short_version, pkg_conf['release_notes_url'])
                existing_version = True
                print(f"{pkg_conf['name']}: version already in RSS feed")
                break

    # If the version is not already in the feed, add it
    if not existing_version:
        new_item = ET.Element('item')
        title_el = ET.SubElement(new_item, 'title')
        title_el.text = pkg_conf['item_title']
        link_el = ET.SubElement(new_item, 'link')
        link_el.text = update_download
        desc_el = ET.SubElement(new_item, 'description')
        _set_description_with_link(desc_el, short_version, pkg_conf['release_notes_url'])
        pubDate = ET.SubElement(new_item, 'pubDate')
        pubDate.text = last_build_date_text
        guid = ET.SubElement(new_item, 'guid')
        guid.text = update_download
        guid.set('isPermaLink', 'false')

        # Insert the new item into the RSS feed
        first_item_index = next((i for i, elem in enumerate(channel) if elem.tag == 'item'), len(channel))
        channel.insert(first_item_index, new_item)
        print(f"{pkg_conf['name']}: RSS feed updated with new version")

    # Always write updates (even if only header normalization happened)
    indent(rss_root)
    rss_tree.write(feed_path, encoding='UTF-8', xml_declaration=True)

    print(f"Wrote RSS feed to {feed_path}")

# Process each configured package
for pkg in PACKAGES:
    # No need to look up in latest.xml; use the pkg_conf fields directly
    if not pkg.get('short_version') or not pkg.get('update_download'):
        print(f"{pkg['name']}: missing version or download; skipping.")
        continue
    _update_rss_for_package(pkg)