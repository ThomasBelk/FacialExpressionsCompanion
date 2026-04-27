## Companion App (Optional for Gameplay, Necessary for Facial Expressions)

**Real Facial Expressions uses a companion app to track your facial expressions in real time.**

**Now can receive tracking from VTube Studio!**

**With the companion app:** Facial expressions are mirrored on your character using your webcam.

**Without the companion app:** You can still play the game normally, but facial animations will not be mirrored. Instead, the default Hytale idle animations will play.

Download the companion app here: [Real Facial Expressions Companion App](https://github.com/ThomasBelk/FacialExpressionsCompanion/releases/latest)

**Note: The plugin only transmits facial blendshape data and a derived eye look direction. No other video or image data ever leaves your PC.**

## Disclaimers
- Real Facial Expressions uses a companion app to send data to the server. The connection fields are intended to remain private. Try not to leak them, or you will at least have to reset your faceId with **/rfe resetFaceId**
- There will very likely be **conflicts** with other player animation plugins, particularly those that modify **Server/Models/Human/Player.json**.

## Licence
The project is currently licensed as All Rights Reserved. I plan to revisit this after further researching more licensing options.
## Installation Guide
1) Install the companion app with the installer [Real Facial Expressions Companion App](https://github.com/ThomasBelk/FacialExpressionsCompanion/releases/latest).
2) Connect to the desired server in Hytale.
3) Run **/rfe faceId** in-game and copy the generated ID into the companion app.
4) Enter the server IP and the port into the companion app. The default port is **25590**.
    - Note: your faceId should not change so you will only have to do this once.
5) Once you tab back into the game, your expressions should be mirrored on your character.

## Building From Python Code
This is mostly for me lol.
### Building Updater:
Updater likely will not change unless there is a bug, but here is how to do it.
- In venv run `pyinstaller --noconfirm RealFacialExpressionsUpdater.spec`
### Building Launcher:
Also will likely not change unless there is a bug
- In venv run `pyinstaller --noconfirm .\RealFacialExpressionsLauncher.spec`

### Building App
- First change version name in update_checker.
- Make sure `INCLUDE_PRE_RELEASE = False`
- In venv run `pyinstaller --noconfirm RealFacialExpressions.spec`
  -  If you have a new folder that needs to be included change the spec
- Change version number in Inno Setup
- Compile and Deploy