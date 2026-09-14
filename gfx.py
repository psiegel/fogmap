from PIL import Image, ImageDraw
import wx

def pilToWx(pil, alpha=True):
	image = wx.Image(pil.size[0], pil.size[1])
	image.SetData(pil.convert("RGB").tobytes())
	if alpha:
		image.SetAlpha(pil.convert("RGBA").tobytes()[3::4])
	return image

def wxToPil(image):
	return Image.frombytes("RGB",
						   (image.GetWidth(), image.GetHeight()),
						   bytes(image.GetData()))

def createNewImg(w, h, color, alpha=False):
	if (alpha):
		im = Image.new("RGBA", (w, h))
		draw = ImageDraw.Draw(im)
		draw.rectangle([(0, 0), (w, h)], fill=color)
		del draw
	else:
		im = Image.new("RGB", (w, h))
		draw = ImageDraw.Draw(im)
		draw.rectangle([(0, 0), (w, h)], fill=color)
		del draw
	return im

def createMask(w, h, color, alpha=True):
	if (alpha):
		im = Image.new("L", (w, h))
	else:
		im = Image.new("1", (w, h))
	draw = ImageDraw.Draw(im)
	draw.rectangle([(0, 0), (w, h)], fill=color)
	del draw
	return im
