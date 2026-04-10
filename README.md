# MAKIAVELICA

> [!WARNING]
> This is a personal project and a probably not a really good optimized bot

## REQUIREMENTS

> [!IMPORTANT]
> this is not a guide to create your first bot, so im assuming you have you own already,
> check this [guide](https://docs.discord.com/developers/quick-start/getting-started) if you want one

* python >= 3.12
* discord.py
* yt-dlp
* ffmpeg (If you are on windows its probably better that you use winget, if you are in any other other platform use the recomended 
    form of installation corresponding to your os)

> [!NOTE]
> Check requirements.txt for the right package versions

## INSTALLATION

First i recommend to set up a venv to not install locally the necessary packages

```python
python -m venv <yourproject>

```

Then you'll need to clone this repository

`git clone https://github.com/conceptoHH/dc_bot_maki.git`

Install from requirements.txt

```PowerShell
#Activate from script
Script\activate.bat 

#if you are on linux
Source Scripts\activate

#Install
python -m pip install -r requirements.txt

``` 

then you are setup to modify the bot check example.env to know what values to change

lastly just run main.py

`python main.py`

