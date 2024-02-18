#!/usr/bin/python
import sys
import glob
import re
import os
from typing import Text
import json

if len(sys.argv) >= 2:
    rootPath = sys.argv[1]
else:
    rootPath = '/etc/sway/config'


def readFile(filePath, source='system'):
    paths = glob.glob(os.path.expandvars(filePath))
    allLines = []
    for path in paths:
        currentSource = 'user' if os.path.expanduser('~') in os.path.abspath(path) else 'system'
        try:
            with open(path, "r") as file:
                lines = file.readlines()
                for line in lines:
                    allLines.append((line, currentSource))
        except Exception as e:
            print(f"Error reading {path}: {str(e)}")
    
    finalLines = []
    for line, currentSource in allLines:
        if re.match(r'^include\s+(.+?)$', line):
            includePath = re.findall(r'^include\s+(.+?)$', line)[0]
            includeLines = readFile(includePath, currentSource)
            finalLines.extend(includeLines)
        else:
            finalLines.append((line, currentSource))

    return finalLines


lines = readFile(rootPath)


def findKeybindingForLine(lineNumber: int, lines: list[tuple[str, str]]):
    if lineNumber + 1 < len(lines):
        nextLine, _ = lines[lineNumber + 1]
        keybindingParts = nextLine.split()
        if keybindingParts:
            return keybindingParts[1]
    return "Not found"


class DocsConfig:
    category: Text
    action: Text
    keybinding: Text


def getDocsConfig(lines):
    docsConfig = []
    for index, (line, source) in enumerate(lines):
        match = re.match(r"^## (?P<category>.+?) // (?P<action>.+?)\s+(// (?P<keybinding>.+?))*##", line)
        if match:
            config = DocsConfig()
            config.category = match.group('category')
            config.action = match.group('action')
            config.keybinding = match.group('keybinding')
            if config.keybinding is None:
                config.keybinding = findKeybindingForLine(index, lines)
            config.isUserConfig = (source == 'user')
            docsConfig.append(config)
    return docsConfig


def getSymbolDict(lines):
    setRegex = r"^set\s+(?P<variable>\$.+?)\s(?P<value>.+)?"
    dictionary = {}
    for line, _ in lines:
        match = re.match(setRegex, line)
        if match:
            if match.group('variable'):
                dictionary[match.group('variable')] = match.group('value')
    return dict(dictionary)


translations = {
    'Mod1': "Alt",
    'Mod2': "NumLk",
    'Mod3': "בּ",
    'Mod4': "",
    'Mod5': "Scroll",
    'question': "?",
    'space': "␣",
    'minus': "-",
    'plus': '+',
    'Return': "Enter",
    'XF86AudioRaiseVolume': "",
    'XF86AudioLowerVolume': "",
    'XF86AudioMute': "",
    'XF86AudioMicMute': '',
    'XF86MonBrightnessUp': "",
    'XF86MonBrightnessDown': "",
    'XF86PowerOff': "",
    'XF86TouchpadToggle': "Toggle Touchpad"
}


def translate(word: Text, dictionary: dict):
    try:
        return dictionary[word.strip()]
    except KeyError:
        return word.strip()


def replaceBindingFromMap(binding: Text, dictionary: dict):
    elements = binding.split('+')
    resultElements = []
    for el in elements:
        translation = translate(translate(el, dictionary), translations)
        resultElements = resultElements + [translation]

    return " + ".join(resultElements)


def sanitize(configs: list[DocsConfig], symbolDict: dict):
    for index, config in enumerate(configs):
        config.keybinding = replaceBindingFromMap(
            config.keybinding, symbolDict)
        configs[index] = config
    return configs


def getDocsList(lines: list[str]):
    docsConfig = getDocsConfig(lines)
    symbolDict = getSymbolDict(lines)
    sanitizedConfig = sanitize(docsConfig, symbolDict)
    uniqueConfig = {}
    for config in sanitizedConfig:
        key = config.action
        if key not in uniqueConfig or (config.isUserConfig and not uniqueConfig[key].isUserConfig):
            uniqueConfig[key] = config

    return list(uniqueConfig.values())
    
docsList = getDocsList(lines)

result = []
for config in docsList:
    result = result + [{'category': config.category,
                        'action': config.action, 'keybinding': config.keybinding}]
print(json.dumps(result))
