################################################################################
#    RunningText.py - Running Text Renderer for Enigma2
#    Version: 1.5 (04.04.2012 23:40)
#    Copyright (C) 2010-2012 vlamo <vlamodev@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
################################################################################

from Components.Renderer.Renderer import Renderer
from skin import parseColor, parseFont
from enigma import eCanvas, eLabel, eTimer, eRect, ePoint, eSize, gRGB, gFont, \
	RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_HALIGN_RIGHT, RT_HALIGN_BLOCK, \
	RT_VALIGN_TOP, RT_VALIGN_CENTER, RT_VALIGN_BOTTOM, RT_WRAP

# scroll type:
NONE     = 0
RUNNING  = 1
SWIMMING = 2
AUTO     = 3
# direction:
LEFT     = 0
RIGHT    = 1
TOP      = 2
BOTTOM   = 3
# halign:
#LEFT     = 0
#RIGHT    = 1
CENTER   = 2
BLOCK    = 3

class RunningText(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.type     = NONE
		self.txfont   = gFont("Regular", 14)
		self.fcolor   = gRGB(255,255,255)
		self.bcolor   = gRGB(0,0,0)
		self.scolor   = None
		self.soffset  = (0,0)
		self.txtflags = 0
		self.txtext   = ""
		self.test_label = self.mTimer = self.mStartPoint = None
		self.X = self.Y = self.W = self.H = self.mStartDelay = 0
		self.mAlways = 1		# always move text
		self.mStep = 1			# moving step: 1 pixel per 1 time
		self.mStepTimeout = 50		# step timeout: 1 step per 50 milliseconds ( speed: 20 pixel per second )
		self.direction = LEFT
		self.mLoopTimeout = self.mOneShot = 0
		self.mRepeat = 0
		self.mPageDelay = self.mPageLength = 0
		self.lineHeight = 0		# for text height auto correction on dmm-enigma2

	GUI_WIDGET = eCanvas

	def postWidgetCreate(self, instance):
		for (attrib, value) in self.skinAttributes:
			if attrib == "size":
				x, y = value.split(',')
				self.W, self.H = int(x), int(y)
		self.instance.setSize( eSize(self.W,self.H) )
		self.test_label = eLabel(instance)
		self.mTimer = eTimer()
		self.mTimer.callback.append(self.movingLoop)

	def preWidgetRemove(self, instance):
		self.mTimer.stop()
		self.mTimer.callback.remove(self.movingLoop)
		self.mTimer = None
		self.test_label = None

	def applySkin(self, desktop, screen):
		def retValue(val, limit, default, Min=False):
			try:
				if Min:
					x = min(limit, int(val))
				else:
					x = max(limit, int(val))
			except:
					x = default
			return x
		def setWrapFlag(attrib, value):
			if (attrib.lower() == "wrap" and value == "0") or \
			   (attrib.lower() == "nowrap" and value != "0"):
				self.txtflags &= ~RT_WRAP
			else:
				self.txtflags |= RT_WRAP

		self.halign = valign = eLabel.alignLeft
		if self.skinAttributes:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "font":
					self.txfont = parseFont(value, ((1,1),(1,1)))
				elif attrib == "foregroundColor":
					self.fcolor = parseColor(value)
				elif attrib == "backgroundColor":
					self.bcolor = parseColor(value)
				elif attrib in ("shadowColor","borderColor"):	# fake for openpli-enigma2
					self.scolor = parseColor(value)
				elif attrib == "shadowOffset":
					x, y = value.split(',')
					self.soffset = (int(x),int(y))
				elif attrib == "borderWidth":			# fake for openpli-enigma2
					self.soffset = (-int(value),-int(value))
				elif attrib == "valign" and value in ("top","center","bottom"):
					valign = { "top": eLabel.alignTop, "center": eLabel.alignCenter, "bottom": eLabel.alignBottom }[value]
					self.txtflags |= { "top": RT_VALIGN_TOP, "center": RT_VALIGN_CENTER, "bottom": RT_VALIGN_BOTTOM }[value]
				elif attrib == "halign" and value in ("left","center","right","block"):
					self.halign = { "left": eLabel.alignLeft, "center": eLabel.alignCenter, "right": eLabel.alignRight, "block": eLabel.alignBlock }[value]
					self.txtflags |= { "left": RT_HALIGN_LEFT, "center": RT_HALIGN_CENTER, "right": RT_HALIGN_RIGHT, "block": RT_HALIGN_BLOCK }[value]
				elif attrib == "noWrap":
					setWrapFlag(attrib, value)
				elif attrib == "options":
					options = value.split(',')
					for o in options:
						if o.find('=') != -1:
							opt, val = (x.strip() for x in o.split('=', 1))
						else:
							opt, val = o.strip(), ""
						
						if opt == "":
							continue
						elif opt in ("wrap", "nowrap"):
							setWrapFlag(opt, val)
						elif opt == "movetype" and val in ("none","running","swimming"):
							self.type = {"none": NONE, "running": RUNNING, "swimming": SWIMMING}[val]
						elif opt =="direction" and val in ("left","right","top","bottom"):
							self.direction = { "left": LEFT, "right": RIGHT, "top": TOP, "bottom": BOTTOM }[val]
						elif opt == "step" and val:
							self.mStep = retValue(val, 1, self.mStep)
						elif opt == "steptime" and val:
							self.mStepTimeout = retValue(val, 25, self.mStepTimeout)
						elif opt == "startdelay" and val:
							self.mStartDelay = retValue(val, 0, self.mStartDelay)
						elif opt == "pause" and val:
							self.mLoopTimeout = retValue(val, 0, self.mLoopTimeout)
						elif opt == "oneshot" and val:
							self.mOneShot = retValue(val, 0, self.mOneShot)
						elif opt =="repeat" and val:
							self.mRepeat = retValue(val, 0, self.mRepeat)
						elif opt =="always" and val:
							self.mAlways = retValue(val, 0, self.mAlways)
						elif opt =="startpoint" and val:
							self.mStartPoint = int(val)
						elif opt == "pagedelay" and val:
							self.mPageDelay = retValue(val, 0, self.mPageDelay)
						elif opt == "pagelength" and val:
							self.mPageLength = retValue(val, 0, self.mPageLength)
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		ret = Renderer.applySkin(self, desktop, screen)
		
		if self.mOneShot: self.mOneShot = max(self.mStepTimeout, self.mOneShot)
		if self.mLoopTimeout: self.mLoopTimeout = max(self.mStepTimeout, self.mLoopTimeout)
		if self.mPageDelay: self.mPageDelay = max(self.mStepTimeout, self.mPageDelay)
		
		self.test_label.setFont(self.txfont)
		if not (self.txtflags & RT_WRAP):
			self.test_label.setNoWrap(1)
		self.test_label.setVAlign(valign)
		self.test_label.setHAlign(self.halign)
		self.test_label.move( ePoint(self.W,self.H) )
		self.test_label.resize( eSize(self.W,self.H) )
		# test for auto correction text height:
		if self.direction in (TOP,BOTTOM):
			from enigma import fontRenderClass
			flh = int(fontRenderClass.getInstance().getLineHeight(self.txfont) or self.txfont.pointSize/6 + self.txfont.pointSize)
			self.test_label.setText("WQq")
			if flh > self.test_label.calculateSize().height():
				self.lineHeight = flh
			self.test_label.setText("")
		return ret

	def doSuspend(self, suspended):
		if suspended:
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.changed((self.CHANGED_DEFAULT,))

	def connect(self, source):
		Renderer.connect(self, source)

	def changed(self, what):
		if not self.mTimer == None: self.mTimer.stop()
		if what[0] == self.CHANGED_CLEAR:
			self.txtext = ""
			if self.instance:
				self.instance.clear(self.bcolor)
		else:
			self.txtext = self.source.text or ""
			if self.instance and not self.calcMoving():
				self.drawText(self.X, self.Y, self.W, self.H)

	def drawText(self, X, Y, W, H):
		self.instance.clear(self.bcolor)
		
		if not self.scolor == None:
			self.instance.writeText( eRect(X-self.soffset[0], Y-self.soffset[1], W, H), self.scolor, self.bcolor, self.txfont, self.txtext, self.txtflags )
			self.instance.writeText( eRect(X, Y, W, H), self.fcolor, self.scolor, self.txfont, self.txtext, self.txtflags )
		else:
			self.instance.writeText( eRect(X-self.soffset[0], Y-self.soffset[1], W, H), self.fcolor, self.bcolor, self.txfont, self.txtext, self.txtflags )

	def calcMoving(self):
		if self.txtext == "" or \
		   self.type == NONE or \
		   self.test_label == None:
			return False
		
		self.test_label.setText(self.txtext)
		text_size = self.test_label.calculateSize()
		text_width = text_size.width()
		text_height = text_size.height()
		self.mStop = None
		# text height correction if necessary:
		if self.lineHeight and self.direction in (TOP,BOTTOM):
			text_height = max(text_height, (text_height + self.lineHeight - 1) / self.lineHeight * self.lineHeight)
		
#		self.type =		0 - NONE; 1 - RUNNING; 2 - SWIMMING; 3 - AUTO(???)
#		self.direction =	0 - LEFT; 1 - RIGHT;   2 - TOP;      3 - BOTTOM
#		self.halign =		0 - LEFT; 1 - RIGHT;   2 - CENTER;   3 - BLOCK

		if self.direction in (LEFT,RIGHT):
			if not self.mAlways and text_width <= self.W:
				return False
			if self.type == RUNNING:
				self.A = self.X - text_width - self.soffset[0] - abs(self.mStep)
				self.B = self.W - self.soffset[0] + abs(self.mStep)
				if self.direction == LEFT:
					self.mStep = -abs(self.mStep)
					self.mStop = self.X
					self.P = self.B
				else:
					self.mStep = abs(self.mStep)
					self.mStop = self.B - text_width + self.soffset[0] - self.mStep
					self.P = self.A
				if not self.mStartPoint == None:
					if self.direction == LEFT:
						self.mStop = self.P = max(self.A, min(self.W, self.mStartPoint))
					else:
						self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - text_width + self.soffset[0]))
			elif self.type == SWIMMING:
				if text_width < self.W:
					self.A = self.X + 1			# incomprehensible indent '+ 1' ???
					self.B = self.W - text_width - 1	# incomprehensible indent '- 1' ???
					if self.halign == LEFT:
						self.P = self.A
						self.mStep = abs(self.mStep)
					elif self.halign == RIGHT:
						self.P = self.B
						self.mStep = -abs(self.mStep)
					else: # if self.halign in (CENTER, BLOCK):
						self.P = int(self.B / 2)
						self.mStep = (self.direction == RIGHT) and abs(self.mStep) or -abs(self.mStep)
				else:
					if text_width == self.W:
						text_width += max(2, text_width/20)
					self.A = self.W - text_width
					self.B = self.X
					if self.halign == LEFT:
						self.P = self.B
						self.mStep = -abs(self.mStep)
					elif self.halign == RIGHT:
						self.P = self.A
						self.mStep = abs(self.mStep)
					else: # if self.halign in (CENTER, BLOCK):
						self.P = int(self.A / 2)
						self.mStep = (self.direction == RIGHT) and abs(self.mStep) or -abs(self.mStep)
			else:
				return False
		elif self.direction in (TOP,BOTTOM):
			if not self.mAlways and text_height <= self.H:
				return False
			if self.type == RUNNING:
				self.A = self.Y - text_height - self.soffset[1] - abs(self.mStep)
				self.B = self.H - self.soffset[1] + abs(self.mStep)
				if self.direction == TOP:
					self.mStep = -abs(self.mStep)
					self.mStop = self.Y
					self.P = self.B
				else:
					self.mStep = abs(self.mStep)
					self.mStop = self.B - text_height + self.soffset[1] - self.mStep
					self.P = self.A
				if not self.mStartPoint == None:
					if self.direction == TOP:
						self.mStop = self.P = max(self.A, min(self.H, self.mStartPoint))
					else:
						self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - text_height + self.soffset[1]))
			elif self.type == SWIMMING:
				if text_height < self.H:
					self.A = self.Y
					self.B = self.H - text_height
					if self.direction == TOP:
						self.P = self.B
						self.mStep = -abs(self.mStep)
					else:
						self.P = self.A
						self.mStep = abs(self.mStep)
				else:
					if text_height == self.H:
						text_height += max(2, text_height/40)
					self.A = self.H - text_height
					self.B = self.Y
					if self.direction == TOP:
						self.P = self.B
						self.mStep = -abs(self.mStep)
						self.mStop = self.B
					else:
						self.P = self.A
						self.mStep = abs(self.mStep)
						self.mStop = self.A
			else:
				return False
		else:
			return False

		self.xW = max(self.W, text_width)
		self.xH = max(self.H, text_height)
		if self.mStartDelay:
			if self.direction in (LEFT,RIGHT):
				self.drawText(self.P, self.Y, self.xW, self.xH)
			else: # if self.direction in (TOP,BOTTOM):
				self.drawText(self.X, self.P, self.xW, self.xH)
		self.mCount = self.mRepeat
		self.mTimer.start(self.mStartDelay,True)
		return True

	def movingLoop(self):
		if self.A <= self.P <= self.B:
			if self.direction in (LEFT,RIGHT):
				self.drawText(self.P, self.Y, self.xW, self.xH)
			else: # if self.direction in (TOP,BOTTOM)
				self.drawText(self.X, self.P, self.xW, self.xH)
			timeout = self.mStepTimeout
			if (self.mStop != None) and (self.mStop + abs(self.mStep) > self.P >= self.mStop):
				if (self.type == RUNNING) and (self.mOneShot > 0):
					if (self.mRepeat > 0) and (self.mCount-1 <= 0): return
					timeout = self.mOneShot
				elif (self.type == SWIMMING) and (self.mPageLength > 0) and (self.mPageDelay > 0):
					if (self.direction == TOP) and (self.mStep < 0):
						self.mStop -= self.mPageLength
						if self.mStop < self.A:
							self.mStop = self.B
						timeout = self.mPageDelay
					elif (self.direction == BOTTOM) and (self.mStep > 0):
						self.mStop += self.mPageLength
						if self.mStop > self.B:
							self.mStop = self.A
						timeout = self.mPageDelay
		else:
			if self.mRepeat > 0:
				self.mCount -= 1
				if self.mCount == 0: return
			timeout = self.mLoopTimeout
			if self.type == RUNNING:
				if self.P < self.A:
					self.P = self.B + abs(self.mStep)
				else:
					self.P = self.A - abs(self.mStep)
			else:
				self.mStep = -self.mStep
		
		self.P += self.mStep
		self.mTimer.start(timeout,True)
