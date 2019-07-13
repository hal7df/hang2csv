#!/usr/bin/env python

"""
Copyright 2019 Paul Bonnen

Licensed (except where otherwise noted) under the Apache License,
Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import sys
import json
import csv
import urllib.parse
import codecs
from datetime import datetime
from operator import itemgetter

def printImm (s):
    sys.stdout.write(s)
    sys.stdout.flush()

def getGroupName (conv):
    name = ""
    if conv["type"] == "GROUP" and "name" in conv:
        if "name" in conv:
            name = conv["name"]
    else:
        for participant in conv["participant_data"]:
            if len(name) > 0:
                name += ", "

            name += participant["fallback_name"] if "fallback_name" in participant else participant["id"]["gaia_id"]

    return name

def getParticipants (conv):
    participants = []

    for p in conv["participant_data"]:
        participant = {}
        participant["id"] = p["id"]["gaia_id"]

        if "fallback_name" in p:
            participant["name"] = p["fallback_name"]

        participants.append(participant)

    return participants

def getParticipant (p, pid):
    return next((x for x in p if x["id"] == pid), None)

def getEventType (event):
    evType = {
        "REGULAR_CHAT_MESSAGE": "msg",
        "RENAME_CONVERSATION": "rename",
        "HANGOUT_EVENT": "call",
        "ADD_USER": "add member(s)",
        "REMOVE_USER": "remove member(s)"
    }.get(event["event_type"], "unknown")

    if evType != "msg":
        return evType

    evType = ""
    contents = event["chat_message"]["message_content"]

    if "segment" in contents:
        evType += "txt"

    if "attachment" in contents:

        for attachment in contents["attachment"]:
            atype = attachment["embed_item"]["type"]
            if len(evType) > 0:
                evType += "+"

            if "PLUS_PHOTO" in atype:
                evType += "img"
            elif "PLACE_V2" in atype:
                evType += "loc"
            else:
                evType += "unk"

    return evType

def formatText (s, opts):
    if opts["bold"]:
        s = "**" + s + "**"

    if opts["italics"]:
        s = "*" + s + "*"

    if opts["strikethrough"]:
        s = "~" + s + "~"

    if opts["underline"]:
        s = "_" + s + "_"

    return s

def flattenSegments (segments):
    parts = []

    for segment in segments:
        if segment["type"] == "TEXT" or segment["type"] == "LINK":
            parts.append(formatText(segment["text"], segment["formatting"]) if "formatting" in segment else segment["text"])
        elif segment["type"] == "LINE_BREAK":
            parts.append("\\n")

    return "".join(parts)

def getContents (event, event_type, participants):
    contentParts = []

    if "txt" in event_type:
        contentParts.append(flattenSegments(event["chat_message"]["message_content"]["segment"]))
        
    if "img" in event_type or "loc" in event_type:
        for attachment in event["chat_message"]["message_content"]["attachment"]:
            item = attachment["embed_item"]
            
            if "PLUS_PHOTO" in item["type"]:
                name = urllib.parse.unquote(item["plus_photo"]["url"].split("/")[-1])
                img = urllib.parse.unquote(name)

                if "txt" in event_type:
                    contentParts.append(" (sent photo: " + img + ")")
                elif len(contentParts) > 0:
                    contentParts.append(", " + img)
                else:
                    contentParts.append(img)
            elif "PLACE_V2" in item["type"]:
                url = item["place_v2"]["url"]
                name = item["place_v2"]["name"]
                address = item["place_v2"]["address"]["postal_address_v2"]
                addressStr = address["name"] if "name" in address else address["street_address"]

                combined = name + " - " + addressStr + " (" + url + ')'

                if len(contentParts) > 0: combined = ", " + combined
                contentParts.append(combined)

    if event_type == "rename":
        rename = event["conversation_rename"]
        contentParts.append("Renamed from \"" + rename["old_name"] + "\" to \"" + rename["new_name"] + "\"")

    elif event_type == "call":
        details = event["hangout_event"]

        if details["event_type"] == "START_HANGOUT":
            if "media_type" in details and details["media_type"] == "AUDIO_VIDEO":
                contentParts.append("Started video call")
            elif "media_type" in details and details["media_type"] == "AUDIO_ONLY":
                contentParts.append("Started audio call")
            else:
                contentParts.append("Started call")
        elif details["event_type"] == "END_HANGOUT":
            duration = int(details["hangout_duration_secs"])

            mins = duration // 60
            secs = duration % 60

            descStr = ""

            if mins > 0:
                descStr = "Call ended in {} mins {} secs".format(mins, secs)
            else:
                descStr = "Call ended in {} secs".format(secs)

            contentParts.append(descStr)

    elif "member" in event_type:
        change = event["membership_change"]

        for participant in change["participant_id"]:
            affected = getParticipant(participants, participant["gaia_id"])
            affected = {"name": "Unknown"} if affected == None else affected

            if len(contentParts) > 0:
                contentParts.append(", ")

            contentParts.append(affected["name"] if "name" in affected else affected["id"])
    
    return "".join(contentParts)

def simplifyEvent (e, participants):
    event = {}
    sender = getParticipant(participants, e["sender_id"]["gaia_id"])

    sender = {"name": "Unknown"} if sender == None else sender

    event["sender"] = sender["name"] if "name" in sender else sender["id"]
    event["timestamp"] = datetime.fromtimestamp(e["timestamp_int"] // (10 ** 6)).strftime("%Y-%m-%d %H:%M:%S")
    event["type"] = getEventType(e)
    event["content"] = getContents(e, event["type"], participants)

    return event

def sanitizeFilename (name):
    name = name.replace(", ", "-")
    name = name.replace(",", "-")
    name = name.replace("/", "-")
    return name


desc = False

if len(sys.argv) == 3:
    if sys.argv[1] != "-a" and sys.argv[1] != "-z":
        print("Unknown option", sys.argv[1])

    desc = True if sys.argv[1] == "-z" else False

fname = sys.argv[2] if len(sys.argv) == 3 else sys.argv[1]

printImm("Loading data from {} (this may take some time)...".format(fname))
data = json.load(open(fname, "r"))["conversations"]
printImm("done\n")

print("Found", len(data), "conversations")
convNum = 1

for conversation in data:
    cdata = conversation["conversation"]["conversation"]
    name = getGroupName(cdata)
    participants = getParticipants(cdata)
    fname = sanitizeFilename(name) + ".csv"

    print("\nProcessing conversation {} ({}/{})".format(name, convNum, len(data)))

    for event in conversation["events"]:
        event["timestamp_int"] = int(event["timestamp"])

    events = sorted(conversation["events"], key=itemgetter("timestamp_int"), reverse=desc)

    printImm("Writing history for conversation '{}' to {}...".format(name, fname))

    with open(fname, "w") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["Sender", "Timestamp", "Type", "Content"])

        for event in events:
            simple = simplifyEvent(event, participants)
            writer.writerow([simple["sender"], simple["timestamp"], simple["type"], simple["content"]])

    printImm("done\n")
    convNum += 1;

print("\nFinished")


