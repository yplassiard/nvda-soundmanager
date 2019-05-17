# *-* coding: utf-8 *-*


import globalPluginHandler
import tones
import ui
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from . import pycaw
from pycaw.pycaw import AudioUtilities
del sys.path[-1]

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = _("Sound Manager")
	enabled = False
	curAppName = None


	def sayFocusedApp(self, session):
		name = None
		try:
			name = session.getDisplayName()
		except:
			pass
		if name is None:
			name = session.Process.name().replace(".exe", "")
		ui.message(name)

	def script_muteApp(self, gesture):
		session,volume = self.findSessionByName(self.curAppName)
		if session == None and self.curAppName is not None:
			tones.beep(200, 500)
			return
		volume.SetMute(not volume.GetMute(), None)



	def script_volumeUp(self, gesture):
		session,volume = self.findSessionByName(self.curAppName)
		if session == None and self.curAppName is not None:
			tones.beep(200, 500)
			return
		volume.SetMasterVolume(volume.GetMasterVolume() + 0.025, None)

	def script_volumeDown(self, gesture):
		session,volume = self.findSessionByName(self.curAppName)
		if session == None and self.curAppName is not None:
			tones.beep(200, 500)
			return
		volume.SetMasterVolume(volume.GetMasterVolume() - 0.025, None)

	def script_nextApp(self, gesture):
		audioSessions = AudioUtilities.GetAllSessions()
		sessions = []
		for session in audioSessions:
			if session.Process is not None:
				sessions.append(session)
		newSession = None
		idx = 0
		nrSessions = len(sessions)
		while idx < nrSessions:
			session = sessions[idx]
			if self.curAppName == session.Process.name():
				newSession = sessions[idx + 1] if idx + 1 < nrSessions else sessions[0]
			idx += 1
		if newSession == None:
			newSession = sessions[0]
		self.curAppName = newSession.Process.name()
		self.sayFocusedApp(newSession)

	def script_previousApp(self, gesture):
		audioSessions = AudioUtilities.GetAllSessions()
		sessions = []
		for session in audioSessions:
			if session.Process is not None:
				sessions.append(session)
		newSession = None
		idx = 0
		nrSessions = len(sessions)
		while idx < nrSessions:
			session = sessions[idx]
			if self.curAppName == session.Process.name():
				newSession = sessions[idx - 1]
			idx += 1
		if newSession == None:
			newSession = sessions[0]
		self.curAppName = newSession.Process.name()
		self.sayFocusedApp(newSession)

	def script_soundManager(self, gesture):
		self.enabled = not self.enabled
		if self.enabled is True:
			tones.beep(660, 100)
			self.bindGesture("kb:uparrow", "volumeUp")
			self.bindGesture("kb:downarrow", "volumeDown")
			self.bindGesture("kb:leftarrow", "previousApp")
			self.bindGesture("kb:rightarrow", "nextApp")
						self.bindGesture("kb:m", "muteApp")
		else:
			tones.beep(440, 100)
			self.clearGestureBindings()
			self.bindGestures(self.__gestures)

	script_soundManager.__doc__ = _("""Toggle volume control adjustment on or off""")

	def findSessionByName(self, name):
		sessions = AudioUtilities.GetAllSessions()
		for session in sessions:
			if session.Process and session.Process.name() == name or name is None:
				volume = session.SimpleAudioVolume
				return session,volume
		return None,None

	__gestures = {
		"kb:nvda+shift+v": "soundManager",
	}

