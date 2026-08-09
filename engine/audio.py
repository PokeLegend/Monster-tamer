import pygame

class AudioManager:
    def __init__(self):
        pygame.mixer.init()
        self.sounds = {}
        self.music_playing = False

    def load_sound(self, name, path):
        try:
            self.sounds[name] = pygame.mixer.Sound(path)
        except:
            pass

    def play_sound(self, name, loops=0):
        if name in self.sounds:
            self.sounds[name].play(loops)

    def play_music(self, path, loops=-1):
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(loops)
            self.music_playing = True
        except:
            pass

    def stop_music(self):
        pygame.mixer.music.stop()
        self.music_playing = False

    def set_volume(self, volume):
        pygame.mixer.music.set_volume(volume)
        for s in self.sounds.values():
            s.set_volume(volume)
