from PIL import Image, ImageDraw
import wx

def pilToWx(pil, alpha=True):
	if alpha:
		image = apply( wx.EmptyImage, pil.size )
		image.SetData( pil.convert( "RGB").tobytes() )
		image.SetAlphaData(pil.convert("RGBA").tobytes()[3::4])
	else:
		image = wx.EmptyImage(pil.size[0], pil.size[1])
		new_image = pil.convert('RGB')
		data = new_image.tostring()
		image.SetData(data)
	return image

def wxToPil(image):
	pil = Image.new('RGB', (image.GetWidth(), image.GetHeight()))
	pil.fromstring(image.GetData())
	return pil

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