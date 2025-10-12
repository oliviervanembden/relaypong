class wire:
    def __init__(self,):
        self.power = 0
        self.poweringPin = []
        self.poweredPin = []
    def powerWireOn(self,pin):
        print(f"powerd wire {self} on from {pin}")
        if pin in self.poweredPin:

            return []
        self.poweredPin.append(pin)
        self.poweringPin.remove(pin)
        if self.power:
            print("ha hier zit je error")
            return []
        else:
            self.power = 1
            return self.poweringPin# return the new pins that needs to be checkd
    def powerWireOff(self,pin):
        if pin in self.poweringPin:
            return []from codecs import namereplace_errors


class wire:
    def __init__(self,):
        self.power = 0
        self.poweringPin = []
        self.poweredPin = []
    def powerWireOn(self,pin):
        #print(f"powerd wire {self} on from {pin}")
        if pin in self.poweredPin:

            return []
        self.poweredPin.append(pin)
        self.poweringPin.remove(pin)
        if self.power:
            #print("ha hier zit je error")
            return []
        else:
            self.power = 1
            return self.poweringPin# return the new pins that needs to be checkd
    def powerWireOff(self,pin):
        if pin in self.poweringPin:
            return []
        self.poweredPin.remove(pin)
        self.poweringPin.append(pin)
        if self.poweredPin == []:
            self.power = 0
            return self.poweringPin## return the new pins that needs to be checkd
        else:
            return []
    def connectPin(self,pin):
        self.poweringPin.append(pin)

class diode:
    def __init__(self,powerIn: type[wire],powerOut: type[wire]):
        self.powerIn = powerIn
        self.powerOut = powerOut
        self.powerIn.connectPin([self, 4])
        self.powerOut.connectPin([self, -1])
    def updateDiode(self):
        if self.powerIn.power:
            return self.powerOut.powerWireOn([self,-1])
        else:
            return self.powerOut.powerWireOff([self,-1])

class relay:
    def __init__(self,coil: type[wire],comm: type[wire],nc: type[wire],no: type[wire]):
        self.coilWire = coil
        self.commWire = comm
        self.ncWire = nc
        self.noWire = no
        self.state = 0
        coil.connectPin([self,0])
        comm.connectPin([self,1])
        nc.connectPin([self,2])
        no.connectPin([self,3])

    def powerRelayOn(self):
        if self.state == 1:
            return []
        else: # the relay change from of to on
            """
            first set the nc pin to of
            #check if comm or no are power have nit ebalbe ti dont know if if faster
            if com is power than power no
            if no is power than power com
            """
            pinsToCheck = []
            self.state = 1

            if [self,2] in self.ncWire.poweredPin:
                # power the nc pin of and adds the nieuw pins that need to be check to the list

                pinsToCheck.extend((self.ncWire.powerWireOff([self,2])))
            if self.noWire.power: #checks if the no wire has power
                #power on the comm wire and adds the new pins to the check list
                pinsToCheck.extend(self.commWire.powerWireOn([self,1]))
            if self.commWire.power: # check if the com wire has power
                pinsToCheck.extend(self.noWire.powerWireOn([self,3]))
            #print(f"powered on  relay send {pinsToCheck} back to be checked")
            return pinsToCheck
    def getConnection(self,pin):
        if pin == 1:  # COM
            updates = []

            if self.commWire.power:
                if self.state:  # relay ON -> COM should be fed from NO
                    # If NC was feeding earlier, stop it.
                    if [self, 2] in self.ncWire.poweredPin:
                        updates.extend(self.ncWire.powerWireOff([self, 2]))
                    # If we're currently driving COM but NO lost power, drop COM.
                    if [self, 1] in self.commWire.poweredPin and not self.noWire.power:
                        updates.extend(self.commWire.powerWireOff([self, 1]))
                    # If NO has power and we're not yet driving COM, drive COM.
                    if self.noWire.power and [self, 1] not in self.commWire.poweredPin:
                        updates.extend(self.commWire.powerWireOn([self, 1]))
                else:  # relay OFF -> COM should be fed from NC
                    # If NO was feeding earlier, stop it.
                    if [self, 3] in self.noWire.poweredPin:
                        updates.extend(self.noWire.powerWireOff([self, 3]))
                    # If we're currently driving COM but NC lost power, drop COM.
                    if [self, 1] in self.commWire.poweredPin and not self.ncWire.power:
                        updates.extend(self.commWire.powerWireOff([self, 1]))
                    # If NC has power and we're not yet driving COM, drive COM.
                    if self.ncWire.power and [self, 1] not in self.commWire.poweredPin:
                        updates.extend(self.commWire.powerWireOn([self, 1]))
            else:
                # COM net has no power: make sure we are not still driving it,
                # and clear any stale contact feeds.
                if [self, 1] in self.commWire.poweredPin:
                    updates.extend(self.commWire.powerWireOff([self, 1]))
                if [self, 3] in self.noWire.poweredPin:
                    updates.extend(self.noWire.powerWireOff([self, 3]))
                if [self, 2] in self.ncWire.poweredPin:
                    updates.extend(self.ncWire.powerWireOff([self, 2]))

            return updates
        if pin == 3: # if the pin is the no pin
            if self.noWire.power:
                if self.state:
                    return self.commWire.powerWireOn([self,1]) # retrun the comm wire if the relay is powerd
                else:
                    return [] #retrun noting when the relay is not powered for th nc pin
            else:
                if self.state:
                    return self.commWire.powerWireOff([self,1]) # retrun the comm wire if the relay is powerd
                else:
                    return [] #retrun noting when the relay is not powered for th nc pin


        if pin == 2: # if the pin is the nc pin
            if self.ncWire.power:
                if self.state:
                    return [] # retun nothing when the relay is on becouse the nc is no conneced
                else:
                    return self.commWire.powerWireOn([self,1]) # return the comm wire if the relay is not powered
            else:
                if self.state:
                    return [] # retun nothing when the relay is on becouse the nc is no conneced
                else:

                    return self.commWire.powerWireOff([self,1]) # return the comm wire if the relay is not powered

    def powerRelayOff(self):
        if self.state == 0:
            return []
        else:# the relay change from of to on
            self.state = 0
            pinsToCheck = []
            """
            first set the no pin to of
            #check if comm or no are power have nit ebalbe ti dont know if if faster
            if com is power than power no
            if no is power than power com
            """
            if [self, 3] in self.noWire.poweredPin:
                # power the no pin of and adds the nieuw pins that need to be check to the list
                pinsToCheck.extend((self.noWire.powerWireOff([self, 3])))
            if self.ncWire.power: #checks if the nc wire has power
                #power on the comm wire and adds the new pins to the check list
                pinsToCheck.extend(self.commWire.powerWireOn([self,1]))
            if self.commWire.power: # check if the com wire has power
                # power on the nc pin
                pinsToCheck.extend(self.ncWire.powerWireOn([self,2]))
            #print(f"power of relay send {pinsToCheck} back to be checked")
            return pinsToCheck

class led:
    def __init__(self,wire: type[wire]):
        self.wire = wire
        self.wire.connectPin([self,5])
    def update(self):
        if self.wire.power:
            print("led is on")
        else:
            print("led is off")


class button:
    def __init__(self, wire):
        self.wire = wire
        self.wire.connectPin([self,-1])

    def press(self):
        # return the list from wire.powerOn(...)
        return self.wire.powerWireOn([self,-1])

    def release(self):
        # return the list from wire.powerOff(...)
        return self.wire.powerWireOff([self,-1])


def check(WireIn):
    toCheck = []
    toCheck.extend(WireIn)


    while toCheck != []:
        #print(f"ruuning next layer for {toCheck}")


        check = toCheck.copy()
        toCheck.clear()
        for pin in check:

            #pin[0] is the object that the shoud be check
            # pin[1] is the pin of that boject
            #print(f'running main loop for pin {pin}')
            if pin[1] == -1:
                continue
            elif pin[1] == 0:
                #print(f'checking pins for relays')
                if pin[0].coilWire.power == 1: # check if the relay need to be turn on
                    #print(f'turn relay {pin[0]} on')
                    toCheck.extend(pin[0].powerRelayOn())
                if pin[0].coilWire.power == 0:
                    #print(f'turn relay {pin[0]} off')
                    toCheck.extend(pin[0].powerRelayOff())
            elif  pin[1] < 4:# there is power or power is removed from one of the pins of the relay that
                #print(pin[1])
                addToCheck = pin[0].getConnection(pin[1])
                #print(f"relay pin f{pin[1]} check and added {addToCheck} to be check")
                toCheck.extend(addToCheck)
            elif pin[1] == 4:
                toCheck.extend(pin[0].updateDiode())
            elif pin[1] == 5:
                #print("want to update led ")
                pin[0].update()
        #print(F'end of layer to be ckech is f{toCheck}')
        toCheck  = [x for x in toCheck if x]


if __name__ == "__main__":
    print("je zit in de verkkede file")



"""
for a in check:
    if a[1] == 0: # turn relay on
        wiresToCheck= a[0].powerOn() # power on the relay
        if wiresToCheck[0].state or wiresToCheck[1].state == 1: # if there is power on one of the pins that are now connected
            if wiresToCheck[0].state == 1: # if  com gives the power
                if [a[0],2] in wiresToCheck[0].poweredWire() :
                    wiresToCheck[0].powerOff()
                #print([a[0],2])
                wiresToCheck[1].powerOn([a[0],3])# turn on no
            else: # if no gives the power
                wiresToCheck[0].powerOn([a[0],1]) # turn on comm
"""










        self.poweredPin.remove(pin)
        self.poweringPin.append(pin)
        if self.poweredPin == []:
            self.power = 0
            return self.poweringPin## return the new pins that needs to be checkd
        else:
            return []
    def connectPin(self,pin):
        self.poweringPin.append(pin)

class diode:
    def __init__(self,powerIn: type[wire],powerOut: type[wire]):
        self.powerIn = powerIn
        self.powerOut = powerOut
        self.powerIn.connectPin([self, 4])
        self.powerOut.connectPin([self, -1])
    def updateDiode(self):
        if self.powerIn.power:
            return self.powerOut.powerWireOn([self,-1])
        else:
            return self.powerOut.powerWireOff([self,-1])

class relay:
    def __init__(self,coil: type[wire],comm: type[wire],nc: type[wire],no: type[wire]):
        self.coilWire = coil
        self.commWire = comm
        self.ncWire = nc
        self.noWire = no
        self.state = 0
        coil.connectPin([self,0])
        comm.connectPin([self,1])
        nc.connectPin([self,2])
        no.connectPin([self,3])

    def powerRelayOn(self):
        if self.state == 1:
            return []
        else: # the relay change from of to on
            """
            first set the nc pin to of
            #check if comm or no are power have nit ebalbe ti dont know if if faster
            if com is power than power no
            if no is power than power com
            """
            pinsToCheck = []
            self.state = 1

            if [self,2] in self.ncWire.poweredPin:
                # power the nc pin of and adds the nieuw pins that need to be check to the list

                pinsToCheck.extend((self.ncWire.powerWireOff([self,2])))
            if self.noWire.power: #checks if the no wire has power
                #power on the comm wire and adds the new pins to the check list
                pinsToCheck.extend(self.commWire.powerWireOn([self,1]))
            if self.commWire.power: # check if the com wire has power
                pinsToCheck.extend(self.noWire.powerWireOn([self,3]))
            print(f"powered on  relay send {pinsToCheck} back to be checked")
            return pinsToCheck
    def getConnection(self,pin):
        if pin == 1:# if the pin is the comm pin
            # send back the connection from the that the com pin is conneced to
            if self.commWire.power:  # changed to on in the comm in
                if self.state:
                    return self.noWire.powerWireOn([self,3])# send the no wire if the relay has power
                else:
                    return self.ncWire.powerWireOn([self,2]) # send the nc wire if the relay has no power
            else:
                if self.state:
                    return self.noWire.powerWireOff([self,3])# send the no wire if the relay has power
                else:
                    return self.ncWire.powerWireOff([self,2]) # send the nc wire if the relay has no power

        if pin == 3: # if the pin is the no pin
            if self.noWire.power:
                if self.state:
                    return self.commWire.powerWireOn([self,1]) # retrun the comm wire if the relay is powerd
                else:
                    return [] #retrun noting when the relay is not powered for th nc pin
            else:
                if self.state:
                    return self.commWire.powerWireOff([self,1]) # retrun the comm wire if the relay is powerd
                else:
                    return [] #retrun noting when the relay is not powered for th nc pin


        if pin == 2: # if the pin is the nc pin
            if self.ncWire.power:
                if self.state:
                    return [] # retun notthing when the relay is on becouse the nc is no conneced
                else:
                    return self.commWire.powerWireOn([self,1]) # return the comm wire if the relay is not powered
            else:
                if self.state:
                    return [] # retun notthing when the relay is on becouse the nc is no conneced
                else:

                    return self.commWire.powerWireOff([self,1]) # return the comm wire if the relay is not powered

    def powerRelayOff(self):
        if self.state == 0:
            return []
        else:# the relay change from of to on
            self.state = 0
            pinsToCheck = []
            """
            first set the no pin to of
            #check if comm or no are power have nit ebalbe ti dont know if if faster
            if com is power than power no
            if no is power than power com
            """
            if [self, 3] in self.noWire.poweredPin:
                # power the no pin of and adds the nieuw pins that need to be check to the list
                pinsToCheck.extend((self.noWire.powerWireOff([self, 3])))
            if self.ncWire.power: #checks if the nc wire has power
                #power on the comm wire and adds the new pins to the check list
                pinsToCheck.extend(self.commWire.powerWireOn([self,1]))
            if self.commWire.power: # check if the com wire has power
                # power on the nc pin
                pinsToCheck.extend(self.ncWire.powerWireOn([self,2]))
            print(f"power of relay send {pinsToCheck} back to be checked")
            return pinsToCheck

class led:
    def __init__(self,wire: type[wire]):
        self.wire = wire
        self.wire.connectPin([self,5])
    def update(self):
        if self.wire.power:
            print("led is on")
        else:
            print("led is off")


class button:
    def __init__(self, wire):
        self.wire = wire
        self.wire.connectPin([self,-1])

    def press(self):
        # return the list from wire.powerOn(...)
        return self.wire.powerWireOn([self,-1])

    def release(self):
        # return the list from wire.powerOff(...)
        return self.wire.powerWireOff([self,-1])

Wcomm =wire()
Wnc = wire()
Wno = wire()
Wnc2 = wire()
Wno2 = wire()
junkWire1 = wire()
ledWire = wire()
R1 = relay(Wcomm,Wcomm,Wnc,Wno)
R2 = relay(Wno,Wno,Wnc2,Wno2)
R3 = relay(Wno2,Wno2,junkWire1,ledWire)
l1 = led(ledWire)


B1 = button(ledWire)
check = []
toCheck = []
toCheck.extend(B1.press())


while toCheck != []:
    print(f"ruuning next layer for {toCheck}")


    check = toCheck.copy()
    toCheck.clear()
    for pin in check:

        #pin[0] is the object that the shoud be check
        # pin[1] is the pin of that boject
        print(f'running main loop for pin {pin}')
        if pin[1] == 0:
            print(f'checking pins for relays')
            if pin[0].coilWire.power == 1: # check if the relay need to be turn on
                print(f'turn relay {pin[0]} on')
                toCheck.extend(pin[0].powerRelayOn())
            if pin[0].coilWire.power == 0:
                print(f'turn relay {pin[0]} off')
                toCheck.extend(pin[0].powerRelayOff())
        elif pin[1] < 4:# there is power or power is removed from one of the pins of the relay that
            addToCheck = pin[0].getConnection(pin[1])
            print(f"relay pin f{pin[1]} check and added {addToCheck} to be check")
            toCheck.append(addToCheck)
        elif pin[1] == 4:
            print("diode")
        elif pin[1] == 5:
            print("want to update led ")
            pin[0].update()
    print(F'end of layer to be ckech is f{toCheck}')
    toCheck  = [x for x in toCheck if x]


"""
for a in check:
    if a[1] == 0: # turn relay on
        wiresToCheck= a[0].powerOn() # power on the relay
        if wiresToCheck[0].state or wiresToCheck[1].state == 1: # if there is power on one of the pins that are now connected
            if wiresToCheck[0].state == 1: # if  com gives the power
                if [a[0],2] in wiresToCheck[0].poweredWire() :
                    wiresToCheck[0].powerOff()
                print([a[0],2])
                wiresToCheck[1].powerOn([a[0],3])# turn on no
            else: # if no gives the power
                wiresToCheck[0].powerOn([a[0],1]) # turn on comm
"""









