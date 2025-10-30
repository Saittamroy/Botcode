"""
Highrise Radio Bot - Direct AzuraCast API Integration
No SDK required - uses aiohttp directly
"""

from highrise import BaseBot
from highrise.models import User, Position
import aiohttp
import asyncio
from typing import Dict, List, Optional
import os


class DirectRadioBot(BaseBot):
    """Highrise bot that directly calls AzuraCast API"""
    
    def __init__(self):
        super().__init__()
        self.base_url = ""
        self.api_key = ""
        self.station_id = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self.cooldowns: Dict[str, float] = {}
        self.cooldown_time = 30
        
    async def on_start(self, session_metadata: dict) -> None:
        """Initialize bot and API connection"""
        print("🎵 Direct Radio Bot starting...")
        
        # Load config from environment
        self.base_url = os.getenv('AZURACAST_URL', '').rstrip('/')
        self.api_key = os.getenv('AZURACAST_API_KEY', '')
        self.station_id = int(os.getenv('AZURACAST_STATION_ID', '1'))
        
        if not self.base_url or not self.api_key:
            print("❌ Missing AZURACAST_URL or AZURACAST_API_KEY")
            return
        
        # Create HTTP session
        self.session = aiohttp.ClientSession(
            headers={
                'X-API-Key': self.api_key,
                'Accept': 'application/json'
            }
        )
        
        print(f"✅ Connected to {self.base_url}")
        
        # Start now playing announcer
        asyncio.create_task(self.announce_now_playing())
    
    async def api_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        Make API request to AzuraCast
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/nowplaying/1')
            **kwargs: Additional aiohttp arguments
        
        Returns:
            JSON response as dictionary or None on error
        """
        if not self.session:
            print("❌ Session not initialized")
            return None
        
        url = f"{self.base_url}/api{endpoint}"
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"API Error: {response.status} - {await response.text()}")
                    return None
        except aiohttp.ClientError as e:
            print(f"Connection error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    async def get_now_playing(self) -> Optional[Dict]:
        """Get currently playing track"""
        return await self.api_request('GET', f'/nowplaying/{self.station_id}')
    
    async def get_requestable_songs(self) -> Optional[List[Dict]]:
        """Get list of requestable songs"""
        return await self.api_request('GET', f'/station/{self.station_id}/requests')
    
    async def request_song(self, request_id: str) -> Optional[Dict]:
        """Request a song to be played"""
        return await self.api_request(
            'POST',
            f'/station/{self.station_id}/request/{request_id}'
        )
    
    async def get_station_info(self) -> Optional[Dict]:
        """Get station information"""
        return await self.api_request('GET', f'/station/{self.station_id}')
    
    async def search_songs(self, query: str) -> List[Dict]:
        """Search requestable songs"""
        songs = await self.get_requestable_songs()
        if not songs:
            return []
        
        query_lower = query.lower()
        results = []
        
        for song in songs:
            song_data = song.get('song', {})
            title = song_data.get('title', '').lower()
            artist = song_data.get('artist', '').lower()
            
            if query_lower in title or query_lower in artist:
                results.append(song)
        
        return results
    
    async def on_chat(self, user: User, message: str) -> None:
        """Handle chat messages"""
        msg = message.strip()
        
        try:
            if msg.lower() in ['!radio', '!help', '!commands']:
                await self.send_help()
            
            elif msg.lower() in ['!np', '!nowplaying', '!playing']:
                await self.show_now_playing()
            
            elif msg.lower().startswith('!request ') or msg.lower().startswith('!req '):
                query = msg.split(' ', 1)[1] if len(msg.split(' ', 1)) > 1 else ''
                await self.handle_request(user, query)
            
            elif msg.lower().startswith('!search '):
                query = msg.split(' ', 1)[1] if len(msg.split(' ', 1)) > 1 else ''
                await self.handle_search(query)
            
            elif msg.lower() in ['!queue', '!q']:
                await self.show_queue()
            
            elif msg.lower() in ['!history', '!recent']:
                await self.show_history()
            
            elif msg.lower() in ['!listeners', '!listen']:
                await self.show_listeners()
            
            elif msg.lower() in ['!station', '!info']:
                await self.show_station_info()
        
        except Exception as e:
            await self.highrise.chat(f"❌ Error: {str(e)}")
            print(f"Command error: {e}")
    
    async def send_help(self):
        """Send help message"""
        help_text = """
🎵 Radio Bot Commands:
!np - Now playing
!request <song> - Request a song
!search <query> - Search songs
!queue - Show queue
!history - Recent tracks
!listeners - Listener count
!station - Station info
        """.strip()
        await self.highrise.chat(help_text)
    
    async def show_now_playing(self):
        """Display currently playing song"""
        data = await self.get_now_playing()
        if not data:
            await self.highrise.chat("❌ Couldn't get now playing info")
            return
        
        song = data.get('now_playing', {}).get('song', {})
        title = song.get('title', 'Unknown')
        artist = song.get('artist', 'Unknown')
        
        await self.highrise.chat(f"🎵 Now Playing: {artist} - {title}")
    
    async def handle_request(self, user: User, query: str):
        """Handle song request"""
        username = user.username
        
        # Check cooldown
        current_time = asyncio.get_event_loop().time()
        if username in self.cooldowns:
            time_left = self.cooldown_time - (current_time - self.cooldowns[username])
            if time_left > 0:
                await self.highrise.chat(
                    f"⏱️ @{username}, wait {int(time_left)}s before requesting again"
                )
                return
        
        if not query:
            await self.highrise.chat("❌ Usage: !request <song name>")
            return
        
        # Search for song
        songs = await self.search_songs(query)
        
        if not songs:
            await self.highrise.chat(f"❌ No songs found matching '{query}'")
            return
        
        # Request first match
        song = songs[0]
        song_data = song.get('song', {})
        request_id = song.get('request_id')
        
        if not request_id:
            await self.highrise.chat("❌ This song cannot be requested")
            return
        
        result = await self.request_song(request_id)
        
        if result:
            title = song_data.get('title', 'Unknown')
            artist = song_data.get('artist', 'Unknown')
            await self.highrise.chat(f"✅ @{username} requested: {artist} - {title}")
            self.cooldowns[username] = current_time
        else:
            await self.highrise.chat("❌ Request failed")
    
    async def handle_search(self, query: str):
        """Handle search command"""
        if not query:
            await self.highrise.chat("❌ Usage: !search <song name>")
            return
        
        songs = await self.search_songs(query)
        
        if not songs:
            await self.highrise.chat(f"❌ No songs found matching '{query}'")
            return
        
        # Show first 3 results
        results = []
        for i, song in enumerate(songs[:3], 1):
            song_data = song.get('song', {})
            title = song_data.get('title', 'Unknown')
            artist = song_data.get('artist', 'Unknown')
            results.append(f"{i}. {artist} - {title}")
        
        message = f"🔍 Found {len(songs)} songs:\n" + "\n".join(results)
        if len(songs) > 3:
            message += f"\n... and {len(songs) - 3} more"
        
        await self.highrise.chat(message)
    
    async def show_queue(self):
        """Show upcoming queue"""
        data = await self.get_now_playing()
        if not data:
            await self.highrise.chat("❌ Couldn't get queue")
            return
        
        playing_next = data.get('playing_next', {})
        if not playing_next:
            await self.highrise.chat("📋 Queue is empty")
            return
        
        song = playing_next.get('song', {})
        title = song.get('title', 'Unknown')
        artist = song.get('artist', 'Unknown')
        
        await self.highrise.chat(f"📋 Up Next: {artist} - {title}")
    
    async def show_history(self):
        """Show recent tracks"""
        data = await self.get_now_playing()
        if not data:
            await self.highrise.chat("❌ Couldn't get history")
            return
        
        history = data.get('song_history', [])[:3]
        
        if not history:
            await self.highrise.chat("📜 No history available")
            return
        
        tracks = []
        for i, item in enumerate(history, 1):
            song = item.get('song', {})
            title = song.get('title', 'Unknown')
            artist = song.get('artist', 'Unknown')
            tracks.append(f"{i}. {artist} - {title}")
        
        message = "📜 Recently Played:\n" + "\n".join(tracks)
        await self.highrise.chat(message)
    
    async def show_listeners(self):
        """Show listener count"""
        data = await self.get_now_playing()
        if not data:
            await self.highrise.chat("❌ Couldn't get listeners")
            return
        
        listeners = data.get('listeners', {}).get('current', 0)
        await self.highrise.chat(f"👥 Current Listeners: {listeners}")
    
    async def show_station_info(self):
        """Show station information"""
        data = await self.get_station_info()
        if not data:
            await self.highrise.chat("❌ Couldn't get station info")
            return
        
        name = data.get('name', 'Unknown Station')
        description = data.get('description', 'No description')
        
        await self.highrise.chat(f"📻 {name}\n{description}")
    
    async def announce_now_playing(self):
        """Periodically announce now playing"""
        await asyncio.sleep(60)  # Wait before first announcement
        
        last_song_id = None
        
        while True:
            try:
                data = await self.get_now_playing()
                if data:
                    song = data.get('now_playing', {}).get('song', {})
                    song_id = song.get('id')
                    
                    if song_id and song_id != last_song_id:
                        title = song.get('title', 'Unknown')
                        artist = song.get('artist', 'Unknown')
                        await self.highrise.chat(f"🎵 Now Playing: {artist} - {title}")
                        last_song_id = song_id
            except Exception as e:
                print(f"Announcement error: {e}")
            
            await asyncio.sleep(300)  # Announce every 5 minutes
    
    async def on_user_join(self, user: User, position: Position) -> None:
        """Welcome new users"""
        await self.highrise.chat(f"👋 Welcome @{user.username}! Type !radio for commands")
    
    async def on_stop(self) -> None:
        """Cleanup when bot stops"""
        if self.session:
            await self.session.close()
        print("Bot stopped")


if __name__ == "__main__":
    from highrise import __main__
    from highrise.__main__ import BotDefinition

    API_TOKEN = os.environ.get("HIGHRISE_API_TOKEN")
    ROOM_ID = os.environ.get("HIGHRISE_ROOM_ID")

    if not API_TOKEN or not ROOM_ID:
        print("❌ Set HIGHRISE_API_TOKEN and HIGHRISE_ROOM_ID environment variables")
        exit(1)

    bot = VirtualMallBot()
    bot_definition = BotDefinition(bot, ROOM_ID, API_TOKEN)

    try:
        asyncio.run(__main__.main([bot_definition]))
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        # Save all data before exiting
        asyncio.run(bot.save_all_data())
    except Exception as e:
        print(f"💥 Bot crashed: {e}")
        # Save all data before crashing
        asyncio.run(bot.save_all_data())
