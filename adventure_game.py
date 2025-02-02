import tkinter as tk
from game_logic import AppalachianAdventure

def main():
    root = tk.Tk()
    game = AppalachianAdventure(root)
    root.mainloop()

if __name__ == "__main__":
    main()