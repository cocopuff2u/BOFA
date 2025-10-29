import requests
import gzip
import plistlib
from datetime import datetime
import pytz
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
import yaml
from collections import defaultdict
from html.parser import HTMLParser
import re
import copy
import logging

# Use a very simple, human-friendly log output (message only)
logging.basicConfig(level=logging.INFO, format="%(message)s")

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

# Small helper: collect anchors from HTML and return list of dicts {href, text}
def collect_anchors(html):
    """
    Parse HTML and return list of anchors with 'href' and concatenated inner text.
    This replaces duplicate inner AnchorCollector classes used in multiple functions.
    """
    class AnchorCollector(HTMLParser):
        def __init__(self):
            super().__init__()
            self._in_a = False
            self._href = None
            self._fragments = []
            self.anchors = []

        def handle_starttag(self, tag, attrs):
            if tag.lower() == "a":
                attrs = dict(attrs)
                href = attrs.get("href")
                if href:
                    self._in_a = True
                    self._href = href
                    self._fragments = []

        def handle_endtag(self, tag):
            if tag.lower() == "a" and self._in_a:
                self.anchors.append({"href": self._href, "text": " ".join(self._fragments)})
                self._in_a = False
                self._href = None
                self._fragments = []

        def handle_data(self, data):
            if self._in_a and data and data.strip():
                self._fragments.append(data.strip())

    parser = AnchorCollector()
    parser.feed(html)
    return parser.anchors

def extract_version_from_url(url):
    # Extract version from URL (e.g., Safari16.6.1BigSurAuto.pkg -> 16.6.1)
    try:
        filename = url.split('/')[-1]
        version = filename.replace('Safari', '').split('Auto')[0]
        version = ''.join(c for c in version if c.isdigit() or c == '.')
        return version
    except Exception:
        return "Unknown"

def extract_os_from_url(url):
    # Extract OS name from URL (e.g., Safari18.3VenturaAuto.pkg -> Ventura)
    try:
        filename = url.split('/')[-1]
        version_and_os = filename.replace('Safari', '').split('Auto')[0]
        # Remove any digits and dots from the start
        os_name = ''.join(c for c in version_and_os if not (c.isdigit() or c == '.'))
        return os_name
    except Exception:
        return "Unknown"

def bytes_to_mb(bytes_size):
    # Return human-readable MB string with two decimals
    return f"{bytes_size / (1024 * 1024):.2f} MB"

def fetch_technology_preview_info():
    """
    Scrape Safari Technology Preview info from Apple developer resources.
    Returns a dict: { release, posted, oses: {<OS>: {URL, PostDate?, Requires?}}, ReleaseNotes? }
    """
    url = "https://developer.apple.com/safari/resources/"
    session = get_session()
    response = session.get(url)
    response.raise_for_status()
    html = response.text

    # Extract loose release/post date info
    info = {"release": None, "posted": None, "oses": {}, "ReleaseNotes": None}
    release_match = re.search(r'Release\s*[:\s]*([0-9]{1,4})', html, re.I)
    if not release_match:
        release_match = re.search(r'Release[\s\S]{0,100}?(\d{1,4})', html, re.I)
    if release_match:
        info["release"] = release_match.group(1).strip()

    posted_match = re.search(r'Posted\s*[:\s]*([A-Za-z]+\s+\d{1,2},\s*\d{4})', html, re.I)
    if posted_match:
        info["posted"] = posted_match.group(1).strip()

    # Use the shared anchor collector
    anchors = collect_anchors(html)

    # process anchors that point to dmg files
    for a in anchors:
        href = a.get("href", "")
        if not href:
            continue
        if ".dmg" not in href.lower():
            # capture release notes link if present
            if "release-notes" in href and not info.get("ReleaseNotes"):
                info["ReleaseNotes"] = href if href.startswith("http") else "https://developer.apple.com" + href
            continue

        anchor_text = a.get("text", "").replace('\xa0', ' ').strip()
        # try to extract "for macOS <Name>" from anchor text
        os_name = None
        m = re.search(r'for\s+macOS[^\w]*(?P<os>[A-Za-z0-9 \-]+)', anchor_text, re.I)
        if m:
            os_name = m.group("os").strip()
        else:
            parts = [p.strip() for p in anchor_text.split() if p.strip()]
            if parts:
                candidate = parts[-1]
                if len(candidate) <= 30 and not candidate.lower().startswith("safari"):
                    os_name = candidate

        # fallback: infer from URL filename or path part
        if not os_name:
            try:
                basename = os.path.basename(href)
                candidate = basename.replace('.dmg', '').replace('-', ' ').strip()
                candidate = re.sub(r'(?i)safaritechnologypreview|safaritechnologypreview|safari|technology|preview', '', candidate).strip()
                if candidate:
                    os_name = candidate
            except Exception:
                os_name = "Unknown"

        if not os_name:
            os_name = "Unknown"

        full_url = href if href.startswith("http") else "https://developer.apple.com" + href

        # look near the href in the html for a strict date element and "Requires macOS"
        requires = None
        postdate = None

        # 1) Try: href followed by a <p ...no-margin>DATE</p>
        try:
            pattern_after_href = re.compile(re.escape(href) + r'[\s\S]{0,800}?<p[^>]*class=["\'][^"\']*no-margin[^"\']*["\'][^>]*>\s*(' + r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}' + r')\s*</p>', re.I)
            m_after = pattern_after_href.search(html)
            if m_after:
                postdate = m_after.group(1).strip()
        except re.error:
            m_after = None

        # 2) Try: after anchor_text
        if not postdate and anchor_text:
            try:
                pattern_after_text = re.compile(re.escape(anchor_text) + r'[\s\S]{0,800}?<p[^>]*class=["\'][^"\']*no-margin[^"\']*["\'][^>]*>\s*(' + r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}' + r')\s*</p>', re.I)
                m_text = pattern_after_text.search(html)
                if m_text:
                    postdate = m_text.group(1).strip()
            except re.error:
                m_text = None

        # 3) Try: date before the href within a window
        if not postdate:
            try:
                pattern_before_href = re.compile(r'<p[^>]*class=["\'][^"\']*no-margin[^"\']*["\'][^>]*>\s*(' + r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}' + r')\s*</p>[\s\S]{0,800}' + re.escape(href), re.I)
                m_before = pattern_before_href.search(html)
                if m_before:
                    postdate = m_before.group(1).strip()
            except re.error:
                m_before = None

        # look for Requires macOS nearby (simpler)
        idx = html.find(href)
        if idx != -1:
            start = max(0, idx - 600)
            snippet = html[start: idx + 600]
            req_match = re.search(r'Requires\s+macOS[^\<\n\r]+', snippet, re.I)
            if req_match:
                req_text = re.sub(r'<[^>]+>', '', req_match.group(0)).strip()
                requires = req_text

        os_key = os_name
        info["oses"].setdefault(os_key, {})["URL"] = full_url
        if requires:
            info["oses"][os_key]["Requires"] = requires
        if postdate:
            info["oses"][os_key]["PostDate"] = postdate
        if not info.get("posted") and postdate:
            info["posted"] = postdate

    # ensure ReleaseNotes captured if present elsewhere
    if not info.get("ReleaseNotes"):
        rn = re.search(r'href="([^"]*release-notes[^"]*)"', html, re.I)
        if rn:
            href = rn.group(1)
            info["ReleaseNotes"] = href if href.startswith("http") else "https://developer.apple.com" + href

    # fallback global posted date
    if not info.get("posted"):
        any_date = re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}', html, re.I)
        if any_date:
            info["posted"] = any_date.group(0).strip()
            for os_key, os_data in info.get("oses", {}).items():
                os_data.setdefault("PostDate", info["posted"])

    return info

def fetch_all_downloads_info():
    """
    Scrape Apple 'All Downloads' page for Safari-related downloads.
    Returns list of dicts: {Name, URL, Version, PostDate, Requires}
    """
    url = "https://developer.apple.com/download/all/?q=Safari"
    session = get_session()
    resp = session.get(url)
    resp.raise_for_status()
    html = resp.text

    # Use the shared anchor collector
    anchors = collect_anchors(html)

    # ...existing code for date patterns...
    month_names = r'January|February|March|April|May|June|July|August|September|October|November'
    date_pattern = rf'(?:{month_names})\s+\d{{1,2}},\s*\d{{4}}'

    results = []
    for a in anchors:
        href = a.get("href", "")
        text = a.get("text", "")
        if not href:
            continue

        full_url = href if href.startswith("http") else "https://developer.apple.com" + href

        # keep links that are downloads or explicitly mention safari
        if not (re.search(r'\.(dmg|pkg|zip|tar\.gz|pkg\.zip)$', full_url, re.I) or re.search(r'safari', text + href, re.I)):
            continue

        name = text.strip() or os.path.basename(href)

        # version from visible text then fallback to filename heuristic
        version = ""
        m = re.search(r'Safari(?:\s|:)?\s*([0-9]+(?:\.[0-9]+)*)', name, re.I)
        if m:
            version = m.group(1)
        else:
            version = extract_version_from_url(full_url) or ""

        # find nearby date
        postdate = ""
        idx = html.find(href)
        if idx != -1:
            start = max(0, idx - 800)
            snippet = html[start: idx + 800]
            mdate = re.search(date_pattern, snippet, re.I)
            if mdate:
                postdate = mdate.group(0).strip()
        if not postdate:
            many = re.search(date_pattern, html, re.I)
            if many:
                postdate = many.group(0).strip()

        # capture 'Requires macOS' nearby
        requires = ""
        if idx != -1:
            start = max(0, idx - 600)
            snippet = html[start: idx + 600]
            req_match = re.search(r'Requires\s+macOS[^\<\n\r]+', snippet, re.I)
            if req_match:
                requires = re.sub(r'<[^>]+>', '', req_match.group(0)).strip()

        results.append({
            "Name": name,
            "URL": full_url,
            "Version": version or "",
            "PostDate": postdate or "",
            "Requires": requires or ""
        })

    # deduplicate by URL
    seen = set()
    unique = []
    for r in results:
        if r["URL"] in seen:
            continue
        seen.add(r["URL"])
        unique.append(r)

    return unique

# Helper: convert an ElementTree to a nested dict (used by both xml_to_json and xml_to_yaml)
def etree_to_dict(t):
    """
    Convert ElementTree element into a nested Python dict.
    Preserves element text and attributes (attributes prefixed with '@', text as '#text').
    """
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
    text = (t.text or "").strip()
    if text:
        if children or t.attrib:
            d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d

def xml_to_json(xml_str):
    try:
        root = ET.fromstring(xml_str)
        return json.dumps(etree_to_dict(root), indent=4)
    except Exception as e:
        logging.error(f"Error converting XML to JSON: {e}")
        return None

def xml_to_yaml(xml_str):
    try:
        root = ET.fromstring(xml_str)
        data_dict = etree_to_dict(root)

        # Ensure last_updated is at the top of the top-level mapping if present
        safari_versions = data_dict.get('safari_versions', {})
        if isinstance(safari_versions, dict) and 'last_updated' in safari_versions:
            last_updated = safari_versions.pop('last_updated')
            safari_versions = {'last_updated': last_updated, **safari_versions}
            data_dict['safari_versions'] = safari_versions

        return yaml.dump(data_dict, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logging.error(f"Error converting XML to YAML: {e}")
        return None

# NEW: fetch and parse Safari release-notes JSON index
def fetch_safari_release_notes_index(json_url="https://developer.apple.com/tutorials/data/documentation/safari-release-notes.json"):
    """
    Fetch the Safari release notes index JSON and return a list of top items per major version.
    Each item contains: major_version, release_notes (identifier), release_notes_url (if found),
    title, released date, and version (e.g. "18.6 (20621.3.11)" or "26.1 beta (20622.2.5)").
    """
    session = get_session()
    resp = session.get(json_url)
    resp.raise_for_status()
    data = resp.json()

    refs = data.get("references", {}) or {}
    results = []

    for sec in data.get("topicSections", []) or []:
        title = sec.get("title", "") or ""
        m = re.search(r'Version\s+(\d+)', title, re.I)
        if not m:
            continue
        major = m.group(1)
        identifiers = sec.get("identifiers", []) or []
        if not identifiers:
            continue

        # Process every identifier for this major version (keeps beta + non-beta entries)
        for identifier in identifiers:
            ref = refs.get(identifier, {}) or {}
            ref_title = ref.get("title", "") or ""
            abstract_arr = ref.get("abstract", []) or []

            # Try to find a URL/path in the reference entry
            release_notes_url = None
            # common possible keys that may contain a URL or path
            for key in ("url", "path", "href", "link", "source", "urlPath"):
                v = ref.get(key)
                if v:
                    # normalize
                    if isinstance(v, str):
                        if v.startswith("http"):
                            release_notes_url = v
                        elif v.startswith("/"):
                            release_notes_url = "https://developer.apple.com" + v
                        else:
                            release_notes_url = "https://developer.apple.com/" + v.lstrip('/')
                    break

            # If we didn't find a URL but reference may have 'identifier' or 'id' we can try a fallback
            if not release_notes_url:
                alt = ref.get("id") or ref.get("identifier")
                if isinstance(alt, str) and alt.startswith("/"):
                    release_notes_url = "https://developer.apple.com" + alt

            abstract_text = None
            if abstract_arr:
                first = abstract_arr[0]
                if isinstance(first, dict):
                    # common shape: {"text": "...", "type": "text"}
                    abstract_text = first.get("text") or first.get("content") or None
                elif isinstance(first, str):
                    abstract_text = first

            released = ""
            version_line = ""
            if abstract_text:
                # Try to parse "Released <Month DD, YYYY> — <version info>"
                m2 = re.search(r'Released\s+([A-Za-z]+\s+\d{1,2},\s*\d{4})\s*[—-]\s*(.*)', abstract_text)
                if m2:
                    released = m2.group(1).strip()
                    version_line = m2.group(2).strip()
                else:
                    version_line = abstract_text.strip()

            # Normalize version_line: remove leading "Version" if present
            version_line = re.sub(r'(?i)^\s*Version\s+', '', version_line).strip()

            # Combine into single "version" field (e.g. "18.6 (20621.3.11)")
            version = version_line.strip()

            results.append({
                "major_version": major,
                "release_notes": identifier,
                "release_notes_url": release_notes_url,   # <-- new field (may be None)
                "title": ref_title,
                "released": released,
                "version": version
            })

    return results

# NEW: convert notes list (dicts) into pretty XML
def notes_to_xml(notes):
	"""
	notes: list of dicts with keys like major_version, release_notes, release_notes_url, title, released, version, etc.
	returns: pretty XML string (utf-8)
	"""
	root = ET.Element('safari_all_history')

	# add last_updated in US/Eastern timezone
	eastern = pytz.timezone('US/Eastern')
	now_str = datetime.now(eastern).strftime('%B %d, %Y %I:%M %p %Z')
	last_updated = ET.SubElement(root, 'last_updated')
	last_updated.text = now_str

	for item in notes:
		release = ET.SubElement(root, 'release')
		# emit fields in required order: major_version, full_version, released, release_notes
		major = item.get('major_version')
		if major is not None:
			m = ET.SubElement(release, 'major_version')
			m.text = str(major)

		# map existing 'version' -> 'full_version'
		full_ver = item.get('version') or item.get('full_version') or ""
		if full_ver:
			fv = ET.SubElement(release, 'full_version')
			fv.text = str(full_ver)

		released = item.get('released')
		if released is not None:
			r = ET.SubElement(release, 'released')
			r.text = str(released)

		# Prefer a full URL for release notes when available; fallback to identifier
		release_notes_url = item.get('release_notes_url')
		release_notes_id = item.get('release_notes')
		rn = ET.SubElement(release, 'release_notes')
		if release_notes_url:
			rn.text = str(release_notes_url)
		elif release_notes_id is not None:
			rn.text = str(release_notes_id)
		else:
			rn.text = ""

		# include any other keys except the ones we've already output and 'title'
		for k, v in item.items():
			if k in ('major_version', 'version', 'full_version', 'released', 'release_notes', 'release_notes_url', 'title'):
				continue
			if v is None or v == "":
				continue
			other = ET.SubElement(release, k)
			other.text = str(v)
	# pretty-print
	xml_bytes = ET.tostring(root, encoding='utf-8')
	pretty = minidom.parseString(xml_bytes).toprettyxml(indent="  ")
	return pretty

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
                                
                                # Use a generic <release> element and include the OS as a child
                                packages = ET.SubElement(root, 'release')
                                os_elem = ET.SubElement(packages, 'os')
                                os_elem.text = os_name
                                
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
        
        # Add Safari_Technology_Preview entries from live scrape
        tp_info = fetch_technology_preview_info()
        tp_release = tp_info.get("release", "")
        tp_posted = tp_info.get("posted", "")
        for os_name, os_data in tp_info.get("oses", {}).items():
            # Compose entry
            stp_elem = ET.SubElement(root, 'Safari_Technology_Preview')
            macos_elem = ET.SubElement(stp_elem, 'macos')
            macos_elem.text = os_name
            version_elem = ET.SubElement(stp_elem, 'version')
            version_elem.text = tp_release
            postdate_elem = ET.SubElement(stp_elem, 'PostDate')
            postdate_elem.text = os_data.get("PostDate") or tp_posted or ""
            url_elem = ET.SubElement(stp_elem, 'URL')
            url_elem.text = os_data.get("URL", "")
            # add ReleaseNotes into each Technology Preview entry if present
            if tp_info.get("ReleaseNotes"):
                rn_elem = ET.SubElement(stp_elem, 'ReleaseNotes')
                rn_elem.text = tp_info["ReleaseNotes"]

        # include Safari beta/downloads from developer downloads page
        try:
            downloads = fetch_all_downloads_info()
            for dl in downloads:
                beta_elem = ET.SubElement(root, 'Safari_Beta')
                name_elem = ET.SubElement(beta_elem, 'Name')
                name_elem.text = dl.get("Name", "")
                version_elem = ET.SubElement(beta_elem, 'version')
                version_elem.text = dl.get("Version", "")
                postdate_elem = ET.SubElement(beta_elem, 'PostDate')
                postdate_elem.text = dl.get("PostDate", "")
                url_elem = ET.SubElement(beta_elem, 'URL')
                url_elem.text = dl.get("URL", "")
                if dl.get("Requires"):
                    req_elem = ET.SubElement(beta_elem, 'Requires')
                    req_elem.text = dl.get("Requires")
        except Exception as e:
            # don't fail the whole flow on downloads scraping errors
            logging.warning(f"downloads scrape failed: {e}")

        # Convert to pretty XML string
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        return xml_str
    
    except Exception as e:
        logging.error(f"Error: {e}")
        return None

def export_to_file(content, filepath):
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(content)

# NEW: fetch Safari release-notes index and write top item per major version
try:
    notes = fetch_safari_release_notes_index()
    if notes:
        os.makedirs('latest_safari_files', exist_ok=True)
        # write real XML instead of JSON-in-XML
        xml_out = notes_to_xml(notes)
        export_to_file(xml_out, 'latest_safari_files/safari_all_history.xml')
        # NEW: also write JSON and YAML representations
        export_to_file(json.dumps(notes, indent=2), 'latest_safari_files/safari_all_history.json')
        export_to_file(yaml.dump(notes, default_flow_style=False, sort_keys=False), 'latest_safari_files/safari_all_history.yaml')
        # Log a short, simple summary for each history item
        for item in notes:
            mv = item.get("major_version")
            title = item.get("title") or item.get("release_notes")
            released = item.get("released") or ""
            version = item.get("version") or ""
            logging.info(f"History: {mv} — {title} — {version} — {released}")
except Exception as e:
    logging.warning(f"failed to fetch release-notes index: {e}")

# Replace __main__ to only run the catalog + export flow (no preview-only helpers)
if __name__ == "__main__":
    # Generate latest Safari versions XML/JSON/YAML from Apple catalog + Technology Preview scraping
    catalog_url = 'https://swscan.apple.com/content/catalogs/others/index-15-14-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog.gz'
    safari_xml = get_latest_safari_version(catalog_url)

    if safari_xml:
        # Build and write catalog package outputs WITHOUT Safari_Technology_Preview entries.
        # Keep original safari_xml intact for creating the Technology Preview "latest_versions" file below.
        try:
            catalog_root = ET.fromstring(safari_xml)
            # remove any Safari_Technology_Preview children
            for stp in catalog_root.findall('Safari_Technology_Preview'):
                catalog_root.remove(stp)
            # pretty-print and export filtered catalog
            catalog_xml_raw = minidom.parseString(ET.tostring(catalog_root, encoding='utf-8')).toprettyxml(indent="  ")
            catalog_xml = "\n".join([ln for ln in catalog_xml_raw.splitlines() if ln.strip() != ""])
            export_to_file(catalog_xml, 'latest_safari_files/safari_all_catalog_pkg.xml')
            catalog_json = xml_to_json(catalog_xml)
            if catalog_json:
                export_to_file(catalog_json, 'latest_safari_files/safari_all_catalog_pkg.json')
            catalog_yaml = xml_to_yaml(catalog_xml)
            if catalog_yaml:
                export_to_file(catalog_yaml, 'latest_safari_files/safari_all_catalog_pkg.yaml')
        except Exception as e:
            # fallback to writing the raw xml if filtering fails
            export_to_file(safari_xml, 'latest_safari_files/safari_all_catalog_pkg.xml')
            safari_json = xml_to_json(safari_xml)
            if safari_json:
                export_to_file(safari_json, 'latest_safari_files/safari_all_catalog_pkg.json')
            safari_yaml = xml_to_yaml(safari_xml)
            if safari_yaml:
                export_to_file(safari_yaml, 'latest_safari_files/safari_all_catalog_pkg.yaml')

        # NEW: create a "latest_versions" output containing ONLY Safari_Technology_Preview entries
        try:
            # parse original catalog xml
            root = ET.fromstring(safari_xml)
            new_root = ET.Element(root.tag)  # keep same root name, e.g. 'safari_versions'
            # copy last_updated if present
            lu = root.find('last_updated')
            if lu is not None:
                new_lu = ET.SubElement(new_root, 'last_updated')
                new_lu.text = lu.text

            # append Technology Preview entries (deep copy)
            for elem in root.findall('Safari_Technology_Preview'):
                new_root.append(copy.deepcopy(elem))

            # Fetch release-notes list so we can pick one "chosen" per major + include beta(s)
            try:
                notes = fetch_safari_release_notes_index()
            except Exception:
                notes = []

            # Group items by major_version
            groups = defaultdict(list)
            for it in notes:
                groups[it.get("major_version")].append(it)

            def numeric_key(vstr):
                m = re.search(r'([0-9]+(?:\.[0-9]+)*)', (vstr or ""))
                if not m:
                    return ()
                return tuple(int(p) for p in m.group(1).split('.'))

            # For each major, choose highest non-beta; also include beta items
            for major, items in groups.items():
                non_beta = [i for i in items if not re.search(r'\bbeta\b', i.get("version",""), re.I)]
                chosen = None
                if non_beta:
                    chosen = max(non_beta, key=lambda x: numeric_key(x.get("version","")))
                else:
                    # fallback to highest including beta if no non-beta present
                    chosen = max(items, key=lambda x: numeric_key(x.get("version","")))

                # collect final list: chosen non-beta + any beta items (if present and not same as chosen)
                selected = []
                if chosen:
                    selected.append(chosen)
                betas = [i for i in items if re.search(r'\bbeta\b', i.get("version",""), re.I)]
                for b in betas:
                    # avoid duplicate if chosen is the same
                    if b is not chosen:
                        selected.append(b)

                # append each selected release as <release> under new_root
                for sel in selected:
                    rel = ET.SubElement(new_root, 'release')
                    mv = ET.SubElement(rel, 'major_version')
                    mv.text = str(sel.get('major_version',''))
                    fv = ET.SubElement(rel, 'full_version')
                    fv.text = str(sel.get('version',''))
                    rd = ET.SubElement(rel, 'released')
                    rd.text = str(sel.get('released',''))
                    # ensure release_notes element contains the URL when available
                    rn = ET.SubElement(rel, 'release_notes')
                    rn.text = str(sel.get('release_notes_url') or sel.get('release_notes',''))

            # normalize whitespace to avoid extra blank lines
            def _strip_whitespace(node):
                if node.text is not None and node.text.strip() == "":
                    node.text = None
                if node.tail is not None and node.tail.strip() == "":
                    node.tail = None
                for c in list(node):
                    _strip_whitespace(c)
            _strip_whitespace(new_root)

            # pretty-print and export
            pretty_raw = minidom.parseString(ET.tostring(new_root, encoding='utf-8')).toprettyxml(indent="  ")
            latest_xml = "\n".join([ln for ln in pretty_raw.splitlines() if ln.strip() != ""])
            export_to_file(latest_xml, 'latest_safari_files/safari_latest_versions.xml')

            latest_json = xml_to_json(latest_xml)
            if latest_json:
                export_to_file(latest_json, 'latest_safari_files/safari_latest_versions.json')
            latest_yaml = xml_to_yaml(latest_xml)
            if latest_yaml:
                export_to_file(latest_yaml, 'latest_safari_files/safari_latest_versions.yaml')
        except Exception as e:
            logging.warning(f"failed to extract Safari_Technology_Preview entries or add selected releases: {e}")

    # NEW: fetch Safari release-notes index and write top item per major version
    try:
        notes = fetch_safari_release_notes_index()
        if notes:
            os.makedirs('latest_safari_files', exist_ok=True)
            # write real XML instead of JSON-in-XML
            xml_out = notes_to_xml(notes)
            export_to_file(xml_out, 'latest_safari_files/safari_all_history.xml')
            # NEW: also write JSON and YAML representations
            export_to_file(json.dumps(notes, indent=2), 'latest_safari_files/safari_all_history.json')
            export_to_file(yaml.dump(notes, default_flow_style=False, sort_keys=False), 'latest_safari_files/safari_all_history.yaml')
            # Log a short, simple summary for each history item
            for item in notes:
                mv = item.get("major_version")
                title = item.get("title") or item.get("release_notes")
                released = item.get("released") or ""
                version = item.get("version") or ""
                logging.info(f"History: {mv} — {title} — {version} — {released}")
    except Exception as e:
        logging.warning(f"failed to fetch release-notes index: {e}")

