import pynput, keyboard, os
from tkinter import *
from PIL import Image, ImageShow, ImageTk
from random import shuffle
from time import sleep

supported_types = ['png', 'jpg', 'gif']

class App():
    def __init__(self):
        self._settings = self._read_settings()
        self._display = Display()
        self._image_manager = ImageManager()
        self._input_manager = InputManager(self)
        
        self._active = True
        self._paused = False
        self._dirtyPath = None

        path = self._image_manager.load_images(self._settings['directory'])
        self._display.show_image(path, False)

        self._cooldown = self._settings['duration']

        self._start_loop()

    def awake(self):
        #TODO
        pass
    
    def togglePause(self):
        if (self._active == False):
            return
        self._paused = not self._paused

    def next(self):
        if (self._active == False):
            return
        self._dirtyPath = self._image_manager.next()

    def back(self):
        if (self._active == False):
            return
        self._dirtyPath = self._image_manager.back()

    def _start_loop(self):
        updateRate = 0.1
        while 1:
            if (self._active == True):
                if (self._dirtyPath != None):
                    self._cooldown = self._settings['duration']
                    self._display.show_image(self._dirtyPath)
                    self._dirtyPath = None
                elif (self._paused == False):
                    self._cooldown = self._cooldown - updateRate
                    if self._cooldown <= 0:
                        self._cooldown = self._settings['duration']
                        path = self._image_manager.next()
                        self._display.show_image(path)
                self._display.update()
                sleep(updateRate)

    def _read_settings(self):
        file = open('settings.txt', 'r')
        lines = file.read().split('\n')
        return {'directory': lines[0], 'duration': float(lines[1])}

    def _list_files(self, path, list = []):
        for file_name in os.listdir(path):
            full_path = path + '/' + file_name
            
            if (os.path.isdir(full_path)):
                self._list_files(full_path, list)
            else:
                type = file_name.split('.')[-1]
                if type in supported_types:
                    list.append(full_path)

        return list


class InputManager():

    def __init__(self, app: App):
        self._app = app
        self._add_listeners()
        

    def _add_listeners(self):
        pynput.mouse.Listener.daemon = False
        mouse_listener = pynput.mouse.Listener(on_move=self._on_mouse_move)
        mouse_listener.start()

        keyboard.add_hotkey('left', self._app.back)
        keyboard.add_hotkey('right', self._app.next)
        keyboard.add_hotkey('space', self._app.togglePause)

    def _on_mouse_move(self, x, y):
        self._app.awake()

    def _on_key_press(self, key):
        if key == keyboard.Key.space:
            self._app.togglePause() 
        elif key.char == 'a':
            self._app.back()
        elif key.char == 'd':
            self._app.next()
        

class ImageManager():

    def __init__(self):
        self._list = []
        self._history = []

    def load_images(self, path):
        for file_name in os.listdir(path):
            full_path = path + '/' + file_name
            
            if (os.path.isdir(full_path)):
                self.load_images(full_path)
            else:
                type = file_name.split('.')[-1]
                if type in supported_types:
                    self._list.append(full_path)


        self._index = 0
        shuffle(self._list)
        return self._list[self._index]

    def next(self):
        self._index += 1
        if (self._index >= len(self._list)):
            shuffle(self._list)
            self._index = 0
        return self._list[self._index]

    def back(self):
        self._index -= 1
        if (self._index < 0):
            self._index = 0
        return self._list[self._index]


class Display():

    def __init__(self):
        self._frame = self._make_frame()
        self._label = self._make_label()
        self._image = None


    def show_image(self, path, resize: bool = True):
        self._image = self._read_image_file(path)
        if resize == True:
            self._resize_image(self._frame.winfo_width(), self._frame.winfo_height())

    def update(self):
        self._frame.update_idletasks()
        self._frame.update()

    def _make_frame(self):
        frame = Tk()
        frame.wm_attributes('-fullscreen', 1)
        frame.configure(background='black')
        return frame

    def _make_label(self):
        label = Label()
        label.bind('<Configure>', self._on_resize)
        label.configure(background='black')
        label.pack(fill = BOTH, expand = YES)
        return label

    def _read_image_file(self, path):
        try:
            image = Image.open(path)
            return image
        except IOError:
            print("cannot read image", path)

    def _on_resize(self, event):
        self._resize_image(event.width, event.height)

    def _resize_image(self, width, height):
        image = self._image
        label = self._label

        windowAspectRatio = width/height
        imageAspectRatio = image.width/image.height

        newWidth = None
        newHeight = None

        if imageAspectRatio < windowAspectRatio:
            newWidth = int(height*imageAspectRatio)
            newHeight = height
        else:
            newWidth = width
            newHeight = int(width/imageAspectRatio)

        resizedImg = image.copy().resize((newWidth, newHeight))
        photo = ImageTk.PhotoImage(resizedImg)
        label.config(image = photo)
        label.image = photo

App()