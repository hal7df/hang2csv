# hang2csv

Python script to convert Hangouts JSON data exported from
[Google Takeout](https://takeout.google.com) into a more user-friendly CSV
format. Chats are sorted in chronological order, although you can reverse the
order using the `-z` switch.

At present, hang2csv only supports Python 2.7.

## Usage

```
python hang2csv.py [-z] <Hangouts.json>
```
Or, if Python is in your `PATH`:
```
./hang2csv.py [-z] <Hangouts.json>
```

The JSON file should be named `Hangouts.json` in the ZIP file, but any JSON file
that uses the same structure can be passed as the last argument.

## Output

The JSON file contains all of your Hangouts chats, so this tool splits up each
chat into a separate file. If the chat is named, the file will have the same
name as the chat (without special characters). If the chat is unnamed, all of
the chat participants' names will appear in the filename.

## Why are some chat participants' names missing?

Sometimes, the participants' nicknames are not stored with the chat data, so the
only identifier is the numeric ID assigned by Google. See
[here](https://blog.jay2k1.com/2014/11/10/how-to-export-and-backup-your-google-hangouts-chat-history/#FAQ).
