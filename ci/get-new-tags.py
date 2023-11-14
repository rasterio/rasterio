from datetime import datetime, timezone
import json
import sys
import xml.etree.ElementTree as ET

_, filename, nhours = sys.argv
nhours = float(nhours)
now = datetime.now(timezone.utc)

with open(filename) as f:
    text = f.read()

feed = ET.fromstring(text)
tags = []

for entry in feed.iterfind("{http://www.w3.org/2005/Atom}entry"):
    updated = entry.find("{http://www.w3.org/2005/Atom}updated").text
    delta = now - datetime.fromisoformat(updated)
    deltah = delta.days * 24 + delta.seconds / 3600
    if deltah <= nhours:
        tid = entry.find("{http://www.w3.org/2005/Atom}id").text
        tag = tid.split("/")[-1]
        tags.append(tag)

print(json.dumps(tags))
