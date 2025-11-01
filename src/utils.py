from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageFont
import uuid
import os
from datetime import datetime
from typing import Optional
import json
import re

class HelperFunctions:
    # Helper Functions
    def load_font(size: int, bold: bool = False):
        """Load font from fonts directory"""
        font_file = "Inter-Bold.ttf" if bold else "Inter-Regular.ttf"
        font_path = os.path.join("fonts", font_file)

        try:
            return ImageFont.truetype(font_path, size)
        except:
            return ImageFont.load_default()

    def format_number(num: int) -> str:
        """Format numbers like Twitter (1.2K, 3.4M, etc.)"""
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)

    def generate_tweet_screenshot(
        username: str,
        display_name: str,
        tweet_text: str,
        verified: bool = False,
        likes: int = 0,
        retweets: int = 0,
        replies: int = 0,
        views: int = 0,
        timestamp: Optional[str] = None,
        profile_image_url: Optional[str] = None,
    ) -> str:
        """Generate a realistic Twitter screenshot"""

        # Image dimensions
        width = 598
        padding = 16

        # Create base image
        img = Image.new("RGB", (width, 500), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Load fonts
        try:
            name_font = ImageFont.truetype("fonts/Inter-Bold.ttf", 15)
            username_font = ImageFont.truetype("fonts/Inter-Regular.ttf", 15)
            text_font = ImageFont.truetype("fonts/Inter-Regular.ttf", 15)
            stats_font = ImageFont.truetype("fonts/Inter-Bold.ttf", 14)
            stats_label_font = ImageFont.truetype("fonts/Inter-Regular.ttf", 14)
            timestamp_font = ImageFont.truetype("fonts/Inter-Regular.ttf", 15)
            button_font = ImageFont.truetype("fonts/Inter-Bold.ttf", 14)
        except:
            name_font = username_font = text_font = stats_font = timestamp_font = (
                ImageFont.load_default()
            )
            stats_label_font = button_font = ImageFont.load_default()

        # Twitter colors
        text_color = (15, 20, 25)
        gray_color = (83, 100, 113)
        blue_color = (29, 155, 240)
        border_color = (239, 243, 244)
        profile_bg = (207, 217, 222)

        y_position = padding

        # === PROFILE SECTION ===
        profile_x = padding
        profile_y = y_position
        profile_size = 48

        # Profile circle
        draw.ellipse(
            [profile_x, profile_y, profile_x + profile_size, profile_y + profile_size],
            fill=profile_bg,
            outline=border_color,
            width=1,
        )

        # Add initials
        if display_name:
            initials = "".join([word[0] for word in display_name.split()[:2]]).upper()
            try:
                initial_font = ImageFont.truetype("fonts/Inter-Bold.ttf", 20)
            except:
                initial_font = name_font

            bbox = draw.textbbox((0, 0), initials, font=initial_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            initial_x = profile_x + (profile_size - text_width) // 2
            initial_y = profile_y + (profile_size - text_height) // 2 - 2

            draw.text(
                (initial_x, initial_y),
                initials,
                font=initial_font,
                fill=(255, 255, 255),
            )

        # === NAME AND VERIFICATION (EVEN SMALLER BADGE) ===
        name_x = profile_x + profile_size + 12
        name_y = y_position + 2

        draw.text((name_x, name_y), display_name, font=name_font, fill=text_color)

        # SMALLER verified badge (reduced to 14px)
        if verified:
            name_bbox = draw.textbbox((name_x, name_y), display_name, font=name_font)
            name_width = name_bbox[2] - name_bbox[0]
            badge_x = name_x + name_width + 6
            badge_y = name_y + 2

            badge_img = Image.open("icons/twitter_verified_badge.png").convert("RGBA")
            badge_img = badge_img.resize((16, 16), Image.Resampling.LANCZOS)  # 👈 scaled down

            img.paste(badge_img, (int(badge_x), int(badge_y)), badge_img)


        # === FOLLOW BUTTON (Top Right) ===
        follow_button_width = 80
        follow_button_height = 32
        follow_button_x = width - padding - follow_button_width
        follow_button_y = y_position 

        # Draw rounded rectangle for follow button
        draw.rounded_rectangle(
            [
                follow_button_x,
                follow_button_y,
                follow_button_x + follow_button_width,
                follow_button_y + follow_button_height,
            ],
            radius=16,
            fill=blue_color,
        )

        # Follow button text
        follow_text = "Follow"
        follow_bbox = draw.textbbox((0, 0), follow_text, font=button_font)
        follow_text_width = follow_bbox[2] - follow_bbox[0]
        follow_text_height = follow_bbox[3] - follow_bbox[1]
        follow_text_x = follow_button_x + (follow_button_width - follow_text_width) // 2
        follow_text_y = (
            follow_button_y + (follow_button_height - follow_text_height) // 2 - 2
        )

        draw.text(
            (follow_text_x, follow_text_y),
            follow_text,
            font=button_font,
            fill=(255, 255, 255),
        )

        # === USERNAME ===
        username_y = name_y + 20
        draw.text(
            (name_x, username_y), f"@{username}", font=username_font, fill=gray_color
        )

        # === TWEET TEXT ===
        text_y = profile_y + profile_size + 12

        # Word wrap
        words = tweet_text.split()
        lines = []
        current_line = []
        max_width = width - (2 * padding)

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=text_font)
            if bbox[2] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        line_height = 20
        for line in lines:
            draw.text((padding, text_y), line, font=text_font, fill=text_color)
            text_y += line_height

        # === TIMESTAMP ===
        text_y += 12
        timestamp_text = (
            timestamp
            if timestamp
            else datetime.now().strftime("%I:%M %p · %b %d, %Y").lstrip("0").replace(" 0", " ")

        )
        draw.text(
            (padding, text_y), timestamp_text, font=timestamp_font, fill=gray_color
        )

        # === SEPARATOR LINE ===
        text_y += 28
        draw.line(
            [(padding, text_y), (width - padding, text_y)], fill=border_color, width=1
        )

        # === ENGAGEMENT STATS ===
        stats_y = text_y + 12
        stats_x = padding

        stats_data = []
        if retweets > 0:
            stats_data.append((HelperFunctions.format_number(retweets), "Retweets"))
        if likes > 0:
            stats_data.append((HelperFunctions.format_number(likes), "Likes"))
        if replies > 0:
            stats_data.append((HelperFunctions.format_number(replies), "Replies"))

        for number, label in stats_data:
            draw.text((stats_x, stats_y), number, font=stats_font, fill=text_color)

            num_bbox = draw.textbbox((stats_x, stats_y), number, font=stats_font)
            num_width = num_bbox[2] - num_bbox[0]

            draw.text(
                (stats_x + num_width + 4, stats_y),
                label,
                font=stats_label_font,
                fill=gray_color,
            )

            label_bbox = draw.textbbox((0, 0), label, font=stats_label_font)
            label_width = label_bbox[2] - label_bbox[0]

            stats_x += num_width + label_width + 20

        # === SEPARATOR LINE ===
        stats_y += 28
        draw.line(
            [(padding, stats_y), (width - padding, stats_y)], fill=border_color, width=1
        )

        # === ACTION BUTTONS (USING LOCAL ICON IMAGES) ===
        button_y = stats_y + 12
        button_spacing = (width - 2 * padding) // 4
        icon_size = 20

        # Load and paste icons from local folder
        icon_paths = {
            "reply": "icons/reply.png",
            "retweet": "icons/retweet.png",
            "like": "icons/like.png",
            "views": "icons/views.png",
        }

        icon_positions = [
            padding + 5,
            padding + button_spacing + 5,
            padding + 2 * button_spacing + 5,
            padding + 3 * button_spacing + 5,
        ]

        icon_names = ["reply", "retweet", "like", "views"]

        # Stats values for each icon
        icon_stats = {
            "reply": replies,
            "retweet": retweets,
            "like": likes,
            "views": views,
        }

        # Font for numbers next to icons
        try:
            icon_number_font = ImageFont.truetype("fonts/Inter-Regular.ttf", 13)
        except:
            icon_number_font = stats_label_font

        for i, icon_name in enumerate(icon_names):
            try:
                icon_path = icon_paths[icon_name]
                icon = Image.open(icon_path).convert("RGBA")
                # Resize icon to desired size
                icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)

                # Paste icon with transparency
                img.paste(icon, (icon_positions[i], button_y), icon)
            except Exception as e:
                # Fallback: draw a simple placeholder circle if icon not found
                draw.ellipse(
                    [
                        icon_positions[i],
                        button_y,
                        icon_positions[i] + icon_size,
                        button_y + icon_size,
                    ],
                    outline=gray_color,
                    width=2,
                )

            # Draw the number next to the icon
            stat_value = icon_stats.get(icon_name, 0)
            if stat_value > 0:  # Only show if there's a value
                formatted_number = HelperFunctions.format_number(stat_value)
                number_x = icon_positions[i] + icon_size + 6  # 6px gap after icon
                number_y = button_y + 2  # Align vertically with icon
                draw.text(
                    (number_x, number_y),
                    formatted_number,
                    font=icon_number_font,
                    fill=gray_color,
                )

        # Crop to actual content height
        final_y = button_y + 35
        img = img.crop((0, 0, width, final_y))
        # Save
        filename = f"tweet_{uuid.uuid4().hex}.png"
        filepath = os.path.join("output", filename)
        img.save(filepath, format="PNG", quality=95, optimize=True)

        return filepath


    def parse_tweet_request(text: str) -> dict:
        result = {}
        text_lower = text.lower().strip()
        
        # Check for verification
        if "verified" in text_lower:
            result["verified"] = True
        
        # Extract engagement metrics FIRST (before extracting tweet text)
        # Pattern: "with 100 likes"
        likes_match = re.search(r"with\s+(\d+(?:k|m)?)\s+likes?", text, re.IGNORECASE)
        if likes_match:
            result["likes"] = HelperFunctions.parse_number(likes_match.group(1))
        
        # Pattern: "50 retweets"
        retweets_match = re.search(r"(\d+(?:k|m)?)\s+retweets?", text, re.IGNORECASE)
        if retweets_match:
            result["retweets"] = HelperFunctions.parse_number(retweets_match.group(1))
        
        # Pattern: "10 replies"
        replies_match = re.search(r"(\d+(?:k|m)?)\s+repl(?:y|ies)", text, re.IGNORECASE)
        if replies_match:
            result["replies"] = HelperFunctions.parse_number(replies_match.group(1))
        
        # Pattern: "500 views"
        views_match = re.search(r"(\d+(?:k|m)?)\s+views?", text, re.IGNORECASE)
        if views_match:
            result["views"] = HelperFunctions.parse_number(views_match.group(1))
        
        # Now extract tweet text (everything between "saying" and "with" or end of string)
        # Pattern 1: "for <username> saying <tweet_text> [with ...]"
        pattern1 = r"(?:create|generate|make|tweet)?\s*(?:a\s+)?(?:verified\s+)?(?:tweet\s+)?for\s+@?(\w+)\s+saying\s+(.+?)(?:\s+with\s+|\s*$)"
        match = re.search(pattern1, text, re.IGNORECASE)
        
        if match:
            result["username"] = match.group(1).lower()
            result["display_name"] = match.group(1).title()
            result["tweet_text"] = match.group(2).strip()
            return result
        
        # Pattern 2: "saying <tweet_text> [with ...]" without username
        pattern2 = r"(?:create|generate|make)?\s*(?:a\s+)?(?:verified\s+)?(?:tweet\s+)?saying\s+(.+?)(?:\s+with\s+|\s*$)"
        match = re.search(pattern2, text, re.IGNORECASE)
        
        if match:
            result["tweet_text"] = match.group(1).strip()
            return result
        
        # Pattern 3: Direct tweet text (no "saying" keyword)
        # If text doesn't start with command words, treat it as direct tweet content
        command_words = ["create", "generate", "make", "tweet", "post", "verified"]
        starts_with_command = any(text_lower.startswith(word) for word in command_words)
        
        if not starts_with_command and text.strip():
            result["tweet_text"] = text.strip()
            return result
        
        # Pattern 4: Just command words with text (fallback)
        # Matches: "create a tweet hello world", "make tweet test"
        pattern4 = r"(?:create|generate|make)\s+(?:a\s+)?(?:verified\s+)?tweet\s+(.+?)(?:\s+with\s+|\s*$)"
        match = re.search(pattern4, text, re.IGNORECASE)
        
        if match:
            result["tweet_text"] = match.group(1).strip()
            return result
        
        return result


    def parse_number(num_str: str) -> int:
        """
        Parse number strings like '1k', '2.5m', '100' to integers
        
        Examples:
        - '100' -> 100
        - '1k' -> 1000
        - '1.5k' -> 1500
        - '2m' -> 2000000
        """
        num_str = num_str.lower().strip()
        
        if 'k' in num_str:
            return int(float(num_str.replace('k', '')) * 1000)
        elif 'm' in num_str:
            return int(float(num_str.replace('m', '')) * 1000000)
        else:
            return int(num_str)