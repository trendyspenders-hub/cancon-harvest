# Topic Harvest as a Claude Desktop tool (MCP)

Turns the harvest into three tools Claude can call in chat:
**start_harvest** · **stop_harvest** · **harvest_status** · **get_results**

## Setup (Mac)

```bash
pip3 install "mcp<2" yt-dlp
```

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(create it if it doesn't exist):

```json
{
  "mcpServers": {
    "cancon-harvest": {
      "command": "python3",
      "args": ["/Users/YOU/Downloads/topic-harvest/mcp/server.py"]
    }
  }
}
```

Fully restart Claude Desktop. The hammer/tools icon should now list
`cancon-harvest`.

## Use

Just talk to it:

- "start the harvest" — begins walking all 17,030 artists (resumes if stopped)
- "how's the harvest going?" — progress, current artist, tracks found
- "stop the harvest" — halts cleanly after the current artist
- "where are the results?" — path to `tracks_local.jsonl`

Results accumulate in `topic-harvest/tracks_local.jsonl`. Upload that file
to your CanCon Radio session (Kimi) to verify + merge into the player.

## Notes

- Requires Python 3.10+ and `yt-dlp` on the machine Claude Desktop runs on.
- Only each artist's own `… - Topic` channel is kept.
- Harvest continues even while you chat about other things; it stops if
  Claude Desktop quits — just say "start the harvest" again to resume.
