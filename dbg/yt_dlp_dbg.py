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
            "default_search": "ytsearch",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            if "entries" in info:
                self.playlist = [(entry["title"], entry["url"]) for entry in info["entries"] if entry]
        
        self.current_index = 0  # Reset to first song
        return self.playlist

    def get_audio_url(self, video_url):
        """Extract the highest quality audio URL using yt-dlp."""
        command = [
            "yt-dlp",
            "-f", "bestaudio/best",  # 최고 음질 선택
            "--audio-quality", "0",  # 최고 비트레이트 적용
            "--get-url",
            "--no-playlist",
            "--extractor-args", "youtube:skip=hls,dash",
            video_url
        ]

        try:
            process = subprocess.run(command, capture_output=True, text=True, check=True)
            return process.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"❌ Error fetching audio URL: {e}")
            return None

    def play_current(self):
        """Play the current video in the playlist with highest quality audio."""
        if not self.playlist or self.current_index < 0 or self.current_index >= len(self.playlist):
            print("No video to play.")
            return

        title, url = self.playlist[self.current_index]
        print(f"🎵 Playing ({self.current_index + 1}/{len(self.playlist)}): {title}")

        # Get highest quality audio URL
        audio_url = self.get_audio_url(url)
        if not audio_url:
            print("❌ Failed to extract audio URL.")
            return

        print(f"🔊 Streaming: {title}")

        # Play using mpv with highest audio quality
        subprocess.run(["mpv", "--no-video", "--cache=no", audio_url])

    def play_next(self):
        """Move to the next video and play."""
        if self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.play_current()
        else:
            print("🔚 End of playlist reached.")

    def play_prev(self):
        """Move to the previous video and play."""
        if self.current_index > 0:
            self.current_index -= 1
            self.play_current()
        else:
            print("🔙 Already at the first song.")

# Example Usage
if __name__ == "__main__":
    playlist = YouTubePlaylist()
    query = "k-pop girl"
    print(f"🔍 Searching for: {query}")
    
    results = playlist.search_youtube(query, max_results=10)
    if results:
        print("🎶 Playlist created!")
        playlist.play_current()

        while True:
            cmd = input("\n▶ [n] Next, [p] Previous, [q] Quit: ").strip().lower()
            if cmd == "n":
                playlist.play_next()
            elif cmd == "p":
                playlist.play_prev()
            elif cmd == "q":
                print("👋 Exiting music player.")
                break
    else:
        print("❌ No results found.")
