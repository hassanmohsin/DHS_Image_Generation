import json
import random
from os import listdir
from os.path import isfile, join

from PIL import Image

from image_funs import advPaste
from poisson_disc_fun import poissonDisc


def allFiles(path):  # Gets a list of all the files in a folder
    files = [f for f in listdir(path) if isfile(join(path, f))]
    return files


def getKeysByValue(dictOfElements, valueToFind, index):
    listOfKeys = list()
    listOfItems = dictOfElements.items()
    for item in listOfItems:
        if item[index] == valueToFind:
            listOfKeys.append(item[0])
    return listOfKeys


def colorRandomizer(dist, args):
    if dist == "U":
        newColor = (
            int(round(random.uniform(args[0][0], args[0][1]))),
            int(round(random.uniform(args[1][0], args[1][1]))),
            int(round(random.uniform(args[2][0], args[2][1]))),
            int(round(random.uniform(args[3][0], args[3][1])))
        )
    if dist == "T":
        newColor = (
            int(round(random.triangular(args[0][0], args[0][1], args[0][2]))),
            int(round(random.triangular(args[1][0], args[1][1], args[1][2]))),
            int(round(random.triangular(args[2][0], args[2][1], args[2][2]))),
            int(round(random.triangular(args[3][0], args[3][1], args[3][2])))
        )
    if dist == "M":
        increments = 1
        newIndex = random.randint(0, len(args) - 2)
        newIncrement = random.randint(0, increments)
        newRed = ((args[newIndex + 1][0] - args[newIndex][0]) / (increments + 1)) * newIncrement + args[newIndex][0]
        newGreen = ((args[newIndex + 1][1] - args[newIndex][1]) / (increments + 1)) * newIncrement + args[newIndex][1]
        newBlue = ((args[newIndex + 1][2] - args[newIndex][2]) / (increments + 1)) * newIncrement + args[newIndex][2]
        newAlpha = ((args[newIndex + 1][3] - args[newIndex][3]) / (increments + 1)) * newIncrement + args[newIndex][3]
        newColor = (int(round(newRed)), int(round(newGreen)), int(round(newBlue)), int(round(newAlpha)))
    return newColor


def genRandomizer(dist, params):
    if dist == "U":
        rand_num = random.uniform(params[0], params[1])
    elif dist == "T":
        rand_num = random.triangular(params[0], params[1], params[2])
    return rand_num


def imageGen(json_dir, mpeg7_dir):
    with open(json_dir) as f:
        json_data = json.load(f)

    params = json_data['params']
    find_images = json_data['find_images']
    excluded_images = json_data['excluded_images']
    save_dir = json_data['save_dir']
    save_name = json_data['save_name']

    fileList = allFiles(mpeg7_dir)

    # remove excluded images
    for item in excluded_images:
        fileList.remove(item["name"])

    # make an empty dictionary to keep track of the images
    imageDic = {}

    # make the background
    composite = Image.new('RGBA', (params["background"]["width"], params["background"]["height"]),
                          color=params["background"]["color"])

    # pre-generate all the image center points
    centerPoints = poissonDisc(params["background"]["width"], params["background"]["height"], params["centers"]["r"],
                               params["centers"]["k"])

    # palce all the random images
    num = 0
    for newCenter in centerPoints:
        new_entry = {
            num: {
                "imageDir": fileList[random.randint(0, len(fileList) - 1)],
                "center": newCenter,
                "scale": genRandomizer(params["scale"]["dist"], params["scale"]["params"]),
                "rotation": genRandomizer(params["rotation"]["dist"], params["rotation"]["params"]),
                "color": colorRandomizer(
                    params["color"]["dist"],
                    params["color"]["args"]
                )
            }
        }
        imageDic.update(new_entry)
        num += 1

    # update the find images
    findIndices = []
    for item in find_images:
        imageNum = int(round((1 - item["depth"]) * len(centerPoints), 0))
        imageDic[imageNum]["imageDir"] = item["name"]
        findIndices.append(imageNum)

    # start pasting images
    for key in imageDic:
        newImageDir = imageDic[key]["imageDir"]
        newImage = Image.open(mpeg7_dir + newImageDir)
        composite = advPaste(
            newImage,
            composite,
            imageDic[key]["center"],
            imageDic[key]["scale"],
            imageDic[key]["rotation"],
            imageDic[key]["color"]
        )

    # save the final image
    composite.save(save_dir + save_name + ".png", 'PNG')

    # make the easy find image
    for i in findIndices:
        findImageDir = imageDic[i]["imageDir"]
        newImage = Image.open(mpeg7_dir + findImageDir)
        composite = advPaste(
            newImage,
            composite,
            imageDic[i]["center"],
            imageDic[i]["scale"],
            imageDic[i]["rotation"],
            (255, 255, 255, 255)
        )

    # save the easy find image
    composite.save(save_dir + save_name + "-find.png", 'PNG')

    # make json file
    json_dic = {
        "save_dir": save_dir,
        "save_name": save_name,
        "params": params,
        "find_images": find_images,
        "excluded_images": excluded_images,
        "results": imageDic
    }

    with open(save_dir + save_name + ".json", 'w') as json_file:
        json.dump(json_dic, json_file, indent=4)
