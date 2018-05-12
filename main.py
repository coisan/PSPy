from tkinter import Label, Frame, Button, Tk, messagebox, simpledialog
from PIL import Image, ImageGrab
from os.path import basename
from holdem_master import holdem_calc
from glob import glob
import pytesseract
import cv2
from win32 import win32gui
import math
import re

#Execution cycle time in ms
MAINLOOP_CYCLE_TIME = 2000

#Number of Monte Carlo simulations to achieve a <2s execution time
PREFLOP_SIMULATIONS = 160
FLOP_SIMULATIONS = 250
TURN_SIMULATIONS = 260
RIVER_SIMULATIONS = 300

WINDOW_POSITION = (0, 0)
WINDOW_SIZE = (0, 0)

POT_POSITION = (488, 275)
POT_SIZE = (360, 40)

ACTION_BUTTON_POSITION = (890, 860)
ACTION_BUTTON_SIZE = (174, 60)

BOARD_POSITION = (447, 331)
BOARD_CARD_DISTANCE = 91

PLAYER_POSITION = (587, 597)
PLAYER_CARD_DISTANCE = 85

PLAYERS_CARD_SIZE = (153, 26)
CARD_SIZE = (23, 58)

playerPositions = [(None, None), (215, 558), (62, 365), (133, 176), (393, 83), (788, 83), (1048, 176), (1120, 365), (968, 558)]
buttonPositions = [(771, 579), (428, 561), (251, 371), (301, 304), (476, 226), (858, 226), (1016, 304), (1061, 364), (906, 549)]

IMAGE_MATCH_THRESHOLD = 0.95
tessdata_config = '--tessdata-dir "C:\\Program Files (x86)\\Tesseract-OCR\\tessdata"'

NOT_IN_HAND = "Not in hand"
PREFLOP = "Preflop"
FLOP = "Flop"
TURN = "Turn"
RIVER = "River"

class WindowMgr:
    
    def __init__ (self):
        self._handle = None

    def _window_enum_callback(self, hwnd, wildcard):
        if re.match(wildcard, str(win32gui.GetWindowText(hwnd))) != None:
            self._handle = hwnd

    def find_window_wildcard(self, wildcard):
        self._handle = None
        win32gui.EnumWindows(self._window_enum_callback, wildcard)

    def set_foreground(self):
        win32gui.SetForegroundWindow(self._handle)

    def get_position(self):
        rect = win32gui.GetWindowRect(self._handle)
        return rect[0], rect[1]

    def get_size(self):
        rect = win32gui.GetWindowRect(self._handle)
        return rect[2]-rect[0], rect[3]-rect[1]

    def gen_handle(self):
        return self._handle

class MyGUI:

    def __init__(self, master):
        frame = Frame(master, width=200, height=20)
        frame.pack()
        self.Status = Label(master, text="State:", font = "TkDefaultFont 10 bold")
        self.Status.pack()
        self.CardOdds = Label(master, text="Winning odds:", font = "TkDefaultFont 10 bold")
        self.CardOdds.pack()
        self.PotOdds = Label(master, text="Pot odds:", font = "TkDefaultFont 10 bold")
        self.PotOdds.pack()
        self.PotSize = Label(master, text="Pot size:")
        self.PotSize.pack()
        self.CallSize = Label(master, text="Call size:")
        self.CallSize.pack()
        self.PlayerCards = Label(master, text="Player cards:")
        self.PlayerCards.pack()
        self.TableCards = Label(master, text="Table cards:")
        self.TableCards.pack()
        Start = Button(master, text="START", command=self.startCallback)
        Start.pack()
        Stop = Button(master, text="STOP", command=self.stopCallback)
        Stop.pack()
        master.after(MAINLOOP_CYCLE_TIME, getScreen, master)
    
    def startCallback(self):
        global run_flag, previous_status, previous_number_players
        global WINDOW_POSITION, WINDOW_SIZE
        previous_status = "init"
        previous_number_players = 0
        table_name = simpledialog.askstring("Table name", "Please specify table name (partial)")
        if table_name == "" or table_name is None:
            messagebox.showinfo("ERROR", "Table name not provided!")
        else:
            w = WindowMgr()
            w.find_window_wildcard(".*" + table_name + ".*")
            if w.gen_handle() == None:
                messagebox.showinfo("ERROR", "Table " + table_name + " not found!")
            else:
                w.set_foreground()
                WINDOW_POSITION = w.get_position()
                WINDOW_SIZE = w.get_size()
                messagebox.showinfo("START", "Bot started!")
                run_flag = True

    def stopCallback(self):
        global run_flag
        run_flag = False
        messagebox.showinfo("STOP", "Bot stopped!")

    def setTableCards(self, value):
        self.TableCards.config(text = "Table cards: " + value)

    def setPlayerCards(self, value):
        self.PlayerCards.config(text = "Player cards: " + value)

    def setCallSize(self, value):
        self.CallSize.config(text = "Call size: " + value)

    def setPotSize(self, value):
        self.PotSize.config(text = "Pot size: " + value)

    def setCardOdds(self, value):
        self.CardOdds.config(text = "Winning odds: " + value)

    def setPotOdds(self, value):
        self.PotOdds.config(text = "Pot odds: " + value)

    def setStatus(self, value, number):
        self.Status.config(text = "State: " + value + " (" + str(number) + ")")

def distance(x, y, point):
    return math.sqrt(math.pow(point[0]-x,2)+math.pow(point[1]-y,2))

def closest_point(x, y, array):
    min_distance = 1024
    min_index = -1
    for i in range (0, len(array)):
        dist = distance(x, y, array[i])
        if min_distance > dist:
            min_distance = dist
            min_index = i
    return min_index

def position(index, active_players):
    cnt = 0
    for i in range (index + 1, len(active_players)):
        if active_players[i] == 1:
            cnt = cnt + 1
    return cnt + 1
    
def getScreen(master):
    global run_flag

    if run_flag == True:

        screen = ImageGrab.grab()
        area = (WINDOW_POSITION[0], WINDOW_POSITION[1], WINDOW_POSITION[0]+WINDOW_SIZE[0], WINDOW_POSITION[1]+WINDOW_SIZE[1])
        PSwindow = screen.crop(area)
        PSwindow.save("prints/window.png")

        area = (POT_POSITION[0], POT_POSITION[1], POT_POSITION[0]+POT_SIZE[0], POT_POSITION[1]+POT_SIZE[1])
        pot = PSwindow.crop(area)
        pot.save("prints/pot.png")

        area = (ACTION_BUTTON_POSITION[0], ACTION_BUTTON_POSITION[1], ACTION_BUTTON_POSITION[0]+ACTION_BUTTON_SIZE[0], ACTION_BUTTON_POSITION[1]+ACTION_BUTTON_SIZE[1])
        playerAction = PSwindow.crop(area)
        playerAction.save("prints/action.png")

        area = (BOARD_POSITION[0], BOARD_POSITION[1], BOARD_POSITION[0]+5*BOARD_CARD_DISTANCE, BOARD_POSITION[1]+CARD_SIZE[1])
        tableCards = PSwindow.crop(area)
        for i in range (0,5):
            area = (i*BOARD_CARD_DISTANCE, 0, i*BOARD_CARD_DISTANCE+CARD_SIZE[0], CARD_SIZE[1])
            tableCard = tableCards.crop(area)
            tableCard.save("prints/tableCard" + str(i+1) + ".png")

        area = (PLAYER_POSITION[0], PLAYER_POSITION[1], PLAYER_POSITION[0]+2*PLAYER_CARD_DISTANCE, PLAYER_POSITION[1]+CARD_SIZE[1])
        playerCards = PSwindow.crop(area)
        for i in range (0,2):
            area = (i*PLAYER_CARD_DISTANCE, 0, i*PLAYER_CARD_DISTANCE+CARD_SIZE[0], CARD_SIZE[1])
            tableCard = playerCards.crop(area)
            tableCard.save("prints/playerCard" + str(i+1) + ".png")

        for i in range (1,9):
            area = (playerPositions[i][0], playerPositions[i][1], playerPositions[i][0]+PLAYERS_CARD_SIZE[0], playerPositions[i][1]+PLAYERS_CARD_SIZE[1])
            player = PSwindow.crop(area)
            player.save("prints/player" + str(i) + ".png")
            
        updateGUI(master)

    master.after(MAINLOOP_CYCLE_TIME, getScreen, master)

def updateGUI(master):
    tableCards = [None] * 5
    tableCards_found = [None] * 5
    playerCards = [None] * 2
    playerCards_found = [None] * 2
    
    for i in range (0,5):
        tableCards[i] = cv2.imread("prints/tableCard" + str(i+1) + ".png")
    for i in range (0,2):
        playerCards[i] = cv2.imread("prints/playerCard" + str(i+1) + ".png")

    files = glob("img/*.png")
    tableCards_max = [0, 0, 0, 0, 0]
    playerCards_max = [0, 0]
    for myfile in files:
        if basename(myfile) != "player_hole.png" and basename(myfile) != "button.png":
            image = cv2.imread(myfile)

            for i in range (0,5):
                result = cv2.matchTemplate(tableCards[i], image, cv2.TM_CCORR_NORMED)
                if tableCards_max[i] < cv2.minMaxLoc(result)[1] and cv2.minMaxLoc(result)[1] > IMAGE_MATCH_THRESHOLD:
                    tableCards_max[i] = cv2.minMaxLoc(result)[1]
                    tableCards_found[i] = basename(myfile).split(".")[0]

            for i in range (0,2):
                result = cv2.matchTemplate(playerCards[i], image, cv2.TM_CCORR_NORMED)
                if playerCards_max[i] < cv2.minMaxLoc(result)[1] and cv2.minMaxLoc(result)[1] > IMAGE_MATCH_THRESHOLD:
                    playerCards_max[i] = cv2.minMaxLoc(result)[1]
                    playerCards_found[i] = basename(myfile).split(".")[0]

    for i in range (0,5):
        if tableCards_found[i] is None:
            tableCards_found[i] = "-"
        elif tableCards_found[i].find("blank")>=0: tableCards_found[i] = "-"

    for i in range (0,2):
        if playerCards_found[i] is None:
            playerCards_found[i] = "-"
        elif playerCards_found[i].find("blank")>=0: playerCards_found[i] = "-"

    GUI.setTableCards(tableCards_found[0] + " " + tableCards_found[1] + " " + tableCards_found[2] + " " + tableCards_found[3] + " " + tableCards_found[4])
    GUI.setPlayerCards(playerCards_found[0] + " " + playerCards_found[1])

    hole_cards = cv2.imread("img/player_hole.png")
    playerStatus = [0] * 9
    number_players = 0
    for i in range (1,9):
        player = cv2.imread("prints/player" + str(i) + ".png")
        if cv2.minMaxLoc(cv2.matchTemplate(player, hole_cards, cv2.TM_CCORR_NORMED))[1] > IMAGE_MATCH_THRESHOLD:
            playerStatus[i] = 1
            number_players = number_players + 1
    if playerCards_found[0] != "-" and playerCards_found[1] != "-":
        playerStatus[0] = 1
        number_players = number_players + 1

    button = cv2.imread("img/button.png")
    window = cv2.imread("prints/window.png")
    button_location = cv2.minMaxLoc(cv2.matchTemplate(window, button, cv2.TM_CCORR_NORMED))[3]
    dealer = closest_point(button_location[0], button_location[1], buttonPositions)
    myPosition = position (dealer, playerStatus)
    
    potSize = pytesseract.image_to_string(Image.open("prints/pot.png"), config=tessdata_config)
    potSize = potSize.replace("Pot: ","")
    potSize = potSize.replace(",","").strip()
    potSize = potSize.replace(" ","")
    if potSize.isnumeric():
        GUI.setPotSize(potSize)
    else:
        GUI.setPotSize("ERROR")

    callSize = pytesseract.image_to_string(Image.open("prints/action.png"), config=tessdata_config)
    if callSize.find("Call")==0:
        callSize = callSize.replace("Call","").strip()
        if callSize.isnumeric():
            GUI.setCallSize(callSize)
        else:
            GUI.setCallSize("ERROR")
        if callSize.isnumeric() and potSize.isnumeric():
            GUI.setPotOdds(str(round(float(callSize)/float(potSize)*100,2))+"%")
        else:
            GUI.setPotOdds("ERROR")
    elif callSize.find("Check")==0:
        GUI.setCallSize("0")
        GUI.setPotOdds("0%")

    global previous_status, previous_number_players
    if playerCards_found[0] == "-" or playerCards_found[1] == "-":
        GUI.setStatus(NOT_IN_HAND, number_players)
        GUI.setCardOdds("")
        GUI.setPotOdds("")
        GUI.setCallSize("")
        status = NOT_IN_HAND
    elif tableCards_found[0] == "-" and tableCards_found[1] == "-" and tableCards_found[2] == "-" and tableCards_found[3] == "-" and tableCards_found[4] == "-":
        GUI.setStatus(PREFLOP, str(myPosition) + "/" + str(number_players))
        status = PREFLOP
    elif tableCards_found[0] != "-" and tableCards_found[1] != "-" and tableCards_found[2] != "-" and tableCards_found[3] == "-" and tableCards_found[4] == "-":
        GUI.setStatus(FLOP, str(myPosition) + "/" + str(number_players))
        status = FLOP
    elif tableCards_found[0] != "-" and tableCards_found[1] != "-" and tableCards_found[2] != "-" and tableCards_found[3] != "-" and tableCards_found[4] == "-":
        GUI.setStatus(TURN, str(myPosition) + "/" + str(number_players))
        status = TURN
    elif tableCards_found[0] != "-" and tableCards_found[1] != "-" and tableCards_found[3] != "-" and tableCards_found[3] != "-" and tableCards_found[4] != "-":
        GUI.setStatus(RIVER, str(myPosition) + "/" + str(number_players))
        status = RIVER

    allCards = playerCards_found
    for i in range (0, number_players):
        allCards.append("?")
        allCards.append("?")
    if (previous_status != status or previous_number_players != number_players) and status != NOT_IN_HAND:
        GUI.setCardOdds("calculating...")
        if status == PREFLOP:
            win_odds = str(round(holdem_calc.calculate(None, False, PREFLOP_SIMULATIONS, None, allCards, False)[1]*100,2))+"%"
        if status == FLOP:
            win_odds = str(round(holdem_calc.calculate([tableCards_found[0], tableCards_found[1], tableCards_found[2]], False, FLOP_SIMULATIONS, None, allCards, False)[1]*100,2))+"%"
        if status == TURN:
            win_odds = str(round(holdem_calc.calculate([tableCards_found[0], tableCards_found[1], tableCards_found[2], tableCards_found[3]], False, TURN_SIMULATIONS, None, allCards, False)[1]*100,2))+"%"
        if status == RIVER:
            win_odds = str(round(holdem_calc.calculate([tableCards_found[0], tableCards_found[1], tableCards_found[2], tableCards_found[3], tableCards_found[4]], False, RIVER_SIMULATIONS, None, allCards, False)[1]*100,2))+"%"
        GUI.setCardOdds(win_odds)
        previous_status = status
        previous_number_players = number_players

if __name__ == "__main__":
    run_flag = False
    previous_status = "init"
    previous_number_players = 0
    root = Tk()
    root.title("PSPy")
    GUI = MyGUI(root)
    root.mainloop()
