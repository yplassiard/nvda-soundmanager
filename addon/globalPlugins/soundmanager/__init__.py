# *-* coding: utf-8 *-*
# Sound Manager
#addon/globalPlugins/sound-manager/__init__.py
#A part of the NVDA Sound Manager add-on
#Copyright (C) 2019 Yannick PLASSIARD, Danstiv, Beqa Gozalishvili
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
import speech
import tones
import ui
import wx
import config

import gui
# Local requirements (Pycaw and its dependencies)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from . import pycaw
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
del sys.path[-1]
addonHandler.initTranslation()

# Configuration specifications and default section name.
SM_CFG_SECTION = "soundManager"

confspec = {
	"sayVolumeChange": "boolean(default=true)",
	"sayAppChange": "boolean(default=true)",
}
config.conf.spec[SM_CFG_SECTION] = confspec

# message contexts
SM_CTX_ERROR = 1
SM_CTX_APP_CHANGE = 2
SM_CTX_VOLUME_CHANGE = 3

# A fake Process class with mininal implementation to comply to the cycleThroughApps plugin method.

class MasterVolumeFakeProcess(object):
	def __init__(self, name):
		self._name = name
	def name(self):
		return self._name

#
# Main global plugin class
#


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	# Translators: The name of the add-on presented to the user.
	scriptCategory = _("Sound Manager")
	volumeChangeStep = 0.02
	enabled = False
	curAppName = None


	def __init__(self, *args, **kwargs):
		super(globalPluginHandler.GlobalPlugin, self).__init__(*args, **kwargs)
		self.readConfiguration()
		self.devices = AudioUtilities.GetSpeakers()
		self.interface = self.devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
		self.master_volume = cast(self.interface, POINTER(IAudioEndpointVolume))
		self.master_volume.SetMasterVolume = self.master_volume.SetMasterVolumeLevelScalar
		self.master_volume.GetMasterVolume = self.master_volume.GetMasterVolumeLevelScalar
		self.master_volume.name = _('Master volume')
		self.master_volume.Process = MasterVolumeFakeProcess(self.master_volume.name)
		self.master_volume.getDisplayName = lambda: self.master_volume.name
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(SoundManagerPanel)
		if hasattr(config, "post_configProfileSwitch"):
			config.post_configProfileSwitch.register(self.handleConfigProfileSwitch)
		else:
			config.configProfileSwitched.register(self.handleConfigProfileSwitch)
	def handleConfigProfileSwitch(self):
		self.readConfiguration()
	def readConfiguration(self):
		self.sayAppChange = config.conf[SM_CFG_SECTION]["sayAppChange"]
		self.sayVolumeChange = config.conf[SM_CFG_SECTION]["sayVolumeChange"]

	def message(self, ctx, msg, interrupt=False):
		if ctx == SM_CTX_VOLUME_CHANGE and self.sayVolumeChange:
			speech.cancelSpeech() if interrupt else None
			ui.message(msg)
		elif ctx == SM_CTX_APP_CHANGE and self.sayAppChange:
			speech.cancelSpeech() if interrupt else None
			ui.message(msg)
		elif ctx == SM_CTX_ERROR:
			ui.message(msg)
		return

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
		session,volume = self.findSessionByName(self.curAppName)
		if session is None:
			if self.curAppName != self.master_volume.name:
				# Translators: Spoken message when unablee to change audio volume for the given application.
				self.message(SM_CTX_ERROR, _("Unable to retrieve current application."))
				return
			else:
				# Translators: Cannot mute the master volume.
				self.message(SM_CTX_ERROR, _("Cannot mute the master volume."))
				return

		muted = volume.GetMute()
		volume.SetMute(not muted, None)
		if not muted:
			# Translator: Spoken message indicating that the app's sound is now muted.
			self.message(SM_CTX_VOLUME_CHANGE, _("{app} muted").format(app=self.getAppNameFromSession(session)))
		else:
			# Translators: Spoken message indicating that the app's audio is now unmuted.
			self.message(SM_CTX_VOLUME_CHANGE, _("{app} unmuted").format(app=self.getAppNameFromSession(session)))

	def focusCurrentApplication(self, silent=False):
		obj = api.getFocusObject()
		appName = None
		try:
			appName = obj.appModule.appName
		except AttributeError:
			appName = None
		session,volume = self.findSessionByName(appName)
		if session is None:
			if not silent:
				# Translators: The current application does not pay audio.
				self.message(SM_CTX_ERROR, _("{app} is not playing any sound.".format(app=appName)))
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

	def script_onVolumeChanged(self, gesture):
		gesture.send()
		self.message(SM_CTX_VOLUME_CHANGE, str(int(round(round(self.master_volume.GetMasterVolume(), 2)*100, 0)))+'%', True)

	def changeVolume(self, volumeStep):
		session,volume = self.findSessionByName(self.curAppName)
		selector = self.master_volume
		if volume is None and self.curAppName is not None:
			# Translators: Spoken message when unablee to change audio volume for the given application
			self.message(SM_CTX_ERROR, _("Unable to retrieve current application."))
			return
		newVolume = volume.GetMasterVolume() + volumeStep
		if volumeStep > 0 and newVolume > 1:
			newVolume = 1.0
		elif volumeStep < 0 and newVolume < 0:
			newVolume = 0.0

		volume.SetMasterVolume(newVolume, None)
		# Translators: Message indicating the volume's percentage ("95%").
		self.message(SM_CTX_VOLUME_CHANGE, _("{volume}%".format(volume=int(round(newVolume * 100)))))

	def cycleThroughApps(self, goForward):
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
		self.message(SM_CTX_APP_CHANGE, self.getAppNameFromSession(newSession))

	def script_nextApp(self, gesture):
		self.cycleThroughApps(True)

	def script_previousApp(self, gesture):
		self.cycleThroughApps(False)

	def script_soundManager(self, gesture):
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

	# Translators: Main script help message.
	script_soundManager.__doc__ = _("""Toggle volume control adjustment on or off""")

	def findSessionByName(self, name):
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
		"kb:volumeDown": "onVolumeChanged",
		"kb:volumeUp": "onVolumeChanged"
	}
# The next class has been adapted from the ScreenCurtain module.


class SoundManagerPanel(gui.SettingsPanel):
	# Translators: This is the label for the Sound manager settings panel.
	title = _("Sound Manager")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.smSayVolumeChange = sHelper.addItem(wx.CheckBox(self, label=_("&announce volume changes")))
		self.smSayVolumeChange.SetValue(config.conf[SM_CFG_SECTION]["sayVolumeChange"])

		self.smSayAppChange = sHelper.addItem(wx.CheckBox(self, label=_("Announce a&pp names when cycling")))
		self.smSayAppChange.SetValue(config.conf[SM_CFG_SECTION]["sayAppChange"])

	def onSave(self):
		config.conf[SM_CFG_SECTION]["sayVolumeChange"] = self.smSayVolumeChange.IsChecked()
		config.conf[SM_CFG_SECTION]["sayAppChange"] = self.smSayAppChange.IsChecked()
		if hasattr(config, "post_configProfileSwitch"):
			config.post_configProfileSwitch.notify()
		else:
			config.configProfileSwitched.notify()
