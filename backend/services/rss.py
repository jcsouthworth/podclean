"""RSS parsing and feed generation."""
import os
import re
from datetime import datetime, timezone
from email.utils import format_datetime

import feedparser
from lxml import etree


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def fetch_podcast_metadata(rss_url: str) -> dict:
    """Fetch an RSS URL and return {name, artwork, description, author} from the channel."""
    feed = feedparser.parse(rss_url)
    channel = feed.feed if feed.feed else {}

    name = channel.get("title", "Unknown Podcast")

    # feedparser normalises both <itunes:image href="..."> and <image><url>...</url>
    # into the same `image` key. `href` comes from iTunes, `url` from standard RSS.
    artwork = None
    img = channel.get("image") or {}
    if hasattr(img, "get"):
        artwork = img.get("href") or img.get("url")

    description = (
        channel.get("summary")
        or channel.get("description")
        or channel.get("subtitle")
    )

    author = (
        channel.get("itunes_author")
        or channel.get("author")
        or channel.get("publisher")
    )

    return {"name": name, "artwork": artwork, "description": description, "author": author}


def generate_feed_xml(podcast, episodes: list, app_base_url: str) -> str:
    """
    Build an RSS 2.0 XML document for the processed episodes of a podcast.
    Items are constructed from Episode model fields since source_rss_entry is
    not populated (feedparser does not expose per-entry raw XML).
    """
    ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"

    rss = etree.Element("rss", attrib={"version": "2.0"}, nsmap={"itunes": ITUNES_NS})
    channel = etree.SubElement(rss, "channel")
    etree.SubElement(channel, "title").text = podcast.name
    etree.SubElement(channel, "link").text = podcast.rss_url

    ad_free_note = "Ad-free version processed by PodClean."
    original_desc = podcast.description or podcast.name
    etree.SubElement(channel, "description").text = f"{ad_free_note} {original_desc}"

    etree.SubElement(channel, "language").text = "en"

    if podcast.author:
        etree.SubElement(channel, f"{{{ITUNES_NS}}}author").text = podcast.author

    if podcast.artwork_url:
        etree.SubElement(
            channel, f"{{{ITUNES_NS}}}image", attrib={"href": podcast.artwork_url}
        )
        img_el = etree.SubElement(channel, "image")
        etree.SubElement(img_el, "url").text = podcast.artwork_url
        etree.SubElement(img_el, "title").text = podcast.name
        etree.SubElement(img_el, "link").text = podcast.rss_url

    for ep in episodes:
        audio_url = (
            f"{app_base_url.rstrip('/')}"
            f"/feeds/{podcast.feed_slug}/episodes/{ep.id}/audio.mp3"
        )

        # Try to get actual file size for the enclosure length attribute
        file_size = 0
        if ep.processed_file and os.path.exists(ep.processed_file):
            try:
                file_size = os.path.getsize(ep.processed_file)
            except OSError:
                pass

        item = etree.SubElement(channel, "item")
        etree.SubElement(item, "title").text = ep.title
        etree.SubElement(item, "guid", attrib={"isPermaLink": "false"}).text = ep.guid
        etree.SubElement(item, "link").text = ep.source_url

        if ep.published_at:
            pub = ep.published_at.replace(tzinfo=timezone.utc) if ep.published_at.tzinfo is None else ep.published_at
            etree.SubElement(item, "pubDate").text = format_datetime(pub)

        etree.SubElement(item, "enclosure", attrib={
            "url": audio_url,
            "type": "audio/mpeg",
            "length": str(file_size),
        })

        if ep.duration_ms:
            total_secs = ep.duration_ms // 1000
            h, remainder = divmod(total_secs, 3600)
            m, s = divmod(remainder, 60)
            duration_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
            etree.SubElement(item, f"{{{ITUNES_NS}}}duration").text = duration_str

    xml_bytes = etree.tostring(
        rss,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )
    xml_str = xml_bytes.decode("utf-8")
    xml_str = xml_str.replace(
        "?>\n",
        "?>\n<!-- Processed by PodClean: advertisements marked/removed -->\n",
        1,
    )
    return xml_str
