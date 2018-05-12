from cv2 import imread, minMaxLoc, matchTemplate
from glob import glob
from os.path import basename

files = glob("cards/*.png")

board1 = imread("prints/tableCard3.png")
board2 = imread("prints_debug/tableCard2.png")
for myfile in files:
        if basename(myfile).split(".")[0] != "player_hole":
            image = imread(myfile)
            print basename(myfile).split(".")[0] + "\t" + str(minMaxLoc(matchTemplate(board1, image, 3))[0]) + "\t" + str(minMaxLoc(matchTemplate(board2, image, 3))[0])
