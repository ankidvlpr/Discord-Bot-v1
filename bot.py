"""
RentAHuman Discord Bounty Bot - Deployable Version
Works with BOTH mock API (for testing) and real API (for production)
NO API KEY REQUIRED for mock mode
"""

import os
import asyncio
import aiohttp
import aiosqlite
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

import discord
from discord import app_commands
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# ============== CONFIGURATION ==============

@dataclass
class Config:
    """Bot configuration with validation"""
    discord_token: str
    api_url: str
    api_key: Optional[str] = None  # Optional for mock API
    poll_interval: int = 60
    api_timeout: int = 10
    max_retries: int = 3
    db_path: str = "bot.db"
    use_mock_api: bool = False
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load and validate config from environment"""
        token = os.getenv("DISCORD_TOKEN")
        api_url = os.getenv("API_URL", "http://localhost:8000/bounties")
        api_key = os.getenv("API_KEY")  # Optional
        use_mock = os.getenv("USE_MOCK_API", "true").lower() == "true"
        
        if not token:
            raise ValueError("DISCORD_TOKEN environment variable not set")
            
        return cls(
            discord_token=token,
            api_url=api_url,
            api_key=api_key,
            use_mock_api=use_mock
        )

config = Config.from_env()

# ============== LOGGING ==============

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== DATABASE ==============

class Database:
    """Async database handler"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Initialize database connection and create tables"""
        self.db = await aiosqlite.connect(self.db_path)
        await self._create_tables()
        logger.info("Database connected and initialized")
    
    async def _create_tables(self):
        """Create database schema"""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                keyword TEXT NOT NULL,
                UNIQUE(guild_id, keyword)
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS processed_bounties (
                bounty_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.db.commit()
    
    async def close(self):
        """Close database connection"""
        if self.db:
            await self.db.close()
            logger.info("Database connection closed")
    
    async def set_channel(self, guild_id: str, channel_id: str):
        """Set notification channel for guild"""
        await self.db.execute(
            "INSERT OR REPLACE INTO guild_settings (guild_id, channel_id) VALUES (?, ?)",
            (guild_id, channel_id)
        )
        await self.db.commit()
    
    async def get_channel(self, guild_id: str) -> Optional[str]:
        """Get notification channel for guild"""
        async with self.db.execute(
            "SELECT channel_id FROM guild_settings WHERE guild_id = ?",
            (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None
    
    async def get_all_guilds(self) -> List[tuple]:
        """Get all guilds with their channels"""
        async with self.db.execute(
            "SELECT guild_id, channel_id FROM guild_settings"
        ) as cursor:
            return await cursor.fetchall()
    
    async def add_subscription(self, guild_id: str, keyword: str) -> bool:
        """Add keyword subscription, returns False if already exists"""
        try:
            await self.db.execute(
                "INSERT INTO subscriptions (guild_id, keyword) VALUES (?, ?)",
                (guild_id, keyword)
            )
            await self.db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False
    
    async def remove_subscription(self, guild_id: str, keyword: str):
        """Remove keyword subscription"""
        await self.db.execute(
            "DELETE FROM subscriptions WHERE guild_id = ? AND keyword = ?",
            (guild_id, keyword)
        )
        await self.db.commit()
    
    async def get_subscriptions(self, guild_id: str) -> List[str]:
        """Get all keywords for a guild"""
        async with self.db.execute(
            "SELECT keyword FROM subscriptions WHERE guild_id = ?",
            (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    async def is_bounty_processed(self, bounty_id: str) -> bool:
        """Check if bounty has been processed"""
        async with self.db.execute(
            "SELECT 1 FROM processed_bounties WHERE bounty_id = ?",
            (bounty_id,)
        ) as cursor:
            return await cursor.fetchone() is not None
    
    async def mark_bounty_processed(self, bounty_id: str):
        """Mark bounty as processed"""
        await self.db.execute(
            "INSERT OR IGNORE INTO processed_bounties (bounty_id) VALUES (?)",
            (bounty_id,)
        )
        await self.db.commit()

# ============== API CLIENT ==============

class BountyAPI:
    """API client that works with both mock and real APIs"""
    
    def __init__(self, api_url: str, api_key: Optional[str] = None, timeout: int = 10):
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.use_auth = api_key is not None
    
    @retry(
        stop=stop_after_attempt(config.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        before_sleep=lambda retry_state: logger.warning(
            f"API request failed, retrying... (attempt {retry_state.attempt_number})"
        )
    )
    async def fetch_bounties(self, page: int = 1, per_page: int = 50) -> List[Dict]:
        """Fetch bounties with pagination and retry logic"""
        headers = {"Accept": "application/json"}
        
        # Add auth header if API key is provided
        if self.use_auth:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        params = {
            "page": page,
            "per_page": per_page
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    self.api_url,
                    headers=headers,
                    params=params
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Handle different API response structures
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict):
                            # Check for common response keys
                            for key in ['bounties', 'data', 'results', 'items']:
                                if key in data:
                                    return data[key]
                            # If no known key, return empty list
                            logger.warning(f"Unexpected API response structure: {list(data.keys())}")
                            return []
                        return []
                        
                    elif resp.status == 401:
                        logger.error("API authentication failed - check your API key")
                        return []
                    elif resp.status == 429:
                        logger.warning("API rate limit hit, backing off...")
                        raise aiohttp.ClientError("Rate limit exceeded")
                    else:
                        logger.error(f"API error: {resp.status}")
                        return []
                        
        except asyncio.TimeoutError:
            logger.error(f"API request timed out after {config.api_timeout}s")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"API client error: {e}")
            raise

# ============== DISCORD BOT ==============

class BountyBot(discord.Client):
    """Discord bot for bounty notifications"""
    
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.db = Database(config.db_path)
        self.api = BountyAPI(config.api_url, config.api_key, config.api_timeout)
        self.poller_task: Optional[asyncio.Task] = None
    
    async def setup_hook(self):
        """Initialize bot resources"""
        await self.db.connect()
        
        # Log configuration
        mode = "MOCK" if config.use_mock_api else "PRODUCTION"
        logger.info(f"Bot configured in {mode} mode")
        logger.info(f"API URL: {config.api_url}")
        logger.info("Bot setup complete")
    
    async def on_ready(self):
        """Bot ready event"""
        await self.tree.sync()
        logger.info(f"Logged in as {self.user}")
        
        # Start polling task
        if not self.poller_task or self.poller_task.done():
            self.poller_task = self.loop.create_task(self.poll_bounties())
            logger.info("Bounty polling started")
    
    async def close(self):
        """Cleanup on shutdown"""
        if self.poller_task:
            self.poller_task.cancel()
        await self.db.close()
        await super().close()
        logger.info("Bot shutdown complete")
    
    async def poll_bounties(self):
        """Main polling loop"""
        await self.wait_until_ready()
        
        while not self.is_closed():
            try:
                logger.info("Fetching new bounties...")
                bounties = await self.api.fetch_bounties()
                logger.info(f"Retrieved {len(bounties)} bounties")
                
                for bounty in bounties:
                    await self.process_bounty(bounty)
                
            except Exception as e:
                logger.error(f"Polling error: {e}", exc_info=True)
            
            await asyncio.sleep(config.poll_interval)
    
    async def process_bounty(self, bounty: Dict):
        """Process a single bounty"""
        bounty_id = str(bounty.get("id", ""))
        
        if not bounty_id:
            logger.warning("Bounty missing ID, skipping")
            return
        
        # Skip if already processed
        if await self.db.is_bounty_processed(bounty_id):
            return
        
        # Mark as processed immediately
        await self.db.mark_bounty_processed(bounty_id)
        
        location = bounty.get("location", "Remote")
        
        # Get all guilds with subscriptions
        guilds = await self.db.get_all_guilds()
        
        for guild_id, channel_id in guilds:
            try:
                keywords = await self.db.get_subscriptions(guild_id)
                
                # Check if bounty matches any keyword
                matched = False
                for keyword in keywords:
                    if self.matches_location(location, keyword):
                        matched = True
                        break
                
                if matched:
                    await self.send_bounty_notification(channel_id, bounty, location)
                    
            except Exception as e:
                logger.error(f"Error processing bounty for guild {guild_id}: {e}")
    
    def matches_location(self, location: str, keyword: str) -> bool:
        """Check if location matches keyword"""
        return keyword.lower() in location.lower()
    
    async def send_bounty_notification(self, channel_id: str, bounty: Dict, location: str):
        """Send bounty notification to channel"""
        try:
            channel = self.get_channel(int(channel_id))
            if not channel:
                logger.warning(f"Channel {channel_id} not found")
                return
            
            embed = self.create_bounty_embed(bounty, location)
            await channel.send(embed=embed)
            logger.info(f"Sent bounty {bounty.get('id')} to channel {channel_id}")
            
        except discord.Forbidden:
            logger.error(f"Missing permissions to send to channel {channel_id}")
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def create_bounty_embed(self, bounty: Dict, location: str) -> discord.Embed:
        """Create enhanced embed for bounty"""
        title = bounty.get("title", "New Bounty")
        description = bounty.get("description", "No description provided")
        url = bounty.get("url", "")
        reward = bounty.get("reward", "Not specified")
        deadline = bounty.get("deadline", "Not specified")
        
        # Truncate description
        if len(description) > 500:
            description = description[:497] + "..."
        
        color = discord.Color.green()
        
        embed = discord.Embed(
            title=f"💰 {title}",
            description=description,
            url=url if url else None,
            timestamp=datetime.utcnow(),
            color=color
        )
        
        embed.add_field(name="📍 Location", value=location, inline=True)
        embed.add_field(name="💵 Reward", value=reward, inline=True)
        embed.add_field(name="⏰ Deadline", value=deadline, inline=True)
        
        # Add skills if available
        if "skills" in bounty and bounty["skills"]:
            skills = ", ".join(bounty["skills"][:5])
            embed.add_field(name="🛠️ Skills", value=skills, inline=False)
        
        embed.set_footer(text="RentAHuman Bounty Alert")
        
        return embed

# ============== COMMANDS ==============

bot = BountyBot()

def has_manage_guild():
    """Check if user has manage guild permission"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ You need 'Manage Server' permission to use this command.",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

@bot.tree.command(name="setchannel", description="Set the bounty notification channel")
@has_manage_guild()
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set notification channel"""
    try:
        await bot.db.set_channel(str(interaction.guild_id), str(channel.id))
        await interaction.response.send_message(
            f"✅ Notification channel set to {channel.mention}",
            ephemeral=True
        )
        logger.info(f"Channel set for guild {interaction.guild_id}: {channel.id}")
    except Exception as e:
        logger.error(f"Error setting channel: {e}")
        await interaction.response.send_message(
            "❌ Failed to set channel. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="subscribe", description="Subscribe to bounties in a specific location")
@has_manage_guild()
async def subscribe(interaction: discord.Interaction, keyword: str):
    """Subscribe to location-based bounties"""
    try:
        channel_id = await bot.db.get_channel(str(interaction.guild_id))
        if not channel_id:
            await interaction.response.send_message(
                "⚠️ Please set a notification channel first using `/setchannel`",
                ephemeral=True
            )
            return
        
        added = await bot.db.add_subscription(str(interaction.guild_id), keyword)
        
        if added:
            await interaction.response.send_message(
                f"✅ Subscribed to bounties in **{keyword}**",
                ephemeral=True
            )
            logger.info(f"Guild {interaction.guild_id} subscribed to '{keyword}'")
        else:
            await interaction.response.send_message(
                f"ℹ️ Already subscribed to **{keyword}**",
                ephemeral=True
            )
    except Exception as e:
        logger.error(f"Error subscribing: {e}")
        await interaction.response.send_message(
            "❌ Failed to subscribe. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="unsubscribe", description="Unsubscribe from a location")
@has_manage_guild()
async def unsubscribe(interaction: discord.Interaction, keyword: str):
    """Unsubscribe from location"""
    try:
        await bot.db.remove_subscription(str(interaction.guild_id), keyword)
        await interaction.response.send_message(
            f"✅ Unsubscribed from **{keyword}**",
            ephemeral=True
        )
        logger.info(f"Guild {interaction.guild_id} unsubscribed from '{keyword}'")
    except Exception as e:
        logger.error(f"Error unsubscribing: {e}")
        await interaction.response.send_message(
            "❌ Failed to unsubscribe. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="subscriptions", description="List all your location subscriptions")
async def subscriptions(interaction: discord.Interaction):
    """List all subscriptions"""
    try:
        keywords = await bot.db.get_subscriptions(str(interaction.guild_id))
        
        if not keywords:
            await interaction.response.send_message(
                "📭 No active subscriptions.\nUse `/subscribe` to add one!",
                ephemeral=True
            )
        else:
            keyword_list = "\n".join([f"• {kw}" for kw in keywords])
            await interaction.response.send_message(
                f"📍 **Active subscriptions:**\n{keyword_list}",
                ephemeral=True
            )
    except Exception as e:
        logger.error(f"Error listing subscriptions: {e}")
        await interaction.response.send_message(
            "❌ Failed to retrieve subscriptions.",
            ephemeral=True
        )

@bot.tree.command(name="status", description="Check bot status and configuration")
async def status(interaction: discord.Interaction):
    """Show bot status"""
    try:
        channel_id = await bot.db.get_channel(str(interaction.guild_id))
        keywords = await bot.db.get_subscriptions(str(interaction.guild_id))
        
        if channel_id:
            channel = bot.get_channel(int(channel_id))
            channel_mention = channel.mention if channel else f"<#{channel_id}>"
        else:
            channel_mention = "❌ Not set"
        
        mode = "🧪 Mock API (Testing)" if config.use_mock_api else "🚀 Production API"
        
        embed = discord.Embed(
            title="🤖 Bot Status",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="📢 Notification Channel", value=channel_mention, inline=False)
        embed.add_field(name="📍 Active Subscriptions", value=f"{len(keywords)} location(s)" if keywords else "None", inline=False)
        embed.add_field(name="🔄 Poll Interval", value=f"{config.poll_interval} seconds", inline=True)
        embed.add_field(name="🌐 API Mode", value=mode, inline=True)
        embed.set_footer(text=f"Bot latency: {round(bot.latency * 1000)}ms")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error showing status: {e}")
        await interaction.response.send_message(
            "❌ Failed to retrieve status.",
            ephemeral=True
        )

# ============== MAIN ==============

if __name__ == "__main__":
    try:
        logger.info("🤖 Starting Bounty Bot...")
        logger.info(f"📡 API Mode: {'MOCK (Testing)' if config.use_mock_api else 'PRODUCTION'}")
        logger.info(f"🔗 API URL: {config.api_url}")
        bot.run(config.discord_token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)