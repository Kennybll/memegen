#!env/bin/python

import os
import sys
import logging

ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(ROOT)

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import speech_recognition

from memegen import __project__, __version__
from memegen.settings import ProdConfig
from memegen.app import create_app
from memegen.domain import Text

log = logging.getLogger(__name__)


class Application:

    def __init__(self, app):
        self.app = app
        self.label = None
        self.text = None
        self._image = None
        self._update_event = None
        self._clear_event = None
        self._recogizer = speech_recognition.Recognizer()
        self._microphone = speech_recognition.Microphone()
        with self._microphone as source:
            log.info("Adjusting for ambient noise...")
            self._recogizer.adjust_for_ambient_noise(source)
        log.info("Listening in the background...")
        self._recogizer.listen_in_background(self._microphone, self.listen)

        # Configure root window
        self.root = tk.Tk()
        self.root.title("{} (v{})".format(__project__, __version__))
        self.root.minsize(500, 500)

        # Initialize the GUI
        self.label = None
        frame = self.init(self.root)
        frame.pack(fill=tk.BOTH, expand=1)

        # Start the event loop
        self.restart()
        self.root.mainloop()

    def init(self, root):
        padded = {'padding': 5}
        sticky = {'sticky': tk.NSEW}

        # Configure grid
        frame = ttk.Frame(root, **padded)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=0)
        frame.columnconfigure(0, weight=1)

        def frame_image(root):
            frame = ttk.Frame(root, **padded)

            # Configure grid
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)

            # Place widgets
            self.label = ttk.Label(frame)
            self.label.grid(row=0, column=0)

            return frame

        def frame_text(root):
            frame = ttk.Frame(root, **padded)

            # Configure grid
            frame.rowconfigure(0, weight=1)
            frame.rowconfigure(1, weight=1)
            frame.columnconfigure(0, weight=1)

            # Place widgets
            self.text = ttk.Entry(frame)
            self.text.bind("<Key>", self.restart)
            self.text.grid(row=0, column=0, **sticky)
            self.text.focus_set()

            return frame

        def separator(root):
            return ttk.Separator(root)

        # Place widgets
        frame_image(frame).grid(row=0, **sticky)
        separator(frame).grid(row=1, padx=10, pady=5, **sticky)
        frame_text(frame).grid(row=2, **sticky)

        return frame

    def listen(self, recognizer, audio):
        log.info("Recognizing speech...")
        try:
            value = recognizer.recognize_google(audio)
        except speech_recognition.UnknownValueError:
            log.warning("No text matched")
        else:
            log.info("Matched text: %s", value)
            self.clear()
            self.text.insert(0, value)

    def update(self):
        text = Text(self.text.get())

        ratio = 0
        match = None

        for template in self.app.template_service.all():
            _ratio, path = template.match(str(text).lower())
            if _ratio > ratio:
                ratio = _ratio
                log.info("Matched at %s: %s - %s", ratio, template, path)
                match = template, Text(path)

        if match:
            domain = self.app.image_service.create(*match)
            image = Image.open(domain.path)
            old_size = image.size
            max_size = self.root.winfo_width(), self.root.winfo_height()
            ratio = min(max_size[0]/old_size[0], max_size[1]/old_size[1]) * .9
            new_size = [int(s * ratio) for s in old_size]
            image = image.resize(new_size, Image.ANTIALIAS)
            self.image = ImageTk.PhotoImage(image)
            self.label.configure(image=self.image)

            self.clear()

        self.restart(update=True, clear=False)

    def clear(self, *_):
        self.text.delete(0, tk.END)
        self.restart()

    def restart(self, *_, update=True, clear=True):
        if update:
            if self._update_event:
                self.root.after_cancel(self._update_event)
            self._update_event = self.root.after(1000, self.update)
        if clear:
            if self._clear_event:
                self.root.after_cancel(self._clear_event)
            self._clear_event = self.root.after(5000, self.clear)


if __name__ == '__main__':
    Application(create_app(ProdConfig))
