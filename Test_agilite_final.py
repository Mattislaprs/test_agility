# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 13:58:59 2024

@author: Student
"""

import json
import os
import sys
import random
# =============================================================================
# import matplotlib.pyplot as plt
# import matplotlib.image as mpimg
# =============================================================================

from ALookCom.commandPub import CommandPub
from ALookCom.comBle import ComBle
from xdpchandler import *

import sensorParam
import setTimer
import nest_asyncio
nest_asyncio.apply()

name_device_ble = 'ENGO 1 123708'

# =============================================================================
#                             IMAGE ---> LUNETTES
# =============================================================================

# Choix connection Ble des lunettes
choice_ble_lunettes = input("Connecter les lunettes en bluetooth \n1 - Oui\n2 - Non (déjà connectées)\n")
print()

if choice_ble_lunettes == "1" :

    # Connection Ble 
    ## Créer l'object "com" via la class "ComBle"
    com = ComBle(True)
    
    ## Associer le nom des lunettes à "com"
    comName = com.findDeviceByName(name_device_ble)
    com.open(comName)

# Identifier la configuration comportant les images cibles dans la mémoire interne
## (class "CommandPub")
cmd = CommandPub(com)

## Sélectionner la configuration actuelle utilisée pour afficher les images
cmd.cfgSet('test_agilite') 

## Afficher l'image "vierge" 
cmd.imgDisplay(1,0,0) # -> id, x, y (x et y = placement dans les lunettes)





#----------------------------Partie Movella Dot-------------------------------#
# Choix connection Ble de l'IMU
choice_ble_IMU = input("Connecter l'IMU en bluetooth \n1 - Oui\n2 - Non (déjà connectées)\n")
print()

if choice_ble_IMU == "1" :

    # Bouton pour connecter IMU 
    input("Press enter pour connecter l'IMU XSens")
    print()
    
    # Initialisation 
    xdpcHandler = XdpcHandler() # IMU ne peut pas être déjà connecté sinon bug    
    
    # Vérifier l'initialisation du SDK pour PC
    if not xdpcHandler.initialize():
        xdpcHandler.cleanup()
        exit(-1)
    
    # Scanner si des dispositifs Movella DOT peuvent être détectés via Bluetooth
    xdpcHandler.scanForDots()
    
    # Si aucun dispositif détecté : fermer les connexions avec tous les dispositifs
    # Movella DOT et détruire le gestionnaire de connexion créé lors de l'initialisation
    if len(xdpcHandler.detectedDots()) == 0:  
        print("No Movella DOT device(s) found. Aborting.")
        xdpcHandler.cleanup()
        exit(-1)
    
    # Connection aux dispositifs Movella DOT détectés via une connexion USB ou Bluetooth
    xdpcHandler.connectDots()
    
    # Si aucune connection identifiée : xdpcHandler.cleanup() pour fermer connexion avec tous les dispositifs
    # Movella DOT et détruire le gestionnaire de connexion créé lors de l'initialisation
    if len(xdpcHandler.connectedDots()) == 0:
        print("Could not connect to any Movella DOT device(s). Aborting.")
        xdpcHandler.cleanup()
        exit(-1)
    
    
    device = xdpcHandler.connectedDots()[0]

input("Press enter pour lancer le test d'agilite")
print()

i = 0
while i == 0 :
    
    # Obtenir les profils du device disponile 
    filterProfiles = device.getAvailableFilterProfiles()
    print("Available filter profiles:")
    for f in filterProfiles:
        print(f.label()) # renvoie "General" ou "Dynamic"

    print(f"Current profile: {device.onboardFilterProfile().label()}")
    if device.setOnboardFilterProfile("General"):
        print("Successfully set profile to General")
    else:
        print("Setting filter profile failed!")

    print("Setting quaternion CSV output")
    device.setLogOptions(movelladot_pc_sdk.XsLogOptions_Quaternion)

    # Filname de sortie en .csv des résultats 
    logFileName = "logfile_" + device.bluetoothAddress().replace(':', '-') + ".csv"
    print(f"Enable logging to: {logFileName}")
    if not device.enableLogging(logFileName):
        print(f"Failed to enable logging. Reason: {device.lastResultText()}")

    print("Putting device into measurement mode.")
    if not device.startMeasurement(movelladot_pc_sdk.XsPayloadMode_ExtendedEuler):
        print(f"Could not put device into measurement mode. Reason: {device.lastResultText()}")
        continue
    
    print("\nMain loop. Recording data for 10 seconds.")
    print("-----------------------------------------")
    
    # Afficher des en-têtes pour voir à quel device appartiennent les données
    ## Affiche le nom du device (exemple : D4:22:CD:00:4B:33)
    s = ""
    s += f"{device.bluetoothAddress():42}"
    print("%s" % s, flush=True)
    
    # Initialisation d'un paramètre
    has_shown_graph = False
    #orientationResetDone = False
    
    
    # Paramétrage du temps (ms) pour réaliser la capture 
    ## Renvoie l'h actuelle en ms depuis le début de l'ère UNIX (1970)
    startTime = movelladot_pc_sdk.XsTimeStamp_nowMs()
    
    ## Enregistre les données du device pendant n temps (ici 10000ms) 
    while movelladot_pc_sdk.XsTimeStamp_nowMs() - startTime <= 10000:
        if xdpcHandler.packetsAvailable():
            s = ""
            
            # Récupérer le packet du device
            packet = xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())

            if packet.containsOrientation():
                # Récupérer les données d'accélération sur x, y, z
                euler = packet.freeAcceleration()
                s += f"PosX:{euler[0]:7.2f}, PosY:{euler[1]:7.2f}, PosZ:{euler[2]:7.2f}| "
            
            # Condition pour afficher l'image dans les lunettes en fonction de l'acc sur y (ou faire norme de l'acc ?)
            # Choix du seuil (ici 14m/s-2)
            if euler[2] > 14 and not has_shown_graph: 

                ## Afficher une image aléatoire de la direction cible
                cmd.clear() # coupe l'affichage de l'image actuelle
                target = random.randint(2, 5)
                cmd.imgDisplay(target,0,0) 
                
                ## Mise à jour du paramètre pour stopper 
                has_shown_graph = True
            
            # Afficher les données d'accélération
            print("%s\r" % s, end="", flush=True)
    
    print("\n-----------------------------------------", end="", flush=True)
    
    # Réinitialiser l'orientation du device (remise à zéro)
    print(f"\nRénitialisation de l'orientation (par default) du Dot {device.portInfo().bluetoothAddress()}: ", end="", flush=True)
    if device.resetOrientation(movelladot_pc_sdk.XRM_DefaultAlignment):
        print("OK", end="", flush=True)
    else:
        print(f"NOK: {device.lastResultText()}", end="", flush=True)
    print("\n", end="", flush=True) 
    
    print("\nStopping measurement...")

    # Vérifier si le device a arrêté les mesures
    if not device.stopMeasurement():
        print("Failed to stop measurement.")
    # Vérifier si le device cesse d'enregistrer les données de mesure
    if not device.disableLogging():
        print("Failed to disable logging.")
    
    # Choix pour arrêter ou lancer un nouveau test
    choice_stop = input("Voulez-vous lancer un nouveau test ? \n1 - Oui\n2 - Non \n3 - Stop et déconnecter l'IMU\n")
    print()
    
    if choice_stop == "1" :
        cmd.imgDisplay(1,0,0) # -> id, x, y (x et y = placement dans les lunettes)
        input("Press enter pour lancer un nouveau test d'agilité")
        print()
    
    if choice_stop == "2" :
        i+= 1 # fin de la boucle while
    
    if choice_stop == "3" :
        # Fermer connexion avec tous les devices et détruire le gestionnaire 
        # de connexion créé lors de l'initialisation
        xdpcHandler.cleanup() 


# =============================================================================
#                               IMAGE ---> CONSOLE
# =============================================================================

# =============================================================================
# # Chemin absolu actuel
# current_dir = os.getcwd() 
# 
# # Afficher l'image avec "plt"
# list_img = ['vierge', 'top_left', 'top_right', 'bottom_left', 'bottom_right']
# 
# img = mpimg.imread(current_dir + '/cfgDescriptor/test_agilite/img/'+list_img[target-1]+'.png') 
# plt.imshow(img)
# plt.axis('off')  # Pour masquer les axes
# plt.show()
# 
# input("Press enter pour démarrer un nouveau test d'agilité")
# print()
# =============================================================================
