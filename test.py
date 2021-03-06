import pynput, keyboard, os
from threading import Lock
from tkinter import *
from PIL import Image, ImageShow, ImageTk
from random import shuffle
from time import sleep

supported_types = ['png', 'jpg', 'gif']

lock = Lock()

class App():
    def __init__(self):
        self._settings = self._read_settings()
        self._display = Display()
        self._image_manager = ImageManager()
        self._input_manager = InputManager(self)
        
        self._active = False
        self._paused = False
        self._dirty_path = None
        self._awake_flag = False

        self._cooldown = self._settings['duration']
        self._remaining_wait = self._settings['wait']

        self._start_loop()

    def awake(self):
        lock.acquire()
        self._awake_flag = True
        lock.release()
    
    def toggle_pause(self):
        if (self._active == False):
            return
        lock.acquire()
        self._paused = not self._paused
        lock.release()

    def toggle_label(self):
        if (self._active == False):
            return
        lock.acquire()
        self._display.toggleLabel()
        lock.release()

    def block_image(self):
        if (self._active == False):
            return
        lock.acquire()
        self._dirty_path = self._image_manager.block_image()
        lock.release()

    def next(self):
        if (self._active == False):
            return
        lock.acquire()
        self._dirty_path = self._image_manager.next()
        lock.release()

    def back(self):
        if (self._active == False):
            return
        lock.acquire()
        self._dirty_path = self._image_manager.back()
        lock.release()

    def _start_loop(self):
        updateRate = 0.1
        while 1:
            lock.acquire()
            if self._awake_flag == True:
                self._awake_flag = False
                self._remaining_wait = self._settings['wait']
                if (self._active):
                    self._deactivate()

            if self._active == True:
                if (self._paused == False):
                    self._cooldown = self._cooldown - updateRate
                    if self._cooldown <= 0 and self._dirty_path == None:
                        self._dirty_path = self._image_manager.next()
                if self._dirty_path != None:
                    self._cooldown = self._settings['duration']
                    while self._display.show_image(self._dirty_path) == False:
                        self._dirty_path = self._image_manager.next()
                    self._dirty_path = None
                self._display.update()
            else:
                self._remaining_wait -= updateRate
                if self._remaining_wait <= 0:
                    self._activate()    
            lock.release()
            sleep(updateRate)

    def _activate(self):
        self._settings = self._read_settings()
        self._input_manager.move_mouse_to_corner()
        self._cooldown = self._settings['duration']
        path = self._image_manager.load_images(self._settings['directory'])
        self._display.show()
        while self._display.show_image(path, False) == False:
            path = self._image_manager.next()
        self._active = True

    def _deactivate(self):
        self._display.hide()
        self._active = False

    def _read_settings(self):
        file = open('settings.txt', 'r')
        lines = file.read().split('\n')
        file.close()
        return {'directory': lines[0], 'duration': float(lines[1]), 'wait': float(lines[2])}

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
        self._mouse = pynput.mouse.Controller()
        self._ignore_mouse_move = False
        self._add_listeners()

    def _add_listeners(self):
        pynput.mouse.Listener.daemon = False
        self._mouse_listener = pynput.mouse.Listener(on_move=self._on_mouse_move)
        self._mouse_listener.start()

        keyboard.add_hotkey('left', self._app.back)
        keyboard.add_hotkey('right', self._app.next)
        keyboard.add_hotkey('space', self._app.toggle_pause)
        keyboard.add_hotkey('enter', self._app.toggle_label)
        keyboard.add_hotkey('tab', self._app.block_image)

    def move_mouse_to_corner(self):
        self._ignore_mouse_move = True
        self._mouse.move(10000, 10000) #move cursor out of the way to bottom-right corner
        self._ignore_mouse_move = False

    def _on_mouse_move(self, x, y):
        if not self._ignore_mouse_move:
            self._app.awake()

class ImageManager():

    def __init__(self):
        self._list = []
        self._history = []

    def _read_blacklist(self):
        file = open('blacklist.txt', 'r')
        lines = file.read().split('\n')
        file.close()
        return lines

    def block_image(self):
        path = self._list[self._index]

        file = open('blacklist.txt', 'a')
        file.write(path + '\n')
        file.close()

        del self._list[self._index]
        
        if self._index >= len(self._list):
            return self.next()
        else:
            return self._list[self._index]
        

    def load_images(self, path, blacklist = None):
        if blacklist == None:
            blacklist = self._read_blacklist()

        for file_name in os.listdir(path):
            full_path = path + '/' + file_name

            if full_path not in blacklist:
                if (os.path.isdir(full_path)):
                    self.load_images(full_path, blacklist)
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
        self._wrapper = self._make_wrapper()
        self._label = self._make_label()
        self._label_visible = True
        self._label_dirty = False
        self._image = None

        self.toggleLabel()

    def show_image(self, path, resize: bool = True):
        self._image = self._read_image_file(path)
        self._label.configure(text=path)
        if resize == True:
            successful = self._resize_image(self._frame.winfo_width(), self._frame.winfo_height())
            return successful

    def toggleLabel(self):
        self._label_dirty = True

    def update(self):
        if (self._label_dirty == True):
            self._label_visible = not self._label_visible
            self._label_dirty = False
            if (self._label_visible == True):
                self._label.place(relx=1.0, rely=1.0, x=-2, y=-2, anchor="se")
            else:
                self._label.place_forget()

        self._frame.update_idletasks()
        self._frame.update()

    def show(self):
        self._frame.deiconify()
        self._frame.focus_set()

    def hide(self):
        self._frame.withdraw()

    def _make_frame(self):
        frame = Tk()
        frame.wm_attributes('-fullscreen', 1)
        frame.configure(background='black')
        return frame

    def _make_label(self):
        label = Label(self._frame, text="(image path)", fg="red")
        label.place(relx=1.0, rely=1.0, x=-2, y=-2, anchor="se")
        return label

    def _make_wrapper(self):
        wrapper = Label()
        wrapper.bind('<Configure>', self._on_resize)
        wrapper.configure(background='black')
        wrapper.pack(fill = BOTH, expand = YES)
        return wrapper

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
        wrapper = self._wrapper

        window_aspect_ratio = width/height
        image_aspect_ratio = image.width/image.height

        new_width = None
        new_height = None

        if image_aspect_ratio < window_aspect_ratio:
            new_width = int(height*image_aspect_ratio)
            new_height = height
        else:
            new_width = width
            new_height = int(width/image_aspect_ratio)

        try:
            resizedImg = image.copy().resize((new_width, new_height), resample=Image.BICUBIC)
            photo = ImageTk.PhotoImage(resizedImg)
            wrapper.config(image = photo)
            wrapper.image = photo
            wrapper.pack()
        except Exception as a:
            print(a)
            return False

        return True
        

App()