import pygame
from pygame import Color, Rect, Surface, Font
# from pygame.font import Font

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

    name = "anonymous"
    type: str
    enabled = True
    visible = True
    parent = None

    _disabledParent = False


class Frame(UIElement):
    position: Udim2
    size: Udim2
    anchorPoint = Vector2(0, 0)
    color: Color
    _surface = None

    actions: dict

    def __init__(self, position=Udim2(), size=Udim2.fromOffset(200, 50)):
        self.type = UI_ELEMENTS_TYPE_NAMES.get(self.__class__)
        self.position, self.size = position, size
        self.absolutePosition, self.absoluteSize = Vector2(), Vector2()
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
                action(self)

        updateActions = self.actions.get("onUpdate")
        if updateActions:
            for action in updateActions:
                action(self)

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
        surface = self._surface or self.updateRenderSurface(layer)
        surface.fill((0, 0, 0, 0))

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
    
    font: Font

    state = "idle"
    
    _cachedRender=("", None)

    def __init__(self, position=Udim2(), size=Udim2.fromOffset(200, 50), font=None):
        Frame.__init__(self, position, size)
        self.font = font or Font()
        self.textColor = Color("black")

    
    def render(self, layer, rect: Rect):
        # Render font if text changed
        if self._cachedRender[0] != self.text:
            render = self.font.render(self.text, True, self.textColor)
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
        isActivated = (self.state == "activated" or self.state == "hold")
        
        if isActivated and m1:
            self.state = "hold"

        if isActivated and not m1:
            self.state = "clicked"

        elif mouseCollision and m1:
            self.state = "activated"
        
        elif mouseCollision and not m1:
            self.state = "hovered"
        
        else:
            self.state = "idle"

        self.executeActions()

        return rect


DISPLAY_UI_ELEMENTS = {
    "FRAME": Frame,
    "TEXT_LABEL": TextLabel,
    "TEXT_BUTTON": TextButton
}

UI_ELEMENTS_TYPE_NAMES = {
    Frame: "FRAME",
    TextLabel: "TEXT_LABEL",
    TextButton: "TEXT_BUTTON"
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
        for infos in tree:
            elem_type = infos.get("type")
            elem_name = infos.get("name")
            if not elem_type:
                raise ValueError(f"{elem_name} ui tree element missing type")
            
            elem_class = DISPLAY_UI_ELEMENTS.get(elem_type)
            if not elem_class:
                raise ValueError(f"{elem_name} ui tree element invalid type: '{elem_type}'")

            elem = elem_class()
            self.setParent(elem, _parent)
            
            for propName, value in infos.items():
                if propName == "parent": continue

                if propName == "name":
                    self.descendants[value] = elem

                if propName == "children":
                    self.build(value, elem)
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
            if not elem.enabled: continue
            
            parent = elem.parent
            parentEnabled = parent.enabled and not parent._disabledParent

            if not parentEnabled:
                elem._disabledParent = True
            elif parentEnabled and elem._disabledParent:
                elem._disabledParent = False

            if elem._disabledParent: continue

            ## Update and render
            boundingBox = elem.update(surface)
            if elem.visible:
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


def demo():
    ratio = 1200/1920
    WIDTH = 1000
    HEIGHT = WIDTH*ratio
    window = pygame.display.set_mode((WIDTH, HEIGHT))
    ui_layer = UILayer(window)

    background_color = Color("black")

    mainPanel = Panel.fromLayer(ui_layer)
    mainPanel.build([
        {
            "type": "TEXT_LABEL",
            "position": (.5,0,0,10),
            "anchorPoint": (.5, 0),
            "font": Font(None, 50),
            "text": "DEMO",
            "textColor": "white",
            "transparency": 1
        }
    ])

    panel1 = Panel.fromLayer(ui_layer)
    panel1.build([
        {
            "type": "FRAME",
            "name": "main_frame",
            "position": (0,0,.5,0),
            "size": (.5,0,.5,0),
            "anchorPoint": (0, .5),
            "color": "blue",
            "children": [
                {
                    "type": "TEXT_LABEL",
                    "transparency": 1,
                    "size": (1,0,0,50),
                    "text": "Panel 1",
                    "font": Font(None, 40),
                    "textColor": "white"
                },
                {
                    "type": "TEXT_BUTTON",
                    "name": "main_button",
                    "size": (1,0, 0,50),
                    "position": (0,0,0,50),
                    "textColor": "red",
                    "color": "white",
                    "transparency": .75,
                    "font": Font(None, 35),
                    "textAlignment": (1, .5),
                    "text": "Spawn Panel 2 >"
                }
            ]
        }
    ])
    
    panel2 = Panel.fromLayer(ui_layer)
    panel2.enabled = False


    frame2 = Frame(position=Udim2.fromScale(1, .5), size=Udim2.fromScale(0.5,0.5))
    frame2.anchorPoint = Vector2(1, .5)
    frame2.color = Color("red")
    panel2.setParent(frame2)

    textlabel2 = TextLabel(size=Udim2(1,0,0,50))
    textlabel2.text = "Welcome to Panel 2"
    textlabel2.font = Font(None, 40)
    textlabel2.setTransparency(1)
    
    panel2.setParent(textlabel2, frame2)

    textbutton2 = TextButton(position=Udim2.fromOffset(0,50), size=Udim2(1,0, 0,50))
    textbutton2.font = Font(None, 35)
    textbutton2.fontSize = 40
    textbutton2.textColor = Color("blue")
    textbutton2.setTransparency(0)
    textbutton2.text = "Dispawn!"
    
    panel2.setParent(textbutton2, frame2)
    

    def displayPanel1(self):
        panel2.enabled = False
        panel1.enabled = True

    def displayPanel2(self):
        panel1.enabled = False
        panel2.enabled = True

    def hoverStyling(self):
        if self.state == "hovered":
            self.setTransparency(0)
        else:
            self.setTransparency(.25)

    panel1_btn = panel1.descendants["main_button"]
    panel1_btn.bindAction("clicked", displayPanel2)
    textbutton2.bindAction("clicked", displayPanel1)

    panel1_btn.bindAction("onUpdate", hoverStyling)
    textbutton2.bindAction("onUpdate", hoverStyling)


    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == 27:
                    return exit()

        now = time()

        if panel2.enabled:
            textlabel2.textAlignment = Vector2((cos(now) + 1)/2, (sin(now) + 1)/2)
        
        ui_layer.render()
        
        window.fill(background_color)
        window.blit(ui_layer.surface, (0, 0))
        
        pygame.display.flip()
        clock.tick(500)


if __name__=="__main__":
    demo()
