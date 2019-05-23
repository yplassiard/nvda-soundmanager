# *-* coding: utf-8 *-*
#addon/globalPlugins/sound-manager/__init__.py
#A part of the NVDA Sound Manager add-on
#Copyright (C) 2019 Yannick PLASSIARD
#This file is covered by the GNU General Public License.
#See the file LICENSE for more details.
#
#This addon uses the following dependencies:
# pycaw - see the pycaw.LICENSE file for more details.

# System modules
import sys, os
# Windows Specific
from comtypes import CLSCTX_ALL
from ctypes import POINTER, cast


# NVDA core requirements
import globalPluginHandler
import addonHandler
import api
from speech import cancelSpeech
import tones
import ui
# Local requirements (Pycaw and its dependencies)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from . import pycaw
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
del sys.path[-1]
addonHandler.initTranslation()

class MasterVolumeFakeProcess(object):
	def __init__(self, name):
		self._name = name
	def name(self):
		return self._name

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	#. Translators: The name of the add-on presented to the user.
	scriptCategory = _("Sound Manager")
	volumeChangeStep = 0.05
	enabled = False
	curAppName = None


	def __init__(self, *args, **kwargs):
		super(globalPluginHandler.GlobalPlugin, self).__init__(*args, **kwargs)
		self.devices = AudioUtilities.GetSpeakers()
		self.interface = self.devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
		self.master_volume = cast(self.interface, POINTER(IAudioEndpointVolume))
		self.master_volume.SetMasterVolume = self.master_volume.SetMasterVolumeLevelScalar
		self.master_volume.GetMasterVolume = self.master_volume.GetMasterVolumeLevelScalar
		self.master_volume.name = _('Master volume')
		self.master_volume.Process = MasterVolumeFakeProcess(self.master_volume.name)
		self.master_volume.getDisplayName = lambda: self.master_volume.name


	def getAppNameFromSession(self, session):
		"""Returns an application's name formatted to be presented to the user from a given audio session."""

		name = None
		if session is None:
			return self.master_volume.name
		try:
			name = session.getDisplayName()
		except Exception as e:
			name = session.Process.name().replace(".exe", "")
		return name


	def script_muteApp(self, gesture):
		"""Mutes or unmute the focused application."""
		session,volume = self.findSessionByName(self.curAppName)
		if session is None:
			if self.curAppName is not None:
				#. Translators: Spoken message when unablee to change audio volume for the given application.
				ui.message(_("Unable to retrieve current application."))
				return
			else:
				#. Translators: Cannot mute the master volume.
				ui.message(_("Cannot mute the master volume."))
				return

		muted = volume.GetMute()
		volume.SetMute(not muted, None)
		if not muted:
			#. Translator: Spoken message indicating that the app's sound is now muted.
			ui.message(_("{app} muted").format(app=self.getAppNameFromSession(session)))
		else:
			#. Translators: Spoken message indicating that the app's audio is now unmuted.
			ui.message(_("{app} unmuted").format(app=self.getAppNameFromSession(session)))

	def focusCurrentApplication(self, silent=False):
		"""Selects the audio control for the current alsplication."""
		obj = api.getFocusObject()
		appName = None
		try:
			appName = obj.appModule.appName
		except AttributeError:
			appName = None
		if appName is None:
			if not silent:
				#. Translators: Unable to determine focused application's name.
				ui.message_("Unable to retrieve current application's name.")
			return False
		session,volume = self.findSessionByName(appName)
		if session is None:
			if not silent:
				#. Translators: The current application does not pay audio.
				ui.message(_("{app} is not playing any sound.".format(app=appName)))
			return False
		self.curAppName = appName
		return True

	def script_curAppVolumeUp(self, gesture):
		"""Increases the volume of focused application if it plays audio."""
		if self.focusCurrentApplication() is False:
			return
		self.changeVolume(self.volumeChangeStep)

	def script_curAppVolumeDown(self, gesture):
		"""Decreases the currently focused application's volume."""
		if self.focusCurrentApplication() is False:
			return
		self.changeVolume(-self.volumeChangeStep)

	def script_curAppMute(self, gesture):
		if self.focusCurrentApplication() is False:
			return
		self.script_muteApp(gesture)

	def script_volumeUp(self, gesture):
		"""Increases the volume of the selected application."""
		self.changeVolume(self.volumeChangeStep)
	def script_volumeDown(self, gesture):
		"""Decreases the volume of the selected application."""
		self.changeVolume(-self.volumeChangeStep)

	def script_volume_changed(self, gesture):
		gesture.send()
		cancelSpeech()
		ui.message(str(int(round(round(self.master_volume.GetMasterVolume(), 2)*100, 0)))+'%')

	def changeVolume(self, volumeStep):
		"""Adjusts the volume of the selected application using the given step value."""
		session,volume = self.findSessionByName(self.curAppName)
		selector = self.master_volume
		if volume is None and self.curAppName is not None:
			#. Translators: Spoken message when unablee to change audio volume for the given application
			ui.message(_("Unable to retrieve current application."))
			return
		newVolume = volume.GetMasterVolume() + volumeStep
		if volumeStep > 0 and newVolume > 1:
			newVolume = 1.0
		elif volumeStep < 0 and newVolume < 0:
			newVolume = 0.0

		volume.SetMasterVolume(newVolume, None)
		#. Translators: Message indicating the volume's percentage ("95%").
		ui.message(_("{volume}%".format(volume=int(round(newVolume * 100)))))

	def cycleThroughApps(self, goForward):
		"""Cycles through apps that are currently playing audio.
		The goForward parameter indicates whether we want to cycle forward or backward in the ring.
		"""
		audioSessions = AudioUtilities.GetAllSessions()
		sessions = []
		sessions.append(self.master_volume)
		for session in audioSessions:
			if session.Process is not None:
				sessions.append(session)
		newSession = None
		idx = 0
		nrSessions = len(sessions)
		while idx < nrSessions:
			session = sessions[idx]
			if self.curAppName == session.Process.name():
				if goForward:
					newSession = sessions[idx + 1] if idx + 1 < nrSessions else sessions[0]
				else:
					newSession = sessions[idx - 1]
			idx += 1
		if newSession is None:
			newSession = sessions[0]
		self.curAppName = newSession.Process.name() if newSession.Process is not None else newSession.name
		ui.message(self.getAppNameFromSession(newSession))

	def script_nextApp(self, gesture):
		"""Focus the next application that is playing audio."""
		self.cycleThroughApps(True)

	def script_previousApp(self, gesture):
		"""Focus the previous application that is playing audio."""
		self.cycleThroughApps(False)

	def script_soundManager(self, gesture):
		"""Activates or deactivates the sound manager mode.
		When activated, this scripts dynamically binds other gestures to perform sound manager
		commands (adjusting the volume for instance). When deactivating, gestures are restored to
		their default behavior.
		"""
		self.enabled = not self.enabled
		if self.enabled is True:
			tones.beep(660, 100)

			# Next gesture is bound to disable the volume control mode by pressing escape.
			self.bindGesture("kb:escape", "soundManager")
			self.bindGesture("kb:control+uparrow", "curAppVolumeUp")
			self.bindGesture("kb:control+downarrow", "curAppVolumeDown")
			self.bindGesture("kb:control+m", "curAppMute")
			self.bindGesture("kb:uparrow", "volumeUp")
			self.bindGesture("kb:downarrow", "volumeDown")
			self.bindGesture("kb:leftarrow", "previousApp")
			self.bindGesture("kb:rightarrow", "nextApp")
			self.bindGesture("kb:m", "muteApp")
			if not self.focusCurrentApplication(True):
				self.curAppName = self.master_volume.name

		else:
			tones.beep(440, 100)
			self.clearGestureBindings()
			self.bindGestures(self.__gestures)

	#. Translators: Main script help message.
	script_soundManager.__doc__ = _("""Toggle volume control adjustment on or off""")

	def findSessionByName(self, name):
		"""Finds an audio session according to the process's name ("chrome.exe")."""
		if name == self.master_volume.name:
			return None,self.master_volume
		sessions = AudioUtilities.GetAllSessions()
		for session in sessions:
			if session.Process is not None:
				pName = session.Process.name()
				if name is None or name.lower() in pName.lower():
					volume = session.SimpleAudioVolume
					return session,volume
		return None,None

	__gestures = {
		"kb:nvda+shift+v": "soundManager",
"kb:volumeDown": "volume_changed",
"kb:volumeUp": "volume_changed"
	}

