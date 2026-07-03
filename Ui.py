import pygame
from pygame import Color, Rect, Surface
from pygame.font import Font

import sys
from time import time
from math import floor, sin, cos
from pyvectors import Vector2

pygame.init()
clock = pygame.time.Clock()

def isSequence(v):
    return type(v) is list or type(v) is tuple

class Udim():
    size: float
    offset: int

    def __init__(self, size=0, offset=0):
        if isSequence(size):
            if len(size) != 2:
                raise ValueError("Udim: 'sequence' argument must be of length 2")
            
            self.size, self.offset = size
        
        else:
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
        if isSequence(scaleX):
            if len(scaleX) != 4:
                raise ValueError("Udim2: 'sequence' argument must be of length 4")
            
            scaleX, offsetX, scaleY, offsetY = scaleX

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
    anchorPoint = Vector2(0, 0)
    color: Color
    _surface = None

    actions: dict

    def __init__(self, position=Udim2(), size=Udim2.fromOffset(200, 50)):
        self.position = position
        self.size = size
        self.absolutePosition = Vector2()
        self.absoluteSize = Vector2()
        self.color = Color("white")

        self.actions = {}


    def updateRenderSurface(self, layer):
        surface = Surface(layer.get_size(), pygame.SRCALPHA)
        surface.set_alpha(255)
        self._surface = surface
        
        return surface

    def bindAction(self, state: str, action):
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
        self.absoluteSize = Vector2(self.size.calc(pSizeX, pSizeY))
        self.absolutePosition = parentPos + relPosition - self.absoluteSize * self.anchorPoint

        posX, posY = self.absolutePosition.components
        sizeX, sizeY = self.absoluteSize.components
        
        return pygame.Rect(posX, posY, sizeX, sizeY)

    def setTransparency(self, transparency: int):
        alpha = floor(255*(1 - transparency))
        self.color.update(self.color.r, self.color.g, self.color.b, alpha)

    def render(self, layer, rect: Rect) -> Rect:
        surface = self._surface
        if not surface:
            surface = self.updateRenderSurface(layer)
        
        surface.fill((0, 0, 0, 0))
        # self._surface = render

        draw_rect = pygame.draw.rect(surface, self.color, rect)
        layer.blit(surface)
        
        return draw_rect

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
    textAlignment = Vector2(0.5, 0.5)
    
    fontName = None
    fontSize = 12

    state = "idle"
    
    _cachedRender=("", None)

    def __init__(self, position=Udim2(), size=Udim2.fromOffset(200, 50)):
        Frame.__init__(self, position, size)
        self.font = pygame.font.Font(None, )
        self.textColor = Color("black")

    
    def render(self, layer, rect: Rect):
        # Render font if text changed
        if self._cachedRender[0] != self.text:
            font = Font(self.fontName, self.fontSize)
            render = font.render(self.text, True, self.textColor)
            self._cachedRender = (self.text, render)

        # Gets the text size and creates a rect centered from the background
        textSize = Vector2(self._cachedRender[1].get_size())
        rectSize = Vector2(rect.size)
        rectPos = Vector2(rect.x, rect.y)
        textPos = rectPos + (rectSize*self.textAlignment - textSize*self.textAlignment)
        
        textRect = Rect(textPos.x, textPos.y, textSize.x, textSize.y)

        # Draw background and text
        Frame.render(self, layer, rect)
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


DISPLAY_UI_ELEMENTS = {
    "frame": Frame,
    "text_label": TextLabel,
    "text_button": TextButton
}


class Panel(UIElement):
    elements: list
    descendants:dict

    def __init__(self):
        self.absolutePosition = Vector2()
        self.absoluteSize = Vector2()
        self.elements = []
        self.descendants = {}

    @classmethod
    def fromLayer(cls, layer):
        self = cls()
        self.parentToLayer(layer)
        return self

    
    def build(self, tree, _parent=None):
        for name, props in tree.items():
            elem = DISPLAY_UI_ELEMENTS[name]()
            self.setParent(elem, _parent)
            
            for propName, value in props.items():
                if propName == "parent": continue

                if propName == "name":
                    self.descendants[value] = elem
                
                if propName == "children":
                    self.build(tree, elem)
                    continue

                if propName == "transparency":
                    elem.setTransparency(value)
                    continue

                if propName in {"color", "textColor"}:
                    value = Color(value)
                if propName in {'position', 'size'}:
                    value = Udim2(value)
                if propName in {'anchorPoint', 'textAlignment'}:
                    value = Vector2(value)

                setattr(elem, propName, value)

        return self.descendants

    def parentToLayer(self, layer):
        self.parent = layer
        self.absoluteSize = Vector2(layer.width, layer.height)

        layer.panels.append(self)

    def setParent(self, child, parent=None):
        parentIndex = -1
        if parent is not None:
            try:
                parentIndex = self.elements.index(parent)
            except:
                raise ValueError("given 'parent' argument is not descendant of Panel")

        for i, elem in enumerate(self.elements):
            if elem is child:
                self.elements.pop(i)
        
        child.parent = parent or self
        self.elements.insert(parentIndex+1, child)

    def render(self, surface):
        for elem in self.elements:
            if elem.enabled:
                boundingBox = elem.update(surface)
                elem.render(surface, boundingBox)


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

    def render(self):
        self.surface.fill(Color(0, 0, 0, 0)) #Makes the surface fully transparent

        for panel in self.panels:
            if not panel.enabled: continue
            panel.render(self.surface)


def exit():
    pygame.quit()
    sys.exit()


def test():
    ratio = 1200/1920
    WIDTH = 1000
    HEIGHT = WIDTH*ratio
    window = pygame.display.set_mode((WIDTH, HEIGHT))
    ui_layer = UILayer(window)

    background_color = Color("red")

    panel1 = Panel.fromLayer(ui_layer)
    panel1.build({
        "frame": {
            "name": "main_frame",
            "position": (0,0,.5,0),
            "size": (.5,0,.5,0),
            "anchorPoint": (0, .5),
            "color": "blue",
            "children": {
                "text_button": {
                    "name": "main_button",
                    "size": (1,0, 0,50),
                    "textColor": "red",
                    "color": "black",
                    "transparency": .75,
                    "fontSize": 40,
                    "textAlignment": (1, .5),
                }
            }
        }
    })
    
    panel2 = Panel.fromLayer(ui_layer)
    panel2.enabled = False

    # frame1 = Frame(position=Udim2.fromScale(0.5, 0.5), size=Udim2.fromScale(.5, .5))
    # frame1.anchorPoint = Vector2(0.5, 0.5)
    # frame1.color = Color("blue")
    # panel1.setParent(frame1)

    frame2 = Frame(size=Udim2.fromScale(0.5,0.5))
    frame2.color = Color("red")
    panel2.setParent(frame2)


    # textbutton1 = TextButton(size=Udim2(1,0, 0,50))
    # textbutton1.fontSize = 40
    # textbutton1.textColor = Color("red")
    # textbutton1.color = Color("black")
    # textbutton1.setTransparency(.75)
    # textbutton1.textAlignment = Vector2(1, 0.5)
    
    # panel1.setParent(textbutton1, frame1)

    textbutton2 = TextButton(size=Udim2(1,0, 0,50))
    textbutton2.fontSize = 40
    textbutton2.textColor = Color("blue")
    textbutton2.setTransparency(0)
    
    panel2.setParent(textbutton2, frame2)
    

    def displayPanel1():
        panel2.enabled = False
        panel1.enabled = True

    def displayPanel2():
        panel1.enabled = False
        panel2.enabled = True

    panel1.descendants["main_button"].bindAction("activated", displayPanel2)
    textbutton2.bindAction("activated", displayPanel1)
    
    # def togglePanels():
    #     panel1.enabled = not panel1.enabled
    #     panel2.enabled = not panel2.enabled

    # textbutton1.bindAction("activated", togglePanels)
    # textbutton2.bindAction("activated", togglePanels)


    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == 27:
                    return exit()

        now = time()
        # pos = textbutton1.position
        # offset = sin(now)*20
        # textbutton1.position = Udim2.fromOffset(sin(now)*20, cos(now)*20)
        
        ui_layer.render()
        
        window.fill(background_color)
        window.blit(ui_layer.surface, (0, 0))
        
        pygame.display.flip()
        clock.tick(60)


if __name__=="__main__":
    test()
