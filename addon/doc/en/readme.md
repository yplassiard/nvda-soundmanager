# NVDA Sound Manager
## Author
- Yannick Plassiard
- Danstiv
- Beqa Gozalishvili

## Download link
https://github.com/yplassiard/nvda-soundmanager/releases/download/v2019.07/soundmanager-2019.07.nvda-addon

## Introduction
This addon aims to provide more advanced sound functionalities within NVDA.
## Features
### Volume Control
Make volume control more haney: Pressing the NVDA+Shift+v shortcut, you can then use the arrow keys to select which application you want, and then use the up and down keys to adjust its playback volume. No more use the Windows sound volume anymore. When done, simply press the NVDA+Shift+v again to get back to the default behavior.

## Shortcuts
- NVDA+Shift+v: enables volume adjustment on or off. A high beep will indicate that the feature is active, a low beep will sound to indicate its deactivation.

When activated the following shortcuts can be used:
- UpArrow: turn volume up
- DownArrow: turn volume down
- LeftArrow: Go to previous app that is playing audio
- RightArrow: Go to next app that is playing audio
- m: mute or unmute the focused app
- control + Up arrow: raises the current application's volume.
- control + Down arrow: lowers the current application's volume.

## Settings
A "Sound Manager" category within the NVDA Setting's dialog allows you to customize the addon behavior:
- Announce volume changes: Instructs the add-on to say the new volume values when changing it.
- Announce app change when cycling: Instructs the add-on to speak the application name when cycligng through app volumes.
