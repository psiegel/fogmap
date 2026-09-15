import wx
import math

from PIL import ImageDraw

def getTriangleArea(triangle):
	"""Triangle should be a list of three tuples defining 
	   the three points of the triangle."""
	a = (triangle[0][0] - triangle[2][0])
	b = (triangle[0][1] - triangle[2][1])
	c = (triangle[1][0] - triangle[2][0])
	d = (triangle[1][1] - triangle[2][1])
	return (0.5 * abs((a*d)-(b*c)));

def pointInTriangle(pt, triangle):
	"""Point is a tuple (x, y) and triangle is a list of three
	   tuples defining the three points of the triangle."""
	triangleArea = getTriangleArea(triangle)
	test1 = getTriangleArea((triangle[0], triangle[1], pt))
	test2 = getTriangleArea((triangle[0], triangle[2], pt))
	test3 = getTriangleArea((triangle[1], triangle[2], pt))
	return ((test1 + test2 + test3) <= triangleArea)

def pointToHexCoords(point, hexSize):
	x, y = point
	halfHex = hexSize // 2
	quarterHex = hexSize // 4
	threeQuarterHex = quarterHex*3
	
	# Convert into squares
	hexX = x // threeQuarterHex
	if (hexX%2 == 1):
		y -= halfHex		
	hexY = y // hexSize
		
	# Check if we're out of the bounds of this hex
	x = x % threeQuarterHex
	y = y % hexSize
	if (x < quarterHex):
		if (y < halfHex):
			# Top Left
			if (pointInTriangle((x, y), ((0, 0), (0, halfHex), (quarterHex, 0)))):
				# Shift up and left
				hexX -= 1
				if (hexX%2 == 1):
					hexY -= 1
		else:
			# Bottom Left
			if (pointInTriangle((x, y), ((0, halfHex), (0, hexSize), (quarterHex, hexSize)))):
				# Shift down and left
				hexX -= 1
				if (hexX%2 == 0):
					hexY += 1
					
	# This is all uneccessary, as the overlap always evalutes to the left-most hex (as you can see
	# from the (x % threeQuarterHex) above.
	#elif (x > (quarterHex * 3)):
		#if (y < halfHex):
			## Top Right
			#if (pointInTriangle((x, y), ((threeQuarterHex, 0), (hexSize, 0), (hexSize, halfHex)))):
				## Shift up and right
				#hexX += 1
				#if (hexX%2 == 1):
					#hexY += 1
		#else:
			# Bottom Right
			#if (pointInTriangle((x, y), ((threeQuarterHex, hexSize), (hexSize, hexSize), (hexSize, halfHex)))):
				## Shift down and right
				#hexX += 1
				#if (hexX%2 == 0):
					#hexY += 1
	
	return (hexX, hexY)

def expandCircleToPoints(x, y, radius):
	pt = (x, y)
	points = []
	
	# First, the center point
	points.append(pt)
	
	# Up
	for i in range(1, radius):
		pt = (pt[0], pt[1] - 1)
		points.append(pt)
		
	# Up Left and Left
	pt = (x, y)
	for i in range(1, radius):
		if (pt[0] % 2 == 0):
			pt = (pt[0]-1, pt[1]-1)
		else:
			pt = (pt[0]-1, pt[1])
		points.append(pt)
		
		tempPt = (pt[0], pt[1])
		for j in range(1, i):
			tempPt = (tempPt[0], tempPt[1]+1)
			points.append(tempPt)

		tempPt = (pt[0], pt[1])
		for j in range(1, i):
			if (tempPt[0]%2 == 0):
				tempPt = (tempPt[0]+1, tempPt[1]-1)
			else:
				tempPt = (tempPt[0]+1, tempPt[1])
			points.append(tempPt)
	
	# Up Right and Right
	pt = (x, y)
	for i in range(1, radius):
		if (pt[0] % 2 == 0):
			pt = (pt[0]+1, pt[1]-1)
		else:
			pt = (pt[0]+1, pt[1])
		points.append(pt)
		
		tempPt = (pt[0], pt[1])
		for j in range(1, i):
			tempPt = (tempPt[0], tempPt[1]+1)
			points.append(tempPt)

		tempPt = (pt[0], pt[1])
		for j in range(1, i):
			if (tempPt[0]%2 == 0):
				tempPt = (tempPt[0]-1, tempPt[1]-1)
			else:
				tempPt = (tempPt[0]-1, tempPt[1])
			points.append(tempPt)
	
	# Down
	pt = (x, y)
	for i in range(1, radius):
		pt = (pt[0], pt[1] + 1)
		points.append(pt)
	
	# Down Left
	pt = (x, y)
	for i in range(1, radius):
		if (pt[0] % 2 == 1):
			pt = (pt[0]-1, pt[1]+1)
		else:
			pt = (pt[0]-1, pt[1])
		points.append(pt)
		
		tempPt = (pt[0], pt[1])
		for j in range(1, i):
			if (tempPt[0]%2 == 1):
				tempPt = (tempPt[0]+1, tempPt[1]+1)
			else:
				tempPt = (tempPt[0]+1, tempPt[1])
			points.append(tempPt)
				
	# Down Right
	pt = (x, y)
	for i in range(1, radius):
		if (pt[0] % 2 == 1):
			pt = (pt[0]+1, pt[1]+1)
		else:
			pt = (pt[0]+1, pt[1])
		points.append(pt)
		
		tempPt = (pt[0], pt[1])
		for j in range(1, i):
			if (tempPt[0]%2 == 1):
				tempPt = (tempPt[0]-1, tempPt[1]+1)
			else:
				tempPt = (tempPt[0]-1, tempPt[1])
			points.append(tempPt)
			
	return points

def createHexPath(gc, size):
	oneseg = size // 4
	twoseg = oneseg*2	# same as size/2

	path = gc.CreatePath()
	path.MoveToPoint(0, twoseg)
	path.AddLineToPoint(oneseg, 0)
	path.AddLineToPoint(oneseg + twoseg, 0)
	path.AddLineToPoint(size , twoseg)
	path.AddLineToPoint(oneseg + twoseg, size)
	path.AddLineToPoint(oneseg, size)
	path.AddLineToPoint(0, twoseg)

	return path
	
def drawHexGridToGc(gc, w, h, hexSize, clip=None):
	"""clip is the box of map being repainted, as (x0, y0, x1, y1), or None for
	   the whole map.  Only the hexes that reach into it are stroked; drawing
	   the lot is thousands of strokes on a large map, and it happens on every
	   repaint."""
	wInc = (hexSize // 4) * 3
	if ((wInc <= 0) or (hexSize <= 0)):
		return

	gc.SetPen(wx.Pen("black", 1))
	gc.SetBrush(wx.Brush("black"))
	hexPath = createHexPath(gc, hexSize)

	# Columns step across by wInc and every other one drops half a hex, so a
	# hex sits at (i*wInc, j*hexSize + half on odd columns) and covers hexSize
	# each way from there.  The bounds below are the same set the old
	# while-loops walked, narrowed to what the clip can actually show.
	cols = int(math.ceil(w / float(wInc)))
	rows = int(math.ceil(h / float(hexSize)))
	if (clip is None):
		iFrom, iTo, jFrom, jTo = 0, cols, 0, rows
	else:
		x0, y0, x1, y1 = clip
		iFrom = max(0, int(math.floor((x0 - hexSize) / float(wInc))))
		iTo = min(cols, int(math.ceil(x1 / float(wInc))) + 1)
		# One row of slack for the half-hex drop on odd columns.
		jFrom = max(0, int(math.floor((y0 - hexSize) / float(hexSize))) - 1)
		jTo = min(rows, int(math.ceil(y1 / float(hexSize))) + 1)

	for i in range(iFrom, iTo):
		x = i * wInc
		hInc = (hexSize // 2) if (i % 2) else 0
		for j in range(jFrom, jTo):
			gc.PushState()
			gc.Translate(x, j * hexSize + hInc)
			gc.StrokePath(hexPath)
			gc.PopState()
	
def fillHexCircleToGc(gc, center, radius, hexSize):
	hexPath = createHexPath(gc, hexSize)
	
	x, y = pointToHexCoords(center, hexSize)	
	points = expandCircleToPoints(x, y, radius)
	
	w = hexSize
	h = hexSize
	for point in points:
		w = max(w, hexSize * point[0])
		h = max(h, hexSize * point[1])
	wInc = (hexSize // 4) * 3

	x = -wInc
	y = -(hexSize // 2)
	pt = (-1, -1)
	
	gc.PushState() 
	gc.Translate(x, y)

	while (y < h+hexSize):
		gc.PushState() 
		hInc = (-hexSize) // 2
		while (x < w):
			if (pt in points):
				gc.DrawPath(hexPath)
			gc.Translate(wInc, hInc)
			x += wInc
			hInc = -hInc
			pt = (pt[0]+1, pt[1])
		gc.PopState()
		gc.Translate(0, hexSize)
		y += hexSize
		x = -wInc
		pt = (-1, pt[1] + 1)
		
	gc.PopState() 

def fillHexToImg(im, x, y, size, color):
	oneseg = size // 4
	twoseg = oneseg*2	# same as size/2

	points = [ (x, y+twoseg),
			   (x+oneseg, y),
			   (x+oneseg + twoseg, y),
			   (x+size , y+twoseg),
			   (x+oneseg+twoseg, y+size),
			   (x+oneseg, y+size) ]

	draw = ImageDraw.Draw(im)
	draw.polygon(points, color)
	del draw
		
def fillHexeCircleToImage(im, center, radius, hexSize, color):
	x, y = pointToHexCoords(center, hexSize)	
	points = expandCircleToPoints(x, y, radius)
		
	w, h = im.size
	wInc = (hexSize // 4) * 3

	x = -wInc
	y = (-hexSize) // 2
	pt = (-1, -1)
	
	while (y < h+hexSize):
		hInc = 0
		while (x < w):
			if (pt in points):
				fillHexToImg(im, x, y+hInc, hexSize, color)
			x += wInc
			if (hInc == 0):
				hInc = -(hexSize // 2)
			else:
				hInc = 0
			pt = (pt[0]+1, pt[1])
		x = -wInc
		y += hexSize
		pt = (-1, pt[1] + 1)		

