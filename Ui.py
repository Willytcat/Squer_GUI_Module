import pygame
from pygame import Color, Rect, Surface
from pygame.font import Font

import sys
from math import floor
from pyvectors import Vector2

pygame.init()
clock = pygame.time.Clock()

class Udim():
    size: float
    offset: int

    def __init__(self, size=0, offset=0):
        self.size = size
        self.offset = offset

    def __str__(self):
        return f"{self.size}, {self.offset}"

    def calc(self, absolute: int):
        return floor(absolute * self.size) + self.offset

class Udim2():
    x: Udim
    y: Udim

    def __init__(self, scaleX=0, offsetX=0, scaleY=0, offsetY=0):
        self.x, self.y = Udim(scaleX, offsetX), Udim(scaleY, offsetY)

    def __str__(self):
        return f"{self.x}; {self.y}"

    @classmethod
    def fromOffset(cls, offsetX: int, offsetY: int):
        return cls(0, offsetX, 0, offsetY)

    @classmethod
    def fromScale(cls, scaleX: float, scaleY: float):
        return cls(scaleX, 0, scaleY, 0)

    def calc(self, absoluteX: int, absoluteY: int):
        return self.x.calc(absoluteX), self.y.calc(absoluteY)


class UIElement():
    absoluteSize: Vector2
    absolutePosition: Vector2

    enabled = True
    parent = None


class Frame(UIElement):
    position: Udim2
    size: Udim2
    color: Color

    actions: dict

    def __init__(self, position=Udim2(), size=Udim2.fromOffset(200, 50)):
        self.position = position
        self.size = size
        self.absolutePosition = Vector2()
        self.absoluteSize = Vector2()
        self.color = Color("white")

        self.actions = {}

    def bindToState(self, state: str, action):
        stateActions = self.actions.get(state)
        
        if stateActions is None:
            self.actions[state] = [action]
        else:
            stateActions.append(action)

    def executeActions(self):
        stateActions = self.actions.get(self.state)
        if stateActions:
            for action in stateActions:
                action()

    def calcRect(self):
        parentPos = self.parent.absolutePosition
        pSizeX, pSizeY = self.parent.absoluteSize.components

        relPosition = Vector2(self.position.calc(pSizeX, pSizeY))
        self.absolutePosition = parentPos + relPosition
        self.absoluteSize = Vector2(self.size.calc(pSizeX, pSizeY))

        posX, posY = self.absolutePosition.components
        sizeX, sizeY = self.absoluteSize.components
        
        return pygame.Rect(posX, posY, sizeX, sizeY)

    def setTransparency(self, transparency: int):
        alpha = floor(255*(1 - transparency))
        self.color.update(self.color.r, self.color.g, self.color.b, alpha)

    def draw(self, surface, rect: Rect) -> Rect:
        return pygame.draw.rect(surface, self.color, rect)

    def update(self, surface) -> Rect:
        rect = self.calcRect()
        mX, mY = pygame.mouse.get_pos()

        if rect.collidepoint(mX, mY):
            self.state = "hovered"
        else:
            self.state = "idle"

        self.executeActions()

        return rect


class TextLabel(Frame):
    text = "Hell0 w0rld"
    textColor: Color
    
    fontName = None
    fontSize = 12

    state = "idle"
    
    _cachedRender=("", None)

    def __init__(self, position=Udim2(), size=Udim2.fromOffset(200, 50)):
        Frame.__init__(self, position, size)
        self.font = pygame.font.Font(None, )
        self.textColor = Color("black")

    
    def draw(self, layer, rect):
        # Render font if text changed
        if self._cachedRender[0] != self.text:
            font = Font(self.fontName, self.fontSize)
            render = font.render(self.text, True, self.textColor)
            self._cachedRender = (self.text, render)

        # Gets the text size and creates a rect centered from the background
        textWidth, textHeight = self._cachedRender[1].get_size()
        textRect = Rect(rect.centerx - textWidth/2, rect.centery - textHeight/2, textWidth, textHeight)

        # Draw background and text
        Frame.draw(self, layer, rect)
        layer.blit(self._cachedRender[1], textRect)

        return rect


class TextButton(TextLabel):
    def update(self, surface):
        rect = self.calcRect()
        mx, my = pygame.mouse.get_pos()
        m1 = pygame.mouse.get_pressed()[0]
        mouseCollision = rect.collidepoint(mx, my)

        if (self.state == "activated" or self.state == "hold") and m1:
            self.state = "hold"

        elif mouseCollision and m1:
            self.state = "activated"
        
        elif mouseCollision and not m1:
            self.state = "hovered"
        
        else:
            self.state = "idle"

        self.executeActions()

        return rect
        

class Panel(UIElement):
    elements: list

    def __init__(self):
        self.absolutePosition = Vector2()
        self.absoluteSize = Vector2()
        self.elements = []

    @classmethod
    def fromLayer(cls, layer):
        self = cls()
        self.parentToLayer(layer)
        return self

    def parentToLayer(self, layer):
        self.parent = layer
        self.absoluteSize = Vector2(layer.width, layer.height)

        layer.panels.append(self)

    def setElemParent(self, child, parent):
        parentIndex = None
        try:
            parentIndex = self.elements.index(parent)
        except:
            raise Exception("given parent is not a descendant of Panel")

        for i, elem in enumerate(self.elements):
            if elem is child:
                self.elements.pop(i)
        
        child.parent = parent
        self.elements.insert(parentIndex+1, child)


    def parentElem(self, elem):
        occurence = self.elements.count(elem)
        if occurence:
            raise Exception("element is already a descendant of Panel")

        elem.parent = self
        self.elements.append(elem)

    def draw(self, surface):
        for elem in self.elements:
            if elem.enabled:
                boundingBox = elem.update(surface)
                elem.draw(surface, boundingBox)


class UILayer():
    width: int
    height: int
    surface: Surface

    panels: list

    def __init__(self, screen: Surface):
        screenSize = screen.get_size()
        self.width, self.height = screenSize
        self.surface = Surface(screenSize, pygame.SRCALPHA)

        self.panels = []

    def draw(self):
        self.surface.fill(Color(0, 0, 0, 0)) #Makes the surface fully transparent

        for panel in self.panels:
            if panel.enabled:
                panel.draw(self.surface)



def exit():
    pygame.quit()
    sys.exit()


def main():
    ratio = 1200/1920
    WIDTH = 800
    HEIGHT = WIDTH*ratio
    window = pygame.display.set_mode((WIDTH, HEIGHT))
    layer = UILayer(window)

    background_color = Color("black")

    panel1 = Panel.fromLayer(layer)
    panel2 = Panel.fromLayer(layer)
    panel2.enabled = False

    frame1 = Frame(size=Udim2.fromScale(0.5,0.5))
    frame1.color = Color("blue")
    panel1.parentElem(frame1)

    frame2 = Frame(size=Udim2.fromScale(0.5,0.5))
    frame2.color = Color("red")
    panel2.parentElem(frame2)


    textbutton1 = TextButton(size=Udim2(1,0, 0,50))
    textbutton1.fontSize = 40
    textbutton1.textColor = Color("red")
    textbutton1.color = Color("white")
    textbutton1.setTransparency(0)
    
    panel1.setElemParent(textbutton1, frame1)

    textbutton2 = TextButton(size=Udim2(1,0, 0,50))
    textbutton2.fontSize = 40
    textbutton2.textColor = Color("blue")
    textbutton2.setTransparency(1)
    
    panel2.setElemParent(textbutton2, frame2)
    

    def togglePanels():
        panel1.enabled = not panel1.enabled
        panel2.enabled = not panel2.enabled

    textbutton1.bindToState("activated", togglePanels)
    textbutton2.bindToState("activated", togglePanels)


    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == 27:
                    return exit()
        
        window.fill(background_color)
        window.blit(layer.surface, (0, 0))

        layer.draw()
        
        pygame.display.flip()
        clock.tick(400)


if __name__=="__main__":
    main()
