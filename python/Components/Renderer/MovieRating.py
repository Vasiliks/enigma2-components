# -*- coding: UTF-8 -*-
#Coders by Nikolasi
# v1.2
# code otimization (by Sirius)
# fix searchPaths (by Sirius)
# py3 fix

from Components.Renderer.Renderer import Renderer
from Components.Converter.Poll import Poll
from enigma import ePixmap, eEnv
from Tools.Directories import resolveFilename ,SCOPE_SKIN_IMAGE, SCOPE_CURRENT_SKIN
import os

class MovieRating(Renderer, Poll):
	__module__ = __name__
	searchPaths = ('/usr/share/enigma2/%s/','/media/hdd/%s/', '/media/usb/%s/', '/media/sdb1/%s/', '/media/sdb2/%s/')

	def __init__(self):
		Poll.__init__(self)
		Renderer.__init__(self)
		self.path = 'starsbar'
		self.nameCache = {}
		self.pngname = ''

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value,) in self.skinAttributes:
			if (attrib == 'path'):
				self.path = value
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		self.poll_interval = 2000
		self.poll_enabled = True
		if self.instance:
			pngname = ''
			if (what[0] != self.CHANGED_CLEAR):
				sname = self.source.text
				pngname = self.nameCache.get(sname, '')
				if (pngname == ''):
					pngname = self.findPicon(sname)
					if (pngname != ''):
						self.nameCache[sname] = pngname
			if (pngname == ''):
				pngname = self.nameCache.get('00', '')
				if (pngname == ''):
					pngname = self.findPicon('00')
					self.nameCache['00'] = pngname
			if (self.pngname != pngname):
				self.instance.setPixmapFromFile(pngname)
				self.pngname = pngname

	def findPicon(self, serviceName):
		IMAGE_PATH2 = resolveFilename(SCOPE_CURRENT_SKIN, 'starsbar')
		path2 = resolveFilename(SCOPE_SKIN_IMAGE, IMAGE_PATH2)
		if os.path.exists(path2):
			pngname = ((path2 + "/" + serviceName) + ".png")
			if os.path.exists(pngname):
				return pngname
		else:
			for path in self.searchPaths:
				pngname = (((path % self.path) + serviceName) + ".png")
				if os.path.exists(pngname):
					return pngname
		return ''

