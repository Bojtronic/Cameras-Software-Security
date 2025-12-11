class PersonPresenceController:
    def __init__(self, frames_on: int, frames_off: int):
        self.frames_on = frames_on
        self.frames_off = frames_off
        self.on_count = 0
        self.off_count = 0
        self.present = False

    def update(self, present_now: bool) -> bool:
        if present_now:
            self.on_count += 1
            self.off_count = 0
            if self.on_count >= self.frames_on:
                self.present = True
        else:
            self.off_count += 1
            self.on_count = 0
            if self.off_count >= self.frames_off:
                self.present = False

        return self.present