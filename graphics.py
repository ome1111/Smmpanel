from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

# Colors (Dark Cyberpunk Theme)
BG = (15, 23, 42)       # Dark Blue
ACCENT = (56, 189, 248) # Cyan Neon
TEXT = (255, 255, 255)  # White
CARD = (30, 41, 59)     # Card BG

def get_font(size):
    try:
        # Google Font Download (Roboto Slab)
        url = "https://github.com/google/fonts/raw/main/apache/robotoslab/RobotoSlab-Bold.ttf"
        return ImageFont.truetype(BytesIO(requests.get(url).content), size)
    except:
        return ImageFont.load_default()

# 1. Welcome Banner
def create_welcome(name):
    img = Image.new('RGB', (800, 400), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(10, 10), (790, 390)], outline=ACCENT, width=4)
    
    draw.text((400, 100), "WELCOME TO", font=get_font(30), fill=TEXT, anchor="mm")
    draw.text((400, 180), "ULTIMATE SMM BOT", font=get_font(55), fill=ACCENT, anchor="mm")
    draw.text((400, 300), f"Hi, {name}", font=get_font(40), fill=TEXT, anchor="mm")
    
    bio = BytesIO(); img.save(bio, 'PNG'); bio.seek(0)
    return bio

# 2. Profile Card
def create_profile(name, uid, bal, spent):
    img = Image.new('RGB', (800, 450), BG)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(50, 50), (750, 400)], radius=25, fill=CARD, outline=ACCENT, width=2)

    draw.text((100, 100), "USER ID CARD", font=get_font(35), fill=ACCENT)
    draw.text((100, 180), f"Name: {name}", font=get_font(28), fill=TEXT)
    draw.text((100, 230), f"ID: {uid}", font=get_font(28), fill=TEXT)
    
    draw.text((450, 180), "BALANCE:", font=get_font(28), fill=ACCENT)
    draw.text((450, 240), f"${bal:.4f}", font=get_font(50), fill=(0, 255, 127))
    
    bio = BytesIO(); img.save(bio, 'PNG'); bio.seek(0)
    return bio

# 3. Receipt
def create_receipt(oid, s_name, cost):
    img = Image.new('RGB', (800, 400), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0,0), (800, 15)], fill=ACCENT)
    
    draw.text((400, 70), "ORDER SUCCESSFUL", font=get_font(40), fill=(0, 255, 127), anchor="mm")
    draw.text((50, 150), f"Order ID: #{oid}", font=get_font(30), fill=TEXT)
    draw.text((50, 220), f"Service: {s_name[:25]}...", font=get_font(30), fill=TEXT)
    draw.text((50, 290), f"Total Cost: ${cost}", font=get_font(30), fill=ACCENT)
    
    bio = BytesIO(); img.save(bio, 'PNG'); bio.seek(0)
    return bio
