import yt_dlp
import subprocess

class YouTubePlaylist:
    def __init__(self):
        self.playlist = []
        self.current_index = -1  # Start before the first song

    def search_youtube(self, query, max_results=10):
        """Search YouTube and create a playlist of video titles and URLs."""
        search_query = f"ytsearch{max_results}:music {query}"
        
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,  # Get URLs only
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            if "entries" in info:
                self.playlist = [(entry["title"], entry["url"]) for entry in info["entries"] if entry]
                print(self.playlist)
        
        self.current_index = 0  # Reset to first song
        return self.playlist

    def play_current(self):
        """Play the current video in the playlist."""
        if not self.playlist or self.current_index < 0 or self.current_index >= len(self.playlist):
            print("No video to play.")
            return

        title, url = self.playlist[self.current_index]
        print(f"Playing ({self.current_index + 1}/{len(self.playlist)}): {title}")

        # Play using mpv (you can switch to another player)
        print(f"playing: {url}")
        subprocess.run(["mpv", "--no-video", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def play_next(self):
        """Move to the next video and play."""
        if self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.play_current()
        else:
            print("End of playlist reached.")

    def play_prev(self):
        """Move to the previous video and play."""
        if self.current_index > 0:
            self.current_index -= 1
            self.play_current()
        else:
            print("Already at the first song.")

# Example Usage
if __name__ == "__main__":
    playlist = YouTubePlaylist()
    query = "color of the night"
    print("Searching for:", query)
    
    results = playlist.search_youtube(query, max_results=20)
    if results:
        print("Playlist created!")
        playlist.play_current()

        # Example controls
        input("Press Enter for next...")
        playlist.play_next()

        input("Press Enter for previous...")
        playlist.play_prev()
    else:
        print("No results found.")
