import colorsys
import random
from PIL import Image,ImageDraw,UnidentifiedImageError
from config import TARGET_SIZE, QUALITY
from decorators import log_time
from colors import extract_dominant_colors_from_palette
import logging

logging.basicConfig()
logging.root.setLevel(logging.INFO)

happy_colors_old = [
    (255, 0, 0, 1), # red
    (0,0,255,1), # blue
    (255, 255, 0, 1), # yellow
    (0, 255, 0, 1), # green
    (255, 0, 255, 1), # pink
    (255, 165, 0, 1), # orange]
]

# The colors are set by using names since
# the old way was not working.
happy_colors = [
    "red", # red
    "blue", # blue
    "yellow", # yellow
    "green", # green
    "pink", # pink
    "orange", # orange]
]

def get_random_happy_color():
    return happy_colors[random.randint(0,len(happy_colors)-1)]

def get_valid_image(path) -> object | bool:
    """
    Check if the image is PNG and RGBA, it also check the size and return the image object. 
    If you have an error at this stage the image is probably corrupted or truncated and so
    you can just exit the program.
    """
    try:
        img = Image.open(path)
        img.load()

        logging.info(f"Image format : {img.format}")
        logging.info(f"Image mode : {img.mode}")

        if(img.mode != "RGBA"):
            logging.info(f"Image mode : {img.mode} converting to RGBA")
            img = img.convert("RGBA")
        
        if(img.format != "PNG"):
            logging.info(f"Image format : {img.format} converting to PNG")
            img.save(path,"PNG")
        
        if(img.size != TARGET_SIZE):
            logging.info(f"Original image size : {img.size}")
            logging.info(f"Resizing image")
            img = img.resize(TARGET_SIZE, Image.LANCZOS)

        return img
    
    except UnidentifiedImageError as imgE:
        logging.error("Error loading image",imgE)
        exit(1)
    except FileNotFoundError:
        logging.error("File Not found")
        exit(1)
    except Exception as e:
        logging.error("Error processing image",e)
        exit(1)

def is_pixel_inside_circle(x:int,y:int):
    distance = ((x - 255) ** 2 + (y - 255) ** 2) ** 0.5
    return distance <= 256

def check_shape(img):
    logging.info(f"Checking shape")
    drawer = ImageDraw.Draw(img)
    width, height = img.size
    for x in range(width):
        for y in range(height):
            if(not is_pixel_inside_circle(x,y)):
              drawer.point((x,y),fill=(255, 0, 0, 0)) # just set alpha channel  
    return

@log_time
def get_palette_sentiment(img:object) -> dict:
    """
    This function extract the palette and run the sentiment analysis on it.
    """
    logging.info(f"Happy - Check if the palette colors is happy,")
    palette = get_colors(img)
    logging.info(f"Palette colors found: {len(palette)}")
    len_palette = len(palette)
    dominats = palette
    

    if(len(palette) > 15):
        dominats,dominant_map = extract_dominant_colors_from_palette(palette)
    
    happy_colors = [(is_happy(color),color) for color in dominats]
    
    # check if the palette is happy or not
    h = sum(1 for v in happy_colors if(v[0]))
    if(h > 2 and h > int(len(happy_colors)/2)):
        h = h > int(len(happy_colors)/2)
    else:
        h = h > 0
        
    logging.info(f"Is happy? {h}")
    if not h and len_palette < 2:
        # we have 2 or 1 color, it make sense to remap the sad colors
        logging.info(f" - Maybe we can fix this..")
        no_happy_map = remap_sad_colors(palette)
        logging.info(f" - Swapping colors {no_happy_map}")
        swap_no_dominants(img,no_happy_map)
        
        
    return 

@log_time
def resize_image(path:str,path_out:str):
    image = Image.open(path)
    # Antialis algorithm
    # https://stackoverflow.com/questions/76616042/attributeerror-module-pil-image-has-no-attribute-antialias
    # or .thumbnail
    resized = image.resize(TARGET_SIZE, Image.LANCZOS)

    # Save the resized image with high quality
    resized.save(path_out, quality=QUALITY)

# Approximate hue ranges in the HSV color space.
def is_happy_old(rgba):
    r, g, b, a = [x / 255 for x in rgba]  # Normalize values to the range [0, 1]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    # to explain the values -> https://en.wikipedia.org/wiki/HSL_and_HSV#/media/File:Hsl-hsv_models.svg
    happy_color_ranges = [
        (0, 15/360), # red
        (345/360, 1), # red
        (15/360, 45/360), # orange
        (45/360, 75/360), # yellow
        (75/360, 170/360), # green
        (170/360, 260/360), # blue
        (260/360, 345/360) # pink
    ]
    if v < 0.3 or v > 0.8: 
        return False # too dark or too light (black or white)
    if a < 0.5 or s < 0.2: # transparent
        return False
    return any([True for start,end in happy_color_ranges if start <= h < end])

def is_happy(rgb):
    """
    Check if the color is happy or not by checking the hue and removing the 
    alpha channel information.
    """
    rgb = rgb[:3]  # Ignore alpha channel
    r, g, b = [x / 255 for x in rgb]  # Normalize values to the range [0, 1]

    # Calculate the hue
    if r == g == b:
        # Handle the case of grayscale (completely desaturated)
        return False

    if r >= g and r >= b:
        h = (g - b) / (r - min(g, b))
    elif g >= r and g >= b:
        h = 2 + (b - r) / (g - min(r, b))
    else:
        h = 4 + (r - g) / (b - min(r, g))

    h = (h / 6) % 1  # Normalize hue to [0, 1]

    # Define the hue ranges for "happy" colors
    happy_color_ranges = [
        (0, 15/360),    # red
        (345/360, 1),   # red
        (15/360, 45/360),    # orange
        (45/360, 75/360),    # yellow
        (75/360, 170/360),   # green
        (170/360, 260/360),  # blue
        (260/360, 345/360)   # pink
    ]

    return any(start <= h < end for start, end in happy_color_ranges)

def is_transparent(rgba):
    if(rgba == (0, 0, 0, 0)):
        return True
    r, g, b, a = rgba
    return a > 0.9

def get_colors(img:object):
    """
    This function is used as implementation of the get_palette function. 
    While looping for the colors the function also create a transparent circle
    around the image and check if there are non-transparent pixel out of the circle.
    """
    out_pixel = False
    width, height = TARGET_SIZE
    colors = []
    drawer = ImageDraw.Draw(img)
    for x in range(width):
        for y in range(height):
            if is_pixel_inside_circle(x,y) and img.getpixel((x,y)) != (255,255,255,0) and img.getpixel((x,y)) != (0,0,0,0) :
                pixel = img.getpixel((x,y))
                #logging.info(f"Pixel: {pixel}")
                pixel_ = (pixel[0],pixel[1],pixel[2],0)
                if(pixel_ not in colors):
                    colors.append(pixel_)
            else:
                # create the circle
                if(
                    not is_transparent(img.getpixel((x,y))) and 
                    not out_pixel
                 ):
                    out_pixel = True
                    logging.info(f"Transparent pixel found: {img.getpixel((x,y))}")
                drawer.point((x,y),fill=(255, 0, 0, 0)) # just set alpha channel
    
    if(not out_pixel):
        logging.info(f"There are no non-transparent pixel out of the circle")

    return colors

def swap_dominants(img:object,dominants:dict):
    pass

def swap_no_dominants(img:object,no_happy:dict):
    def getColor(t,m):
        return [p[1] for p in m if p[0] == t][-1]

    img_drawer = ImageDraw.Draw(img)
    
    width, height = TARGET_SIZE
    no_happy_s = [c[0] for c in no_happy]
    logging.info(f"Swapping no dominants colors {no_happy_s}")
    for x in range(width):
        for y in range(height):
            pixel = img.getpixel((x,y))
            if is_pixel_inside_circle(x,y) and pixel != (0, 0, 0, 0):
                pixel_ = (pixel[0],pixel[1],pixel[2],0)
                if(pixel_ in no_happy_s):
                    img_drawer.point((x,y),fill=getColor(pixel_,no_happy))
            else:
                img_drawer.point((x,y),fill=(255,255,255,0)) # just set alpha channel


    return

def remap_sad_colors(colors:list):    
    """
    For each sad color get a random happy color.
    """
    return[(color,get_random_happy_color()) for color in colors if(not color[0])]
    
def make_happy(img:object,info:dict):
    if(info["dominant_map"] != {}):
        logging.info(f"Clustering applied - Swapping dominants colors")
        # swap dopminants
        return img
    
    no_happy_map = remap_sad_colors(info["palette"])
    logging.info(f"Swapping colors {no_happy_map}")
    swap_no_dominants(img,no_happy_map)

    return 

def happy_or_swap(img:object):
    
    logging.info(f"Happy or swap - Check if the palette is happy in case is not then swap")
    info = get_palette_sentiment(img)
    logging.info(f"Dominants colors found: {info['palette']}")
    
    if(not info["is_happy"]):
        logging.info("Image is not happy")
        make_happy(img,info)
    
    return info

    

@log_time
def base(path:str,path_out:str):
    logging.info(f"Parallel - Image path: {path}")
    
    img = get_valid_image(path)
    if(not img):
        logging.error("Invalid image")
        return
    
    get_palette_sentiment(img)

    logging.info(f"Saving image at {path_out}")    
    img.save(path_out)

    return



